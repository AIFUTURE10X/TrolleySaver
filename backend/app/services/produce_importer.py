"""
Fresh Foods Importer Service

Imports fresh foods (fruit & vegetables, meat & seafood) from store APIs.
Runs daily to keep prices up-to-date.

Unlike specials which change weekly, fresh food prices can change daily,
so this runs more frequently.
"""
import logging
from datetime import datetime
from typing import Optional

from app.database import SessionLocal
from app.models import Store, Product, StoreProduct, Price, Category
from app.services.store_product_importer import StoreProductImporter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Fresh food categories to import
FRESH_CATEGORIES = {
    "woolworths": {
        "fruit-veg": "Fruit & Vegetables",
        "meat-seafood": "Meat & Seafood",
    },
    "coles": {
        "fruit-vegetables": "Fruit & Vegetables",
        "meat-seafood": "Meat & Seafood",
    }
}


class FreshFoodsImporter:
    """
    Import fresh foods (produce and meat) from all supported stores.

    Uses the existing StoreProductImporter infrastructure but focuses
    specifically on fresh food categories.
    """

    def __init__(self):
        self.importer = StoreProductImporter()

    def import_all_fresh_foods(self, max_pages: int = 10) -> dict:
        """
        Import fresh foods from all stores.

        Args:
            max_pages: Maximum pages to fetch per store per category

        Returns:
            Summary of import results
        """
        results = {
            "woolworths": {"produce": 0, "meat": 0},
            "coles": {"produce": 0, "meat": 0},
            "total": 0,
            "timestamp": datetime.now().isoformat()
        }

        logger.info("Starting fresh foods import from all stores...")

        # Import Woolworths produce
        try:
            count = self.importer.import_woolworths_products(
                "fruit-veg", page_size=36, max_pages=max_pages
            )
            results["woolworths"]["produce"] = count
            results["total"] += count
            logger.info(f"Woolworths produce: {count} products")
        except Exception as e:
            logger.error(f"Error importing Woolworths produce: {e}")

        # Import Woolworths meat
        try:
            count = self.importer.import_woolworths_products(
                "meat-seafood", page_size=36, max_pages=max_pages
            )
            results["woolworths"]["meat"] = count
            results["total"] += count
            logger.info(f"Woolworths meat: {count} products")
        except Exception as e:
            logger.error(f"Error importing Woolworths meat: {e}")

        # Import Coles produce
        try:
            count = self.importer.import_coles_products(
                "fruit-vegetables", max_pages=max_pages
            )
            results["coles"]["produce"] = count
            results["total"] += count
            logger.info(f"Coles produce: {count} products")
        except Exception as e:
            logger.error(f"Error importing Coles produce: {e}")

        # Import Coles meat
        try:
            count = self.importer.import_coles_products(
                "meat-seafood", max_pages=max_pages
            )
            results["coles"]["meat"] = count
            results["total"] += count
            logger.info(f"Coles meat: {count} products")
        except Exception as e:
            logger.error(f"Error importing Coles meat: {e}")

        logger.info(f"Fresh foods import complete. Total: {results['total']} products")
        return results

    def import_produce_only(self, max_pages: int = 10) -> dict:
        """Import just produce (fruit & veg)."""
        results = {"woolworths": 0, "coles": 0, "total": 0}

        try:
            results["woolworths"] = self.importer.import_woolworths_products(
                "fruit-veg", page_size=36, max_pages=max_pages
            )
            results["total"] += results["woolworths"]
        except Exception as e:
            logger.error(f"Error importing Woolworths produce: {e}")

        try:
            results["coles"] = self.importer.import_coles_products(
                "fruit-vegetables", max_pages=max_pages
            )
            results["total"] += results["coles"]
        except Exception as e:
            logger.error(f"Error importing Coles produce: {e}")

        return results

    def import_meat_only(self, max_pages: int = 10) -> dict:
        """Import just meat & seafood."""
        results = {"woolworths": 0, "coles": 0, "total": 0}

        try:
            results["woolworths"] = self.importer.import_woolworths_products(
                "meat-seafood", page_size=36, max_pages=max_pages
            )
            results["total"] += results["woolworths"]
        except Exception as e:
            logger.error(f"Error importing Woolworths meat: {e}")

        try:
            results["coles"] = self.importer.import_coles_products(
                "meat-seafood", max_pages=max_pages
            )
            results["total"] += results["coles"]
        except Exception as e:
            logger.error(f"Error importing Coles meat: {e}")

        return results

    def get_fresh_foods_summary(self) -> dict:
        """
        Get a summary of fresh foods data in the database.

        Returns:
            Summary statistics
        """
        db = SessionLocal()
        try:
            summary = {
                "produce": {"total": 0, "by_store": {}},
                "meat": {"total": 0, "by_store": {}},
            }

            stores = db.query(Store).all()

            # Find produce categories
            produce_cats = db.query(Category).filter(
                Category.slug.in_(["fruit-veg", "fruit-vegetables"])
            ).all()
            produce_ids = [c.id for c in produce_cats]

            # Find meat categories
            meat_cats = db.query(Category).filter(
                Category.slug.in_(["meat-seafood", "poultry-meat-seafood"])
            ).all()
            meat_ids = [c.id for c in meat_cats]

            for store in stores:
                # Count produce
                if produce_ids:
                    produce_count = db.query(StoreProduct).join(Product).filter(
                        Product.category_id.in_(produce_ids),
                        StoreProduct.store_id == store.id
                    ).count()
                    if produce_count > 0:
                        summary["produce"]["by_store"][store.name] = produce_count
                        summary["produce"]["total"] += produce_count

                # Count meat
                if meat_ids:
                    meat_count = db.query(StoreProduct).join(Product).filter(
                        Product.category_id.in_(meat_ids),
                        StoreProduct.store_id == store.id
                    ).count()
                    if meat_count > 0:
                        summary["meat"]["by_store"][store.name] = meat_count
                        summary["meat"]["total"] += meat_count

            return summary
        finally:
            db.close()


