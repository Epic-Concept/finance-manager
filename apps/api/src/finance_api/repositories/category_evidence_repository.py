"""CategoryEvidenceRepository for managing classification evidence."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from finance_api.models.category_evidence import CategoryEvidence


class CategoryEvidenceNotFoundError(Exception):
    """Raised when category evidence is not found."""

    pass


class CategoryEvidenceRepository:
    """Repository for category evidence CRUD operations."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy database session.
        """
        self._session = session

    def create(
        self,
        transaction_id: int,
        item_description: str,
        item_price: Decimal,
        category_id: int,
        evidence_type: str,
        item_currency: str = "GBP",
        item_quantity: int = 1,
        email_account_id: int | None = None,
        email_message_id: str | None = None,
        email_datetime: datetime | None = None,
        evidence_summary: str | None = None,
        confidence_score: Decimal | None = None,
        model_used: str | None = None,
        raw_extraction: str | None = None,
    ) -> CategoryEvidence:
        """Create a new category evidence record.

        Args:
            transaction_id: The transaction ID.
            item_description: Description of the item.
            item_price: Price of the item.
            category_id: The assigned category ID.
            evidence_type: Type of evidence (email, manual, rule, ai_inferred).
            item_currency: Currency code (default GBP).
            item_quantity: Quantity of items (default 1).
            email_account_id: Source email account ID.
            email_message_id: Email Message-ID header.
            email_datetime: When the email was sent.
            evidence_summary: Human-readable summary.
            confidence_score: AI confidence (0-1).
            model_used: LLM model identifier.
            raw_extraction: Full LLM JSON output.

        Returns:
            The created CategoryEvidence.
        """
        evidence = CategoryEvidence(
            transaction_id=transaction_id,
            item_description=item_description,
            item_price=item_price,
            item_currency=item_currency,
            item_quantity=item_quantity,
            category_id=category_id,
            evidence_type=evidence_type,
            email_account_id=email_account_id,
            email_message_id=email_message_id,
            email_datetime=email_datetime,
            evidence_summary=evidence_summary,
            confidence_score=confidence_score,
            model_used=model_used,
            raw_extraction=raw_extraction,
        )
        self._session.add(evidence)
        self._session.flush()
        return evidence

    def create_batch(self, evidence_list: list[dict]) -> list[CategoryEvidence]:
        """Create multiple category evidence records.

        Args:
            evidence_list: List of dictionaries with evidence data.

        Returns:
            List of created CategoryEvidence records.
        """
        created = []
        for evidence_data in evidence_list:
            evidence = self.create(**evidence_data)
            created.append(evidence)
        return created

    def get(self, evidence_id: int) -> CategoryEvidence:
        """Get a category evidence record by ID.

        Args:
            evidence_id: The evidence ID.

        Returns:
            The CategoryEvidence.

        Raises:
            CategoryEvidenceNotFoundError: If evidence doesn't exist.
        """
        evidence = self._session.get(CategoryEvidence, evidence_id)
        if evidence is None:
            raise CategoryEvidenceNotFoundError(
                f"Category evidence {evidence_id} not found"
            )
        return evidence

    def get_by_transaction(self, transaction_id: int) -> list[CategoryEvidence]:
        """Get all evidence records for a transaction.

        Args:
            transaction_id: The transaction ID.

        Returns:
            List of CategoryEvidence records for the transaction.
        """
        stmt = (
            select(CategoryEvidence)
            .where(CategoryEvidence.transaction_id == transaction_id)
            .order_by(CategoryEvidence.id)
        )
        return list(self._session.execute(stmt).scalars().all())

    def get_by_email_message(
        self, email_account_id: int, email_message_id: str
    ) -> list[CategoryEvidence]:
        """Get all evidence records from a specific email.

        Args:
            email_account_id: The email account ID.
            email_message_id: The email Message-ID header.

        Returns:
            List of CategoryEvidence records from the email.
        """
        stmt = (
            select(CategoryEvidence)
            .where(CategoryEvidence.email_account_id == email_account_id)
            .where(CategoryEvidence.email_message_id == email_message_id)
        )
        return list(self._session.execute(stmt).scalars().all())

    def get_transaction_total(self, transaction_id: int) -> Decimal:
        """Calculate the total of all evidence items for a transaction.

        Args:
            transaction_id: The transaction ID.

        Returns:
            Sum of (item_price * item_quantity) for all items.
        """
        stmt = select(
            func.coalesce(
                func.sum(CategoryEvidence.item_price * CategoryEvidence.item_quantity),
                0,
            )
        ).where(CategoryEvidence.transaction_id == transaction_id)

        result = self._session.execute(stmt).scalar_one()
        return Decimal(result) if result is not None else Decimal("0")

    def get_dominant_category(self, transaction_id: int) -> int | None:
        """Get the category with the highest total value for a transaction.

        Args:
            transaction_id: The transaction ID.

        Returns:
            Category ID of the dominant category, or None if no evidence.
        """
        # Find category with highest total (price * quantity)
        stmt = (
            select(
                CategoryEvidence.category_id,
                func.sum(
                    CategoryEvidence.item_price * CategoryEvidence.item_quantity
                ).label("total"),
            )
            .where(CategoryEvidence.transaction_id == transaction_id)
            .group_by(CategoryEvidence.category_id)
            .order_by(
                func.sum(
                    CategoryEvidence.item_price * CategoryEvidence.item_quantity
                ).desc()
            )
            .limit(1)
        )

        result = self._session.execute(stmt).first()
        return result[0] if result else None

    def delete_by_transaction(self, transaction_id: int) -> int:
        """Delete all evidence records for a transaction.

        Args:
            transaction_id: The transaction ID.

        Returns:
            Number of records deleted.
        """
        evidence_records = self.get_by_transaction(transaction_id)
        count = len(evidence_records)
        for evidence in evidence_records:
            self._session.delete(evidence)
        return count

    def delete(self, evidence_id: int) -> None:
        """Delete a category evidence record.

        Args:
            evidence_id: The evidence ID.

        Raises:
            CategoryEvidenceNotFoundError: If evidence doesn't exist.
        """
        evidence = self.get(evidence_id)
        self._session.delete(evidence)
