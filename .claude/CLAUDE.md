# Trolley Saver (Supermarket Specials Compare)

## Quick Start
Run `start-dev.bat` to start both frontend and backend servers:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

## Project Structure
- `frontend/` - React + Vite + TailwindCSS app
- `backend/` - FastAPI Python backend

## Deployment
- **Backend**: Railway (https://trolleysaver-production.up.railway.app)
  - PostgreSQL database (persistent)
  - Auto-deploys on push to main branch
- **Frontend**: Vercel (https://trolleysaver-au.vercel.app)
  - Auto-deploys on push to main branch
  - Uses `VITE_API_BASE_URL` env var for API endpoint

## Database
- **Production**: PostgreSQL on Railway (data persists across deployments)
- **Local**: SQLite at `backend/specials.db`
- Contains specials from Woolworths, Coles, ALDI, and IGA
- Current counts (as of Jan 18, 2026): ~2027 total specials

## Product URLs & "View at" Links
- Specials with `product_url` show "View at [Store]" links on cards
- URL coverage by store:
  - ALDI: ~88%
  - Woolworths: ~51%
  - Coles: ~38%
  - IGA: ~6%
- Woolworths API blocks automated URL fetching (timeouts on all requests)
- Script `backend/fetch_woolworths_urls.py` exists but can't be used due to API blocking

## API Endpoints
- `GET /api/stores` - List all stores
- `GET /api/specials` - List specials with filtering
- `GET /api/specials/stats` - Get specials statistics
- `GET /api/staples` - Fresh food staples from specials
- `GET /api/staples/categories` - Staples category list
- `GET /api/compare/fresh-foods` - Price comparison across stores
- `POST /api/import-specials` - Import specials (JSON array, uses raw SQL)
- `DELETE /api/admin/clear-specials` - Clear all specials
- `POST /api/admin/migrate-schema` - Add missing DB columns
- `GET /api/admin/debug/specials-raw` - Raw SQL query for debugging

## Importing Specials to Production
```bash
cd backend
# Export from local
python -c "
import sqlite3, json
conn = sqlite3.connect('specials.db')
cur = conn.cursor()
cur.execute('''SELECT s.name, st.slug, s.price, s.was_price, s.brand, s.size,
    c.name, s.image_url, s.product_url, s.discount_percent
    FROM specials s JOIN stores st ON s.store_id = st.id
    LEFT JOIN categories c ON s.category_id = c.id''')
specials = [{'product_name':r[0],'store_slug':r[1],'price':r[2],'was_price':r[3],
    'brand':r[4],'size':r[5],'category':r[6],'image_url':r[7],'product_url':r[8],
    'discount_percent':r[9]} for r in cur.fetchall()]
with open('specials_export.json','w') as f: json.dump(specials,f)
print(f'Exported {len(specials)} specials')
"

# Import to production (chunked)
python -c "
import json, requests, time
with open('specials_export.json') as f: specials = json.load(f)
URL = 'https://trolleysaver-production.up.railway.app/api/import-specials'
for i in range(0, len(specials), 100):
    resp = requests.post(URL, json=specials[i:i+100], timeout=60)
    print(f'Chunk {i//100+1}: {resp.json()}')
    time.sleep(0.5)
"
```

Note: For large imports (2000+ records), split into chunks of 100 to avoid timeouts.

## Important: Import Endpoint Uses Raw SQL
The `/api/import-specials` endpoint uses raw SQL instead of SQLAlchemy ORM. This is intentional because:
- SQLAlchemy ORM caches table metadata at startup
- If columns are added to production DB after deployment, ORM won't see them
- Raw SQL ensures all columns (including `product_url`) are saved correctly

## IGA Image Fetching
- Script: `backend/fetch_iga_images.py`
- IGA Shop API: `https://www.igashop.com.au/api/storefront/stores/{STORE_ID}/search?q={query}&take=10`
- Store ID for Erskine Park: `32600`
- Run with: `cd backend && python fetch_iga_images.py`

## Browser Testing Guidelines
- Prefer `browser_take_screenshot` over `browser_snapshot` to reduce context usage
- Only use `browser_snapshot` when you need to interact with elements
- Screenshots are ~1k tokens, snapshots are ~10k tokens

## Key Files
- `backend/app/main.py` - Main FastAPI app, includes `/api/import-specials` endpoint
- `backend/app/database.py` - DB setup, seeds stores and categories on startup
- `backend/app/routers/staples.py` - Staples page API (uses specials with keyword matching)
- `backend/app/routers/compare.py` - Compare page API (fresh food price comparison)
- `backend/app/routers/admin.py` - Admin endpoints (clear, migrate, debug)
- `frontend/src/App.tsx` - React router setup
- `frontend/src/pages/SpecialsV2.tsx` - Specials page with "View at" links
