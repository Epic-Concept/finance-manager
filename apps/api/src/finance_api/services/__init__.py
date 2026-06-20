"""Business logic services.

The legacy classification stack (rule-engine RulesClassificationService,
ClassificationOrchestrator, AIDisambiguationService, and the redundant LLM
rule-creation surfaces) has been removed in favour of the evidence-driven
engine in ``finance_api.classification``. The conversational refinement tool
(clustering + validation + interactive refinement) is retained for the
review/learning loop.
"""

from finance_api.services.interactive_refinement_service import (
    InteractiveRefinementError,
    InteractiveRefinementService,
    ProposedRule,
    RefinementResponse,
)
from finance_api.services.rule_validation_service import (
    ConflictResult,
    RuleValidationService,
    ValidationResult,
)
from finance_api.services.transaction_clustering_service import (
    ClusterStatistics,
    TransactionCluster,
    TransactionClusteringService,
)

__all__ = [
    "ConflictResult",
    "RuleValidationService",
    "ValidationResult",
    "ClusterStatistics",
    "TransactionCluster",
    "TransactionClusteringService",
    "InteractiveRefinementError",
    "InteractiveRefinementService",
    "ProposedRule",
    "RefinementResponse",
]
