"""Persistent, local top ten shared by the browser and the export command."""
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3

NAME = re.compile(r"[A-Za-z0-9_]{3,12}")


def data_path():
    override = os.environ.get("LANTERN_DATA_DIR")
    default = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "dao-den-long"
    return (Path(override).expanduser() if override else default) / "leaderboard.sqlite3"


def connect(path=None):
    path = data_path() if path is None else Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, score INTEGER NOT NULL,
            nights_won INTEGER NOT NULL, achieved_at TEXT NOT NULL, seed TEXT NOT NULL
        )
    """)
    return db


def list_entries(db):
    entries = db.execute("""
        SELECT name, score, nights_won, achieved_at, seed FROM scores
        ORDER BY score DESC, achieved_at ASC, id ASC LIMIT 10
    """)
    return [{**entry, "seed": int(entry["seed"])} for entry in entries]


def entries(path=None):
    with closing(connect(path)) as db:
        return list_entries(db)


def save(name, score, nights_won, seed, path=None):
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise ValueError("Tên phải có 3–12 ký tự A–Z, 0–9 hoặc dấu gạch dưới.")
    achieved_at = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    with closing(connect(path)) as db, db:
        db.execute("INSERT INTO scores(name, score, nights_won, achieved_at, seed) VALUES (?, ?, ?, ?, ?)",
                   (name, score, nights_won, achieved_at, str(seed)))
        db.execute("""
            DELETE FROM scores WHERE id NOT IN (
                SELECT id FROM scores ORDER BY score DESC, achieved_at ASC, id ASC LIMIT 10
            )
        """)
        return list_entries(db)


def export(path):
    Path(path).write_text(json.dumps({"entries": entries()}, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
