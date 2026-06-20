"""CLI entrypoint: classify newly-synced transactions.

Run nightly after the sync step:

    python -m finance_api.scripts.classify_transactions
"""

from __future__ import annotations

import sys

from finance_api.classification.daily import run_daily_classification
from finance_api.classification.factory import build_engine
from finance_api.db.session import SessionLocal


def main() -> int:
    session = SessionLocal()
    try:
        engine = build_engine(session)
        result = run_daily_classification(session, engine)
        print(
            f"classify ok: classified={result.classified} "
            f"auto_applied={result.auto_applied} review={result.review}"
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        session.rollback()
        print(f"classify failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
