"""
Catalogue Parser Service

Parses weekly specials from Australian supermarket catalogues.
Handles Woolworths, Coles, and ALDI.
"""
import httpx
import logging
from abc import ABC, abstractmethod
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Store, Product, StoreProduct, Price, Category

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============== Store CDN Image URL Helpers ==============

def get_woolworths_image_url(stockcode: str) -> str:
    """
    Construct Woolworths CDN image URL from stockcode.

    Verified pattern: https://cdn1.woolworths.media/content/wowproductimages/large/{STOCKCODE}.jpg
    """
    if not stockcode:
        return ""
    return f"https://cdn1.woolworths.media/content/wowproductimages/large/{stockcode}.jpg"


def get_coles_image_url(product_id: str) -> str:
    """
    Construct Coles CDN image URL from product ID.

    Verified pattern: https://productimages.coles.com.au/productimages/{FIRST_DIGIT}/{PRODUCT_ID}.jpg
    """
    if not product_id:
        return ""
    first_digit = product_id[0] if product_id else '0'
    return f"https://productimages.coles.com.au/productimages/{first_digit}/{product_id}.jpg"


def get_aldi_image_url(product_path: str) -> str:
    """
    Construct ALDI CDN image URL.

    Pattern: https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/400/{PRODUCT_PATH}
    """
    if not product_path:
        return ""
    return f"https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/{product_path}"


class SpecialItem:
    """Represents a single special/deal from a catalogue."""
    def __init__(
        self,
        name: str,
        price: Decimal,
        was_price: Optional[Decimal] = None,
        unit_price: Optional[Decimal] = None,
        special_type: Optional[str] = None,
        valid_from: Optional[date] = None,
        valid_to: Optional[date] = None,
        category: Optional[str] = None,
        image_url: Optional[str] = None,
        product_url: Optional[str] = None,
        store_product_id: Optional[str] = None
    ):
        self.name = name
        self.price = price
        self.was_price = was_price
        self.unit_price = unit_price
        self.special_type = special_type
        self.valid_from = valid_from
        self.valid_to = valid_to
        self.category = category
        self.image_url = image_url
        self.product_url = product_url
        self.store_product_id = store_product_id

    def __repr__(self):
        return f"SpecialItem({self.name}, ${self.price})"


