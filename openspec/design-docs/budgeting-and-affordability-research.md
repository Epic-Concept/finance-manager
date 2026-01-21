# Research: Principled Approaches to Personal Expense Categorization

> **Reference Document**: This is a comprehensive research document capturing frameworks, algorithms, and design patterns for personal finance categorization and affordability calculations. It serves as the foundation for the `add-category-hierarchy` change proposal.

## The Core Problem

The goal is to answer: **"Can I afford to spend X on Y?"** with nuanced responses:
- "Yes you can"
- "Yes, but you will save less"
- "No, you will run out of money before your next payday"

This requires understanding **three dimensions**:
1. **Commitment level** - What MUST you spend vs what CAN you adjust?
2. **Time horizon** - When is money due vs when does income arrive?
3. **Priority** - What gets cut first when there's not enough?

---

## Established Frameworks

### 1. The 50/30/20 Rule (Elizabeth Warren)

The simplest principled hierarchy:

| Level | % of Income | Description |
|-------|-------------|-------------|
| **Needs** | 50% | Essential for survival/function |
| **Wants** | 30% | Quality of life, discretionary |
| **Savings** | 20% | Future self, debt paydown |

**Pros**: Simple, intuitive
**Cons**: The line between "need" and "want" is blurry (is internet a need? Depends on your job)

### 2. YNAB's Category Philosophy

YNAB uses a more nuanced hierarchy:

```
├── Immediate Obligations (bills that never fail)
│   ├── Rent/Mortgage
│   ├── Utilities
│   ├── Insurance (monthly)
│   └── Minimum debt payments
├── True Expenses (predictable but irregular)
│   ├── Annual insurance premiums
│   ├── Car maintenance
│   ├── Holiday gifts
│   └── Medical expenses
├── Quality of Life Goals
│   ├── Vacation fund
│   ├── Education
│   └── Home improvement
└── Just for Fun
    ├── Dining out
    ├── Entertainment
    └── Hobbies
```

**Key insight**: "True Expenses" acknowledges that some costs are predictable but not monthly - you need to save $100/month for a $1200 annual insurance premium.

### 3. Fixed / Variable / Discretionary Model

Categorizes by **flexibility**, not importance:

| Type | Definition | Examples |
|------|------------|----------|
| **Fixed** | Same amount every period, contractual | Rent, loan payments, subscriptions |
| **Variable Essential** | Necessary but amount varies | Groceries, utilities, gas |
| **Variable Discretionary** | Optional and amount varies | Dining out, entertainment |
| **Periodic** | Predictable but not monthly | Insurance, taxes, maintenance |

### 4. Mental Accounting (Behavioral Economics)

Richard Thaler's research shows people naturally create mental "buckets" for money. This is actually useful - it prevents overspending by creating artificial constraints.

**Key insight**: A good category system should work WITH human psychology, not against it. People naturally think in buckets.

---

## Recommended 5-Level Commitment Hierarchy

Based on the research, here's a hierarchy designed specifically to answer affordability questions:

### Level 0: Survival Baseline (Non-Negotiable)
These are expenses where failure to pay has severe consequences:
- Housing (eviction risk)
- Basic utilities (water, electricity for safety)
- Essential food
- Required medications
- Minimum debt payments (credit score, legal)
- Transportation to work (income-protecting)

**Property**: Cannot be reduced without serious life disruption

### Level 1: Committed Obligations (Hard to Change)
Contractual or near-contractual:
- Insurance premiums
- Phone/internet (if needed for work)
- Childcare
- Regular medical needs
- Debt payments above minimum

**Property**: Could be reduced but requires significant effort/time

### Level 2: Standard of Living (Adjustable with Effort)
Normal life expenses that could be trimmed:
- Grocery quality (organic vs regular)
- Utility usage (AC/heating comfort)
- Transportation convenience (Uber vs bus)
- Personal care (haircuts, gym)

