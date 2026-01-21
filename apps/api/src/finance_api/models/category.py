"""Category and CategoryClosure models for hierarchical category management."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finance_api.db.base import Base


class Category(Base):
    """Stores category definitions with parent reference for adjacency list."""

    __tablename__ = "categories"
    __table_args__ = {"schema": "finance"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("finance.categories.id"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    parent: Mapped["Category | None"] = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="children",
    )
    children: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="parent",
    )

    # Closure table relationships
    ancestor_entries: Mapped[list["CategoryClosure"]] = relationship(
        "CategoryClosure",
        foreign_keys="CategoryClosure.descendant_id",
        back_populates="descendant",
    )
    descendant_entries: Mapped[list["CategoryClosure"]] = relationship(
        "CategoryClosure",
        foreign_keys="CategoryClosure.ancestor_id",
        back_populates="ancestor",
    )

    # Classification relationships
    classification_rules: Mapped[list["ClassificationRule"]] = relationship(
        "ClassificationRule",
        back_populates="category",
    )
    category_evidence: Mapped[list["CategoryEvidence"]] = relationship(
        "CategoryEvidence",
        back_populates="category",
    )

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}')>"


class CategoryClosure(Base):
    """Closure table for efficient category hierarchy queries."""

    __tablename__ = "category_closure"
    __table_args__ = (
        Index("IX_category_closure_descendant", "descendant_id"),
        {"schema": "finance"},
    )

    # Note: SQL Server doesn't allow multiple CASCADE paths, so we use NO ACTION
    # and rely on CategoryRepository to manage closure table consistency
    ancestor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("finance.categories.id", ondelete="NO ACTION"),
        primary_key=True,
    )
    descendant_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("finance.categories.id", ondelete="NO ACTION"),
        primary_key=True,
    )
    depth: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    ancestor: Mapped["Category"] = relationship(
        "Category",
        foreign_keys=[ancestor_id],
        back_populates="descendant_entries",
    )
    descendant: Mapped["Category"] = relationship(
        "Category",
        foreign_keys=[descendant_id],
        back_populates="ancestor_entries",
    )

    def __repr__(self) -> str:
        return f"<CategoryClosure(ancestor={self.ancestor_id}, descendant={self.descendant_id}, depth={self.depth})>"
