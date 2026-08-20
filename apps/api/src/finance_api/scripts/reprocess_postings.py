"""Rebuild ledger postings from applied classification decisions.

python -m finance_api.scripts.reprocess_postings
"""

from __future__ import annotations

import sys

from finance_api.db.session import SessionLocal
from finance_api.ledger.poster import reprocess_postings


def main() -> int:
    session = SessionLocal()
    try:
        count = reprocess_postings(session)
        session.commit()
        print(f"Reprocessed {count} decisions into journal entries.")
        return 0
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        print(f"reprocess failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
