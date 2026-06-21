## 1. Foundation — shell & design system

- [ ] 1.1 Add deps + tooling: React Router, a data-fetching layer (React Query), and confirm vitest/RTL setup
- [ ] 1.2 Implement the Quiet Ledger design tokens (CSS variables: paper/ink/muted/line/verdigris/ochre/clay) + fonts (Newsreader / Hanken Grotesk / IBM Plex Mono, tabular numerals)
- [ ] 1.3 Build the shared primitives: `Card`, `Button`, `TierMark` (4-step evidence dots), `LedgerTable`, `StatLine`, with loading/empty/error states
- [ ] 1.4 App shell: left-rail nav + routes (`/review`, `/bootstrap`, `/rules`, `/overview`); active-surface state; reduced-motion-respecting card transition
- [ ] 1.5 Typed API client (base URL from config) + error normalization
- [ ] 1.6 Tests: routing renders each surface; primitives render tier/empty/error states

## 2. Cockpit API (backend)

- [ ] 2.1 Bootstrap proposals: generate (async job → cached proposal set), list (samples/size/category/confidence/coverage), apply (confirmations → `apply_proposals`) — reuse `build_proposals`/`cluster_coverage`/`apply_proposals`
- [ ] 2.2 Stats endpoint: coverage (decided/total), auto-apply rate, pending-review count
- [ ] 2.3 Active-rules endpoint (pattern + target category) via `DbRuleSource`/repo
- [ ] 2.4 Schemas + router wiring under `/api/v1/{bootstrap,stats,rules}`
- [ ] 2.5 Tests: proposals list/apply (fakes), stats computation, rules list, generation-is-non-blocking

## 3. Bootstrap review UI (human-in-loop first)

- [ ] 3.1 Bootstrap surface: cluster focus cards (samples + LLM proposal + confidence), largest-first, with a live coverage bar
- [ ] 3.2 Confirm / change-category / skip per cluster → apply via the API; generation-progress state
- [ ] 3.3 A human-triggered "confirm all high-confidence" escape hatch (still reviewable, never automatic)
- [ ] 3.4 Tests: confirm-creates-rule, skip-creates-nothing, coverage updates, progress while generating

## 4. Review queue UI

- [ ] 4.1 Review surface: focus card (merchant/amount/date, evidence + `TierMark`, proposed category, "N of M" progress)
- [ ] 4.2 Resolve: confirm / change category / mark internal-transfer → applies + advances to next card
- [ ] 4.3 Keyboard acceleration (confirm/change/skip keys) with visible focus + pointer parity
- [ ] 4.4 Tests: list→resolve advances queue, mark-transfer, keyboard confirm parity, empty queue state

## 5. Overview UI

- [ ] 5.1 Health stat lines: coverage, auto-apply rate, pending-review count (from stats endpoint)
- [ ] 5.2 Rules ledger table (pattern, category, provenance)
- [ ] 5.3 Recently-classified transactions (category, amount, outcome)
- [ ] 5.4 Tests: stats render, rules/recent tables render + empty states

## 6. Deploy & verify on gb10

- [ ] 6.1 Build `finance-manager-web` with the cockpit; confirm it reaches the API on the finance-net/Tailscale
- [ ] 6.2 Live: bootstrap a real cluster set end-to-end through the UI; resolve a few review items; confirm overview reflects reality
- [ ] 6.3 Accessibility/quality floor: keyboard focus, reduced motion, responsive down to a laptop/tablet width; document the cockpit in the ops runbook
