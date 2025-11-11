-- Create the SourceContentVersion table
CREATE TABLE "SourceContentVersion" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES "ProjectSource"(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL,
    raw_content TEXT NOT NULL,
    version_name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Index for quick lookup by source and project
CREATE INDEX idx_sourcecontentversion_source_id ON "SourceContentVersion"(source_id);
CREATE INDEX idx_sourcecontentversion_project_id ON "SourceContentVersion"(project_id);