import type {
  AnalyticsOverview,
  CrawlJobResponse,
  CrawlFlowAnalytics,
  DataQualityAnalytics,
  DataQualityTableAnalytics,
  DashboardAnalytics,
  DashboardSummary,
  DiagnosticsResponse,
  EngagementAnalytics,
  KeywordHeatmapAnalytics,
  HealthResponse,
  KeywordAnalytics,
  KeywordNetworkAnalytics,
  LineageAnalytics,
  PlatformAnalytics,
  PostResponse,
  ReportSummary,
  SourceHealthAnalytics,
  SourceCatalogEntryStatus,
  SourceResponse,
  TrendAnalytics,
  TimeSeriesAnalytics,
  VerifyResponse,
  WorkflowSummary,
} from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
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
};

function queryString(params: Record<string, string | number | undefined>): string {
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
  health: () => request<HealthResponse>('/health'),
  summary: () => request<DashboardSummary>('/summary'),
  sources: () => request<SourceResponse[]>('/sources'),
  sourceCatalog: () => request<SourceCatalogEntryStatus[]>('/source-catalog'),
  posts: (filters: PostFilters) => request<PostResponse[]>(`/posts${queryString(filters)}`),
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
    keywordHeatmap: () => request<KeywordHeatmapAnalytics>('/analytics/keyword-heatmap'),
    sourceHealth: () => request<SourceHealthAnalytics>('/analytics/source-health'),
    lineage: () => request<LineageAnalytics>('/analytics/lineage'),
    crawlFlow: () => request<CrawlFlowAnalytics>('/analytics/crawl-flow'),
    topPosts: () => request<{ rows: PostResponse[] | Array<Record<string, unknown>> }>('/analytics/top-posts'),
    dataQualityTable: () => request<DataQualityTableAnalytics>('/analytics/data-quality-table'),
  },
};
