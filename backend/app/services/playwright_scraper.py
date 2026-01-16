"""
Playwright-based scraper for supermarket specials.

Scrapes weekly specials from Woolworths, Coles, ALDI, and IGA
using browser automation for accurate data extraction.
"""
import asyncio
import logging
import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional
from dataclasses import dataclass, field
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout

from app.database import SessionLocal
from app.models import Store, Category, Special

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ScrapedProduct:
    """Represents a scraped product from a supermarket."""
    name: str
    price: Decimal
    was_price: Optional[Decimal] = None
    savings: Optional[Decimal] = None
    discount_percent: Optional[int] = None
    unit_price: Optional[str] = None
    size: Optional[str] = None
    brand: Optional[str] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    special_type: Optional[str] = None  # "Half Price", "Fresh Special", etc.
    category_name: Optional[str] = None
    store_slug: str = ""


@dataclass
class CategoryConfig:
    """Configuration for a category to scrape."""
    name: str
    slug: str
    url: str
    subcategories: list[dict] = field(default_factory=list)


# ============== WOOLWORTHS CATEGORY CONFIGURATION ==============
WOOLWORTHS_CATEGORIES = [
    CategoryConfig(
        name="Fruit & Veg",
        slug="fruit-veg",
        url="https://www.woolworths.com.au/shop/browse/fruit-veg/fruit-veg-specials"
    ),
    CategoryConfig(
        name="Poultry, Meat & Seafood",
        slug="meat-seafood",
        url="https://www.woolworths.com.au/shop/browse/poultry-meat-seafood/poultry-meat-seafood-specials"
    ),
    CategoryConfig(
        name="Deli",
        slug="deli",
        url="https://www.woolworths.com.au/shop/browse/deli/deli-specials"
    ),
    CategoryConfig(
        name="Dairy, Eggs & Fridge",
        slug="dairy-eggs-fridge",
        url="https://www.woolworths.com.au/shop/browse/dairy-eggs-fridge/dairy-eggs-fridge-specials"
    ),
    CategoryConfig(
        name="Bakery",
        slug="bakery",
        url="https://www.woolworths.com.au/shop/browse/bakery/bakery-specials"
    ),
    CategoryConfig(
        name="Freezer",
        slug="frozen",
        url="https://www.woolworths.com.au/shop/browse/freezer/freezer-specials"
    ),
    CategoryConfig(
        name="Pantry",
        slug="pantry",
        url="https://www.woolworths.com.au/shop/browse/pantry/pantry-specials"
    ),
    CategoryConfig(
        name="Snacks & Confectionery",
        slug="snacks-confectionery",
        url="https://www.woolworths.com.au/shop/browse/snacks-confectionery/snacks-confectionery-specials"
    ),
    CategoryConfig(
        name="Drinks",
        slug="drinks",
        url="https://www.woolworths.com.au/shop/browse/drinks/drinks-specials"
    ),
    CategoryConfig(
        name="Beer, Wine & Spirits",
        slug="liquor",
        url="https://www.woolworths.com.au/shop/browse/beer-wine-spirits/beer-wine-spirits-specials"
    ),
    CategoryConfig(
        name="Health & Wellness",
        slug="health-wellness",
        url="https://www.woolworths.com.au/shop/browse/health-wellness/health-wellness-specials"
    ),
    CategoryConfig(
        name="Beauty",
        slug="beauty",
        url="https://www.woolworths.com.au/shop/browse/beauty/beauty-specials"
    ),
    CategoryConfig(
        name="Personal Care",
        slug="personal-care",
        url="https://www.woolworths.com.au/shop/browse/personal-care/personal-care-specials"
    ),
    CategoryConfig(
        name="Baby",
        slug="baby",
        url="https://www.woolworths.com.au/shop/browse/baby/baby-specials"
    ),
    CategoryConfig(
        name="Pet",
        slug="pet",
        url="https://www.woolworths.com.au/shop/browse/pet/pet-specials"
    ),
    CategoryConfig(
        name="Cleaning & Maintenance",
        slug="household",
        url="https://www.woolworths.com.au/shop/browse/cleaning-maintenance/cleaning-maintenance-specials"
    ),
    CategoryConfig(
        name="Lunch Box",
        slug="lunch-box",
        url="https://www.woolworths.com.au/shop/browse/lunch-box/lunch-box-specials"
    ),
    CategoryConfig(
        name="International Foods",
        slug="international-foods",
        url="https://www.woolworths.com.au/shop/browse/international-foods/international-foods-specials"
    ),
]

