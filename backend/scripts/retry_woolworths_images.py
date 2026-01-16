"""
Retry downloading Woolworths images that failed.
Run with: python -m scripts.retry_woolworths_images
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import sessionmaker
from app.database import engine
from app.models import MasterProduct, Store
from app.services.image_cache import image_cache


async def retry_woolworths():
    """Retry downloading Woolworths product images."""
    print("Retrying Woolworths image downloads...")

    Session = sessionmaker(bind=engine)
    db_session = Session()

    try:
        # Get Woolworths store
        woolworths = db_session.query(Store).filter(Store.slug == "woolworths").first()
        if not woolworths:
            print("Woolworths store not found")
            return

        # Get products without cached images
        products = db_session.query(MasterProduct).filter(
            MasterProduct.store_id == woolworths.id,
            MasterProduct.image_cached == False,
            MasterProduct.original_image_url.isnot(None)
        ).all()

        print(f"Found {len(products)} Woolworths products needing images")

        if not products:
            print("All images already cached!")
            return

        # Download in smaller batches with delay to avoid rate limiting
        batch_size = 10
        success = 0
        failed = 0

        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(products) + batch_size - 1) // batch_size
            print(f"Batch {batch_num}/{total_batches}...", end=" ", flush=True)

            images = [{
                "url": p.original_image_url,
                "store_slug": "woolworths",
                "stockcode": p.stockcode,
                "product_id": p.id
            } for p in batch]

            results = await image_cache.cache_batch(images, max_concurrent=5)

            # Update database for successful downloads
            for img_info in images:
                if image_cache.image_exists("woolworths", img_info["stockcode"]):
                    product = db_session.query(MasterProduct).get(img_info["product_id"])
                    if product and not product.image_cached:
                        product.local_image_path = image_cache.get_local_path(
                            "woolworths",
                            img_info["stockcode"]
                        )
                        product.image_cached = True
                        success += 1
                else:
                    failed += 1

            db_session.commit()
            print(f"OK ({results['success']} new)")

            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(products):
                await asyncio.sleep(1)

        print(f"\nComplete: {success} cached, {failed} failed")

        # Print stats
        stats = image_cache.get_cache_stats()
        print(f"\nTotal cached images: {stats['total']}")
        for store, count in stats['by_store'].items():
            print(f"  {store}: {count}")

    finally:
        db_session.close()


if __name__ == "__main__":
    asyncio.run(retry_woolworths())
