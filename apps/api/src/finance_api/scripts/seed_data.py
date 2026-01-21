"""Seed data script for populating the local database with Parquet data."""

import argparse
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from finance_api.db.session import SessionLocal
from finance_api.models.online_purchase import OnlinePurchase
from finance_api.models.transaction import Transaction


def load_bank_transactions(parquet_path: Path, clear: bool = False) -> int:
    """Load bank transactions from Parquet into the transactions table.

    Args:
        parquet_path: Path to the bank_transactions.parquet file.
        clear: If True, delete existing records before loading.

    Returns:
        Number of records inserted.
    """
    db = SessionLocal()
    try:
        if clear:
            db.execute(text("DELETE FROM finance.transactions"))
            db.commit()
            print("Cleared existing transactions")

        df = pd.read_parquet(parquet_path)

        inserted = 0
        skipped = 0

        for _, row in df.iterrows():
            external_id = str(row["transaction_id"])

            # Check for existing record by external_id
            existing = (
                db.query(Transaction)
                .filter(Transaction.external_id == external_id)
                .first()
            )
            if existing:
                skipped += 1
                continue

            # Parse transaction date
            txn_date = row["transaction_date"]
            if isinstance(txn_date, pd.Timestamp):
                txn_date = txn_date.date()
            elif isinstance(txn_date, datetime):
                txn_date = txn_date.date()
            elif isinstance(txn_date, str):
                txn_date = datetime.strptime(txn_date.split(" ")[0], "%Y-%m-%d").date()

            # Get description
            description = row.get("description") or row.get("merchant_name") or "Unknown"
            if pd.isna(description) or not description:
                description = "Unknown"

            # Get amount
            amount = Decimal(str(row["amount"]))

            transaction = Transaction(
                transaction_date=txn_date,
                description=str(description),
                amount=amount,
                currency=str(row["currency"]),
                external_id=external_id,
                account_name=str(row["account_name"]) if pd.notna(row["account_name"]) else None,
                notes=None,
            )
            db.add(transaction)
            inserted += 1

        db.commit()
        print(f"Transactions: inserted {inserted}, skipped {skipped} duplicates")
        return inserted

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def load_purchases(parquet_path: Path, clear: bool = False) -> int:
    """Load purchases from Parquet into the online_purchases table.

    Args:
        parquet_path: Path to the purchases.parquet file.
        clear: If True, delete existing records before loading.

    Returns:
        Number of records inserted.
    """
    db = SessionLocal()
    try:
        if clear:
            db.execute(text("DELETE FROM finance.online_purchases"))
            db.commit()
            print("Cleared existing online purchases")

        df = pd.read_parquet(parquet_path)

        inserted = 0
        skipped = 0

        for _, row in df.iterrows():
            item_name = str(row["item_name"])
            shop_name = str(row["store_name"])

            # Parse purchase datetime
            purchase_dt = row["purchase_date"]
            if isinstance(purchase_dt, pd.Timestamp):
                purchase_dt = purchase_dt.to_pydatetime()
            elif isinstance(purchase_dt, str):
                if "." in purchase_dt:
                    purchase_dt = purchase_dt.split(".")[0]
                purchase_dt = datetime.strptime(purchase_dt, "%Y-%m-%d %H:%M:%S")

            # Check for existing record
            existing = (
                db.query(OnlinePurchase)
                .filter(OnlinePurchase.items == item_name)
                .filter(OnlinePurchase.shop_name == shop_name)
                .filter(OnlinePurchase.purchase_datetime == purchase_dt)
                .first()
            )
            if existing:
                skipped += 1
                continue

            purchase = OnlinePurchase(
                shop_name=shop_name,
                items=item_name,
                purchase_datetime=purchase_dt,
                price=Decimal(str(row["price"])),
                currency="PLN",  # Default currency for purchases
                is_deferred_payment=bool(row["credited"]) if pd.notna(row["credited"]) else False,
                transaction_id=None,
            )
            db.add(purchase)
            inserted += 1

        db.commit()
        print(f"Purchases: inserted {inserted}, skipped {skipped} duplicates")
        return inserted

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def main() -> int:
    """CLI entrypoint for seed data script."""
    parser = argparse.ArgumentParser(
        description="Seed the local database with data from Parquet files."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing Parquet files (default: data/)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing data before seeding",
    )
    parser.add_argument(
        "--transactions-only",
        action="store_true",
        help="Only load bank transactions",
    )
    parser.add_argument(
        "--purchases-only",
        action="store_true",
        help="Only load purchases",
    )

    args = parser.parse_args()

    data_dir = args.data_dir
    if not data_dir.exists():
        print(f"Error: Data directory '{data_dir}' does not exist")
        return 1

    # Determine what to load
    load_txns = not args.purchases_only
    load_purch = not args.transactions_only

    total_inserted = 0

    if load_txns:
        txn_file = data_dir / "bank_transactions.parquet"
        if txn_file.exists():
            total_inserted += load_bank_transactions(txn_file, clear=args.clear)
        else:
            print(f"Warning: {txn_file} not found, skipping transactions")

    if load_purch:
        purch_file = data_dir / "purchases.parquet"
        if purch_file.exists():
            total_inserted += load_purchases(purch_file, clear=args.clear)
        else:
            print(f"Warning: {purch_file} not found, skipping purchases")

    print(f"\nTotal records inserted: {total_inserted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
