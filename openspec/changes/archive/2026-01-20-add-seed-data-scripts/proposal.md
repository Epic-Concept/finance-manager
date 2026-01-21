# Change: Add seed data scripts for local development

## Why
Developers need a way to populate the local SQL Server database with real data from CSV files for feature development and manual testing. This data is sensitive and should not be committed to the repository.

## What Changes
- Add `data/` folder to `.gitignore` to prevent accidental commits of real financial data
- Create a Python CLI script to load CSV data into the local database
- Support loading `purchases.csv` into `online_purchases` table
- Support loading `bank_transactions.csv` into `transactions` table
- Add Makefile targets for easy data seeding operations

## Impact
- Affected specs: `local-database` (new requirements for data seeding)
- Affected code: 
  - `.gitignore` (add data/ exclusion)
  - `apps/api/src/finance_api/scripts/` (new seed data module)
  - `Makefile` (new seed targets)
