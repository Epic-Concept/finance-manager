-- Seed categories with hierarchical closure table
--
-- This script creates the category hierarchy based on a 5-level commitment model:
--   Level 0: SURVIVAL - Non-negotiable expenses (housing, utilities, food basics)
--   Level 1: COMMITTED - Contractual obligations (insurance, communication, childcare)
--   Level 2: LIFESTYLE - Adjustable quality-of-life expenses (quality food, personal care)
--   Level 3: DISCRETIONARY - Easily reducible expenses (dining out, entertainment, travel)
--   Level 4: FUTURE - Savings and investments (emergency fund, retirement, goals)
--
-- Usage:
--   docker exec finance-manager-db /opt/mssql-tools18/bin/sqlcmd \
--     -S localhost -U sa -P "Password123!" -C -d master \
--     -i /path/to/seed_categories.sql
--
-- Or copy into container first:
--   docker cp apps/api/scripts/sql/seed_categories.sql finance-manager-db:/tmp/
--   docker exec finance-manager-db /opt/mssql-tools18/bin/sqlcmd \
--     -S localhost -U sa -P "Password123!" -C -d master \
--     -i /tmp/seed_categories.sql

-- Clear existing data first
DELETE FROM finance.category_closure;
DELETE FROM finance.categories;

SET IDENTITY_INSERT finance.categories ON;

-- =============================================================================
-- LEVEL 0: SURVIVAL (Non-negotiable)
-- =============================================================================

