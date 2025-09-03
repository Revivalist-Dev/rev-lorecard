UPDATE "BackgroundJob"
SET task_name = 'confirm_links'
WHERE task_name = 'extract_links';