# ============== COLES CATEGORY CONFIGURATION ==============
COLES_CATEGORIES = [
    CategoryConfig(
        name="Fruit & Vegetables",
        slug="fruit-veg",
        url="https://www.coles.com.au/on-special/fruit-vegetables"
    ),
    CategoryConfig(
        name="Meat & Seafood",
        slug="meat-seafood",
        url="https://www.coles.com.au/on-special/meat-seafood"
    ),
    CategoryConfig(
        name="Dairy, Eggs & Fridge",
        slug="dairy-eggs-fridge",
        url="https://www.coles.com.au/on-special/dairy-eggs-fridge"
    ),
    CategoryConfig(
        name="Bakery",
        slug="bakery",
        url="https://www.coles.com.au/on-special/bakery"
    ),
    CategoryConfig(
        name="Deli & Chilled Meals",
        slug="deli",
        url="https://www.coles.com.au/on-special/deli-chilled-meals"
    ),
    CategoryConfig(
        name="Pantry",
        slug="pantry",
        url="https://www.coles.com.au/on-special/pantry"
    ),
    CategoryConfig(
        name="Frozen",
        slug="frozen",
        url="https://www.coles.com.au/on-special/frozen"
    ),
    CategoryConfig(
        name="Drinks",
        slug="drinks",
        url="https://www.coles.com.au/on-special/drinks"
    ),
    CategoryConfig(
        name="Liquor",
        slug="liquor",
        url="https://www.coles.com.au/on-special/liquor"
    ),
    CategoryConfig(
        name="Health & Beauty",
        slug="health-beauty",
        url="https://www.coles.com.au/on-special/health-beauty"
    ),
    CategoryConfig(
        name="Household",
        slug="household",
        url="https://www.coles.com.au/on-special/household"
    ),
    CategoryConfig(
        name="Baby",
        slug="baby",
        url="https://www.coles.com.au/on-special/baby"
    ),
    CategoryConfig(
        name="Pet",
        slug="pet",
        url="https://www.coles.com.au/on-special/pet"
    ),
]

# ============== ALDI CONFIGURATION ==============
ALDI_CATEGORIES = [
    CategoryConfig(
        name="Super Savers",
        slug="super-savers",
        url="https://www.aldi.com.au/groceries/super-savers/"
    ),
    CategoryConfig(
        name="Special Buys",
        slug="special-buys",
        url="https://www.aldi.com.au/special-buys/"
    ),
]


class PlaywrightScraper:
    """Base class for Playwright-based scraping."""

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        # Set a reasonable viewport
        await self.page.set_viewport_size({"width": 1920, "height": 1080})
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()

    async def wait_for_content(self, timeout: int = 10000):
        """Wait for main content to load."""
        try:
            await self.page.wait_for_load_state("networkidle", timeout=timeout)
        except PlaywrightTimeout:
            logger.warning("Timeout waiting for network idle, continuing...")

    async def scroll_to_load_all(self, max_scrolls: int = 20):
        """Scroll down to load lazy-loaded content."""
        for _ in range(max_scrolls):
            prev_height = await self.page.evaluate("document.body.scrollHeight")
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(0.5)
            new_height = await self.page.evaluate("document.body.scrollHeight")
            if new_height == prev_height:
                break


