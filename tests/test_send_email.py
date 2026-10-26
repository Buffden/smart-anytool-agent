import email
import json
from pathlib import Path
from unittest.mock import patch

from approval import ScriptedApprover
from config import settings
from tools import send_email
from validation import dispatch

_ARGS = {"recipient": "ops@example.com", "subject": "Headcount", "body": "Engineering: 12"}


def _outbox() -> list[Path]:
    path = Path(settings.outbox_dir)
    return sorted(path.glob("*.eml")) if path.exists() else []


def test_send_email_writes_exactly_one_file():
    result = send_email(**_ARGS)
    files = _outbox()
    assert len(files) == 1
    assert result == {"sent": True, "recipient": "ops@example.com", "path": str(files[0])}


def test_outbox_file_is_a_readable_email():
    send_email(**_ARGS)
    message = email.message_from_string(_outbox()[0].read_text())
    assert message["To"] == "ops@example.com"
    assert message["Subject"] == "Headcount"
    assert message.get_payload().strip() == "Engineering: 12"


def test_two_sends_make_two_files():
    send_email(**_ARGS)
    send_email(**_ARGS)
    assert len(_outbox()) == 2


def test_unwritable_outbox_returns_transport_error():
    with patch("pathlib.Path.open", side_effect=PermissionError("read-only")):
        result = send_email(**_ARGS)
    assert result["kind"] == "transport"
    assert "error" in result


def test_bad_recipient_is_a_validation_error():
    result = dispatch("send_email", json.dumps({**_ARGS, "recipient": "the team"}))
    assert result["kind"] == "validation"
    assert _outbox() == []


def test_missing_body_is_a_validation_error():
    args = {k: v for k, v in _ARGS.items() if k != "body"}
    assert dispatch("send_email", json.dumps(args))["kind"] == "validation"


def test_dispatch_without_approver_sends_nothing():
    result = dispatch("send_email", json.dumps(_ARGS))
    assert result["kind"] == "denied"
    assert _outbox() == []


def test_dispatch_approved_sends_one_file():
    result = dispatch("send_email", json.dumps(_ARGS), approver=ScriptedApprover([True]))
    assert result["sent"] is True
    assert len(_outbox()) == 1


def test_dispatch_denied_sends_nothing():
    result = dispatch("send_email", json.dumps(_ARGS), approver=ScriptedApprover([False]))
    assert result["kind"] == "denied"
    assert _outbox() == []
