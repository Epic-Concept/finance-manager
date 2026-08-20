"""Ensure pockets exist for ingested account names."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from finance_api.models.ledger import Pocket
from finance_api.models.transaction import Transaction

TRANSFERS_ACCOUNT = "__transfers__"
UNSPECIFIED_ACCOUNT = "__unspecified__"


def get_or_create_pocket(
    session: Session, account_name: str | None, *, kind: str = "asset"
) -> Pocket:
    key = account_name or UNSPECIFIED_ACCOUNT
    existing = session.scalars(select(Pocket).where(Pocket.account_name == key)).first()
    if existing is not None:
        return existing
    pocket = Pocket(
        name=account_name or "Unspecified",
        account_name=key,
        kind=kind,
    )
    session.add(pocket)
    session.flush()
    return pocket


def transfers_pocket(session: Session) -> Pocket:
    existing = session.scalars(
        select(Pocket).where(Pocket.account_name == TRANSFERS_ACCOUNT)
    ).first()
    if existing is not None:
        return existing
    pocket = Pocket(name="Transfers", account_name=TRANSFERS_ACCOUNT, kind="asset")
    session.add(pocket)
    session.flush()
    return pocket


def ensure_pockets_from_transactions(session: Session) -> int:
    """Create a pocket for each distinct transaction.account_name. Returns created count."""
    names = {
        (row[0] or UNSPECIFIED_ACCOUNT)
        for row in session.execute(select(Transaction.account_name)).all()
    }
    created = 0
    for name in names:
        display = None if name == UNSPECIFIED_ACCOUNT else name
        before = session.scalars(
            select(Pocket).where(Pocket.account_name == name)
        ).first()
        get_or_create_pocket(session, display)
        after = session.scalars(
            select(Pocket).where(Pocket.account_name == name)
        ).first()
        if before is None and after is not None:
            created += 1
    transfers_pocket(session)
    return created
