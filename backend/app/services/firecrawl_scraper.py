"""
Firecrawl scraper service for extracting supermarket specials.
Uses Firecrawl to scrape and extract product data from store websites.
"""
import os
import re
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
import time

from firecrawl import Firecrawl
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Store, Special, ScrapeLog, MasterProduct, ProductPrice, Category
from app.config import get_settings
from app.services.image_cache import image_cache
from app.services.auto_categorizer import categorize_product

logger = logging.getLogger(__name__)


class FirecrawlScraper:
    """Scraper service for extracting weekly specials from supermarket websites."""

    # Store-specific specials URLs with pagination
    STORE_URLS = {
        "woolworths": {
            "base_urls": [
                "https://www.woolworths.com.au/shop/browse/specials/half-price",
            ],
            "max_pages": 3,  # Scrape up to 3 pages per category
        },
        "coles": {
            "base_urls": [
                "https://www.coles.com.au/on-special",  # Main specials page (includes half-price)
            ],
            "max_pages": 3,
        },
        "aldi": {
            "base_urls": [
                "https://www.aldi.com.au/products/super-savers/k/1588161426952145",  # Actual product listing
            ],
            "max_pages": 1,  # ALDI usually has all on one page
        },
    }

    def __init__(self):
        api_key = get_settings().firecrawl_api_key
        if not api_key:
            raise ValueError("FIRECRAWL_API_KEY environment variable not set")
        self.app = Firecrawl(api_key=api_key)

    def scrape_all_stores(self, db: Optional[Session] = None) -> dict:
        """Scrape specials from all stores."""
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        results = {}
        try:
            for store_slug in ["woolworths", "coles", "aldi"]:
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
                raise ValueError(f"Store not found: {store_slug}")

            # Start scrape log
            scrape_log = ScrapeLog(
                store_id=store.id,
                started_at=datetime.utcnow(),
                status="running"
            )
            db.add(scrape_log)
            db.commit()

            store_config = self.STORE_URLS.get(store_slug, {})
            base_urls = store_config.get("base_urls", [])
            max_pages = store_config.get("max_pages", 1)

            all_specials = []
            seen_names = set()  # Deduplicate by name

            for base_url in base_urls:
                for page in range(1, max_pages + 1):
                    try:
                        # Construct paginated URL
                        url = self._get_paginated_url(base_url, page, store_slug)
                        logger.info(f"Scraping {store_slug} page {page}: {url}")

                        specials = self._scrape_url(url, store_slug)

                        # Deduplicate
                        new_specials = []
                        for s in specials:
                            name_key = f"{s.get('name', '')}-{s.get('price', '')}"
                            if name_key not in seen_names:
                                seen_names.add(name_key)
                                new_specials.append(s)

                        all_specials.extend(new_specials)
                        logger.info(f"Found {len(new_specials)} new specials on page {page}")

                        # If we got very few results, stop pagination
                        if len(specials) < 5:
                            logger.info(f"Few results on page {page}, stopping pagination")
                            break

                        # Rate limiting - be nice to the API
                        time.sleep(1)

                    except Exception as e:
                        logger.error(f"Error scraping {url}: {e}")
                        break

            # Save specials to database
            saved_count = self._save_specials(db, store, all_specials)

            # Update scrape log
            scrape_log.completed_at = datetime.utcnow()
            scrape_log.items_found = saved_count
            scrape_log.status = "success"
            db.commit()

            logger.info(f"Saved {saved_count} specials for {store_slug}")
            return saved_count

        except Exception as e:
            logger.error(f"Scrape failed for {store_slug}: {e}")
            if scrape_log:
                scrape_log.completed_at = datetime.utcnow()
                scrape_log.status = "failed"
                scrape_log.error_message = str(e)
                db.commit()
            raise
        finally:
            if close_db:
                db.close()

    def _get_paginated_url(self, base_url: str, page: int, store_slug: str) -> str:
        """Construct paginated URL for each store."""
        if page == 1:
            return base_url

        if store_slug == "woolworths":
            # Woolworths uses ?pageNumber=X
            separator = "&" if "?" in base_url else "?"
            return f"{base_url}{separator}pageNumber={page}"
        elif store_slug == "coles":
            # Coles uses ?page=X
            separator = "&" if "?" in base_url else "?"
            return f"{base_url}{separator}page={page}"
        else:
            return base_url

    def _scrape_url(self, url: str, store_slug: str) -> list[dict]:
        """Scrape a single URL using Firecrawl scrape + markdown parsing."""
        # Use scrape method to get markdown content
        result = self.app.scrape(url, formats=['markdown'])

        if not result or not result.markdown:
            logger.warning(f"No markdown content from {url}")
            return []

        # Parse products from markdown based on store
        if store_slug == "coles":
            products = self._parse_coles_markdown(result.markdown)
        elif store_slug == "woolworths":
            products = self._parse_woolworths_markdown(result.markdown)
        elif store_slug == "aldi":
            products = self._parse_aldi_markdown(result.markdown)
        else:
            products = []

        logger.info(f"Parsed {len(products)} products from markdown")

        # Process products to add CDN image URLs
        processed = []
        for product in products:
            if not product.get("name") or not product.get("price"):
                continue
            processed_product = self._process_product(product, store_slug)
            if processed_product:
                processed.append(processed_product)

        return processed

    def _parse_coles_markdown(self, markdown: str) -> list[dict]:
        """Parse Coles products from markdown content."""
        products = []

        # Split by product sections (## headers)
        sections = re.split(r'\n##\s+', markdown)

        for section in sections:
            lines = section.strip().split('\n')
            if not lines:
                continue

            name = lines[0].strip()

            # Skip navigation/promo sections
            if len(name) < 5 or 'Browse' in name or 'category' in name.lower():
                continue
            if 'half-price' in name.lower() or 'win' in name.lower() or 'Shop' in name:
                continue

            # Find product URL
            url_match = re.search(r'\[.*?\]\((https://www\.coles\.com\.au/product/[^)]+)\)', section)
            product_url = url_match.group(1) if url_match else None
            if not product_url:
                continue

            # Find prices - looking for $X.XX pattern
            price_match = re.search(r'\$(\d+\.?\d*)\s*\n', section)
            was_match = re.search(r'Was\s+\$(\d+\.?\d*)', section)

            price = float(price_match.group(1)) if price_match else None
            was_price = float(was_match.group(1)) if was_match else None

            if name and price:
                # Extract product ID from URL
                id_match = re.search(r'-(\d+)$', product_url)
                product_id = id_match.group(1) if id_match else None

                # Extract size from name (e.g., "| 250g" or "250g")
                size_match = re.search(r'\|\s*(\d+[gGmMlLkK]+(?:\s*[pP]ack)?)', name)
                if not size_match:
                    size_match = re.search(r'(\d+[gGmMlLkK]+)$', name)
                size = size_match.group(1) if size_match else None

                products.append({
                    'name': name.replace('\\|', '|').strip(),
                    'price': price,
                    'was_price': was_price,
                    'product_url': product_url,
                    'store_product_id': product_id,
                    'size': size,
                })

        return products

    def _parse_woolworths_markdown(self, markdown: str) -> list[dict]:
        """Parse Woolworths products from markdown content."""
        products = []

        # Woolworths has similar structure to Coles
        sections = re.split(r'\n##\s+', markdown)

        for section in sections:
            lines = section.strip().split('\n')
            if not lines:
                continue

            name = lines[0].strip()

            # Skip non-product sections
            if len(name) < 5 or 'menu' in name.lower() or 'browse' in name.lower():
                continue

            # Find product URL
            url_match = re.search(r'\[.*?\]\((https://www\.woolworths\.com\.au/shop/productdetails/(\d+)[^)]*)\)', section)
            if not url_match:
                continue

            product_url = url_match.group(1)
            stockcode = url_match.group(2)

            # Find prices
            price_match = re.search(r'\$(\d+\.?\d*)', section)
            was_match = re.search(r'[Ww]as\s+\$(\d+\.?\d*)', section)

            price = float(price_match.group(1)) if price_match else None
            was_price = float(was_match.group(1)) if was_match else None

            if name and price:
                products.append({
                    'name': name,
                    'price': price,
                    'was_price': was_price,
                    'product_url': product_url,
                    'store_product_id': stockcode,
                })

        return products

    def _parse_aldi_markdown(self, markdown: str) -> list[dict]:
        """Parse ALDI products from markdown content."""
        products = []

        # ALDI format: [BRAND\\\n\\\nProduct\\\n\\\nsize\\\n\\\n(unit_price)\\\n\\\n$price](url)
        # The escape pattern is \\\ followed by \n
        product_pattern = re.compile(
            r'\[([A-Z][A-Z\s,\.!\-…]+?)\\\\\n\\\\\n(.+?)\\\\\n\\\\\n([^\\\n]+)\\\\\n\\\\\n\([^\)]+\)\\\\\n\\\\\n\$(\d+\.?\d*)\]\((https://www\.aldi\.com\.au/product/[^\)]+)\)',
            re.MULTILINE
        )

        for match in product_pattern.finditer(markdown):
            brand = match.group(1).strip()
            name = match.group(2).strip()
            size = match.group(3).strip()
            price = float(match.group(4))
            product_url = match.group(5)

            # Extract product ID from URL
            id_match = re.search(r'-(\d{12,})$', product_url)
            product_id = id_match.group(1) if id_match else None

            products.append({
                'name': f"{brand} {name}",
                'brand': brand,
                'price': price,
                'was_price': None,  # ALDI Super Savers don't show was price
                'size': size,
                'product_url': product_url,
                'store_product_id': product_id,
            })

        return products

    def _get_extraction_prompt(self, store_slug: str) -> str:
        """Get store-specific extraction prompt."""
        if store_slug == "woolworths":
            return """Extract ALL products on special from this Woolworths page. For each product, extract:
- name: Full product name (e.g., "Cadbury Dairy Milk Chocolate Block 180g")
- brand: Brand name (e.g., "Cadbury")
- price: Current sale price as number (e.g., 4.50)
- was_price: Original price before discount as number (e.g., 9.00)
- size: Package size (e.g., "180g", "1L")
- product_url: Link to product page (contains /productdetails/STOCKCODE/)

Look for products with "Was $X.XX" or showing savings. Product URLs contain /shop/productdetails/STOCKCODE/.
Include ALL products visible. Return in the products array."""

        elif store_slug == "coles":
            return """Extract ALL products on special from this Coles page. For each product extract:
- name: Full product name including size (e.g., "Gillette Venus Satin Care Sensitive Skin Shaving Gel 195g")
- brand: Brand name (e.g., "Gillette")
- price: Current price as number (e.g., 4.00)
- was_price: Original price as number from "Was $X.XX" (e.g., 8.00)
- size: Package size from name (e.g., "195g")
- unit_price: Price per unit (e.g., "$2.05/100g")
- product_url: Link to product (e.g., https://www.coles.com.au/product/...)

IMPORTANT: Look for products with "Save $X.XX" and "Was $X.XX".
The page shows prices like: $4.00 Save $4.00 ... Was $8.00
Extract the numeric values only (4.00 for price, 8.00 for was_price).
Include ALL products on special. Return in the products array."""

        elif store_slug == "aldi":
            return """Extract ALL products from this ALDI Super Savers page. For each product extract:
- name: Full product name (e.g., "Australian Pork Leg Roast")
- brand: Brand name if shown (e.g., "REMANO", "FARMDALE")
- price: Current price as number (e.g., 5.99)
- was_price: Original price as number if shown
- size: Package size (e.g., "500g", "1kg")
- product_url: Link to product if available
- image_url: Product image URL from dm.apac.cms.aldi.cx domain

Include ALL products shown. Return in the products array."""

        return """Extract ALL products on special. For each product extract:
- name: Full product name
- brand: Brand name
- price: Current price as number
- was_price: Original price as number
- size: Package size
- product_url: Link to product

Include ALL products. Return in the products array."""

    def _process_product(self, product: dict, store_slug: str) -> dict:
        """Process and enrich a product with store-specific data."""
        result = {
            "name": product.get("name", "").strip(),
            "brand": product.get("brand"),
            "price": product.get("price"),
            "was_price": product.get("was_price"),
            "size": product.get("size"),
            "unit_price": product.get("unit_price"),
            "product_url": product.get("product_url"),
            "category": product.get("category"),
            "image_url": product.get("image_url"),
        }

        # Extract store product ID and construct CDN image URL
        if store_slug == "woolworths":
            stockcode = self._extract_woolworths_stockcode(product.get("product_url", ""))
            result["store_product_id"] = stockcode
            # Prefer CDN URL if we have stockcode, otherwise use extracted image
            if stockcode:
                result["image_url"] = self._get_woolworths_image(stockcode)
            elif not result["image_url"]:
                result["image_url"] = product.get("image_url")

        elif store_slug == "coles":
            product_id = self._extract_coles_product_id(product.get("product_url", ""))
            result["store_product_id"] = product_id
            # Prefer CDN URL if we have product_id
            if product_id:
                result["image_url"] = self._get_coles_image(product_id)
            elif not result["image_url"]:
                result["image_url"] = product.get("image_url")

        elif store_slug == "aldi":
            # For ALDI, extract product ID from URL for reference
            aldi_id = self._extract_aldi_product_id(product.get("product_url", ""))
            result["store_product_id"] = aldi_id
            # For ALDI, we rely on Firecrawl to extract the image URL
            # ALDI uses UUIDs in image URLs that can't be constructed from product ID

        # Clean up image URL
        if result["image_url"]:
            result["image_url"] = self._clean_image_url(result["image_url"])

        return result

    def _clean_image_url(self, url: str) -> Optional[str]:
        """Clean and validate image URL."""
        if not url:
            return None

        url = url.strip()

        # Skip placeholder images
        if "placeholder" in url.lower() or "no-image" in url.lower():
            return None

        # Ensure it starts with http
        if not url.startswith("http"):
            return None

        return url

    def _extract_woolworths_stockcode(self, url: str) -> Optional[str]:
        """Extract stockcode from Woolworths product URL."""
        if not url:
            return None
        # URL format: woolworths.com.au/shop/productdetails/6033684/product-name
        match = re.search(r'/productdetails/(\d+)', url)
        if match:
            return match.group(1)
        # Also try: /shop/product/STOCKCODE
        match = re.search(r'/product/(\d+)', url)
        return match.group(1) if match else None

    def _get_woolworths_image(self, stockcode: str) -> Optional[str]:
        """Construct Woolworths CDN image URL from stockcode."""
        if not stockcode:
            return None
        return f"https://cdn0.woolworths.media/content/wowproductimages/large/{stockcode}.jpg"

    def _extract_coles_product_id(self, url: str) -> Optional[str]:
        """Extract product ID from Coles product URL."""
        if not url:
            return None
        # URL format: coles.com.au/product/product-name-123456
        match = re.search(r'-(\d+)(?:\?|$|/)', url)
        if match:
            return match.group(1)
        # Also try just ending with digits
        match = re.search(r'/(\d+)$', url.rstrip('/'))
        return match.group(1) if match else None

    def _get_coles_image(self, product_id: str) -> Optional[str]:
        """Construct Coles CDN image URL from product ID."""
        if not product_id:
            return None
        # First digit is used as prefix folder
        first_digit = product_id[0]
        return f"https://productimages.coles.com.au/productimages/{first_digit}/{product_id}.jpg"

    def _extract_aldi_product_id(self, url: str) -> Optional[str]:
        """Extract product ID from ALDI product URL."""
        if not url:
            return None
        # URL format: aldi.com.au/product/product-name-000000000000123456
        match = re.search(r'-(\d{12,})(?:\?|$|/)?', url)
        return match.group(1) if match else None

    def _get_aldi_image(self, product_id: str) -> Optional[str]:
        """Construct ALDI image URL from product ID."""
        if not product_id:
            return None
        # ALDI Australia uses this CDN pattern for product images
        # Format: https://prod.cloud.aldi.com.au/images/{product_id}/fm/w-200
        return f"https://prod.cloud.aldi.com.au/images/{product_id}/fm/w-400"

    def _save_specials(self, db: Session, store: Store, specials: list[dict]) -> int:
        """Save scraped specials to database (both old and new schema)."""
        today = date.today()
        # Specials typically valid for 7 days
        valid_to = today + timedelta(days=7)

        saved_count = 0
        seen_product_ids = set()  # Track to avoid duplicate store_product_id in same batch
        images_to_cache = []  # Queue images for background caching

        # Build category slug -> id mapping for auto-categorization
        # Include ALL categories (both parents and subcategories) for granular matching
        category_map = {}
        all_categories = db.query(Category).all()
        for cat in all_categories:
            category_map[cat.slug] = cat.id

        for item in specials:
            try:
                # Calculate discount percentage
                discount_percent = None
                if item.get("was_price") and item.get("price"):
                    was_price = float(item["was_price"])
                    price = float(item["price"])
                    if was_price > price and was_price > 0:
                        discount_percent = int(((was_price - price) / was_price) * 100)

                # Skip if we already processed this store_product_id in this batch
                store_product_id = item.get("store_product_id")
                if store_product_id and store_product_id in seen_product_ids:
                    logger.debug(f"Skipping duplicate store_product_id: {store_product_id}")
                    continue
                if store_product_id:
                    seen_product_ids.add(store_product_id)

                # === SAVE TO NEW NORMALIZED SCHEMA ===
                self._save_to_normalized_schema(
                    db, store, item, today, valid_to, discount_percent, images_to_cache
                )

                # === SAVE TO OLD SCHEMA (for backwards compatibility) ===
                # Check for existing special by store_product_id (matches unique constraint)
                existing = None
                if store_product_id:
                    existing = db.query(Special).filter(
                        Special.store_id == store.id,
                        Special.store_product_id == store_product_id,
                        Special.valid_from == today
                    ).first()
                # If no store_product_id, check by name
                if not existing:
                    existing = db.query(Special).filter(
                        Special.store_id == store.id,
                        Special.name == item["name"],
                        Special.valid_from == today
                    ).first()

                # Auto-categorize product
                category_slug = categorize_product(item["name"], item.get("brand"))
                category_id = category_map.get(category_slug) if category_slug else None

                if existing:
                    # Update existing
                    existing.price = Decimal(str(item["price"]))
                    existing.was_price = Decimal(str(item["was_price"])) if item.get("was_price") else None
                    existing.discount_percent = discount_percent
                    existing.image_url = item.get("image_url") or existing.image_url
                    existing.scraped_at = datetime.utcnow()
                    # Update category_id if not set
                    if not existing.category_id and category_id:
                        existing.category_id = category_id
                else:
                    # Create new
                    special = Special(
                        store_id=store.id,
                        name=item["name"],
                        brand=item.get("brand"),
                        size=item.get("size"),
                        category=item.get("category"),
                        category_id=category_id,  # Auto-categorized
                        price=Decimal(str(item["price"])),
                        was_price=Decimal(str(item["was_price"])) if item.get("was_price") else None,
                        discount_percent=discount_percent,
                        unit_price=item.get("unit_price"),
                        store_product_id=store_product_id,
                        product_url=item.get("product_url"),
                        image_url=item.get("image_url"),
                        valid_from=today,
                        valid_to=valid_to,
                    )
                    db.add(special)

                saved_count += 1
            except Exception as e:
                logger.warning(f"Failed to save special {item.get('name')}: {e}")
                db.rollback()
                continue

        try:
            db.commit()
        except Exception as e:
            logger.error(f"Failed to commit specials: {e}")
            db.rollback()
            raise

        # Queue images for background caching
        if images_to_cache:
            logger.info(f"Queuing {len(images_to_cache)} images for caching")
            self._cache_images_background(images_to_cache)

        return saved_count

    def _save_to_normalized_schema(
        self, db: Session, store: Store, item: dict,
        today: date, valid_to: date, discount_percent: int,
        images_to_cache: list
    ):
        """Save product to normalized MasterProduct + ProductPrice schema."""
        store_product_id = item.get("store_product_id")
        if not store_product_id:
            store_product_id = f"unknown_{hash(item['name'])}"

        # Check if product already exists
        product = db.query(MasterProduct).filter(
            MasterProduct.store_id == store.id,
            MasterProduct.stockcode == store_product_id
        ).first()

        if product:
            # Update existing product
            product.last_seen_at = datetime.utcnow()
            # Update product details if changed
            if item.get("name"):
                product.name = item["name"]
            if item.get("brand"):
                product.brand = item["brand"]
            if item.get("size"):
                product.size = item["size"]
            if item.get("product_url"):
                product.product_url = item["product_url"]
            if item.get("image_url") and not product.image_cached:
                product.original_image_url = item["image_url"]
        else:
            # Create new product
            product = MasterProduct(
                store_id=store.id,
                stockcode=store_product_id,
                name=item["name"],
                brand=item.get("brand"),
                size=item.get("size"),
                category=item.get("category"),
                product_url=item.get("product_url"),
                original_image_url=item.get("image_url"),
                image_cached=False,
                created_at=datetime.utcnow(),
                last_seen_at=datetime.utcnow()
            )
            db.add(product)
            db.flush()  # Get product ID

            # Queue image for caching if URL exists
            if item.get("image_url"):
                images_to_cache.append({
                    "url": item["image_url"],
                    "store_slug": store.slug,
                    "stockcode": store_product_id,
                    "product_id": product.id
                })

        # Convert price to cents
        price_cents = int(float(item["price"]) * 100)
        was_price_cents = int(float(item["was_price"]) * 100) if item.get("was_price") else None

        # Check if price record already exists for this period
        existing_price = db.query(ProductPrice).filter(
            ProductPrice.product_id == product.id,
            ProductPrice.valid_from == today
        ).first()

        if existing_price:
            # Update existing price
            existing_price.price = f"${item['price']:.2f}"
            existing_price.price_numeric = price_cents
            existing_price.was_price = f"${item['was_price']:.2f}" if item.get("was_price") else None
            existing_price.was_price_numeric = was_price_cents
            existing_price.discount_percent = discount_percent or 0
            existing_price.unit_price = item.get("unit_price")
            existing_price.scraped_at = datetime.utcnow()
        else:
            # Mark all previous prices as not current
            db.query(ProductPrice).filter(
                ProductPrice.product_id == product.id,
                ProductPrice.is_current == True
            ).update({"is_current": False})

            # Create new price record
            price_record = ProductPrice(
                product_id=product.id,
                price=f"${item['price']:.2f}",
                price_numeric=price_cents,
                was_price=f"${item['was_price']:.2f}" if item.get("was_price") else None,
                was_price_numeric=was_price_cents,
                discount_percent=discount_percent or 0,
                unit_price=item.get("unit_price"),
                valid_from=today,
                valid_to=valid_to,
                is_current=True,
                scraped_at=datetime.utcnow()
            )
            db.add(price_record)

    def _cache_images_background(self, images: list):
        """Cache images in background (non-blocking)."""
        import asyncio

        async def cache_batch():
            try:
                results = await image_cache.cache_batch(images, max_concurrent=5)
                logger.info(f"Image cache results: {results}")
            except Exception as e:
                logger.error(f"Background image caching failed: {e}")

        # Run in background - don't block the scraper
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(cache_batch())
            else:
                asyncio.run(cache_batch())
        except RuntimeError:
            # No event loop, create one
            asyncio.run(cache_batch())

    def clear_expired_specials(self, db: Optional[Session] = None) -> int:
        """Remove specials that have expired."""
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            today = date.today()
            deleted = db.query(Special).filter(Special.valid_to < today).delete()
            db.commit()
            return deleted
        finally:
            if close_db:
                db.close()

    def clear_all_specials(self, db: Optional[Session] = None) -> int:
        """Clear all specials (for fresh scrape)."""
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            deleted = db.query(Special).delete()
            db.commit()
            return deleted
        except Exception as e:
            db.rollback()
            raise
        finally:
            if close_db:
                db.close()


# Convenience function for scheduled jobs
def run_weekly_scrape():
    """Run the weekly scrape job. Called by scheduler."""
    logger.info("Starting weekly specials scrape...")
    scraper = FirecrawlScraper()

    db = SessionLocal()
    try:
        # Clear expired specials first
        expired = scraper.clear_expired_specials(db)
        logger.info(f"Cleared {expired} expired specials")

        # Scrape all stores
        results = scraper.scrape_all_stores(db)

        for store, result in results.items():
            if result["status"] == "success":
                logger.info(f"{store}: {result['items']} specials scraped")
            else:
                logger.error(f"{store}: scrape failed - {result.get('error')}")

    except Exception as e:
        logger.error(f"Weekly scrape failed: {e}")
        raise
    finally:
        db.close()

    logger.info("Weekly scrape completed")
