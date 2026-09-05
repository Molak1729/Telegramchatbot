"""Telegram personal-agent bot.

Commands:
  /start            Welcome + help
  /help             Show help
  /ask <question>   Ask the AI a question
  /todo <task>      Add a to-do
  /list             Show open to-dos
  /done <id>        Mark a to-do complete
  /remind <when> <text>   e.g. /remind in 10 minutes call mom

Any plain message (no command) is answered by the AI.
"""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import ai
import config
import db
import scheduler
import timeparse

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("bot")

_LOCAL_TZ = ZoneInfo(config.TIMEZONE)

HELP_TEXT = (
    "\U0001f916 *Personal Agent*\n\n"
    "I can answer technical questions, manage your to-dos, and remind you of things.\n\n"
    "*Commands*\n"
    "/ask <question> \u2013 ask me anything\n"
    "/todo <task> \u2013 add a to-do\n"
    "/list \u2013 show open to-dos\n"
    "/done <id> \u2013 complete a to-do\n"
    "/remind <when> <text> \u2013 set a reminder\n\n"
    "*Reminder examples*\n"
    "`/remind in 10 minutes drink water`\n"
    "`/remind at 6:30pm gym`\n"
    "`/remind tomorrow 09:00 standup`\n\n"
    "You can also just type a message and I'll answer it."
)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_markdown(HELP_TEXT)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_markdown(HELP_TEXT)


async def ask_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = " ".join(context.args).strip()
    if not question:
        await update.message.reply_text("Usage: /ask <your question>")
        return
    await _answer_with_ai(update, question)


async def todo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    task = " ".join(context.args).strip()
    if not task:
        await update.message.reply_text("Usage: /todo <task>")
        return
    todo_id = db.add_todo(update.effective_chat.id, task)
    await update.message.reply_text(f"Added to-do #{todo_id}: {task}")


async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = db.list_todos(update.effective_chat.id)
    if not rows:
        await update.message.reply_text("Your to-do list is empty. \U0001f389")
        return
    lines = [f"#{r['id']}  {r['task']}" for r in rows]
    await update.message.reply_text("Your to-dos:\n" + "\n".join(lines))


async def done_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /done <id>")
        return
    todo_id = int(context.args[0])
    if db.complete_todo(update.effective_chat.id, todo_id):
        await update.message.reply_text(f"Marked #{todo_id} as done. \u2705")
    else:
        await update.message.reply_text(f"No open to-do with id #{todo_id}.")


async def remind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text(
            "Usage: /remind <when> <text>\nExample: /remind in 10 minutes call mom"
        )
        return

    due_utc, body = timeparse.parse(text)
    if due_utc is None:
        await update.message.reply_text(
            "I couldn't understand the time. Try:\n"
            "\u2022 in 10 minutes ...\n\u2022 at 6:30pm ...\n\u2022 tomorrow 09:00 ..."
        )
        return

    chat_id = update.effective_chat.id
    reminder_id = db.add_reminder(chat_id, body, due_utc)
    scheduler.schedule_reminder(reminder_id, chat_id, body, due_utc)

    local_time = due_utc.astimezone(_LOCAL_TZ).strftime("%Y-%m-%d %H:%M")
    await update.message.reply_text(
        f"Okay, I'll remind you at {local_time}: {body}"
    )


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _answer_with_ai(update, update.message.text)


async def _answer_with_ai(update: Update, prompt: str) -> None:
    chat_id = update.effective_chat.id
    await update.effective_chat.send_action(ChatAction.TYPING)
    answer = ai.ask(chat_id, prompt)
    await update.message.reply_text(answer)


async def _on_startup(app: Application) -> None:
    scheduler.start(app.bot)
    logger.info("Scheduler started; bot is ready.")


def main() -> None:
    db.init_db()

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).post_init(_on_startup).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ask", ask_cmd))
    app.add_handler(CommandHandler("todo", todo_cmd))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CommandHandler("done", done_cmd))
    app.add_handler(CommandHandler("remind", remind_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))

    logger.info("Starting bot (provider=%s)...", config.AI_PROVIDER)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
