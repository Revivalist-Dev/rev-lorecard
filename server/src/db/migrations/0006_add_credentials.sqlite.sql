-- SQLite does not support adding foreign key constraints to existing tables via ALTER TABLE.
-- A full table rebuild is required.

-- == PRE-MIGRATION: Disable foreign keys to allow table manipulation ==
PRAGMA foreign_keys=OFF;

-- == PART 1: Create the Credential table ==
CREATE TABLE "Credential" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL UNIQUE,
    "provider_type" TEXT NOT NULL,
    "values" TEXT NOT NULL, -- Encrypted JSON
    "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS "ix_credential_provider_type" ON "Credential" ("provider_type");
CREATE TRIGGER IF NOT EXISTS update_credential_updated_at AFTER UPDATE ON "Credential"
BEGIN
    UPDATE "Credential" SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = OLD.id;
END;


-- == PART 2: Rebuild the Project table ==
ALTER TABLE "Project" RENAME TO "Project_old_for_credentials";
DROP TRIGGER IF EXISTS update_project_updated_at;

CREATE TABLE "Project" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "prompt" TEXT,
    "search_params" TEXT CHECK(search_params IS NULL OR json_valid(search_params)),
    "templates" TEXT NOT NULL CHECK(json_valid(templates)),
    "status" TEXT NOT NULL DEFAULT 'draft',
    "requests_per_minute" INTEGER NOT NULL DEFAULT 15,
    "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    "credential_id" TEXT,
    "model_name" TEXT,
    "model_parameters" TEXT CHECK(model_parameters IS NULL OR json_valid(model_parameters)),
    FOREIGN KEY ("credential_id") REFERENCES "Credential"("id") ON DELETE SET NULL
);

-- Copy data from the old table, leaving new columns as NULL for now.
-- The data migration script will populate them.
INSERT INTO "Project" (id, name, prompt, search_params, templates, status, requests_per_minute, created_at, updated_at)
SELECT id, name, prompt, search_params, templates, status, requests_per_minute, created_at, updated_at FROM "Project_old_for_credentials";

-- Recreate trigger and index
CREATE INDEX IF NOT EXISTS "ix_project_credential_id" ON "Project" ("credential_id");
CREATE TRIGGER IF NOT EXISTS update_project_updated_at AFTER UPDATE ON "Project"
BEGIN
    UPDATE "Project" SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = OLD.id;
END;


-- == PART 3: Rebuild dependent tables to update their Foreign Keys ==
-- This is necessary in SQLite because dropping/renaming the parent table invalidates FKs.

