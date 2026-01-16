"""
Categorize Existing Products Script

Backfills category_id for existing specials using auto-categorization.
Run with: python -m scripts.categorize_existing
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import sessionmaker
from app.database import engine
from app.models import Special, Category
from app.services.auto_categorizer import categorize_product


def categorize_existing():
    """Categorize existing specials using auto-categorization."""
    print("Categorizing existing specials...")

    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Build category slug -> id mapping (include ALL categories - parents and subcategories)
        categories = db.query(Category).all()
        category_map = {c.slug: c.id for c in categories}

        print(f"Loaded {len(category_map)} categories (including subcategories)")

        # Get all specials without category_id
        specials = db.query(Special).filter(
            Special.category_id.is_(None)
        ).all()

        print(f"Found {len(specials)} specials to categorize")

        if not specials:
            print("All specials already have categories!")
            return

        categorized = 0
        uncategorized = 0
        by_category = {}

        for special in specials:
            # Auto-categorize based on product name and brand
            category_slug = categorize_product(special.name, special.brand)

            if category_slug and category_slug in category_map:
                special.category_id = category_map[category_slug]
                categorized += 1

                # Track counts by category
                by_category[category_slug] = by_category.get(category_slug, 0) + 1

                if categorized % 50 == 0:
                    print(f"  Processed {categorized}...")
                    db.commit()
            else:
                uncategorized += 1
                if uncategorized <= 10:
                    print(f"  Could not categorize: {special.name}")

        db.commit()

        # Print summary
        print(f"\nResults:")
        print(f"  Categorized: {categorized}")
        print(f"  Uncategorized: {uncategorized}")
        print(f"  Success rate: {categorized / (categorized + uncategorized) * 100:.1f}%")

        print(f"\nBy category:")
        for slug, count in sorted(by_category.items(), key=lambda x: -x[1]):
            print(f"  {slug}: {count}")

        # Show sample of uncategorized
        if uncategorized > 0:
            print(f"\nSample uncategorized products (first 10):")
            uncategorized_samples = db.query(Special).filter(
                Special.category_id.is_(None)
            ).limit(10).all()
            for s in uncategorized_samples:
                print(f"  - {s.name}")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def show_stats():
    """Show current categorization stats."""
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        total = db.query(Special).count()
        with_category = db.query(Special).filter(Special.category_id.isnot(None)).count()
        without_category = db.query(Special).filter(Special.category_id.is_(None)).count()

        print(f"Current stats:")
        print(f"  Total specials: {total}")
        print(f"  With category: {with_category}")
        print(f"  Without category: {without_category}")

    finally:
        db.close()


def recategorize_all():
    """Re-categorize ALL specials (including ones already categorized)."""
    print("Re-categorizing ALL specials...")

    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Build category slug -> id mapping (include ALL categories - parents and subcategories)
        categories = db.query(Category).all()
        category_map = {c.slug: c.id for c in categories}

        print(f"Loaded {len(category_map)} categories (including subcategories)")

        # Get ALL specials
        specials = db.query(Special).all()

        print(f"Found {len(specials)} specials to re-categorize")

        categorized = 0
        uncategorized = 0
        changed = 0
        by_category = {}

        for special in specials:
            old_category_id = special.category_id

            # Auto-categorize based on product name and brand
            category_slug = categorize_product(special.name, special.brand)

            if category_slug and category_slug in category_map:
                new_category_id = category_map[category_slug]
                if special.category_id != new_category_id:
                    special.category_id = new_category_id
                    changed += 1
                categorized += 1

                # Track counts by category
                by_category[category_slug] = by_category.get(category_slug, 0) + 1

                if categorized % 100 == 0:
                    print(f"  Processed {categorized}...")
                    db.commit()
            else:
                # Clear category if no longer matches
                if special.category_id is not None:
                    special.category_id = None
                    changed += 1
                uncategorized += 1

        db.commit()

        # Print summary
        print(f"\nResults:")
        print(f"  Categorized: {categorized}")
        print(f"  Uncategorized: {uncategorized}")
        print(f"  Changed: {changed}")
        print(f"  Success rate: {categorized / (categorized + uncategorized) * 100:.1f}%")

        print(f"\nBy category:")
        for slug, count in sorted(by_category.items(), key=lambda x: -x[1]):
            print(f"  {slug}: {count}")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--stats":
        show_stats()
    elif len(sys.argv) > 1 and sys.argv[1] == "--all":
        recategorize_all()
    else:
        categorize_existing()
