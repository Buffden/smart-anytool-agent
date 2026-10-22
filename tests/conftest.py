import pytest

from config import settings


@pytest.fixture(autouse=True)
def _isolated_audit_log(tmp_path, monkeypatch):
    # Keep test runs out of the real audit log.
    monkeypatch.setattr(settings, "audit_log_path", str(tmp_path / "audit.jsonl"))
