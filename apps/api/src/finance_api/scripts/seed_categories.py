"""Seed categories script for populating the database with hierarchical categories."""

import argparse
import sys

from sqlalchemy import text

from finance_api.db.session import SessionLocal
from finance_api.repositories.category_repository import CategoryRepository

# Category hierarchy with commitment levels (0-4)
# 0=Survival, 1=Committed, 2=Lifestyle, 3=Discretionary, 4=Future
CATEGORY_HIERARCHY = [
    # LEVEL 0: SURVIVAL (Non-negotiable)
    {
        "name": "Housing",
        "commitment_level": 0,
        "frequency": "monthly",
        "children": [
            {"name": "Rent", "commitment_level": 0, "frequency": "monthly"},
            {"name": "Mortgage", "commitment_level": 0, "frequency": "monthly"},
            {"name": "Property Tax", "commitment_level": 0, "frequency": "annual"},
            {"name": "HOA Fees", "commitment_level": 0, "frequency": "monthly"},
        ],
    },
    {
        "name": "Utilities - Basic",
        "commitment_level": 0,
        "frequency": "monthly",
        "children": [
            {"name": "Electricity", "commitment_level": 0, "frequency": "monthly"},
            {"name": "Gas", "commitment_level": 0, "frequency": "monthly"},
            {"name": "Water", "commitment_level": 0, "frequency": "monthly"},
            {"name": "Trash", "commitment_level": 0, "frequency": "monthly"},
        ],
    },
    {
        "name": "Food - Baseline",
        "commitment_level": 0,
        "frequency": "weekly",
        "children": [
            {"name": "Groceries - Basic", "commitment_level": 0, "frequency": "weekly"},
        ],
    },
    {
        "name": "Healthcare - Essential",
        "commitment_level": 0,
        "frequency": "monthly",
        "children": [
            {"name": "Health Insurance", "commitment_level": 0, "frequency": "monthly"},
            {"name": "Medications", "commitment_level": 0, "frequency": "monthly"},
        ],
    },
    {
        "name": "Transportation - Work",
        "commitment_level": 0,
        "frequency": "monthly",
        "children": [
            {"name": "Public Transit", "commitment_level": 0, "frequency": "monthly"},
            {"name": "Gas - Commute", "commitment_level": 0, "frequency": "weekly"},
            {"name": "Car Payment", "commitment_level": 0, "frequency": "monthly"},
        ],
    },
    {
        "name": "Debt - Minimums",
        "commitment_level": 0,
        "frequency": "monthly",
        "children": [
            {"name": "Credit Card Minimum", "commitment_level": 0, "frequency": "monthly"},
            {"name": "Student Loan Minimum", "commitment_level": 0, "frequency": "monthly"},
            {"name": "Other Debt Minimum", "commitment_level": 0, "frequency": "monthly"},
        ],
    },
    # LEVEL 1: COMMITTED (Contractual)
    {
        "name": "Insurance",
        "commitment_level": 1,
        "frequency": "monthly",
        "children": [
            {"name": "Auto Insurance", "commitment_level": 1, "frequency": "monthly"},
            {"name": "Life Insurance", "commitment_level": 1, "frequency": "monthly"},
            {"name": "Home Insurance", "commitment_level": 1, "frequency": "annual"},
            {"name": "Disability Insurance", "commitment_level": 1, "frequency": "monthly"},
        ],
    },
    {
        "name": "Communication",
        "commitment_level": 1,
        "frequency": "monthly",
        "children": [
            {"name": "Mobile Phone", "commitment_level": 1, "frequency": "monthly"},
            {"name": "Internet", "commitment_level": 1, "frequency": "monthly"},
            {"name": "Landline", "commitment_level": 1, "frequency": "monthly"},
        ],
    },
    {
        "name": "Dependents",
        "commitment_level": 1,
        "frequency": "monthly",
        "children": [
            {"name": "Daycare", "commitment_level": 1, "frequency": "monthly"},
            {"name": "Elder Care", "commitment_level": 1, "frequency": "monthly"},
            {"name": "Child Support", "commitment_level": 1, "frequency": "monthly"},
        ],
    },
    {
        "name": "Pets - Essential",
        "commitment_level": 1,
        "frequency": "monthly",
        "children": [
            {"name": "Pet Food", "commitment_level": 1, "frequency": "monthly"},
            {"name": "Vet Bills", "commitment_level": 1, "frequency": "one-time"},
            {"name": "Pet Insurance", "commitment_level": 1, "frequency": "monthly"},
        ],
    },
    {
        "name": "Subscriptions - Required",
        "commitment_level": 1,
        "frequency": "monthly",
        "children": [
            {"name": "Work Software", "commitment_level": 1, "frequency": "monthly"},
            {"name": "Professional Memberships", "commitment_level": 1, "frequency": "annual"},
        ],
    },
    {
        "name": "Debt - Extra Payments",
        "commitment_level": 1,
        "frequency": "monthly",
        "children": [
            {"name": "Credit Card Extra", "commitment_level": 1, "frequency": "monthly"},
            {"name": "Loan Extra Payments", "commitment_level": 1, "frequency": "monthly"},
        ],
    },
    # LEVEL 2: LIFESTYLE (Adjustable)
    {
        "name": "Food - Quality",
        "commitment_level": 2,
        "frequency": "weekly",
        "children": [
            {"name": "Organic Groceries", "commitment_level": 2, "frequency": "weekly"},
            {"name": "Coffee", "commitment_level": 2, "frequency": "weekly"},
            {"name": "Alcohol", "commitment_level": 2, "frequency": "weekly"},
        ],
    },
    {
        "name": "Transportation - Comfort",
        "commitment_level": 2,
        "frequency": "monthly",
        "children": [
            {"name": "Rideshare", "commitment_level": 2, "frequency": "one-time"},
            {"name": "Car Maintenance", "commitment_level": 2, "frequency": "one-time"},
            {"name": "Parking", "commitment_level": 2, "frequency": "monthly"},
        ],
    },
    {
        "name": "Personal Care",
        "commitment_level": 2,
        "frequency": "monthly",
        "children": [
            {"name": "Haircuts", "commitment_level": 2, "frequency": "monthly"},
            {"name": "Gym Membership", "commitment_level": 2, "frequency": "monthly"},
            {"name": "Spa", "commitment_level": 2, "frequency": "one-time"},
            {"name": "Cosmetics", "commitment_level": 2, "frequency": "monthly"},
        ],
    },
    {
        "name": "Home Maintenance",
        "commitment_level": 2,
        "frequency": "one-time",
        "children": [
            {"name": "Repairs", "commitment_level": 2, "frequency": "one-time"},
            {"name": "Garden", "commitment_level": 2, "frequency": "monthly"},
            {"name": "Decor", "commitment_level": 2, "frequency": "one-time"},
            {"name": "Cleaning Supplies", "commitment_level": 2, "frequency": "monthly"},
        ],
    },
    {
        "name": "Clothing",
        "commitment_level": 2,
        "frequency": "one-time",
        "children": [
            {"name": "Work Clothing", "commitment_level": 2, "frequency": "one-time"},
            {"name": "Casual Clothing", "commitment_level": 2, "frequency": "one-time"},
            {"name": "Accessories", "commitment_level": 2, "frequency": "one-time"},
        ],
    },
    {
        "name": "Education",
        "commitment_level": 2,
        "frequency": "one-time",
        "children": [
            {"name": "Books", "commitment_level": 2, "frequency": "one-time"},
            {"name": "Online Courses", "commitment_level": 2, "frequency": "one-time"},
            {"name": "Workshops", "commitment_level": 2, "frequency": "one-time"},
        ],
    },
    {
        "name": "Healthcare - Elective",
        "commitment_level": 2,
        "frequency": "one-time",
        "children": [
            {"name": "Dental", "commitment_level": 2, "frequency": "annual"},
            {"name": "Therapy", "commitment_level": 2, "frequency": "monthly"},
            {"name": "Vision", "commitment_level": 2, "frequency": "annual"},
        ],
    },
    # LEVEL 3: DISCRETIONARY (Easily cut)
    {
        "name": "Dining Out",
        "commitment_level": 3,
        "frequency": "one-time",
        "children": [
            {"name": "Restaurants", "commitment_level": 3, "frequency": "one-time"},
            {"name": "Fast Food", "commitment_level": 3, "frequency": "one-time"},
            {"name": "Coffee Shops", "commitment_level": 3, "frequency": "one-time"},
            {"name": "Delivery", "commitment_level": 3, "frequency": "one-time"},
        ],
    },
    {
        "name": "Entertainment",
        "commitment_level": 3,
        "frequency": "monthly",
        "children": [
            {"name": "Streaming Services", "commitment_level": 3, "frequency": "monthly"},
            {"name": "Movies", "commitment_level": 3, "frequency": "one-time"},
            {"name": "Concerts", "commitment_level": 3, "frequency": "one-time"},
            {"name": "Games", "commitment_level": 3, "frequency": "one-time"},
        ],
    },
    {
        "name": "Hobbies",
        "commitment_level": 3,
        "frequency": "one-time",
        "children": [
            {"name": "Sports Equipment", "commitment_level": 3, "frequency": "one-time"},
            {"name": "Arts & Crafts", "commitment_level": 3, "frequency": "one-time"},
            {"name": "Outdoor Activities", "commitment_level": 3, "frequency": "one-time"},
        ],
    },
    {
        "name": "Shopping",
        "commitment_level": 3,
        "frequency": "one-time",
        "children": [
            {"name": "Electronics", "commitment_level": 3, "frequency": "one-time"},
            {"name": "General Shopping", "commitment_level": 3, "frequency": "one-time"},
            {"name": "Home Goods", "commitment_level": 3, "frequency": "one-time"},
        ],
    },
    {
        "name": "Gifts",
        "commitment_level": 3,
        "frequency": "one-time",
        "children": [
            {"name": "Birthday Gifts", "commitment_level": 3, "frequency": "one-time"},
            {"name": "Holiday Gifts", "commitment_level": 3, "frequency": "annual"},
            {"name": "Charitable Donations", "commitment_level": 3, "frequency": "one-time"},
        ],
    },
    {
        "name": "Travel",
        "commitment_level": 3,
        "frequency": "one-time",
        "children": [
            {"name": "Flights", "commitment_level": 3, "frequency": "one-time"},
            {"name": "Hotels", "commitment_level": 3, "frequency": "one-time"},
            {"name": "Vacation Activities", "commitment_level": 3, "frequency": "one-time"},
            {"name": "Travel Insurance", "commitment_level": 3, "frequency": "one-time"},
        ],
    },
    # LEVEL 4: FUTURE (Savings)
    {
        "name": "Emergency Fund",
        "commitment_level": 4,
        "frequency": "monthly",
        "children": [],
    },
    {
        "name": "Retirement",
        "commitment_level": 4,
        "frequency": "monthly",
        "children": [
            {"name": "401k", "commitment_level": 4, "frequency": "monthly"},
            {"name": "IRA", "commitment_level": 4, "frequency": "monthly"},
            {"name": "Pension", "commitment_level": 4, "frequency": "monthly"},
        ],
    },
    {
        "name": "Sinking Funds",
        "commitment_level": 4,
        "frequency": "monthly",
        "children": [
            {"name": "Annual Insurance", "commitment_level": 4, "frequency": "monthly"},
            {"name": "Annual Taxes", "commitment_level": 4, "frequency": "monthly"},
            {"name": "Car Replacement", "commitment_level": 4, "frequency": "monthly"},
        ],
    },
    {
        "name": "Savings Goals",
        "commitment_level": 4,
        "frequency": "monthly",
        "children": [
            {"name": "House Down Payment", "commitment_level": 4, "frequency": "monthly"},
            {"name": "New Car", "commitment_level": 4, "frequency": "monthly"},
            {"name": "Education Fund", "commitment_level": 4, "frequency": "monthly"},
            {"name": "Vacation Fund", "commitment_level": 4, "frequency": "monthly"},
        ],
    },
]


