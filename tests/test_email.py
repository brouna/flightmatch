"""Tests for email token generation and verification."""
import pytest
from app.notifications.email import generate_response_token, verify_response_token


def test_token_roundtrip():
    token = generate_response_token(match_id=42, response="accepted")
    data = verify_response_token(token)
    assert data is not None
    assert data["match_id"] == 42
    assert data["response"] == "accepted"


def test_invalid_token():
    result = verify_response_token("garbage.token.value")
    assert result is None


def test_decline_token():
    token = generate_response_token(match_id=99, response="declined")
    data = verify_response_token(token)
    assert data["response"] == "declined"


def test_expired_token():
    # Manually forge a token with a very old timestamp using itsdangerous internals
    from itsdangerous import URLSafeTimedSerializer
    from app.config import get_settings
    s = URLSafeTimedSerializer(get_settings().secret_key, salt="match-response")
    # Dump payload, then verify with max_age=-1 (always expired)
    token = s.dumps({"match_id": 1, "response": "accepted"})
    result = verify_response_token(token, max_age_seconds=-1)
    assert result is None
