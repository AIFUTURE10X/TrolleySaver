# Supermarket Specials Compare

## Quick Start
Run `start-dev.bat` to start both frontend and backend servers:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

## Project Structure
- `frontend/` - React + Vite + TailwindCSS app
- `backend/` - FastAPI Python backend with SQLite database

## Browser Testing Guidelines
- Prefer `browser_take_screenshot` over `browser_snapshot` to reduce context usage
- Only use `browser_snapshot` when you need to interact with elements (clicking, typing, etc.)
- Screenshots are ~1k tokens, snapshots are ~10k tokens

## Database
- SQLite database at `backend/specials.db`
- Contains specials from Woolworths, Coles, ALDI, and IGA