**Property**: Can be reduced with lifestyle adjustment

### Level 3: Discretionary (Easily Adjustable)
Pure wants:
- Dining out
- Entertainment/subscriptions
- Hobbies
- Shopping beyond needs
- Vacations

**Property**: Can be cut immediately without hardship

### Level 4: Savings Goals (Flexible but Important)
Your future self:
- Emergency fund contributions
- Retirement contributions
- Other savings goals

**Property**: Skipping hurts future, not present

---

## Affordability Algorithm

### Required Data Points

```
INPUTS:
├── current_balance          # Cash + checking available now
├── next_payday_date         # When income arrives
├── next_payday_amount       # Expected income
├── days_until_payday        # Calculated from today
│
├── committed_expenses[]     # Expenses due before payday
│   ├── amount
│   ├── due_date
│   └── commitment_level (0, 1)
│
├── expected_spending        # Typical L2/L3 spending per day
├── savings_goal_this_period # What user planned to save
└── minimum_safe_balance     # Buffer (e.g., $100 to avoid overdraft)
```

### The Algorithm

```python
def can_i_afford(purchase_amount: Decimal) -> AffordabilityResult:

    # Step 1: Calculate committed costs until payday
    committed_until_payday = sum(
        expense.amount
        for expense in committed_expenses
        if expense.due_date <= next_payday_date
        and expense.commitment_level in [0, 1]  # Survival + Committed only
    )

    # Step 2: Estimate variable essential spending (L2)
    estimated_lifestyle_spending = (
        daily_average_l2_spending * days_until_payday
    )

    # Step 3: Calculate what's truly available
    available_for_discretionary = (
        current_balance
        - committed_until_payday
        - estimated_lifestyle_spending
        - minimum_safe_balance
    )

    # Step 4: Account for savings goal
    available_after_savings = (
        available_for_discretionary - savings_goal_this_period
    )

    # Step 5: Decision logic
    if purchase_amount <= available_after_savings:
        return AffordabilityResult(
            verdict="YES",
            message="You can afford this purchase",
            impact_on_savings=0,
            remaining_discretionary=available_after_savings - purchase_amount
        )

    elif purchase_amount <= available_for_discretionary:
        savings_reduction = purchase_amount - available_after_savings
        return AffordabilityResult(
            verdict="YES_WITH_TRADEOFF",
            message=f"Yes, but you'll save ${savings_reduction:.2f} less",
            impact_on_savings=savings_reduction,
            remaining_discretionary=0
        )

    elif purchase_amount <= current_balance - committed_until_payday - minimum_safe_balance:
        lifestyle_cut_needed = purchase_amount - available_for_discretionary
        return AffordabilityResult(
            verdict="POSSIBLE_WITH_SACRIFICE",
            message=f"Possible, but you'll need to cut ${lifestyle_cut_needed:.2f} from lifestyle spending",
            impact_on_savings=savings_goal_this_period,
            lifestyle_adjustment=lifestyle_cut_needed
        )

    else:
        shortfall = (
            purchase_amount
            - (current_balance - committed_until_payday - minimum_safe_balance)
        )
        return AffordabilityResult(
            verdict="NO",
            message=f"No, you'd be ${shortfall:.2f} short before payday",
            shortfall=shortfall,
            suggestion=f"Wait {days_until_payday} days, or find ${shortfall:.2f} elsewhere"
        )
```

### Financial Runway Calculation

```python
def calculate_runway() -> RunwayResult:
    # Daily burn rate = (L0 + L1 + typical L2) / 30
    monthly_committed = sum(
        expense.monthly_equivalent()
        for expense in all_expenses
        if expense.commitment_level in [0, 1]
    )
    monthly_lifestyle = average_monthly_l2_spending

    daily_burn = (monthly_committed + monthly_lifestyle) / 30

    available = current_balance - minimum_safe_balance
    runway_days = available / daily_burn

    return RunwayResult(
        days=runway_days,
        daily_burn=daily_burn,
        message=f"At current pace, you have {runway_days:.0f} days of runway"
    )
```

