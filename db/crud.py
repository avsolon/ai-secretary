import logging
from typing import Optional, List, Dict, Any

from db.database import get_connection

logger = logging.getLogger(__name__)


def get_user(db_path: str, telegram_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    cur = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def create_user(db_path: str, telegram_id: int, username: str = None,
                first_name: str = None, last_name: str = None) -> Dict[str, Any]:
    conn = get_connection(db_path)
    conn.execute(
        """INSERT OR IGNORE INTO users (telegram_id, username, first_name, last_name)
           VALUES (?, ?, ?, ?)""",
        (telegram_id, username, first_name, last_name),
    )
    conn.commit()
    return get_user(db_path, telegram_id)


def update_user(db_path: str, telegram_id: int, **kwargs) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    fields = []
    values = []
    for key, val in kwargs.items():
        fields.append(f"{key} = ?")
        values.append(val)
    if not fields:
        return get_user(db_path, telegram_id)
    values.append(telegram_id)
    conn.execute(
        f"UPDATE users SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?",
        values,
    )
    conn.commit()
    return get_user(db_path, telegram_id)


def is_admin(db_path: str, telegram_id: int) -> bool:
    user = get_user(db_path, telegram_id)
    if user and user.get("is_admin"):
        return True
    return False


def save_booking_session(db_path: str, user_id: int, state: str,
                         data: Dict[str, Any]) -> int:
    conn = get_connection(db_path)
    existing = conn.execute(
        "SELECT id FROM booking_sessions WHERE user_id = ? AND state != 'completed'",
        (user_id,),
    ).fetchone()
    if existing:
        conn.execute(
            """UPDATE booking_sessions
               SET state = ?, service = ?, date = ?, time = ?,
                   client_name = ?, client_phone = ?, comment = ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (state, data.get("service"), data.get("date"), data.get("time"),
             data.get("client_name"), data.get("client_phone"), data.get("comment"),
             existing["id"]),
        )
        conn.commit()
        return existing["id"]
    else:
        cur = conn.execute(
            """INSERT INTO booking_sessions
               (user_id, state, service, date, time, client_name, client_phone, comment)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, state, data.get("service"), data.get("date"), data.get("time"),
             data.get("client_name"), data.get("client_phone"), data.get("comment")),
        )
        conn.commit()
        return cur.lastrowid


def get_services(db_path: str) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    cur = conn.execute("SELECT * FROM services WHERE is_active = 1 ORDER BY name")
    return [dict(r) for r in cur.fetchall()]


def add_service(db_path: str, name: str, description: str = "",
                duration_minutes: int = 60) -> int:
    conn = get_connection(db_path)
    cur = conn.execute(
        "INSERT OR IGNORE INTO services (name, description, duration_minutes) VALUES (?, ?, ?)",
        (name, description, duration_minutes),
    )
    conn.commit()
    return cur.lastrowid


def create_appointment(db_path: str, user_id: int, service_name: str,
                       appointment_date: str, start_time: str, end_time: str,
                       client_name: str = None, client_phone: str = None,
                       comment: str = None, google_event_id: str = None) -> int:
    conn = get_connection(db_path)
    cur = conn.execute(
        """INSERT INTO appointments
           (user_id, service_name, appointment_date, start_time, end_time,
            client_name, client_phone, comment, google_event_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, service_name, appointment_date, start_time, end_time,
         client_name, client_phone, comment, google_event_id),
    )
    conn.commit()
    return cur.lastrowid


def get_appointments(db_path: str, date: str = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    if date:
        cur = conn.execute(
            "SELECT * FROM appointments WHERE appointment_date = ? ORDER BY start_time",
            (date,),
        )
    else:
        cur = conn.execute(
            "SELECT * FROM appointments ORDER BY appointment_date DESC, start_time DESC LIMIT 50"
        )
    return [dict(r) for r in cur.fetchall()]


def save_document_record(db_path: str, filename: str, source: str,
                         chunks_count: int) -> int:
    conn = get_connection(db_path)
    cur = conn.execute(
        "INSERT INTO knowledge_documents (filename, source, chunks_count) VALUES (?, ?, ?)",
        (filename, source, chunks_count),
    )
    conn.commit()
    return cur.lastrowid


def get_documents(db_path: str) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    cur = conn.execute("SELECT * FROM knowledge_documents ORDER BY uploaded_at DESC")
    return [dict(r) for r in cur.fetchall()]
