import pytest

from config import settings


@pytest.fixture(autouse=True)
def _isolated_side_effects(tmp_path, monkeypatch):
    # Keep test runs out of the real audit log and outbox.
    monkeypatch.setattr(settings, "audit_log_path", str(tmp_path / "audit.jsonl"))
    monkeypatch.setattr(settings, "outbox_dir", str(tmp_path / "outbox"))
