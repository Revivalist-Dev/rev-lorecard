@echo off
setlocal

echo ===========================================
echo  Lorebook Creator - Startup Script
echo ===========================================
echo.

REM --- 1. Check for Git and pull latest changes ---
echo [1/6] Checking for updates...
git pull
if errorlevel 1 (
    echo ERROR: Failed to pull updates from Git. Please check your connection and repository status.
    pause
    exit /b 1
)
echo      Done.
echo.

REM --- 2. Check for prerequisites: pnpm and uv ---
echo [2/6] Checking prerequisites...
where pnpm >nul 2>nul
if errorlevel 1 (
    echo ERROR: pnpm is not installed or not in your PATH.
    echo Please install it by running: npm install -g pnpm
    pause
    exit /b 1
)

where uv >nul 2>nul
if errorlevel 1 (
    echo ERROR: uv is not installed or not in your PATH.
    echo Please follow installation instructions at https://github.com/astral-sh/uv
    pause
    exit /b 1
)
echo      pnpm and uv found.
echo.

REM --- 3. Setup Python virtual environment ---
echo [3/6] Setting up Python environment...
if not exist server/.venv (
    echo      Virtual environment not found. Creating...
    cd server
    uv venv
    cd ..
)
cd server
uv pip install -r requirements.txt
cd ..
echo      Python dependencies are up to date.
echo.

REM --- 4. Install client dependencies ---
echo [4/6] Installing client dependencies...
cd client
pnpm install
if errorlevel 1 (
    echo ERROR: Failed to install client dependencies with pnpm.
    pause
    exit /b 1
)
cd ..
echo      Client dependencies installed.
echo.


REM --- 5. Build the client application ---
echo [5/6] Building client application...
cd client
pnpm build
if errorlevel 1 (
    echo ERROR: Failed to build the client application.
    pause
    exit /b 1
)
cd ..
echo      Client build complete.
echo.

REM --- 6. Start the server ---
echo [6/6] Starting the server...
cd server
uv run python src/main.py

endlocal