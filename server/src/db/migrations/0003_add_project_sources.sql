-- Create the new table to store project sources
CREATE TABLE "ProjectSource" (
    "id" UUID NOT NULL PRIMARY KEY,
    "project_id" TEXT NOT NULL,
    "url" TEXT NOT NULL,
    "link_extraction_selector" TEXT[], -- Array of CSS selectors for content
    "link_extraction_pagination_selector" TEXT, -- Single selector for 'next page'
    "max_pages_to_crawl" INTEGER NOT NULL DEFAULT 20,
    "last_crawled_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE,
    UNIQUE ("project_id", "url")
);

CREATE INDEX "ix_projectsource_project_id" ON "ProjectSource" ("project_id");

-- **DATA PRESERVATION STEP**: Create a ProjectSource for each existing Project that has a source_url.
-- This must run BEFORE we drop the columns from the Project table.
INSERT INTO "ProjectSource" (id, project_id, url, link_extraction_selector, link_extraction_pagination_selector, max_pages_to_crawl, created_at, updated_at)
SELECT
    gen_random_uuid(), -- Generate a new UUID for the source
    id, -- The project's own ID becomes the foreign key
    source_url,
    link_extraction_selector,
    link_extraction_pagination_selector,
    max_pages_to_crawl,
    created_at, -- Use the project's creation time as a baseline
    updated_at
FROM "Project"
WHERE "source_url" IS NOT NULL AND "source_url" != '';

-- Now that the data is safely migrated, remove the old single-source columns from the Project table.
ALTER TABLE "Project"
DROP COLUMN "source_url",
DROP COLUMN "link_extraction_selector",
DROP COLUMN "link_extraction_pagination_selector",
DROP COLUMN "max_pages_to_crawl";