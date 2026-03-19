from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    db_path = Path(settings.sqlite_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rewrite_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS youtube_jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                result_json TEXT,
                error_text TEXT,
                export_files_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def insert_rewrite_run(request_data: dict[str, Any], response_data: dict[str, Any]) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO rewrite_runs (request_json, response_json, created_at)
            VALUES (?, ?, ?)
            """,
            (json.dumps(request_data, ensure_ascii=False), json.dumps(response_data, ensure_ascii=False), _now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)


def create_youtube_job(job_id: str, payload: dict[str, Any], status: str = "queued") -> None:
    now = _now_iso()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO youtube_jobs (job_id, status, payload_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, status, json.dumps(payload, ensure_ascii=False), now, now),
        )
        conn.commit()


def update_youtube_job(
    job_id: str,
    *,
    status: Optional[str] = None,
    result: Optional[dict[str, Any]] = None,
    error_text: Optional[str] = None,
    export_files: Optional[dict[str, str]] = None,
) -> None:
    updates: list[str] = ["updated_at = ?"]
    values: list[Any] = [_now_iso()]

    if status is not None:
        updates.append("status = ?")
        values.append(status)
    if result is not None:
        updates.append("result_json = ?")
        values.append(json.dumps(result, ensure_ascii=False))
    if error_text is not None:
        updates.append("error_text = ?")
        values.append(error_text)
    if export_files is not None:
        updates.append("export_files_json = ?")
        values.append(json.dumps(export_files, ensure_ascii=False))

    values.append(job_id)

    with _connect() as conn:
        conn.execute(f"UPDATE youtube_jobs SET {', '.join(updates)} WHERE job_id = ?", values)
        conn.commit()


def get_youtube_job(job_id: str) -> Optional[dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM youtube_jobs WHERE job_id = ?", (job_id,)).fetchone()

    if not row:
        return None

    def _loads(raw: Optional[str]) -> Any:
        if not raw:
            return None
        return json.loads(raw)

    return {
        "job_id": row["job_id"],
        "status": row["status"],
        "payload": _loads(row["payload_json"]),
        "result": _loads(row["result_json"]),
        "error": row["error_text"],
        "export_files": _loads(row["export_files_json"]) or {},
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
