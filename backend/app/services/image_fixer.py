"""
Image fixer service for correcting placeholder image URLs after SaleFinder scrape.

SaleFinder uses its own item IDs for images which often don't resolve correctly.
This service fixes images by:
1. Identifying products with placeholder/broken image URLs
2. Constructing correct CDN URLs from product URLs or searching store websites
"""
import re
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Store, Special

logger = logging.getLogger(__name__)


class ImageFixer:
    """Service to fix broken/placeholder image URLs for specials."""

    # Patterns that indicate a placeholder or broken image
    PLACEHOLDER_PATTERNS = [
        r'dduhxx0oznf63\.cloudfront\.net',  # SaleFinder placeholder CDN
        r'/thumbs/',  # Thumbnail URLs that should be replaced
    ]

    # Store-specific CDN URL patterns
    CDN_PATTERNS = {
        "woolworths": "https://cdn0.woolworths.media/content/wowproductimages/large/{product_id}.jpg",
        "coles": "https://cdn.productimages.coles.com.au/productimages/{first_digit}/{product_id}.jpg",
    }

    # Patterns to extract product ID from product URLs
    PRODUCT_URL_PATTERNS = {
        "woolworths": r'/(\d{6,})$',  # Woolworths URLs end with product ID
        "coles": r'-(\d{6,})$',  # Coles URLs end with -productid
    }

    def is_placeholder_image(self, url: str) -> bool:
        """Check if an image URL is a placeholder that needs fixing."""
        if not url:
            return True
        for pattern in self.PLACEHOLDER_PATTERNS:
            if re.search(pattern, url):
                return True
        return False

    def extract_product_id_from_url(self, product_url: str, store_slug: str) -> Optional[str]:
        """Extract the real product ID from a product URL."""
        if not product_url:
            return None

        pattern = self.PRODUCT_URL_PATTERNS.get(store_slug)
        if not pattern:
            return None

        match = re.search(pattern, product_url)
        if match:
            return match.group(1)
        return None

    def construct_cdn_url(self, product_id: str, store_slug: str) -> Optional[str]:
        """Construct the correct CDN image URL for a product."""
        if not product_id:
            return None

        if store_slug == "woolworths":
            return self.CDN_PATTERNS["woolworths"].format(product_id=product_id)
        elif store_slug == "coles":
            first_digit = product_id[0] if product_id else '0'
            return self.CDN_PATTERNS["coles"].format(
                first_digit=first_digit,
                product_id=product_id
            )
        return None

    def fix_store_images(self, db: Session, store_slug: str) -> dict:
        """Fix placeholder images for a specific store."""
        store = db.query(Store).filter(Store.slug == store_slug).first()
        if not store:
            logger.warning(f"Store not found: {store_slug}")
            return {"status": "error", "error": f"Store not found: {store_slug}"}

        # Get specials with potentially bad images
        specials = db.query(Special).filter(
            Special.store_id == store.id,
            Special.valid_to >= datetime.now().date()
        ).all()

        fixed_count = 0
        checked_count = 0

        for special in specials:
            checked_count += 1

            # Skip if image looks valid
            if not self.is_placeholder_image(special.image_url):
                continue

            # Try to extract product ID from product_url
            product_id = self.extract_product_id_from_url(special.product_url, store_slug)

            # If no product_url, try extracting from store_product_id if it looks like a real ID
            if not product_id and special.store_product_id:
                # SaleFinder IDs are typically 9+ digits, real store IDs are 6-7 digits
                if len(special.store_product_id) <= 8:
                    product_id = special.store_product_id

            if product_id:
                new_url = self.construct_cdn_url(product_id, store_slug)
                if new_url and new_url != special.image_url:
                    logger.debug(f"Fixing image for '{special.name}': {special.image_url} -> {new_url}")
                    special.image_url = new_url
                    fixed_count += 1

        if fixed_count > 0:
            db.commit()
            logger.info(f"Fixed {fixed_count} images for {store_slug}")

        return {
            "status": "success",
            "store": store_slug,
            "checked": checked_count,
            "fixed": fixed_count
        }

    def fix_all_images(self, db: Optional[Session] = None) -> dict:
        """Fix placeholder images for all stores."""
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        results = {}
        try:
            for store_slug in ["woolworths", "coles"]:
                try:
                    result = self.fix_store_images(db, store_slug)
                    results[store_slug] = result
                except Exception as e:
                    logger.error(f"Failed to fix images for {store_slug}: {e}")
                    results[store_slug] = {"status": "error", "error": str(e)}
        finally:
            if close_db:
                db.close()

        return results


def run_image_fix():
    """Run the image fix job. Called by scheduler after SaleFinder scrape."""
    logger.info("Starting post-scrape image fix...")
    fixer = ImageFixer()

    db = SessionLocal()
    try:
        results = fixer.fix_all_images(db)

        for store, result in results.items():
            if result.get("status") == "success":
                logger.info(f"{store}: Fixed {result.get('fixed', 0)}/{result.get('checked', 0)} images")
            else:
                logger.error(f"{store}: Image fix failed - {result.get('error')}")

        return results

    except Exception as e:
        logger.error(f"Image fix failed: {e}")
        raise
    finally:
        db.close()
