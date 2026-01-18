"""
Script to fetch missing product URLs for Woolworths specials.
Uses the Woolworths search API to find product pages.
"""
import sqlite3
import requests
import time
import re
import json
from urllib.parse import quote

# Woolworths search API endpoint
WOOLWORTHS_SEARCH_URL = "https://www.woolworths.com.au/apis/ui/Search/products"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
}


def search_woolworths(product_name: str) -> str | None:
    """Search Woolworths for a product and return its URL if found."""
    # Clean up product name for search
    # Remove size info, special characters, etc.
    search_term = product_name
    # Remove common suffixes like "| 500g", "500g", etc.
    search_term = re.sub(r'\s*\|\s*\d+.*$', '', search_term)
    search_term = re.sub(r'\s+\d+\s*(g|kg|ml|l|pack|pk)\b.*$', '', search_term, flags=re.IGNORECASE)
    # Remove brand repetition and clean up
    search_term = search_term.strip()[:50]  # Limit search term length

    if not search_term:
        return None

    payload = {
        "SearchTerm": search_term,
        "PageSize": 5,
        "PageNumber": 1,
        "SortType": "TraderRelevance",
        "Location": "/shop/search/products",
        "EnableAdReRanking": False,
        "GroupEdm498Products": True,
    }

    try:
        response = requests.post(
            WOOLWORTHS_SEARCH_URL,
            headers=HEADERS,
            json=payload,
            timeout=10
        )

        if response.status_code != 200:
            print(f"  Search failed with status {response.status_code}")
            return None

        data = response.json()
        products = data.get("Products", [])

        if not products:
            # Try a shorter search term
            words = search_term.split()
            if len(words) > 2:
                shorter_term = " ".join(words[:3])
                payload["SearchTerm"] = shorter_term
                response = requests.post(
                    WOOLWORTHS_SEARCH_URL,
                    headers=HEADERS,
                    json=payload,
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    products = data.get("Products", [])

        if products:
            # Get the first matching product
            product = products[0]
            stockcode = product.get("Stockcode")
            url_friendly_name = product.get("UrlFriendlyName", "")

            if stockcode:
                product_url = f"https://www.woolworths.com.au/shop/productdetails/{stockcode}/{url_friendly_name}"
                return product_url

        return None

    except Exception as e:
        print(f"  Error searching: {e}")
        return None


def fetch_missing_urls():
    """Fetch URLs for Woolworths products that don't have them."""
    conn = sqlite3.connect('specials.db')
    cur = conn.cursor()

    # Get Woolworths store ID
    cur.execute("SELECT id FROM stores WHERE slug = 'woolworths'")
    woolworths_id = cur.fetchone()[0]

    # Get products without URLs
    cur.execute("""
        SELECT id, name FROM specials
        WHERE store_id = ? AND (product_url IS NULL OR product_url = '')
    """, (woolworths_id,))

    products = cur.fetchall()
    print(f"Found {len(products)} Woolworths products without URLs")

    updated = 0
    failed = 0

    for i, (product_id, name) in enumerate(products):
        print(f"[{i+1}/{len(products)}] Searching for: {name[:50]}...")

        url = search_woolworths(name)

        if url:
            cur.execute(
                "UPDATE specials SET product_url = ? WHERE id = ?",
                (url, product_id)
            )
            conn.commit()
            updated += 1
            print(f"  Found: {url[:60]}...")
        else:
            failed += 1
            print(f"  Not found")

        # Rate limiting - be nice to the API
        time.sleep(0.5)

        # Progress save every 50 products
        if (i + 1) % 50 == 0:
            print(f"\n--- Progress: {updated} updated, {failed} failed ---\n")

    conn.close()

    print(f"\n=== Complete ===")
    print(f"Updated: {updated}")
    print(f"Failed: {failed}")


if __name__ == "__main__":
    fetch_missing_urls()
