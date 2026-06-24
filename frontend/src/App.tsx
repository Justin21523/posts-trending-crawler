import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from '@tanstack/react-table';
import ForceGraph2D from 'react-force-graph-2d';
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
  Network,
  PlayCircle,
  RefreshCw,
  Route,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api, type PostFilters } from './api/client';
import type {
  AnalyticsOverview,
  CrawlJobResponse,
  CrawlFlowAnalytics,
  DataQualityAnalytics,
  DataQualityTableAnalytics,
  DashboardAnalytics,
  DashboardSummary,
  DemoStoryAnalytics,
  DemoStoryStep,
  DiagnosticsResponse,
  DrilldownResponse,
  EngagementAnalytics,
  GraphNode,
  KeywordHeatmapAnalytics,
  KeywordAnalytics,
  KeywordNetworkAnalytics,
  LineageAnalytics,
  PlatformAnalytics,
  PostResponse,
  PostsSearchResponse,
  ReportSummary,
  SourceCatalogEntryStatus,
  SourceHealthAnalytics,
  SourceResponse,
  StoryGraph,
  TimeSeriesAnalytics,
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
  | 'demo'
  | 'architecture'
  | 'sources'
  | 'workflow'
  | 'lifecycle'
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
  { key: 'demo', label: 'Demo Walkthrough', icon: PlayCircle },
  { key: 'architecture', label: 'Architecture Map', icon: Network },
  { key: 'sources', label: 'Source Registry', icon: Database },
  { key: 'workflow', label: 'Crawler Workflow', icon: GitBranch },
  { key: 'lifecycle', label: 'Data Lifecycle Story', icon: Route },
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

const chartColors = ['#2563eb', '#0f766e', '#f59e0b', '#dc2626', '#7c3aed', '#0891b2'];
const graphNodeTypes = { enhanced: EnhancedFlowNode };

export function App() {
  const [activePage, setActivePage] = useState<PageKey>('overview');
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [dashboard, setDashboard] = useState<DashboardAnalytics | null>(null);
  const [timeSeries, setTimeSeries] = useState<TimeSeriesAnalytics | null>(null);
  const [keywordNetwork, setKeywordNetwork] = useState<KeywordNetworkAnalytics | null>(null);
  const [keywordHeatmap, setKeywordHeatmap] = useState<KeywordHeatmapAnalytics | null>(null);
  const [sourceHealth, setSourceHealth] = useState<SourceHealthAnalytics | null>(null);
  const [lineage, setLineage] = useState<LineageAnalytics | null>(null);
  const [crawlFlow, setCrawlFlow] = useState<CrawlFlowAnalytics | null>(null);
  const [dataQualityTable, setDataQualityTable] = useState<DataQualityTableAnalytics | null>(null);
  const [demoStory, setDemoStory] = useState<DemoStoryAnalytics | null>(null);
  const [trends, setTrends] = useState<TrendAnalytics | null>(null);
  const [keywords, setKeywords] = useState<KeywordAnalytics | null>(null);
  const [engagement, setEngagement] = useState<EngagementAnalytics | null>(null);
  const [platforms, setPlatforms] = useState<PlatformAnalytics | null>(null);
  const [quality, setQuality] = useState<DataQualityAnalytics | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowSummary | null>(null);
  const [sources, setSources] = useState<SourceResponse[]>([]);
  const [sourceCatalog, setSourceCatalog] = useState<SourceCatalogEntryStatus[]>([]);
  const [posts, setPosts] = useState<PostResponse[]>([]);
  const [postsTotal, setPostsTotal] = useState(0);
  const [postFacets, setPostFacets] = useState<PostsSearchResponse['facets']>({});
  const [jobs, setJobs] = useState<CrawlJobResponse[]>([]);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [filters, setFilters] = useState<PostFilters>({ limit: 50 });
  const [coreLoading, setCoreLoading] = useState(true);
  const [loadingPosts, setLoadingPosts] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  const [demoRunning, setDemoRunning] = useState(false);
  const [endpointStatus, setEndpointStatus] = useState<Record<string, string>>({});
  const [insight, setInsight] = useState<DrilldownResponse | null>(null);
  const [insightLoading, setInsightLoading] = useState(false);
  const [status, setStatus] = useState('Connecting to backend...');

  const loadCore = useCallback(async () => {
    setCoreLoading(true);
    const requests = [
      ['summary', api.summary()],
      ['sources', api.sources()],
      ['sourceCatalog', api.sourceCatalog()],
      ['jobs', api.jobs()],
      ['reports', api.reports()],
      ['overview', api.analytics.overview()],
      ['dashboard', api.analytics.dashboard()],
      ['timeSeries', api.analytics.timeSeries()],
      ['keywordNetwork', api.analytics.keywordNetwork()],
      ['keywordHeatmap', api.analytics.keywordHeatmap()],
      ['sourceHealth', api.analytics.sourceHealth()],
      ['lineage', api.analytics.lineage()],
      ['crawlFlow', api.analytics.crawlFlow()],
      ['dataQualityTable', api.analytics.dataQualityTable()],
      ['demoStory', api.analytics.demoStory()],
      ['trends', api.analytics.trends()],
      ['keywords', api.analytics.keywords()],
      ['engagement', api.analytics.engagement()],
      ['platforms', api.analytics.platforms()],
      ['quality', api.analytics.dataQuality()],
      ['workflow', api.analytics.workflow()],
    ] as const;
    const results = await Promise.allSettled(requests.map(([, request]) => request));
    const nextEndpointStatus: Record<string, string> = {};
    const value = <T,>(index: number): T | null => {
      const result = results[index];
      const name = requests[index][0];
      if (result.status === 'fulfilled') {
        nextEndpointStatus[name] = 'ready';
        return result.value as T;
      }
      nextEndpointStatus[name] = result.reason instanceof Error ? result.reason.message : 'failed';
      return null;
    };
    try {
      const nextSummary = value<DashboardSummary>(0);
      const nextSources = value<SourceResponse[]>(1);
      const nextSourceCatalog = value<SourceCatalogEntryStatus[]>(2);
      const nextJobs = value<CrawlJobResponse[]>(3);
      const nextReports = value<ReportSummary[]>(4);
      const nextOverview = value<AnalyticsOverview>(5);
      const nextDashboard = value<DashboardAnalytics>(6);
      const nextTimeSeries = value<TimeSeriesAnalytics>(7);
      const nextKeywordNetwork = value<KeywordNetworkAnalytics>(8);
      const nextKeywordHeatmap = value<KeywordHeatmapAnalytics>(9);
      const nextSourceHealth = value<SourceHealthAnalytics>(10);
      const nextLineage = value<LineageAnalytics>(11);
      const nextCrawlFlow = value<CrawlFlowAnalytics>(12);
      const nextDataQualityTable = value<DataQualityTableAnalytics>(13);
      const nextDemoStory = value<DemoStoryAnalytics>(14);
      const nextTrends = value<TrendAnalytics>(15);
      const nextKeywords = value<KeywordAnalytics>(16);
      const nextEngagement = value<EngagementAnalytics>(17);
      const nextPlatforms = value<PlatformAnalytics>(18);
      const nextQuality = value<DataQualityAnalytics>(19);
      const nextWorkflow = value<WorkflowSummary>(20);
      setSummary(nextSummary);
      setSources(nextSources ?? []);
      setSourceCatalog(nextSourceCatalog ?? []);
      setJobs(nextJobs ?? []);
      setReports(nextReports ?? []);
      setOverview(nextOverview);
      setDashboard(nextDashboard);
      setTimeSeries(nextTimeSeries);
      setKeywordNetwork(nextKeywordNetwork);
      setKeywordHeatmap(nextKeywordHeatmap);
      setSourceHealth(nextSourceHealth);
      setLineage(nextLineage);
      setCrawlFlow(nextCrawlFlow);
      setDataQualityTable(nextDataQualityTable);
      setDemoStory(nextDemoStory);
      setTrends(nextTrends);
      setKeywords(nextKeywords);
      setEngagement(nextEngagement);
      setPlatforms(nextPlatforms);
      setQuality(nextQuality);
      setWorkflow(nextWorkflow);
      setEndpointStatus(nextEndpointStatus);
      setStatus(nextSummary?.health.database_ready ? 'API ready' : 'Partial data loaded');
    } catch (error) {
      setStatus((error as Error).message);
    } finally {
      setCoreLoading(false);
    }
  }, []);

  const loadPosts = useCallback(async (nextFilters: PostFilters) => {
    setLoadingPosts(true);
    try {
      const result = await api.postsSearch(nextFilters);
      setPosts(result.rows);
      setPostsTotal(result.total);
      setPostFacets(result.facets);
    } catch (error) {
      setStatus((error as Error).message);
    } finally {
      setLoadingPosts(false);
    }
  }, []);

  async function openDrilldown(kind: string, id: string | number, fallback?: Partial<DrilldownResponse>) {
    setInsight({
      kind,
      id: String(id),
      title: fallback?.title ?? `${kind}:${id}`,
      subtitle: fallback?.subtitle ?? 'Loading detail...',
      summary: fallback?.summary ?? {},
      metadata: fallback?.metadata ?? {},
      related_posts: fallback?.related_posts ?? [],
      related_jobs: fallback?.related_jobs ?? [],
      quality_flags: fallback?.quality_flags ?? [],
      raw_payload: fallback?.raw_payload ?? {},
    });
    setInsightLoading(true);
    try {
      setInsight(await api.analytics.drilldown({ kind, id }));
    } catch (error) {
      setStatus((error as Error).message);
    } finally {
      setInsightLoading(false);
    }
  }

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

  async function runDemoWorkflow() {
    setDemoRunning(true);
    setStatus('Generating demo workflow dataset...');
    try {
      await refreshAfterRun(api.demo.runWorkflow({ rows: 2000, reset_demo: true }));
      setStatus('Demo workflow ready');
      setDemoMode(true);
      setActivePage('demo');
    } catch (error) {
      setStatus((error as Error).message);
    } finally {
      setDemoRunning(false);
    }
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
            <button
              className={demoMode ? 'demo-toggle active' : 'demo-toggle'}
              type="button"
              onClick={() => setDemoMode((enabled) => !enabled)}
            >
              <Sparkles size={16} />
              Demo Mode
            </button>
            <button
              className="primary-action"
              type="button"
              onClick={() => void runDemoWorkflow()}
              disabled={demoRunning}
            >
              <PlayCircle size={16} />
              {demoRunning ? 'Running...' : 'Run demo workflow'}
            </button>
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

        {demoMode && <InterviewDemoGuide activePage={activePage} story={demoStory} />}
        {coreLoading && <div className="loading-strip">Loading analytics endpoints...</div>}
        <EndpointStatusMatrix statuses={endpointStatus} />

        {renderPage(activePage)}
      </section>

      {insight && (
        <InsightDrawer
          insight={insight}
          loading={insightLoading}
          onClose={() => setInsight(null)}
          onDrilldown={(kind, id) => void openDrilldown(kind, id)}
        />
      )}
    </main>
  );

  function renderPage(page: PageKey) {
    switch (page) {
      case 'overview':
        return (
          <>
            <SummaryCards
              summary={summary}
              onSelectMetric={(key, label, value) => void openDrilldown('kpi', key, {
                title: label,
                summary: { value },
              })}
            />
            <OverviewDashboard
              dashboard={dashboard}
              jobs={jobs}
              onDrilldown={(kind, id, fallback) => void openDrilldown(kind, id, fallback)}
            />
          </>
        );
      case 'demo':
        return <DemoWalkthroughPage story={demoStory} onRunDemo={() => void runDemoWorkflow()} running={demoRunning} />;
      case 'architecture':
        return (
          <ArchitectureMapPage
            graph={demoStory?.architecture ?? null}
            story={demoStory}
            onDrilldown={(kind, id, fallback) => void openDrilldown(kind, id, fallback)}
          />
        );
      case 'sources':
        return (
          <SourceRegistry
            sources={sources}
            catalog={sourceCatalog}
            summary={summary}
            onDrilldown={(kind, id, fallback) => void openDrilldown(kind, id, fallback)}
          />
        );
      case 'workflow':
        return (
          <WorkflowPage
            workflow={workflow}
            crawlFlow={crawlFlow}
            onDrilldown={(kind, id, fallback) => void openDrilldown(kind, id, fallback)}
          />
        );
      case 'lifecycle':
        return (
          <LifecycleStoryPage
            graph={demoStory?.lifecycle ?? null}
            story={demoStory}
            onDrilldown={(kind, id, fallback) => void openDrilldown(kind, id, fallback)}
          />
        );
      case 'runs':
        return <JobsTimeline jobs={jobs} />;
      case 'explorer':
        return (
          <PostsExplorer
            posts={posts}
            total={postsTotal}
            facets={postFacets}
            filters={filters}
            loading={loadingPosts}
            onFiltersChange={(nextFilters) => setFilters({ ...nextFilters, limit: 50, offset: 0 })}
            onPageChange={(offset) => setFilters((current) => ({ ...current, offset }))}
            onSelectPost={(post) => void openDrilldown('post', post.id, {
              title: post.title,
              subtitle: `${post.platform} / ${post.board_or_forum ?? '-'}`,
              metadata: post as unknown as Record<string, unknown>,
            })}
          />
        );
      case 'trends':
        return <TrendPage trends={trends} timeSeries={timeSeries} />;
      case 'keywords':
        return (
          <KeywordPage
            keywords={keywords}
            network={keywordNetwork}
            heatmap={keywordHeatmap}
            onDrilldown={(kind, id, fallback) => void openDrilldown(kind, id, fallback)}
          />
        );
      case 'engagement':
        return <EngagementPage engagement={engagement} />;
      case 'platforms':
        return (
          <PlatformPage
            platforms={platforms}
            sourceHealth={sourceHealth}
            onDrilldown={(kind, id, fallback) => void openDrilldown(kind, id, fallback)}
          />
        );
      case 'quality':
        return (
          <QualityPage
            quality={quality}
            lineage={lineage}
            table={dataQualityTable}
            onDrilldown={(kind, id, fallback) => void openDrilldown(kind, id, fallback)}
          />
        );
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

function EndpointStatusMatrix({ statuses }: { statuses: Record<string, string> }) {
  const entries = Object.entries(statuses);
  if (!entries.length) {
    return null;
  }
  const failed = entries.filter(([, value]) => value !== 'ready');
  return (
    <div className="endpoint-matrix" aria-label="Endpoint loading status">
      <span>{entries.length - failed.length}/{entries.length} endpoints ready</span>
      {failed.slice(0, 4).map(([name, message]) => (
        <button className="endpoint-error" key={name} type="button" title={message}>
          {name}
        </button>
      ))}
    </div>
  );
}

function EnhancedFlowNode({ data, selected }: NodeProps) {
  const payload = data as Record<string, unknown>;
  const status = String(payload.status ?? payload.type ?? 'ready');
  return (
    <button className={selected ? 'enhanced-node selected' : 'enhanced-node'} type="button">
      <Handle type="target" position={Position.Left} />
      <div className={`node-orbit node-status-${status.replaceAll('_', '-')}`} />
      <div className="node-body">
        <strong>{String(payload.label ?? 'Node')}</strong>
        <span>{String(payload.purpose ?? payload.subtitle ?? payload.type ?? 'interactive graph node')}</span>
      </div>
      <b>{String(payload.count ?? payload.value ?? '')}</b>
      <Handle type="source" position={Position.Right} />
    </button>
  );
}

function InsightDrawer({
  insight,
  loading,
  onClose,
  onDrilldown,
}: {
  insight: DrilldownResponse;
  loading: boolean;
  onClose: () => void;
  onDrilldown: (kind: string, id: string | number) => void;
}) {
  const relatedPostColumns = columnsForRows(insight.related_posts);
  const relatedJobColumns = columnsForRows(insight.related_jobs);
  return (
    <aside className="drawer insight-drawer" aria-label="Insight detail">
      <div className="drawer-header">
        <div>
          <p className="eyebrow">{insight.kind} / {insight.id}</p>
          <h2>{insight.title}</h2>
          <span>{insight.subtitle}</span>
        </div>
        <button className="icon-button" type="button" onClick={onClose} aria-label="Close insight detail">
          <X size={17} />
        </button>
      </div>
      {loading && <div className="loading-strip">Loading drilldown...</div>}
      <div className="drawer-body">
        <InsightSection title="Summary" payload={insight.summary} />
        <InsightSection title="Metadata" payload={insight.metadata} />
        {insight.quality_flags.length > 0 && (
          <div className="detail-section">
            <strong>Quality Flags</strong>
            <TagList items={insight.quality_flags} tone="danger" />
          </div>
        )}
        <div className="detail-section">
          <strong>Related Posts</strong>
          <DataTable
            columns={relatedPostColumns}
            data={insight.related_posts}
            onRowSelect={(row) => row.id && onDrilldown('post', String(row.id))}
          />
        </div>
        <div className="detail-section">
          <strong>Related Crawl Jobs</strong>
          <DataTable
            columns={relatedJobColumns}
            data={insight.related_jobs}
            onRowSelect={(row) => row.id && onDrilldown('job', String(row.id))}
          />
        </div>
        <div className="detail-section">
          <strong>Raw Payload</strong>
          <pre className="json-panel">{JSON.stringify(insight.raw_payload, null, 2)}</pre>
        </div>
      </div>
    </aside>
  );
}

function InsightSection({ title, payload }: { title: string; payload: Record<string, unknown> }) {
  return (
    <div className="detail-section">
      <strong>{title}</strong>
      <div className="metadata-list">
        {Object.entries(payload).length ? Object.entries(payload).map(([key, value]) => (
          <div className="metadata-row" key={key}>
            <strong>{key}</strong>
            <span>{formatValue(value)}</span>
          </div>
        )) : <div className="empty-state">No metadata.</div>}
      </div>
    </div>
  );
}

function InterviewDemoGuide({
  activePage,
  story,
}: {
  activePage: PageKey;
  story: DemoStoryAnalytics | null;
}) {
  const pageMessage: Partial<Record<PageKey, string>> = {
    overview: 'Start here: KPI cards prove the crawler stores enough normalized data to analyze trends.',
    demo: 'Walk an interviewer through the full public-data workflow from source selection to Excel export.',
    architecture: 'Use this map to explain how connectors, crawler core, SQLite, API, UI, and Excel reports fit together.',
    workflow: 'Click each pipeline node to show governance, inputs, outputs, failure modes, and compliance strategy.',
    lifecycle: 'Use this lineage story to trace one article from raw response to analytics and Excel output.',
    quality: 'Show that blocked requests and data quality problems are treated as measurable pipeline facts.',
    reports: 'Close the demo by showing how analytics become reproducible Excel deliverables.',
  };
  return (
    <div className="demo-guide">
      <div>
        <p className="eyebrow">Interview demo mode</p>
        <strong>{pageMessage[activePage] ?? 'Use this page to discuss the data engineering capability behind the UI.'}</strong>
      </div>
      <div className="demo-guide-metrics">
        <span>{story?.kpis.total_posts ?? 0} posts</span>
        <span>{story?.kpis.total_crawl_runs ?? 0} crawl runs</span>
        <span>{story?.demo_live_ratio.demo ?? 0} demo rows</span>
      </div>
    </div>
  );
}

function DemoWalkthroughPage({
  story,
  onRunDemo,
  running,
}: {
  story: DemoStoryAnalytics | null;
  onRunDemo: () => void;
  running: boolean;
}) {
  const [selectedStep, setSelectedStep] = useState<DemoStoryStep | null>(null);
  const activeStep = selectedStep ?? story?.walkthrough_steps[0] ?? null;
  return (
    <section className="story-layout">
      <div className="panel wide-panel story-hero">
        <div>
          <p className="eyebrow">guided portfolio demo</p>
          <h2>{story?.title ?? 'Taiwan Public Web Intelligence Workbench'}</h2>
          <p>{story?.subtitle ?? 'Crawler governance, normalization, analytics, and Excel reporting in one workflow.'}</p>
        </div>
        <button className="primary-action large-action" type="button" onClick={onRunDemo} disabled={running}>
          <PlayCircle size={18} />
          {running ? 'Generating dataset...' : 'Run demo workflow'}
        </button>
      </div>

      <div className="walkthrough-track">
        {(story?.walkthrough_steps ?? []).map((step) => (
          <button
            key={step.key}
            className={activeStep?.key === step.key ? 'story-step active' : 'story-step'}
            type="button"
            onClick={() => setSelectedStep(step)}
          >
            <span className="step-index">{step.index}</span>
            <strong>{step.label}</strong>
            <small>{step.purpose}</small>
            <StatusBadge value={step.status} />
          </button>
        ))}
      </div>

      <StoryStepDetail step={activeStep} />

      <div className="panel wide-panel">
        <div className="panel-header">
          <h2>Engineering Capabilities Shown</h2>
          <span className="pill">interview talking points</span>
        </div>
        <div className="highlight-grid">
          {(story?.interview_highlights ?? []).map((highlight) => (
            <div className="highlight-card" key={highlight}>
              <Sparkles size={17} />
              <span>{highlight}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function StoryStepDetail({ step }: { step: DemoStoryStep | null }) {
  if (!step) {
    return <div className="panel"><div className="empty-state">Run or load demo story data.</div></div>;
  }
  return (
    <aside className="panel story-detail-panel">
      <div className="panel-header">
        <h2>{step.label}</h2>
        <StatusBadge value={step.status} />
      </div>
      <p className="detail-purpose">{step.purpose}</p>
      <div className="detail-section">
        <strong>Inputs</strong>
        <TagList items={step.inputs} />
      </div>
      <div className="detail-section">
        <strong>Outputs</strong>
        <TagList items={step.outputs} />
      </div>
      <div className="detail-section">
        <strong>Tables / Artifacts</strong>
        <TagList items={[...step.tables, step.artifact ?? 'runtime diagnostics']} />
      </div>
      <div className="detail-section">
        <strong>Possible Failure Modes</strong>
        <TagList items={step.failure_modes} tone="danger" />
      </div>
      <div className="compliance-callout">
        <ShieldCheck size={18} />
        <span>{step.compliance}</span>
      </div>
      <div className="engineering-note">{step.engineering_highlight}</div>
    </aside>
  );
}

function ArchitectureMapPage({
  graph,
  story,
  onDrilldown,
}: {
  graph: StoryGraph | null;
  story: DemoStoryAnalytics | null;
  onDrilldown: (kind: string, id: string, fallback?: Partial<DrilldownResponse>) => void;
}) {
  return (
    <section className="page-grid analytics-grid">
      <div className="wide-panel">
        <StoryGraphPanel graph={graph} title="System Architecture Map" onDrilldown={onDrilldown} />
      </div>
      <aside className="panel wide-panel">
        <div className="panel-header"><h2>Architecture Narrative</h2></div>
        <div className="metadata-list">
          <div className="metadata-row"><strong>Sources</strong><span>Public forums, RSS feeds, sitemap targets, and API-first connectors.</span></div>
          <div className="metadata-row"><strong>Crawler Core</strong><span>Rate limit, robots guard, request budget, retry, policy errors, and provenance.</span></div>
          <div className="metadata-row"><strong>Storage</strong><span>SQLite tables preserve source, job, normalized post, metrics, and export lineage.</span></div>
          <div className="metadata-row"><strong>Presentation</strong><span>FastAPI serves analytics payloads into React charts and Excel exports.</span></div>
        </div>
        <div className="demo-guide-metrics vertical">
          <span>{story?.kpis.total_sources ?? 0} sources</span>
          <span>{story?.kpis.total_posts ?? 0} normalized posts</span>
          <span>{story?.kpis.successful_crawl_runs ?? 0} successful runs</span>
        </div>
      </aside>
    </section>
  );
}

function LifecycleStoryPage({
  graph,
  story,
  onDrilldown,
}: {
  graph: StoryGraph | null;
  story: DemoStoryAnalytics | null;
  onDrilldown: (kind: string, id: string, fallback?: Partial<DrilldownResponse>) => void;
}) {
  return (
    <section className="page-grid analytics-grid">
      <div className="wide-panel">
        <StoryGraphPanel graph={graph} title="Raw Data to Excel Lineage" onDrilldown={onDrilldown} />
      </div>
      <div className="panel">
        <div className="panel-header"><h2>Lifecycle Explanation</h2></div>
        <div className="metadata-list">
          <div className="metadata-row"><strong>Raw response</strong><span>Public JSON, RSS XML, or HTML fetched with provenance.</span></div>
          <div className="metadata-row"><strong>Parsed item</strong><span>Connector extracts title, content, date, board, URL, and metrics.</span></div>
          <div className="metadata-row"><strong>Normalized post</strong><span>Cross-platform schema enables one analytics pipeline.</span></div>
          <div className="metadata-row"><strong>Analysis output</strong><span>Keyword, quality, engagement, trend, and Excel report artifacts.</span></div>
        </div>
      </div>
      <div className="panel">
        <div className="panel-header"><h2>Demo Data Mix</h2></div>
        <div className="ratio-meter">
          <div style={{ width: `${story?.demo_live_ratio.total ? (story.demo_live_ratio.demo / story.demo_live_ratio.total) * 100 : 0}%` }} />
        </div>
        <div className="metadata-list">
          <div className="metadata-row"><strong>Demo rows</strong><span>{story?.demo_live_ratio.demo ?? 0}</span></div>
          <div className="metadata-row"><strong>Live rows</strong><span>{story?.demo_live_ratio.live ?? 0}</span></div>
        </div>
      </div>
    </section>
  );
}

function StoryGraphPanel({
  graph,
  title,
  onDrilldown,
}: {
  graph: StoryGraph | null;
  title: string;
  onDrilldown?: (kind: string, id: string, fallback?: Partial<DrilldownResponse>) => void;
}) {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const nodes = (graph?.nodes ?? []).map((node) => ({
    id: node.id,
    type: 'enhanced',
    position: node.position ?? { x: 0, y: 0 },
    data: { label: node.label ?? node.id, ...node },
    className: `flow-node story-node-${node.type ?? 'default'}`,
  })) as Node[];
  const edges = (graph?.edges ?? []).map((edge, index) => ({ id: edge.id ?? `${edge.source}-${edge.target}-${index}`, ...edge })) as Edge[];
  return (
    <div className="story-graph-grid">
      <div className="panel flow-panel story-flow-panel">
        <div className="panel-header">
          <h2>{title}</h2>
          <span className="pill">click nodes</span>
        </div>
        <ReactFlow
          nodeTypes={graphNodeTypes}
          nodes={nodes}
          edges={edges}
          fitView
          onNodeClick={(_, node) => {
            setSelectedNode(node as unknown as GraphNode);
            onDrilldown?.('workflow_node', node.id, {
              title: String(node.data?.label ?? node.id),
              subtitle: String(node.data?.type ?? 'Graph node'),
              metadata: node.data as Record<string, unknown>,
            });
          }}
        >
          <MiniMap />
          <Controls />
          <Background />
        </ReactFlow>
      </div>
      <NodeDetailPanel node={selectedNode ?? (graph?.nodes[0] ?? null)} title="Selected Node" />
    </div>
  );
}

function OverviewDashboard({
  dashboard,
  jobs,
  onDrilldown,
}: {
  dashboard: DashboardAnalytics | null;
  jobs: CrawlJobResponse[];
  onDrilldown: (kind: string, id: string | number, fallback?: Partial<DrilldownResponse>) => void;
}) {
  const areaData = pivotSeries(dashboard?.daily_platform_volume ?? [], 'platform');
  const platforms = uniqueGroups(dashboard?.daily_platform_volume ?? [], 'platform');
  const ratio = dashboard?.demo_live_ratio ?? { demo: 0, live: 0, total: 0 };
  const topPostColumns: ColumnDef<Record<string, unknown>>[] = [
    { accessorKey: 'platform', header: 'Platform' },
    { accessorKey: 'title', header: 'Title' },
    { accessorKey: 'engagement_score', header: 'Score' },
    { accessorKey: 'comment_count', header: 'Comments' },
  ];

  return (
    <section className="page-grid analytics-grid">
      <button className="panel wide-panel interactive-panel" type="button" onClick={() => onDrilldown('kpi', 'daily_platform_volume', { title: 'Daily Platform Volume', raw_payload: { rows: dashboard?.daily_platform_volume ?? [] } })}>
        <div className="panel-header">
          <h2>Daily Platform Volume</h2>
          <span className="pill">stacked area</span>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={areaData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" minTickGap={18} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            {platforms.map((platform, index) => (
              <Area
                key={platform}
                type="monotone"
                dataKey={platform}
                stackId="posts"
                stroke={chartColors[index % chartColors.length]}
                fill={chartColors[index % chartColors.length]}
                fillOpacity={0.72}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </button>

      <button className="panel interactive-panel" type="button" onClick={() => onDrilldown('kpi', 'platform_distribution', { title: 'Platform Distribution', raw_payload: { rows: dashboard?.platform_distribution ?? [] } })}>
        <div className="panel-header">
          <h2>Platform Distribution</h2>
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie
              data={dashboard?.platform_distribution ?? []}
              dataKey="count"
              nameKey="platform"
              innerRadius={58}
              outerRadius={92}
              paddingAngle={2}
            >
              {(dashboard?.platform_distribution ?? []).map((entry, index) => (
                <Cell key={entry.platform} fill={chartColors[index % chartColors.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </button>

      <button className="panel interactive-panel" type="button" onClick={() => onDrilldown('kpi', 'demo_live_ratio', { title: 'Demo / Live Ratio', summary: ratio })}>
        <div className="panel-header">
          <h2>Demo / Live Ratio</h2>
        </div>
        <div className="ratio-meter">
          <div style={{ width: `${ratio.total ? (ratio.demo / ratio.total) * 100 : 0}%` }} />
        </div>
        <div className="metadata-list">
          <div className="metadata-row"><strong>Demo records</strong><span>{ratio.demo}</span></div>
          <div className="metadata-row"><strong>Live records</strong><span>{ratio.live}</span></div>
          <div className="metadata-row"><strong>Total records</strong><span>{ratio.total}</span></div>
        </div>
      </button>

      <button className="panel interactive-panel" type="button" onClick={() => onDrilldown('kpi', 'crawl_status_counts', { title: 'Crawl Outcome', raw_payload: { rows: dashboard?.crawl_status_counts ?? [] } })}>
        <div className="panel-header">
          <h2>Crawl Outcome</h2>
        </div>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={dashboard?.crawl_status_counts ?? []} layout="vertical">
            <XAxis type="number" allowDecimals={false} />
            <YAxis type="category" dataKey="status" width={120} />
            <Tooltip />
            <Bar dataKey="count" fill="var(--color-primary)" radius={[0, 6, 6, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </button>

      <button className="panel interactive-panel" type="button" onClick={() => onDrilldown('keyword', dashboard?.top_keywords?.[0]?.keyword ?? 'AI', { title: 'Top Keywords', raw_payload: { rows: dashboard?.top_keywords ?? [] } })}>
        <div className="panel-header">
          <h2>Top Keywords</h2>
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={dashboard?.top_keywords ?? []} layout="vertical">
            <XAxis type="number" allowDecimals={false} />
            <YAxis type="category" dataKey="keyword" width={86} />
            <Tooltip />
            <Bar dataKey="count" fill="var(--color-secondary)" radius={[0, 6, 6, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </button>

      <div className="panel wide-panel">
        <div className="panel-header">
          <h2>Latest Hot Posts</h2>
        </div>
        <DataTable
          columns={topPostColumns}
          data={(dashboard?.top_posts ?? []) as Array<Record<string, unknown>>}
          onRowSelect={(row) => row.id && onDrilldown('post', String(row.id), {
            title: String(row.title ?? 'Post'),
            metadata: row,
          })}
        />
      </div>

      <div className="panel wide-panel">
        <div className="panel-header">
          <h2>Recent Crawl Timeline</h2>
        </div>
        <div className="job-list">
          {jobs.slice(0, 8).map((job) => (
            <button className="job-row interactive-row" type="button" key={job.id} onClick={() => onDrilldown('job', job.id, { title: `${job.source} / ${job.job_type}`, metadata: job as unknown as Record<string, unknown> })}>
              <div>
                <div className="job-title">{job.source} / {job.job_type}</div>
                <div className="job-meta">{job.request_count} requests / {job.item_count} items</div>
              </div>
              <StatusBadge value={job.status} />
            </button>
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
  onDrilldown,
}: {
  sources: SourceResponse[];
  catalog: SourceCatalogEntryStatus[];
  summary: DashboardSummary | null;
  onDrilldown: (kind: string, id: string, fallback?: Partial<DrilldownResponse>) => void;
}) {
  return (
    <section className="page-grid">
      <SourceOverview
        sources={sources}
        summary={summary}
        onSelectSource={(source) => onDrilldown('source', source.name, {
          title: source.name,
          subtitle: source.source_type,
          metadata: source as unknown as Record<string, unknown>,
        })}
      />
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
            <button className="catalog-card interactive-panel" type="button" key={source.name} onClick={() => onDrilldown('source', source.name, {
              title: source.display_name,
              subtitle: `${source.platform} / ${source.strategy}`,
              metadata: source as unknown as Record<string, unknown>,
            })}>
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
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

function WorkflowPage({
  workflow,
  crawlFlow,
  onDrilldown,
}: {
  workflow: WorkflowSummary | null;
  crawlFlow: CrawlFlowAnalytics | null;
  onDrilldown: (kind: string, id: string, fallback?: Partial<DrilldownResponse>) => void;
}) {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const nodes = (crawlFlow?.nodes ?? []).map((node) => ({
    ...node,
    type: 'enhanced',
    className: `flow-node flow-node-${String(node.data?.status ?? 'unknown').replaceAll('_', '-')}`,
  })) as Node[];
  const edges = (crawlFlow?.edges ?? []) as Edge[];

  return (
    <section className="flow-layout">
      <div className="panel flow-panel">
        <div className="panel-header">
          <h2>Crawler Pipeline Graph</h2>
          {workflow?.latest_error && <span className="pill">latest stop condition captured</span>}
        </div>
        <ReactFlow
          nodeTypes={graphNodeTypes}
          nodes={nodes}
          edges={edges}
          fitView
          onNodeClick={(_, node) => {
            setSelectedNode(node as unknown as GraphNode);
            onDrilldown('workflow_node', node.id, {
              title: String(node.data?.label ?? node.id),
              subtitle: String(node.data?.purpose ?? 'Workflow node'),
              metadata: node.data as Record<string, unknown>,
            });
          }}
        >
          <MiniMap />
          <Controls />
          <Background />
        </ReactFlow>
      </div>
      <NodeDetailPanel node={selectedNode ?? (crawlFlow?.nodes?.[0] ?? null)} title="Pipeline Node Detail" />
    </section>
  );
}

function TrendPage({
  trends,
  timeSeries,
}: {
  trends: TrendAnalytics | null;
  timeSeries: TimeSeriesAnalytics | null;
}) {
  const sourceData = pivotSeries(timeSeries?.daily_by_source ?? [], 'source');
  const sources = uniqueGroups(timeSeries?.daily_by_source ?? [], 'source').slice(0, 6);
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
            <Line type="monotone" dataKey="count" stroke="var(--color-primary)" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="panel wide-panel">
        <div className="panel-header"><h2>Source Trend</h2></div>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={sourceData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            {sources.map((source, index) => (
              <Area key={source} type="monotone" dataKey={source} stackId="source" stroke={chartColors[index % chartColors.length]} fill={chartColors[index % chartColors.length]} fillOpacity={0.55} />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <SimpleList title="Top Boards / Forums" rows={(trends?.top_boards ?? []).map((item) => [item.board_or_forum, item.count])} />
    </section>
  );
}

function KeywordPage({
  keywords,
  network,
  heatmap,
  onDrilldown,
}: {
  keywords: KeywordAnalytics | null;
  network: KeywordNetworkAnalytics | null;
  heatmap: KeywordHeatmapAnalytics | null;
  onDrilldown: (kind: string, id: string, fallback?: Partial<DrilldownResponse>) => void;
}) {
  const [selectedNode, setSelectedNode] = useState<Record<string, unknown> | null>(null);
  const heatmapMax = Math.max(...(heatmap?.cells ?? []).map((cell) => cell.count), 1);
  const phraseColumns: ColumnDef<Record<string, unknown>>[] = [
    { accessorKey: 'keyword', header: 'Keyword' },
    { accessorKey: 'count', header: 'Count' },
  ];

  return (
    <section className="page-grid analytics-grid">
      <div className="panel">
        <div className="panel-header"><h2>Keyword Frequency</h2></div>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={keywords?.keywords ?? []} layout="vertical">
            <XAxis type="number" allowDecimals={false} />
            <YAxis type="category" dataKey="keyword" width={90} />
            <Tooltip />
            <Bar dataKey="count" fill="var(--color-primary)" radius={[0, 6, 6, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="panel network-panel">
        <div className="panel-header"><h2>Keyword Co-occurrence Network</h2></div>
        <ForceGraph2D
          graphData={{ nodes: network?.nodes ?? [], links: network?.links ?? [] }}
          nodeLabel="label"
          nodeVal="value"
          linkWidth={(link) => Math.max(1, Number(link.value ?? 1) / 6)}
          nodeColor={() => 'var(--color-primary)'}
          onNodeClick={(node) => {
            const payload = node as Record<string, unknown>;
            setSelectedNode(payload);
            onDrilldown('keyword', String(payload.id ?? payload.label ?? 'AI'), {
              title: String(payload.label ?? payload.id ?? 'Keyword'),
              metadata: payload,
            });
          }}
          width={520}
          height={320}
        />
      </div>
      <div className="panel wide-panel">
        <div className="panel-header"><h2>Platform x Keyword Heatmap</h2></div>
        <div className="heatmap-grid" style={{ gridTemplateColumns: `140px repeat(${heatmap?.keywords.length ?? 1}, minmax(70px, 1fr))` }}>
          <span />
          {(heatmap?.keywords ?? []).map((keyword) => <strong key={keyword}>{keyword}</strong>)}
          {(heatmap?.platforms ?? []).flatMap((platform) => [
            <strong key={`${platform}-label`}>{platform}</strong>,
            ...(heatmap?.keywords ?? []).map((keyword) => {
              const count = heatmap?.cells.find((cell) => cell.platform === platform && cell.keyword === keyword)?.count ?? 0;
              return <span key={`${platform}-${keyword}`} style={{ opacity: 0.25 + (count / heatmapMax) * 0.75 }}>{count}</span>;
            }),
          ])}
        </div>
      </div>
      <div className="panel">
        <div className="panel-header"><h2>Top Phrase Table</h2></div>
        <DataTable
          columns={phraseColumns}
          data={(keywords?.keywords ?? []) as Array<Record<string, unknown>>}
          onRowSelect={(row) => onDrilldown('keyword', String(row.keyword ?? 'AI'), {
            title: String(row.keyword ?? 'Keyword'),
            metadata: row,
          })}
        />
      </div>
      <div className="panel">
        <div className="panel-header"><h2>Selected Keyword Node</h2></div>
        {selectedNode ? <pre className="json-panel">{JSON.stringify(selectedNode, null, 2)}</pre> : <div className="empty-state">Click a network node.</div>}
      </div>
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

function PlatformPage({
  platforms,
  sourceHealth,
  onDrilldown,
}: {
  platforms: PlatformAnalytics | null;
  sourceHealth: SourceHealthAnalytics | null;
  onDrilldown: (kind: string, id: string, fallback?: Partial<DrilldownResponse>) => void;
}) {
  const platformRows = platforms?.platforms ?? [];
  const radarData = platformRows.map((row) => ({
    platform: row.platform,
    volume: row.post_count,
    engagement: row.average_engagement_score,
    content: row.average_content_length,
    success: row.crawl_success_rate ?? 0,
  }));
  const sourceColumns: ColumnDef<Record<string, unknown>>[] = [
    { accessorKey: 'display_name', header: 'Source' },
    { accessorKey: 'platform', header: 'Platform' },
    { accessorKey: 'post_count', header: 'Posts' },
    { accessorKey: 'success_rate', header: 'Success %' },
    { accessorKey: 'failed_count', header: 'Failed' },
    { accessorKey: 'last_status', header: 'Last Status' },
  ];

  return (
    <section className="page-grid analytics-grid">
      <div className="panel">
        <div className="panel-header"><h2>Platform Volume</h2></div>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={platformRows}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="platform" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="post_count" fill="var(--color-primary)" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="panel">
        <div className="panel-header"><h2>Schema Normalization Radar</h2></div>
        <ResponsiveContainer width="100%" height={280}>
          <RadarChart data={radarData}>
            <PolarGrid />
            <PolarAngleAxis dataKey="platform" />
            <Radar name="Volume" dataKey="volume" stroke="var(--color-primary)" fill="var(--color-primary)" fillOpacity={0.28} />
            <Radar name="Engagement" dataKey="engagement" stroke="var(--color-secondary)" fill="var(--color-secondary)" fillOpacity={0.22} />
            <Tooltip />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <div className="panel">
        <div className="panel-header"><h2>Average Content Length</h2></div>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={platformRows}>
            <XAxis dataKey="platform" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="average_content_length" fill="var(--color-secondary)" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="panel">
        <div className="panel-header"><h2>Crawl Success Rate</h2></div>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={platformRows}>
            <XAxis dataKey="platform" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="crawl_success_rate" fill="var(--color-warning)" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="panel wide-panel">
        <div className="panel-header"><h2>Source Health Matrix</h2></div>
        <DataTable
          columns={sourceColumns}
          data={(sourceHealth?.rows ?? []) as Array<Record<string, unknown>>}
          onRowSelect={(row) => onDrilldown('source', String(row.source ?? row.display_name), {
            title: String(row.display_name ?? row.source),
            metadata: row,
          })}
        />
      </div>
    </section>
  );
}

function QualityPage({
  quality,
  lineage,
  table,
  onDrilldown,
}: {
  quality: DataQualityAnalytics | null;
  lineage: LineageAnalytics | null;
  table: DataQualityTableAnalytics | null;
  onDrilldown: (kind: string, id: string, fallback?: Partial<DrilldownResponse>) => void;
}) {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [activeTable, setActiveTable] = useState<keyof DataQualityTableAnalytics>('missing_content');
  const lineageNodes = (lineage?.nodes ?? []).map((node, index) => ({
    id: node.id,
    type: 'enhanced',
    position: { x: index * 190, y: index % 2 ? 140 : 20 },
    data: { label: `${node.label ?? node.id} (${node.count ?? 0})`, ...node },
    className: `flow-node lineage-node-${node.type ?? 'default'}`,
  })) as Node[];
  const lineageEdges = (lineage?.edges ?? []).map((edge, index) => ({ id: edge.id ?? `edge-${index}`, ...edge })) as Edge[];
  const rows = (table?.[activeTable] ?? []) as Array<Record<string, unknown>>;
  const columns = columnsForRows(rows);

  return (
    <section className="page-grid analytics-grid">
      <div className="panel wide-panel flow-panel lineage-panel">
        <div className="panel-header"><h2>Data Lineage Graph</h2></div>
        <ReactFlow
          nodeTypes={graphNodeTypes}
          nodes={lineageNodes}
          edges={lineageEdges}
          fitView
          onNodeClick={(_, node) => {
            setSelectedNode(node as unknown as GraphNode);
            onDrilldown('workflow_node', node.id, {
              title: String(node.data?.label ?? node.id),
              metadata: node.data as Record<string, unknown>,
            });
          }}
        >
          <MiniMap />
          <Controls />
          <Background />
        </ReactFlow>
      </div>
      <NodeDetailPanel node={selectedNode ?? (lineage?.nodes?.[0] ?? null)} title="Lineage Node Detail" />
      <SimpleList title="Data Quality Checks" rows={(quality?.checks ?? []).map((item) => [item.name, item.count])} />
      <SimpleList title="Policy Events" rows={(quality?.policy_events ?? []).map((item) => [item.category, item.count])} />
      <div className="panel wide-panel">
        <div className="panel-header"><h2>Quality Tables</h2></div>
        <div className="tab-row">
          {(['missing_content', 'duplicates', 'failed_crawls', 'policy_blocks'] as Array<keyof DataQualityTableAnalytics>).map((key) => (
            <button key={key} className={activeTable === key ? 'active' : ''} type="button" onClick={() => setActiveTable(key)}>{key}</button>
          ))}
        </div>
        <DataTable
          columns={columns}
          data={rows}
          onRowSelect={(row) => {
            if (row.id) {
              onDrilldown(activeTable === 'failed_crawls' || activeTable === 'policy_blocks' ? 'job' : 'post', String(row.id), {
                title: String(row.title ?? row.job_type ?? activeTable),
                metadata: row,
              });
            }
          }}
        />
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

function DataTable({
  columns,
  data,
  onRowSelect,
}: {
  columns: ColumnDef<Record<string, unknown>>[];
  data: Array<Record<string, unknown>>;
  onRowSelect?: (row: Record<string, unknown>) => void;
}) {
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });
  if (!data.length) {
    return <div className="empty-state">No table rows.</div>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th key={header.id}>
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              className={onRowSelect ? 'clickable-row' : undefined}
              key={row.id}
              onClick={() => onRowSelect?.(row.original)}
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id}>{String(cell.getValue() ?? '-')}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function NodeDetailPanel({ node, title }: { node: GraphNode | null; title: string }) {
  const payload = node?.data ?? node ?? {};
  return (
    <aside className="panel node-detail-panel">
      <div className="panel-header"><h2>{title}</h2></div>
      {node ? (
        <div className="metadata-list">
          {Object.entries(payload).map(([key, value]) => (
            <div className="metadata-row" key={key}>
              <strong>{key}</strong>
              <span>{formatValue(value)}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">Click a node.</div>
      )}
    </aside>
  );
}

function TagList({ items, tone = 'default' }: { items: string[]; tone?: 'default' | 'danger' }) {
  return (
    <div className={tone === 'danger' ? 'tag-list danger-tags' : 'tag-list'}>
      {items.map((item) => <span key={item}>{item}</span>)}
    </div>
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

function pivotSeries<T extends Record<string, string | number>>(
  rows: T[],
  groupKey: keyof T,
): Array<Record<string, string | number>> {
  const map = new Map<string, Record<string, string | number>>();
  rows.forEach((row) => {
    const date = String(row.date);
    const group = String(row[groupKey]);
    const next = map.get(date) ?? { date };
    next[group] = Number(next[group] ?? 0) + Number(row.count ?? 0);
    map.set(date, next);
  });
  return Array.from(map.values()).sort((left, right) => String(left.date).localeCompare(String(right.date)));
}

function uniqueGroups<T extends Record<string, string | number>>(rows: T[], groupKey: keyof T): string[] {
  return Array.from(new Set(rows.map((row) => String(row[groupKey]))));
}

function columnsForRows(rows: Array<Record<string, unknown>>): ColumnDef<Record<string, unknown>>[] {
  const keys = Object.keys(rows[0] ?? {}).slice(0, 6);
  return keys.map((key) => ({ accessorKey: key, header: key }));
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return '-';
  }
  if (Array.isArray(value)) {
    return value.map((item) => formatValue(item)).join(', ');
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}
