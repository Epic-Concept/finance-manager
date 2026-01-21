"""Repository layer for data access patterns."""

from finance_api.repositories.category_evidence_repository import (
    CategoryEvidenceNotFoundError,
    CategoryEvidenceRepository,
)
from finance_api.repositories.category_repository import (
    CategoryHasChildrenError,
    CategoryNotFoundError,
    CategoryRepository,
)
from finance_api.repositories.classification_rule_repository import (
    ClassificationRuleNotFoundError,
    ClassificationRuleRepository,
)
from finance_api.repositories.email_account_repository import (
    EmailAccountNotFoundError,
    EmailAccountRepository,
)

__all__ = [
    "CategoryEvidenceNotFoundError",
    "CategoryEvidenceRepository",
    "CategoryHasChildrenError",
    "CategoryNotFoundError",
    "CategoryRepository",
    "ClassificationRuleNotFoundError",
    "ClassificationRuleRepository",
    "EmailAccountNotFoundError",
    "EmailAccountRepository",
]
