import json
import sqlite3
from pathlib import Path

from backend.config import Config
from backend.models.schema import SCHEMA_SQL


DEFAULT_SETTINGS = {
    "distance_warning_mm": 350,
    "distance_presence_mm": 1200,
    "light_low_lux": 150,
    "temperature_high_c": 30,
    "humidity_high_percent": 75,
    "leave_grace_seconds": 15,
    "snapshot_enabled": True,
    "snapshot_event_types": ["distance_too_close", "presence_away"],
    "lamp_control": {
        "brightness": 68,
        "color_temperature": 4100,
        "scene_mode": "eye_care",
    },
}


THRESHOLD_SETTING_KEYS = frozenset(
    {
        "distance_warning_mm",
        "distance_presence_mm",
        "light_low_lux",
        "temperature_high_c",
        "humidity_high_percent",
        "leave_grace_seconds",
    }
)


def _connect():
    Path(Config.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate_db(conn):
    columns = {row[1] for row in conn.execute("PRAGMA table_info(events)").fetchall()}
    if "snapshot_path" not in columns:
        conn.execute("ALTER TABLE events ADD COLUMN snapshot_path TEXT")
    if "has_snapshot" not in columns:
        conn.execute("ALTER TABLE events ADD COLUMN has_snapshot INTEGER NOT NULL DEFAULT 0")


def get_threshold_settings(settings=None):
    source = settings if settings is not None else get_settings()
    return {key: source[key] for key in THRESHOLD_SETTING_KEYS if key in source}


def init_db():
    with _connect() as conn:
        conn.executescript(SCHEMA_SQL)
        _migrate_db(conn)
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO NOTHING
                """,
                (key, json.dumps(value)),
            )
        conn.commit()


def execute(query, params=()):
    with _connect() as conn:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.lastrowid


def fetch_one(query, params=()):
    with _connect() as conn:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None


def fetch_all(query, params=()):
    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def get_settings():
    rows = fetch_all("SELECT key, value FROM settings ORDER BY key")
    result = {}
    for row in rows:
        result[row["key"]] = json.loads(row["value"])
    return result


def update_settings(payload):
    with _connect() as conn:
        for key, value in payload.items():
            conn.execute(
                """
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, json.dumps(value)),
            )
        conn.commit()
    return get_settings()
