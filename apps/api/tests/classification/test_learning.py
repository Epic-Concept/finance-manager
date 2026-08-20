"""Tests for the shadow learner (classification-learning spec, group 8)."""

from decimal import Decimal

from finance_api.classification.evidence import Claim, Split
from finance_api.classification.learning import (
    LearningObservation,
    ShadowLearner,
    merchant_key,
    observe,
)


class TestObserve:
    def test_single_category_outcome_becomes_observation(self) -> None:
        obs = observe("GREGGS 123", Claim.single_category(9), human_confirmed=True)
        assert obs.merchant_key == "GREGGS"
        assert obs.category_id == 9
        assert obs.is_split is False
        assert obs.human_confirmed is True

    def test_split_outcome_carries_signature_and_total(self) -> None:
        claim = Claim.split([Split(1, Decimal("12.00")), Split(2, Decimal("8.00"))])
        obs = observe("AMAZON MKTP", claim, human_confirmed=False)
        assert obs.is_split is True
        assert obs.total_amount == Decimal("20.00")
        assert obs.split_signature == ((1, Decimal("12.00")), (2, Decimal("8.00")))


def _obs(
    key: str,
    category: int,
    human: bool,
    is_split: bool = False,
    total: str | None = None,
    signature: tuple[tuple[int, str], ...] | None = None,
) -> LearningObservation:
    return LearningObservation(
        merchant_key=key,
        category_id=category,
        human_confirmed=human,
        is_split=is_split,
        total_amount=Decimal(total) if total else None,
        split_signature=(
            tuple((c, Decimal(a)) for c, a in signature) if signature else None
        ),
    )


class TestMerchantKey:
    def test_first_significant_token(self) -> None:
        assert merchant_key("GREGGS 123 LONDON") == "GREGGS"
        assert merchant_key("TESCO STORES 4471") == "TESCO"


class TestRulePromotion:
    def test_consistent_human_confirmed_proposes_rule(self) -> None:
        learner = ShadowLearner(min_observations=3)
        obs = [
            _obs("GREGGS", 9, human=True),
            _obs("GREGGS", 9, human=False),
            _obs("GREGGS", 9, human=True),
        ]
        proposals = learner.propose_rules(obs)
        assert len(proposals) == 1
        assert proposals[0].merchant_key == "GREGGS"
        assert proposals[0].category_id == 9
        assert proposals[0].support == 3
        assert "matches" in proposals[0].expression
        assert "GREGGS" in proposals[0].expression

    def test_below_min_observations_no_proposal(self) -> None:
        learner = ShadowLearner(min_observations=3)
        assert learner.propose_rules([_obs("X", 1, True), _obs("X", 1, True)]) == []

    def test_never_human_confirmed_no_proposal(self) -> None:
        # self-confirmation guard: only the system's own auto-applies
        learner = ShadowLearner(min_observations=3)
        obs = [_obs("X", 1, False) for _ in range(5)]
        assert learner.propose_rules(obs) == []

    def test_conflicting_categories_no_proposal(self) -> None:
        learner = ShadowLearner(min_observations=3)
        obs = [_obs("X", 1, True), _obs("X", 2, True), _obs("X", 1, True)]
        assert learner.propose_rules(obs) == []


class TestCacheAsymmetry:
    def test_splits_do_not_produce_merchant_rules(self) -> None:
        learner = ShadowLearner(min_observations=2)
        obs = [_obs("AMAZON", 1, True, is_split=True) for _ in range(5)]
        assert learner.propose_rules(obs) == []

    def test_recurring_identical_split_proposes_template(self) -> None:
        learner = ShadowLearner(min_observations=3)
        sig = ((1, "10.00"), (2, "5.00"))
        obs = [
            _obs(
                "NETFLIXBUNDLE",
                1,
                human=True,
                is_split=True,
                total="15.00",
                signature=sig,
            )
            for _ in range(3)
        ]
        templates = learner.detect_recurring_splits(obs)
        assert len(templates) == 1
        assert templates[0].merchant_key == "NETFLIXBUNDLE"
        assert templates[0].total_amount == Decimal("15.00")
        assert templates[0].support == 3

    def test_variable_splits_no_template(self) -> None:
        learner = ShadowLearner(min_observations=2)
        obs = [
            _obs(
                "AMAZON",
                1,
                True,
                is_split=True,
                total="20.00",
                signature=((1, "20.00"),),
            ),
            _obs(
                "AMAZON",
                1,
                True,
                is_split=True,
                total="35.00",
                signature=((2, "35.00"),),
            ),
        ]
        assert learner.detect_recurring_splits(obs) == []


class TestLearningBoundary:
    def test_recalibration_is_advisory_and_needs_human_approval(self) -> None:
        learner = ShadowLearner()
        rec = learner.recommend_recalibration(0.996, "single_category@STRONG")
        assert rec.requires_human_approval is True
        assert "loosen" in rec.message.lower()

    def test_low_accuracy_recommends_tightening(self) -> None:
        learner = ShadowLearner()
        rec = learner.recommend_recalibration(0.90, "unknown@STRONG")
        assert rec.requires_human_approval is True
        assert "tighten" in rec.message.lower()

    def test_learner_cannot_mutate_the_policy_gate(self) -> None:
        # The learner must expose no way to change the required-tier table.
        learner = ShadowLearner()
        assert not hasattr(learner, "apply_recalibration")
        assert not hasattr(learner, "set_required_tier")
