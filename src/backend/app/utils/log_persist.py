"""Utility functions for task log persistence."""

import math
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, insert
from sqlmodel import Session

PROMOTED_KEYS = {"type", "level", "timestamp", "message"}


def sanitize_for_json(obj):
    """Replace non-finite floats (inf, -inf, nan) with None for strict JSON compliance."""
    if isinstance(obj, float):
        if math.isinf(obj) or math.isnan(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    return obj


def _parse_timestamp(raw) -> datetime | None:
    """Parse a timestamp value from a log entry."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    return None


def bulk_insert_task_logs(
    session: Session,
    task_id: uuid.UUID,
    logs: list[dict],
    chunk_size: int = 5000,
) -> None:
    """Bulk insert log entries into the task_log table in chunks.

    Args:
        session: Database session (FastAPI or Celery).
        task_id: Task ID to associate logs with.
        logs: List of log entry dicts from Redis.
        chunk_size: Number of rows per INSERT batch.
    """
    from app.models import TaskLog

    session.execute(delete(TaskLog).where(TaskLog.task_id == task_id))

    # Deduplicate "generated" entries by file_name, keeping the latest.
    seen_generated_keys: set = set()
    deduped: list[dict] = []
    for entry in reversed(logs):
        if entry.get("type") == "generated":
            gen_key = entry.get("file_name")
            if gen_key is None:
                data = entry.get("data")
                if isinstance(data, dict):
                    gen_key = data.get("id")
            if gen_key is not None:
                if gen_key in seen_generated_keys:
                    continue
                seen_generated_keys.add(gen_key)
        deduped.append(entry)
    deduped.reverse()

    now = datetime.now(UTC)
    rows = []
    for entry in deduped:
        strip_generated_code_content(entry)
        extra = {k: v for k, v in entry.items() if k not in PROMOTED_KEYS}
        rows.append(
            {
                "id": uuid.uuid4(),
                "task_id": task_id,
                "type": entry.get("type", "log"),
                "level": entry.get("level"),
                "timestamp": _parse_timestamp(entry.get("timestamp")),
                "message": entry.get("message"),
                "data": extra if extra else None,
                "created_time": now,
                "updated_time": now,
            }
        )

    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]
        session.execute(insert(TaskLog), chunk)


def strip_generated_code_content(entry: dict) -> None:
    """Null out the heavy source-code text inside a ``generated`` log entry.

    The ``code_artifacts[*].content`` field stores the full generated source code
    and dominates the log payload size. It is nulled on the persistence path so the
    full code is never stored in ``task_log``; other fields (``generation_meta``,
    ``worktree``, ``description``, metrics, etc.) are left intact so reports can still
    use them. The function mutates ``entry`` in place and only touches keys that
    already exist, so it is safe to call on entries that lack these fields (e.g.
    non-``generated`` entries or older payload shapes).

    Args:
        entry: A log entry dict whose nested ``data`` holds the solution payload.
    """
    if entry.get("type") != "generated":
        return
    data = entry.get("data")
    if not isinstance(data, dict):
        return
    artifacts = data.get("code_artifacts")
    if not isinstance(artifacts, list):
        return
    for artifact in artifacts:
        if isinstance(artifact, dict) and "content" in artifact:
            artifact["content"] = None


# Fields nulled from a "generated" log entry's nested solution data when serving the
# log-list API. These hold the full source code, generation metadata, worktree info,
# and the long description text — none of which are needed for list rendering or
# charts, and together they dominate the payload. Reports read logs through a separate
# path, so stripping them here does not affect report generation.
LIST_STRIPPED_GENERATED_FIELDS = ("code_artifacts", "generation_meta", "worktree", "description")


def strip_generated_fields_for_list(entry: dict) -> None:
    """Null out heavy fields inside a ``generated`` entry for log-list responses.

    More aggressive than :func:`strip_generated_code_content`: it nulls the entire
    ``code_artifacts``, ``generation_meta``, ``worktree`` and ``description`` fields
    rather than just the code text. Used only on the API read path, where the dropped
    fields are not needed. Mutates ``entry`` in place and only touches keys that
    already exist, so it safely tolerates non-``generated`` entries and older payload
    shapes.

    Args:
        entry: A log entry dict whose nested ``data`` holds the solution payload.
    """
    if entry.get("type") != "generated":
        return
    data = entry.get("data")
    if not isinstance(data, dict):
        return
    for key in LIST_STRIPPED_GENERATED_FIELDS:
        if key in data:
            data[key] = None


def task_log_to_dict(log) -> dict:
    """Convert a TaskLog ORM row back to the original dict format.

    Args:
        log: TaskLog model instance.

    Returns:
        Dict matching the original Redis log entry format.
    """
    result: dict = {"type": log.type}
    if log.timestamp is not None:
        result["timestamp"] = log.timestamp.isoformat()
    if log.level is not None:
        result["level"] = log.level
    if log.message is not None:
        result["message"] = log.message
    if log.data:
        result.update(log.data)
    return result
