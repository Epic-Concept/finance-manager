"""CLI entrypoint: classify newly-synced transactions.

Run nightly after the sync step:

    python -m finance_api.scripts.classify_transactions
"""

from __future__ import annotations

import argparse
import sys

from finance_api.classification.cold_start import ColdStartBlocked
from finance_api.classification.daily import (
    discover_review_cohorts,
    run_daily_classification,
)
from finance_api.classification.factory import build_engine
from finance_api.db.session import SessionLocal


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify undecided transactions.")
    parser.add_argument(
        "--limit", type=int, default=None, help="max transactions to classify this run"
    )
    args = parser.parse_args()

    session = SessionLocal()
    try:
        engine = build_engine(session)
        result = run_daily_classification(session, engine, limit=args.limit)
        cohorts = discover_review_cohorts(session)
        print(
            f"classify ok: classified={result.classified} "
            f"auto_applied={result.auto_applied} review={result.review} "
            f"cohorts={cohorts}"
        )
        return 0
    except ColdStartBlocked as exc:
        session.rollback()
        print(
            f"classify blocked (offer cohort bootstrap first): {exc}", file=sys.stderr
        )
        return 2
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        session.rollback()
        print(f"classify failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
