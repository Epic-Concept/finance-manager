"""Live Azure SQL implementation of ``TransactionSource``.

Reads ``finance.bank_transactions`` read-only, authenticating with the
``finance-manager-gb10`` Entra service principal (client-credentials token, no
SQL password). Requires the Microsoft ODBC Driver 18 (``msodbcsql18``) and
``pyodbc`` to be available in the runtime image.
"""

from __future__ import annotations

import json
import struct
import time
import urllib.parse
import urllib.request
from collections.abc import Sequence
from datetime import datetime

from finance_api.core.config import settings
from finance_api.ingestion.source import SourceTransaction

_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
_SCOPE = "https://database.windows.net/.default"
_SQL_COPT_SS_ACCESS_TOKEN = 1256  # ODBC connection attribute for an AAD token


def _acquire_token() -> str:
    data = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": settings.azure_sql_client_id,
            "client_secret": settings.azure_sql_client_secret,
            "scope": _SCOPE,
        }
    ).encode()
    url = _TOKEN_URL.format(tenant=settings.azure_sql_tenant_id)
    with urllib.request.urlopen(
        urllib.request.Request(url, data=data), timeout=30
    ) as resp:
        return str(json.load(resp)["access_token"])


def _token_struct(token: str) -> bytes:
    tb = token.encode("utf-16-le")
    return struct.pack("=i", len(tb)) + tb


class AzureSqlSource:
    """Reads new transactions from the upstream Azure SQL database.

    The upstream is a serverless database that auto-pauses, so the first nightly
    connection typically times out while it resumes; ``connect_retries`` retries
    the connection (with ``resume_delay`` between attempts) to ride out the wake.
    """

    def __init__(
        self,
        connect_timeout: int = 60,
        connect_retries: int = 5,
        resume_delay: float = 20.0,
    ) -> None:
        self._connect_timeout = connect_timeout
        self._connect_retries = connect_retries
        self._resume_delay = resume_delay

    def _connect(self, conn_str: str, token: bytes):  # type: ignore[no-untyped-def]
        import pyodbc  # type: ignore[import-not-found]

        last_error: Exception | None = None
        for attempt in range(self._connect_retries):
            try:
                return pyodbc.connect(
                    conn_str, attrs_before={_SQL_COPT_SS_ACCESS_TOKEN: token}
                )
            except pyodbc.OperationalError as exc:  # serverless resume / transient
                last_error = exc
                if attempt < self._connect_retries - 1:
                    time.sleep(self._resume_delay)
        raise last_error if last_error else RuntimeError("connect failed")

    def fetch_since(self, cursor: datetime | None) -> Sequence[SourceTransaction]:
        # pyodbc is imported lazily inside _connect so the package imports without
        # the ODBC driver present (it only exists in the runtime image).
        conn_str = (
            "Driver={ODBC Driver 18 for SQL Server};"
            f"Server=tcp:{settings.azure_sql_server},1433;"
            f"Database={settings.azure_sql_database};"
            f"Encrypt=yes;TrustServerCertificate=no;Connection Timeout={self._connect_timeout}"
        )
        token = _token_struct(_acquire_token())
        table = f"[{settings.azure_sql_schema}].[{settings.azure_sql_table}]"
        with self._connect(conn_str, token) as conn:
            cur = conn.cursor()
            select = (
                "SELECT transaction_id, transaction_date, amount, currency, "
                "account_name, description, merchant_name, synced_at "
                f"FROM {table} "
            )
            if cursor is None:
                cur.execute(select + "ORDER BY synced_at ASC")
            else:
                cur.execute(
                    select + "WHERE synced_at > ? ORDER BY synced_at ASC", cursor
                )
            return [
                SourceTransaction(
                    transaction_id=row.transaction_id,
                    transaction_date=row.transaction_date,
                    amount=row.amount,
                    currency=row.currency,
                    account_name=row.account_name,
                    description=row.description,
                    merchant_name=row.merchant_name,
                    synced_at=row.synced_at,
                )
                for row in cur.fetchall()
            ]
