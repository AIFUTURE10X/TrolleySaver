"""
Re-categorize Products Script

Re-runs the auto-categorizer on all existing specials to update their category_id
based on the improved categorization rules.

Run with: python -m scripts.recategorize_products
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import sessionmaker
from app.database import engine
from app.models import Special, Category
from app.services.auto_categorizer import categorize_product


def recategorize_all_products():
    """Re-categorize all specials using updated auto-categorizer rules."""
    print("Re-categorizing all products...")
    print("=" * 60)

    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Get all categories for lookup
        categories = db.query(Category).all()
        category_lookup = {cat.slug: cat.id for cat in categories}
        category_names = {cat.slug: cat.name for cat in categories}

        print(f"Loaded {len(categories)} categories")

        # Get all specials
        specials = db.query(Special).all()
        total = len(specials)
        print(f"Found {total} specials to process")
        print("-" * 60)

        # Stats tracking
        stats = {
            "changed": 0,
            "unchanged": 0,
            "newly_categorized": 0,
            "uncategorized": 0,
            "changes_by_category": {},
        }

        for i, special in enumerate(specials, 1):
            # Get new category from auto-categorizer
            new_category_slug = categorize_product(special.name, special.brand)
            new_category_id = category_lookup.get(new_category_slug) if new_category_slug else None

            old_category_id = special.category_id

            if new_category_id != old_category_id:
                if old_category_id is None and new_category_id is not None:
                    stats["newly_categorized"] += 1
                    print(f"  NEW: '{special.name}' -> {category_names.get(new_category_slug, new_category_slug)}")
                elif old_category_id is not None and new_category_id is not None:
                    stats["changed"] += 1
                    # Find old category name
                    old_cat = db.query(Category).filter(Category.id == old_category_id).first()
                    old_name = old_cat.name if old_cat else "Unknown"
                    new_name = category_names.get(new_category_slug, new_category_slug)
                    print(f"  CHANGED: '{special.name}' from '{old_name}' -> '{new_name}'")

                    # Track changes by category
                    change_key = f"{old_name} -> {new_name}"
                    stats["changes_by_category"][change_key] = stats["changes_by_category"].get(change_key, 0) + 1
                elif new_category_id is None:
                    stats["uncategorized"] += 1

                # Update the category
                special.category_id = new_category_id
            else:
                stats["unchanged"] += 1

            # Progress indicator
            if i % 500 == 0:
                print(f"  Processed {i}/{total} products...")

        # Commit changes
        db.commit()
        print("-" * 60)
        print("\nRe-categorization complete!")
        print(f"\nStatistics:")
        print(f"  Total processed: {total}")
        print(f"  Changed: {stats['changed']}")
        print(f"  Newly categorized: {stats['newly_categorized']}")
        print(f"  Unchanged: {stats['unchanged']}")
        print(f"  Could not categorize: {stats['uncategorized']}")

        if stats["changes_by_category"]:
            print(f"\nCategory changes breakdown:")
            for change, count in sorted(stats["changes_by_category"].items(), key=lambda x: -x[1]):
                print(f"  {change}: {count}")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def preview_changes(limit=100):
    """Preview changes without actually applying them."""
    print(f"Previewing first {limit} category changes (dry run)...")
    print("=" * 60)

    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        categories = db.query(Category).all()
        category_lookup = {cat.slug: cat.id for cat in categories}
        category_names = {cat.slug: cat.name for cat in categories}
        id_to_name = {cat.id: cat.name for cat in categories}

        specials = db.query(Special).limit(limit * 10).all()
        changes_found = 0

        for special in specials:
            if changes_found >= limit:
                break

            new_category_slug = categorize_product(special.name, special.brand)
            new_category_id = category_lookup.get(new_category_slug) if new_category_slug else None

            if new_category_id != special.category_id:
                old_name = id_to_name.get(special.category_id, "None")
                new_name = category_names.get(new_category_slug, "None")
                print(f"  '{special.name}': {old_name} -> {new_name}")
                changes_found += 1

        print(f"\n{changes_found} changes would be made (showing first {limit})")

    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Re-categorize all products")
    parser.add_argument("--preview", action="store_true", help="Preview changes without applying")
    parser.add_argument("--limit", type=int, default=100, help="Limit for preview mode")
    args = parser.parse_args()

    if args.preview:
        preview_changes(args.limit)
    else:
        recategorize_all_products()
