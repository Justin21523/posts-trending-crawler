import type {
  AnalyticsOverview,
  CrawlJobResponse,
  CrawlFlowAnalytics,
  DataQualityAnalytics,
  DataQualityTableAnalytics,
  DashboardAnalytics,
  DashboardSummary,
  DemoStoryAnalytics,
  DemoWorkflowRunResponse,
  DiagnosticsResponse,
  DrilldownResponse,
  ComplianceSummary,
  EngagementAnalytics,
  ExcelReportRunResponse,
  KeywordHeatmapAnalytics,
  HealthResponse,
  KeywordAnalytics,
  KeywordInsightsAnalytics,
  KeywordNetworkAnalytics,
  LineageAnalytics,
  PlatformAnalytics,
  PostResponse,
  PostsSearchResponse,
  ReportSummary,
  SourceHealthAnalytics,
  SourceCatalogEntryStatus,
  SourceResponse,
  TopicAnalytics,
  TrendAnalytics,
  TimeSeriesAnalytics,
  VerifyResponse,
  WorkflowSummary,
} from './types';

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000';
const API_BASE_CANDIDATES = [
  import.meta.env.VITE_API_BASE_URL,
  DEFAULT_API_BASE_URL,
  'http://127.0.0.1:8001',
  'http://localhost:8000',
  'http://localhost:8001',
].filter(Boolean) as string[];

let activeApiBaseUrl: string | null = null;
let apiBaseUrlPromise: Promise<string> | null = null;

function isCrawlerHealth(payload: unknown): payload is HealthResponse {
  return (
    typeof payload === 'object' &&
    payload !== null &&
    'database_ready' in payload &&
    typeof (payload as HealthResponse).database_ready === 'boolean'
  );
}

async function resolveApiBaseUrl(): Promise<string> {
  if (activeApiBaseUrl) return activeApiBaseUrl;
  if (apiBaseUrlPromise) return apiBaseUrlPromise;
  apiBaseUrlPromise = (async () => {
    const errors: string[] = [];
    for (const baseUrl of Array.from(new Set(API_BASE_CANDIDATES))) {
      try {
        const response = await fetch(`${baseUrl}/health`);
        if (!response.ok) {
          errors.push(`${baseUrl}: HTTP ${response.status}`);
          continue;
        }
        const payload = await response.json();
        if (!isCrawlerHealth(payload)) {
          errors.push(`${baseUrl}: API mismatch`);
          continue;
        }
        activeApiBaseUrl = baseUrl;
        return baseUrl;
      } catch (error) {
        errors.push(`${baseUrl}: ${(error as Error).message}`);
      }
    }
    apiBaseUrlPromise = null;
    throw new Error(`無法連線到 Taiwan Crawler API。${errors.join(' | ')}`);
  })();
  return apiBaseUrlPromise;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const apiBaseUrl = await resolveApiBaseUrl();
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export type PostFilters = {
  platform?: string;
  source?: string;
  board_or_forum?: string;
  keyword?: string;
  limit?: number;
  offset?: number;
};

function queryString(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') {
      search.set(key, String(value));
    }
  });
  const text = search.toString();
  return text ? `?${text}` : '';
}

export const api = {
  runtime: {
    baseUrl: () => activeApiBaseUrl ?? import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL,
  },
  health: () => request<HealthResponse>('/health'),
  summary: () => request<DashboardSummary>('/summary'),
  sources: () => request<SourceResponse[]>('/sources'),
  sourceCatalog: () => request<SourceCatalogEntryStatus[]>('/source-catalog'),
  posts: (filters: PostFilters) => request<PostResponse[]>(`/posts${queryString(filters)}`),
  postsSearch: (filters: PostFilters) =>
    request<PostsSearchResponse>(`/posts/search${queryString(filters)}`),
  jobs: () => request<CrawlJobResponse[]>('/crawl-jobs?limit=20'),
  reports: () => request<ReportSummary[]>('/reports'),
  verifyDcard: (payload: { forum: string; mode: string; max_posts: number }) =>
    request<VerifyResponse>('/verify/dcard', { method: 'POST', body: JSON.stringify(payload) }),
  verifyPtt: (payload: {
    board: string;
    max_pages: number;
    max_posts: number;
    allow_robots_unavailable: boolean;
    allow_over18_public_confirm: boolean;
  }) => request<VerifyResponse>('/verify/ptt', { method: 'POST', body: JSON.stringify(payload) }),
  verifyNewsRss: (payload: { source_name: string; feed_url: string; max_articles: number }) =>
    request<VerifyResponse>('/verify/news-rss', { method: 'POST', body: JSON.stringify(payload) }),
  diagnoseDcard: (payload: { forum: string; sample_post_id?: number }) =>
    request<DiagnosticsResponse>('/diagnostics/dcard', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  analytics: {
    overview: () => request<AnalyticsOverview>('/analytics/overview'),
    trends: () => request<TrendAnalytics>('/analytics/trends'),
    keywords: () => request<KeywordAnalytics>('/analytics/keywords'),
    engagement: () => request<EngagementAnalytics>('/analytics/engagement'),
    platforms: () => request<PlatformAnalytics>('/analytics/platforms'),
    dataQuality: () => request<DataQualityAnalytics>('/analytics/data-quality'),
    workflow: () => request<WorkflowSummary>('/workflow/summary'),
    dashboard: () => request<DashboardAnalytics>('/analytics/dashboard'),
    timeSeries: () => request<TimeSeriesAnalytics>('/analytics/time-series'),
    keywordNetwork: () => request<KeywordNetworkAnalytics>('/analytics/keyword-network'),
    keywordInsights: () => request<KeywordInsightsAnalytics>('/analytics/keyword-insights'),
    keywordHeatmap: () => request<KeywordHeatmapAnalytics>('/analytics/keyword-heatmap'),
    topics: () => request<TopicAnalytics>('/analytics/topics'),
    sourceHealth: () => request<SourceHealthAnalytics>('/analytics/source-health'),
    lineage: () => request<LineageAnalytics>('/analytics/lineage'),
    crawlFlow: () => request<CrawlFlowAnalytics>('/analytics/crawl-flow'),
    topPosts: () => request<{ rows: PostResponse[] | Array<Record<string, unknown>> }>('/analytics/top-posts'),
    dataQualityTable: () => request<DataQualityTableAnalytics>('/analytics/data-quality-table'),
    demoStory: () => request<DemoStoryAnalytics>('/analytics/demo-story'),
    complianceSummary: () => request<ComplianceSummary>('/analytics/compliance-summary'),
    drilldown: (payload: { kind: string; id: string | number }) =>
      request<DrilldownResponse>(
        `/analytics/drilldown${queryString({ kind: payload.kind, id: payload.id })}`,
      ),
  },
  reportsApi: {
    generateExcel: (payload: { output?: string } = {}) =>
      request<ExcelReportRunResponse>(
        `/reports/excel${queryString({ output: payload.output ?? 'data/exports/analysis_report.xlsx' })}`,
        { method: 'POST' },
      ),
    downloadUrl: (path: string) => `${api.runtime.baseUrl()}/reports/download${queryString({ path })}`,
  },
  demo: {
    runWorkflow: (payload: { rows?: number; reset_demo?: boolean } = {}) =>
      request<DemoWorkflowRunResponse>(
        `/demo/workflow/run${queryString({
          rows: payload.rows ?? 10000,
          reset_demo: payload.reset_demo === undefined ? 'true' : String(payload.reset_demo),
        })}`,
        { method: 'POST' },
      ),
  },
};
