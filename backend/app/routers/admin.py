"""Admin API endpoints for managing the application."""
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from app.database import SessionLocal
from app.tasks.scheduler import (
    get_scheduler_status,
    trigger_manual_update,
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
