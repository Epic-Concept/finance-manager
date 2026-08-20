"""Build IMAP mailbox clients from DB ``EmailAccount`` rows or env fallback."""

from __future__ import annotations

import logging
import os

from sqlalchemy.orm import Session

from finance_api.classification.gatherers.imap_mailbox import ImapMailboxClient
from finance_api.core.config import Settings
from finance_api.core.config import settings as default_settings
from finance_api.repositories.email_account_repository import EmailAccountRepository

logger = logging.getLogger(__name__)

_PROVIDER_DEFAULTS: dict[str, tuple[str, str]] = {
    "gmail": ("imap.gmail.com", "\\All"),
    "outlook": ("outlook.office365.com", "INBOX"),
    "imap_generic": ("", "INBOX"),
}


def resolve_credential(reference: str | None, settings: Settings) -> str:
    """Resolve a mailbox password from ``ENV:VAR`` or a literal reference."""
    if not reference:
        return ""
    if reference.startswith("ENV:"):
        return os.environ.get(reference[4:], "")
    return reference


def build_mailbox_clients(
    session: Session, settings: Settings = default_settings
) -> list[ImapMailboxClient]:
    """Build searchable IMAP clients from active email accounts or env fallback."""
    repo = EmailAccountRepository(session)
    clients: list[ImapMailboxClient] = []

    for account in repo.get_active_by_priority():
        password = resolve_credential(account.credential_reference, settings)
        if not password:
            logger.warning(
                "skipping email account %s: no credential resolved",
                account.email_address,
            )
            continue

        host_default, folder_default = _PROVIDER_DEFAULTS.get(
            account.provider, _PROVIDER_DEFAULTS["imap_generic"]
        )
        host = account.imap_server or host_default
        if not host:
            logger.warning(
                "skipping email account %s: imap_server not configured",
                account.email_address,
            )
            continue

        clients.append(
            ImapMailboxClient(
                mailbox_id=account.email_address,
                host=host,
                username=account.email_address,
                password=password,
                port=account.imap_port,
                folder=folder_default,
            )
        )

    if not clients and settings.gmail_imap_user and settings.gmail_imap_password:
        clients.append(
            ImapMailboxClient(
                mailbox_id=settings.gmail_imap_user,
                host=settings.gmail_imap_host,
                username=settings.gmail_imap_user,
                password=settings.gmail_imap_password,
                folder=settings.gmail_imap_folder,
            )
        )

    return clients
