"""
Store Product Importer Service

Imports products directly from store websites with high-quality CDN images.
This populates the database with real products that can be compared across stores.
"""
import httpx
import logging
import asyncio
import re
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Store, Product, StoreProduct, Price, Category
from app.services.catalogue_parser import (
    get_woolworths_image_url,
    get_coles_image_url
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Woolworths category IDs (from their API)
WOOLWORTHS_CATEGORIES = {
    "fruit-veg": "1-E5BEE36E",
    "meat-seafood": "1-39FD4627",
    "dairy-eggs-fridge": "1-9E8D69DD",
    "bakery": "1-3AB8FAC3",
    "pantry": "1-6CDACB9E",
    "drinks": "1-7A77C9BB",
    "freezer": "1-9E0B6B5E",
    "health-beauty": "1-BD48B32D",
    "household": "1-73E6E7E7",
    "baby": "1-AB47EB5E",
    "pet": "1-E05F9A56",
}

# Coles category slugs
COLES_CATEGORIES = {
    "fruit-vegetables": "fruit-vegetables",
    "meat-seafood": "meat-seafood",
    "dairy-eggs-fridge": "dairy-eggs-fridge",
    "bakery": "bakery",
    "pantry": "pantry",
    "drinks": "drinks",
    "frozen": "frozen",
    "health-beauty": "health-beauty",
    "household": "household",
    "baby": "baby",
    "pet": "pet",
}


class StoreProductImporter:
    """Import products directly from store websites with images."""

    def __init__(self):
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-AU,en;q=0.9",
                "Origin": "https://www.woolworths.com.au",
                "Referer": "https://www.woolworths.com.au/",
            }
        )

    def import_woolworths_products(self, category_slug: str, page_size: int = 36, max_pages: int = 5) -> int:
        """
        Import products from a Woolworths category.

        Returns: Number of products imported
        """
        db = SessionLocal()
        try:
            store = db.query(Store).filter(Store.slug == "woolworths").first()
            if not store:
                logger.error("Woolworths store not found in database")
                return 0

            category_id = WOOLWORTHS_CATEGORIES.get(category_slug)
            if not category_id:
                logger.error(f"Unknown Woolworths category: {category_slug}")
                return 0

            # Get or create category
            category = self._get_or_create_category(db, category_slug)

            total_imported = 0

            for page in range(1, max_pages + 1):
                try:
                    # Woolworths Browse API
                    url = f"https://www.woolworths.com.au/apis/ui/browse/category"
                    params = {
                        "categoryId": category_id,
                        "pageNumber": page,
                        "pageSize": page_size,
                        "sortType": "TraderRelevance",
                        "url": f"/shop/browse/{category_slug}",
                        "location": "",
                        "formatObject": '{"name":""}',
                    }

                    response = self.client.get(url, params=params)

                    if response.status_code != 200:
                        logger.warning(f"Woolworths API returned {response.status_code}")
                        break

                    data = response.json()
                    bundles = data.get("Bundles", [])

                    if not bundles:
                        logger.info(f"No more products in category {category_slug}")
                        break

                    for bundle in bundles:
                        products = bundle.get("Products", [])
                        for prod_data in products:
                            imported = self._import_woolworths_product(
                                db, store, category, prod_data
                            )
                            if imported:
                                total_imported += 1

                    db.commit()
                    logger.info(f"Woolworths {category_slug} page {page}: imported {len(bundles)} bundles")

                    # Rate limiting
                    asyncio.run(asyncio.sleep(1))

                except Exception as e:
                    logger.error(f"Error fetching Woolworths page {page}: {e}")
                    break

            return total_imported

        finally:
            db.close()

    def _import_woolworths_product(
        self, db: Session, store: Store, category: Category, data: dict
    ) -> bool:
        """Import a single Woolworths product."""
        try:
            name = data.get("Name") or data.get("DisplayName")
            if not name:
                return False

            stockcode = str(data.get("Stockcode", ""))
            price = data.get("Price")
            was_price = data.get("WasPrice")
            cup_price = data.get("CupPrice")
            cup_measure = data.get("CupMeasure", "")
            package_size = data.get("PackageSize", "")
            brand = data.get("Brand", "")

            if not price or price <= 0:
                return False

            # Construct image URL
            image_url = get_woolworths_image_url(stockcode)

            # Find or create product
            product = db.query(Product).filter(
                Product.name.ilike(name)
            ).first()

            if not product:
                product = Product(
                    name=name,
                    brand=brand if brand else None,
                    category_id=category.id if category else None,
                    size=package_size if package_size else None,
                    image_url=image_url,
                    is_key_product=False,
                )
                db.add(product)
                db.flush()

            # Get or create store product
            store_product = db.query(StoreProduct).filter(
                StoreProduct.product_id == product.id,
                StoreProduct.store_id == store.id
            ).first()

            if not store_product:
                store_product = StoreProduct(
                    product_id=product.id,
                    store_id=store.id,
                    store_product_id=stockcode,
                    store_product_name=name,
                    image_url=image_url,
                )
                db.add(store_product)
                db.flush()
            elif not store_product.image_url:
                store_product.image_url = image_url

            # Add price record
            unit_price = None
            if cup_price:
                try:
                    unit_price = Decimal(str(cup_price))
                except:
                    pass

            price_record = Price(
                store_product_id=store_product.id,
                price=Decimal(str(price)),
                was_price=Decimal(str(was_price)) if was_price else None,
                unit_price=unit_price,
                is_special=was_price is not None and was_price > price,
                source="import",
            )
            db.add(price_record)

            return True

        except Exception as e:
            logger.debug(f"Error importing Woolworths product: {e}")
            return False

    def import_coles_products(self, category_slug: str, max_pages: int = 5) -> int:
        """
        Import products from a Coles category.

        Returns: Number of products imported
        """
        db = SessionLocal()
        try:
            store = db.query(Store).filter(Store.slug == "coles").first()
            if not store:
                logger.error("Coles store not found in database")
                return 0

            coles_category = COLES_CATEGORIES.get(category_slug)
            if not coles_category:
                logger.error(f"Unknown Coles category: {category_slug}")
                return 0

            # Get or create category
            category = self._get_or_create_category(db, category_slug)

            total_imported = 0

            for page in range(1, max_pages + 1):
                try:
                    # Coles category page
                    url = f"https://www.coles.com.au/browse/{coles_category}"
                    params = {"page": page}

                    response = self.client.get(url, params=params)

                    if response.status_code != 200:
                        logger.warning(f"Coles returned {response.status_code}")
                        break

                    # Extract __NEXT_DATA__ JSON
                    products = self._extract_coles_products(response.text)

                    if not products:
                        logger.info(f"No more products in Coles category {category_slug}")
                        break

                    for prod_data in products:
                        imported = self._import_coles_product(
                            db, store, category, prod_data
                        )
                        if imported:
                            total_imported += 1

                    db.commit()
                    logger.info(f"Coles {category_slug} page {page}: imported {len(products)} products")

                    # Rate limiting
                    asyncio.run(asyncio.sleep(1))

                except Exception as e:
                    logger.error(f"Error fetching Coles page {page}: {e}")
                    break

            return total_imported

        finally:
            db.close()

    def _extract_coles_products(self, html: str) -> list:
        """Extract products from Coles HTML page."""
        import json
        from bs4 import BeautifulSoup

        products = []

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Find __NEXT_DATA__ script
            script = soup.find('script', id='__NEXT_DATA__')
            if script:
                try:
                    data = json.loads(script.string)
                    props = data.get('props', {})
                    page_props = props.get('pageProps', {})

                    # Primary location: searchResults.results
                    if 'searchResults' in page_props:
                        search_results = page_props['searchResults']
                        if 'results' in search_results:
                            products.extend(search_results['results'])

                    # Fallback: initialState.search.results
                    if not products and 'initialState' in page_props:
                        state = page_props['initialState']
                        if 'search' in state:
                            results = state['search'].get('results', [])
                            products.extend(results)

                    # Fallback: direct products
                    if not products and 'products' in page_props:
                        products.extend(page_props['products'])

                except json.JSONDecodeError:
                    pass

        except Exception as e:
            logger.debug(f"Error extracting Coles products: {e}")

        return products

    def _import_coles_product(
        self, db: Session, store: Store, category: Category, data: dict
    ) -> bool:
        """Import a single Coles product."""
        try:
            name = data.get("name") or data.get("description")
            if not name:
                return False

            product_id = str(data.get("id", ""))
            brand = data.get("brand", "")
            package_size = data.get("size", "") or data.get("packageSize", "")

            # Extract pricing
            pricing = data.get("pricing", {})
            price = pricing.get("now") or pricing.get("price")
            was_price = pricing.get("was") or pricing.get("comparable")
            unit_price_str = pricing.get("unit", {}).get("price")

            if not price or price <= 0:
                return False

            # Construct image URL
            image_url = get_coles_image_url(product_id)

            # Find or create product
            product = db.query(Product).filter(
                Product.name.ilike(name)
            ).first()

            if not product:
                product = Product(
                    name=name,
                    brand=brand if brand else None,
                    category_id=category.id if category else None,
                    size=package_size if package_size else None,
                    image_url=image_url,
                    is_key_product=False,
                )
                db.add(product)
                db.flush()

            # Get or create store product
            store_product = db.query(StoreProduct).filter(
                StoreProduct.product_id == product.id,
                StoreProduct.store_id == store.id
            ).first()

            if not store_product:
                store_product = StoreProduct(
                    product_id=product.id,
                    store_id=store.id,
                    store_product_id=product_id,
                    store_product_name=name,
                    image_url=image_url,
                )
                db.add(store_product)
                db.flush()
            elif not store_product.image_url:
                store_product.image_url = image_url

            # Add price record
            unit_price = None
            if unit_price_str:
                try:
                    unit_price = Decimal(str(unit_price_str))
                except:
                    pass

            price_record = Price(
                store_product_id=store_product.id,
                price=Decimal(str(price)),
                was_price=Decimal(str(was_price)) if was_price else None,
                unit_price=unit_price,
                is_special=was_price is not None and was_price > price,
                source="import",
            )
            db.add(price_record)

            return True

        except Exception as e:
            logger.debug(f"Error importing Coles product: {e}")
            return False

    def _get_or_create_category(self, db: Session, slug: str) -> Optional[Category]:
        """Get or create a category by slug."""
        # First, try to find by slug (most reliable)
        category = db.query(Category).filter(Category.slug == slug).first()
        if category:
            return category

        # Map slugs to display names and alternate slugs
        category_mappings = {
            "fruit-veg": {"name": "Fruit & Veg", "alt_slugs": ["fruit-vegetables"]},
            "fruit-vegetables": {"name": "Fruit & Veg", "alt_slugs": ["fruit-veg"]},
            "meat-seafood": {"name": "Poultry, Meat & Seafood", "alt_slugs": []},
            "dairy-eggs-fridge": {"name": "Dairy, Eggs & Fridge", "alt_slugs": []},
            "bakery": {"name": "Bakery", "alt_slugs": []},
            "pantry": {"name": "Pantry", "alt_slugs": []},
            "drinks": {"name": "Drinks", "alt_slugs": []},
            "freezer": {"name": "Frozen", "alt_slugs": ["frozen"]},
            "frozen": {"name": "Frozen", "alt_slugs": ["freezer"]},
            "health-beauty": {"name": "Health & Beauty", "alt_slugs": []},
            "household": {"name": "Household", "alt_slugs": []},
            "baby": {"name": "Baby", "alt_slugs": []},
            "pet": {"name": "Pet", "alt_slugs": []},
        }

        mapping = category_mappings.get(slug, {"name": slug.replace("-", " ").title(), "alt_slugs": []})

        # Try alternate slugs
        for alt_slug in mapping["alt_slugs"]:
            category = db.query(Category).filter(Category.slug == alt_slug).first()
            if category:
                return category

        # Try by name (case insensitive)
        category = db.query(Category).filter(
            Category.name.ilike(mapping["name"])
        ).first()

        if not category:
            # Create new category
            category = Category(name=mapping["name"], slug=slug)
            db.add(category)
            db.flush()

        return category

    def import_all_categories(self, max_pages_per_category: int = 3) -> dict:
        """
        Import products from all categories across all stores.

        Returns: Summary of imports
        """
        results = {
            "woolworths": {},
            "coles": {},
            "total": 0
        }

        # Import from Woolworths
        logger.info("Starting Woolworths import...")
        for category_slug in WOOLWORTHS_CATEGORIES.keys():
            count = self.import_woolworths_products(
                category_slug,
                max_pages=max_pages_per_category
            )
            results["woolworths"][category_slug] = count
            results["total"] += count
            logger.info(f"Woolworths {category_slug}: {count} products")

        # Import from Coles
        logger.info("Starting Coles import...")
        for category_slug in COLES_CATEGORIES.keys():
            count = self.import_coles_products(
                category_slug,
                max_pages=max_pages_per_category
            )
            results["coles"][category_slug] = count
            results["total"] += count
            logger.info(f"Coles {category_slug}: {count} products")

        return results

    def quick_import(self, categories: list[str] = None, pages: int = 2) -> dict:
        """
        Quick import of key categories to populate the database.

        Default categories: dairy, pantry, drinks, meat
        """
        if categories is None:
            categories = ["dairy-eggs-fridge", "pantry", "drinks", "meat-seafood"]

        results = {"woolworths": {}, "coles": {}, "total": 0}

        for category in categories:
            # Import from Woolworths
            if category in WOOLWORTHS_CATEGORIES:
                count = self.import_woolworths_products(category, max_pages=pages)
                results["woolworths"][category] = count
                results["total"] += count

            # Import from Coles
            if category in COLES_CATEGORIES:
                count = self.import_coles_products(category, max_pages=pages)
                results["coles"][category] = count
                results["total"] += count

        return results

    def import_iga_products(self, search_terms: list[str] = None, max_per_term: int = 50) -> int:
        """
        Import products from IGA Shop API.

        Args:
            search_terms: List of search terms to fetch products
            max_per_term: Maximum products per search term

        Returns: Number of products imported
        """
        if search_terms is None:
            # Fresh produce search terms
            search_terms = [
                "banana", "apple", "orange", "grape", "strawberry", "mango", "avocado",
                "potato", "onion", "carrot", "tomato", "lettuce", "broccoli", "capsicum",
                "cucumber", "spinach", "mushroom", "celery", "corn", "beans",
                "chicken", "beef", "lamb", "pork", "mince", "sausage", "steak",
                "salmon", "fish", "prawns"
            ]

        db = SessionLocal()
        try:
            store = db.query(Store).filter(Store.slug == "iga").first()
            if not store:
                logger.error("IGA store not found in database")
                return 0

            # Get or create Fruit & Veg category
            category = self._get_or_create_category(db, "fruit-veg")

            total_imported = 0
            seen_products = set()  # Avoid duplicates

            store_id = "32600"  # Erskine Park IGA
            base_url = f"https://www.igashop.com.au/api/storefront/stores/{store_id}/search"

            for term in search_terms:
                try:
                    params = {"q": term, "take": max_per_term}
                    response = self.client.get(base_url, params=params)

                    if response.status_code != 200:
                        logger.warning(f"IGA API returned {response.status_code} for '{term}'")
                        continue

                    data = response.json()
                    items = data.get("items", [])

                    for item in items:
                        product_id = item.get("productId", "")
                        if product_id in seen_products:
                            continue
                        seen_products.add(product_id)

                        imported = self._import_iga_product(db, store, category, item)
                        if imported:
                            total_imported += 1

                    db.commit()
                    logger.info(f"IGA '{term}': found {len(items)} items")

                except Exception as e:
                    logger.error(f"Error fetching IGA products for '{term}': {e}")
                    continue

            return total_imported

        finally:
            db.close()

    def _import_iga_product(
        self, db: Session, store: Store, category: Category, data: dict
    ) -> bool:
        """Import a single IGA product."""
        try:
            name = data.get("name")
            if not name:
                return False

            product_id = data.get("productId", "")
            brand = data.get("brand", "")
            price_numeric = data.get("priceNumeric")

            if not price_numeric or price_numeric <= 0:
                return False

            # Get image URL
            image_data = data.get("image", {})
            image_url = image_data.get("default") if image_data else None

            # Get unit price
            unit_price_str = data.get("pricePerUnit", "")

            # Determine if it's fresh produce
            categories = data.get("categories", [])
            is_fresh = any(
                c.get("retailerId") in ["Fruit_and_Vegetable", "Fruit", "Vegetables", "Meat", "Seafood"]
                for c in categories
            )

            # Find or create product
            product = db.query(Product).filter(
                Product.name.ilike(name)
            ).first()

            if not product:
                product = Product(
                    name=name,
                    brand=brand if brand else None,
                    category_id=category.id if category else None,
                    image_url=image_url,
                    is_key_product=False,
                )
                db.add(product)
                db.flush()

            # Get or create store product
            store_product = db.query(StoreProduct).filter(
                StoreProduct.product_id == product.id,
                StoreProduct.store_id == store.id
            ).first()

            if not store_product:
                store_product = StoreProduct(
                    product_id=product.id,
                    store_id=store.id,
                    store_product_id=product_id,
                    store_product_name=name,
                    image_url=image_url,
                )
                db.add(store_product)
                db.flush()
            elif not store_product.image_url and image_url:
                store_product.image_url = image_url

            # Add price record
            unit_price = None
            if unit_price_str:
                # Parse unit price like "$4.90/kg"
                try:
                    price_part = unit_price_str.replace("$", "").split("/")[0]
                    unit_price = Decimal(price_part)
                except:
                    pass

            price_record = Price(
                store_product_id=store_product.id,
                price=Decimal(str(price_numeric)),
                unit_price=unit_price,
                is_special=data.get("priceSource") == "tpr",
                source="import",
            )
            db.add(price_record)

            return True

        except Exception as e:
            logger.debug(f"Error importing IGA product: {e}")
            return False


