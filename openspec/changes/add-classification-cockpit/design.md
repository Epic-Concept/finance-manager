## Context

The classifier runs unattended; the human only supervises — confirming categories the system is unsure about, and bootstrapping the rule cache. Those steps are currently CLI/chat. This change gives them a frontend. The web app is a bare Vite + React + TypeScript skeleton (no router, state, or design system), served as `finance-manager-web` on gb10; the API is FastAPI on :8088. Single operator (the user + spouse) over Tailscale.

## Goals / Non-Goals

**Goals**
- Make the human steps (bootstrap, daily review) fast and calm — a repeatable ritual, not a firehose.
- One cohesive product: a small shared design system + one signature interaction reused everywhere.
- A thin, honest API over the existing engine (proposals, stats, rules) + the existing review API.

**Non-Goals**
- Multi-user auth/roles; editing the category hierarchy in-UI; reprocessing after rule changes; budgeting/analytics dashboards.

## Design direction — "Quiet Ledger"

The subject is a *private ledger you keep with a machine*: it proposes, you initial each entry. The feeling is an unhurried review ritual at a desk, not a trading terminal. One decision fills the view; everything else recedes.

### Color — a verdigris-ink ledger (not cream/terracotta, not near-black/acid)
- `--paper` `#F6F7F4` — cool paper, faint green-grey (deliberately not the warm-cream default)
- `--ink` `#19211E` — near-black with a green tint, for primary text
- `--muted` `#6C736E` — slate-sage, secondary text and captions
- `--line` `#E3E6E0` — hairline rules and card borders
- `--verdigris` `#2E6E5E` — the single brand accent: confirm, active nav, focus ring (aged ledger ink + money)
- functional signal: `--ochre` `#B07D2A` (review / WEAK), `--clay` `#9A4B3B` (contested / needs attention). Used only as small marks, never as fills.

### Type — editorial voice + humanist UI + tabular money
- **Display (serif): Newsreader** — the "ledger voice": the merchant name on a focus card, surface titles. Warm, editorial, used with restraint.
- **UI (sans): Hanken Grotesk** — buttons, labels, nav, body. Humanist, a little character, not Inter.
- **Data (mono): IBM Plex Mono** — amounts, dates, transaction ids, evidence sources. **Tabular numerals** so money columns align.
- Scale is quiet and large where it matters: the merchant name is the biggest thing on the screen; actions and metadata sit well below it.

### Layout — the focus card is the hero
A narrow centered column on paper, a quiet left rail for the four surfaces. The hero is literally the **focus card**: one transaction, its evidence, the suggested category, three calm actions — the first thing you see, because deciding is the job.

```
┌────────────┬───────────────────────────────────────┐
│  ◦ Review  │              Review · 3 of 24          │
│  ◦ Bootstrap                                        │
│  ◦ Rules   │      CENTRUM MEDYCZNE MEDICONCEPT      │  ← Newsreader, large
│  ◦ Overview│         −126,00 PLN · 2026-06-12       │  ← Plex Mono, tabular
│            │                                        │
│            │     evidence  web-lookup · ·· WEAK     │  ← tier as a quiet mark
│            │     suggested → General Shopping       │
│            │                                        │
│            │   [ Confirm ]   [ Change ]   [ Skip ]  │  ← verdigris primary
│            │     c            e            s        │  ← subtle key hints
└────────────┴───────────────────────────────────────┘
```

Bootstrap reuses the same card (cluster samples + LLM proposal + a slim coverage bar instead of "N of M"). Overview is a short stack of quiet stat lines + a ledger table; Rules is that table filtered.

### Signature — the evidence-graded focus card + the "initial it" ritual
The one memorable element: a single decision card where **evidence strength is a typographic mark, not a badge** — a 4-step tier rendered as graded dots/weight (`···· PROOF` → `·    NONE`) in the verdigris ink, so you read confidence at a glance and develop a rhythm. Confirm/Change/Skip carry quiet `c/e/s` keys so a practiced operator clears the queue without reaching for the mouse — calm by default, fast when you want it. Progress is honest ("3 of 24", a thin coverage bar), never gamified.

### Restraint
One accent (verdigris); signal colors only as small marks. No gradients, no card shadows beyond a hairline, motion limited to a soft card cross-fade between decisions (respecting `prefers-reduced-motion`). The boldness is spent on the focus card; everything else is quiet.

## Technical decisions

### Decision: React Router + a tiny typed API client, no heavy state lib
Four routes (`/review`, `/bootstrap`, `/rules`, `/overview`). Server state via a small fetch wrapper + React Query (cache/refetch) — no Redux. Keeps the bundle small for a single-operator app.

### Decision: A hand-built design system, not a component kit
The Quiet Ledger look is the point; a kit (MUI/Chakra) would fight it. CSS variables for the tokens above + a handful of primitives (Card, Button, TierMark, LedgerTable, StatLine). Small surface, full control, matches the brief.

### Decision: Bootstrap proposals are precomputed and cached, generated async
LLM-per-cluster is slow (tens of seconds each). The API exposes "generate proposals" as a job that writes a cached proposal set; the UI lists the cached set and shows generation progress, and "apply" turns confirmed rows into rules via `apply_proposals`. No request blocks on the LLM.

### Decision: Reuse the engine; the API is thin
`cockpit-api` wraps existing building blocks — `build_proposals`/`apply_proposals`, `ReviewService`, `DbRuleSource`, persisted decisions — adding only proposal-cache + stats endpoints. No classification logic in the web tier.

### Decision: Single-operator access posture
Served over Tailscale to a trusted operator; no login. A shared-secret header is the only gate if exposed beyond the tailnet (deferred). Documented, not built now.

## Risks / Trade-offs
- **Proposal generation latency** → async generate + cache + progress; never block a request.
- **Calm vs. throughput** → the focus-card ritual could feel slow at 100s of items; mitigate with keyboard `c/e/s` and a "confirm all high-confidence" escape hatch on bootstrap (still human-triggered).
- **Design drift** → a tiny enforced token set + primitives; no second styling system.
- **Backlog already decided** (no reprocessing) → the overview surfaces this; out of scope to fix here.

## Migration Plan
1. Stand up the cockpit shell + design system + routing (no behavior yet).
2. Build `cockpit-api` (proposals cache/apply, rules, stats).
3. Ship the human-in-loop surfaces first: bootstrap-review, then review-queue.
4. Add the overview (stats + rules + recent transactions).
5. Deploy `finance-manager-web` on gb10; verify over Tailscale.

Rollback: the cockpit is additive (new routes + new read/affordance endpoints); the CLIs remain the fallback.

## Open Questions
- Generate proposals on demand (with progress) vs. precompute nightly and cache.
- Whether to add a global command palette later (keyboard navigation across surfaces).
