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

export type SourceCatalogEntryStatus = {
  name: string;
  display_name: string;
  platform: string;
  source_type: string;
  strategy: string;
  enabled: boolean;
  base_url: string | null;
  target_url: string | null;
  board: string | null;
  robots_url: string | null;
  default_max_items: number;
  default_max_pages: number;
  allow_robots_unavailable: boolean;
  allow_over18_public_confirm: boolean;
  notes: string | null;
  tags: string[];
  group: string;
  database_source_id: number | null;
  database_backed: boolean;
  post_count: number;
  latest_job: Record<string, unknown> | null;
  last_status: string | null;
  last_error: string | null;
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

export type PostsSearchResponse = {
  rows: PostResponse[];
  total: number;
  limit: number;
  offset: number;
  facets: Record<string, Array<{ value: string | null; count: number }>>;
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

export type KPIOverview = {
  total_sources: number;
  total_posts: number;
  successful_crawl_runs: number;
  failed_crawl_runs: number;
  parse_success_rate: number;
  duplicate_rate: number;
  total_crawl_runs: number;
};

export type AnalyticsOverview = {
  demo_dataset_present: boolean;
  kpis: KPIOverview;
  platforms: Array<{ platform: string; count: number }>;
  top_keywords: Array<{ keyword: string; count: number }>;
  top_posts: EngagementPost[];
  latest_jobs: Array<Record<string, unknown>>;
};

export type TrendAnalytics = {
  daily_post_count: Array<{ date: string; platform: string; count: number }>;
  top_boards: Array<{ board_or_forum: string; count: number }>;
};

export type KeywordAnalytics = {
  keywords: Array<{ keyword: string; count: number }>;
  by_platform: Array<{ platform: string; keyword: string; count: number }>;
};

export type EngagementPost = {
  id: number;
  source: string;
  platform: string;
  board_or_forum: string | null;
  title: string;
  published_at: string | null;
  like_count: number;
  comment_count: number;
  view_count: number;
  engagement_score: number;
  url: string | null;
};

export type EngagementAnalytics = {
  top_posts: EngagementPost[];
  missing_metrics: Record<string, number>;
  average_score_by_platform: Array<{ platform: string; average_engagement_score: number }>;
};

export type PlatformAnalytics = {
  platforms: Array<{
    platform: string;
    post_count: number;
    average_content_length: number;
    average_engagement_score: number;
    crawl_success_rate: number | null;
  }>;
};

export type DataQualityAnalytics = {
  total_posts: number;
  demo_records: number;
  checks: Array<{ name: string; count: number }>;
  policy_events: Array<{ category: string; count: number }>;
};

export type WorkflowSummary = {
  demo_dataset_present: boolean;
  latest_error: Record<string, unknown> | null;
  stages: Array<{
    key: string;
    label: string;
    status: string;
    count: number;
    error_reason: string | null;
  }>;
};

export type DashboardAnalytics = {
  kpis: KPIOverview;
  daily_platform_volume: Array<{ date: string; platform: string; count: number }>;
  platform_distribution: Array<{ platform: string; count: number }>;
  crawl_status_counts: Array<{ status: string; count: number }>;
  top_keywords: Array<{ keyword: string; count: number }>;
  top_posts: EngagementPost[];
  demo_live_ratio: { demo: number; live: number; total: number };
  policy_events: Array<{ category: string; count: number }>;
};

export type TimeSeriesAnalytics = {
  daily_by_platform: Array<{ date: string; platform: string; count: number }>;
  daily_by_source: Array<{ date: string; source: string; count: number }>;
  daily_by_board: Array<{ date: string; board_or_forum: string; count: number }>;
};

export type KeywordNetworkAnalytics = {
  nodes: Array<{ id: string; label: string; value: number; samples?: Array<Record<string, unknown>> }>;
  links: Array<{ source: string; target: string; value: number }>;
};

export type KeywordHeatmapAnalytics = {
  platforms: string[];
  keywords: string[];
  cells: Array<{ platform: string; keyword: string; count: number }>;
};

export type SourceHealthAnalytics = {
  rows: Array<{
    source: string;
    display_name: string;
    platform: string;
    enabled: boolean;
    post_count: number;
    success_rate: number | null;
    failed_count: number;
    policy_events: number;
    freshness: string | null;
    last_status: string | null;
    last_error: string | null;
  }>;
};

export type GraphNode = {
  id: string;
  label?: string;
  type?: string;
  count?: number;
  position?: { x: number; y: number };
  data?: Record<string, unknown>;
};

export type GraphEdge = {
  id?: string;
  source: string;
  target: string;
  label?: string;
  animated?: boolean;
};

export type LineageAnalytics = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export type CrawlFlowAnalytics = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export type DataQualityTableAnalytics = {
  missing_content: Array<Record<string, unknown>>;
  duplicates: Array<Record<string, unknown>>;
  failed_crawls: Array<Record<string, unknown>>;
  policy_blocks: Array<Record<string, unknown>>;
};

export type DemoStoryStep = {
  index: number;
  key: string;
  label: string;
  status: string;
  count: number;
  purpose: string;
  inputs: string[];
  outputs: string[];
  tables: string[];
  artifact: string | null;
  failure_modes: string[];
  compliance: string;
  engineering_highlight: string;
};

export type StoryGraph = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export type DemoStoryAnalytics = {
  title: string;
  subtitle: string;
  demo_dataset_present: boolean;
  kpis: KPIOverview;
  demo_live_ratio: { demo: number; live: number; total: number };
  walkthrough_steps: DemoStoryStep[];
  architecture: StoryGraph;
  lifecycle: StoryGraph;
  interview_highlights: string[];
};

export type DemoWorkflowRunResponse = {
  status: string;
  stats: Record<string, unknown>;
  summary: Record<string, unknown>;
};

export type DrilldownResponse = {
  kind: string;
  id: string;
  title: string;
  subtitle: string;
  summary: Record<string, unknown>;
  metadata: Record<string, unknown>;
  related_posts: Array<Record<string, unknown>>;
  related_jobs: Array<Record<string, unknown>>;
  quality_flags: string[];
  raw_payload: Record<string, unknown>;
};
