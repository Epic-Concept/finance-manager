"""Tests for the cold-start rule bootstrap.

Clusters transactions and asks the LLM to propose a category per cluster (one
call per cluster, not per transaction). The human confirms; confirmed proposals
become rules. Tested with a fake LLM (no network).
"""

from finance_api.classification.bootstrap import (
    ClusterCategoryProposer,
    build_proposals,
)
from finance_api.classification.gatherers.llm_inference import CategoryRef
from finance_api.services.transaction_clustering_service import TransactionCluster

CATEGORIES = [CategoryRef(9, "Eating Out"), CategoryRef(1, "Groceries")]


class _FakeLLM:
    def __init__(self, reply: str) -> None:
        self._reply = reply

    def complete(self, system: str, user: str) -> str:
        return self._reply


def _cluster(key: str, count: int, samples: list[str]) -> TransactionCluster:
    return TransactionCluster(
        cluster_key=key,
        cluster_hash="h",
        transactions=[object()] * count,  # only len() is used
        sample_descriptions=samples,
    )


class TestClusterCategoryProposer:
    def test_proposes_category_and_pattern(self) -> None:
        proposer = ClusterCategoryProposer(
            _FakeLLM('{"category_id": 9, "confidence": "high"}'), CATEGORIES
        )
        p = proposer.propose(_cluster("GREGGS", 14, ["GREGGS 12", "GREGGS 90"]))
        assert p.cluster_key == "GREGGS"
        assert p.transaction_count == 14
        assert p.proposed_category_id == 9
        assert p.proposed_category_name == "Eating Out"
        assert p.confidence == "high"
        # a usable regex matching the merchant key, case-insensitive
        assert "GREGGS" in p.suggested_pattern.upper()

    def test_invalid_category_leaves_proposal_unresolved(self) -> None:
        proposer = ClusterCategoryProposer(
            _FakeLLM('{"category_id": 999, "confidence": "high"}'), CATEGORIES
        )
        p = proposer.propose(_cluster("MYSTERY", 3, ["X"]))
        assert p.proposed_category_id is None

    def test_unparseable_reply_leaves_proposal_unresolved(self) -> None:
        proposer = ClusterCategoryProposer(_FakeLLM("dunno"), CATEGORIES)
        assert proposer.propose(_cluster("X", 2, ["a"])).proposed_category_id is None


class TestBuildProposals:
    def test_proposes_for_largest_clusters_first(self) -> None:
        from finance_api.services.transaction_clustering_service import (
            TransactionClusteringService,
        )

        class _Txn:
            def __init__(self, id, desc):
                self.id = id
                self.description = desc

        txns = [_Txn(i, "GREGGS shop") for i in range(5)] + [
            _Txn(100 + i, "TESCO store") for i in range(2)
        ]
        proposer = ClusterCategoryProposer(
            _FakeLLM('{"category_id": 1, "confidence": "medium"}'), CATEGORIES
        )
        proposals = build_proposals(
            txns, proposer, TransactionClusteringService(min_cluster_size=1), top_n=10
        )
        # largest cluster (GREGGS, 5) ranked before TESCO (2)
        assert proposals[0].transaction_count >= proposals[1].transaction_count
        assert {p.cluster_key for p in proposals} == {"GREGGS", "TESCO"}
