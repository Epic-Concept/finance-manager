"""AIDisambiguationService for AI-powered transaction classification."""

from dataclasses import dataclass
from decimal import Decimal

from finance_api.models.category_evidence import CategoryEvidence
from finance_api.models.transaction import Transaction
from finance_api.repositories.category_evidence_repository import (
    CategoryEvidenceRepository,
)
from finance_api.services.category_mapping_service import (
    CategoryMappingService,
    MappingResult,
)
from finance_api.services.email_search_service import EmailMessage, EmailSearchService
from finance_api.services.receipt_extraction_service import (
    ExtractedReceipt,
    ReceiptExtractionError,
    ReceiptExtractionService,
)


@dataclass
class DisambiguationResult:
    """Result of AI disambiguation for a transaction."""

    transaction_id: int
    success: bool
    dominant_category_id: int | None
    evidence_records: list[CategoryEvidence]
    confidence_score: Decimal
    error_message: str | None = None


class DisambiguationError(Exception):
    """Raised when disambiguation fails."""

    pass


class AIDisambiguationService:
    """Service for disambiguating transactions using email receipts and AI.

    Orchestrates:
    1. Email search for receipt/order confirmation emails
    2. Receipt extraction using LLM
    3. Category mapping
    4. Evidence storage

    Configuration via __init__ parameters:
    - confidence_threshold: Minimum confidence for auto-acceptance (default 0.9)
    - total_tolerance: Allowed variance between receipt and transaction (default 0.05 = 5%)
    - model: Claude model to use for extraction
    """

    def __init__(
        self,
        email_search_service: EmailSearchService,
        receipt_extraction_service: ReceiptExtractionService,
        category_mapping_service: CategoryMappingService,
        evidence_repository: CategoryEvidenceRepository,
        confidence_threshold: Decimal = Decimal("0.9"),
        total_tolerance: Decimal = Decimal("0.05"),
    ) -> None:
        """Initialize the service.

        Args:
            email_search_service: Service for searching emails.
            receipt_extraction_service: Service for extracting receipt data.
            category_mapping_service: Service for mapping items to categories.
            evidence_repository: Repository for storing evidence.
            confidence_threshold: Minimum confidence for auto-acceptance.
            total_tolerance: Allowed variance between receipt and transaction total.
        """
        self._email_service = email_search_service
        self._extraction_service = receipt_extraction_service
        self._mapping_service = category_mapping_service
        self._evidence_repo = evidence_repository
        self._confidence_threshold = confidence_threshold
        self._total_tolerance = total_tolerance

    def _select_best_email(
        self, emails: list[EmailMessage], transaction: Transaction
    ) -> EmailMessage | None:
        """Select the most relevant email for a transaction.

        Args:
            emails: List of candidate emails.
            transaction: The transaction to match.

        Returns:
            Best matching email or None.
        """
        if not emails:
            return None

        # Simple heuristic: prefer emails closest to transaction date
        if len(emails) == 1:
            return emails[0]

        txn_date = transaction.transaction_date

        def date_distance(email: EmailMessage) -> int:
            if email.date:
                delta_days = (email.date.date() - txn_date).days
                return abs(int(delta_days))
            return 999

        sorted_emails = sorted(emails, key=date_distance)
        return sorted_emails[0]

    def _store_evidence(
        self,
        transaction: Transaction,
        receipt: ExtractedReceipt,
        mapping_result: MappingResult,
        email: EmailMessage,
        model_used: str,
    ) -> list[CategoryEvidence]:
        """Store evidence records for mapped items.

        Args:
            transaction: The transaction.
            receipt: Extracted receipt data.
            mapping_result: Category mapping result.
            email: Source email message.
            model_used: LLM model identifier.

        Returns:
            List of created CategoryEvidence records.
        """
        evidence_records: list[CategoryEvidence] = []

        for mapped_item in mapping_result.mapped_items:
            evidence = self._evidence_repo.create(
                transaction_id=transaction.id,
                item_description=mapped_item.item.name,
                item_price=mapped_item.item.price,
                item_quantity=mapped_item.item.quantity,
                item_currency=receipt.currency,
                category_id=mapped_item.category_id,
                evidence_type="email",
                email_account_id=email.email_account_id,
                email_message_id=email.message_id,
                email_datetime=email.date,
                evidence_summary=(
                    f"Extracted from {receipt.merchant} order email dated "
                    f"{receipt.order_date}"
                ),
                confidence_score=receipt.confidence_score,
                model_used=model_used,
                raw_extraction=receipt.raw_response,
            )
            evidence_records.append(evidence)

        # Store shipping as separate evidence if present (including free shipping)
        if receipt.shipping_cost is not None:
            # Try to use the dominant category for shipping
            shipping_category_id = mapping_result.dominant_category_id
            if shipping_category_id:
                evidence = self._evidence_repo.create(
                    transaction_id=transaction.id,
                    item_description="Shipping",
                    item_price=receipt.shipping_cost,
                    item_quantity=1,
                    item_currency=receipt.currency,
                    category_id=shipping_category_id,
                    evidence_type="email",
                    email_account_id=email.email_account_id,
                    email_message_id=email.message_id,
                    email_datetime=email.date,
                    evidence_summary=f"Shipping cost from {receipt.merchant}",
                    confidence_score=receipt.confidence_score,
                    model_used=model_used,
                    raw_extraction=None,  # Don't duplicate raw response
                )
                evidence_records.append(evidence)

        return evidence_records

    def disambiguate(self, transaction: Transaction) -> DisambiguationResult:
        """Disambiguate a transaction using email receipts.

        Steps:
        1. Search for receipt emails
        2. Extract order details using LLM
        3. Map items to categories
        4. Validate totals
        5. Store evidence

        Args:
            transaction: The transaction to disambiguate.

        Returns:
            DisambiguationResult with outcome and evidence.
        """
        # Step 1: Search for emails
        try:
            emails = self._email_service.search_for_transaction(transaction)
        except ValueError as e:
            return DisambiguationResult(
                transaction_id=transaction.id,
                success=False,
                dominant_category_id=None,
                evidence_records=[],
                confidence_score=Decimal("0"),
                error_message=f"Email search configuration error: {e}",
            )
        except Exception as e:
            return DisambiguationResult(
                transaction_id=transaction.id,
                success=False,
                dominant_category_id=None,
                evidence_records=[],
                confidence_score=Decimal("0"),
                error_message=f"Email search failed: {e}",
            )

        if not emails:
            return DisambiguationResult(
                transaction_id=transaction.id,
                success=False,
                dominant_category_id=None,
                evidence_records=[],
                confidence_score=Decimal("0"),
                error_message="No matching emails found",
            )

        # Step 2: Select best email and extract receipt
        email = self._select_best_email(emails, transaction)
        if email is None:
            return DisambiguationResult(
                transaction_id=transaction.id,
                success=False,
                dominant_category_id=None,
                evidence_records=[],
                confidence_score=Decimal("0"),
                error_message="No suitable email found",
            )

        try:
            receipt = self._extraction_service.extract(email)
        except ReceiptExtractionError as e:
            return DisambiguationResult(
                transaction_id=transaction.id,
                success=False,
                dominant_category_id=None,
                evidence_records=[],
                confidence_score=Decimal("0"),
                error_message=f"Receipt extraction failed: {e}",
            )

        # Step 3: Map items to categories
        mapping_result = self._mapping_service.map_receipt(receipt)

        if not mapping_result.mapped_items:
            return DisambiguationResult(
                transaction_id=transaction.id,
                success=False,
                dominant_category_id=None,
                evidence_records=[],
                confidence_score=receipt.confidence_score,
                error_message="No items could be mapped to categories",
            )

        # Step 4: Validate totals
        is_valid_total, diff_ratio = self._mapping_service.validate_total(
            receipt, transaction.amount, self._total_tolerance
        )

        # Adjust confidence based on total validation
        final_confidence = receipt.confidence_score
        if not is_valid_total:
            # Reduce confidence if totals don't match
            final_confidence = min(
                final_confidence, Decimal("0.7") - (diff_ratio * Decimal("0.2"))
            )
            final_confidence = max(final_confidence, Decimal("0"))

        # Step 5: Store evidence
        model_used = self._extraction_service._model  # Access model name
        evidence_records = self._store_evidence(
            transaction, receipt, mapping_result, email, model_used
        )

        # Determine success based on confidence threshold
        success = final_confidence >= self._confidence_threshold

        return DisambiguationResult(
            transaction_id=transaction.id,
            success=success,
            dominant_category_id=mapping_result.dominant_category_id,
            evidence_records=evidence_records,
            confidence_score=final_confidence,
            error_message=None if success else "Confidence below threshold",
        )

    def disambiguate_batch(
        self, transactions: list[Transaction]
    ) -> dict[int, DisambiguationResult]:
        """Disambiguate multiple transactions.

        Args:
            transactions: List of transactions.

        Returns:
            Dictionary mapping transaction ID to result.
        """
        results: dict[int, DisambiguationResult] = {}
        for transaction in transactions:
            results[transaction.id] = self.disambiguate(transaction)
        return results
