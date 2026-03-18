"""Celery tasks for email notifications."""
import asyncio
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.notifications.send_match_notifications", bind=True, max_retries=3)
def send_match_notifications(self, mission_id: int):
    """Send match notification emails for all pilots in a mission's match log."""
    asyncio.run(_send_match_notifications_async(mission_id))


async def _send_match_notifications_async(mission_id: int):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.database import AsyncSessionLocal
    from app.models import Mission, MatchLog, Pilot
    from app.notifications.email import send_match_email

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Mission)
            .where(Mission.id == mission_id)
            .options(selectinload(Mission.passengers))
        )
        mission = result.scalar_one_or_none()
        if not mission:
            return

        result = await db.execute(
            select(MatchLog)
            .where(
                MatchLog.mission_id == mission_id,
                MatchLog.notification_sent == False,  # noqa: E712
            )
            .order_by(MatchLog.rank)
        )
        match_logs = result.scalars().all()

        for log in match_logs:
            result = await db.execute(select(Pilot).where(Pilot.id == log.pilot_id))
            pilot = result.scalar_one_or_none()
            if not pilot:
                continue

            sent = await send_match_email(
                pilot_email=pilot.email,
                pilot_name=pilot.name,
                mission=mission,
                match_log_id=log.id,
            )
            if sent:
                log.notification_sent = True

        await db.commit()