---

## Complete Category Hierarchy

```
LEVEL 0: SURVIVAL (Non-negotiable essentials)
─────────────────────────────────────────────
├── Housing
│   ├── Rent
│   ├── Mortgage Principal + Interest
│   ├── Property Tax (if escrowed)
│   ├── HOA Fees (if required)
│   └── Renter's Insurance (if required by lease)
│
├── Utilities - Basic
│   ├── Electricity
│   ├── Gas / Heating
│   ├── Water & Sewer
│   └── Trash Collection
│
├── Food - Baseline
│   └── Groceries (basic nutrition)
│
├── Healthcare - Essential
│   ├── Health Insurance Premium
│   ├── Required Medications
│   └── Critical Medical Supplies
│
├── Transportation - Work
│   ├── Public Transit Pass
│   ├── Gas (commute only)
│   ├── Car Payment (if no alternative)
│   └── Required Parking
│
└── Debt - Minimums
    ├── Credit Card Minimum Payments
    ├── Student Loan Minimums
    └── Other Loan Minimums


LEVEL 1: COMMITTED (Contractual, hard to change)
────────────────────────────────────────────────
├── Insurance
│   ├── Auto Insurance
│   ├── Life Insurance
│   ├── Home / Renter's Insurance (if not in L0)
│   ├── Umbrella Insurance
│   └── Disability Insurance
│
├── Communication
│   ├── Mobile Phone
│   ├── Internet (if work-required)
│   └── Landline (if any)
│
├── Childcare / Dependents
│   ├── Daycare / Preschool
│   ├── After-school Care
│   ├── Child Support (if applicable)
│   └── Elder Care
│
├── Pets - Essential
│   ├── Pet Food
│   ├── Veterinary Care (routine)
│   └── Pet Insurance
│
├── Subscriptions - Required
│   ├── Work Software
│   ├── Professional Memberships
│   └── Security Systems
│
└── Debt - Above Minimum
    ├── Extra Credit Card Payments
    ├── Extra Student Loan Payments
    └── Extra Mortgage Payments


LEVEL 2: LIFESTYLE (Adjustable with effort)
───────────────────────────────────────────
├── Food - Quality
│   ├── Groceries (upgraded: organic, specialty)
│   ├── Coffee / Snacks
│   └── Alcohol (home)
│
├── Transportation - Comfort
│   ├── Rideshare / Taxi
│   ├── Gas (non-commute)
│   ├── Car Maintenance
│   ├── Car Wash
│   └── Parking (discretionary)
│
├── Personal Care
│   ├── Haircuts / Salon
│   ├── Gym / Fitness
│   ├── Spa / Massage
│   └── Cosmetics / Toiletries (beyond basic)
│
├── Home Maintenance
│   ├── Cleaning Supplies
│   ├── Lawn / Garden
│   ├── Minor Repairs
│   ├── Home Improvement
│   └── Furniture / Decor
│
├── Clothing
│   ├── Work Clothes
│   ├── Casual Clothes
│   ├── Shoes
│   └── Accessories
│
├── Education
│   ├── Books / Learning Materials
│   ├── Courses / Training
│   └── School Supplies (kids)
│
└── Healthcare - Elective
    ├── Dental (beyond covered)
    ├── Vision / Glasses
    ├── Therapy / Mental Health
    └── Supplements / Vitamins


LEVEL 3: DISCRETIONARY (Easily cut)
───────────────────────────────────
├── Dining Out
│   ├── Restaurants
│   ├── Fast Food
│   ├── Coffee Shops
│   ├── Bars
│   └── Delivery / Takeout
│
├── Entertainment
│   ├── Streaming Services
│   ├── Movies / Theater
│   ├── Concerts / Events
│   ├── Sports (attending)
│   ├── Video Games
│   └── Books / Music / Apps
│
├── Hobbies
│   ├── Sports / Recreation (participating)
│   ├── Arts / Crafts
│   ├── Photography
│   ├── Outdoor Activities
│   └── Collections
│
├── Shopping
│   ├── Electronics / Gadgets
│   ├── Home Goods (non-essential)
│   └── General Shopping
│
├── Gifts
│   ├── Birthday Gifts
│   ├── Holiday Gifts
│   ├── Wedding / Baby Gifts
│   └── Charitable Donations
│
└── Travel / Vacation
    ├── Flights
    ├── Hotels / Lodging
    ├── Rental Cars
    ├── Activities / Tours
    └── Travel Food / Souvenirs


LEVEL 4: FUTURE (Savings & Goals)
─────────────────────────────────
├── Emergency Fund
│   └── Target: 3-6 months expenses
│
├── Retirement
│   ├── 401(k) / Pension
│   ├── IRA / Roth IRA
│   └── Other Retirement
│
├── Sinking Funds (Periodic Expenses)
│   ├── Annual Insurance Premiums
│   ├── Property Tax (if not escrowed)
│   ├── Vehicle Registration
│   ├── Holiday Spending
│   ├── Annual Subscriptions
│   └── Planned Large Purchases
│
└── Goals
    ├── House Down Payment
    ├── Car Fund
    ├── Education Fund
    ├── Wedding Fund
    ├── Vacation Fund
    └── Other Goals
```

