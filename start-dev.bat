@echo off
echo Starting Supermarket Specials Compare...
echo.
start cmd /k "cd /d "C:\Projects\Supermarket Specials Compare\frontend" && npm run dev"
start cmd /k "cd /d "C:\Projects\Supermarket Specials Compare\backend" && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
echo.
echo Servers starting in new windows...
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8000
echo.
echo Close this window or press any key to exit.
pause >nul
