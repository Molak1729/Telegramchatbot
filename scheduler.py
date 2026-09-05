"""Reminder scheduling built on APScheduler.

The scheduler runs in the background. Each due reminder triggers a coroutine
that sends the Telegram message and marks the reminder as fired. Pending
reminders are reloaded on startup so nothing is lost across restarts.
"""
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

import config
import db

logger = logging.getLogger(__name__)
_UTC = ZoneInfo("UTC")

_scheduler = AsyncIOScheduler(timezone="UTC")
_bot: Bot | None = None


def start(bot: Bot) -> None:
    """Start the scheduler and re-arm any reminders still pending."""
    global _bot
    _bot = bot
    if not _scheduler.running:
        _scheduler.start()
    for row in db.pending_reminders():
        due = datetime.fromisoformat(row["due_at"])
        if due.tzinfo is None:
            due = due.replace(tzinfo=_UTC)
        _arm(row["id"], row["chat_id"], row["text"], due)


def schedule_reminder(reminder_id: int, chat_id: int, text: str, due_at_utc: datetime) -> None:
    _arm(reminder_id, chat_id, text, due_at_utc)


def _arm(reminder_id: int, chat_id: int, text: str, due_at_utc: datetime) -> None:
    now = datetime.now(tz=_UTC)
    run_date = due_at_utc if due_at_utc > now else now
    _scheduler.add_job(
        _fire,
        trigger="date",
        run_date=run_date,
        args=[reminder_id, chat_id, text],
        id=f"reminder-{reminder_id}",
        replace_existing=True,
        misfire_grace_time=3600,
    )


async def _fire(reminder_id: int, chat_id: int, text: str) -> None:
    if _bot is None:
        return
    try:
        await _bot.send_message(chat_id=chat_id, text=f"\u23f0 Reminder: {text}")
        db.mark_reminder_fired(reminder_id)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to send reminder %s", reminder_id)
