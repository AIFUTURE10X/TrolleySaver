"""
Test script to scrape vegetables from supermarkets.
"""
import os
import re
import json
from dotenv import load_dotenv

load_dotenv()

from firecrawl import Firecrawl

# Initialize Firecrawl
app = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))

# Vegetable URLs - only stores that work
VEGETABLE_URLS = {
    "coles": [
        "https://www.coles.com.au/browse/fruit-vegetables/vegetables",
        "https://www.coles.com.au/browse/fruit-vegetables/vegetables?page=2",
        "https://www.coles.com.au/browse/fruit-vegetables/vegetables?page=3",
    ],
    "aldi": [
        "https://www.aldi.com.au/products/fruits-vegetables/k/950000000",  # Fruit & Vegetables category
    ],
    "iga": [
        "https://www.igashop.com.au/categories/fruit-and-vegetable/vegetables/1",
        "https://www.igashop.com.au/categories/fruit-and-vegetable/vegetables/1?page=2",
        "https://www.igashop.com.au/categories/fruit-and-vegetable/vegetables/1?page=3",
    ],
}


def scrape_url(store_name: str, url: str, page_num: int = 1) -> tuple[list[dict], str]:
    """Scrape vegetables from a URL. Returns (products, markdown)."""
    print(f"  Scraping page {page_num}: {url}")

    try:
        result = app.scrape(url, formats=['markdown'])

        if not result or not result.markdown:
            print(f"  No content from {url}")
            return [], ""

        return [], result.markdown

    except Exception as e:
        print(f"  Error: {e}")
        return [], ""


def parse_coles_vegetables(markdown: str) -> list[dict]:
    """Parse Coles vegetables from markdown."""
    products = []

    # Split by product sections (## headers)
    sections = re.split(r'\n##\s+', markdown)

    for section in sections:
        lines = section.strip().split('\n')
        if not lines:
            continue

        name = lines[0].strip()

        # Skip navigation/promo sections
        if len(name) < 3 or 'Browse' in name or 'category' in name.lower():
            continue
        if 'Shop' in name or 'View' in name or 'Sign' in name or 'Filter' in name:
            continue
        if 'vegetables' in name.lower() and len(name) < 20:
            continue

        # Find product URL
        url_match = re.search(r'\[.*?\]\((https://www\.coles\.com\.au/product/[^)]+)\)', section)
        product_url = url_match.group(1) if url_match else None
        if not product_url:
            continue

        # Find price - looking for $X.XX pattern
        price_match = re.search(r'\$(\d+\.?\d*)', section)
        price = float(price_match.group(1)) if price_match else None

        # Check for "was" price (if on special)
        was_match = re.search(r'Was\s+\$(\d+\.?\d*)', section)
        was_price = float(was_match.group(1)) if was_match else None

        # Extract unit price
        unit_match = re.search(r'\$(\d+\.?\d*)\s*(?:per|/)\s*(kg|each|100g|bunch)', section, re.IGNORECASE)
        unit_price = f"${unit_match.group(1)}/{unit_match.group(2)}" if unit_match else None

        if name and price:
            # Extract product ID from URL
            id_match = re.search(r'-(\d+)$', product_url)
            product_id = id_match.group(1) if id_match else None

            # Construct image URL
            image_url = None
            if product_id:
                first_digit = product_id[0]
                image_url = f"https://productimages.coles.com.au/productimages/{first_digit}/{product_id}.jpg"

            products.append({
                'name': name.replace('\\|', '|').strip(),
                'price': price,
                'was_price': was_price,
                'unit_price': unit_price,
                'product_url': product_url,
                'product_id': product_id,
                'image_url': image_url,
                'store': 'coles'
            })

    return products


