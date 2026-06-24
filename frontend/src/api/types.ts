export type HealthResponse = {
  status: string;
  database_ready: boolean;
};

export type SourceResponse = {
  id: number;
  name: string;
  source_type: string;
  base_url: string | null;
  robots_url: string | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type PostResponse = {
  id: number;
  source: string;
  source_id: number;
  platform: string;
  external_id: string;
  post_id: number | null;
  board_or_forum: string | null;
  title: string;
  excerpt: string | null;
  content: string | null;
  published_at: string | null;
  created_at: string | null;
  crawled_at: string;
  like_count: number;
  comment_count: number;
  share_count: number;
  view_count: number;
  url: string | null;
  canonical_url: string | null;
  content_hash: string | null;
};

export type CrawlJobResponse = {
  id: number;
  source: string;
  source_id: number;
  job_type: string;
  target_url: string | null;
  status: string;
  started_at: string;
  finished_at: string | null;
  error_category: string | null;
  error_reason: string | null;
  request_count: number;
  item_count: number;
};

export type ReportSummary = {
  path: string;
  report_type: string;
  platform: string | null;
  source: string | null;
  generated_at: string | null;
  job_id: number | null;
  status: string | null;
};

export type DashboardSummary = {
  counts: Record<string, number>;
  recent_jobs: CrawlJobResponse[];
  recent_reports: ReportSummary[];
  platforms: Record<string, number>;
  health: HealthResponse;
};

export type VerifyResponse = {
  platform: string;
  source: string;
  job_id: number | null;
  status: string | null;
  quality_status: string | null;
  report_path: string;
  stats: Record<string, unknown>;
};

export type DiagnosticsResponse = {
  platform: string;
  forum: string;
  report_path: string;
  summary: Record<string, unknown>;
  endpoints: Array<Record<string, unknown>>;
};
