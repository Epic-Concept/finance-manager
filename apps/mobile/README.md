# Quiet Ledger Mobile (Expo)

iOS-first Expo app for reviewing Quiet Ledger cohorts and checking overview stats from your phone.

## Prerequisites

- Node.js 20+
- Expo Go (quick try) or an Apple Developer account (TestFlight / device builds)
- Quiet Ledger API reachable from the phone (`http://gb10.local:8000` by default)

## Quick start

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

## TestFlight (Apple Developer)

1. Install EAS CLI: `npm i -g eas-cli`
2. Log in: `eas login`
3. From `apps/mobile`, create the project: `eas init` (replace the placeholder `extra.eas.projectId` in `app.json`)
4. Build: `eas build -p ios --profile preview`
5. Submit to TestFlight: `eas submit -p ios`

The iOS bundle identifier is `local.quietledger.app`. Change it in `app.json` if that id is already taken in your Apple team.

Local HTTP to a household host is enabled via `NSAllowsLocalNetworking`. Prefer HTTPS when you expose the API beyond the LAN.

## Architecture

- Expo Router tabs: Review · Overview · Settings
- Typed API client in `lib/api.ts` against the existing FastAPI routes
- Persisted API base URL in AsyncStorage (`lib/config.ts`)
