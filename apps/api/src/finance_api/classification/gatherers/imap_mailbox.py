"""IMAP mailbox client (e.g. Gmail via an app password).

Implements the MailboxClient protocol: searches a mailbox over IMAP within a
date window for merchant terms and returns RawEmail objects for the receipt
gatherer. Credentials (app password) come from configuration, never hard-coded.

Pure helpers (search-criteria building, message parsing) are unit-tested; the
network search() is covered by a live integration test.
"""

from __future__ import annotations

import email
import imaplib
import re
from collections.abc import Sequence
from datetime import date
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parsedate_to_datetime

from finance_api.classification.gatherers.mailbox import RawEmail

_QUOTED = re.compile(r'"([^"]*)"')


def _imap_date(d: date) -> str:
    return d.strftime("%d-%b-%Y")


def quote_mailbox(name: str) -> str:
    """Quote an IMAP mailbox name so names with spaces (e.g. '[Gmail]/All Mail')
    parse correctly; imaplib does not quote them automatically."""
    return f'"{name}"'


def find_special_folder(list_response: Sequence[object], flag: str) -> str | None:
    """Find the mailbox carrying an IMAP special-use flag (e.g. '\\All').

    Locale-independent: Gmail localizes folder display names ('All Mail' vs
    'Wszystkie'), but the special-use flags on the LIST response are stable.
    """
    for raw in list_response:
        line = raw.decode(errors="replace") if isinstance(raw, bytes) else str(raw)
        flags_part = line[: line.find(")")] if ")" in line else line
        if flag.lower() in flags_part.lower():
            names = _QUOTED.findall(line)
            if names:
                return str(names[-1])
    return None


def build_search_criteria(terms: list[str], since: date, until: date) -> list[str]:
    """Build IMAP SEARCH arguments for a date window + OR-combined text terms."""
    criteria = ["SINCE", _imap_date(since), "BEFORE", _imap_date(until)]
    if terms:
        # IMAP OR is prefix and binary; fold terms into nested ORs.
        term_criteria = ["TEXT", terms[0]]
        for term in terms[1:]:
            term_criteria = ["OR", "TEXT", term] + term_criteria
        criteria += term_criteria
    return criteria


def _decode_header(value: str) -> str:
    """Decode an RFC 2047 MIME-encoded header (e.g. '=?UTF-8?Q?...?=')."""
    try:
        return str(make_header(decode_header(value)))
    except (ValueError, LookupError):
        return value


def _body_text(message: Message) -> str:
    """Extract the best body text (prefer text/plain, fall back to text/html)."""
    if message.is_multipart():
        plain = None
        html_part = None
        for part in message.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain" and plain is None:
                plain = part
            elif ctype == "text/html" and html_part is None:
                html_part = part
        chosen = plain or html_part
        if chosen is not None:
            payload = chosen.get_payload(decode=True)
            if isinstance(payload, bytes):
                return payload.decode(
                    chosen.get_content_charset() or "utf-8", "replace"
                )
        return ""
    payload = message.get_payload(decode=True)
    if isinstance(payload, bytes):
        return payload.decode(message.get_content_charset() or "utf-8", "replace")
    return str(message.get_payload())


class ImapMailboxClient:
    """A single IMAP mailbox searchable by the multi-mailbox source."""

    def __init__(
        self,
        mailbox_id: str,
        host: str,
        username: str,
        password: str,
        port: int = 993,
        folder: str = "INBOX",
        max_results: int = 10,
    ) -> None:
        self.mailbox_id = mailbox_id
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._folder = folder
        self._max_results = max_results

    def _parse_message(self, raw: bytes) -> RawEmail:
        message = email.message_from_bytes(raw)
        date_header = message.get("Date")
        msg_date = date(1970, 1, 1)
        if date_header:
            try:
                msg_date = parsedate_to_datetime(date_header).date()
            except (TypeError, ValueError):
                pass
        return RawEmail(
            message_id=str(message.get("Message-ID", "")).strip(),
            mailbox=self.mailbox_id,
            subject=_decode_header(str(message.get("Subject", ""))).strip(),
            body=_body_text(message),
            date=msg_date,
            sender=_decode_header(str(message.get("From", ""))).strip(),
        )

    def search(self, terms: list[str], since: date, until: date) -> list[RawEmail]:
        criteria = build_search_criteria(terms, since, until)
        conn = imaplib.IMAP4_SSL(self._host, self._port)
        try:
            conn.login(self._username, self._password)
            folder = self._folder
            # A "\Flag" folder is resolved to the actual (possibly localized)
            # mailbox name via its IMAP special-use flag.
            if folder.startswith("\\"):
                _, boxes = conn.list()
                folder = find_special_folder(boxes or [], folder) or "INBOX"
            conn.select(quote_mailbox(folder), readonly=True)
            _, data = conn.search(None, *criteria)
            message_ids = data[0].split() if data and data[0] else []
            results: list[RawEmail] = []
            for mid in message_ids[-self._max_results :]:
                _, fetched = conn.fetch(mid, "(RFC822)")
                if fetched and isinstance(fetched[0], tuple):
                    results.append(self._parse_message(fetched[0][1]))
            return results
        finally:
            try:
                conn.logout()
            except OSError:
                pass
