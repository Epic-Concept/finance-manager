## ADDED Requirements

### Requirement: Cockpit shell and navigation

The system SHALL provide a single-page cockpit that navigates between the Review, Bootstrap, Rules, and Overview surfaces without a full page reload, sharing one design system (the Quiet Ledger tokens and the focus-card pattern).

#### Scenario: Navigating between surfaces

- **WHEN** the operator selects a surface from the navigation
- **THEN** that surface is shown without a full page reload, with the navigation reflecting the active surface

### Requirement: Honest loading, empty, and error states

Every surface SHALL show a loading state while data is fetched, a directive empty state when there is nothing to act on, and a recoverable error state (what failed + how to retry) when a request fails.

#### Scenario: A surface has nothing to act on

- **WHEN** a surface has no items (e.g. an empty review queue)
- **THEN** it shows an empty state that says so and points to the next useful action, not a blank screen

#### Scenario: A request fails

- **WHEN** a data request fails
- **THEN** the surface shows what failed and a retry affordance, and does not lose the operator's place

### Requirement: Single-operator access posture

The cockpit SHALL be served to a single trusted operator over the private network (Tailscale) without a login, and SHALL NOT expose any write action that the API does not already authorize.

#### Scenario: Operator opens the cockpit

- **WHEN** the operator opens the cockpit over the tailnet
- **THEN** all surfaces are available without a login step
