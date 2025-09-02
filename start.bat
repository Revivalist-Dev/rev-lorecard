@echo off
setlocal enabledelayedexpansion

echo ===========================================
echo  Lorebook Creator - Startup Script
echo ===========================================
echo.

REM --- 1. Environment Configuration (.env file) ---
echo [1/7] Environment Configuration
set "ENV_FILE=server\.env"

REM Ensure the .env file exists before reading or writing to it
if not exist "%ENV_FILE%" (
    echo. > "%ENV_FILE%"
    echo      Created empty %ENV_FILE%.
)

REM --- Handle DATABASE_TYPE ---
set "DB_TYPE_SET="
findstr /b "DATABASE_TYPE=" "%ENV_FILE%" >nul
if not errorlevel 1 ( set "DB_TYPE_SET=true" )

if not defined DB_TYPE_SET (
    echo.
    CHOICE /C 12 /N /M "Which database would you like to use? [1] PostgreSQL (requires Docker) [2] SQLite (default): "
    if errorlevel 2 (
        set "DATABASE_TYPE=sqlite"
    ) else if errorlevel 1 (
        set "DATABASE_TYPE=postgres"
    )
    
    REM Append the new setting to the .env file
    echo DATABASE_TYPE=!DATABASE_TYPE!>>"%ENV_FILE%"
    echo      Database choice saved to %ENV_FILE%.
)

REM Read the final DATABASE_TYPE from the file for use later in this script
for /f "tokens=1,* delims==" %%a in ('findstr /b "DATABASE_TYPE=" "%ENV_FILE%"') do (
    set "DATABASE_TYPE=%%b"
)

REM --- Handle OPENROUTER_API_KEY ---
set "KEY_IN_FILE="
findstr /b "OPENROUTER_API_KEY=" "%ENV_FILE%" >nul
if not errorlevel 1 ( set "KEY_IN_FILE=true" )

if defined KEY_IN_FILE (
    echo      Using OpenRouter API Key from %ENV_FILE%.
) else if defined OPENROUTER_API_KEY (
    echo      Using OpenRouter API Key from system environment.
) else (
    echo.
    echo      OpenRouter API Key not found.
    set /p "API_KEY=Please enter your OpenRouter API Key and press Enter: "
    
    REM Append the API key to the .env file
    echo OPENROUTER_API_KEY=!API_KEY!>>"%ENV_FILE%"
    echo      API Key saved to %ENV_FILE%.
)
echo.

REM --- Start Docker if PostgreSQL is selected ---
if /I "%DATABASE_TYPE%"=="postgres" (
    echo      PostgreSQL selected. Checking Docker and starting container...
    where docker >nul 2>nul
    if errorlevel 1 (
        echo ERROR: Docker is not found in your PATH. It is required for PostgreSQL.
        pause
        exit /b 1
    )
    
    where docker-compose >nul 2>nul
    if %errorlevel% equ 0 ( set "DOCKER_COMPOSE_CMD=docker-compose" ) else ( set "DOCKER_COMPOSE_CMD=docker compose" )

    cd server
    %DOCKER_COMPOSE_CMD% up -d
    if errorlevel 1 (
        echo ERROR: Failed to start the PostgreSQL container.
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo      PostgreSQL container started successfully.
    echo.
)

REM --- 2. Check for Git and pull latest changes ---
echo [2/7] Checking for updates...
git pull
if errorlevel 1 (
    echo ERROR: Failed to pull updates from Git.
    pause
    exit /b 1
)
echo      Done.
echo.

REM --- 3. Check for prerequisites: pnpm and uv ---
echo [3/7] Checking prerequisites...
where pnpm >nul 2>nul || (echo ERROR: pnpm is not installed or not in your PATH.& pause & exit /b 1)
where uv >nul 2>nul || (echo ERROR: uv is not installed or not in your PATH.& pause & exit /b 1)
echo      pnpm and uv found.
echo.

REM --- 4. Setup Python virtual environment ---
echo [4/7] Setting up Python environment...
if not exist server\.venv (
    echo      Virtual environment not found. Creating with Python 3.10...
    cd server & uv venv --python 3.10 & cd ..
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment. Please ensure Python 3.10 is installed and available.
        pause
        exit /b 1
    )
)
cd server
uv pip install -r requirements.txt
cd ..
echo      Python dependencies are up to date.
echo.

REM --- 5. Install client dependencies ---
echo [5/7] Installing client dependencies...
cd client
pnpm install
if errorlevel 1 ( echo ERROR: Failed to install client dependencies with pnpm.& cd .. & pause & exit /b 1 )
cd ..
echo      Client dependencies installed.
echo.

REM --- 6. Build the client application ---
echo [6/7] Building client application...
cd client
pnpm build
if errorlevel 1 ( echo ERROR: Failed to build the client application.& cd .. & pause & exit /b 1 )
cd ..
echo      Client build complete.
echo.

REM --- 7. Start the server ---
echo [7/7] Starting the server...
echo      Using %DATABASE_TYPE% database (from %ENV_FILE%).
echo.
cd server
uv run python src/main.py

endlocal