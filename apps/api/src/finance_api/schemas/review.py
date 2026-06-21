"""Pydantic schemas for the review queue API."""

from __future__ import annotations

from pydantic import BaseModel


class EvidenceResponse(BaseModel):
    evidence_type: str
    source: str
    strength: int


class ReviewItemResponse(BaseModel):
    decision_id: int
    transaction_id: int
    description: str
    amount: str
    proposed_category_id: int | None
    strength: int
    reason: str
    evidence: list[EvidenceResponse]


class ReviewListResponse(BaseModel):
    items: list[ReviewItemResponse]


class ResolveRequest(BaseModel):
    category_id: int


class ResolveResponse(BaseModel):
    decision_id: int
    confirmed: bool
    category_id: int