-- Housing (1-5)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (1, 'Housing', NULL, 0, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (1, 1, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (2, 'Rent', 1, 0, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (2, 2, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (1, 2, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (3, 'Mortgage', 1, 0, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (3, 3, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (1, 3, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (4, 'Property Tax', 1, 0, 'annual', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (4, 4, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (1, 4, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (5, 'HOA Fees', 1, 0, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (5, 5, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (1, 5, 1);

-- Utilities - Basic (6-10)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (6, 'Utilities - Basic', NULL, 0, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (6, 6, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (7, 'Electricity', 6, 0, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (7, 7, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (6, 7, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (8, 'Gas', 6, 0, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (8, 8, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (6, 8, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (9, 'Water', 6, 0, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (9, 9, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (6, 9, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (10, 'Trash', 6, 0, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (10, 10, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (6, 10, 1);

-- Food - Baseline (11-12)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (11, 'Food - Baseline', NULL, 0, 'weekly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (11, 11, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (12, 'Groceries - Basic', 11, 0, 'weekly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (12, 12, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (11, 12, 1);

-- Healthcare - Essential (13-15)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (13, 'Healthcare - Essential', NULL, 0, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (13, 13, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (14, 'Health Insurance', 13, 0, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (14, 14, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (13, 14, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (15, 'Medications', 13, 0, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (15, 15, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (13, 15, 1);

-- Transportation - Work (16-19)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (16, 'Transportation - Work', NULL, 0, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (16, 16, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (17, 'Public Transit', 16, 0, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (17, 17, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (16, 17, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (18, 'Gas - Commute', 16, 0, 'weekly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (18, 18, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (16, 18, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (19, 'Car Payment', 16, 0, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (19, 19, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (16, 19, 1);

-- Debt - Minimums (20-23)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (20, 'Debt - Minimums', NULL, 0, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (20, 20, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (21, 'Credit Card Minimum', 20, 0, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (21, 21, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (20, 21, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (22, 'Student Loan Minimum', 20, 0, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (22, 22, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (20, 22, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (23, 'Other Debt Minimum', 20, 0, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (23, 23, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (20, 23, 1);

-- =============================================================================
-- LEVEL 1: COMMITTED (Contractual)
-- =============================================================================

-- Insurance (24-28)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (24, 'Insurance', NULL, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (24, 24, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (25, 'Auto Insurance', 24, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (25, 25, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (24, 25, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (26, 'Life Insurance', 24, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (26, 26, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (24, 26, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (27, 'Home Insurance', 24, 1, 'annual', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (27, 27, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (24, 27, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (28, 'Disability Insurance', 24, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (28, 28, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (24, 28, 1);

-- Communication (29-32)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (29, 'Communication', NULL, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (29, 29, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (30, 'Mobile Phone', 29, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (30, 30, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (29, 30, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (31, 'Internet', 29, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (31, 31, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (29, 31, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (32, 'Landline', 29, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (32, 32, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (29, 32, 1);

-- Dependents (33-36)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (33, 'Dependents', NULL, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (33, 33, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (34, 'Daycare', 33, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (34, 34, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (33, 34, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (35, 'Elder Care', 33, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (35, 35, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (33, 35, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (36, 'Child Support', 33, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (36, 36, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (33, 36, 1);

-- Pets - Essential (37-40)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (37, 'Pets - Essential', NULL, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (37, 37, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (38, 'Pet Food', 37, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (38, 38, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (37, 38, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (39, 'Vet Bills', 37, 1, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (39, 39, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (37, 39, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (40, 'Pet Insurance', 37, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (40, 40, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (37, 40, 1);

-- Subscriptions - Required (41-43)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (41, 'Subscriptions - Required', NULL, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (41, 41, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (42, 'Work Software', 41, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (42, 42, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (41, 42, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (43, 'Professional Memberships', 41, 1, 'annual', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (43, 43, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (41, 43, 1);

-- Debt - Extra Payments (44-46)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (44, 'Debt - Extra Payments', NULL, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (44, 44, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (45, 'Credit Card Extra', 44, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (45, 45, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (44, 45, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (46, 'Loan Extra Payments', 44, 1, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (46, 46, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (44, 46, 1);

-- =============================================================================
-- LEVEL 2: LIFESTYLE (Adjustable)
-- =============================================================================

-- Food - Quality (47-50)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (47, 'Food - Quality', NULL, 2, 'weekly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (47, 47, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (48, 'Organic Groceries', 47, 2, 'weekly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (48, 48, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (47, 48, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (49, 'Coffee', 47, 2, 'weekly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (49, 49, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (47, 49, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (50, 'Alcohol', 47, 2, 'weekly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (50, 50, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (47, 50, 1);

-- Transportation - Comfort (51-54)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (51, 'Transportation - Comfort', NULL, 2, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (51, 51, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (52, 'Rideshare', 51, 2, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (52, 52, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (51, 52, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (53, 'Car Maintenance', 51, 2, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (53, 53, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (51, 53, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (54, 'Parking', 51, 2, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (54, 54, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (51, 54, 1);

-- Personal Care (55-59)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (55, 'Personal Care', NULL, 2, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (55, 55, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (56, 'Haircuts', 55, 2, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (56, 56, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (55, 56, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (57, 'Gym Membership', 55, 2, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (57, 57, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (55, 57, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (58, 'Spa', 55, 2, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (58, 58, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (55, 58, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (59, 'Cosmetics', 55, 2, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (59, 59, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (55, 59, 1);

-- Home Maintenance (60-64)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (60, 'Home Maintenance', NULL, 2, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (60, 60, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (61, 'Repairs', 60, 2, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (61, 61, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (60, 61, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (62, 'Garden', 60, 2, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (62, 62, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (60, 62, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (63, 'Decor', 60, 2, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (63, 63, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (60, 63, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (64, 'Cleaning Supplies', 60, 2, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (64, 64, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (60, 64, 1);

-- Clothing (65-68)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (65, 'Clothing', NULL, 2, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (65, 65, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (66, 'Work Clothing', 65, 2, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (66, 66, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (65, 66, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (67, 'Casual Clothing', 65, 2, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (67, 67, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (65, 67, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (68, 'Accessories', 65, 2, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (68, 68, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (65, 68, 1);

-- Education (69-72)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (69, 'Education', NULL, 2, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (69, 69, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (70, 'Books', 69, 2, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (70, 70, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (69, 70, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (71, 'Online Courses', 69, 2, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (71, 71, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (69, 71, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (72, 'Workshops', 69, 2, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (72, 72, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (69, 72, 1);

-- Healthcare - Elective (73-76)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (73, 'Healthcare - Elective', NULL, 2, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (73, 73, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (74, 'Dental', 73, 2, 'annual', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (74, 74, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (73, 74, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (75, 'Therapy', 73, 2, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (75, 75, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (73, 75, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (76, 'Vision', 73, 2, 'annual', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (76, 76, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (73, 76, 1);

-- =============================================================================
-- LEVEL 3: DISCRETIONARY (Easily cut)
-- =============================================================================

-- Dining Out (77-81)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (77, 'Dining Out', NULL, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (77, 77, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (78, 'Restaurants', 77, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (78, 78, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (77, 78, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (79, 'Fast Food', 77, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (79, 79, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (77, 79, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (80, 'Coffee Shops', 77, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (80, 80, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (77, 80, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (81, 'Delivery', 77, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (81, 81, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (77, 81, 1);

-- Entertainment (82-86)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (82, 'Entertainment', NULL, 3, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (82, 82, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (83, 'Streaming Services', 82, 3, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (83, 83, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (82, 83, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (84, 'Movies', 82, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (84, 84, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (82, 84, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (85, 'Concerts', 82, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (85, 85, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (82, 85, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (86, 'Games', 82, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (86, 86, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (82, 86, 1);

-- Hobbies (87-90)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (87, 'Hobbies', NULL, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (87, 87, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (88, 'Sports Equipment', 87, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (88, 88, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (87, 88, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (89, 'Arts and Crafts', 87, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (89, 89, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (87, 89, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (90, 'Outdoor Activities', 87, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (90, 90, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (87, 90, 1);

-- Shopping (91-94)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (91, 'Shopping', NULL, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (91, 91, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (92, 'Electronics', 91, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (92, 92, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (91, 92, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (93, 'General Shopping', 91, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (93, 93, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (91, 93, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (94, 'Home Goods', 91, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (94, 94, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (91, 94, 1);

-- Gifts (95-98)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (95, 'Gifts', NULL, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (95, 95, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (96, 'Birthday Gifts', 95, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (96, 96, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (95, 96, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (97, 'Holiday Gifts', 95, 3, 'annual', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (97, 97, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (95, 97, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (98, 'Charitable Donations', 95, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (98, 98, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (95, 98, 1);

-- Travel (99-103)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (99, 'Travel', NULL, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (99, 99, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (100, 'Flights', 99, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (100, 100, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (99, 100, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (101, 'Hotels', 99, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (101, 101, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (99, 101, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (102, 'Vacation Activities', 99, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (102, 102, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (99, 102, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (103, 'Travel Insurance', 99, 3, 'one-time', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (103, 103, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (99, 103, 1);

-- =============================================================================
-- LEVEL 4: FUTURE (Savings)
-- =============================================================================

-- Emergency Fund (104)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (104, 'Emergency Fund', NULL, 4, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (104, 104, 0);

-- Retirement (105-108)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (105, 'Retirement', NULL, 4, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (105, 105, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (106, '401k', 105, 4, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (106, 106, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (105, 106, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (107, 'IRA', 105, 4, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (107, 107, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (105, 107, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (108, 'Pension', 105, 4, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (108, 108, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (105, 108, 1);

-- Sinking Funds (109-112)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (109, 'Sinking Funds', NULL, 4, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (109, 109, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (110, 'Annual Insurance', 109, 4, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (110, 110, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (109, 110, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (111, 'Annual Taxes', 109, 4, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (111, 111, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (109, 111, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (112, 'Car Replacement', 109, 4, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (112, 112, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (109, 112, 1);

-- Savings Goals (113-117)
INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (113, 'Savings Goals', NULL, 4, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (113, 113, 0);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (114, 'House Down Payment', 113, 4, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (114, 114, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (113, 114, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (115, 'New Car', 113, 4, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (115, 115, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (113, 115, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (116, 'Education Fund', 113, 4, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (116, 116, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (113, 116, 1);

INSERT INTO finance.categories (id, name, parent_id, commitment_level, frequency, is_essential, created_at, updated_at)
VALUES (117, 'Vacation Fund', 113, 4, 'monthly', 0, GETDATE(), GETDATE());
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (117, 117, 0);
INSERT INTO finance.category_closure (ancestor_id, descendant_id, depth) VALUES (113, 117, 1);

SET IDENTITY_INSERT finance.categories OFF;

-- =============================================================================
-- Summary
-- =============================================================================
SELECT 'Categories created: ' + CAST(COUNT(*) AS VARCHAR) AS summary FROM finance.categories;
SELECT 'Closure entries: ' + CAST(COUNT(*) AS VARCHAR) AS summary FROM finance.category_closure;
SELECT commitment_level, COUNT(*) as count FROM finance.categories GROUP BY commitment_level ORDER BY commitment_level;
