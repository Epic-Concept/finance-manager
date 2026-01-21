## 1. Git Configuration
- [x] 1.1 Add `data/` to `.gitignore`

## 2. Seed Data Script
- [x] 2.1 Create `apps/api/src/finance_api/scripts/` package with `__init__.py`
- [x] 2.2 Create `seed_data.py` module with CSV loading logic
- [x] 2.3 Implement `load_bank_transactions()` function to parse CSV and insert into `transactions` table
- [x] 2.4 Implement `load_purchases()` function to parse CSV and insert into `online_purchases` table
- [x] 2.5 Create CLI entrypoint with options to seed all data or specific tables
- [x] 2.6 Add `--clear` flag to truncate tables before seeding

## 3. Integration
- [x] 3.1 Register script entrypoint in `pyproject.toml`
- [x] 3.2 Add `make seed-data` target to Makefile
- [x] 3.3 Add `make seed-data-clear` target to clear and reseed
