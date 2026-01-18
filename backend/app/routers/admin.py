"""Admin API endpoints for managing the application."""
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from app.database import SessionLocal
from app.tasks.scheduler import (
    get_scheduler_status,
    trigger_manual_update,
    trigger_salefinder_update,
    start_scheduler,
    stop_scheduler
)
from app.services.data_import import (
    import_prices_from_csv,
    import_prices_from_json,
    get_csv_template,
    get_json_template
)
from app.services.openfoodfacts_import import (
    import_products_from_openfoodfacts,
    get_import_status
)

router = APIRouter(prefix="/admin", tags=["admin"])


# Default stores to seed
DEFAULT_STORES = [
    {"name": "Woolworths", "slug": "woolworths", "logo_url": "https://www.woolworths.com.au/static/wowlogo/logo.svg", "website_url": "https://www.woolworths.com.au", "specials_day": "wednesday"},
    {"name": "Coles", "slug": "coles", "logo_url": "https://www.coles.com.au/content/dam/coles/coles-logo.svg", "website_url": "https://www.coles.com.au", "specials_day": "wednesday"},
    {"name": "ALDI", "slug": "aldi", "logo_url": "https://www.aldi.com.au/static/aldi/logo.svg", "website_url": "https://www.aldi.com.au", "specials_day": "wednesday"},
    {"name": "IGA", "slug": "iga", "logo_url": "https://www.iga.com.au/sites/default/files/IGA_Logo.png", "website_url": "https://www.iga.com.au", "specials_day": "wednesday"},
]


@router.post("/seed-stores")
def seed_stores():
    """Initialize the database with default stores."""
    from app.models import Store

    db = SessionLocal()
    try:
        # Check if stores already exist
        existing = db.query(Store).count()
        if existing > 0:
            return {"message": f"Stores already exist ({existing} found)", "created": 0}

        # Create default stores
        created = 0
        for store_data in DEFAULT_STORES:
            store = Store(**store_data)
            db.add(store)
            created += 1

        db.commit()
        return {"message": "Stores seeded successfully", "created": created}
    finally:
        db.close()


class SpecialImport(BaseModel):
    """Single special item for import."""
    product_name: str
    store_slug: str
    price: float
    was_price: Optional[float] = None
    brand: Optional[str] = None
    size: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    discount_percent: Optional[int] = None


@router.post("/import-specials")
def import_specials(specials: list[SpecialImport]):
    """Import specials directly into the database."""
    from app.models import Store, Special
    from datetime import datetime, timedelta

    db = SessionLocal()
    try:
        # Get store mapping
        stores = {s.slug: s.id for s in db.query(Store).all()}

        created = 0
        skipped = 0
        for item in specials:
            if item.store_slug not in stores:
                skipped += 1
                continue

            # Create special (truncate name to 255 chars for DB constraint)
            special = Special(
                store_id=stores[item.store_slug],
                name=item.product_name[:255] if item.product_name else "",
                brand=item.brand,
                size=item.size,
                category=item.category,
                price=item.price,
                was_price=item.was_price,
                discount_percent=item.discount_percent,
                image_url=item.image_url,
                valid_from=datetime.now().date(),
                valid_to=(datetime.now() + timedelta(days=7)).date(),
                scraped_at=datetime.now()
            )
            db.add(special)
            created += 1

        db.commit()
        return {"message": "Specials imported", "created": created, "skipped": skipped}
    finally:
        db.close()


@router.get("/scheduler/status")
def scheduler_status():
    """Get the current scheduler status and last run results."""
    return get_scheduler_status()


@router.post("/scheduler/start")
def start_scheduler_endpoint():
    """Start the background scheduler."""
    start_scheduler()
    return {"message": "Scheduler started", "status": get_scheduler_status()}


@router.post("/scheduler/stop")
def stop_scheduler_endpoint():
    """Stop the background scheduler."""
    stop_scheduler()
    return {"message": "Scheduler stopped"}


@router.post("/catalogue/update")
def trigger_catalogue_update(
    store: str | None = None,
    background_tasks: BackgroundTasks = None
):
    """
    Manually trigger a catalogue update.

    Args:
        store: Optional store slug (woolworths, coles, aldi).
               If not provided, updates all stores.
    """
    # Run synchronously for now (could use background_tasks for async)
    result = trigger_manual_update(store)

    if "error" in result and "Unknown store" in result.get("error", ""):
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/catalogue/parsers")
def list_parsers():
    """List available catalogue parsers."""
    from app.services.catalogue_parser import get_all_parsers

    parsers = []
    for parser in get_all_parsers():
        parsers.append({
            "store_slug": parser.store_slug,
            "store_name": parser.store_name
        })

    return {"parsers": parsers}


