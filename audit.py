import datetime
import json
import uuid
from pathlib import Path

from config import settings


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def outcome_of(result) -> str:
    # Same two failure shapes executor._is_failure checks: a dict with
    # "error", or web_search's list wrapping one.
    if isinstance(result, dict) and "error" in result:
        return result.get("kind", "error")
    if isinstance(result, list) and any(isinstance(r, dict) and "error" in r for r in result):
        return "error"
    return "success"


def record(
    *,
    run_id: str | None,
    tool: str,
    risk: str,
    args,
    decision: str,
    decided_by: str | None,
    outcome: str,
) -> None:
    # Append-only: the file is only ever opened in "a" mode. Arguments are
    # kept, results are not (they can be large and hold rows from the DB).
    entry = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "run_id": run_id,
        "tool": tool,
        "risk": risk,
        "args": args,
        "decision": decision,
        "decided_by": decided_by,
        "outcome": outcome,
    }
    path = Path(settings.audit_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