def parse_aldi_products(markdown: str) -> list[dict]:
    """Parse ALDI products from markdown - fresh produce format without brand."""
    products = []
    seen_urls = set()

    # Pattern for ALDI fresh produce (no brand, just product name)
    # Format: [Product Name\\\nsize\\\n(unit_price)\\\n$price](url)
    # Or: [Product Name\\\nsize\\\n(unit_price)\\\n$price/size](url) for loose items

    # Find all product links
    product_links = re.findall(
        r'\[([^\]]+)\]\((https://www\.aldi\.com\.au/product/[^\)]+)\)',
        markdown
    )

    for link_text, url in product_links:
        if url in seen_urls:
            continue

        # Skip navigation links
        if 'Fresh Fruits' in link_text or 'Fresh Herbs' in link_text:
            continue
        if 'Fresh Vegetables' in link_text or 'Salads' in link_text:
            continue
        if 'Prepared Vegetables' in link_text:
            continue

        # Parse the link text - split by \\ or newlines
        parts = re.split(r'\\+\n*', link_text)
        parts = [p.strip() for p in parts if p.strip()]

        if len(parts) < 2:
            continue

        name = parts[0]

        # Find price - look for $X.XX pattern
        price = None
        for part in parts:
            # Handle "$X.XX" or "$X.XX/size" patterns
            price_match = re.search(r'\$(\d+\.?\d*)', part)
            if price_match:
                price = float(price_match.group(1))

        # Find size (usually second part)
        size = parts[1] if len(parts) > 1 and not parts[1].startswith('(') and not parts[1].startswith('$') else None

        if name and price:
            seen_urls.add(url)
            products.append({
                'name': name.strip(),
                'price': price,
                'size': size,
                'product_url': url,
                'store': 'aldi'
            })

    return products


def parse_iga_vegetables(markdown: str) -> list[dict]:
    """Parse IGA Shop vegetables from markdown."""
    products = []
    seen_urls = set()

    # IGA format: [![Name](image)](url) [NameSize](url) price unit_price
    # Or simpler: [NameSize](url) was $X.XX $price $unit_price

    # Find product links - they contain /product/ in the URL
    product_pattern = re.compile(
        r'\[([^\]]+)\]\((https://www\.igashop\.com\.au/product/[^\)]+)\)',
        re.MULTILINE
    )

    # Split markdown into product sections
    sections = markdown.split('Add to Cart')

    for section in sections:
        # Find product link in this section
        matches = product_pattern.findall(section)
        if not matches:
            continue

        # Get the product name link (skip image links)
        product_url = None
        name = None
        for match_name, match_url in matches:
            if match_url in seen_urls:
                continue
            # Skip if it's just the image link (usually has image.png in alt)
            if 'default-product-image' not in match_name and match_url not in seen_urls:
                # Extract name and size - format is "Product NameSize" e.g. "Baby Capsicums175 Gram"
                # Try to split name from size
                size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:Gram|Kg|Each|Pack|Bunch|g|kg))', match_name, re.IGNORECASE)
                if size_match:
                    size = size_match.group(1)
                    name = match_name[:size_match.start()].strip()
                else:
                    name = match_name.strip()
                    size = None
                product_url = match_url
                break

        if not name or not product_url or product_url in seen_urls:
            continue

        # Find prices in section
        # Look for "was $X.XX" pattern for specials
        was_match = re.search(r'was\s+\$(\d+\.?\d*)', section, re.IGNORECASE)
        was_price = float(was_match.group(1)) if was_match else None

        # Find current price - usually after "was" or standalone
        # Format: $X.XX or $X.XX followed by unit price
        price_matches = re.findall(r'\$(\d+\.?\d*)', section)
        price = None
        for p in price_matches:
            p_float = float(p)
            # Skip if it's the was_price or a unit price (per 100g etc)
            if was_price and abs(p_float - was_price) < 0.01:
                continue
            # Unit prices are usually small per-unit values, skip those if we already have a price
            if price is None:
                price = p_float
            elif p_float > price and p_float < 50:  # Skip obvious unit prices
                price = p_float

        # Extract unit price
        unit_match = re.search(r'\$(\d+\.?\d*)\s*per\s*(100g|kg|each)', section, re.IGNORECASE)
        unit_price = f"${unit_match.group(1)}/per {unit_match.group(2)}" if unit_match else None

        if name and price:
            seen_urls.add(product_url)
            products.append({
                'name': name,
                'price': price,
                'was_price': was_price,
                'size': size if 'size' in dir() else None,
                'unit_price': unit_price,
                'product_url': product_url,
                'store': 'iga'
            })

    return products


def is_vegetable(name: str) -> bool:
    """Check if a product name is likely a vegetable."""
    name_lower = name.lower()

    # Common vegetables
    vegetables = [
        'potato', 'tomato', 'onion', 'carrot', 'broccoli', 'cauliflower',
        'cabbage', 'lettuce', 'spinach', 'kale', 'celery', 'cucumber',
        'capsicum', 'pepper', 'zucchini', 'eggplant', 'pumpkin', 'squash',
        'bean', 'pea', 'corn', 'asparagus', 'mushroom', 'leek', 'garlic',
        'ginger', 'beetroot', 'radish', 'turnip', 'parsnip', 'sweet potato',
        'avocado', 'chilli', 'spring onion', 'shallot', 'bok choy', 'choy sum',
        'sprout', 'artichoke', 'fennel', 'rocket', 'watercress', 'herbs',
        'basil', 'parsley', 'coriander', 'mint', 'dill', 'thyme', 'rosemary'
    ]

    for veg in vegetables:
        if veg in name_lower:
            return True

    return False