class BaseCatalogueParser(ABC):
    """Base class for all catalogue parsers."""

    store_slug: str = ""
    store_name: str = ""

    def __init__(self):
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

    @abstractmethod
    def fetch_specials(self) -> list[SpecialItem]:
        """Fetch current specials from the catalogue. Override in subclass."""
        pass

    def save_specials(self, specials: list[SpecialItem], db: Session) -> int:
        """Save fetched specials to the database."""
        store = db.query(Store).filter(Store.slug == self.store_slug).first()
        if not store:
            logger.error(f"Store not found: {self.store_slug}")
            return 0

        saved_count = 0
        for special in specials:
            try:
                # Try to match with existing product
                product = self._match_product(special, db)

                if not product:
                    # Create new product if not found
                    product = Product(
                        name=special.name,
                        is_key_product=False,
                        image_url=special.image_url
                    )
                    db.add(product)
                    db.flush()
                    logger.info(f"Created new product: {special.name}")

                # Get or create store product
                store_product = db.query(StoreProduct).filter(
                    StoreProduct.product_id == product.id,
                    StoreProduct.store_id == store.id
                ).first()

                if not store_product:
                    store_product = StoreProduct(
                        product_id=product.id,
                        store_id=store.id,
                        store_product_id=special.store_product_id,
                        store_product_name=special.name,
                        product_url=special.product_url,
                        image_url=special.image_url  # Store CDN image
                    )
                    db.add(store_product)
                    db.flush()
                elif special.image_url and not store_product.image_url:
                    # Update image_url if not already set
                    store_product.image_url = special.image_url

                # Create price entry
                price = Price(
                    store_product_id=store_product.id,
                    price=special.price,
                    was_price=special.was_price,
                    unit_price=special.unit_price,
                    is_special=True,
                    special_type=special.special_type,
                    special_ends=special.valid_to,
                    source="catalogue",
                    valid_from=special.valid_from,
                    valid_to=special.valid_to
                )
                db.add(price)
                saved_count += 1

            except Exception as e:
                logger.error(f"Error saving special {special.name}: {e}")
                continue

        db.commit()
        return saved_count

    def _match_product(self, special: SpecialItem, db: Session) -> Optional[Product]:
        """Try to match a special with an existing product."""
        # Exact name match first
        product = db.query(Product).filter(
            Product.name.ilike(special.name)
        ).first()

        if product:
            return product

        # Try fuzzy matching on key products
        # Simple approach: check if special name contains product name or vice versa
        key_products = db.query(Product).filter(Product.is_key_product == True).all()

        special_lower = special.name.lower()
        for kp in key_products:
            kp_lower = kp.name.lower()
            # Check for substantial overlap
            if kp_lower in special_lower or special_lower in kp_lower:
                return kp
            # Check for key word matches (e.g., "milk 2l" matches "Full Cream Milk 2L")
            kp_words = set(kp_lower.split())
            special_words = set(special_lower.split())
            common = kp_words & special_words
            if len(common) >= 2:  # At least 2 words in common
                return kp

        return None

    def run(self) -> dict:
        """Run the parser and save results."""
        logger.info(f"Starting catalogue parse for {self.store_name}")

        try:
            specials = self.fetch_specials()
            logger.info(f"Fetched {len(specials)} specials from {self.store_name}")

            if specials:
                db = SessionLocal()
                try:
                    saved = self.save_specials(specials, db)
                    logger.info(f"Saved {saved} specials to database")
                    return {
                        "store": self.store_name,
                        "fetched": len(specials),
                        "saved": saved,
                        "status": "success"
                    }
                finally:
                    db.close()
            else:
                return {
                    "store": self.store_name,
                    "fetched": 0,
                    "saved": 0,
                    "status": "no_data"
                }

        except Exception as e:
            logger.error(f"Error parsing {self.store_name}: {e}")
            return {
                "store": self.store_name,
                "fetched": 0,
                "saved": 0,
                "status": "error",
                "error": str(e)
            }


class WoolworthsParser(BaseCatalogueParser):
    """Parser for Woolworths weekly specials."""

    store_slug = "woolworths"
    store_name = "Woolworths"

    # Woolworths specials API endpoint (discovered from network inspection)
    SPECIALS_URL = "https://www.woolworths.com.au/apis/ui/browse/category"
    SPECIALS_CATEGORY = "specials"

    def fetch_specials(self) -> list[SpecialItem]:
        """Fetch specials from Woolworths."""
        specials = []

        try:
            # Try the catalogue/specials page
            response = self.client.get(
                "https://www.woolworths.com.au/shop/browse/specials",
                headers={
                    "Accept": "text/html,application/xhtml+xml",
                }
            )

            if response.status_code == 200:
                specials = self._parse_specials_page(response.text)
            else:
                logger.warning(f"Woolworths returned status {response.status_code}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching Woolworths: {e}")
        except Exception as e:
            logger.error(f"Error fetching Woolworths: {e}")

        return specials

    def _parse_specials_page(self, html: str) -> list[SpecialItem]:
        """Parse the specials HTML page."""
        specials = []
        soup = BeautifulSoup(html, 'lxml')

        # Look for product tiles (this structure may change)
        # Woolworths uses React, so most data is loaded dynamically
        # Try to find any embedded JSON data
        scripts = soup.find_all('script', type='application/json')
        for script in scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict) and 'products' in data:
                    for prod in data['products']:
                        special = self._parse_product_json(prod)
                        if special:
                            specials.append(special)
            except:
                continue

        # Also try to find product cards in HTML
        product_cards = soup.select('[data-testid="product-tile"]')
        for card in product_cards:
            special = self._parse_product_card(card)
            if special:
                specials.append(special)

        return specials

    def _parse_product_json(self, data: dict) -> Optional[SpecialItem]:
        """Parse a product from JSON data."""
        try:
            name = data.get('name') or data.get('displayName') or data.get('Name')
            price = data.get('price') or data.get('salePrice') or data.get('Price')
            was_price = data.get('wasPrice') or data.get('listPrice') or data.get('WasPrice')
            stockcode = str(data.get('stockcode', '') or data.get('Stockcode', ''))

            if name and price:
                # Construct CDN image URL from stockcode
                image_url = get_woolworths_image_url(stockcode)

                return SpecialItem(
                    name=name,
                    price=Decimal(str(price)),
                    was_price=Decimal(str(was_price)) if was_price else None,
                    special_type="catalogue",
                    store_product_id=stockcode,
                    image_url=image_url  # Woolworths CDN image
                )
        except Exception as e:
            logger.debug(f"Error parsing product JSON: {e}")
        return None

    def _parse_product_card(self, card) -> Optional[SpecialItem]:
        """Parse a product from HTML card."""
        try:
            name_elem = card.select_one('[class*="product-title"]')
            price_elem = card.select_one('[class*="price"]')

            if name_elem and price_elem:
                name = name_elem.get_text(strip=True)
                price_text = price_elem.get_text(strip=True)
                # Extract price from text like "$4.50"
                import re
                price_match = re.search(r'\$?([\d.]+)', price_text)
                if price_match:
                    return SpecialItem(
                        name=name,
                        price=Decimal(price_match.group(1)),
                        special_type="catalogue"
                    )
        except Exception as e:
            logger.debug(f"Error parsing product card: {e}")
        return None


