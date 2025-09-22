-- Add a column to store URL exclusion patterns for a source (PostgreSQL version)
ALTER TABLE "ProjectSource" ADD COLUMN "url_exclusion_patterns" TEXT[];