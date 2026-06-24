import {
  Activity,
  BarChart3,
  BookOpenCheck,
  ClipboardCheck,
  Database,
  FileSpreadsheet,
  FileText,
  GitBranch,
  Layers,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api, type PostFilters } from './api/client';
import type {
  AnalyticsOverview,
  CrawlJobResponse,
  DataQualityAnalytics,
  DashboardSummary,
  DiagnosticsResponse,
  EngagementAnalytics,
  KeywordAnalytics,
  PlatformAnalytics,
  PostResponse,
  ReportSummary,
  SourceCatalogEntryStatus,
  SourceResponse,
  TrendAnalytics,
  VerifyResponse,
  WorkflowSummary,
} from './api/types';
import { ControlPanel } from './components/ControlPanel';
import { JobsTimeline } from './components/JobsTimeline';
import { PostsExplorer } from './components/PostsExplorer';
import { ReportsPanel } from './components/ReportsPanel';
import { SourceOverview } from './components/SourceOverview';
import { StatusBadge } from './components/StatusBadge';
import { SummaryCards } from './components/SummaryCards';

type PageKey =
  | 'overview'
  | 'sources'
  | 'workflow'
  | 'runs'
  | 'explorer'
  | 'trends'
  | 'keywords'
  | 'engagement'
  | 'platforms'
  | 'quality'
  | 'reports'
  | 'compliance'
  | 'settings';

const pages: Array<{ key: PageKey; label: string; icon: typeof Activity }> = [
  { key: 'overview', label: 'Overview Dashboard', icon: BarChart3 },
  { key: 'sources', label: 'Source Registry', icon: Database },
  { key: 'workflow', label: 'Crawler Workflow', icon: GitBranch },
  { key: 'runs', label: 'Crawl Runs', icon: Activity },
  { key: 'explorer', label: 'Data Explorer', icon: Search },
  { key: 'trends', label: 'Trend Analytics', icon: TrendingUp },
  { key: 'keywords', label: 'Keyword & Topic Mining', icon: Sparkles },
  { key: 'engagement', label: 'Engagement Analysis', icon: ClipboardCheck },
  { key: 'platforms', label: 'Platform Comparison', icon: Layers },
  { key: 'quality', label: 'Data Quality & Lineage', icon: BookOpenCheck },
  { key: 'reports', label: 'Excel Report Center', icon: FileSpreadsheet },
  { key: 'compliance', label: 'Compliance & Diagnostics', icon: ShieldCheck },
  { key: 'settings', label: 'Settings', icon: Settings },
];

