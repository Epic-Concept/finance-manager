## ADDED Requirements

### Requirement: Focus-card review of the queue

The review surface SHALL present pending decisions one focus card at a time, showing the transaction (merchant, amount, date), the supporting evidence with its strength tier, and the proposed categorization, and SHALL show progress through the queue (position and total).

#### Scenario: Reviewing a pending decision

- **WHEN** the review surface loads with a non-empty queue
- **THEN** it shows the first pending decision as a focus card with the transaction, evidence + strength tier, proposed category, and queue progress

### Requirement: Resolve a decision

The operator SHALL be able to resolve the current card by confirming the proposed category, changing it to another category, or marking it an internal transfer; on resolve the categorization is applied, the item leaves the queue, and the next card is shown.

#### Scenario: Confirming the current card

- **WHEN** the operator confirms (or changes) the current card's category
- **THEN** the categorization is applied, the item leaves the queue, and the next pending card is shown

#### Scenario: Marking an internal transfer

- **WHEN** the operator marks the current card an internal transfer
- **THEN** it is categorized as an internal transfer and leaves the queue

### Requirement: Keyboard acceleration

The review surface SHALL support resolving the current card from the keyboard (confirm / change / skip) so a practiced operator can clear the queue without the mouse, while remaining fully usable with pointer and keyboard focus visible.

#### Scenario: Confirming from the keyboard

- **WHEN** the operator presses the confirm key on a focus card
- **THEN** the card is confirmed and the next card is shown, the same as clicking Confirm
