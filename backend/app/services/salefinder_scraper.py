"""
SaleFinder scraper service for extracting supermarket specials.
Uses the SaleFinder embed API to fetch catalogue data from Australian supermarkets.
"""
import re
import json
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
import time

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Store, Special, ScrapeLog, MasterProduct, ProductPrice, Category
from app.config import get_settings
from app.services.auto_categorizer import categorize_product
from app.services.brand_extractor import extract_brand_from_name, extract_size_from_name

logger = logging.getLogger(__name__)


class SaleFinderScraper:
    """Scraper service for extracting weekly specials from SaleFinder."""

    BASE_URL = "https://embed.salefinder.com.au"
    WEBSERVICE_URL = "https://webservice.salefinder.com.au"

    # Store configuration from SaleFinder
    # retailer_id and location_id discovered from szdc/catalogue project and SaleFinder website
    STORE_CONFIG = {
        "woolworths": {
            "retailer_id": 126,
            "location_id": 4778,
            "name": "Woolworths",
            "salefinder_url": "woolworths-catalogue",
        },
        "coles": {
            "retailer_id": 148,
            "location_id": 8245,
            "name": "Coles",
            "salefinder_url": "coles-catalogue",
        },
        # ALDI is not available on SaleFinder (redirects to notfound)
        "iga": {
            "retailer_id": 183,
            "location_id": 0,  # Location varies by franchise
            "name": "IGA",
            "salefinder_url": "iga-catalogue",
        },
    }

    def __init__(self):
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json, text/javascript, */*",
            }
        )

    def _parse_jsonp(self, response_text: str) -> dict:
        """Parse JSONP response by stripping callback wrapper."""
        # JSONP format: callback({...}) or just ({...})
        # Strip leading function call and trailing characters
        text = response_text.strip()

        # Find the JSON content between parentheses
        start = text.find('(')
        end = text.rfind(')')

        if start != -1 and end != -1 and end > start:
            json_text = text[start + 1:end]
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                pass

        # Try parsing as plain JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response: {e}")
            return {}

    def discover_catalogues(self, store_slug: str) -> list[dict]:
        """Discover available catalogues for a store."""
        config = self.STORE_CONFIG.get(store_slug)
        if not config:
            logger.error(f"Store not configured: {store_slug}")
            return []

        catalogues = []

        # Use the salefinder_url from config
        salefinder_url = config.get("salefinder_url", f"{store_slug}-catalogue")

        try:
            url = f"https://salefinder.com.au/{salefinder_url}"
            response = self.client.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')

                # Look for catalogue links with pattern /{store}-catalogue/.../XXXXX/
                pattern = rf'/{re.escape(salefinder_url)}/[^/]+/(\d+)/'
                links = soup.find_all('a', href=re.compile(pattern))
                for link in links:
                    match = re.search(rf'({re.escape(salefinder_url)}/[^/]+/(\d+))/', link.get('href', ''))
                    if match:
                        full_path = match.group(1)  # e.g., "coles-catalogue/coles-catalogue-nsw-metro/63026"
                        cat_id = match.group(2)
                        cat_name = full_path.split('/')[1].replace('-', ' ').title() if '/' in full_path else f"Catalogue {cat_id}"
                        catalogues.append({
                            "id": int(cat_id),
                            "name": cat_name,
                            "path": full_path,  # Store the full path for scraping
                        })

                # Also check Facebook like buttons for catalogue IDs
                iframes = soup.find_all('iframe', src=re.compile(r'salefinder\.com\.au%2F(\d{5,})'))
                for iframe in iframes:
                    match = re.search(r'salefinder\.com\.au%2F(\d{5,})', iframe.get('src', ''))
                    if match:
                        catalogues.append({
                            "id": int(match.group(1)),
                            "name": "Current Catalogue",
                        })

        except Exception as e:
            logger.error(f"Failed to discover {store_slug} catalogues: {e}")

        # Deduplicate by ID
        seen_ids = set()
        unique_catalogues = []
        for cat in catalogues:
            cat_id = cat.get("id")
            if cat_id and cat_id not in seen_ids:
                seen_ids.add(cat_id)
                unique_catalogues.append(cat)

        logger.info(f"Found {len(unique_catalogues)} catalogues for {store_slug}")
        return unique_catalogues

    def get_categories(self, catalogue_id: int, retailer_id: int) -> list[dict]:
        """Get categories for a catalogue."""
        try:
            url = f"{self.BASE_URL}/catalogue/getNavbar/{catalogue_id}"
            params = {
                "retailerId": retailer_id,
                "format": "json",
            }
            response = self.client.get(url, params=params)
            if response.status_code == 200:
                data = self._parse_jsonp(response.text)

                # Extract categories from response
                categories = []
                if isinstance(data, dict):
                    # Check for 'content' field which contains HTML
                    content = data.get("content", "")
                    if content:
                        soup = BeautifulSoup(content, 'lxml')
                        # Find category links
                        cat_links = soup.find_all('a', {'data-category-id': True})
                        for link in cat_links:
                            categories.append({
                                "id": link.get('data-category-id'),
                                "name": link.get_text(strip=True),
                            })

                    # Also check for direct categories array
                    if "categories" in data:
                        categories.extend(data["categories"])

                return categories
        except Exception as e:
            logger.error(f"Failed to get categories: {e}")

        return []

    def get_products(self, catalogue_path: str, catalogue_id: int = None, max_pages: int = 50) -> list[dict]:
        """Get products from a catalogue by scraping the SaleFinder list page with pagination.

        Args:
            catalogue_path: Full path like "coles-catalogue/coles-catalogue-nsw-metro/63026"
            catalogue_id: Optional catalogue ID (for backwards compatibility)
            max_pages: Maximum number of pages to fetch (default 50, roughly 600 products)
        """
        all_products = []

        try:
            # Start with page 1
            base_url = f"https://salefinder.com.au/{catalogue_path}/list"
            current_page = 1
            total_pages = 1

            while current_page <= min(total_pages, max_pages):
                # Build URL with pagination
                if current_page == 1:
                    url = base_url
                else:
                    url = f"{base_url}?qs={current_page},,,,"

                logger.debug(f"Fetching page {current_page}: {url}")
                response = self.client.get(url)

                if response.status_code != 200:
                    logger.warning(f"List page returned {response.status_code} for {url}")
                    break

                # Parse products from this page
                page_products = self._parse_salefinder_list(response.text)
                all_products.extend(page_products)

                # On first page, detect total number of pages from pagination
                if current_page == 1:
                    total_pages = self._detect_total_pages(response.text)
                    logger.info(f"Detected {total_pages} pages for {catalogue_path}")

                # If we got no products, stop
                if not page_products:
                    logger.debug(f"No products on page {current_page}, stopping pagination")
                    break

                logger.debug(f"Found {len(page_products)} products on page {current_page}")
                current_page += 1

                # Rate limiting - be respectful
                if current_page <= total_pages:
                    time.sleep(0.5)

            logger.info(f"Total products collected: {len(all_products)} from {current_page - 1} pages")

        except Exception as e:
            logger.error(f"Failed to get products: {e}")

        return all_products

    def _detect_total_pages(self, html_content: str) -> int:
        """Detect the total number of pages from pagination links."""
        soup = BeautifulSoup(html_content, 'lxml')
        max_page = 1

        # Look for pagination links like ?qs=N,,,,
        pagination_links = soup.find_all('a', href=re.compile(r'\?qs=(\d+)'))
        for link in pagination_links:
            href = link.get('href', '')
            match = re.search(r'\?qs=(\d+)', href)
            if match:
                page_num = int(match.group(1))
                max_page = max(max_page, page_num)

        # Also check for [X-Y] style links indicating more pages
        range_links = soup.find_all('a', string=re.compile(r'\[\d+-\d+\]'))
        for link in range_links:
            match = re.search(r'\[(\d+)-(\d+)\]', link.get_text())
            if match:
                max_page = max(max_page, int(match.group(2)))

        return max_page

    def _parse_salefinder_list(self, html_content: str) -> list[dict]:
        """Parse products from SaleFinder list page HTML."""
        products = []
        soup = BeautifulSoup(html_content, 'lxml')

        # Method 1: Find product links with data-itemid and data-itemname attributes
        item_links = soup.find_all('a', {'class': 'item-image', 'data-itemid': True})

        for link in item_links:
            try:
                item_id = link.get('data-itemid', '')
                item_name = link.get('data-itemname', '').replace('&#039;', "'")

                # Find the parent container to get price info
                parent = link.find_parent('div') or link.find_parent('li')
                if not parent:
                    continue

                # Find the price element
                price_el = parent.find('span', class_='price')
                price = None
                was_price = None

                if price_el:
                    price_text = price_el.get_text(strip=True)
                    price = self._extract_price(price_text)

                # Find "Was $X.XX" text
                text_content = parent.get_text()
                was_match = re.search(r'Was\s*\$(\d+\.?\d*)', text_content)
                if was_match:
                    was_price = float(was_match.group(1))

                # Find image
                img = link.find('img')
                image_url = img.get('src', '') if img else ''

                # Use high-res image if available
                if item_id and 'thumbs' in image_url:
                    image_url = f"https://dduhxx0oznf63.cloudfront.net/images/products/{item_id}.jpg"

                if item_name and price:
                    products.append({
                        "name": item_name,
                        "price": price,
                        "was_price": was_price,
                        "image_url": image_url,
                        "store_product_id": item_id,
                    })

            except Exception as e:
                logger.debug(f"Failed to parse product (method 1): {e}")
                continue

        # Method 2: Find products by URL pattern (fallback for different page structure)
        if not products:
            # Look for product links with URL pattern like /63026/.../productid/
            product_links = soup.find_all('a', href=re.compile(r'/\d{5}/[^/]+/[^/]+/[^/]+/(\d+)/'))

            seen_ids = set()
            for link in product_links:
                try:
                    href = link.get('href', '')

                    # Extract product ID from URL
                    match = re.search(r'/(\d{8,})/?$', href)
                    if not match:
                        continue

                    item_id = match.group(1)
                    if item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)

                    # Get product container - go up to find the whole product div
                    container = link.find_parent('div')
                    for _ in range(5):  # Go up max 5 levels
                        if container and container.find('h1'):
                            break
                        container = container.find_parent('div') if container else None

                    if not container:
                        continue

                    # Extract product name from h1
                    h1 = container.find('h1')
                    if not h1:
                        continue

                    item_name = h1.get_text(strip=True)

                    # Extract prices from container text
                    container_text = container.get_text(' ', strip=True)

                    # Find "Was $X.XX" price
                    was_match = re.search(r'Was\s*\$(\d+\.?\d*)', container_text)
                    was_price = float(was_match.group(1)) if was_match else None

                    # Find current price like "$2.00 each" or "$34.00 kg"
                    price = None
                    price_match = re.search(r'\$(\d+\.?\d*)\s*(?:each|kg|per)', container_text)
                    if price_match:
                        price = float(price_match.group(1))
                    else:
                        # Try to find any price that's not the "Was" price
                        all_prices = re.findall(r'\$(\d+\.?\d*)', container_text)
                        if all_prices:
                            # Take the smallest price as sale price
                            price = min(float(p) for p in all_prices)

                    if not price:
                        continue

                    # Find image
                    img = container.find('img')
                    image_url = ''
                    if img:
                        image_url = img.get('src', '') or img.get('data-src', '')

                    products.append({
                        "name": item_name,
                        "price": price,
                        "was_price": was_price,
                        "image_url": image_url,
                        "store_product_id": item_id,
                    })

                except Exception as e:
                    logger.debug(f"Failed to parse product (method 2): {e}")
                    continue

        return products

    def _parse_products_html(self, html_content: str) -> list[dict]:
        """Parse products from HTML content (legacy method)."""
        products = []
        soup = BeautifulSoup(html_content, 'lxml')

        # Try multiple selectors for product tiles
        selectors = [
            '.shelfProductTile',
            '.product-tile',
            '[data-product-id]',
            '.productTile',
        ]

        product_elements = []
        for selector in selectors:
            product_elements = soup.select(selector)
            if product_elements:
                break

        for element in product_elements:
            try:
                product = self._parse_product_element(element)
                if product and product.get("name") and product.get("price"):
                    products.append(product)
            except Exception as e:
                logger.debug(f"Failed to parse product element: {e}")
                continue

        return products

    def _parse_product_element(self, element) -> dict:
        """Parse a single product element."""
        product = {}

        # Try to find product name
        name_selectors = [
            '.shelfProductTile-descriptionLink',
            '.product-title',
            '.product-name',
            'h3', 'h4',
            '[data-product-name]',
        ]
        for selector in name_selectors:
            name_el = element.select_one(selector)
            if name_el:
                product["name"] = name_el.get_text(strip=True)
                break

        # Try to find prices
        # Sale price
        price_selectors = [
            '.price-sale',
            '.sale-price',
            '.current-price',
            '[data-sale-price]',
        ]
        for selector in price_selectors:
            price_el = element.select_one(selector)
            if price_el:
                price_text = price_el.get_text(strip=True)
                price = self._extract_price(price_text)
                if price:
                    product["price"] = price
                    break

        # Regular/was price
        was_price_selectors = [
            '.price-regular',
            '.was-price',
            '.original-price',
            '[data-regular-price]',
        ]
        for selector in was_price_selectors:
            was_el = element.select_one(selector)
            if was_el:
                was_text = was_el.get_text(strip=True)
                was_price = self._extract_price(was_text)
                if was_price:
                    product["was_price"] = was_price
                    break

        # Price text (e.g., "1/2 Price")
        promo_selectors = [
            '.price-text',
            '.promo-text',
            '.discount-label',
        ]
        for selector in promo_selectors:
            promo_el = element.select_one(selector)
            if promo_el:
                product["price_text"] = promo_el.get_text(strip=True)
                break

        # Product URL
        link = element.select_one('a[href]')
        if link:
            product["product_url"] = link.get('href', '')

        # Image URL
        img = element.select_one('img')
        if img:
            product["image_url"] = img.get('src') or img.get('data-src', '')

        # Product ID
        product_id = element.get('data-product-id') or element.get('data-id')
        if product_id:
            product["store_product_id"] = str(product_id)

        return product

    def _extract_price(self, text: str) -> Optional[float]:
        """Extract price from text like '$4.50' or '4.50'."""
        if not text:
            return None
        match = re.search(r'\$?(\d+\.?\d*)', text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None

    def _normalize_product(self, data: dict) -> dict:
        """Normalize product data from API response."""
        return {
            "name": data.get("name") or data.get("productName", ""),
            "price": data.get("salePrice") or data.get("price"),
            "was_price": data.get("regularPrice") or data.get("wasPrice"),
            "price_text": data.get("priceText", ""),
            "product_url": data.get("url") or data.get("productUrl", ""),
            "image_url": data.get("imageUrl") or data.get("image", ""),
            "store_product_id": str(data.get("id") or data.get("productId", "")),
        }

    def scrape_store(self, store_slug: str, db: Optional[Session] = None) -> int:
        """Scrape specials for a specific store."""
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        scrape_log = None
        try:
            store = db.query(Store).filter(Store.slug == store_slug).first()
            if not store:
                raise ValueError(f"Store not found in database: {store_slug}")

            config = self.STORE_CONFIG.get(store_slug)
            if not config:
                raise ValueError(f"Store not configured in SaleFinder: {store_slug}")

            # Start scrape log
            scrape_log = ScrapeLog(
                store_id=store.id,
                started_at=datetime.utcnow(),
                status="running"
            )
            db.add(scrape_log)
            db.commit()

            # Discover current catalogues
            catalogues = self.discover_catalogues(store_slug)
            if not catalogues:
                logger.warning(f"No catalogues found for {store_slug}")
                # Try using a default/recent catalogue ID
                # These would need to be updated periodically
                default_ids = {
                    "woolworths": 22558,  # Example from szdc/catalogue
                    "coles": 22000,  # Placeholder
                }
                if store_slug in default_ids:
                    catalogues = [{"id": default_ids[store_slug], "name": "Default"}]

            all_products = []
            seen_names = set()

            for catalogue in catalogues[:1]:  # Only process first (most recent) catalogue
                catalogue_id = catalogue.get("id")
                catalogue_path = catalogue.get("path")

                if not catalogue_id or not catalogue_path:
                    logger.warning(f"Catalogue missing id or path: {catalogue}")
                    continue

                logger.info(f"Processing catalogue {catalogue_id} for {store_slug} (path: {catalogue_path})")

                # Get products directly from the list page
                products = self.get_products(catalogue_path, catalogue_id)

                # Deduplicate by name
                for p in products:
                    name_key = f"{p.get('name', '')}-{p.get('price', '')}"
                    if name_key not in seen_names:
                        seen_names.add(name_key)
                        all_products.append(p)

                logger.info(f"Found {len(products)} products in catalogue {catalogue_id}")

                # Rate limiting
                time.sleep(1)

            # Save products to database
            saved_count = self._save_specials(db, store, all_products)

            # Update scrape log
            scrape_log.completed_at = datetime.utcnow()
            scrape_log.items_found = saved_count
            scrape_log.status = "success"
            db.commit()

            logger.info(f"Saved {saved_count} specials for {store_slug} from SaleFinder")
            return saved_count

        except Exception as e:
            logger.error(f"SaleFinder scrape failed for {store_slug}: {e}")
            if scrape_log:
                scrape_log.completed_at = datetime.utcnow()
                scrape_log.status = "failed"
                scrape_log.error_message = str(e)
                db.commit()
            raise
        finally:
            if close_db:
                db.close()

    def scrape_all_stores(self, db: Optional[Session] = None) -> dict:
        """Scrape specials from all configured stores."""
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        results = {}
        try:
            for store_slug in self.STORE_CONFIG.keys():
                try:
                    count = self.scrape_store(store_slug, db)
                    results[store_slug] = {"status": "success", "items": count}
                except Exception as e:
                    logger.error(f"Failed to scrape {store_slug}: {e}")
                    results[store_slug] = {"status": "failed", "error": str(e)}
        finally:
            if close_db:
                db.close()

        return results

    def _save_specials(self, db: Session, store: Store, specials: list[dict]) -> int:
        """Save scraped specials to database (both old and new schema)."""
        today = date.today()
        valid_to = today + timedelta(days=7)

        saved_count = 0
        seen_product_ids = set()

        # Build category slug -> id mapping
        category_map = {}
        all_categories = db.query(Category).all()
        for cat in all_categories:
            category_map[cat.slug] = cat.id

        for item in specials:
            try:
                # Skip if missing required fields
                if not item.get("name") or not item.get("price"):
                    continue

                # Calculate discount percentage
                discount_percent = None
                if item.get("was_price") and item.get("price"):
                    was_price = float(item["was_price"])
                    price = float(item["price"])
                    if was_price > price and was_price > 0:
                        discount_percent = int(((was_price - price) / was_price) * 100)

                # Skip duplicates
                store_product_id = item.get("store_product_id")
                if store_product_id and store_product_id in seen_product_ids:
                    continue
                if store_product_id:
                    seen_product_ids.add(store_product_id)

                # Extract brand and size
                brand = extract_brand_from_name(item["name"])
                size = extract_size_from_name(item["name"])

                # Auto-categorize
                category_slug = categorize_product(item["name"], brand)
                category_id = category_map.get(category_slug) if category_slug else None

                # Construct image URL if needed
                image_url = item.get("image_url")
                if not image_url and store_product_id:
                    if store.slug == "woolworths":
                        image_url = f"https://cdn0.woolworths.media/content/wowproductimages/large/{store_product_id}.jpg"
                    elif store.slug == "coles":
                        first_digit = store_product_id[0] if store_product_id else '0'
                        image_url = f"https://productimages.coles.com.au/productimages/{first_digit}/{store_product_id}.jpg"

                # Check for existing special
                existing = None
                if store_product_id:
                    existing = db.query(Special).filter(
                        Special.store_id == store.id,
                        Special.store_product_id == store_product_id,
                        Special.valid_from == today
                    ).first()

                if existing:
                    # Update existing
                    existing.price = Decimal(str(item["price"]))
                    existing.was_price = Decimal(str(item["was_price"])) if item.get("was_price") else None
                    existing.discount_percent = discount_percent
                    existing.image_url = image_url or existing.image_url
                    existing.scraped_at = datetime.utcnow()
                    if not existing.category_id and category_id:
                        existing.category_id = category_id
                    if not existing.brand and brand:
                        existing.brand = brand
                    if not existing.size and size:
                        existing.size = size
                else:
                    # Create new
                    special = Special(
                        store_id=store.id,
                        name=item["name"],
                        brand=brand,
                        size=size,
                        category_id=category_id,
                        price=Decimal(str(item["price"])),
                        was_price=Decimal(str(item["was_price"])) if item.get("was_price") else None,
                        discount_percent=discount_percent,
                        store_product_id=store_product_id,
                        product_url=item.get("product_url"),
                        image_url=image_url,
                        valid_from=today,
                        valid_to=valid_to,
                    )
                    db.add(special)

                saved_count += 1

            except Exception as e:
                logger.warning(f"Failed to save special {item.get('name')}: {e}")
                continue

        try:
            db.commit()
        except Exception as e:
            logger.error(f"Failed to commit specials: {e}")
            db.rollback()
            raise

        return saved_count


# Convenience function for scheduled jobs
def run_salefinder_scrape():
    """Run the SaleFinder scrape job. Called by scheduler."""
    logger.info("Starting SaleFinder specials scrape...")
    scraper = SaleFinderScraper()

    db = SessionLocal()
    try:
        results = scraper.scrape_all_stores(db)

        for store, result in results.items():
            if result["status"] == "success":
                logger.info(f"{store}: {result['items']} specials scraped from SaleFinder")
            else:
                logger.error(f"{store}: SaleFinder scrape failed - {result.get('error')}")

    except Exception as e:
        logger.error(f"SaleFinder scrape failed: {e}")
        raise
    finally:
        db.close()

    logger.info("SaleFinder scrape completed")
    return results