# Backward compatibility alias
ProduceImporter = FreshFoodsImporter


def run_fresh_foods_import():
    """Entry point for scheduler to run fresh foods import."""
    importer = FreshFoodsImporter()
    return importer.import_all_fresh_foods()


# CLI interface
if __name__ == "__main__":
    import sys

    importer = FreshFoodsImporter()

    if len(sys.argv) > 1:
        if sys.argv[1] == "--summary":
            print("Fresh Foods Summary:")
            summary = importer.get_fresh_foods_summary()
            print(f"  Produce: {summary['produce']}")
            print(f"  Meat: {summary['meat']}")

        elif sys.argv[1] == "--produce":
            pages = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            print(f"Importing produce only ({pages} pages per store)...")
            results = importer.import_produce_only(max_pages=pages)
            print(f"Results: {results}")

        elif sys.argv[1] == "--meat":
            pages = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            print(f"Importing meat only ({pages} pages per store)...")
            results = importer.import_meat_only(max_pages=pages)
            print(f"Results: {results}")

        elif sys.argv[1] == "--quick":
            print("Quick import (3 pages per store per category)...")
            results = importer.import_all_fresh_foods(max_pages=3)
            print(f"Results: {results}")

        else:
            pages = int(sys.argv[1])
            print(f"Importing fresh foods ({pages} pages per store)...")
            results = importer.import_all_fresh_foods(max_pages=pages)
            print(f"Results: {results}")
    else:
        print("Usage:")
        print("  python -m app.services.produce_importer --quick")
        print("  python -m app.services.produce_importer --produce [pages]")
        print("  python -m app.services.produce_importer --meat [pages]")
        print("  python -m app.services.produce_importer --summary")
        print("  python -m app.services.produce_importer <pages>")
