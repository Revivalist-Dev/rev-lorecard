# Comprehensive Handoff Document: Character Context Sources Implementation

**Date:** 2025-11-07
**Project:** rev-lorecard
**Current Workspace Directory:** f:/Visual Studio/Tavern Hub/rev-lorecard
**Target Environment:** Dockerized PostgreSQL 18 (via `docker-compose.yml`)

## 1. Task Objective
Implement two new context source types for Character Projects (`/projects/character`):
1.  **User Text File** (`user_text_file`)
2.  **Other Character Card** (`character_card`)

## 2. Implementation Details (Completed)

### 2.1. Backend Model and Migration (`server/src/db/sources.py`)
*   **Type Definition:** Added `SourceType = Literal["web_url", "user_text_file", "character_card"]` to [`server/src/db/sources.py`](server/src/db/sources.py).
*   **Model Update:** Added `source_type: SourceType = "web_url"` and `raw_content: Optional[str] = None` to the `ProjectSource` Pydantic model.
*   **Migration:** Created [`server/src/db/migrations/0010_add_source_type.sql`](server/src/db/migrations/0010_add_source_type.sql). The PostgreSQL migration was finalized as:
    ```sql
    -- Add source_type column with default value 'web_url'
    ALTER TABLE "ProjectSource" ADD COLUMN source_type TEXT NOT NULL DEFAULT 'web_url';
    ```

### 2.2. Character Card Parsing and Fetching Logic
*   **New Service:** Created [`server/src/services/character_card_parser.py`](server/src/services/character_card_parser.py) to handle fetching and parsing character card files (PNG/JSON/TXT).
    *   **Local Path Fix:** Implemented logic to correctly parse Windows local file paths (e.g., `C:\...`) by checking for single-letter schemes and using `urllib.request.url2pathname`.
    *   **PNG Parsing:** Supports `chara` (V2), `ccv3` (V3), and `troll` (Legacy) metadata chunks.
    *   **Fallback:** Implemented a robust fallback mechanism: if standard chunks are missing, it extracts all available PNG metadata as plain text to ensure content is always fetched and viewable.
*   **Job Handler Update:** Modified `fetch_source_content` in [`server/src/services/background_jobs.py`](server/src/services/background_jobs.py) (around lines 190-225) to:
    *   Prioritize handling based on `source_type`.
    *   Include a warning/override to treat `web_url` sources with local file paths as `character_card` sources for character projects, mitigating issues with pre-migration sources.
    *   Added database debugging logs to `update_project_source` in [`server/src/db/sources.py`](server/src/db/sources.py) to capture query details upon failure.

### 2.3. Frontend Implementation
*   **Payload Update:** Updated `CreateSourcePayload` in [`client/src/hooks/useProjectSources.ts`](client/src/hooks/useProjectSources.ts) to make crawling fields optional and include new source fields.
*   **UI Logic:** Updated [`client/src/components/workspace/CharacterSources.tsx`](client/src/components/workspace/CharacterSources.tsx) to enable the "View Content" button and selection checkbox if `source.source_type === 'user_text_file'` or if `source.last_crawled_at` is set.

## 3. Resolution of PostgreSQL Migration Failure

The persistent issue of silent DDL failure has been resolved. The root cause was identified as an `AttributeError` in the `psycopg` driver's asynchronous connection handling, which was masked by subsequent connection resets.

### 3.1. Final Fixes Implemented

1.  **Corrected Asynchronous Autocommit:** The synchronous property assignment `conn.autocommit = True/False` was replaced with the correct asynchronous method calls `await conn.set_autocommit(True/False)` in `PostgresDB.execute` in [`server/src/db/database.py`](server/src/db/database.py).
2.  **Forced DDL Persistence:** An explicit `await conn.commit()` was added to `PostgresDB.execute` to ensure DDL statements executed under `autocommit=True` are immediately persisted before the connection is returned to the pool.
3.  **Enhanced Debugging:** Detailed logging and a critical `table_exists` check were added to [`server/src/db/migration_runner.py`](server/src/db/migration_runner.py) to prevent future silent failures.

### 3.2. Status

The application now successfully runs all 10 migrations, and the database tables are correctly created and persisted in the Dockerized PostgreSQL instance.

## 4. Next Steps: Continuing Source Type Implementation

The database is stable. We now proceed with resolving issues related to the implementation of the new source types (`user_text_file` and `character_card`).

## 5. Character Card Parsing Implementation and Environment Stabilization (2025-11-08)

This session focused on implementing robust character card parsing and resolving environment issues related to Docker and local file access.

### 5.1. Dependency and Environment Fixes

1.  **Rust Toolchain Integration:** Added the local Rust-based `aichar` library to [`server/requirements.txt`](server/requirements.txt) (`-e ./aichar-main`) and guided the user through installing the Rust toolchain to compile the dependency.
2.  **Python Environment Repair:** Uninstalled globally installed dependencies and recreated/reinstalled the `server/.venv` virtual environment to ensure clean dependency management.
3.  **Litestar Warning Resolution:** Removed redundant `sync_to_thread=False` decorators from asynchronous functions (`spa_fallback` and `get_app_info`) in [`server/src/main.py`](server/src/main.py) to eliminate `LitestarWarning` messages.

### 5.2. Robust Character Card Parsing (`server/src/services/character_card_parser.py`)

The manual PNG parsing logic was replaced with the highly robust `aichar` library, which handles V1, V2, V3, and other formats reliably.

