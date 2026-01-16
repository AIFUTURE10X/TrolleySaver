"""
Playwright-based specials scraper using the MCP browser tools.

This script extracts specials data from supermarket websites and saves
them to the database. Designed to be run category by category.
"""
import re
import json
import logging
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta
from dataclasses import dataclass, asdict
from typing import Optional

from app.database import SessionLocal
from app.models import Store, Category, Special

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ProductData:
    """Extracted product data."""
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
    special_type: Optional[str] = None
    category_name: Optional[str] = None


# Woolworths category URL mappings
WOOLWORTHS_CATEGORIES = {
    "fruit-veg": "https://www.woolworths.com.au/shop/browse/fruit-veg/fruit-veg-specials",
    "meat-seafood": "https://www.woolworths.com.au/shop/browse/poultry-meat-seafood/poultry-meat-seafood-specials",
    "deli": "https://www.woolworths.com.au/shop/browse/deli/deli-specials",
    "dairy-eggs-fridge": "https://www.woolworths.com.au/shop/browse/dairy-eggs-fridge/dairy-eggs-fridge-specials",
    "bakery": "https://www.woolworths.com.au/shop/browse/bakery/bakery-specials",
    "frozen": "https://www.woolworths.com.au/shop/browse/freezer/freezer-specials",
    "pantry": "https://www.woolworths.com.au/shop/browse/pantry/pantry-specials",
    "snacks-confectionery": "https://www.woolworths.com.au/shop/browse/snacks-confectionery/snacks-confectionery-specials",
    "drinks": "https://www.woolworths.com.au/shop/browse/drinks/drinks-specials",
    "liquor": "https://www.woolworths.com.au/shop/browse/beer-wine-spirits/beer-wine-spirits-specials",
    "health-wellness": "https://www.woolworths.com.au/shop/browse/health-wellness/health-wellness-specials",
    "beauty": "https://www.woolworths.com.au/shop/browse/beauty/beauty-specials",
    "personal-care": "https://www.woolworths.com.au/shop/browse/personal-care/personal-care-specials",
    "baby": "https://www.woolworths.com.au/shop/browse/baby/baby-specials",
    "pet": "https://www.woolworths.com.au/shop/browse/pet/pet-specials",
    "household": "https://www.woolworths.com.au/shop/browse/cleaning-maintenance/cleaning-maintenance-specials",
    "lunch-box": "https://www.woolworths.com.au/shop/browse/lunch-box/lunch-box-specials",
}

# Coles category URL mappings
COLES_CATEGORIES = {
    "fruit-veg": "https://www.coles.com.au/on-special/fruit-vegetables",
    "meat-seafood": "https://www.coles.com.au/on-special/meat-seafood",
    "dairy-eggs-fridge": "https://www.coles.com.au/on-special/dairy-eggs-fridge",
    "bakery": "https://www.coles.com.au/on-special/bakery",
    "deli": "https://www.coles.com.au/on-special/deli-chilled-meals",
    "pantry": "https://www.coles.com.au/on-special/pantry",
    "frozen": "https://www.coles.com.au/on-special/frozen",
    "drinks": "https://www.coles.com.au/on-special/drinks",
    "liquor": "https://www.coles.com.au/on-special/liquor",
    "health-beauty": "https://www.coles.com.au/on-special/health-beauty",
    "household": "https://www.coles.com.au/on-special/household",
    "baby": "https://www.coles.com.au/on-special/baby",
    "pet": "https://www.coles.com.au/on-special/pet",
}