class WoolworthsScraper(PlaywrightScraper):
    """Scraper for Woolworths specials."""

    STORE_SLUG = "woolworths"

    def _parse_price(self, price_text: str) -> Optional[Decimal]:
        """Parse price from text like '$3.70' or '$12.00 / 1KG'."""
        if not price_text:
            return None
        match = re.search(r'\$(\d+\.?\d*)', price_text)
        if match:
            try:
                return Decimal(match.group(1))
            except InvalidOperation:
                return None
        return None

    def _parse_savings(self, savings_text: str) -> Optional[Decimal]:
        """Parse savings amount from text like 'SAVE $1.00'."""
        if not savings_text:
            return None
        match = re.search(r'\$(\d+\.?\d*)', savings_text)
        if match:
            try:
                return Decimal(match.group(1))
            except InvalidOperation:
                return None
        return None

    def _extract_size(self, name: str) -> Optional[str]:
        """Extract size from product name like 'Milk 2L' -> '2L'."""
        patterns = [
            r'(\d+\.?\d*\s*[kK][gG])',  # 1kg, 500g
            r'(\d+\.?\d*\s*[gG])',       # 100g
            r'(\d+\.?\d*\s*[mM][lL])',   # 500ml
            r'(\d+\.?\d*\s*[lL])',       # 2L
            r'(\d+\s*[pP]ack)',          # 6 pack
            r'(\d+\s*x\s*\d+)',          # 2 x 60
        ]
        for pattern in patterns:
            match = re.search(pattern, name)
            if match:
                return match.group(1).strip()
        return None

    def _extract_brand(self, name: str) -> Optional[str]:
        """Extract brand from product name (first word if capitalized)."""
        # Common Woolworths own brands
        own_brands = ["Woolworths", "Macro", "Freefrom", "Gold"]
        words = name.split()
        if words:
            first_word = words[0]
            if first_word in own_brands or (first_word[0].isupper() and len(first_word) > 2):
                return first_word
        return None

    async def scrape_category(self, category: CategoryConfig) -> list[ScrapedProduct]:
        """Scrape all products from a category page."""
        products = []

        logger.info(f"Scraping Woolworths category: {category.name}")

        try:
            await self.page.goto(category.url, timeout=30000)
            await self.wait_for_content()
            await asyncio.sleep(2)  # Extra wait for dynamic content

            # Scroll to load all products
            await self.scroll_to_load_all(max_scrolls=10)

            # Get all product cards
            product_cards = await self.page.query_selector_all('[class*="product-tile"]')

            if not product_cards:
                # Try alternative selector
                product_cards = await self.page.query_selector_all('[data-testid="product-tile"]')

            if not product_cards:
                # Try getting products from the grid
                product_cards = await self.page.query_selector_all('section[class*="product-grid"] > div')

            logger.info(f"Found {len(product_cards)} product cards")

            # If we can't find cards, use JavaScript to extract data
            if len(product_cards) == 0:
                products = await self._scrape_via_javascript(category)
            else:
                for card in product_cards:
                    try:
                        product = await self._parse_product_card(card, category.name)
                        if product:
                            products.append(product)
                    except Exception as e:
                        logger.warning(f"Error parsing product card: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error scraping category {category.name}: {e}")

        return products

    async def _scrape_via_javascript(self, category: CategoryConfig) -> list[ScrapedProduct]:
        """Extract product data using JavaScript when DOM parsing fails."""
        products = []

        # Use page.evaluate to extract all product data
        product_data = await self.page.evaluate("""
            () => {
                const products = [];

                // Find all product links with price info
                const productLinks = document.querySelectorAll('a[href*="/shop/productdetails/"]');

                for (const link of productLinks) {
                    try {
                        const container = link.closest('[class*="product"]') || link.parentElement?.parentElement;
                        if (!container) continue;

                        // Get product name from link text
                        const nameEl = container.querySelector('a[href*="/shop/productdetails/"]');
                        const name = nameEl?.textContent?.trim() || '';

                        // Skip if no name or if it's a navigation link
                        if (!name || name.length < 3) continue;

                        // Get price - look for dollar amounts
                        const priceText = container.textContent;
                        const priceMatch = priceText.match(/\$(\d+\.?\d*)/);
                        const price = priceMatch ? priceMatch[1] : null;

                        // Get was price
                        const wasMatch = priceText.match(/was\s*\$(\d+\.?\d*)/i) ||
                                        priceText.match(/\$(\d+\.?\d*)\s*\/\s*1/);
                        const wasPrice = wasMatch ? wasMatch[1] : null;

                        // Get savings
                        const saveMatch = priceText.match(/SAVE\s*\$(\d+\.?\d*)/i);
                        const savings = saveMatch ? saveMatch[1] : null;

                        // Get image
                        const img = container.querySelector('img[src*="cdn"]');
                        const imageUrl = img?.src || null;

                        // Get product URL
                        const productUrl = nameEl?.href || link.href;

                        // Get special type
                        const specialBadge = container.querySelector('img[alt*="Special"], img[alt*="Price"], img[alt*="Off"]');
                        const specialType = specialBadge?.alt || null;

                        if (price) {
                            products.push({
                                name,
                                price,
                                wasPrice,
                                savings,
                                imageUrl,
                                productUrl,
                                specialType
                            });
                        }
                    } catch (e) {
                        console.error('Error parsing product:', e);
                    }
                }

                // Dedupe by name
                const seen = new Set();
                return products.filter(p => {
                    if (seen.has(p.name)) return false;
                    seen.add(p.name);
                    return true;
                });
            }
        """)

        for data in product_data:
            try:
                product = ScrapedProduct(
                    name=data.get('name', ''),
                    price=Decimal(data['price']) if data.get('price') else Decimal('0'),
                    was_price=Decimal(data['wasPrice']) if data.get('wasPrice') else None,
                    savings=Decimal(data['savings']) if data.get('savings') else None,
                    image_url=data.get('imageUrl'),
                    product_url=data.get('productUrl'),
                    special_type=data.get('specialType'),
                    category_name=category.name,
                    store_slug=self.STORE_SLUG,
                    size=self._extract_size(data.get('name', '')),
                    brand=self._extract_brand(data.get('name', ''))
                )

                # Calculate discount percent if we have was_price
                if product.was_price and product.price and product.was_price > 0:
                    discount = ((product.was_price - product.price) / product.was_price) * 100
                    product.discount_percent = int(discount)

                products.append(product)
            except Exception as e:
                logger.warning(f"Error creating product from JS data: {e}")

        return products

    async def _parse_product_card(self, card, category_name: str) -> Optional[ScrapedProduct]:
        """Parse a single product card element."""
        try:
            # Get product name
            name_el = await card.query_selector('a[href*="/shop/productdetails/"]')
            if not name_el:
                return None

            name = await name_el.inner_text()
            name = name.strip()

            # Get product URL
            product_url = await name_el.get_attribute('href')
            if product_url and not product_url.startswith('http'):
                product_url = f"https://www.woolworths.com.au{product_url}"

            # Get price
            price_el = await card.query_selector('[class*="price"]')
            price_text = await price_el.inner_text() if price_el else ""
            price = self._parse_price(price_text)

            if not price:
                return None

            # Get was price
            was_price_el = await card.query_selector('[class*="was-price"], [class*="strike"]')
            was_price = None
            if was_price_el:
                was_price_text = await was_price_el.inner_text()
                was_price = self._parse_price(was_price_text)

            # Get savings
            savings_el = await card.query_selector('[class*="save"], [class*="saving"]')
            savings = None
            if savings_el:
                savings_text = await savings_el.inner_text()
                savings = self._parse_savings(savings_text)

            # Get image
            img_el = await card.query_selector('img')
            image_url = await img_el.get_attribute('src') if img_el else None

            # Get special type badge
            badge_el = await card.query_selector('img[alt*="Special"], img[alt*="Price"]')
            special_type = None
            if badge_el:
                special_type = await badge_el.get_attribute('alt')

            # Calculate discount percent
            discount_percent = None
            if was_price and price and was_price > 0:
                discount = ((was_price - price) / was_price) * 100
                discount_percent = int(discount)

            return ScrapedProduct(
                name=name,
                price=price,
                was_price=was_price,
                savings=savings,
                discount_percent=discount_percent,
                image_url=image_url,
                product_url=product_url,
                special_type=special_type,
                category_name=category_name,
                store_slug=self.STORE_SLUG,
                size=self._extract_size(name),
                brand=self._extract_brand(name)
            )

        except Exception as e:
            logger.warning(f"Error parsing product card: {e}")
            return None

    async def scrape_all_categories(self) -> dict[str, list[ScrapedProduct]]:
        """Scrape all Woolworths categories."""
        results = {}

        for category in WOOLWORTHS_CATEGORIES:
            products = await self.scrape_category(category)
            results[category.name] = products
            logger.info(f"Scraped {len(products)} products from {category.name}")

            # Small delay between categories to be polite
            await asyncio.sleep(2)

        return results