-- Rebuild BackgroundJob
ALTER TABLE "BackgroundJob" RENAME TO "BackgroundJob_old";
DROP TRIGGER IF EXISTS update_backgroundjob_updated_at;
CREATE TABLE "BackgroundJob" (
    "id" TEXT NOT NULL PRIMARY KEY, "task_name" TEXT NOT NULL, "payload" TEXT CHECK(payload IS NULL OR json_valid(payload)), "status" TEXT NOT NULL DEFAULT 'pending', "project_id" TEXT, "result" TEXT CHECK(result IS NULL OR json_valid(result)), "error_message" TEXT, "total_items" INTEGER, "processed_items" INTEGER, "progress" REAL, "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')), "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "ix_backgroundjob_status_created_at" ON "BackgroundJob" ("status", "created_at");
CREATE TRIGGER IF NOT EXISTS update_backgroundjob_updated_at AFTER UPDATE ON "BackgroundJob" BEGIN UPDATE "BackgroundJob" SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = OLD.id; END;
INSERT INTO "BackgroundJob" SELECT * FROM "BackgroundJob_old";
DROP TABLE "BackgroundJob_old";

-- Rebuild LorebookEntry
ALTER TABLE "LorebookEntry" RENAME TO "LorebookEntry_old";
DROP TRIGGER IF EXISTS update_lorebookentry_updated_at;
CREATE TABLE "LorebookEntry" (
    "id" TEXT NOT NULL PRIMARY KEY, "project_id" TEXT NOT NULL, "title" TEXT NOT NULL, "content" TEXT NOT NULL, "keywords" TEXT NOT NULL CHECK(json_valid(keywords)), "source_url" TEXT NOT NULL, "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')), "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "ix_lorebookentry_project_id" ON "LorebookEntry" ("project_id");
CREATE TRIGGER IF NOT EXISTS update_lorebookentry_updated_at AFTER UPDATE ON "LorebookEntry" BEGIN UPDATE "LorebookEntry" SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = OLD.id; END;
INSERT INTO "LorebookEntry" SELECT * FROM "LorebookEntry_old";
DROP TABLE "LorebookEntry_old";

-- Rebuild Link
ALTER TABLE "Link" RENAME TO "Link_old";
CREATE TABLE "Link" (
    "id" TEXT NOT NULL PRIMARY KEY, "project_id" TEXT NOT NULL, "url" TEXT NOT NULL, "status" TEXT NOT NULL DEFAULT 'pending', "error_message" TEXT, "lorebook_entry_id" TEXT, "raw_content" TEXT, "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')), "skip_reason" TEXT,
    FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE,
    FOREIGN KEY ("lorebook_entry_id") REFERENCES "LorebookEntry"("id") ON DELETE SET NULL,
    UNIQUE ("project_id", "url")
);
CREATE INDEX IF NOT EXISTS "ix_link_project_id_status" ON "Link" ("project_id", "status");
INSERT INTO "Link" SELECT id, project_id, url, status, error_message, lorebook_entry_id, raw_content, created_at, skip_reason FROM "Link_old";
DROP TABLE "Link_old";

-- Rebuild ApiRequestLog
ALTER TABLE "ApiRequestLog" RENAME TO "ApiRequestLog_old";
CREATE TABLE "ApiRequestLog" (
    "id" TEXT NOT NULL PRIMARY KEY, "project_id" TEXT NOT NULL, "job_id" TEXT, "api_provider" TEXT NOT NULL, "model_used" TEXT NOT NULL, "request" TEXT NOT NULL CHECK(json_valid(request)), "response" TEXT CHECK(response IS NULL OR json_valid(response)), "input_tokens" INTEGER, "output_tokens" INTEGER, "calculated_cost" REAL, "latency_ms" INTEGER NOT NULL, "timestamp" TEXT NOT NULL, "error" INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE,
    FOREIGN KEY ("job_id") REFERENCES "BackgroundJob"("id") ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS "ix_apirequestlog_project_id" ON "ApiRequestLog" ("project_id");
INSERT INTO "ApiRequestLog" SELECT * FROM "ApiRequestLog_old";
DROP TABLE "ApiRequestLog_old";

-- Rebuild ProjectSource
ALTER TABLE "ProjectSource" RENAME TO "ProjectSource_old";
DROP TRIGGER IF EXISTS update_projectsource_updated_at;
CREATE TABLE "ProjectSource" (
    "id" TEXT NOT NULL PRIMARY KEY, "project_id" TEXT NOT NULL, "url" TEXT NOT NULL, "link_extraction_selector" TEXT CHECK(link_extraction_selector IS NULL OR json_valid(link_extraction_selector)), "link_extraction_pagination_selector" TEXT, "max_pages_to_crawl" INTEGER NOT NULL DEFAULT 20, "last_crawled_at" TEXT, "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')), "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')), "max_crawl_depth" INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE,
    UNIQUE ("project_id", "url")
);
CREATE INDEX IF NOT EXISTS "ix_projectsource_project_id" ON "ProjectSource" ("project_id");
CREATE TRIGGER IF NOT EXISTS update_projectsource_updated_at AFTER UPDATE ON "ProjectSource" BEGIN UPDATE "ProjectSource" SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = OLD.id; END;
INSERT INTO "ProjectSource" SELECT * FROM "ProjectSource_old";
DROP TABLE "ProjectSource_old";

-- Rebuild ProjectSourceHierarchy
ALTER TABLE "ProjectSourceHierarchy" RENAME TO "ProjectSourceHierarchy_old";
CREATE TABLE "ProjectSourceHierarchy" (
    "id" TEXT NOT NULL PRIMARY KEY, "project_id" TEXT NOT NULL, "parent_source_id" TEXT NOT NULL, "child_source_id" TEXT NOT NULL, "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE,
    FOREIGN KEY ("parent_source_id") REFERENCES "ProjectSource"("id") ON DELETE CASCADE,
    FOREIGN KEY ("child_source_id") REFERENCES "ProjectSource"("id") ON DELETE CASCADE,
    UNIQUE ("parent_source_id", "child_source_id")
);
CREATE INDEX IF NOT EXISTS "ix_projectsourcehierarchy_project_id" ON "ProjectSourceHierarchy" ("project_id");
CREATE INDEX IF NOT EXISTS "ix_projectsourcehierarchy_parent_id" ON "ProjectSourceHierarchy" ("parent_source_id");
CREATE INDEX IF NOT EXISTS "ix_projectsourcehierarchy_child_id" ON "ProjectSourceHierarchy" ("child_source_id");
INSERT INTO "ProjectSourceHierarchy" SELECT * FROM "ProjectSourceHierarchy_old";
DROP TABLE "ProjectSourceHierarchy_old";


-- == PART 4: Clean up and re-enable foreign keys ==
-- The data migration script will run after this, then we drop the old table.
-- We cannot drop it here as the script needs access to `ai_provider_config`.
PRAGMA foreign_keys=ON;