# ============== Data Import Endpoints ==============

class JsonImportRequest(BaseModel):
    """Request body for JSON import."""
    data: list[dict]


@router.get("/import/template/csv")
def get_import_csv_template():
    """Get a CSV template with example data for importing prices."""
    return {
        "template": get_csv_template(),
        "instructions": "Upload a CSV file with columns: product_name, store_slug, price, was_price, is_special, special_type"
    }


@router.get("/import/template/json")
def get_import_json_template():
    """Get a JSON template with example data for importing prices."""
    return {
        "template": get_json_template(),
        "instructions": "Submit a JSON array of price objects"
    }


@router.post("/import/csv")
async def import_csv(file: UploadFile = File(...)):
    """
    Import prices from a CSV file.

    Expected columns: product_name, store_slug, price, was_price, is_special, special_type
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    csv_content = content.decode('utf-8')

    db = SessionLocal()
    try:
        result = import_prices_from_csv(csv_content, db)
        return result
    finally:
        db.close()


@router.post("/import/json")
def import_json(request: JsonImportRequest):
    """
    Import prices from JSON data.

    Expected format: Array of objects with product_name, store_slug, price,
    was_price, is_special, special_type
    """
    import json
    json_content = json.dumps(request.data)

    db = SessionLocal()
    try:
        result = import_prices_from_json(json_content, db)
        return result
    finally:
        db.close()


# ============== Open Food Facts Import ==============

@router.get("/openfoodfacts/status")
def openfoodfacts_status():
    """Get current Open Food Facts import status."""
    db = SessionLocal()
    try:
        return get_import_status(db)
    finally:
        db.close()


@router.post("/openfoodfacts/import")
def openfoodfacts_import(
    max_pages: int = 10,
    start_page: int = 1,
    background_tasks: BackgroundTasks = None
):
    """
    Import Australian products from Open Food Facts.

    Args:
        max_pages: Maximum pages to import (100 products per page). Default 10 = 1000 products.
        start_page: Page to start from (for resuming large imports)

    Note: Full import of ~68,000 products requires ~680 pages and takes ~10-15 minutes.
    Run in smaller batches to avoid timeouts.
    """
    db = SessionLocal()
    try:
        result = import_products_from_openfoodfacts(
            db,
            max_pages=max_pages,
            start_page=start_page
        )
        return result
    finally:
        db.close()


# ============== SaleFinder Integration ==============

@router.post("/salefinder/scrape")
def salefinder_scrape(store: str | None = None):
    """
    Manually trigger a SaleFinder scrape.

    Args:
        store: Optional store slug (woolworths, coles).
               If not provided, scrapes all configured stores.
    """
    result = trigger_salefinder_update(store)

    if "error" in result and "not configured" in result.get("error", "").lower():
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/salefinder/catalogues/{store}")
def salefinder_catalogues(store: str):
    """
    List available catalogues for a store from SaleFinder.

    Args:
        store: Store slug (woolworths, coles)
    """
    from app.services.salefinder_scraper import SaleFinderScraper

    scraper = SaleFinderScraper()
    try:
        catalogues = scraper.discover_catalogues(store)
        return {
            "store": store,
            "catalogues": catalogues
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch catalogues: {str(e)}")


@router.get("/salefinder/status")
def salefinder_status():
    """Get last SaleFinder scrape status."""
    status = get_scheduler_status()
    return {
        "last_scrape": status.get("last_salefinder_scrape", {}),
        "next_scheduled": next(
            (job["next_run"] for job in status.get("jobs", [])
             if job["id"] == "weekly_salefinder_scrape"),
            None
        )
    }


@router.post("/scrape")
def unified_scrape(
    source: str = "salefinder",
    store: str | None = None
):
    """
    Trigger a scrape with source selection.

    Args:
        source: Data source to use - 'salefinder', 'firecrawl', or 'both'
        store: Optional store slug. If not provided, scrapes all stores.
    """
    results = {}

    if source in ("salefinder", "both"):
        sf_result = trigger_salefinder_update(store)
        results["salefinder"] = sf_result

    if source in ("firecrawl", "both"):
        # Use existing Firecrawl trigger (via catalogue update)
        fc_result = trigger_manual_update(store)
        results["firecrawl"] = fc_result

    if source not in ("salefinder", "firecrawl", "both"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source: {source}. Must be 'salefinder', 'firecrawl', or 'both'"
        )

    return {
        "source": source,
        "store": store or "all",
        "results": results
    }
