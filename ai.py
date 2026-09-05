"""AI provider abstraction.

Supports Google Gemini (default) and OpenAI. The provider is selected via
the AI_PROVIDER env var. Keeps a tiny per-chat conversation history so the
assistant has short-term context.
"""
from collections import defaultdict, deque
from typing import Deque, Dict, List

import config

SYSTEM_PROMPT = (
    "You are a helpful personal assistant living inside a Telegram bot. "
    "You answer technical questions clearly and concisely, help manage "
    "to-dos and reminders, and keep a friendly, practical tone. When code "
    "is useful, provide short, correct examples."
)

# Keep the last N message pairs per chat for lightweight context.
_HISTORY_TURNS = 6
_history: Dict[int, Deque[dict]] = defaultdict(lambda: deque(maxlen=_HISTORY_TURNS * 2))


def _remember(chat_id: int, role: str, content: str) -> None:
    _history[chat_id].append({"role": role, "content": content})


# ---------------- Gemini ----------------

def _ask_gemini(chat_id: int, prompt: str) -> str:
    import google.generativeai as genai

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        config.GEMINI_MODEL, system_instruction=SYSTEM_PROMPT
    )

    # Gemini uses "user"/"model" roles.
    contents: List[dict] = []
    for msg in _history[chat_id]:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [msg["content"]]})
    contents.append({"role": "user", "parts": [prompt]})

    response = model.generate_content(contents)
    return (response.text or "").strip()


# ---------------- OpenAI ----------------

def _ask_openai(chat_id: int, prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(_history[chat_id])
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=config.OPENAI_MODEL, messages=messages
    )
    return (response.choices[0].message.content or "").strip()


# ---------------- Public API ----------------

def ask(chat_id: int, prompt: str) -> str:
    """Answer a prompt using the configured provider, with error safety."""
    try:
        if config.AI_PROVIDER == "openai":
            answer = _ask_openai(chat_id, prompt)
        else:
            answer = _ask_gemini(chat_id, prompt)
    except Exception as exc:  # noqa: BLE001 - surface a clean message to the user
        return f"Sorry, I couldn't reach the AI service ({exc})."

    if not answer:
        return "I didn't get a response from the AI service. Please try again."

    _remember(chat_id, "user", prompt)
    _remember(chat_id, "assistant", answer)
    return answer
