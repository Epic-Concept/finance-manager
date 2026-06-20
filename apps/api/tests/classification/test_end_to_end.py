"""End-to-end tests for the assembled classification pipeline (task 9.1).

Wires the real ClassificationEngine + all six gatherers together with faked
external backends (LLM, mailbox, web) and exercises the four headline scenarios:
known-merchant fast path, multi-item receipt split, no-receipt review, and
double-receipt ambiguity.
"""

from datetime import date
from decimal import Decimal

from finance_api.classification.engine import (
    ClassificationEngine,
    KeywordMerchantClassifier,
)
from finance_api.classification.gatherer import GatherContext
from finance_api.classification.gatherers.history import HistoryGatherer
from finance_api.classification.gatherers.llm_inference import (
    CategoryRef,
    LLMInferenceGatherer,
)
from finance_api.classification.gatherers.receipt import EmailCandidate, ReceiptGatherer
from finance_api.classification.gatherers.rules import RuleGatherer, RulePattern
from finance_api.classification.gatherers.web_lookup import WebLookupGatherer
from finance_api.classification.policy import EvidencePolicy, MerchantClass, Outcome
from finance_api.classification.receipt import ReceiptExtractor

CATEGORIES = [
    CategoryRef(1, "Groceries"),
    CategoryRef(2, "Books"),
    CategoryRef(3, "Electronics & Hardware"),
    CategoryRef(7, "Transport"),
]


class _FakeLLM:
    """Routes complete() by prompt; serves chat() from a script. Records calls."""

    def __init__(self, receipt_reply="", inference_reply="", chat_replies=None) -> None:
        self.receipt_reply = receipt_reply
        self.inference_reply = inference_reply
        self._chat = iter(chat_replies or [])
        self.complete_calls = 0
        self.chat_calls = 0

    def complete(self, system: str, user: str) -> str:
        self.complete_calls += 1
        if "receipt" in system.lower() or "line item" in system.lower():
            return self.receipt_reply
        return self.inference_reply

    def chat(self, messages, tools=None) -> dict:
        self.chat_calls += 1
        return next(self._chat)


class _FakeRuleSource:
    def __init__(self, rules):
        self._rules = rules

    def active_rules(self):
        return list(self._rules)


class _FakeHistorySource:
    def __init__(self, outcomes=None):
        self._outcomes = outcomes or []

    def outcomes_for(self, description):
        return list(self._outcomes)


class _FakeMailbox:
    def __init__(self, candidates):
        self._candidates = candidates

    def find_candidates(self, context):
        return list(self._candidates)


class _FakeWebSearch:
    def search(self, query):
        return []


def _build_engine(
    *,
    rules=(),
    history=None,
    mailbox_candidates=(),
    llm=None,
    splittable=("amazon",),
):
    llm = llm or _FakeLLM()
    gatherers = [
        RuleGatherer(_FakeRuleSource(rules)),
        HistoryGatherer(_FakeHistorySource(history)),
        ReceiptGatherer(
            _FakeMailbox(mailbox_candidates), ReceiptExtractor(llm), CATEGORIES
        ),
        WebLookupGatherer(llm.chat, _FakeWebSearch(), CATEGORIES),
        LLMInferenceGatherer(llm, CATEGORIES),
    ]
    return ClassificationEngine(
        gatherers=gatherers,
        policy=EvidencePolicy(),
        merchant_classifier=KeywordMerchantClassifier(list(splittable)),
    )


def _ctx(description, amount="20.00"):
    return GatherContext(
        transaction_id=1,
        description=description,
        amount=Decimal(amount),
        currency="GBP",
        transaction_date=date(2026, 6, 6),
    )


def _candidate(mailbox, mid):
    return EmailCandidate(text="order email", mailbox=mailbox, message_id=mid)


_RECEIPT_2_ITEMS = (
    '{"merchant":"Amazon","currency":"GBP","items":['
    '{"description":"book","amount":12.00,"category_id":2},'
    '{"description":"cable","amount":8.00,"category_id":3}]}'
)


class TestEndToEnd:
    def test_known_merchant_fast_path_skips_costly_gatherers(self) -> None:
        llm = _FakeLLM()
        engine = _build_engine(rules=[RulePattern(r"(?i)tfl", 7, "tfl")], llm=llm)
        outcome = engine.classify(_ctx("TFL TRAVEL"))
        assert outcome.decision.outcome is Outcome.AUTO_APPLY
        assert outcome.decision.claim.category_ids == (7,)
        # rule resolved it: the LLM was never touched
        assert llm.complete_calls == 0 and llm.chat_calls == 0

    def test_multi_item_receipt_split_auto_applies(self) -> None:
        llm = _FakeLLM(receipt_reply=_RECEIPT_2_ITEMS)
        engine = _build_engine(
            mailbox_candidates=[_candidate("joint@x.com", "m1")], llm=llm
        )
        outcome = engine.classify(_ctx("AMAZON MKTP", "20.00"))
        assert outcome.merchant_class is MerchantClass.SPLITTABLE
        assert outcome.decision.outcome is Outcome.AUTO_APPLY
        assert outcome.decision.claim.itemized is True
        assert sorted(s.amount for s in outcome.decision.claim.splits) == [
            Decimal("8.00"),
            Decimal("12.00"),
        ]

    def test_no_receipt_for_splittable_merchant_routes_to_review(self) -> None:
        # empty mailbox; web/llm can only offer non-itemized guesses -> review
        llm = _FakeLLM(
            inference_reply='{"category_id": 3}',
            chat_replies=[
                {
                    "role": "assistant",
                    "content": '{"category_id":3,"single_category_merchant":false,"confidence":"low"}',
                    "tool_calls": None,
                }
            ],
        )
        engine = _build_engine(mailbox_candidates=[], llm=llm)
        outcome = engine.classify(_ctx("AMAZON MKTP", "20.00"))
        assert outcome.decision.outcome is Outcome.REVIEW

    def test_double_receipt_ambiguity_routes_to_review(self) -> None:
        # reconciling receipt found in TWO mailboxes -> strength capped below PROOF
        llm = _FakeLLM(
            receipt_reply=_RECEIPT_2_ITEMS,
            inference_reply='{"category_id": 3}',
            chat_replies=[
                {
                    "role": "assistant",
                    "content": '{"category_id":3,"single_category_merchant":false,"confidence":"low"}',
                    "tool_calls": None,
                }
            ],
        )
        engine = _build_engine(
            mailbox_candidates=[
                _candidate("wife@x.com", "m1"),
                _candidate("husband@x.com", "m2"),
            ],
            llm=llm,
        )
        outcome = engine.classify(_ctx("AMAZON MKTP", "20.00"))
        assert outcome.decision.outcome is Outcome.REVIEW
