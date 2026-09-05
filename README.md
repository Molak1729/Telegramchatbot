# Telegram Personal Agent Bot

A Telegram bot that acts as a personal assistant. It can:

- Answer technical (and general) questions using an AI model
- Manage a to-do list (add, list, complete)
- Set reminders that ping you at a chosen time

Built with Python, `python-telegram-bot`, SQLite, and APScheduler.

## Project layout

| File            | Purpose                                             |
| --------------- | --------------------------------------------------- |
| `bot.py`        | Entry point: wires up commands and the AI handler   |
| `config.py`     | Loads settings from `.env`                          |
| `db.py`         | SQLite storage for to-dos and reminders             |
| `ai.py`         | AI provider (Gemini by default, OpenAI optional)    |
| `scheduler.py`  | Fires reminders on time (APScheduler)               |
| `timeparse.py`  | Understands "in 10 minutes", "at 6:30pm", etc.      |

## Requirements

- Python 3.10 - 3.12 recommended. (Python 3.13/3.14 may work but some
  dependencies can lag on brand-new releases; if `pip install` fails to build a
  package, use 3.12.)
- Works on Windows, macOS, and Linux. The code is cross-platform; only the shell
  commands below differ per OS.

## Setup

### 1. Create and activate a virtual environment

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If activation is blocked on Windows by execution policy, run once:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 2. Install dependencies

**macOS / Linux**

```bash
pip3 install -r requirements.txt
```

**Windows (PowerShell)**

```powershell
pip install -r requirements.txt
```

### 3. Configure secrets

Copy the example env file:

**macOS / Linux**

```bash
cp .env.example .env
```

**Windows (PowerShell)**

```powershell
Copy-Item .env.example .env
```

Then edit `.env`:

- `TELEGRAM_BOT_TOKEN` — from @BotFather (use a freshly revoked token)
- `GEMINI_API_KEY` — from https://aistudio.google.com/app/apikey (free tier)
- `TIMEZONE` — e.g. `Asia/Kolkata` or `America/New_York`

To use OpenAI instead of Gemini, set `AI_PROVIDER=openai`, fill `OPENAI_API_KEY`,
and also install the client: `pip install openai`.

### 4. Run

**macOS / Linux**

```bash
python3 bot.py
```

**Windows (PowerShell)**

```powershell
python bot.py
```

Open Telegram, find your bot by its `@username`, and send `/start`.

## Commands

| Command                  | Example                              |
| ------------------------ | ------------------------------------ |
| `/ask <question>`        | `/ask explain async in python`       |
| `/todo <task>`           | `/todo buy groceries`                |
| `/list`                  | show open to-dos                     |
| `/done <id>`             | `/done 3`                            |
| `/remind <when> <text>`  | `/remind in 10 minutes call mom`     |

Reminder time formats: `in 10 minutes ...`, `at 6:30pm ...`, `tomorrow 09:00 ...`.

You can also just type any message and the AI will answer it.

## Optional: register the command menu in Telegram

Send this to @BotFather via `/setcommands`, pick your bot, then paste:

```
ask - Ask the assistant a question
todo - Add a to-do item
list - Show your open to-dos
done - Mark a to-do complete (needs id)
remind - Set a reminder
help - Show help
```

## Security note

Never commit your `.env` or share your bot token. If a token is exposed,
revoke it in @BotFather (`/mybots` -> your bot -> API Token -> Revoke) and
put the new one in `.env`.