# CLI interface
if __name__ == "__main__":
    import sys

    importer = StoreProductImporter()

    if len(sys.argv) > 1:
        if sys.argv[1] == "--quick":
            print("Running quick import (key categories)...")
            results = importer.quick_import()
            print(f"\nImport complete!")
            print(f"Total products imported: {results['total']}")
            print(f"Woolworths: {results['woolworths']}")
            print(f"Coles: {results['coles']}")

        elif sys.argv[1] == "--full":
            print("Running full import (all categories)...")
            results = importer.import_all_categories()
            print(f"\nImport complete!")
            print(f"Total products imported: {results['total']}")

        elif sys.argv[1] == "--woolworths":
            category = sys.argv[2] if len(sys.argv) > 2 else "pantry"
            print(f"Importing Woolworths {category}...")
            count = importer.import_woolworths_products(category)
            print(f"Imported {count} products")

        elif sys.argv[1] == "--coles":
            category = sys.argv[2] if len(sys.argv) > 2 else "pantry"
            print(f"Importing Coles {category}...")
            count = importer.import_coles_products(category)
            print(f"Imported {count} products")

        elif sys.argv[1] == "--iga":
            print("Importing IGA fresh produce...")
            count = importer.import_iga_products()
            print(f"Imported {count} products")

        elif sys.argv[1] == "--all-fresh":
            print("Importing fresh produce from all stores...")
            results = {"woolworths": 0, "coles": 0, "iga": 0, "total": 0}

            # Woolworths
            print("\n=== Woolworths ===")
            count = importer.import_woolworths_products("fruit-veg", max_pages=5)
            results["woolworths"] = count
            results["total"] += count
            print(f"Woolworths: {count} products")

            # Coles
            print("\n=== Coles ===")
            count = importer.import_coles_products("fruit-vegetables", max_pages=5)
            results["coles"] = count
            results["total"] += count
            print(f"Coles: {count} products")

            # IGA
            print("\n=== IGA ===")
            count = importer.import_iga_products()
            results["iga"] = count
            results["total"] += count
            print(f"IGA: {count} products")

            print(f"\nTotal imported: {results['total']}")
            print(f"Results: {results}")

    else:
        print("Usage:")
        print("  python -m app.services.store_product_importer --quick")
        print("  python -m app.services.store_product_importer --full")
        print("  python -m app.services.store_product_importer --woolworths <category>")
        print("  python -m app.services.store_product_importer --coles <category>")
        print("  python -m app.services.store_product_importer --iga")
        print("  python -m app.services.store_product_importer --all-fresh")
        print("\nCategories: dairy-eggs-fridge, pantry, drinks, meat-seafood, fruit-veg, bakery, freezer, household")
