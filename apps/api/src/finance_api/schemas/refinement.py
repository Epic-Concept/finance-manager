"""Pydantic schemas for interactive refinement API."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# --- Session Schemas ---


class SessionCreate(BaseModel):
    """Request to create a new refinement session."""

    cluster_hash: str = Field(..., description="Hash identifying the transaction cluster")


class SessionResponse(BaseModel):
    """Response with session details."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    cluster_hash: str
    cluster_key: str
    cluster_size: int
    sample_descriptions: list[str]
    status: str
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    message_count: int = 0
    proposal_count: int = 0


class SessionListResponse(BaseModel):
    """Response with list of sessions."""

    sessions: list[SessionResponse]
    total: int


# --- Message Schemas ---


class MessageCreate(BaseModel):
    """Request to send a message in a session."""

    content: str = Field(..., min_length=1, description="User message content")


class ProposedRuleResponse(BaseModel):
    """A rule proposed by the LLM."""

    pattern: str
    category_id: int
    category_name: str
    confidence: str
    reasoning: str


class MessageResponse(BaseModel):
    """Response with message details."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    proposed_rules: list[ProposedRuleResponse] | None = None
    created_at: datetime


class ConversationResponse(BaseModel):
    """Response with full conversation history."""

    session_id: int
    messages: list[MessageResponse]


# --- Proposal Schemas ---


class ValidationResultResponse(BaseModel):
    """Validation results for a proposed rule."""

    total_matches: int
    true_positives: int
    false_positives: int
    precision: Decimal
    coverage: Decimal
    sample_true_positives: list[str]
    sample_false_positives: list[str]
    is_valid_regex: bool
    regex_error: str | None = None


class ProposalResponse(BaseModel):
    """Response with proposal details."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    proposed_pattern: str
    proposed_category_id: int
    proposed_category_name: str
    llm_confidence: str
    llm_reasoning: str
    validation: ValidationResultResponse | None = None
    status: str
    created_at: datetime
    reviewed_at: datetime | None = None


class ProposalActionRequest(BaseModel):
    """Request for proposal accept/reject actions."""

    notes: str | None = Field(None, description="Optional notes for the action")


# --- Cluster Schemas ---


class ClusterResponse(BaseModel):
    """Response with cluster details."""

    cluster_hash: str
    cluster_key: str
    size: int
    sample_descriptions: list[str]
    has_active_session: bool = False
    active_session_id: int | None = None


class ClusterListResponse(BaseModel):
    """Response with list of clusters."""

    clusters: list[ClusterResponse]
    total: int
