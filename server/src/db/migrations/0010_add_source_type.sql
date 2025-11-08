-- Add source_type column with default value 'web_url'
ALTER TABLE "ProjectSource" ADD COLUMN source_type TEXT NOT NULL DEFAULT 'web_url';