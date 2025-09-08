-- == Part 1: Add Project Type and Enhance ProjectSource ==

-- Add a project_type column to distinguish between Lorebook and Character projects.
ALTER TABLE "Project" ADD COLUMN "project_type" TEXT NOT NULL DEFAULT 'lorebook';
CREATE INDEX "ix_project_project_type" ON "Project" ("project_type");

-- Enhance ProjectSource to cache scraped content.
ALTER TABLE "ProjectSource" ADD COLUMN "raw_content" TEXT;
ALTER TABLE "ProjectSource" ADD COLUMN "content_type" TEXT; -- 'html' or 'markdown'
ALTER TABLE "ProjectSource" ADD COLUMN "content_char_count" INTEGER;

-- == Part 2: Create the CharacterCard Table ==

CREATE TABLE "CharacterCard" (
    "id" UUID NOT NULL PRIMARY KEY,
    "project_id" TEXT NOT NULL UNIQUE, -- A project can only have one character card
    "name" TEXT,
    "description" TEXT,
    "persona" TEXT,
    "scenario" TEXT,
    "first_message" TEXT,
    "example_messages" TEXT, -- Storing as a single formatted string
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE CASCADE
);
CREATE INDEX "ix_charactercard_project_id" ON "CharacterCard" ("project_id");