def parse_woolworths_products(raw_data: list[dict], category_slug: str) -> list[ProductData]:
    """
    Parse raw Woolworths product data into structured ProductData objects.

    Handles the complex pricing format from Woolworths pages.
    """
    products = []

    for item in raw_data:
        try:
            name = item.get('name', '').strip()
            if not name:
                continue

            # Parse the link text which contains pricing info
            link_text = item.get('linkText', '')

            # Try to extract the actual price
            # The link text format is like: "Product Name. 2 for $5.00. Non-member price $3.7, $3.70 / 1EA"
            # Or: "Product Name. Save $1.00. Product, $2.00, Was $3.00, $16.67 / 1KG"

            price = None
            was_price = None
            savings = None
            unit_price = None

            # Get raw price and was_price from item
            raw_price = item.get('price')
            raw_was = item.get('wasPrice')
            raw_savings = item.get('savings')

            # If we have savings, the actual price is was_price - savings
            # Or we can get it from the non-member price
            if raw_savings and raw_was:
                try:
                    was_price = Decimal(raw_was)
                    savings = Decimal(raw_savings)
                    price = was_price - savings
                except (InvalidOperation, TypeError):
                    pass
            elif raw_price:
                try:
                    price = Decimal(raw_price)
                except (InvalidOperation, TypeError):
                    pass

            # If still no price, try parsing from link text
            if not price and link_text:
                # Look for "Non-member price $X" pattern
                member_match = re.search(r'Non-member price \$(\d+\.?\d*)', link_text)
                if member_match:
                    try:
                        price = Decimal(member_match.group(1))
                    except InvalidOperation:
                        pass

                # Or look for the main price pattern
                if not price:
                    price_match = re.search(r'\$(\d+\.?\d*)', link_text)
                    if price_match:
                        try:
                            price = Decimal(price_match.group(1))
                        except InvalidOperation:
                            pass

            # Skip if we couldn't determine a valid price
            if not price or price <= 0:
                continue

            # Extract unit price
            unit_match = re.search(r'\$[\d.]+\s*\/\s*(\d*\s*)?(KG|100G|1L|1EA|100ML)', link_text, re.IGNORECASE)
            if unit_match:
                unit_price = unit_match.group(0)

            # Extract size from name
            size = extract_size(name)

            # Extract brand
            brand = extract_brand(name)

            # Calculate discount percent
            discount_percent = None
            if was_price and price and was_price > price:
                discount_percent = int(((was_price - price) / was_price) * 100)

            # Build full URL
            url = item.get('url', '')
            if url and not url.startswith('http'):
                url = f"https://www.woolworths.com.au{url}"

            products.append(ProductData(
                name=name,
                price=price,
                was_price=was_price,
                savings=savings,
                discount_percent=discount_percent,
                unit_price=unit_price,
                size=size,
                brand=brand,
                product_url=url,
                category_name=category_slug
            ))

        except Exception as e:
            logger.warning(f"Error parsing product: {e}")
            continue

    return products


def extract_size(name: str) -> Optional[str]:
    """Extract size from product name."""
    patterns = [
        r'(\d+\.?\d*\s*[kK][gG])',      # 1kg, 500g
        r'(\d+\.?\d*\s*[gG](?![rR]))',  # 100g (not "gr")
        r'(\d+\.?\d*\s*[mM][lL])',      # 500ml
        r'(\d+\.?\d*\s*[lL](?![iI]))',  # 2L (not "li")
        r'(\d+\s*[pP]ack)',             # 6 pack
        r'(\d+\s*x\s*\d+)',             # 2 x 60
    ]
    for pattern in patterns:
        match = re.search(pattern, name)
        if match:
            return match.group(1).strip()
    return None


def extract_brand(name: str) -> Optional[str]:
    """Extract brand from product name."""
    # Common supermarket brands
    known_brands = [
        "Woolworths", "Coles", "ALDI", "Black & Gold",
        "Macro", "Freefrom", "Gold", "Essentials"
    ]

    words = name.split()
    if words:
        first_word = words[0]
        # Check if it's a known brand
        if first_word in known_brands:
            return first_word
        # Or if it looks like a brand (capitalized, reasonable length)
        if first_word[0].isupper() and len(first_word) > 2 and first_word.isalpha():
            return first_word
    return None


def save_products_to_database(
    products: list[ProductData],
    store_slug: str,
    category_slug: str
) -> dict:
    """Save parsed products to the database."""
    db = SessionLocal()

    try:
        # Get store
        store = db.query(Store).filter(Store.slug == store_slug).first()
        if not store:
            logger.error(f"Store not found: {store_slug}")
            return {"error": f"Store not found: {store_slug}"}

        # Get category
        category = db.query(Category).filter(Category.slug == category_slug).first()
        category_id = category.id if category else None

        # Set validity dates (specials typically valid for 1 week)
        valid_from = date.today()
        valid_to = valid_from + timedelta(days=7)

        saved = 0
        updated = 0
        errors = 0

        for product in products:
            try:
                # Check if special already exists
                existing = db.query(Special).filter(
                    Special.store_id == store.id,
                    Special.name == product.name
                ).first()

                if existing:
                    # Update existing
                    existing.price = product.price
                    existing.was_price = product.was_price
                    existing.discount_percent = product.discount_percent
                    existing.unit_price = product.unit_price
                    existing.product_url = product.product_url
                    existing.valid_from = valid_from
                    existing.valid_to = valid_to
                    updated += 1
                else:
                    # Create new
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
            "category": category_slug,
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