def seed_categories(clear: bool = False) -> int:
    """Seed categories into the database.

    Args:
        clear: If True, delete existing categories before seeding.

    Returns:
        Number of categories created.
    """
    db = SessionLocal()
    try:
        repo = CategoryRepository(db)

        if clear:
            # Delete closure table first due to foreign keys
            db.execute(text("DELETE FROM finance.category_closure"))
            db.execute(text("DELETE FROM finance.categories"))
            db.commit()
            print("Cleared existing categories")

        created_count = 0

        def create_category_tree(categories: list, parent_id: int | None = None) -> int:
            """Recursively create categories and their children."""
            count = 0
            for cat_data in categories:
                category = repo.create(
                    name=cat_data["name"],
                    parent_id=parent_id,
                    description=None,
                    commitment_level=cat_data.get("commitment_level"),
                    frequency=cat_data.get("frequency"),
                    is_essential=False,
                )
                count += 1
                print(f"  Created: {cat_data['name']} (level={cat_data.get('commitment_level')})")

                # Create children if any
                children = cat_data.get("children", [])
                if children:
                    count += create_category_tree(children, category.id)

            return count

        print("Creating categories...")
        created_count = create_category_tree(CATEGORY_HIERARCHY)
        db.commit()

        print(f"\nTotal categories created: {created_count}")
        return created_count

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def main() -> int:
    """CLI entrypoint for seed categories script."""
    parser = argparse.ArgumentParser(
        description="Seed the database with hierarchical categories."
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing categories before seeding",
    )

    args = parser.parse_args()

    try:
        seed_categories(clear=args.clear)
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
