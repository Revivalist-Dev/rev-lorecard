CREATE TABLE IF NOT EXISTS "Project" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "source_url" TEXT,
    "prompt" TEXT,
    "search_params" TEXT CHECK(search_params IS NULL OR json_valid(search_params)),
    "link_extraction_selector" TEXT CHECK(link_extraction_selector IS NULL OR json_valid(link_extraction_selector)),
    "link_extraction_pagination_selector" TEXT,
    "max_pages_to_crawl" INTEGER NOT NULL DEFAULT 20,
    "templates" TEXT NOT NULL CHECK(json_valid(templates)),
    "ai_provider_config" TEXT NOT NULL CHECK(json_valid(ai_provider_config)),
    "status" TEXT NOT NULL DEFAULT 'draft',
    "requests_per_minute" INTEGER NOT NULL DEFAULT 15,
    "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS "BackgroundJob" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "task_name" TEXT NOT NULL,
    "payload" TEXT CHECK(payload IS NULL OR json_valid(payload)),
    "status" TEXT NOT NULL DEFAULT 'pending',
    "project_id" TEXT,
    "result" TEXT CHECK(result IS NULL OR json_valid(result)),
    "error_message" TEXT,
    "total_items" INTEGER,
    "processed_items" INTEGER,
    "progress" REAL,
    "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS "ix_backgroundjob_status_created_at" ON "BackgroundJob" ("status", "created_at");

CREATE TABLE IF NOT EXISTS "LorebookEntry" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "project_id" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "keywords" TEXT NOT NULL CHECK(json_valid(keywords)),
    "source_url" TEXT NOT NULL,
    "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS "ix_lorebookentry_project_id" ON "LorebookEntry" ("project_id");

CREATE TABLE IF NOT EXISTS "Link" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "project_id" TEXT NOT NULL,
    "url" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "error_message" TEXT,
    "lorebook_entry_id" TEXT,
    "raw_content" TEXT,
    "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE,
    FOREIGN KEY ("lorebook_entry_id") REFERENCES "LorebookEntry"("id") ON DELETE SET NULL,
    UNIQUE ("project_id", "url")
);

CREATE INDEX IF NOT EXISTS "ix_link_project_id_status" ON "Link" ("project_id", "status");

CREATE TABLE IF NOT EXISTS "ApiRequestLog" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "project_id" TEXT NOT NULL,
    "job_id" TEXT,
    "api_provider" TEXT NOT NULL,
    "model_used" TEXT NOT NULL,
    "request" TEXT NOT NULL CHECK(json_valid(request)),
    "response" TEXT CHECK(response IS NULL OR json_valid(response)),
    "input_tokens" INTEGER,
    "output_tokens" INTEGER,
    "calculated_cost" REAL,
    "latency_ms" INTEGER NOT NULL,
    "timestamp" TEXT NOT NULL,
    "error" INTEGER NOT NULL DEFAULT 0, -- BOOLEAN is INTEGER 0/1 in SQLite
    FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE,
    FOREIGN KEY ("job_id") REFERENCES "BackgroundJob"("id") ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS "ix_apirequestlog_project_id" ON "ApiRequestLog" ("project_id");

CREATE TABLE IF NOT EXISTS "GlobalTemplate" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL UNIQUE,
    "content" TEXT NOT NULL,
    "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Triggers to update 'updated_at' columns
CREATE TRIGGER IF NOT EXISTS update_project_updated_at AFTER UPDATE ON "Project"
BEGIN
    UPDATE "Project" SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS update_backgroundjob_updated_at AFTER UPDATE ON "BackgroundJob"
BEGIN
    UPDATE "BackgroundJob" SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS update_lorebookentry_updated_at AFTER UPDATE ON "LorebookEntry"
BEGIN
    UPDATE "LorebookEntry" SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS update_globaltemplate_updated_at AFTER UPDATE ON "GlobalTemplate"
BEGIN
    UPDATE "GlobalTemplate" SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = OLD.id;
END;