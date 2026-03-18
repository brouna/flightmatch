"""Email sending and response token utilities."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.config import get_settings

_serializer: URLSafeTimedSerializer | None = None


def _get_serializer() -> URLSafeTimedSerializer:
    global _serializer
    if _serializer is None:
        settings = get_settings()
        _serializer = URLSafeTimedSerializer(settings.secret_key, salt="match-response")
    return _serializer


def generate_response_token(match_id: int, response: str) -> str:
    """Generate a signed token for pilot email response links."""
    return _get_serializer().dumps({"match_id": match_id, "response": response})


def verify_response_token(token: str, max_age_seconds: int = 72 * 3600) -> dict | None:
    """Verify and decode a response token. Returns None on failure."""
    try:
        return _get_serializer().loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None


async def send_match_email(
    pilot_email: str,
    pilot_name: str,
    mission: Any,
    match_log_id: int,
) -> bool:
    """Send mission match notification email to a pilot."""
    settings = get_settings()

    if not settings.mail_username and not settings.mail_server:
        return False  # Email not configured

    accept_token = generate_response_token(match_log_id, "accepted")
    decline_token = generate_response_token(match_log_id, "declined")

    accept_url = f"{settings.frontend_base_url}/api/v1/matches/respond?token={accept_token}"
    decline_url = f"{settings.frontend_base_url}/api/v1/matches/respond?token={decline_token}"

    try:
        from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
        from jinja2 import Environment, FileSystemLoader
        import os

        templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(loader=FileSystemLoader(templates_dir))

        context = {
            "pilot_name": pilot_name,
            "mission_title": mission.title if hasattr(mission, "title") else str(mission),
            "origin": mission.origin_airport if hasattr(mission, "origin_airport") else "",
            "destination": mission.destination_airport if hasattr(mission, "destination_airport") else "",
            "earliest_departure": mission.earliest_departure if hasattr(mission, "earliest_departure") else "",
            "accept_url": accept_url,
            "decline_url": decline_url,
        }

        html_template = env.get_template("mission_match.html")
        html_body = html_template.render(**context)

        txt_template = env.get_template("mission_match.txt")
        txt_body = txt_template.render(**context)

        conf = ConnectionConfig(
            MAIL_USERNAME=settings.mail_username,
            MAIL_PASSWORD=settings.mail_password,
            MAIL_FROM=settings.mail_from,
            MAIL_PORT=settings.mail_port,
            MAIL_SERVER=settings.mail_server,
            MAIL_STARTTLS=settings.mail_starttls,
            MAIL_SSL_TLS=settings.mail_ssl_tls,
            USE_CREDENTIALS=bool(settings.mail_username),
        )

        message = MessageSchema(
            subject=f"Mission Match: {context['mission_title']}",
            recipients=[pilot_email],
            body=html_body,
            subtype=MessageType.html,
            alternative_body=txt_body,
        )

        fm = FastMail(conf)
        await fm.send_message(message)
        return True
    except Exception:
        return False