class ColesScraper(PlaywrightScraper):
    """Scraper for Coles specials."""

    STORE_SLUG = "coles"

    def _parse_price(self, price_text: str) -> Optional[Decimal]:
        """Parse price from Coles format."""
        if not price_text:
            return None
        match = re.search(r'\$?(\d+\.?\d*)', price_text)
        if match:
            try:
                return Decimal(match.group(1))
            except InvalidOperation:
                return None
        return None

    async def scrape_category(self, category: CategoryConfig) -> list[ScrapedProduct]:
        """Scrape products from a Coles category page."""
        products = []

        logger.info(f"Scraping Coles category: {category.name}")

        try:
            await self.page.goto(category.url, timeout=30000)
            await self.wait_for_content()
            await asyncio.sleep(3)

            # Scroll to load all products
            await self.scroll_to_load_all(max_scrolls=15)

            # Extract via JavaScript
            product_data = await self.page.evaluate("""
                () => {
                    const products = [];

                    // Find product tiles
                    const tiles = document.querySelectorAll('[data-testid="product-tile"], .product-tile, [class*="ProductTile"]');

                    for (const tile of tiles) {
                        try {
                            // Get name
                            const nameEl = tile.querySelector('[data-testid="product-title"], .product-title, h2, h3');
                            const name = nameEl?.textContent?.trim() || '';

                            if (!name || name.length < 3) continue;

                            // Get price
                            const priceEl = tile.querySelector('[data-testid="product-pricing"] .price, .product-price, [class*="price"]');
                            const priceText = priceEl?.textContent || tile.textContent;
                            const priceMatch = priceText.match(/\$(\d+\.?\d*)/);
                            const price = priceMatch ? priceMatch[1] : null;

                            // Get was price
                            const wasEl = tile.querySelector('.was-price, [class*="was"], s, strike');
                            const wasPrice = wasEl ? wasEl.textContent.match(/\$?(\d+\.?\d*)/)?.[1] : null;

                            // Get image
                            const img = tile.querySelector('img');
                            const imageUrl = img?.src || null;

                            // Get link
                            const link = tile.querySelector('a[href*="/product/"]');
                            const productUrl = link?.href || null;

                            if (price) {
                                products.push({
                                    name,
                                    price,
                                    wasPrice,
                                    imageUrl,
                                    productUrl
                                });
                            }
                        } catch (e) {
                            console.error('Error:', e);
                        }
                    }

                    return products;
                }
            """)

            for data in product_data:
                try:
                    price = Decimal(data['price']) if data.get('price') else None
                    was_price = Decimal(data['wasPrice']) if data.get('wasPrice') else None

                    if not price:
                        continue

                    discount_percent = None
                    savings = None
                    if was_price and price and was_price > 0:
                        savings = was_price - price
                        discount_percent = int(((was_price - price) / was_price) * 100)

                    products.append(ScrapedProduct(
                        name=data['name'],
                        price=price,
                        was_price=was_price,
                        savings=savings,
                        discount_percent=discount_percent,
                        image_url=data.get('imageUrl'),
                        product_url=data.get('productUrl'),
                        category_name=category.name,
                        store_slug=self.STORE_SLUG
                    ))
                except Exception as e:
                    logger.warning(f"Error creating product: {e}")

        except Exception as e:
            logger.error(f"Error scraping Coles category {category.name}: {e}")

        return products

    async def scrape_all_categories(self) -> dict[str, list[ScrapedProduct]]:
        """Scrape all Coles categories."""
        results = {}

        for category in COLES_CATEGORIES:
            products = await self.scrape_category(category)
            results[category.name] = products
            logger.info(f"Scraped {len(products)} products from {category.name}")
            await asyncio.sleep(2)

        return results


