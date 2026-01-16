"""
Image Caching Service

Downloads product images from CDN and stores them locally.
Benefits:
- Faster loading (local static files vs CDN)
- Reduced external dependencies
- Images persist even if CDN URLs change
- Ability to resize/optimize images
"""
import os
import asyncio
import httpx
from pathlib import Path
from typing import Optional
import logging
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)

# Base directory for cached images
IMAGES_DIR = Path(__file__).parent.parent.parent / "static" / "images"

# Image optimization settings
MAX_IMAGE_WIDTH = 400  # Max width for product images
JPEG_QUALITY = 85

# Browser-like headers to avoid CDN blocks
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.woolworths.com.au/",
}


class ImageCacheService:
    """Service for downloading and caching product images."""

    def __init__(self):
        self.images_dir = IMAGES_DIR
        self._ensure_directories()

    def _ensure_directories(self):
        """Create necessary directories for each store."""
        stores = ["woolworths", "coles", "aldi", "iga"]
        for store in stores:
            store_dir = self.images_dir / store
            store_dir.mkdir(parents=True, exist_ok=True)

    def get_local_path(self, store_slug: str, stockcode: str) -> str:
        """Get the local path for a product image."""
        return f"/images/{store_slug}/{stockcode}.jpg"

    def get_full_path(self, store_slug: str, stockcode: str) -> Path:
        """Get the full filesystem path for a product image."""
        return self.images_dir / store_slug / f"{stockcode}.jpg"

    def image_exists(self, store_slug: str, stockcode: str) -> bool:
        """Check if image is already cached."""
        return self.get_full_path(store_slug, stockcode).exists()

    async def download_image(
        self,
        url: str,
        store_slug: str,
        stockcode: str,
        optimize: bool = True
    ) -> Optional[str]:
        """
        Download and cache an image from URL.

        Args:
            url: CDN URL for the image
            store_slug: Store identifier (woolworths, coles, etc.)
            stockcode: Product stockcode
            optimize: Whether to resize/compress the image

        Returns:
            Local path if successful, None if failed
        """
        if not url:
            return None

        # Skip if already cached
        if self.image_exists(store_slug, stockcode):
            return self.get_local_path(store_slug, stockcode)

        try:
            async with httpx.AsyncClient(timeout=30.0, headers=BROWSER_HEADERS) as client:
                response = await client.get(url, follow_redirects=True)

                if response.status_code != 200:
                    logger.warning(f"Failed to download image {url}: {response.status_code}")
                    return None

                content = response.content
                content_type = response.headers.get("content-type", "")

                # Verify it's an image
                if "image" not in content_type and not self._is_valid_image(content):
                    logger.warning(f"Invalid image content from {url}")
                    return None

                # Optimize if requested
                if optimize:
                    content = self._optimize_image(content)
                    if content is None:
                        return None

                # Save to disk
                output_path = self.get_full_path(store_slug, stockcode)
                output_path.write_bytes(content)

                logger.info(f"Cached image: {store_slug}/{stockcode}")
                return self.get_local_path(store_slug, stockcode)

        except Exception as e:
            logger.error(f"Error downloading image {url}: {e}")
            return None

    def _is_valid_image(self, content: bytes) -> bool:
        """Check if content is a valid image."""
        try:
            Image.open(BytesIO(content))
            return True
        except Exception:
            return False

    def _optimize_image(self, content: bytes) -> Optional[bytes]:
        """Resize and compress image for web delivery."""
        try:
            img = Image.open(BytesIO(content))

            # Convert to RGB if necessary (for JPEG)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Resize if too large
            if img.width > MAX_IMAGE_WIDTH:
                ratio = MAX_IMAGE_WIDTH / img.width
                new_height = int(img.height * ratio)
                img = img.resize((MAX_IMAGE_WIDTH, new_height), Image.Resampling.LANCZOS)

            # Save as optimized JPEG
            output = BytesIO()
            img.save(output, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            return output.getvalue()

        except Exception as e:
            logger.error(f"Error optimizing image: {e}")
            return None

    async def cache_batch(
        self,
        images: list[dict],
        max_concurrent: int = 10
    ) -> dict:
        """
        Download multiple images concurrently.

        Args:
            images: List of dicts with keys: url, store_slug, stockcode
            max_concurrent: Maximum concurrent downloads

        Returns:
            Dict with counts: success, failed, skipped (already cached)
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {"success": 0, "failed": 0, "skipped": 0}

        async def download_with_semaphore(img_info):
            async with semaphore:
                if self.image_exists(img_info["store_slug"], img_info["stockcode"]):
                    results["skipped"] += 1
                    return

                result = await self.download_image(
                    img_info["url"],
                    img_info["store_slug"],
                    img_info["stockcode"]
                )

                if result:
                    results["success"] += 1
                else:
                    results["failed"] += 1

        tasks = [download_with_semaphore(img) for img in images]
        await asyncio.gather(*tasks)

        logger.info(
            f"Image cache batch complete: {results['success']} success, "
            f"{results['failed']} failed, {results['skipped']} skipped"
        )

        return results

    def get_cache_stats(self) -> dict:
        """Get statistics about cached images."""
        stats = {"total": 0, "by_store": {}}

        for store_dir in self.images_dir.iterdir():
            if store_dir.is_dir():
                count = len(list(store_dir.glob("*.jpg")))
                stats["by_store"][store_dir.name] = count
                stats["total"] += count

        return stats

    def clear_cache(self, store_slug: Optional[str] = None):
        """Clear cached images for a store or all stores."""
        if store_slug:
            store_dir = self.images_dir / store_slug
            if store_dir.exists():
                for img in store_dir.glob("*.jpg"):
                    img.unlink()
                logger.info(f"Cleared image cache for {store_slug}")
        else:
            for store_dir in self.images_dir.iterdir():
                if store_dir.is_dir():
                    for img in store_dir.glob("*.jpg"):
                        img.unlink()
            logger.info("Cleared all image caches")


# Singleton instance
image_cache = ImageCacheService()
