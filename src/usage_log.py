"""
Usage / audit logging for the Similar Question Search app.

Every search a user runs is appended as one line of JSON to a dated file
under LOGS_DIR (config/settings.py) -- who ran it, when, what they asked,
and what came back. This is deliberately plain-text, append-only JSON
Lines rather than a database: easy to read by hand, easy to grep, easy to
ship into a real log pipeline later without a rewrite, and it can never
corrupt older records the way an in-place-edited file could.

Logging failures must never break a search for the user -- if the log
file can't be written (disk full, permissions, read-only filesystem),
record_search() swallows the error after logging a warning and the caller
still gets its result.
"""

from __future__ import annotations

import json
import logging
import pathlib
from datetime import datetime, timezone
from typing import Optional

from config.settings import LOGS_DIR

logger = logging.getLogger(__name__)


def _log_path(when: datetime) -> pathlib.Path:
    logs_dir = pathlib.Path(LOGS_DIR)
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir / f"usage_{when.strftime('%Y-%m-%d')}.jsonl"


def record_search(
    evaluator_name: str,
    question: str,
    matches: Optional[list] = None,
    elapsed_seconds: float = 0.0,
    error: Optional[str] = None,
) -> None:
    """
    Append one audit record for a single search.

    matches is the same list of dicts search_similar_questions() returns
    (conversation_id, question_number, similarity_score, reasoning, ...)
    -- stored as-is so the log is a complete record of what the evaluator
    saw, not just a summary of it. Pass error (a short string) instead of
    matches when the search itself failed.
    """
    now = datetime.now(timezone.utc)
    record = {
        "timestamp_utc": now.isoformat(timespec="seconds"),
        "evaluator": (evaluator_name or "").strip() or "unknown",
        "question": question,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "match_count": len(matches) if matches else 0,
        "matches": matches or [],
        "error": error,
    }

    try:
        path = _log_path(now)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.warning("Could not write usage log entry: %s", exc)


def get_last_used() -> Optional[dict]:
    """
    Return the most recent audit record across all log files, or None if
    nothing has been logged yet. Not currently shown in the UI -- kept
    here in case a "last used by X at Y" banner is wanted later, so that
    only app.py would need a small addition, not this module.
    """
    logs_dir = pathlib.Path(LOGS_DIR)
    if not logs_dir.exists():
        return None

    files = sorted(logs_dir.glob("usage_*.jsonl"))
    if not files:
        return None

    last_line = None
    try:
        with open(files[-1], "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    last_line = line
    except OSError as exc:
        logger.warning("Could not read usage log: %s", exc)
        return None

    if not last_line:
        return None

    try:
        return json.loads(last_line)
    except json.JSONDecodeError:
        return None
