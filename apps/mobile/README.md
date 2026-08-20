# Quiet Ledger Mobile (Expo)

iOS-first Expo app for reviewing Quiet Ledger cohorts and checking overview stats from your phone.

## Prerequisites

- Node.js 22+
- Expo account + [EAS](https://expo.dev)
- Apple Developer account (TestFlight / device builds)
- Quiet Ledger API reachable from the phone (`http://gb10.local:8000` by default)

## Quick start (Expo Go)

```bash
cd apps/mobile
npm install
npm start
```

Scan the QR code with Expo Go, or press `i` for the iOS simulator (macOS).

Set the API base URL under **Settings** if you are not on `gb10.local`.

## Scripts

| Command | Purpose |
|---------|---------|
| `npm start` | Expo dev server |
| `npm test` | Jest unit tests |
| `npm run lint` | ESLint |
| `npm run typecheck` | TypeScript `--noEmit` |
| `npm run ios` | Open iOS simulator |

## CI/CD (no Apple passwords in GitHub)

You do **not** put Apple ID / app-specific passwords in the repo or in chat.

| Where | What |
|-------|------|
| **GitHub secret** | `EXPO_TOKEN` — Expo access token from [expo.dev/settings/access-tokens](https://expo.dev/settings/access-tokens) |
| **EAS (remote)** | iOS distribution cert + provisioning profile — created once via `eas credentials` |
| **Optional GitHub secrets** | ASC API key fields — only if CI must repair Apple credentials (`EXPO_ASC_*`, `EXPO_APPLE_TEAM_*`) |

### One-time local setup

```bash
npm i -g eas-cli
eas login
cd apps/mobile
eas init                    # writes real expo.extra.eas.projectId into app.json — commit it
eas credentials -p ios      # let EAS manage signing (remote credentials)
```

For TestFlight submit, set `submit.production.ios.ascAppId` in `eas.json` to your App Store Connect app id (numeric), then commit.

### GitHub Actions

Workflow: [`.github/workflows/eas-mobile.yml`](../../.github/workflows/eas-mobile.yml)

- **Push to `main`** (paths under `apps/mobile/**`) → iOS **preview** build on EAS (`--no-wait`)
- **Actions → Mobile EAS → Run workflow** → choose profile / platform / optional store submit

Add the repo secret:

1. GitHub → Settings → Secrets and variables → Actions → New repository secret
2. Name: `EXPO_TOKEN`
3. Value: Expo personal access token

Until `eas init` has replaced `replace-with-eas-project-id` in `app.json`, the workflow fails fast with a clear error.

### Manual builds (same as CI)

```bash
cd apps/mobile
eas build -p ios --profile preview
eas submit -p ios --profile production --latest   # after a production build
```

Bundle id: `local.quietledger.app` (change in `app.json` if taken in your Apple team).

Local HTTP to a household host is enabled via `NSAllowsLocalNetworking`. Prefer HTTPS when you expose the API beyond the LAN.

## Architecture

- Expo Router tabs: Review · Overview · Settings
- Typed API client in `lib/api.ts` against the existing FastAPI routes
- Persisted API base URL in AsyncStorage (`lib/config.ts`)
