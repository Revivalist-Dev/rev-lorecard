@echo off
setlocal enabledelayedexpansion

echo ===========================================
echo  Lorebook Creator - Startup Script
echo ===========================================
echo.

REM --- 1. Environment Configuration (.env file) ---
echo [1/8] Environment Configuration
set "ENV_FILE=server\.env"

REM Ensure the .env file exists
if not exist "%ENV_FILE%" (
    echo. > "%ENV_FILE%"
    echo      Created empty %ENV_FILE%.
)

REM --- Handle DATABASE_TYPE ---
findstr /b "DATABASE_TYPE=" "%ENV_FILE%" >nul
if errorlevel 1 (
    echo.
    CHOICE /C 12 /N /M "Which database would you like to use? [1] PostgreSQL [2] SQLite (default): "
    if errorlevel 2 ( set "DATABASE_TYPE=sqlite" ) else ( set "DATABASE_TYPE=postgres" )
    echo DATABASE_TYPE=!DATABASE_TYPE!>>"%ENV_FILE%"
    echo      Database choice saved to %ENV_FILE%.
)

REM Read DATABASE_TYPE for use in this script
for /f "tokens=1,* delims==" %%a in ('findstr /b "DATABASE_TYPE=" "%ENV_FILE%"') do ( set "DATABASE_TYPE=%%b" )

REM --- Handle OPENROUTER_API_KEY ---
findstr /b "OPENROUTER_API_KEY=" "%ENV_FILE%" >nul
if errorlevel 1 (
    if not defined OPENROUTER_API_KEY (
        echo.
        echo      OpenRouter API Key not found. You can leave this blank if you plan to use another provider.
        set /p "API_KEY=Please enter your OpenRouter API Key and press Enter: "
        echo OPENROUTER_API_KEY=!API_KEY!>>"%ENV_FILE%"
        echo      OpenRouter API Key setting saved to %ENV_FILE%.
    ) else (
        echo      Using OpenRouter API Key from system environment.
    )
) else (
    echo      Using OpenRouter API Key from %ENV_FILE%.
)

REM --- Handle GOOGLE_GEMINI_KEY ---
findstr /b "GOOGLE_GEMINI_KEY=" "%ENV_FILE%" >nul
if errorlevel 1 (
    if not defined GOOGLE_GEMINI_KEY (
        echo.
        echo      Google Gemini API Key not found. You can leave this blank if you plan to use another provider.
        set /p "API_KEY=Please enter your Google Gemini API Key and press Enter: "
        echo GOOGLE_GEMINI_KEY=!API_KEY!>>"%ENV_FILE%"
        echo      Google Gemini API Key setting saved to %ENV_FILE%.
    ) else (
        echo      Using Google Gemini API Key from system environment.
    )
) else (
    echo      Using Google Gemini API Key from %ENV_FILE%.
)

REM --- Handle OPENAI_COMPATIBLE_BASE_URL ---
findstr /b "OPENAI_COMPATIBLE_BASE_URL=" "%ENV_FILE%" >nul
if errorlevel 1 (
    echo.
    echo      OpenAI Compatible URL not found. Required for using custom endpoints (e.g., local LLMs).
    set /p "BASE_URL=Please enter the Base URL (e.g., http://localhost:11434/v1) and press Enter: "
    echo OPENAI_COMPATIBLE_BASE_URL=!BASE_URL!>>"%ENV_FILE%"
    echo      OpenAI Compatible URL saved to %ENV_FILE%.
)

REM --- Handle OPENAI_COMPATIBLE_API_KEY ---
findstr /b "OPENAI_COMPATIBLE_API_KEY=" "%ENV_FILE%" >nul
if errorlevel 1 (
    echo.
    echo      OpenAI Compatible API Key not found. This is optional and can be left blank.
    set /p "COMPATIBLE_API_KEY=Please enter the API Key and press Enter: "
    echo OPENAI_COMPATIBLE_API_KEY=!COMPATIBLE_API_KEY!>>"%ENV_FILE%"
    echo      OpenAI Compatible API Key setting saved to %ENV_FILE%.
)

REM --- Handle PORT ---
findstr /b "PORT=" "%ENV_FILE%" >nul
if errorlevel 1 (
    echo.
    set /p "PORT=Enter the port to run the server on (default: 3000): "
    if not defined PORT ( set "PORT=3000" )
    echo PORT=!PORT!>>"%ENV_FILE%"
    echo      Port saved to %ENV_FILE%.
)

REM Read PORT for use in this script
for /f "tokens=1,* delims==" %%a in ('findstr /b "PORT=" "%ENV_FILE%"') do ( set "PORT=%%b" )
echo.

REM --- 2. Start Docker if needed ---
echo [2/8] Docker Check
if /I "%DATABASE_TYPE%"=="postgres" (
    echo      PostgreSQL selected. Checking Docker and starting container...
    where docker >nul 2>nul || (echo ERROR: Docker is not found. It is required for PostgreSQL.& pause & exit /b 1)
    where docker-compose >nul 2>nul && (set "DOCKER_CMD=docker-compose") || (set "DOCKER_CMD=docker compose")
    cd server & !DOCKER_CMD! up -d & cd ..
    if errorlevel 1 ( echo ERROR: Failed to start PostgreSQL container.& pause & exit /b 1 )
    echo      PostgreSQL container started successfully.
) else (
    echo      Using SQLite, no Docker required.
)
echo.

REM --- 3. Check for Git and pull latest changes ---
echo [3/8] Checking for updates...
git pull
if errorlevel 1 ( echo ERROR: Failed to pull updates from Git.& pause & exit /b 1 )
echo      Done.
echo.

REM --- 4. Check for prerequisites: pnpm and uv ---
echo [4/8] Checking prerequisites...
where pnpm >nul 2>nul || (echo ERROR: pnpm is not installed or not in your PATH.& pause & exit /b 1)
where uv >nul 2>nul || (echo ERROR: uv is not installed or not in your PATH.& pause & exit /b 1)
echo      pnpm and uv found.
echo.

REM --- 5. Setup Python virtual environment ---
echo [5/8] Setting up Python environment...
if not exist server\.venv (
    echo      Virtual environment not found. Creating with Python 3.10...
    cd server & uv venv --python 3.10 & cd ..
    if errorlevel 1 ( echo ERROR: Failed to create venv. Is Python 3.10 installed?& pause & exit /b 1 )
)
cd server
uv pip install -r requirements.txt
cd ..
echo      Python dependencies are up to date.
echo.

REM --- 6. Install client dependencies ---
echo [6/8] Installing client dependencies...
cd client
pnpm install
if errorlevel 1 ( echo ERROR: Failed to install client dependencies.& cd .. & pause & exit /b 1 )
cd ..
echo      Client dependencies installed.
echo.

REM --- 7. Build the client application ---
echo [7/8] Building client application...
cd client
pnpm build
if errorlevel 1 ( echo ERROR: Failed to build the client application.& cd .. & pause & exit /b 1 )
cd ..
echo      Client build complete.
echo.

REM --- 7.5. Set Application Version from Git ---
echo [7.5/8] Detecting application version...
set "APP_VERSION=development"
for /f "tokens=*" %%g in ('git describe --tags --always') do (set "APP_VERSION=%%g")
echo      Version detected: !APP_VERSION!
echo.

REM --- 8. Start the server ---
echo [8/8] Starting the server...
echo      Using %DATABASE_TYPE% database and running on port %PORT%.
echo.
cd server
REM The APP_VERSION variable is now available to the uv run command
uv run python src/main.py

endlocal