class ColesParser(BaseCatalogueParser):
    """Parser for Coles weekly specials."""

    store_slug = "coles"
    store_name = "Coles"

    def fetch_specials(self) -> list[SpecialItem]:
        """Fetch specials from Coles."""
        specials = []

        try:
            response = self.client.get(
                "https://www.coles.com.au/on-special",
                headers={
                    "Accept": "text/html,application/xhtml+xml",
                }
            )

            if response.status_code == 200:
                specials = self._parse_specials_page(response.text)
            else:
                logger.warning(f"Coles returned status {response.status_code}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching Coles: {e}")
        except Exception as e:
            logger.error(f"Error fetching Coles: {e}")

        return specials

    def _parse_specials_page(self, html: str) -> list[SpecialItem]:
        """Parse the Coles specials page."""
        specials = []
        soup = BeautifulSoup(html, 'lxml')

        # Try to find embedded JSON data
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and '__NEXT_DATA__' in str(script.string):
                try:
                    import json
                    # Extract JSON from Next.js data
                    json_text = script.string
                    data = json.loads(json_text)
                    products = self._extract_products_from_nextjs(data)
                    for prod in products:
                        special = self._parse_product_data(prod)
                        if special:
                            specials.append(special)
                except Exception as e:
                    logger.debug(f"Error parsing Next.js data: {e}")

        # Try HTML parsing as fallback
        product_tiles = soup.select('[data-testid="product-tile"]')
        for tile in product_tiles:
            special = self._parse_product_tile(tile)
            if special:
                specials.append(special)

        return specials

    def _extract_products_from_nextjs(self, data: dict) -> list:
        """Extract products from Next.js page data."""
        products = []
        try:
            # Navigate through typical Next.js structure
            props = data.get('props', {})
            page_props = props.get('pageProps', {})

            # Look for products in various locations
            if 'products' in page_props:
                products = page_props['products']
            elif 'initialData' in page_props:
                initial = page_props['initialData']
                if 'products' in initial:
                    products = initial['products']
        except:
            pass
        return products

    def _parse_product_data(self, data: dict) -> Optional[SpecialItem]:
        """Parse product from Coles JSON data."""
        try:
            name = data.get('name') or data.get('brand', '') + ' ' + data.get('name', '')

            pricing = data.get('pricing', {})
            price = pricing.get('now') or pricing.get('price')
            was_price = pricing.get('was') or pricing.get('comparable')
            product_id = str(data.get('id', ''))

            if name and price:
                # Construct CDN image URL from product ID
                image_url = get_coles_image_url(product_id)

                return SpecialItem(
                    name=name.strip(),
                    price=Decimal(str(price)),
                    was_price=Decimal(str(was_price)) if was_price else None,
                    special_type=pricing.get('promotionType', 'special'),
                    store_product_id=product_id,
                    image_url=image_url  # Coles CDN image
                )
        except Exception as e:
            logger.debug(f"Error parsing Coles product: {e}")
        return None

    def _parse_product_tile(self, tile) -> Optional[SpecialItem]:
        """Parse product from HTML tile."""
        try:
            name_elem = tile.select_one('[class*="product-title"], [class*="product-name"]')
            price_elem = tile.select_one('[class*="price-dollars"]')

            if name_elem:
                name = name_elem.get_text(strip=True)
                price = None

                if price_elem:
                    import re
                    price_text = price_elem.get_text(strip=True)
                    price_match = re.search(r'([\d.]+)', price_text)
                    if price_match:
                        price = Decimal(price_match.group(1))

                if name and price:
                    return SpecialItem(
                        name=name,
                        price=price,
                        special_type="catalogue"
                    )
        except Exception as e:
            logger.debug(f"Error parsing Coles tile: {e}")
        return None