def main():
    all_products = {'coles': [], 'aldi': [], 'iga': []}
    all_markdown = {}

    # Scrape Coles
    print("\n" + "="*60)
    print("COLES - Vegetables")
    print("="*60)
    coles_markdown = ""
    for i, url in enumerate(VEGETABLE_URLS["coles"], 1):
        _, markdown = scrape_url("coles", url, i)
        coles_markdown += markdown
        products = parse_coles_vegetables(markdown)
        all_products['coles'].extend(products)
        print(f"  Found {len(products)} products on page {i}")

    # Save combined markdown
    with open("debug_coles_all.md", "w", encoding="utf-8") as f:
        f.write(coles_markdown)

    # Deduplicate by product_id
    seen_ids = set()
    unique_coles = []
    for p in all_products['coles']:
        if p['product_id'] and p['product_id'] not in seen_ids:
            seen_ids.add(p['product_id'])
            unique_coles.append(p)
        elif not p['product_id']:
            unique_coles.append(p)
    all_products['coles'] = unique_coles

    print(f"\nCOLES TOTAL: {len(all_products['coles'])} unique vegetables")

    # Scrape ALDI
    print("\n" + "="*60)
    print("ALDI - Fruit & Vegetables")
    print("="*60)
    for i, url in enumerate(VEGETABLE_URLS["aldi"], 1):
        _, markdown = scrape_url("aldi", url, i)
        all_markdown['aldi'] = markdown

        # Save markdown
        with open("debug_aldi_produce.md", "w", encoding="utf-8") as f:
            f.write(markdown)

        products = parse_aldi_products(markdown)

        # Filter to only vegetables
        vegetables = [p for p in products if is_vegetable(p['name'])]
        all_products['aldi'] = vegetables
        print(f"  Found {len(products)} total products, {len(vegetables)} vegetables")

    # Scrape IGA
    print("\n" + "="*60)
    print("IGA SHOP - Vegetables")
    print("="*60)
    iga_markdown = ""
    for i, url in enumerate(VEGETABLE_URLS["iga"], 1):
        _, markdown = scrape_url("iga", url, i)
        iga_markdown += markdown
        products = parse_iga_vegetables(markdown)
        all_products['iga'].extend(products)
        print(f"  Found {len(products)} products on page {i}")

    # Save IGA markdown
    with open("debug_iga_all.md", "w", encoding="utf-8") as f:
        f.write(iga_markdown)

    # Deduplicate IGA by URL
    seen_urls = set()
    unique_iga = []
    for p in all_products['iga']:
        if p['product_url'] not in seen_urls:
            seen_urls.add(p['product_url'])
            unique_iga.append(p)
    all_products['iga'] = unique_iga

    print(f"\nIGA TOTAL: {len(all_products['iga'])} unique vegetables")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY - TOP VEGETABLES")
    print("="*60)

    # Combine and sort by price
    all_vegetables = []
    for store, products in all_products.items():
        all_vegetables.extend(products)

    # Sort by price
    all_vegetables.sort(key=lambda x: x['price'])

    print(f"\nTotal vegetables found: {len(all_vegetables)}")
    print("\nTop 30 cheapest vegetables:")
    print("-" * 80)

    for i, veg in enumerate(all_vegetables[:30], 1):
        store = veg['store'].upper()
        price = f"${veg['price']:.2f}"
        was = f" (was ${veg['was_price']:.2f})" if veg.get('was_price') else ""
        unit = f" - {veg['unit_price']}" if veg.get('unit_price') else ""
        print(f"{i:2}. [{store:6}] {price:8}{was:15} {veg['name'][:50]}{unit}")

    # Save results
    results = {
        'coles': all_products['coles'],
        'aldi': all_products['aldi'],
        'iga': all_products['iga'],
        'top_30': all_vegetables[:30]
    }

    with open("vegetables_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\nFull results saved to vegetables_results.json")

    # Note about stores not available
    print("\n" + "="*60)
    print("NOTES")
    print("="*60)
    print("- Woolworths: JavaScript-heavy site, requires special handling")
    print("- ALDI: Limited fresh produce listings online")
    print("- IGA: Prices may vary by store location")


if __name__ == "__main__":
    main()