export function App() {
  const [activePage, setActivePage] = useState<PageKey>('overview');
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [trends, setTrends] = useState<TrendAnalytics | null>(null);
  const [keywords, setKeywords] = useState<KeywordAnalytics | null>(null);
  const [engagement, setEngagement] = useState<EngagementAnalytics | null>(null);
  const [platforms, setPlatforms] = useState<PlatformAnalytics | null>(null);
  const [quality, setQuality] = useState<DataQualityAnalytics | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowSummary | null>(null);
  const [sources, setSources] = useState<SourceResponse[]>([]);
  const [sourceCatalog, setSourceCatalog] = useState<SourceCatalogEntryStatus[]>([]);
  const [posts, setPosts] = useState<PostResponse[]>([]);
  const [jobs, setJobs] = useState<CrawlJobResponse[]>([]);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [selectedPost, setSelectedPost] = useState<PostResponse | null>(null);
  const [filters, setFilters] = useState<PostFilters>({ limit: 50 });
  const [loadingPosts, setLoadingPosts] = useState(false);
  const [status, setStatus] = useState('Connecting to backend...');

  const loadCore = useCallback(async () => {
    try {
      const [
        nextSummary,
        nextSources,
        nextSourceCatalog,
        nextJobs,
        nextReports,
        nextOverview,
        nextTrends,
        nextKeywords,
        nextEngagement,
        nextPlatforms,
        nextQuality,
        nextWorkflow,
      ] = await Promise.all([
        api.summary(),
        api.sources(),
        api.sourceCatalog(),
        api.jobs(),
        api.reports(),
        api.analytics.overview(),
        api.analytics.trends(),
        api.analytics.keywords(),
        api.analytics.engagement(),
        api.analytics.platforms(),
        api.analytics.dataQuality(),
        api.analytics.workflow(),
      ]);
      setSummary(nextSummary);
      setSources(nextSources);
      setSourceCatalog(nextSourceCatalog);
      setJobs(nextJobs);
      setReports(nextReports);
      setOverview(nextOverview);
      setTrends(nextTrends);
      setKeywords(nextKeywords);
      setEngagement(nextEngagement);
      setPlatforms(nextPlatforms);
      setQuality(nextQuality);
      setWorkflow(nextWorkflow);
      setStatus(nextSummary.health.database_ready ? 'API ready' : 'Database schema needs init');
    } catch (error) {
      setStatus((error as Error).message);
    }
  }, []);

  const loadPosts = useCallback(async (nextFilters: PostFilters) => {
    setLoadingPosts(true);
    try {
      setPosts(await api.posts(nextFilters));
    } catch (error) {
      setStatus((error as Error).message);
    } finally {
      setLoadingPosts(false);
    }
  }, []);

  useEffect(() => {
    void loadCore();
  }, [loadCore]);

  useEffect(() => {
    void loadPosts(filters);
  }, [filters, loadPosts]);

  async function refreshAfterRun<T>(operation: Promise<T>): Promise<T> {
    const result = await operation;
    await loadCore();
    await loadPosts(filters);
    return result;
  }

  return (
    <main className="workbench-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <span className="brand-mark">TW</span>
          <div>
            <p>Taiwan Public Web</p>
            <strong>Intelligence Workbench</strong>
          </div>
        </div>
        <nav className="sidebar-nav" aria-label="Workbench navigation">
          {pages.map((page) => {
            const Icon = page.icon;
            return (
              <button
                key={page.key}
                className={activePage === page.key ? 'active' : ''}
                type="button"
                onClick={() => setActivePage(page.key)}
              >
                <Icon size={17} />
                <span>{page.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <section className="content-shell">
        <header className="topbar">
          <div>
            <p className="eyebrow">Public data pipeline portfolio</p>
            <h1>{pages.find((page) => page.key === activePage)?.label}</h1>
          </div>
          <div className="topbar-actions">
            <span className="api-status">{status}</span>
            <button className="icon-button" onClick={() => void loadCore()} aria-label="Refresh dashboard">
              <RefreshCw size={17} />
            </button>
          </div>
        </header>

        {overview?.demo_dataset_present && (
          <div className="demo-banner">
            Demo dataset generated for portfolio preview. Records are labeled with crawl_source=demo.
          </div>
        )}

        {renderPage(activePage)}
      </section>

      {selectedPost && <PostDrawer post={selectedPost} onClose={() => setSelectedPost(null)} />}
    </main>
  );

  function renderPage(page: PageKey) {
    switch (page) {
      case 'overview':
        return (
          <>
            <SummaryCards summary={summary} />
            <OverviewDashboard overview={overview} trends={trends} jobs={jobs} />
          </>
        );
      case 'sources':
        return <SourceRegistry sources={sources} catalog={sourceCatalog} summary={summary} />;
      case 'workflow':
        return <WorkflowPage workflow={workflow} />;
      case 'runs':
        return <JobsTimeline jobs={jobs} />;
      case 'explorer':
        return (
          <PostsExplorer
            posts={posts}
            filters={filters}
            loading={loadingPosts}
            onFiltersChange={(nextFilters) => setFilters({ ...nextFilters, limit: 50 })}
            onSelectPost={setSelectedPost}
          />
        );
      case 'trends':
        return <TrendPage trends={trends} />;
      case 'keywords':
        return <KeywordPage keywords={keywords} />;
      case 'engagement':
        return <EngagementPage engagement={engagement} />;
      case 'platforms':
        return <PlatformPage platforms={platforms} />;
      case 'quality':
        return <QualityPage quality={quality} />;
      case 'reports':
        return <ReportsCenter reports={reports} />;
      case 'compliance':
        return (
          <CompliancePage
            jobs={jobs}
            quality={quality}
            onVerifyDcard={(payload) => refreshAfterRun(api.verifyDcard(payload))}
            onVerifyPtt={(payload) => refreshAfterRun(api.verifyPtt(payload))}
            onVerifyNews={(payload) => refreshAfterRun(api.verifyNewsRss(payload))}
            onDiagnoseDcard={(payload) => refreshAfterRun(api.diagnoseDcard(payload))}
          />
        );
      case 'settings':
        return <SettingsPage status={status} />;
      default:
        return null;
    }
  }
}

function OverviewDashboard({
  overview,
  trends,
  jobs,
}: {
  overview: AnalyticsOverview | null;
  trends: TrendAnalytics | null;
  jobs: CrawlJobResponse[];
}) {
  const platformData = overview?.platforms ?? [];
  const dailyData = compressDailyTrends(trends?.daily_post_count ?? []);
  return (
    <section className="page-grid">
      <div className="panel">
        <div className="panel-header">
          <h2>Platform Volume</h2>
        </div>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={platformData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="platform" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="count" fill="#1f7a5f" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="panel">
        <div className="panel-header">
          <h2>Daily Posts</h2>
        </div>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={dailyData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" minTickGap={20} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Line type="monotone" dataKey="count" stroke="#1455d9" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="panel">
        <div className="panel-header">
          <h2>Top Keywords</h2>
        </div>
        <div className="keyword-list">
          {(overview?.top_keywords ?? []).map((item) => (
            <span className="keyword-chip" key={item.keyword}>
              {item.keyword}<strong>{item.count}</strong>
            </span>
          ))}
        </div>
      </div>
      <div className="panel">
        <div className="panel-header">
          <h2>Latest Hot Posts</h2>
        </div>
        <div className="ranked-list">
          {(overview?.top_posts ?? []).slice(0, 6).map((post) => (
            <div className="ranked-row" key={post.id}>
              <div>
                <strong>{post.title}</strong>
                <span>{post.platform} / {post.board_or_forum ?? '-'}</span>
              </div>
              <b>{post.engagement_score}</b>
            </div>
          ))}
        </div>
      </div>
      <div className="panel wide-panel">
        <div className="panel-header">
          <h2>Recent Crawl Timeline</h2>
        </div>
        <div className="job-list">
          {jobs.slice(0, 6).map((job) => (
            <div className="job-row" key={job.id}>
              <div>
                <div className="job-title">{job.source} / {job.job_type}</div>
                <div className="job-meta">{job.request_count} requests / {job.item_count} items</div>
              </div>
              <StatusBadge value={job.status} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function SourceRegistry({
  sources,
  catalog,
  summary,
}: {
  sources: SourceResponse[];
  catalog: SourceCatalogEntryStatus[];
  summary: DashboardSummary | null;
}) {
  return (
    <section className="page-grid">
      <SourceOverview sources={sources} summary={summary} />
      <div className="panel">
        <div className="panel-header">
          <h2>Catalog Summary</h2>
        </div>
        <div className="metadata-list">
          <div className="metadata-row">
            <strong>Configured Sources</strong>
            <span>{catalog.length}</span>
          </div>
          <div className="metadata-row">
            <strong>Enabled Sources</strong>
            <span>{catalog.filter((source) => source.enabled).length}</span>
          </div>
          <div className="metadata-row">
            <strong>Database-backed</strong>
            <span>{catalog.filter((source) => source.database_backed).length}</span>
          </div>
        </div>
      </div>
      <div className="panel wide-panel">
        <div className="panel-header">
          <h2>Source Catalog</h2>
          <span className="pill">YAML-driven batch crawl targets</span>
        </div>
        <div className="catalog-grid">
          {catalog.map((source) => (
            <div className="catalog-card" key={source.name}>
              <div className="catalog-title">
                <div>
                  <strong>{source.display_name}</strong>
                  <span>{source.name}</span>
                </div>
                <StatusBadge value={source.last_status ?? (source.enabled ? 'catalog_ready' : 'disabled')} />
              </div>
              <div className="catalog-meta">
                <span>{source.group}</span>
                <span>{source.platform}</span>
                <span>{source.strategy}</span>
                <span>{source.post_count} posts</span>
              </div>
              <p>{source.board ?? source.target_url ?? source.base_url}</p>
              {source.last_error && <small>{source.last_error}</small>}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function WorkflowPage({ workflow }: { workflow: WorkflowSummary | null }) {
  return (
    <section className="panel wide-panel">
      <div className="panel-header">
        <h2>Crawl Pipeline</h2>
        {workflow?.latest_error && <span className="pill">latest stop condition captured</span>}
      </div>
      <div className="workflow-grid">
        {(workflow?.stages ?? []).map((stage, index) => (
          <div className="workflow-step" key={stage.key}>
            <span className="step-index">{index + 1}</span>
            <div>
              <strong>{stage.label}</strong>
              <p>{stage.count} records/events</p>
              {stage.error_reason && <small>{stage.error_reason}</small>}
            </div>
            <StatusBadge value={stage.status} />
          </div>
        ))}
      </div>
    </section>
  );
}

function TrendPage({ trends }: { trends: TrendAnalytics | null }) {
  return (
    <section className="page-grid">
      <div className="panel wide-panel">
        <div className="panel-header">
          <h2>Daily Trend</h2>
        </div>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={compressDailyTrends(trends?.daily_post_count ?? [])}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Line type="monotone" dataKey="count" stroke="#1455d9" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <SimpleList title="Top Boards / Forums" rows={(trends?.top_boards ?? []).map((item) => [item.board_or_forum, item.count])} />
    </section>
  );
}

function KeywordPage({ keywords }: { keywords: KeywordAnalytics | null }) {
  return (
    <section className="page-grid">
      <SimpleList title="Keyword Frequency" rows={(keywords?.keywords ?? []).map((item) => [item.keyword, item.count])} />
      <SimpleList
        title="Platform Keyword Distribution"
        rows={(keywords?.by_platform ?? []).slice(0, 16).map((item) => [`${item.platform} / ${item.keyword}`, item.count])}
      />
    </section>
  );
}

function EngagementPage({ engagement }: { engagement: EngagementAnalytics | null }) {
  return (
    <section className="page-grid">
      <SimpleList
        title="Average Score by Platform"
        rows={(engagement?.average_score_by_platform ?? []).map((item) => [item.platform, item.average_engagement_score])}
      />
      <SimpleList
        title="Missing Metrics"
        rows={Object.entries(engagement?.missing_metrics ?? {})}
      />
      <div className="panel wide-panel">
        <div className="panel-header">
          <h2>Top Engagement Posts</h2>
        </div>
        <div className="ranked-list">
          {(engagement?.top_posts ?? []).slice(0, 12).map((post) => (
            <div className="ranked-row" key={post.id}>
              <div>
                <strong>{post.title}</strong>
                <span>{post.platform} / comments {post.comment_count} / likes {post.like_count}</span>
              </div>
              <b>{post.engagement_score}</b>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function PlatformPage({ platforms }: { platforms: PlatformAnalytics | null }) {
  return (
    <section className="panel wide-panel">
      <div className="panel-header">
        <h2>Cross-platform Comparison</h2>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Platform</th>
              <th>Posts</th>
              <th>Avg Content Length</th>
              <th>Avg Engagement</th>
              <th>Crawl Success Rate</th>
            </tr>
          </thead>
          <tbody>
            {(platforms?.platforms ?? []).map((platform) => (
              <tr key={platform.platform}>
                <td>{platform.platform}</td>
                <td>{platform.post_count}</td>
                <td>{platform.average_content_length}</td>
                <td>{platform.average_engagement_score}</td>
                <td>{platform.crawl_success_rate ?? '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function QualityPage({ quality }: { quality: DataQualityAnalytics | null }) {
  return (
    <section className="page-grid">
      <SimpleList title="Data Quality Checks" rows={(quality?.checks ?? []).map((item) => [item.name, item.count])} />
      <SimpleList title="Policy Events" rows={(quality?.policy_events ?? []).map((item) => [item.category, item.count])} />
      <div className="panel wide-panel">
        <div className="panel-header">
          <h2>Lineage Model</h2>
        </div>
        <div className="lineage-strip">
          {['source', 'crawl_run', 'raw_response', 'parser', 'normalized_record', 'analysis_result'].map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
      </div>
    </section>
  );
}

function ReportsCenter({ reports }: { reports: ReportSummary[] }) {
  return (
    <section className="dashboard-grid">
      <ReportsPanel reports={reports} />
      <div className="panel">
        <div className="panel-header">
          <h2>Excel Report Sheets</h2>
        </div>
        <div className="metadata-list">
          {['Summary', 'Raw Data', 'Daily Trend', 'Keyword Matches', 'Top Posts', 'Platform Comparison', 'Data Quality', 'Crawl Runs'].map((sheet) => (
            <div className="metadata-row" key={sheet}>
              <strong>{sheet}</strong>
              <span>ready for export-excel-report pipeline</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function CompliancePage({
  jobs,
  quality,
  onVerifyDcard,
  onVerifyPtt,
  onVerifyNews,
  onDiagnoseDcard,
}: {
  jobs: CrawlJobResponse[];
  quality: DataQualityAnalytics | null;
  onVerifyDcard: (payload: { forum: string; mode: string; max_posts: number }) => Promise<VerifyResponse>;
  onVerifyPtt: (payload: {
    board: string;
    max_pages: number;
    max_posts: number;
    allow_robots_unavailable: boolean;
    allow_over18_public_confirm: boolean;
  }) => Promise<VerifyResponse>;
  onVerifyNews: (payload: { source_name: string; feed_url: string; max_articles: number }) => Promise<VerifyResponse>;
  onDiagnoseDcard: (payload: { forum: string }) => Promise<DiagnosticsResponse>;
}) {
  return (
    <section className="dashboard-grid">
      <ControlPanel
        onVerifyDcard={onVerifyDcard}
        onVerifyPtt={onVerifyPtt}
        onVerifyNews={onVerifyNews}
        onDiagnoseDcard={onDiagnoseDcard}
      />
      <SimpleList title="Stop Conditions" rows={(quality?.policy_events ?? []).map((item) => [item.category, item.count])} />
      <div className="panel wide-panel">
        <div className="panel-header">
          <h2>Recent Compliance Outcomes</h2>
        </div>
        <div className="job-list">
          {jobs.map((job) => (
            <div className="job-row" key={job.id}>
              <div>
                <div className="job-title">{job.source} / {job.job_type}</div>
                <div className="job-meta">{job.error_category ?? 'no policy event'} / {job.error_reason ?? 'ok'}</div>
              </div>
              <StatusBadge value={job.error_category ?? job.status} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function SettingsPage({ status }: { status: string }) {
  return (
    <section className="page-grid">
      <div className="panel">
        <div className="panel-header">
          <h2>Backend</h2>
        </div>
        <div className="metadata-list">
          <div className="metadata-row">
            <strong>API Status</strong>
            <span>{status}</span>
          </div>
          <div className="metadata-row">
            <strong>Default API Base URL</strong>
            <span>http://127.0.0.1:8000</span>
          </div>
        </div>
      </div>
      <div className="panel">
        <div className="panel-header">
          <h2>Portfolio Commands</h2>
        </div>
        <code className="command-block">dcard-crawler seed-demo-data --rows 2000 --reset-demo</code>
        <code className="command-block">dcard-crawler export-excel-report --output data/exports/analysis_report.xlsx</code>
      </div>
    </section>
  );
}

function SimpleList({ title, rows }: { title: string; rows: Array<[string, number | string]> }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <h2>{title}</h2>
      </div>
      <div className="metadata-list">
        {rows.length ? rows.map(([label, value]) => (
          <div className="metadata-row" key={label}>
            <strong>{label}</strong>
            <span>{value}</span>
          </div>
        )) : <div className="empty-state">No data yet.</div>}
      </div>
    </div>
  );
}

function PostDrawer({ post, onClose }: { post: PostResponse; onClose: () => void }) {
  return (
    <aside className="drawer" aria-label="Post detail">
      <div className="drawer-header">
        <div>
          <p className="eyebrow">{post.platform} / {post.board_or_forum ?? '-'}</p>
          <h2>{post.title}</h2>
        </div>
        <button className="icon-button" type="button" onClick={onClose} aria-label="Close post detail">
          <X size={17} />
        </button>
      </div>
      <div className="drawer-body">
        <p>{post.content || post.excerpt || 'No content captured.'}</p>
        <div className="metadata-list">
          <div className="metadata-row"><strong>Source</strong><span>{post.source}</span></div>
          <div className="metadata-row"><strong>External ID</strong><span>{post.external_id}</span></div>
          <div className="metadata-row"><strong>Published</strong><span>{post.published_at ?? '-'}</span></div>
          <div className="metadata-row"><strong>Comments</strong><span>{post.comment_count}</span></div>
          <div className="metadata-row"><strong>Likes</strong><span>{post.like_count}</span></div>
          <div className="metadata-row"><strong>Views</strong><span>{post.view_count}</span></div>
          <div className="metadata-row"><strong>Content Hash</strong><span>{post.content_hash ?? '-'}</span></div>
          <div className="metadata-row"><strong>URL</strong><span>{post.url ?? '-'}</span></div>
        </div>
        {post.url && <a className="external-link" href={post.url} target="_blank" rel="noreferrer"><FileText size={16} /> Open source URL</a>}
      </div>
    </aside>
  );
}

function compressDailyTrends(rows: Array<{ date: string; platform: string; count: number }>) {
  const totals = new Map<string, number>();
  rows.forEach((row) => {
    totals.set(row.date, (totals.get(row.date) ?? 0) + row.count);
  });
  return Array.from(totals.entries())
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([date, count]) => ({ date, count }));
}
