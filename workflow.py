from executor import execute_plan, synthesize
from planner import generate_plan


def run_workflow(request: str, stop_on_failure: bool = True) -> dict:
    plan = generate_plan(request)
    results = execute_plan(plan, stop_on_failure=stop_on_failure)
    return synthesize(request, results)
