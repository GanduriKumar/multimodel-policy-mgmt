from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from app.core.config import get_settings
from app.services.governance_ledger import GovernanceLedger


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Verify GovernanceLedger chain integrity")
    parser.add_argument(
        "--ledger-path",
        dest="ledger_path",
        type=str,
        default=None,
        help="Path to the governance ledger JSONL file (defaults to settings)",
    )
    args = parser.parse_args(argv)

    try:
        settings = get_settings()
        path = args.ledger_path or getattr(settings, "governance_ledger_path", None) or None
        ledger = GovernanceLedger(path)
        ok = ledger.verify_chain()
        if ok:
            print(json.dumps({"ok": True}))
            return 0
        else:
            print(json.dumps({"ok": False, "error": "verification_failed"}))
            return 2
    except SystemExit:
        raise
    except Exception as e:
        # Avoid leaking secrets; only print class name and string message
        msg = str(e) if str(e) else e.__class__.__name__
        print(json.dumps({"ok": False, "error": msg}))
        return 3


if __name__ == "__main__":
    sys.exit(main())
