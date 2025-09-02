-- Main organizational unit for a lorebook generation task.
CREATE TABLE "Project" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "source_url" TEXT,
    "prompt" TEXT,
    "search_params" JSONB,
    "link_extraction_selector" TEXT[], -- CSS selectors to extract links
    "link_extraction_pagination_selector" TEXT,
    "max_pages_to_crawl" INTEGER NOT NULL DEFAULT 20,
    "templates" JSONB NOT NULL,
    "ai_provider_config" JSONB NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'draft',
    "requests_per_minute" INTEGER NOT NULL DEFAULT 15,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Represents a single asynchronous task executed by a background worker.
CREATE TABLE "BackgroundJob" (
    "id" UUID NOT NULL PRIMARY KEY,
    "task_name" TEXT NOT NULL,
    "payload" JSONB,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "project_id" TEXT,
    "result" JSONB,
    "error_message" TEXT,
    "total_items" INTEGER,
    "processed_items" INTEGER,
    "progress" REAL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE
);

CREATE INDEX "ix_backgroundjob_status_created_at" ON "BackgroundJob" ("status", "created_at");

-- The final, structured output of the generation process.
CREATE TABLE "LorebookEntry" (
    "id" UUID NOT NULL PRIMARY KEY,
    "project_id" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "keywords" JSONB NOT NULL,
    "source_url" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE
);

CREATE INDEX "ix_lorebookentry_project_id" ON "LorebookEntry" ("project_id");

-- Represents a single URL extracted from the project's source_url.
CREATE TABLE "Link" (
    "id" UUID NOT NULL PRIMARY KEY,
    "project_id" TEXT NOT NULL,
    "url" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "error_message" TEXT,
    "lorebook_entry_id" UUID,
    "raw_content" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE,
    FOREIGN KEY ("lorebook_entry_id") REFERENCES "LorebookEntry"("id") ON DELETE SET NULL,
    UNIQUE ("project_id", "url")
);

CREATE INDEX "ix_link_project_id_status" ON "Link" ("project_id", "status");

-- An immutable audit record of every billable call made to an external LLM API.
CREATE TABLE "ApiRequestLog" (
    "id" UUID NOT NULL PRIMARY KEY,
    "project_id" TEXT NOT NULL,
    "job_id" UUID,
    "api_provider" TEXT NOT NULL,
    "model_used" TEXT NOT NULL,
    "request" JSONB NOT NULL,
    "response" JSONB,
    "input_tokens" INTEGER,
    "output_tokens" INTEGER,
    "calculated_cost" NUMERIC,
    "latency_ms" INTEGER NOT NULL,
    "timestamp" TIMESTAMPTZ NOT NULL,
    "error" BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE,
    FOREIGN KEY ("job_id") REFERENCES "BackgroundJob"("id") ON DELETE SET NULL
);

CREATE INDEX "ix_apirequestlog_project_id" ON "ApiRequestLog" ("project_id");

-- Stores global templates that can be used across projects.
CREATE TABLE "GlobalTemplate" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL UNIQUE,
    "content" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);