class ALDIScraper(PlaywrightScraper):
    """Scraper for ALDI specials."""

    STORE_SLUG = "aldi"

    async def scrape_category(self, category: CategoryConfig) -> list[ScrapedProduct]:
        """Scrape products from an ALDI page."""
        products = []

        logger.info(f"Scraping ALDI: {category.name}")

        try:
            await self.page.goto(category.url, timeout=30000)
            await self.wait_for_content()
            await asyncio.sleep(3)

            # ALDI uses a different structure
            product_data = await self.page.evaluate("""
                () => {
                    const products = [];

                    // Find product boxes
                    const boxes = document.querySelectorAll('.box--product, [class*="product-box"], .product');

                    for (const box of boxes) {
                        try {
                            const nameEl = box.querySelector('.box--description--header, h4, .product-title');
                            const name = nameEl?.textContent?.trim() || '';

                            if (!name) continue;

                            const priceEl = box.querySelector('.box--price, .price, [class*="price"]');
                            const priceText = priceEl?.textContent || '';
                            const priceMatch = priceText.match(/\$?(\d+\.?\d*)/);
                            const price = priceMatch ? priceMatch[1] : null;

                            const img = box.querySelector('img');
                            const imageUrl = img?.src || null;

                            const link = box.querySelector('a');
                            const productUrl = link?.href || null;

                            if (price) {
                                products.push({
                                    name,
                                    price,
                                    imageUrl,
                                    productUrl
                                });
                            }
                        } catch (e) {}
                    }

                    return products;
                }
            """)

            for data in product_data:
                try:
                    products.append(ScrapedProduct(
                        name=data['name'],
                        price=Decimal(data['price']) if data.get('price') else Decimal('0'),
                        image_url=data.get('imageUrl'),
                        product_url=data.get('productUrl'),
                        category_name=category.name,
                        store_slug=self.STORE_SLUG
                    ))
                except Exception as e:
                    logger.warning(f"Error creating ALDI product: {e}")

        except Exception as e:
            logger.error(f"Error scraping ALDI {category.name}: {e}")

        return products

    async def scrape_all_categories(self) -> dict[str, list[ScrapedProduct]]:
        """Scrape all ALDI categories."""
        results = {}

        for category in ALDI_CATEGORIES:
            products = await self.scrape_category(category)
            results[category.name] = products
            logger.info(f"Scraped {len(products)} products from ALDI {category.name}")
            await asyncio.sleep(2)

        return results


