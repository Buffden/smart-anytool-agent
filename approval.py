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
