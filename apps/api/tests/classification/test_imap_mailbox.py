"""Tests for the IMAP mailbox client (Gmail via app password).

The network search() is covered by a live test; here we unit-test the pure
IMAP-search-criteria builder and the raw-message parser.
"""

from datetime import date

from finance_api.classification.gatherers.imap_mailbox import (
    ImapMailboxClient,
    build_search_criteria,
    quote_mailbox,
)


class TestQuoteMailbox:
    def test_quotes_names_with_spaces(self) -> None:
        assert quote_mailbox("[Gmail]/All Mail") == '"[Gmail]/All Mail"'


RAW_EMAIL = b"""From: Amazon <auto-confirm@amazon.co.uk>
Subject: Your Amazon order
Date: Mon, 09 Jun 2026 10:30:00 +0000
Message-ID: <order-123@amazon.co.uk>
Content-Type: text/plain; charset="utf-8"

Order total GBP 20.00
"""


class TestBuildSearchCriteria:
    def test_date_window_only(self) -> None:
        crit = build_search_criteria([], date(2026, 6, 5), date(2026, 6, 15))
        assert crit == ["SINCE", "05-Jun-2026", "BEFORE", "15-Jun-2026"]

    def test_single_term(self) -> None:
        crit = build_search_criteria(["AMAZON"], date(2026, 6, 5), date(2026, 6, 15))
        assert crit == [
            "SINCE",
            "05-Jun-2026",
            "BEFORE",
            "15-Jun-2026",
            "TEXT",
            "AMAZON",
        ]

    def test_multiple_terms_are_or_combined(self) -> None:
        crit = build_search_criteria(
            ["AMZN", "AMAZON"], date(2026, 6, 5), date(2026, 6, 15)
        )
        # OR is prefix in IMAP: OR <a> <b>
        assert crit == [
            "SINCE",
            "05-Jun-2026",
            "BEFORE",
            "15-Jun-2026",
            "OR",
            "TEXT",
            "AMAZON",
            "TEXT",
            "AMZN",
        ]


class TestParseMessage:
    def test_decodes_mime_encoded_subject(self) -> None:
        raw = (
            b"Subject: =?UTF-8?Q?Your_=C2=A315_order?=\r\n"
            b"Message-ID: <x@y>\r\nDate: Mon, 09 Jun 2026 10:00:00 +0000\r\n"
            b'Content-Type: text/plain; charset="utf-8"\r\n\r\nbody\r\n'
        )
        client = ImapMailboxClient(
            mailbox_id="me@gmail.com",
            host="imap.gmail.com",
            username="me@gmail.com",
            password="x",
        )
        assert client._parse_message(raw).subject == "Your £15 order"

    def test_parses_headers_and_body(self) -> None:
        client = ImapMailboxClient(
            mailbox_id="me@gmail.com",
            host="imap.gmail.com",
            username="me@gmail.com",
            password="x",
        )
        raw = client._parse_message(RAW_EMAIL)
        assert raw.mailbox == "me@gmail.com"
        assert raw.message_id == "<order-123@amazon.co.uk>"
        assert raw.subject == "Your Amazon order"
        assert raw.date == date(2026, 6, 9)
        assert "Order total GBP 20.00" in raw.body
