from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path
from app.config import get_settings
from app.database import init_db
from app.routers.specials import router as specials_router
from app.routers.specials_v2 import router as specials_v2_router
from app.routers.compare import router as compare_router
from app.routers.admin import router as admin_router
from app.routers.staples import router as staples_router  # Staples price comparison
from app.tasks.scheduler import start_scheduler, stop_scheduler
from app.services.cache import cache

settings = get_settings()

# Static files directory for cached images
STATIC_DIR = Path(__file__).parent.parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
(STATIC_DIR / "images").mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database, cache, and scheduler on startup."""
    print("Starting up... Initializing database")
    init_db()
    print("Connecting to Redis cache...")
    await cache.connect()
    print("Starting specials scraper scheduler...")
    start_scheduler()
    yield
    print("Shutting down...")
    stop_scheduler()
    await cache.disconnect()


app = FastAPI(
    title="Supermarket Specials API",
    description="Find weekly specials from Woolworths, Coles, and ALDI",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for cached images
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include routers
app.include_router(specials_router, prefix=settings.api_prefix)
app.include_router(specials_v2_router, prefix=settings.api_prefix)
app.include_router(compare_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
app.include_router(staples_router, prefix=settings.api_prefix)


@app.get("/")
def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": "Supermarket Specials API",
        "version": "2.0.0"
    }


@app.get("/api/stores")
def list_stores():
    """List all supported stores."""
    from app.database import SessionLocal
    from app.models import Store

    db = SessionLocal()
    try:
        stores = db.query(Store).all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "slug": s.slug,
                "specials_day": s.specials_day
            }
            for s in stores
        ]
    finally:
        db.close()


@app.post("/api/import-specials")
def import_specials_direct(specials: list[dict]):
    """Import specials directly into the database."""
    from app.database import SessionLocal
    from app.models import Store, Special
    from datetime import datetime, timedelta

    db = SessionLocal()
    try:
        # Get store mapping
        stores = {s.slug: s.id for s in db.query(Store).all()}

        created = 0
        skipped = 0
        for item in specials:
            store_slug = item.get('store_slug')
            if store_slug not in stores:
                skipped += 1
                continue

            # Create special
            special = Special(
                store_id=stores[store_slug],
                name=item.get('product_name'),
                brand=item.get('brand'),
                size=item.get('size'),
                category=item.get('category'),
                price=item.get('price'),
                was_price=item.get('was_price'),
                discount_percent=item.get('discount_percent'),
                image_url=item.get('image_url'),
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
