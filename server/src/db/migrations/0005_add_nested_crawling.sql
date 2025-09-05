-- == Part 1: Schema changes for nested crawling ==
-- Add a column to ProjectSource to control the maximum depth of a crawl starting from this source.
ALTER TABLE "ProjectSource" ADD COLUMN "max_crawl_depth" INTEGER NOT NULL DEFAULT 1;

-- Create a new table to store the hierarchical relationships between sources.
CREATE TABLE "ProjectSourceHierarchy" (
    "id" UUID NOT NULL PRIMARY KEY,
    "project_id" TEXT NOT NULL,
    "parent_source_id" UUID NOT NULL,
    "child_source_id" UUID NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE,
    FOREIGN KEY ("parent_source_id") REFERENCES "ProjectSource"("id") ON DELETE CASCADE,
    FOREIGN KEY ("child_source_id") REFERENCES "ProjectSource"("id") ON DELETE CASCADE,
    UNIQUE ("parent_source_id", "child_source_id")
);

CREATE INDEX "ix_projectsourcehierarchy_project_id" ON "ProjectSourceHierarchy" ("project_id");
CREATE INDEX "ix_projectsourcehierarchy_parent_id" ON "ProjectSourceHierarchy" ("parent_source_id");
CREATE INDEX "ix_projectsourcehierarchy_child_id" ON "ProjectSourceHierarchy" ("child_source_id");

-- Rename the old 'generate_selector' task to be more descriptive of its new role.
UPDATE "BackgroundJob" SET task_name = 'discover_and_crawl_sources' WHERE task_name = 'generate_selector';


-- == Part 2: Lossless data conversion for historical job results ==
-- This single statement converts job results from the old format (with 'new_urls') directly
-- to the final format (with 'new_links'), preserving the URL lists and avoiding data loss.
UPDATE "BackgroundJob"
SET result = jsonb_build_object(
    'new_links', COALESCE(result->'new_urls', '[]'::jsonb),
    'existing_links', COALESCE(result->'existing_urls', '[]'::jsonb),
    'new_sources_created', 0, -- This information cannot be derived from old data, so we default to 0.
    'selectors_generated', CASE
        WHEN task_name = 'rescan_links' THEN 0 -- Rescans don't generate selectors.
        ELSE COALESCE((SELECT count(*) FROM jsonb_object_keys(result->'selectors')), 0)
    END
)
WHERE
    (task_name = 'discover_and_crawl_sources' OR task_name = 'rescan_links')
    AND result IS NOT NULL
    AND result ? 'new_urls'; -- This condition specifically targets the old format with URL lists.