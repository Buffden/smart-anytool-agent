import argparse
import logging
import sys

from smart import self_awareness_check
import retriever


def configure_logging(verbose: bool) -> None:
    if verbose:
        logging.basicConfig(
            level=logging.INFO,
            format="[%(name)s] %(message)s",
            stream=sys.stdout,
        )
    else:
        logging.disable(logging.CRITICAL)


def run_cli(verbose: bool) -> None:
    print("Smart AnyTool Agent  (type 'exit' or 'quit' to stop)\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        try:
            result = self_awareness_check(user_input)

            if not result["needs_tool"]:
                if verbose:
                    print(f"[SMART] Answering directly - no tool needed. Reason: {result['reason']}")
                answer = result["answer"] or "I can answer that directly, but no answer was returned."
            else:
                if verbose:
                    print(f"[SMART] Tool required. Reason: {result['reason']}")
                answer = retriever.run(user_input)

            print(f"Agent: {answer}\n")

        except Exception as exc:
            print(f"Agent: Sorry, something went wrong: {exc}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smart AnyTool Agent CLI")
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show pipeline decisions (SMART layer, category selection, tool calls)",
    )
    args = parser.parse_args()

    configure_logging(args.verbose)
    run_cli(args.verbose)


if __name__ == "__main__":
    main()