*   **Integration:** Imported `aichar` and used `asyncio.to_thread` to call synchronous parsing functions (`load_character_card`, `load_character_json`, `load_character_yaml`).
*   **Format Support:** Full support for **PNG, JSON, and YAML** character card files.
*   **Cleanup:** Removed the redundant `_parse_json_card` function.

### 5.3. Docker Local File Access Resolution

To enable the Docker container to read local Windows files (e.g., `D:\...`), the following changes were made:

1.  **Volume Mount:** Added a volume mount to [`docker-compose.yml`](docker-compose.yml) to map the `D:` drive to `/d` inside the `app` container:
    ```yaml
    volumes:
      - ./data:/app/server/data
      - D:/:/d
    ```
2.  **Path Translation:** Implemented `_translate_windows_path_to_linux` in [`server/src/services/character_card_parser.py`](server/src/services/character_card_parser.py) to convert Windows drive paths to the Linux mount path (e.g., `D:\...` -> `/d/...`) and URL-quote special characters in the path.

### 5.4. Frontend UI Fix

*   **View Content Button:** Modified the `disabled` prop for the "View Content" button in [`client/src/components/workspace/CharacterSources.tsx`](client/src/components/workspace/CharacterSources.tsx) to be more permissive, enabling it for file-based sources (`character_card` and `user_text_file`) even if `raw_content` is temporarily empty, unblocking the user.

## 6. Potential Improvements

1.  **Asynchronous `aichar` Wrapper:** Since `aichar` is synchronous, every call requires `asyncio.to_thread`. Consider creating a dedicated asynchronous wrapper class for `aichar` to manage the thread pool and simplify its usage across the server codebase.
2.  **Error Handling:** Now that the confusing fallback logic is removed, ensure that the `CharacterCardParseError` messages returned to the user are highly informative, potentially including details from the underlying `aichar` exception.
3.  **Docker Build Context:** If the `aichar` dependency is intended to be used in the Docker environment, the `Dockerfile` needs to be updated to install the Rust toolchain and build dependencies (like `build-essential` on Debian-based images) to compile the Rust extension during the image build process.

## 7. Post-Implementation Stabilization and Refinements (2025-11-08)

This session focused on integrating the Rust toolchain, implementing robust error handling, and resolving subsequent environment and runtime issues.

### 7.1. Docker and Environment Fixes

1.  **Rust Toolchain Integration in Docker:** Updated [`Dockerfile`](Dockerfile) to use a multi-stage build (`server_builder` stage) to install the Rust toolchain (`rustup`, `build-essential`, `curl`, `pkg-config`, `libssl-dev`) and successfully compile the `aichar-main` dependency.
2.  **Dependency Path Correction:** Corrected the editable install path for `aichar-main` in [`server/requirements.txt`](server/requirements.txt) from `-e ./aichar-main` to `-e ../aichar-main` to resolve Docker build errors when running `uv pip install` from the `/app/server` directory.
3.  **UV Executable Fix:** Explicitly copied the `uv` executable from `/usr/local/bin/uv` in the `server_builder` stage to the `final` image to resolve container startup errors (`exec: "uv": executable file not found in $PATH`).
4.  **SQLite Deprecation Cleanup:** Removed all references to SQLite, including `aiosqlite` from [`server/requirements.txt`](server/requirements.txt), `ENV DATABASE_TYPE=sqlite` and `ENV DATABASE_URL=lorecard.db` defaults from [`Dockerfile`](Dockerfile), and all SQLite implementation code (`_SQLiteTransaction`, `SQLiteDB`, `import aiosqlite`) from [`server/src/db/database.py`](server/src/db/database.py).
5.  **Local Path Translation Correction:** Modified `_translate_windows_path_to_linux` in [`server/src/services/character_card_parser.py`](server/src/services/character_card_parser.py) to remove unnecessary URL quoting of the path components, resolving "Local file not found" errors when accessing files via Docker volume mounts (e.g., `D:\...` paths).

### 7.2. Robust Character Card Parsing and Frontend Stability

1.  **Robust Error Handling:** Updated [`server/src/services/character_card_parser.py`](server/src/services/character_card_parser.py) to remove the raw text fallback for JSON/YAML parsing failures. The service now raises detailed `CharacterCardParseError` exceptions, ensuring clear error reporting for all character card formats.
2.  **Frontend Editor Stability:** In [`client/src/components/workspace/ViewSourceContentModal.tsx`](client/src/components/workspace/ViewSourceContentModal.tsx), the `MonacoEditorInput` language was made dynamic, defaulting to `plaintext` for non-markdown content when editing. This prevents potential UI crashes when editing large raw text files.

### 7.3. Next Suggested Improvements

1.  **Codebase Documentation (.info files):** Start creating comprehensive `.info` files in each directory to describe the purpose and function of each file in the codebase, aiding in project adoption and maintenance.
2.  **Asynchronous `aichar` Wrapper:** (Carried over from Section 6.1) Implement a dedicated asynchronous wrapper class for `aichar` to manage the thread pool and simplify its usage across the server codebase, reducing boilerplate `asyncio.to_thread` calls.
3.  **Error Handling Refinement:** (Carried over from Section 6.2) Review all `CharacterCardParseError` messages to ensure they are user-friendly and actionable, potentially mapping specific `aichar` internal errors to clearer external messages.
4.  **Frontend Content Type Handling:** Explicitly handle `text/plain` content type in `ViewSourceContentModal.tsx` to ensure consistency, although the current fallback logic works.