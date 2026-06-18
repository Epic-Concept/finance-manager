"""Tests for the Brave web-search adapter.

The HTTP wiring is covered by a live integration test; here we unit-test the
pure response parsing.
"""

from finance_api.classification.gatherers.web_lookup import SearchResult
from finance_api.classification.web_search import BraveWebSearch

SAMPLE = {
    "web": {
        "results": [
            {
                "title": "Seeed Studio",
                "url": "https://seeedstudio.com",
                "description": "Open-source hardware and electronics.",
            },
            {
                "title": "Seeed on Wikipedia",
                "url": "https://en.wikipedia.org/wiki/Seeed",
                "description": "A German band.",
            },
        ]
    }
}


class TestBraveParse:
    def test_parses_results_into_search_results(self) -> None:
        results = BraveWebSearch._parse(SAMPLE)
        assert results == [
            SearchResult(
                "Seeed Studio",
                "https://seeedstudio.com",
                "Open-source hardware and electronics.",
            ),
            SearchResult(
                "Seeed on Wikipedia",
                "https://en.wikipedia.org/wiki/Seeed",
                "A German band.",
            ),
        ]

    def test_missing_web_block_yields_empty(self) -> None:
        assert BraveWebSearch._parse({}) == []
        assert BraveWebSearch._parse({"web": {}}) == []
