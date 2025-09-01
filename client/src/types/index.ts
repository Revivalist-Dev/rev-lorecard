export interface AiProviderConfig {
  api_provider: string;
  model_name: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  model_parameters: Record<string, any>;
}

export interface ProjectTemplates {
  selector_generation: string;
  entry_creation: string;
  search_params_generation: string;
}

export interface SearchParams {
  purpose: string;
  extraction_notes: string;
  criteria: string;
}

export type ProjectStatus =
  | 'draft'
  | 'search_params_generated'
  | 'selector_generated'
  | 'links_extracted'
  | 'processing'
  | 'completed'
  | 'failed';

export interface Project {
  id: string;
  name: string;
  source_url?: string;
  prompt?: string;
  templates: ProjectTemplates;
  ai_provider_config: AiProviderConfig;
  requests_per_minute: number;
  link_extraction_selector?: string[];
  search_params?: SearchParams;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
}

export type LinkStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface Link {
  id: string; // UUID
  project_id: string;
  url: string;
  status: LinkStatus;
  error_message?: string;
  lorebook_entry_id?: string; // UUID
  created_at: string;
  raw_content?: string;
}

export interface LorebookEntry {
  id: string; // UUID
  project_id: string;
  title: string;
  content: string;
  keywords: string[];
  source_url: string;
  created_at: string;
  updated_at: string;
}

export type JobStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelling' | 'canceled';
export type TaskName = 'generate_selector' | 'extract_links' | 'process_project_entries' | 'generate_search_params';

export interface BackgroundJob {
  id: string; // UUID
  task_name: TaskName;
  project_id: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  result?: Record<string, any>;
  error_message?: string;
  total_items?: number;
  processed_items?: number;
  progress?: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: {
    current_page: number;
    per_page: number;
    total_items: number;
  };
}

export interface SingleResponse<T> {
  data: T;
}

export interface ModelInfo {
  id: string;
  name: string;
}

export interface ProviderInfo {
  id: string;
  name: string;
  models: ModelInfo[];
}

export interface GlobalTemplate {
  id: string;
  name: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface CreateProjectPayload {
  id: string;
  name: string;
  source_url?: string;
  prompt?: string;
  templates: ProjectTemplates;
  ai_provider_config: AiProviderConfig;
  requests_per_minute: number;
}

export interface ProjectAnalytics {
  total_requests: number;
  total_cost: number;
  total_input_tokens: number;
  total_output_tokens: number;
  average_latency_ms: number;
  link_status_counts: Record<LinkStatus, number>;
  job_status_counts: Record<JobStatus, number>;
  total_lorebook_entries: number;
  total_links: number;
  total_jobs: number;
}

export interface ApiRequestLog {
  id: string; // UUID
  project_id: string;
  job_id?: string; // UUID
  api_provider: string;
  model_used: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  request: Record<string, any>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  response?: Record<string, any>;
  input_tokens?: number;
  output_tokens?: number;
  calculated_cost?: number;
  latency_ms: number;
  timestamp: string; // ISO 8601 date string
  error: boolean;
}

export interface GlobalTemplate {
  id: string;
  name: string;
  content: string;
  created_at: string;
  updated_at: string;
}