# JavaScript code for extracting Woolworths products
WOOLWORTHS_EXTRACT_JS = """
async (page) => {
    const products = [];

    // Get all "Find out more about" links which identify products
    const productLinks = await page.getByRole('link', { name: /Find out more about/ }).all();

    for (const link of productLinks) {
        try {
            const name = await link.textContent();
            const href = await link.getAttribute('href');

            // Get the product container (go up several levels)
            const container = await link.evaluateHandle(el => {
                let node = el;
                for (let i = 0; i < 6 && node.parentElement; i++) {
                    node = node.parentElement;
                }
                return node;
            });

            const containerText = await container.evaluate(el => el?.textContent || '');

            // Get the full link text which contains pricing info
            const fullLink = await container.evaluate(el => {
                const links = el.querySelectorAll('a');
                for (const link of links) {
                    if (link.textContent?.includes('$')) {
                        return link.textContent;
                    }
                }
                return '';
            });

            // Extract prices more carefully
            // Look for patterns like: "$3.70" for current price
            // "Was $4.50" or "$4.50" after current price for was_price
            // "SAVE $0.50" for savings

            let price = null;
            let wasPrice = null;
            let savings = null;

            // Get savings first
            const saveMatch = containerText.match(/SAVE\\s*\\$([\\d.]+)/i);
            if (saveMatch) {
                savings = saveMatch[1];
            }

            // Find all dollar amounts
            const allPrices = containerText.match(/\\$([\\d.]+)/g) || [];
            const priceValues = allPrices.map(p => parseFloat(p.replace('$', '')));

            if (savings) {
                // If there's savings, the format is usually: SAVE $X, $currentPrice, $wasPrice
                // Or: $currentPrice, $wasPrice
                // The was_price is typically the second unique price
                const uniquePrices = [...new Set(priceValues)].sort((a, b) => a - b);
                if (uniquePrices.length >= 2) {
                    // Current price is usually the smaller one (discounted)
                    // Was price is the larger one
                    const savingsAmount = parseFloat(savings);
                    for (let i = 0; i < uniquePrices.length - 1; i++) {
                        if (Math.abs(uniquePrices[i + 1] - uniquePrices[i] - savingsAmount) < 0.01) {
                            price = uniquePrices[i].toFixed(2);
                            wasPrice = uniquePrices[i + 1].toFixed(2);
                            break;
                        }
                    }
                    // Fallback
                    if (!price) {
                        price = uniquePrices[0].toFixed(2);
                        wasPrice = uniquePrices[uniquePrices.length - 1].toFixed(2);
                    }
                }
            } else {
                // No savings, just get the first price
                if (priceValues.length > 0) {
                    price = priceValues[0].toFixed(2);
                }
            }

            // Get image URL
            const imageUrl = await container.evaluate(el => {
                const img = el.querySelector('img[src*="cdn"]');
                return img?.src || null;
            });

            if (name && (price || priceValues.length > 0)) {
                products.push({
                    name: name.trim(),
                    url: href,
                    price: price || (priceValues[0] ? priceValues[0].toFixed(2) : null),
                    wasPrice,
                    savings,
                    linkText: fullLink,
                    imageUrl
                });
            }
        } catch (e) {
            console.log('Error:', e.message);
        }
    }

    return products;
}
"""


def get_extraction_script(store: str) -> str:
    """Get the JavaScript extraction script for a store."""
    if store == "woolworths":
        return WOOLWORTHS_EXTRACT_JS
    elif store == "coles":
        return COLES_EXTRACT_JS
    else:
        raise ValueError(f"Unknown store: {store}")


# Coles extraction script (different structure)
COLES_EXTRACT_JS = """
async (page) => {
    const products = [];

    // Coles uses different selectors
    const tiles = await page.locator('[data-testid="product-tile"]').all();

    for (const tile of tiles) {
        try {
            // Get product name
            const nameEl = await tile.locator('[data-testid="product-title"]').first();
            const name = await nameEl.textContent();

            // Get price
            const priceEl = await tile.locator('.price, [class*="price"]').first();
            const priceText = await priceEl.textContent();
            const priceMatch = priceText.match(/\\$([\\d.]+)/);
            const price = priceMatch ? priceMatch[1] : null;

            // Get was price if exists
            const wasEl = await tile.locator('.was-price, s').first().catch(() => null);
            let wasPrice = null;
            if (wasEl) {
                const wasText = await wasEl.textContent();
                const wasMatch = wasText.match(/\\$?([\\d.]+)/);
                wasPrice = wasMatch ? wasMatch[1] : null;
            }

            // Get product URL
            const link = await tile.locator('a[href*="/product/"]').first();
            const url = await link.getAttribute('href');

            // Get image
            const img = await tile.locator('img').first();
            const imageUrl = await img.getAttribute('src');

            if (name && price) {
                products.push({
                    name: name.trim(),
                    url,
                    price,
                    wasPrice,
                    imageUrl
                });
            }
        } catch (e) {
            console.log('Error:', e.message);
        }
    }

    return products;
}
"""
