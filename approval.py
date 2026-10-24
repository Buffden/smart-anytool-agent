import getpass
import json
from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class ApprovalRequest:
    tool: str
    args: dict
    reason: str = ""
    # Steps that failed earlier in the same run, so the human sees them
    # before deciding instead of approving a send built on missing data.
    failed_steps: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class Decision:
    approved: bool
    by: str


Approver = Callable[[ApprovalRequest], Decision]


class ScriptedApprover:
    """Answers from a fixed list, for tests. Runs out -> says no."""

    def __init__(self, answers: list[bool], by: str = "scripted"):
        self._answers = list(answers)
        self._by = by
        self.requests: list[ApprovalRequest] = []

    def __call__(self, request: ApprovalRequest) -> Decision:
        self.requests.append(request)
        approved = self._answers.pop(0) if self._answers else False
        return Decision(approved=approved, by=self._by)


class CliApprover:
    """Shows the full pending action in the terminal and waits for 'yes'."""

    def __init__(self, input_fn=input, print_fn=print):
        self._input = input_fn
        self._print = print_fn
        self.by = f"cli:{getpass.getuser()}"

    def __call__(self, request: ApprovalRequest) -> Decision:
        self._print("\n=== Approval needed ===")
        # Failed steps first, so they can't be missed under a long body.
        if request.failed_steps:
            self._print("WARNING: earlier steps in this run failed:")
            for step in request.failed_steps:
                self._print(f"  step {step['step']} ({step['tool']}, {step['purpose']}): {step['error']}")
        self._print(f"Action: {request.tool}")
        if request.reason:
            self._print(f"Reason: {request.reason}")
        self._print("Arguments:")
        self._print(json.dumps(request.args, indent=2))
        answer = self._input("Type 'yes' to approve, anything else declines: ")
        return Decision(approved=answer.strip().lower() == "yes", by=self.by)
