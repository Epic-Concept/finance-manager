## Why

The classifier is operational, but every human-in-the-loop step is a CLI or a chat transcript: cold-start bootstrap is an interactive terminal session (or pasting tables into a conversation), and resolving the review queue is raw API calls. That doesn't scale to supervising hundreds of merchant decisions, and it makes the one thing only a human can do — confirming categories — the slowest part of the loop. We need a **cockpit**: a calm, fast surface that turns supervising the classifier into a short, repeatable ritual, so coverage grows without the human dreading it.

## What Changes

- **NEW** A React **management cockpit** ("Quiet Ledger") that makes the human steps streamlined: a one-decision-at-a-time focus-card review of the daily queue, the cold-start bootstrap review (cluster → LLM proposal → confirm/correct/skip with live coverage), and an at-a-glance overview of coverage, auto-apply rate, rules, and recent activity. Single-operator (gb10 over Tailscale), no heavyweight auth.
- **NEW** The **cockpit API** the UI needs: generate/list/apply bootstrap cluster proposals (today the bootstrap is CLI-only), list active rules, and classification stats (coverage, auto-apply rate, queue depth). The review queue API already exists and is reused.
- A small, consistent **design system** (the Quiet Ledger tokens + the focus-card pattern) shared across every surface so the whole experience reads as one product.
- Replaces the deferred React review-screen stub (operationalize-classification 5.5) with a real, cohesive cockpit.

## Capabilities

### New Capabilities
- `cockpit-shell`: The app frame for the management cockpit — navigation between surfaces, the shared Quiet Ledger design system and the focus-card pattern, loading/empty/error states, and the single-operator access posture.
- `bootstrap-review-ui`: The cold-start review surface — present the largest clusters with the LLM's proposed category and running coverage, and let the operator confirm/correct/skip, creating rules only on confirmation.
- `review-queue-ui`: The daily review surface — a focus-card flow to resolve pending decisions (confirm / reclassify / mark internal-transfer) with the supporting evidence shown.
- `classification-overview-ui`: The at-a-glance surface — coverage, auto-apply rate, and queue depth as live signal, plus browsable rules and recently-classified transactions.
- `cockpit-api`: The backend endpoints the cockpit needs — generate/list/apply bootstrap cluster proposals, list active rules, and classification stats.

### Modified Capabilities
<!-- None: builds on operationalize-classification + the evidence-driven engine without changing their requirements. -->

## Impact

- **Affected code:** `apps/web/` (router, design-system, pages, services — currently a bare Vite/React/TS skeleton); new `finance_api/routers/{bootstrap,stats}.py` + schemas; reuses `bootstrap.build_proposals`/`apply_proposals`, `ReviewService`, `DbRuleSource`, and the persisted decisions.
- **Dependencies:** the local LLM gateway for bootstrap proposal generation (already reachable from the API container); no new external services.
- **Operations:** served by the existing `finance-manager-web` container on gb10 (:8089) over Tailscale, talking to the API on :8088. Bootstrap proposal generation is slow (LLM per cluster) → generated asynchronously, not in a request.
- **Out of scope (deferred):** multi-user auth/roles, editing the category hierarchy in-UI, reprocessing already-decided transactions after a rule change, and budgeting/reporting dashboards.

## Open Questions

- Bootstrap proposal generation is slow (reasoning LLM per cluster) — generate on demand with progress, or precompute on a schedule and cache?
- How much keyboard acceleration the "quiet ritual" should carry (confirm/change/skip shortcuts) without turning into a firehose.
- Whether "mark internal-transfer" needs a dedicated affordance vs. just picking the Internal Transfer category.
