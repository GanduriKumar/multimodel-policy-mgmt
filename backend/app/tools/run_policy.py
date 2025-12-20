"""
CLI to evaluate a policy against input text.

- Loads a policy JSON from a file path argument into PolicyDoc.
- Reads input text from STDIN.
- Evaluates using app.services.policy_engine.evaluate_policy.
- Prints JSON with fields: {"allowed": bool, "reasons": [str, ...]}.

Usage examples:
  type input.txt | python -m app.tools.run_policy path/to/policy.json
  echo "some text" | python -m app.tools.run_policy policy.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Tuple, List

# Ensure the 'backend' directory is on sys.path so we can import app modules
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.schemas.policy_format import PolicyDoc  # noqa: E402
from app.services.policy_engine import evaluate_policy  # noqa: E402


def _parse_args() -> argparse.Namespace:
    """
    Parse CLI arguments.
    """
    parser = argparse.ArgumentParser(
        description="Evaluate a policy JSON against input text from STDIN and print JSON result."
    )
    parser.add_argument(
        "policy_path",
        help="Path to the policy JSON file.",
    )
    return parser.parse_args()


def _load_policy(path: str) -> PolicyDoc:
    """
    Load and validate a PolicyDoc from a JSON file.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Works for both Pydantic v1 and v2
    return PolicyDoc(**data)


def _read_stdin() -> str:
    """
    Read all input from STDIN as a string.
    """
    return sys.stdin.read()


def main() -> int:
    """
    Main entrypoint for the CLI.

    Returns:
        Process exit code (0 for success, non-zero for error).
    """
    args = _parse_args()
    try:
        policy = _load_policy(args.policy_path)
        input_text = _read_stdin()

        # Evidence types are not provided via CLI in this version; use empty set
        allowed, reasons = evaluate_policy(policy, input_text=input_text, evidence_types=set())

        result = {"allowed": bool(allowed), "reasons": list(reasons)}
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())