# ============== DATABASE SAVE FUNCTIONS ==============

def save_products_to_db(products: list[ScrapedProduct], store_slug: str) -> dict:
    """Save scraped products to the database."""
    db = SessionLocal()

    try:
        # Get store
        store = db.query(Store).filter(Store.slug == store_slug).first()
        if not store:
            logger.error(f"Store not found: {store_slug}")
            return {"error": f"Store not found: {store_slug}"}

        # Get or create categories
        category_map = {}
        for cat in db.query(Category).all():
            category_map[cat.slug] = cat.id
            category_map[cat.name.lower()] = cat.id

        saved = 0
        updated = 0
        errors = 0

        # Set validity dates
        valid_from = date.today()
        valid_to = valid_from + timedelta(days=7)  # Specials typically valid for a week

        for product in products:
            try:
                # Find category
                category_id = None
                if product.category_name:
                    cat_lower = product.category_name.lower()
                    # Try exact match first
                    for key, cat_id in category_map.items():
                        if cat_lower in key or key in cat_lower:
                            category_id = cat_id
                            break

                # Check if special already exists (by name and store)
                existing = db.query(Special).filter(
                    Special.store_id == store.id,
                    Special.name == product.name
                ).first()

                if existing:
                    # Update existing
                    existing.price = product.price
                    existing.was_price = product.was_price
                    existing.discount_percent = product.discount_percent
                    existing.image_url = product.image_url
                    existing.product_url = product.product_url
                    existing.valid_from = valid_from
                    existing.valid_to = valid_to
                    updated += 1
                else:
                    # Create new special
                    special = Special(
                        store_id=store.id,
                        category_id=category_id,
                        name=product.name,
                        brand=product.brand,
                        size=product.size,
                        price=product.price,
                        was_price=product.was_price,
                        discount_percent=product.discount_percent,
                        unit_price=product.unit_price,
                        image_url=product.image_url,
                        product_url=product.product_url,
                        valid_from=valid_from,
                        valid_to=valid_to,
                        source="playwright"
                    )
                    db.add(special)
                    saved += 1

            except Exception as e:
                logger.error(f"Error saving product {product.name}: {e}")
                errors += 1

        db.commit()

        return {
            "store": store_slug,
            "saved": saved,
            "updated": updated,
            "errors": errors,
            "total": len(products)
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        return {"error": str(e)}

    finally:
        db.close()


# ============== MAIN SCRAPING FUNCTIONS ==============

async def scrape_woolworths() -> dict:
    """Scrape all Woolworths specials."""
    async with WoolworthsScraper() as scraper:
        results = await scraper.scrape_all_categories()

    # Save to database
    all_products = []
    for category_name, products in results.items():
        all_products.extend(products)

    save_result = save_products_to_db(all_products, "woolworths")

    return {
        "categories_scraped": len(results),
        "total_products": len(all_products),
        "db_result": save_result
    }


async def scrape_coles() -> dict:
    """Scrape all Coles specials."""
    async with ColesScraper() as scraper:
        results = await scraper.scrape_all_categories()

    all_products = []
    for category_name, products in results.items():
        all_products.extend(products)

    save_result = save_products_to_db(all_products, "coles")

    return {
        "categories_scraped": len(results),
        "total_products": len(all_products),
        "db_result": save_result
    }


async def scrape_aldi() -> dict:
    """Scrape all ALDI specials."""
    async with ALDIScraper() as scraper:
        results = await scraper.scrape_all_categories()

    all_products = []
    for category_name, products in results.items():
        all_products.extend(products)

    save_result = save_products_to_db(all_products, "aldi")

    return {
        "categories_scraped": len(results),
        "total_products": len(all_products),
        "db_result": save_result
    }


async def scrape_all_stores() -> dict:
    """Scrape specials from all stores."""
    results = {}

    logger.info("Starting Woolworths scrape...")
    results["woolworths"] = await scrape_woolworths()

    logger.info("Starting Coles scrape...")
    results["coles"] = await scrape_coles()

    logger.info("Starting ALDI scrape...")
    results["aldi"] = await scrape_aldi()

    return results


# Entry point for running from command line
if __name__ == "__main__":
    import sys

    async def main():
        if len(sys.argv) > 1:
            store = sys.argv[1].lower()
            if store == "woolworths":
                result = await scrape_woolworths()
            elif store == "coles":
                result = await scrape_coles()
            elif store == "aldi":
                result = await scrape_aldi()
            else:
                print(f"Unknown store: {store}")
                return
        else:
            result = await scrape_all_stores()

        print(f"\nResults: {result}")

    asyncio.run(main())
