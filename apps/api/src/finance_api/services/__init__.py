"""Business logic services."""

from finance_api.services.ai_disambiguation_service import (
    AIDisambiguationService,
    DisambiguationError,
    DisambiguationResult,
)
from finance_api.services.category_mapping_service import (
    CategoryMappingService,
    MappedItem,
    MappingResult,
)
from finance_api.services.classification_orchestrator import (
    ClassificationOrchestrator,
    ClassificationResult,
)
from finance_api.services.email_search_service import (
    EmailClientInterface,
    EmailMessage,
    EmailSearchQuery,
    EmailSearchService,
)
from finance_api.services.receipt_extraction_service import (
    ExtractedItem,
    ExtractedReceipt,
    ReceiptExtractionError,
    ReceiptExtractionService,
)
from finance_api.services.rules_classification_service import (
    RuleMatch,
    RulesClassificationService,
)

__all__ = [
    # AI Disambiguation
    "AIDisambiguationService",
    "DisambiguationError",
    "DisambiguationResult",
    # Category Mapping
    "CategoryMappingService",
    "MappedItem",
    "MappingResult",
    # Classification Orchestrator
    "ClassificationOrchestrator",
    "ClassificationResult",
    # Email Search
    "EmailClientInterface",
    "EmailMessage",
    "EmailSearchQuery",
    "EmailSearchService",
    # Receipt Extraction
    "ExtractedItem",
    "ExtractedReceipt",
    "ReceiptExtractionError",
    "ReceiptExtractionService",
    # Rules Classification
    "RuleMatch",
    "RulesClassificationService",
]
