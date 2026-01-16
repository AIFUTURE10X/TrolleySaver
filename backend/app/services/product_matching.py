"""
Product Matching Service

Handles extraction of product types from product names and finding similar products.
This enables comparing all brands of the same product type (e.g., "Full Cream Milk 2L").
"""
import re
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.models import Product


def extract_product_type(name: str, brand: Optional[str]) -> str:
    """
    Extract product type from product name by removing the brand.

    Examples:
        "Dairy Farmers Full Cream Milk 2L" -> "Full Cream Milk 2L"
        "Pauls Full Cream Milk 2L" -> "Full Cream Milk 2L"
        "Woolworths Butter Salted 500g" -> "Butter Salted 500g"
        "A2 Full Cream Milk 2L" -> "Full Cream Milk 2L"
    """
    if not brand or not name:
        return name or ""

    # Remove brand from start of name (case-insensitive)
    # Handle brands with special chars by escaping
    pattern = re.compile(r'^' + re.escape(brand) + r'\s*', re.IGNORECASE)
    product_type = pattern.sub('', name).strip()

    # Clean up any leading/trailing punctuation or dashes
    product_type = re.sub(r'^[\s\-,]+|[\s\-,]+$', '', product_type)

    return product_type if product_type else name


def normalize_product_type(product_type: str) -> str:
    """
    Normalize product type for matching.
    Handles common variations in naming.
    """
    if not product_type:
        return ""

    # Lowercase
    normalized = product_type.lower()

    # Normalize common variations
    replacements = {
        "full cream": "fullcream",
        "full-cream": "fullcream",
        "semi skim": "semi-skim",
        "semi-skimmed": "semi-skim",
        "skim milk": "skimmilk",
        "low fat": "lowfat",
        "low-fat": "lowfat",
        "no added": "noadded",
        "free range": "freerange",
        "extra virgin": "extravirgin",
    }

    for old, new in replacements.items():
        normalized = normalized.replace(old, new)

    # Remove extra whitespace
    normalized = ' '.join(normalized.split())

    return normalized


def find_similar_products(
    db: Session,
    product_type: str,
    size: Optional[str],
    category_id: Optional[int],
    limit: int = 50
) -> list[Product]:
    """
    Find all products matching a product type and size.

    Args:
        db: Database session
        product_type: The extracted product type (without brand)
        size: Product size to match exactly
        category_id: Category to filter by (for performance)
        limit: Maximum products to return

    Returns:
        List of matching products
    """
    normalized_type = normalize_product_type(product_type)

    if not normalized_type:
        return []

    # Build base query
    query = db.query(Product)

    # Filter by category if available (big performance win)
    if category_id:
        query = query.filter(Product.category_id == category_id)

    # Filter by size (must match exactly for like-for-like comparison)
    if size:
        query = query.filter(Product.size == size)

    # Get candidates - limit to avoid loading entire DB
    candidates = query.limit(1000).all()

    # Filter by product type similarity
    matching = []
    for product in candidates:
        candidate_type = extract_product_type(product.name, product.brand)
        candidate_normalized = normalize_product_type(candidate_type)

        # Check for exact match after normalization
        if normalized_type == candidate_normalized:
            matching.append(product)
        # Check for fuzzy match (key terms overlap)
        elif _types_match(normalized_type, candidate_normalized):
            matching.append(product)

    return matching[:limit]


def _types_match(type1: str, type2: str) -> bool:
    """
    Check if two product types represent the same product using fuzzy matching.

    This handles cases where naming differs slightly:
    - "Full Cream Milk" vs "Fullcream Milk"
    - "Butter Salted" vs "Salted Butter"
    """
    if not type1 or not type2:
        return False

    # Split into words
    words1 = set(type1.split())
    words2 = set(type2.split())

    # Remove common size/unit indicators that might be duplicated
    size_patterns = {'ml', 'l', 'g', 'kg', 'pk', 'pack', 'x', 'ea', 'each'}
    words1 = words1 - size_patterns
    words2 = words2 - size_patterns

    # Remove numbers (sizes already handled by size field)
    words1 = {w for w in words1 if not w.isdigit()}
    words2 = {w for w in words2 if not w.isdigit()}

    if not words1 or not words2:
        return False

    # Calculate overlap
    overlap = len(words1 & words2)
    min_len = min(len(words1), len(words2))

    # Require at least 80% overlap of the smaller set
    return overlap / min_len >= 0.8


def get_product_type_suggestions(
    db: Session,
    search_query: str,
    category_id: Optional[int] = None,
    limit: int = 20
) -> list[dict]:
    """
    Search for product types and return unique suggestions.

    Groups products by their extracted type + size combination,
    useful for search autocomplete.

    Returns:
        List of dicts with product_type, size, sample_product_id, brand_count
    """
    if not search_query or len(search_query) < 2:
        return []

    # Search products by name or brand
    query = db.query(Product).filter(
        or_(
            Product.name.ilike(f"%{search_query}%"),
            Product.brand.ilike(f"%{search_query}%")
        )
    )

    if category_id:
        query = query.filter(Product.category_id == category_id)

    products = query.limit(200).all()

    # Group by product type + size
    type_groups: dict[tuple, dict] = {}

    for product in products:
        product_type = extract_product_type(product.name, product.brand)
        normalized = normalize_product_type(product_type)
        key = (normalized, product.size or "")

        if key not in type_groups:
            type_groups[key] = {
                "product_type": product_type,  # Keep original for display
                "size": product.size,
                "sample_product_id": product.id,
                "brands": set(),
                "category_id": product.category_id,
            }

        if product.brand:
            type_groups[key]["brands"].add(product.brand)

    # Convert to list with brand counts
    results = [
        {
            "product_type": v["product_type"],
            "size": v["size"],
            "sample_product_id": v["sample_product_id"],
            "brand_count": len(v["brands"]),
            "category_id": v["category_id"],
        }
        for v in type_groups.values()
    ]

    # Sort by brand count (more brands = better comparison)
    results.sort(key=lambda x: x["brand_count"], reverse=True)

    return results[:limit]
