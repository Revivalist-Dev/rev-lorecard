-- == PRE-MIGRATION: Disable foreign keys to allow table manipulation ==
PRAGMA foreign_keys=OFF;

-- == PART 1: Rebuild the Project table (remove old columns) ==
ALTER TABLE "Project" RENAME TO "Project_old";
DROP TRIGGER IF EXISTS update_project_updated_at;

CREATE TABLE "Project" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "prompt" TEXT,
    "search_params" TEXT CHECK(search_params IS NULL OR json_valid(search_params)),
    "templates" TEXT NOT NULL CHECK(json_valid(templates)),
    "ai_provider_config" TEXT NOT NULL CHECK(json_valid(ai_provider_config)),
    "status" TEXT NOT NULL DEFAULT 'draft',
    "requests_per_minute" INTEGER NOT NULL DEFAULT 15,
    "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE TRIGGER IF NOT EXISTS update_project_updated_at AFTER UPDATE ON "Project"
BEGIN
    UPDATE "Project" SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = OLD.id;
END;
INSERT INTO "Project" (id, name, prompt, search_params, templates, ai_provider_config, status, requests_per_minute, created_at, updated_at)
SELECT id, name, prompt, search_params, templates, ai_provider_config, status, requests_per_minute, created_at, updated_at FROM "Project_old";


-- == PART 2: Rebuild dependent tables to update their Foreign Keys ==

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


-- == PART 3: Create the new ProjectSource table ==
CREATE TABLE "ProjectSource" (
    "id" TEXT NOT NULL PRIMARY KEY, "project_id" TEXT NOT NULL, "url" TEXT NOT NULL, "link_extraction_selector" TEXT CHECK(link_extraction_selector IS NULL OR json_valid(link_extraction_selector)), "link_extraction_pagination_selector" TEXT, "max_pages_to_crawl" INTEGER NOT NULL DEFAULT 20, "last_crawled_at" TEXT, "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')), "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE,
    UNIQUE ("project_id", "url")
);
CREATE INDEX IF NOT EXISTS "ix_projectsource_project_id" ON "ProjectSource" ("project_id");
CREATE TRIGGER IF NOT EXISTS update_projectsource_updated_at AFTER UPDATE ON "ProjectSource" BEGIN UPDATE "ProjectSource" SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = OLD.id; END;

INSERT INTO "ProjectSource" (id, project_id, url, link_extraction_selector, link_extraction_pagination_selector, max_pages_to_crawl, created_at, updated_at)
SELECT
    lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab', 1 + (abs(random()) % 4), 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6))),
    id, source_url, link_extraction_selector, link_extraction_pagination_selector, max_pages_to_crawl, created_at, updated_at
FROM "Project_old" WHERE "source_url" IS NOT NULL AND "source_url" != '';


-- == PART 4: Clean up and re-enable foreign keys ==
DROP TABLE "Project_old";
PRAGMA foreign_keys=ON;
