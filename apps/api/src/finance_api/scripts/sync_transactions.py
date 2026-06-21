"""CLI entrypoint: incremental transaction sync from Azure SQL into gb10.

Run nightly (cron / systemd timer) after the upstream evening refresh:

    python -m finance_api.scripts.sync_transactions
"""

from __future__ import annotations

import sys

from finance_api.db.session import SessionLocal
from finance_api.ingestion.azure_sql_source import AzureSqlSource
from finance_api.ingestion.service import TransactionSyncService


def main() -> int:
    session = SessionLocal()
    try:
        service = TransactionSyncService(session)
        before = service.get_cursor()
        result = service.sync(AzureSqlSource())
        print(
            f"sync ok: imported={result.imported} updated={result.updated} "
            f"cursor {before} -> {result.cursor}"
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print(f"sync failed (cursor unchanged): {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
