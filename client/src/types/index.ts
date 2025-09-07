// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type ModelParameters = Record<string, any>;

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
  prompt?: string;
  templates: ProjectTemplates;
  requests_per_minute: number;
  search_params?: SearchParams;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
  credential_id?: string; // UUID
  model_name?: string;
  model_parameters: ModelParameters;
}

export interface CreateProjectPayload {
  id: string;
  name: string;
  prompt?: string;
  templates: ProjectTemplates;
  requests_per_minute: number;
  credential_id?: string;
  model_name?: string;
  model_parameters: ModelParameters;
}

export interface CredentialValues {
  api_key?: string;
  base_url?: string;
}

export interface Credential {
  id: string; // UUID
  name: string;
  provider_type: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  public_values: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface CreateCredentialPayload {
  name: string;
  provider_type: string;
  values: CredentialValues;
}

export type UpdateCredentialPayload = Partial<CreateCredentialPayload>;

export interface TestCredentialPayload {
  provider_type: string;
  values: CredentialValues;
  model_name: string;
  credential_id?: string;
}

export interface TestCredentialResult {
  success: boolean;
  message: string;
}

export interface ProjectSource {
  id: string; // UUID
  project_id: string;
  url: string;
  link_extraction_selector?: string[];
  link_extraction_pagination_selector?: string;
  max_pages_to_crawl: number;
  max_crawl_depth: number;
  last_crawled_at?: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectSourceHierarchy {
  id: string; // UUID
  project_id: string;
  parent_source_id: string; // UUID
  child_source_id: string; // UUID
  created_at: string;
}

export type LinkStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'skipped';

export interface Link {
  id: string; // UUID
  project_id: string;
  url: string;
  status: LinkStatus;
  error_message?: string;
  skip_reason?: string;
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

export interface UpdateLorebookEntryPayload {
  title?: string;
  content?: string;
  keywords?: string[];
}

export type JobStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelling' | 'canceled';
export type TaskName =
  | 'discover_and_crawl_sources'
  | 'confirm_links'
  | 'process_project_entries'
  | 'generate_search_params'
  | 'rescan_links';

export interface ProcessProjectEntriesPayload {
  project_id: string;
  link_ids?: string[];
}

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
  configured: boolean;
}

export interface GlobalTemplate {
  id: string;
  name: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectAnalytics {
  total_requests: number;
  total_cost: number;
  has_unknown_costs: boolean;
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

export interface TestSelectorsPayload {
  url: string;
  content_selectors: string[];
  pagination_selector?: string;
}

export interface TestSelectorsResult {
  content_links: string[];
  pagination_link?: string;
  error?: string;
  link_count: number;
}
