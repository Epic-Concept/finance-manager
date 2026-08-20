# ADR-003: Expo Mobile Client

## Status
Accepted

## Context
Quiet Ledger review work is frequent and short. Phone access is a major convenience. We already expose a versioned FastAPI surface used by the web client, and an Apple Developer account is available for TestFlight distribution.

## Decision
Add an Expo / React Native app under `apps/mobile` that:

1. Reuses the existing `/api/v1/cohorts`, `/api/v1/stats`, and `/api/v1/rules` endpoints
2. Ships Review, Overview, and Settings tabs as the first vertical slice
3. Uses EAS Build + TestFlight for iOS distribution
4. Keeps the web app as the desktop client; mobile is a peer client, not a rewrite of the API

## Consequences

### Positive
- Native phone UX without duplicating backend logic
- Fast iteration via Expo Go during development
- Clear path to App Store / TestFlight with the existing Apple Developer account

### Negative
- Additional CI surface and dependency tree in the monorepo
- Two UI codebases (web + mobile) to keep feature-aligned

### Neutral
- API base URL is configurable on-device for LAN hosts such as `gb10.local`
