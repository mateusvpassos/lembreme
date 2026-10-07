"""Persistência em SQLite (%APPDATA%\\Lembreme\\lembreme.db)."""
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .parser import next_occurrence


@dataclass
class Reminder:
    id: int
    message: str
    due: datetime
    recurrence: str
    anchor_day: int | None


def default_path() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home())) / "Lembreme"
    base.mkdir(parents=True, exist_ok=True)
    return base / "lembreme.db"


class Store:
    def __init__(self, path: Path | str | None = None):
        self.db = sqlite3.connect(str(path or default_path()))
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                due TEXT NOT NULL,
                recurrence TEXT NOT NULL DEFAULT 'unica',
                anchor_day INTEGER,
                active INTEGER NOT NULL DEFAULT 1,
                created TEXT NOT NULL
            )""")
        self.db.commit()

    @staticmethod
    def _row(r) -> Reminder:
        return Reminder(r[0], r[1], datetime.fromisoformat(r[2]), r[3], r[4])

    def add(self, message: str, due: datetime, recurrence: str = "unica", anchor_day: int | None = None) -> int:
        cur = self.db.execute(
            "INSERT INTO reminders (message, due, recurrence, anchor_day, created) VALUES (?,?,?,?,?)",
            (message, due.isoformat(timespec="minutes"), recurrence, anchor_day,
             datetime.now().isoformat(timespec="seconds")))
        self.db.commit()
        return cur.lastrowid

    def active(self) -> list[Reminder]:
        rows = self.db.execute(
            "SELECT id, message, due, recurrence, anchor_day FROM reminders WHERE active=1 ORDER BY due")
        return [self._row(r) for r in rows]

    def due(self, now: datetime) -> list[Reminder]:
        return [r for r in self.active() if r.due <= now]

    def delete(self, rid: int):
        self.db.execute("DELETE FROM reminders WHERE id=?", (rid,))
        self.db.commit()

    def fire(self, r: Reminder, now: datetime):
        """Marca como disparado: único desativa, recorrente avança p/ próxima data futura."""
        nxt = next_occurrence(r.due, r.recurrence, r.anchor_day)
        while nxt and nxt <= now:
            nxt = next_occurrence(nxt, r.recurrence, r.anchor_day)
        if nxt:
            self.db.execute("UPDATE reminders SET due=? WHERE id=?", (nxt.isoformat(timespec="minutes"), r.id))
        else:
            self.db.execute("UPDATE reminders SET active=0 WHERE id=?", (r.id,))
        self.db.commit()
