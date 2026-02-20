import json
import os
from datetime import datetime

SESSIONS_FILE = os.path.join(os.path.dirname(__file__), "sessions.json")
MAX_SESSIONS = 10


def load_sessions() -> list:
    if not os.path.exists(SESSIONS_FILE):
        return []
    with open(SESSIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_session(label: str, form_data: dict) -> None:
    sessions = load_sessions()
    now = datetime.now()
    sessions.insert(
        0,
        {
            "id": now.strftime("%Y%m%d%H%M%S%f"),
            "label": label,
            "saved_at": now.strftime("%d-%m-%Y %H:%M"),
            "form_data": form_data,
        },
    )
    sessions = sessions[:MAX_SESSIONS]
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)
