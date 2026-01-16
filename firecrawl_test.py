"""
Firecrawl Test Script for Australian Supermarket Price Scraping
================================================================

This script tests Firecrawl's ability to scrape specials/catalogue data
from Woolworths, Coles, and ALDI Australia.

Prerequisites:
    pip install firecrawl-py python-dotenv

Setup:
    1. Get API key from https://firecrawl.dev
    2. Create .env file with: FIRECRAWL_API_KEY=your_key_here
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import firecrawl
try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False
    print("⚠️  Firecrawl not installed. Run: pip install firecrawl-py")


# Australian Supermarket URLs to test
TARGETS = {
    "woolworths": {
        "specials": "https://www.woolworths.com.au/shop/browse/specials",
        "half_price": "https://www.woolworths.com.au/shop/browse/specials/half-price",
        "catalogue": "https://www.woolworths.com.au/shop/catalogue",
    },
    "coles": {
        "specials": "https://www.coles.com.au/on-special",
        "half_price": "https://www.coles.com.au/on-special/half-price",
        "catalogue": "https://www.coles.com.au/catalogues-and-specials",
    },
    "aldi": {
        "specials": "https://www.aldi.com.au/en/special-buys/",
        "groceries": "https://www.aldi.com.au/en/groceries/",
    }
}


def test_firecrawl_scrape(url: str, store_name: str) -> dict:
    """
    Test Firecrawl's ability to scrape a single URL.

    Returns dict with:
        - success: bool
        - content_length: int (markdown length)
        - has_prices: bool (found $ symbols)
        - has_products: bool (found product-like content)
        - sample: str (first 500 chars)
        - error: str (if failed)
    """
    result = {
        "url": url,
        "store": store_name,
        "timestamp": datetime.now().isoformat(),
        "success": False,
        "content_length": 0,
        "has_prices": False,
        "has_products": False,
        "sample": "",
        "error": None
    }

    if not FIRECRAWL_AVAILABLE:
        result["error"] = "Firecrawl not installed"
        return result

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        result["error"] = "FIRECRAWL_API_KEY not set in environment"
        return result

    try:
        app = FirecrawlApp(api_key=api_key)

        # Scrape with Firecrawl
        scraped = app.scrape_url(
            url,
            params={
                "formats": ["markdown", "html"],
                "waitFor": 3000,  # Wait for JS to load
                "timeout": 30000,
            }
        )

        if scraped and "markdown" in scraped:
            markdown = scraped["markdown"]
            result["success"] = True
            result["content_length"] = len(markdown)
            result["has_prices"] = "$" in markdown
            result["has_products"] = any(word in markdown.lower() for word in
                ["save", "special", "price", "half price", "% off"])
            result["sample"] = markdown[:500]
            result["full_content"] = markdown  # Store full content for analysis

    except Exception as e:
        result["error"] = str(e)

    return result


def test_firecrawl_crawl(base_url: str, store_name: str, max_pages: int = 5) -> dict:
    """
    Test Firecrawl's crawl feature to discover multiple pages.
    """
    result = {
        "base_url": base_url,
        "store": store_name,
        "timestamp": datetime.now().isoformat(),
        "success": False,
        "pages_found": 0,
        "urls_discovered": [],
        "error": None
    }

    if not FIRECRAWL_AVAILABLE:
        result["error"] = "Firecrawl not installed"
        return result

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        result["error"] = "FIRECRAWL_API_KEY not set in environment"
        return result

    try:
        app = FirecrawlApp(api_key=api_key)

        # Crawl with limits
        crawl_result = app.crawl_url(
            base_url,
            params={
                "limit": max_pages,
                "scrapeOptions": {
                    "formats": ["markdown"]
                }
            },
            poll_interval=5
        )

        if crawl_result:
            result["success"] = True
            result["pages_found"] = len(crawl_result.get("data", []))
            result["urls_discovered"] = [
                page.get("metadata", {}).get("url", "unknown")
                for page in crawl_result.get("data", [])
            ]

    except Exception as e:
        result["error"] = str(e)

    return result


def run_all_tests():
    """Run scrape tests against all supermarket targets."""
    results = {
        "test_run": datetime.now().isoformat(),
        "scrape_results": [],
        "summary": {
            "total_tests": 0,
            "successful": 0,
            "found_prices": 0,
            "found_products": 0,
            "blocked": 0
        }
    }

    print("=" * 60)
    print("🛒 Australian Supermarket Firecrawl Test")
    print("=" * 60)

    for store, urls in TARGETS.items():
        print(f"\n📍 Testing {store.upper()}...")

        for page_type, url in urls.items():
            print(f"   → {page_type}: {url}")

            result = test_firecrawl_scrape(url, store)
            results["scrape_results"].append(result)
            results["summary"]["total_tests"] += 1

            if result["success"]:
                results["summary"]["successful"] += 1
                status = "✅"
            else:
                results["summary"]["blocked"] += 1
                status = "❌"

            if result["has_prices"]:
                results["summary"]["found_prices"] += 1
            if result["has_products"]:
                results["summary"]["found_products"] += 1

            print(f"      {status} Content: {result['content_length']} chars | "
                  f"Prices: {result['has_prices']} | Products: {result['has_products']}")

            if result["error"]:
                print(f"      ⚠️  Error: {result['error']}")

    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    s = results["summary"]
    print(f"   Total Tests:    {s['total_tests']}")
    print(f"   Successful:     {s['successful']}")
    print(f"   Found Prices:   {s['found_prices']}")
    print(f"   Found Products: {s['found_products']}")
    print(f"   Blocked/Failed: {s['blocked']}")

    # Save results
    output_file = "firecrawl_test_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n💾 Results saved to: {output_file}")

    return results


def extract_product_data(markdown_content: str) -> list:
    """
    Attempt to extract product data from scraped markdown.

    This is a basic extractor - would need refinement based on
    actual page structure.
    """
    import re

    products = []

    # Look for price patterns like "$X.XX" or "$ X.XX"
    price_pattern = r'\$\s*(\d+\.?\d*)'

    # Split content into lines and look for price + product combos
    lines = markdown_content.split('\n')

    for i, line in enumerate(lines):
        prices = re.findall(price_pattern, line)
        if prices:
            # Try to get product name from nearby content
            product_name = line
            # Clean up the product name
            product_name = re.sub(price_pattern, '', product_name).strip()
            product_name = re.sub(r'[#*\[\]]', '', product_name).strip()

            if product_name and len(product_name) > 3:
                products.append({
                    "name": product_name[:100],  # Limit length
                    "prices_found": prices,
                    "raw_line": line[:200]
                })

    return products


# Alternative: Using requests + BeautifulSoup as fallback
def test_basic_scrape(url: str) -> dict:
    """
    Basic scrape test without Firecrawl to compare results.
    Uses requests + BeautifulSoup.
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return {"error": "requests/beautifulsoup4 not installed"}

    result = {
        "url": url,
        "success": False,
        "status_code": None,
        "content_length": 0,
        "error": None
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-AU,en;q=0.9",
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        result["status_code"] = response.status_code
        result["content_length"] = len(response.text)
        result["success"] = response.status_code == 200

        if result["success"]:
            soup = BeautifulSoup(response.text, "html.parser")
            # Check if we got actual content or a block page
            result["title"] = soup.title.string if soup.title else "No title"
            result["has_prices"] = "$" in response.text

    except Exception as e:
        result["error"] = str(e)

    return result


if __name__ == "__main__":
    print("\n🔧 Configuration Check:")
    print(f"   Firecrawl installed: {FIRECRAWL_AVAILABLE}")
    print(f"   API Key set: {bool(os.getenv('FIRECRAWL_API_KEY'))}")

    if not FIRECRAWL_AVAILABLE:
        print("\n📦 To install Firecrawl:")
        print("   pip install firecrawl-py python-dotenv beautifulsoup4 requests")
        print("\n🔑 To set up API key:")
        print("   1. Get key from https://firecrawl.dev")
        print("   2. Create .env file with: FIRECRAWL_API_KEY=your_key")

    # Run basic tests first (no API key needed)
    print("\n" + "=" * 60)
    print("🧪 Basic HTTP Test (no Firecrawl)")
    print("=" * 60)

    test_urls = [
        ("Woolworths Specials", "https://www.woolworths.com.au/shop/browse/specials"),
        ("Coles Specials", "https://www.coles.com.au/on-special"),
        ("ALDI Special Buys", "https://www.aldi.com.au/en/special-buys/"),
    ]

    for name, url in test_urls:
        print(f"\n   Testing: {name}")
        result = test_basic_scrape(url)
        if result.get("success"):
            print(f"   ✅ Status: {result['status_code']} | "
                  f"Size: {result['content_length']} | "
                  f"Prices: {result.get('has_prices', 'N/A')}")
        else:
            print(f"   ❌ Failed: {result.get('error', result.get('status_code'))}")

    # Run Firecrawl tests if available
    if FIRECRAWL_AVAILABLE and os.getenv("FIRECRAWL_API_KEY"):
        print("\n" + "=" * 60)
        print("🔥 Running Firecrawl Tests...")
        print("=" * 60)
        run_all_tests()
    else:
        print("\n⚠️  Skipping Firecrawl tests (not configured)")
        print("   Set FIRECRAWL_API_KEY to run full tests")
