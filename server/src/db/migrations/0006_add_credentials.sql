-- == Part 1: Create the Credential table ==
CREATE TABLE "Credential" (
    "id" UUID NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL UNIQUE,
    "provider_type" TEXT NOT NULL,
    "values" TEXT NOT NULL, -- Encrypted JSON
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX "ix_credential_provider_type" ON "Credential" ("provider_type");

-- == Part 2: Modify the Project table ==
-- Add new columns to store credential reference and model config
ALTER TABLE "Project" ADD COLUMN "credential_id" UUID;
ALTER TABLE "Project" ADD COLUMN "model_name" TEXT;
ALTER TABLE "Project" ADD COLUMN "model_parameters" JSONB;

-- Add foreign key constraint after adding the column
ALTER TABLE "Project" ADD CONSTRAINT "fk_project_credential"
    FOREIGN KEY ("credential_id") REFERENCES "Credential"("id") ON DELETE SET NULL;

-- Create an index on the new foreign key
CREATE INDEX "ix_project_credential_id" ON "Project" ("credential_id");

-- == Part 3: Data Migration (handled by data_migrations.py) ==
-- The logic to move data from the old ai_provider_config column
-- to the new columns and the Credential table will be in a Python script.

-- == Part 4: Drop the old column ==
-- The data migration script will now handle dropping this column after migrating the data.
