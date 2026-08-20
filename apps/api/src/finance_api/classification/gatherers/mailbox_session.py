"""Reuse IMAP connections for the duration of a receipt gather."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager

from finance_api.classification.gatherers.imap_mailbox import ImapMailboxClient
from finance_api.classification.gatherers.mailbox import MailboxClient


@contextmanager
def imap_session(clients: Sequence[MailboxClient]) -> Iterator[None]:
    """Connect all IMAP clients for a gather, disconnect on exit."""
    imap_clients = [c for c in clients if isinstance(c, ImapMailboxClient)]
    for client in imap_clients:
        client.connect()
    try:
        yield
    finally:
        for client in imap_clients:
            client.disconnect()
