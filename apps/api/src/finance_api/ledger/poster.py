"""Post classification decisions as balanced journal entries."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from finance_api.classification.cel.activation import amount_to_minor
from finance_api.ledger.pockets import get_or_create_pocket, transfers_pocket
from finance_api.models.category import Category
from finance_api.models.classification_decision import ClassificationDecision
from finance_api.models.ledger import JournalEntry, Posting
from finance_api.models.transaction import Transaction

TRANSFER_NAME = "Internal Transfer"


def _is_transfer_nominal(session: Session, category_id: int) -> bool:
    category = session.get(Category, category_id)
    while category is not None:
        if category.name == TRANSFER_NAME:
            return True
        category = (
            session.get(Category, category.parent_id) if category.parent_id else None
        )
    return False


def _active_entries(session: Session, transaction_id: int) -> list[JournalEntry]:
    reversed_ids = set(
        session.scalars(
            select(JournalEntry.reversed_entry_id).where(
                JournalEntry.transaction_id == transaction_id,
                JournalEntry.reversed_entry_id.is_not(None),
            )
        )
    )
    entries = list(
        session.scalars(
            select(JournalEntry).where(JournalEntry.transaction_id == transaction_id)
        )
    )
    return [e for e in entries if e.id not in reversed_ids and e.kind != "reversal"]


def reverse_entry(session: Session, entry: JournalEntry) -> JournalEntry:
    reversal = JournalEntry(
        transaction_id=entry.transaction_id,
        decision_id=entry.decision_id,
        kind="reversal",
        reversed_entry_id=entry.id,
    )
    session.add(reversal)
    session.flush()
    for posting in entry.postings:
        session.add(
            Posting(
                entry_id=reversal.id,
                pocket_id=posting.pocket_id,
                category_id=posting.category_id,
                amount_minor=-posting.amount_minor,
            )
        )
    session.flush()
    return reversal


def post_decision(
    session: Session, txn: Transaction, decision: ClassificationDecision
) -> JournalEntry:
    """Write a balanced entry for an applied decision, reversing any prior posting."""
    for prior in _active_entries(session, txn.id):
        reverse_entry(session, prior)

    splits = list(decision.splits)
    if not splits:
        raise ValueError("cannot post a decision with no splits")

    pocket = get_or_create_pocket(session, txn.account_name)
    total_minor = amount_to_minor(txn.amount)
    transfer = all(_is_transfer_nominal(session, s.category_id) for s in splits)

    if transfer:
        kind = "transfer"
        clearing = transfers_pocket(session)
        # Money leaving the source pocket lands in Transfers until the other leg posts.
        pocket_delta = total_minor  # debit amount is typically negative
        postings = [
            Posting(pocket_id=pocket.id, category_id=None, amount_minor=pocket_delta),
            Posting(
                pocket_id=clearing.id, category_id=None, amount_minor=-pocket_delta
            ),
        ]
    elif len(splits) == 1:
        kind = "income" if total_minor > 0 else "spend"
        nominal_delta = -total_minor  # expense debit is positive when cash went out
        postings = [
            Posting(
                pocket_id=None,
                category_id=splits[0].category_id,
                amount_minor=nominal_delta,
            ),
            Posting(pocket_id=pocket.id, category_id=None, amount_minor=total_minor),
        ]
    else:
        kind = "split"
        sign = 1 if total_minor < 0 else -1
        postings = [
            Posting(pocket_id=pocket.id, category_id=None, amount_minor=total_minor)
        ]
        for split in splits:
            postings.append(
                Posting(
                    pocket_id=None,
                    category_id=split.category_id,
                    amount_minor=sign * abs(amount_to_minor(split.amount)),
                )
            )

    if sum(p.amount_minor for p in postings) != 0:
        raise ValueError("journal postings do not sum to zero")

    entry = JournalEntry(
        transaction_id=txn.id,
        decision_id=decision.id,
        kind=kind,
    )
    session.add(entry)
    session.flush()
    for posting in postings:
        posting.entry_id = entry.id
        session.add(posting)
    session.flush()
    return entry


def reprocess_postings(session: Session) -> int:
    """Rebuild postings from auto-applied or confirmed decisions. Idempotent."""
    stmt = select(ClassificationDecision).where(
        ClassificationDecision.outcome == "auto_apply"
    )
    count = 0
    for decision in session.scalars(stmt):
        txn = session.get(Transaction, decision.transaction_id)
        if txn is None or not decision.splits:
            continue
        post_decision(session, txn, decision)
        count += 1
    return count