---

## Edge Cases

### 1. Credit Card Spending
**Recommended**: `Available = Cash_Balance - Credit_Card_Balance_Owed`
Credit card spending IS spending - available credit is not your money.

### 2. Joint Accounts / Couples
Support "Yours/Mine/Ours" model with proportional contribution option based on income ratios.

### 3. Irregular / Variable Income
Use "Pay yourself a salary" model: Variable income → Buffer account → Fixed "salary" → Personal account

### 4. Pending Transactions
Always deduct pending outflows; don't count pending inflows until posted.

### 5. Variable Recurring Expenses
Use rolling average + seasonal awareness; take higher of average or last month.

### 6. Sinking Funds
Treat monthly contributions as L1 committed - the $1200 insurance bill IS coming.

### 7. Windfalls
Prompt for allocation split (savings/sinking/discretionary).

### 8. Overdraft Protection
NEVER include in available - it's debt, not money.

---

## Sources

- [Citizens Bank - 50/30/20 Rule](https://www.citizensbank.com/learning/50-30-20-budget.aspx)
- [YNAB - The Four Rules](https://www.youneedabudget.com/the-four-rules/)
- [YNAB - Category Structure](https://www.ynab.com/blog/how-many-ynab-categories)
- [The Decision Lab - Mental Accounting](https://thedecisionlab.com/biases/mental-accounting)
- [Empower - Fixed vs Variable Expenses](https://www.empower.com/the-currency/play/variable-expenses)
- [CalendarBudget - Sinking Funds](https://calendarbudget.com/sinking-funds-the-secret-to-stress-free-budgeting-for-irregular-expenses/)
- [Expense Sorted - Financial Runway](https://www.expensesorted.com/blog/financial-runway-calculator-how-long-without-income)
- [NerdWallet - Zero-Based Budgeting](https://www.nerdwallet.com/finance/learn/zero-based-budgeting-explained)
- [Wikipedia - Mental Accounting](https://en.wikipedia.org/wiki/Mental_accounting)
- [Monarch Money - 23 Budget Categories](https://www.monarch.com/blog/the-23-budget-categories-you-need-in-your-budget)
- [Tiller - Budget Categories](https://tiller.com/budget-categories/)
- [PocketGuard - Category Guide](https://pocketguard.com/blog/budget-categories-101-what-they-are-how-many-should-you-have/)
- [Copilot Money - Category Groups](https://help.copilot.money/en/articles/3767655-groups-of-categories)