class ALDIParser(BaseCatalogueParser):
    """Parser for ALDI Special Buys."""

    store_slug = "aldi"
    store_name = "ALDI"

    def fetch_specials(self) -> list[SpecialItem]:
        """Fetch specials from ALDI."""
        specials = []

        try:
            # ALDI has a simpler website structure
            response = self.client.get(
                "https://www.aldi.com.au/en/special-buys/",
                headers={
                    "Accept": "text/html,application/xhtml+xml",
                }
            )

            if response.status_code == 200:
                specials = self._parse_specials_page(response.text)
            else:
                logger.warning(f"ALDI returned status {response.status_code}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching ALDI: {e}")
        except Exception as e:
            logger.error(f"Error fetching ALDI: {e}")

        return specials

    def _parse_specials_page(self, html: str) -> list[SpecialItem]:
        """Parse ALDI Special Buys page."""
        specials = []
        soup = BeautifulSoup(html, 'lxml')

        # ALDI product boxes
        product_boxes = soup.select('.box--product, [class*="product-box"]')
        for box in product_boxes:
            special = self._parse_product_box(box)
            if special:
                specials.append(special)

        # Also try finding script data
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                import json
                data = json.loads(script.string)
                if data.get('@type') == 'Product':
                    special = self._parse_ld_json(data)
                    if special:
                        specials.append(special)
            except:
                continue

        return specials

    def _parse_product_box(self, box) -> Optional[SpecialItem]:
        """Parse ALDI product box."""
        try:
            name_elem = box.select_one('.box--description__header, [class*="product-title"]')
            price_elem = box.select_one('.box--price, [class*="price"]')

            if name_elem:
                name = name_elem.get_text(strip=True)
                price = None

                if price_elem:
                    import re
                    price_text = price_elem.get_text(strip=True)
                    price_match = re.search(r'\$?([\d.]+)', price_text)
                    if price_match:
                        price = Decimal(price_match.group(1))

                if name and price:
                    return SpecialItem(
                        name=name,
                        price=price,
                        special_type="special_buy"
                    )
        except Exception as e:
            logger.debug(f"Error parsing ALDI box: {e}")
        return None

    def _parse_ld_json(self, data: dict) -> Optional[SpecialItem]:
        """Parse product from LD+JSON schema."""
        try:
            name = data.get('name')
            offers = data.get('offers', {})
            price = offers.get('price')

            if name and price:
                return SpecialItem(
                    name=name,
                    price=Decimal(str(price)),
                    special_type="special_buy",
                    store_product_id=data.get('sku', '')
                )
        except:
            pass
        return None


# Factory function to get all parsers
def get_all_parsers() -> list[BaseCatalogueParser]:
    """Return instances of all catalogue parsers."""
    return [
        WoolworthsParser(),
        ColesParser(),
        ALDIParser()
    ]


def run_all_parsers() -> list[dict]:
    """Run all parsers and return results."""
    results = []
    for parser in get_all_parsers():
        result = parser.run()
        results.append(result)
    return results


# CLI interface
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("Testing catalogue parsers...")
        results = run_all_parsers()
        for r in results:
            print(f"\n{r['store']}:")
            print(f"  Status: {r['status']}")
            print(f"  Fetched: {r['fetched']}")
            print(f"  Saved: {r['saved']}")
            if 'error' in r:
                print(f"  Error: {r['error']}")
    else:
        print("Usage: python -m app.services.catalogue_parser --test")
