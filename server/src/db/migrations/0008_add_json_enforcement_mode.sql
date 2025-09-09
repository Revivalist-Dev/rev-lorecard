-- This column allows specifying the method for ensuring JSON output from LLMs.
-- 'api_native' (default): Relies on the provider's native response_format/tool_use feature.
-- 'prompt_engineered': Uses a special prompt wrapper to force JSON in a code block.

ALTER TABLE "Project"
ADD COLUMN "json_enforcement_mode" TEXT NOT NULL DEFAULT 'api_native';