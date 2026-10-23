import json

from approval import Approver
from audit import new_run_id
from executor import _is_failure, execute_plan, synthesize
from planner import generate_plan
from validation import dispatch


def _failed_steps(results: list[dict]) -> list[dict]:
    failed = []
    for number, step in enumerate(results, start=1):
        if _is_failure(step["result"]):
            error = step["result"]
            if isinstance(error, list):
                error = next(item for item in error if isinstance(item, dict) and "error" in item)
            failed.append({
                "step": number,
                "tool": step["tool"],
                "purpose": step["purpose"],
                "error": error["error"],
            })
    return failed


def _propose_send(request, output, results, recipient, approver, run_id) -> dict:
    # The recipient is a parameter, never something the model picks, so a
    # tool result can't redirect the email. The approver still sees it.
    if not recipient:
        return {"status": "not_proposed", "reason": "No recipient was given."}

    args = {
        "recipient": recipient,
        "subject": f"Report: {request}"[:200],
        "body": output.get("email_draft") or output.get("report") or "",
    }
    result = dispatch(
        "send_email",
        json.dumps(args),
        approver=approver,
        reason=f"Send the workflow report for: {request}",
        failed_steps=_failed_steps(results),
        run_id=run_id,
    )

    if isinstance(result, dict) and result.get("sent"):
        return {"status": "sent", "recipient": recipient, "path": result["path"]}
    return {"status": "not_sent", "recipient": recipient, "kind": result.get("kind"), "error": result.get("error")}


def run_workflow(
    request: str,
    stop_on_failure: bool = True,
    approver: Approver | None = None,
    recipient: str | None = None,
) -> dict:
    run_id = new_run_id()
    plan = generate_plan(request)
    results = execute_plan(plan, stop_on_failure=stop_on_failure, approver=approver, run_id=run_id)
    output = synthesize(request, results)

    # A denied or failed send never costs the user the report itself.
    output["email"] = _propose_send(request, output, results, recipient, approver, run_id)
    output["run_id"] = run_id
    return output
