"""CLI entrypoint: scheduled learner promotion (off the classification hot path).

Promotes stable, human-confirmed merchants to active rules so future
transactions are auto-applied by the rules fast-path. Run on a schedule after
the classify step.

    python -m finance_api.scripts.run_learner
"""

from __future__ import annotations

import sys

from finance_api.classification.review import run_learner_promotion
from finance_api.db.session import SessionLocal


def main() -> int:
    session = SessionLocal()
    try:
        created = run_learner_promotion(session)
        session.commit()
        print(f"learner ok: promoted {created} new rule(s)")
        return 0
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        session.rollback()
        print(f"learner failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
