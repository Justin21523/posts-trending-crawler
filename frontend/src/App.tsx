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
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { select, zoom, zoomIdentity, type ZoomBehavior, type ZoomTransform } from 'd3';
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
  ComplianceSummary,
  EngagementAnalytics,
  ExcelReportRunResponse,
  GraphNode,
  KeywordHeatmapAnalytics,
  KeywordAnalytics,
  KeywordInsightsAnalytics,
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
  TopicAnalytics,
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

type Language = 'zh' | 'en';

const pages: Array<{ key: PageKey; labelKey: string; icon: typeof Activity }> = [
  { key: 'overview', labelKey: 'page.overview', icon: BarChart3 },
  { key: 'demo', labelKey: 'page.demo', icon: PlayCircle },
  { key: 'architecture', labelKey: 'page.architecture', icon: Network },
  { key: 'sources', labelKey: 'page.sources', icon: Database },
  { key: 'workflow', labelKey: 'page.workflow', icon: GitBranch },
  { key: 'lifecycle', labelKey: 'page.lifecycle', icon: Route },
  { key: 'runs', labelKey: 'page.runs', icon: Activity },
  { key: 'explorer', labelKey: 'page.explorer', icon: Search },
  { key: 'trends', labelKey: 'page.trends', icon: TrendingUp },
  { key: 'keywords', labelKey: 'page.keywords', icon: Sparkles },
  { key: 'engagement', labelKey: 'page.engagement', icon: ClipboardCheck },
  { key: 'platforms', labelKey: 'page.platforms', icon: Layers },
  { key: 'quality', labelKey: 'page.quality', icon: BookOpenCheck },
  { key: 'reports', labelKey: 'page.reports', icon: FileSpreadsheet },
  { key: 'compliance', labelKey: 'page.compliance', icon: ShieldCheck },
  { key: 'settings', labelKey: 'page.settings', icon: Settings },
];

const chartColors = ['#2563eb', '#0f766e', '#f59e0b', '#dc2626', '#7c3aed', '#0891b2'];
const graphNodeTypes = { enhanced: EnhancedFlowNode };

const pagePaths: Record<PageKey, string> = {
  overview: '/overview',
  demo: '/demo',
  architecture: '/architecture',
  sources: '/sources',
  workflow: '/workflow',
  lifecycle: '/lifecycle',
  runs: '/runs',
  explorer: '/explorer',
  trends: '/trends',
  keywords: '/keywords',
  engagement: '/engagement',
  platforms: '/platforms',
  quality: '/quality',
  reports: '/reports',
  compliance: '/compliance',
  settings: '/settings',
};

const pathPages = new Map(Object.entries(pagePaths).map(([key, path]) => [path, key as PageKey]));

const messages: Record<Language, Record<string, string>> = {
  zh: {
    'page.overview': '總覽儀表板',
    'page.demo': 'Demo 操作導覽',
    'page.architecture': '系統架構圖',
    'page.sources': '資料來源管理',
    'page.workflow': 'Crawler Workflow',
    'page.lifecycle': '資料生命週期',
    'page.runs': '爬取執行紀錄',
    'page.explorer': '資料瀏覽器',
    'page.trends': '趨勢分析',
    'page.keywords': 'Keyword & Topic Mining',
    'page.engagement': '互動熱度分析',
    'page.platforms': '平台比較',
    'page.quality': '資料品質與 Lineage',
    'page.reports': 'Excel Report Center',
    'page.compliance': 'Compliance & Diagnostics',
    'page.settings': '設定',
    'top.eyebrow': '公開資料 Pipeline 作品集',
    'button.demoMode': 'Demo Mode',
    'button.runDemo': '產生 Demo workflow',
    'button.running': '執行中...',
    'button.assistant': '開啟小幫手',
    'assistant.title': '作品集導覽小幫手',
    'assistant.start': '開始導覽',
    'assistant.next': '下一步',
    'assistant.prev': '上一步',
    'assistant.skip': '略過',
    'assistant.done': '完成',
    'reports.generate': '產生 Excel 報表',
    'reports.generating': '產生中...',
    'reports.generator': 'Excel 報表產生器',
    'reports.output': '輸出路徑',
    'reports.rows': '資料筆數',
    'reports.matches': '關鍵字命中',
    'reports.sheets': 'Excel 報表 Sheets',
    'compliance.summary': '合規治理總覽',
    'compliance.outcomes': '近期合規結果',
    'compliance.rules': '治理規則',
    'keyword.frequency': '關鍵字頻率',
    'keyword.network': 'Keyword 共現網路',
    'keyword.heatmap': '平台 x 關鍵字熱力圖',
    'network.legend': 'Keyword 分群圖例',
    'metadata.status': 'Metadata 狀態',
  },
  en: {
    'page.overview': 'Overview Dashboard',
    'page.demo': 'Demo Walkthrough',
    'page.architecture': 'Architecture Map',
    'page.sources': 'Source Registry',
    'page.workflow': 'Crawler Workflow',
    'page.lifecycle': 'Data Lifecycle Story',
    'page.runs': 'Crawl Runs',
    'page.explorer': 'Data Explorer',
    'page.trends': 'Trend Analytics',
    'page.keywords': 'Keyword & Topic Mining',
    'page.engagement': 'Engagement Analysis',
    'page.platforms': 'Platform Comparison',
    'page.quality': 'Data Quality & Lineage',
    'page.reports': 'Excel Report Center',
    'page.compliance': 'Compliance & Diagnostics',
    'page.settings': 'Settings',
    'top.eyebrow': 'Public data pipeline portfolio',
    'button.demoMode': 'Demo Mode',
    'button.runDemo': 'Run demo workflow',
    'button.running': 'Running...',
    'button.assistant': 'Open assistant',
    'assistant.title': 'Portfolio Demo Assistant',
    'assistant.start': 'Start tour',
    'assistant.next': 'Next',
    'assistant.prev': 'Back',
    'assistant.skip': 'Skip',
    'assistant.done': 'Done',
    'reports.generate': 'Generate Excel Report',
    'reports.generating': 'Generating...',
    'reports.generator': 'Excel Report Generator',
    'reports.output': 'Output',
    'reports.rows': 'Rows',
    'reports.matches': 'Keyword Matches',
    'reports.sheets': 'Excel Report Sheets',
    'compliance.summary': 'Crawler Governance Summary',
    'compliance.outcomes': 'Recent Compliance Outcomes',
    'compliance.rules': 'Governance Rules',
    'keyword.frequency': 'Keyword Frequency',
    'keyword.network': 'Keyword Co-occurrence Network',
    'keyword.heatmap': 'Platform x Keyword Heatmap',
    'network.legend': 'Keyword Group Legend',
    'metadata.status': 'Metadata Status',
  },
};

const tourSteps: Array<{
  page: PageKey;
  target: string;
  i18nKey: string;
  title: Record<Language, string>;
  body: Record<Language, string>;
  bullets: Record<Language, string[]>;
}> = [
  {
    page: 'overview',
    target: 'overview-kpis',
    i18nKey: 'overview',
    title: { zh: '先看總覽 KPI', en: 'Start with overview KPIs' },
    body: {
      zh: '這裡快速展示資料來源、文章量、crawl jobs 與 API 狀態，讓面試官先理解系統規模。',
      en: 'This shows source, post, crawl job, and API readiness at a glance.',
    },
    bullets: {
      zh: ['點擊任一卡片可開啟 metadata drilldown', 'Demo data 與 live data 會被清楚標示'],
      en: ['Click any card to open metadata drilldown', 'Demo and live data are clearly labeled'],
    },
  },
  {
    page: 'demo',
    target: 'demo-workflow',
    i18nKey: 'demo',
    title: { zh: '執行展示資料流程', en: 'Run the demo workflow' },
    body: {
      zh: '這一步用可重現的 demo dataset 展示完整 pipeline，不依賴外部網站當下是否可抓。',
      en: 'This uses a reproducible demo dataset to show the full pipeline.',
    },
    bullets: { zh: ['按 Run demo workflow', '資料會刷新到所有圖表'], en: ['Click Run demo workflow', 'Charts refresh after seeding'] },
  },
  {
    page: 'architecture',
    target: 'architecture-map',
    i18nKey: 'architecture',
    title: { zh: '解釋系統架構', en: 'Explain the architecture' },
    body: { zh: '用節點圖說明 Sources、Connectors、Crawler Core、SQLite、API、React 與 Excel Export。', en: 'Use the graph to explain sources, connectors, crawler core, SQLite, API, React, and Excel export.' },
    bullets: { zh: ['點節點看 metadata', '強調 connector-based 架構'], en: ['Click nodes for metadata', 'Highlight connector-based design'] },
  },
  {
    page: 'workflow',
    target: 'workflow-graph',
    i18nKey: 'workflow',
    title: { zh: '展示合規爬蟲流程', en: 'Show crawler governance flow' },
    body: { zh: '每個節點都有 inputs、outputs、failure modes 與 compliance policy。', en: 'Each node exposes inputs, outputs, failure modes, and compliance policy.' },
    bullets: { zh: ['Policy Check 不做 bypass', '403/429/CAPTCHA fail closed'], en: ['Policy Check does not bypass', '403/429/CAPTCHA fail closed'] },
  },
  {
    page: 'keywords',
    target: 'keyword-network',
    i18nKey: 'keyword',
    title: { zh: '查看 Keyword Network', en: 'Explore the Keyword Network' },
    body: { zh: '不同顏色代表不同主題分群，點擊節點可看相關文章與 metadata。', en: 'Colors represent topic groups; click nodes to inspect related posts and metadata.' },
    bullets: { zh: ['圓形節點大小代表出現次數', '線條代表共同出現'], en: ['Circle size reflects frequency', 'Links show co-occurrence'] },
  },
  {
    page: 'compliance',
    target: 'compliance-summary',
    i18nKey: 'compliance',
    title: { zh: '說明合規與診斷', en: 'Explain compliance diagnostics' },
    body: { zh: '這頁把 robots、policy blocks、429/403、source health 變成可分析資料。', en: 'This page turns robots, policy blocks, 429/403, and source health into analyzable data.' },
    bullets: { zh: ['不繞過平台限制', '所有 stop condition 都可追蹤'], en: ['No platform bypass', 'Every stop condition is traceable'] },
  },
  {
    page: 'reports',
    target: 'report-center',
    i18nKey: 'report',
    title: { zh: '產生 Excel 報表', en: 'Generate Excel report' },
    body: { zh: '最後展示資料工程成果可以輸出成可交付的 Excel analytics report。', en: 'Finally show that the pipeline produces a deliverable Excel analytics report.' },
    bullets: { zh: ['按 Generate Excel Report', '報表會出現在 reports list'], en: ['Click Generate Excel Report', 'The report appears in the reports list'] },
  },
];

export function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const { t, i18n } = useTranslation();
  const routePage = pathPages.get(location.pathname) ?? (location.pathname === '/' ? 'overview' : null);
  const isDetailRoute = location.pathname.startsWith('/detail/');
  const [activePage, setActivePage] = useState<PageKey>(routePage ?? 'overview');
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [dashboard, setDashboard] = useState<DashboardAnalytics | null>(null);
  const [timeSeries, setTimeSeries] = useState<TimeSeriesAnalytics | null>(null);
  const [keywordNetwork, setKeywordNetwork] = useState<KeywordNetworkAnalytics | null>(null);
  const [keywordInsights, setKeywordInsights] = useState<KeywordInsightsAnalytics | null>(null);
  const [keywordHeatmap, setKeywordHeatmap] = useState<KeywordHeatmapAnalytics | null>(null);
  const [topics, setTopics] = useState<TopicAnalytics | null>(null);
  const [sourceHealth, setSourceHealth] = useState<SourceHealthAnalytics | null>(null);
  const [lineage, setLineage] = useState<LineageAnalytics | null>(null);
  const [crawlFlow, setCrawlFlow] = useState<CrawlFlowAnalytics | null>(null);
  const [dataQualityTable, setDataQualityTable] = useState<DataQualityTableAnalytics | null>(null);
  const [demoStory, setDemoStory] = useState<DemoStoryAnalytics | null>(null);
  const [complianceSummary, setComplianceSummary] = useState<ComplianceSummary | null>(null);
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
  const [reportRunning, setReportRunning] = useState(false);
  const [lastReportRun, setLastReportRun] = useState<ExcelReportRunResponse | null>(null);
  const [endpointStatus, setEndpointStatus] = useState<Record<string, string>>({});
  const [insight, setInsight] = useState<DrilldownResponse | null>(null);
  const [insightLoading, setInsightLoading] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [tourStep, setTourStep] = useState(0);
  const [status, setStatus] = useState('Connecting to backend...');
  const language = i18n.language === 'en' ? 'en' : 'zh';

  function changeLanguage(next: Language) {
    localStorage.setItem('twCrawlerLang', next);
    void i18n.changeLanguage(next);
  }

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
      ['keywordInsights', api.analytics.keywordInsights()],
      ['keywordHeatmap', api.analytics.keywordHeatmap()],
      ['topics', api.analytics.topics()],
      ['sourceHealth', api.analytics.sourceHealth()],
      ['lineage', api.analytics.lineage()],
      ['crawlFlow', api.analytics.crawlFlow()],
      ['dataQualityTable', api.analytics.dataQualityTable()],
      ['demoStory', api.analytics.demoStory()],
      ['complianceSummary', api.analytics.complianceSummary()],
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
      const nextKeywordInsights = value<KeywordInsightsAnalytics>(9);
      const nextKeywordHeatmap = value<KeywordHeatmapAnalytics>(10);
      const nextTopics = value<TopicAnalytics>(11);
      const nextSourceHealth = value<SourceHealthAnalytics>(12);
      const nextLineage = value<LineageAnalytics>(13);
      const nextCrawlFlow = value<CrawlFlowAnalytics>(14);
      const nextDataQualityTable = value<DataQualityTableAnalytics>(15);
      const nextDemoStory = value<DemoStoryAnalytics>(16);
      const nextComplianceSummary = value<ComplianceSummary>(17);
      const nextTrends = value<TrendAnalytics>(18);
      const nextKeywords = value<KeywordAnalytics>(19);
      const nextEngagement = value<EngagementAnalytics>(20);
      const nextPlatforms = value<PlatformAnalytics>(21);
      const nextQuality = value<DataQualityAnalytics>(22);
      const nextWorkflow = value<WorkflowSummary>(23);
      setSummary(nextSummary);
      setSources(nextSources ?? []);
      setSourceCatalog(nextSourceCatalog ?? []);
      setJobs(nextJobs ?? []);
      setReports(nextReports ?? []);
      setOverview(nextOverview);
      setDashboard(nextDashboard);
      setTimeSeries(nextTimeSeries);
      setKeywordNetwork(nextKeywordNetwork);
      setKeywordInsights(nextKeywordInsights);
      setKeywordHeatmap(nextKeywordHeatmap);
      setTopics(nextTopics);
      setSourceHealth(nextSourceHealth);
      setLineage(nextLineage);
      setCrawlFlow(nextCrawlFlow);
      setDataQualityTable(nextDataQualityTable);
      setDemoStory(nextDemoStory);
      setComplianceSummary(nextComplianceSummary);
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

  function openDrilldown(kind: string, id: string | number, fallback?: Partial<DrilldownResponse>) {
    setInsight(null);
    navigate(`/detail/${encodeURIComponent(kind)}/${encodeURIComponent(String(id))}`, {
      state: { fallback, from: location.pathname },
    });
  }

  useEffect(() => {
    void loadCore();
  }, [loadCore]);

  useEffect(() => {
    void loadPosts(filters);
  }, [filters, loadPosts]);

  useEffect(() => {
    if (routePage) {
      setActivePage(routePage);
    }
  }, [routePage]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setInsight(null);
        setAssistantOpen(false);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

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
      await refreshAfterRun(api.demo.runWorkflow({ rows: 10000, reset_demo: true }));
      setStatus('Demo workflow ready');
      setDemoMode(true);
      setActivePage('demo');
    } catch (error) {
      setStatus((error as Error).message);
    } finally {
      setDemoRunning(false);
    }
  }

  async function generateExcelReport() {
    setInsight(null);
    setReportRunning(true);
    setStatus('Generating Excel report...');
    try {
      const result = await api.reportsApi.generateExcel();
      setLastReportRun(result);
      await loadCore();
      setStatus(`Excel report ready: ${result.output_path}`);
    } catch (error) {
      setStatus((error as Error).message);
    } finally {
      setReportRunning(false);
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
                onClick={() => {
                  setInsight(null);
                  navigate(pagePaths[page.key]);
                  setActivePage(page.key);
                }}
              >
                <Icon size={17} />
                <span>{t(page.labelKey)}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <section className="content-shell">
        <header className="topbar">
          <div>
            <p className="eyebrow">{t('top.eyebrow')}</p>
            <h1>{isDetailRoute ? t('detail.title') : t(pages.find((page) => page.key === activePage)?.labelKey ?? '')}</h1>
          </div>
          <div className="topbar-actions">
            <div className="language-toggle" aria-label="Language switcher">
              <button className={language === 'zh' ? 'active' : ''} type="button" onClick={() => changeLanguage('zh')}>中文</button>
              <button className={language === 'en' ? 'active' : ''} type="button" onClick={() => changeLanguage('en')}>English</button>
            </div>
            <button className="demo-toggle" type="button" onClick={() => setAssistantOpen(true)}>
              <Sparkles size={16} />
              {t('button.assistant')}
            </button>
            <button
              className={demoMode ? 'demo-toggle active' : 'demo-toggle'}
              type="button"
              onClick={() => setDemoMode((enabled) => !enabled)}
            >
              <Sparkles size={16} />
              {t('button.demoMode')}
            </button>
            <button
              className="primary-action"
              type="button"
              onClick={() => void runDemoWorkflow()}
              disabled={demoRunning}
            >
              <PlayCircle size={16} />
              {demoRunning ? t('button.running') : t('button.runDemo')}
            </button>
            <span className="api-status">{status}</span>
            <button className="icon-button" onClick={() => void loadCore()} aria-label="Refresh dashboard">
              <RefreshCw size={17} />
            </button>
          </div>
        </header>

        {overview?.demo_dataset_present && (
          <div className="demo-banner">
            {t('top.demoBanner')}
          </div>
        )}

        {demoMode && <InterviewDemoGuide activePage={activePage} story={demoStory} />}
        <DemoAssistant
          open={assistantOpen}
          step={tourStep}
          language={language}
          onClose={() => setAssistantOpen(false)}
          onStepChange={(nextStep, page) => {
            setInsight(null);
            setTourStep(nextStep);
            setActivePage(page);
            window.setTimeout(() => {
              document.querySelector(`[data-tour="${tourSteps[nextStep].target}"]`)?.scrollIntoView({
                behavior: 'smooth',
                block: 'center',
              });
            }, 120);
            navigate(pagePaths[page]);
          }}
          onOpen={() => {
            setInsight(null);
            setAssistantOpen(true);
            setTourStep(0);
            setActivePage(tourSteps[0].page);
            navigate(pagePaths[tourSteps[0].page]);
          }}
        />
        {coreLoading && <div className="loading-strip">{t('top.loading')}</div>}
        <EndpointStatusMatrix statuses={endpointStatus} />

        {isDetailRoute ? <DetailPage /> : renderPage(activePage)}
      </section>

      {insight && (
        <InsightDrawer
          insight={insight}
          loading={insightLoading}
          onClose={() => setInsight(null)}
          onDrilldown={(kind, id) => void openDrilldown(kind, id)}
          t={t}
        />
      )}
    </main>
  );

  function renderPage(page: PageKey) {
    switch (page) {
      case 'overview':
        return (
          <>
            <div data-tour="overview-kpis">
            <SummaryCards
              summary={summary}
              onSelectMetric={(key, label, value) => void openDrilldown('kpi', key, {
                title: label,
                summary: { value },
              })}
            />
            </div>
            <OverviewDashboard
              dashboard={dashboard}
              jobs={jobs}
              onDrilldown={(kind, id, fallback) => void openDrilldown(kind, id, fallback)}
            />
          </>
        );
      case 'demo':
        return (
          <DemoWalkthroughPage
            story={demoStory}
            onRunDemo={() => void runDemoWorkflow()}
            running={demoRunning}
            onDrilldown={(kind, id, fallback) => void openDrilldown(kind, id, fallback)}
          />
        );
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
        return <JobsTimeline jobs={jobs} onSelectJob={(job) => openDrilldown('job', job.id, { title: `${job.source} / ${job.job_type}`, metadata: job as unknown as Record<string, unknown> })} />;
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
            topics={topics}
            network={keywordNetwork}
            insights={keywordInsights}
            heatmap={keywordHeatmap}
            onDrilldown={(kind, id, fallback) => void openDrilldown(kind, id, fallback)}
            t={t}
          />
        );
      case 'engagement':
        return <EngagementPage engagement={engagement} onDrilldown={(kind, id, fallback) => openDrilldown(kind, id, fallback)} />;
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
        return (
          <ReportsCenter
            reports={reports}
            running={reportRunning}
            lastRun={lastReportRun}
            onGenerate={() => void generateExcelReport()}
            onDrilldown={(kind, id, fallback) => void openDrilldown(kind, id, fallback)}
            t={t}
          />
        );
      case 'compliance':
        return (
          <CompliancePage
            jobs={jobs}
            quality={quality}
            complianceSummary={complianceSummary}
            onVerifyDcard={(payload) => refreshAfterRun(api.verifyDcard(payload))}
            onVerifyPtt={(payload) => refreshAfterRun(api.verifyPtt(payload))}
            onVerifyNews={(payload) => refreshAfterRun(api.verifyNewsRss(payload))}
            onDiagnoseDcard={(payload) => refreshAfterRun(api.diagnoseDcard(payload))}
            onDrilldown={(kind, id, fallback) => void openDrilldown(kind, id, fallback)}
            t={t}
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

function DemoAssistant({
  open,
  step,
  language,
  onClose,
  onStepChange,
  onOpen,
}: {
  open: boolean;
  step: number;
  language: Language;
  onClose: () => void;
  onStepChange: (step: number, page: PageKey) => void;
  onOpen: () => void;
}) {
  const { t } = useTranslation();
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null);
  useEffect(() => {
    document.querySelectorAll('.tour-target-active').forEach((item) => item.classList.remove('tour-target-active'));
    if (open) {
      const target = document.querySelector(`[data-tour="${tourSteps[step].target}"]`);
      target?.classList.add('tour-target-active');
      const updateRect = () => {
        const rect = target?.getBoundingClientRect();
        setTargetRect(rect ?? null);
      };
      updateRect();
      window.addEventListener('resize', updateRect);
      window.addEventListener('scroll', updateRect, true);
      return () => {
        window.removeEventListener('resize', updateRect);
        window.removeEventListener('scroll', updateRect, true);
        document.querySelectorAll('.tour-target-active').forEach((item) => item.classList.remove('tour-target-active'));
      };
    }
    return () => {
      document.querySelectorAll('.tour-target-active').forEach((item) => item.classList.remove('tour-target-active'));
    };
  }, [open, step]);

  if (!open) {
    return (
      <button className="assistant-bubble" type="button" onClick={onOpen} aria-label={t('button.assistant')}>
        <Sparkles size={20} />
        <span>{t('button.assistant')}</span>
      </button>
    );
  }
  const current = tourSteps[step];
  const isLast = step === tourSteps.length - 1;
  const title = t(`assistant.steps.${current.i18nKey}Title`);
  const body = t(`assistant.steps.${current.i18nKey}Body`);
  const bullets = t(`assistant.steps.${current.i18nKey}Bullets`, { returnObjects: true }) as unknown as string[];
  return (
    <>
      <div className="tour-overlay" />
      {targetRect && (
        <div
          className="tour-spotlight"
          style={{
            top: targetRect.top - 10,
            left: targetRect.left - 10,
            width: targetRect.width + 20,
            height: targetRect.height + 20,
          }}
        />
      )}
      {targetRect && (
        <div
          className="tour-arrow"
          style={{
            top: Math.min(targetRect.bottom + 12, window.innerHeight - 170),
            left: Math.min(Math.max(targetRect.left + targetRect.width / 2, 80), window.innerWidth - 120),
          }}
        />
      )}
      <aside className="assistant-card">
        <div className="assistant-header">
          <div>
            <p className="eyebrow">{t('assistant.title')}</p>
            <h2>{title}</h2>
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Close assistant">
            <X size={16} />
          </button>
        </div>
        <p>{body}</p>
        <ul>
          {bullets.map((item) => <li key={item}>{item}</li>)}
        </ul>
        <div className="assistant-target">{t('assistant.target')}: {current.target}</div>
        <div className="assistant-actions">
          <button type="button" onClick={() => onStepChange(Math.max(step - 1, 0), tourSteps[Math.max(step - 1, 0)].page)} disabled={step === 0}>{t('assistant.prev')}</button>
          <button type="button" onClick={onClose}>{t('assistant.skip')}</button>
          <button
            className="primary-action"
            type="button"
            onClick={() => {
              if (isLast) {
                onClose();
              } else {
                onStepChange(step + 1, tourSteps[step + 1].page);
              }
            }}
          >
            {isLast ? t('assistant.done') : t('assistant.next')}
          </button>
        </div>
      </aside>
    </>
  );
}

function EnhancedFlowNode({ data, selected }: NodeProps) {
  const { i18n } = useTranslation();
  const payload = data as Record<string, unknown>;
  const status = String(payload.status ?? payload.type ?? 'ready');
  const label = localizedField(payload, 'label', i18n.language);
  const purpose = localizedField(payload, 'purpose', i18n.language);
  return (
    <button className={selected ? 'enhanced-node selected' : 'enhanced-node'} type="button">
      <Handle type="target" position={Position.Left} />
      <div className={`node-orbit node-status-${status.replaceAll('_', '-')}`} />
      <div className="node-body">
        <strong>{label || 'Node'}</strong>
        <span>{purpose || String(payload.subtitle ?? payload.type ?? 'interactive graph node')}</span>
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
  t,
}: {
  insight: DrilldownResponse;
  loading: boolean;
  onClose: () => void;
  onDrilldown: (kind: string, id: string | number) => void;
  t: (key: string) => string;
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
      {loading && <div className="loading-strip">{t('detail.loading')}</div>}
      <div className="drawer-body">
        <div className="metadata-status">
          <strong>{t('metadata.status')} / Metadata</strong>
          <span>{insight.metadata_status ?? 'available'}</span>
          <small>Fields: {(insight.available_fields ?? []).join(', ') || '-'}</small>
        </div>
        <InsightSection title={String(t('common.summary'))} payload={insight.summary} />
        <InsightSection title={String(t('common.metadata'))} payload={insight.metadata} />
        {insight.quality_flags.length > 0 && (
          <div className="detail-section">
            <strong>{t('common.qualityFlags')}</strong>
            <TagList items={insight.quality_flags} tone="danger" />
          </div>
        )}
        <div className="detail-section">
          <strong>{t('common.relatedPosts')}</strong>
          <DataTable
            columns={relatedPostColumns}
            data={insight.related_posts}
            onRowSelect={(row) => row.id && onDrilldown('post', String(row.id))}
          />
        </div>
        <div className="detail-section">
          <strong>{t('common.relatedJobs')}</strong>
          <DataTable
            columns={relatedJobColumns}
            data={insight.related_jobs}
            onRowSelect={(row) => row.id && onDrilldown('job', String(row.id))}
          />
        </div>
        <div className="detail-section">
          <strong>{t('common.rawPayload')}</strong>
          <pre className="json-panel">{JSON.stringify(insight.raw_payload, null, 2)}</pre>
        </div>
      </div>
    </aside>
  );
}

function InsightSection({ title, payload }: { title: string; payload: Record<string, unknown> }) {
  const { t } = useTranslation();
  return (
    <div className="detail-section">
      <strong>{title}</strong>
      <div className="metadata-list">
        {Object.entries(payload).length ? Object.entries(payload).map(([key, value]) => (
          <div className="metadata-row" key={key}>
            <strong>{key}</strong>
            <span>{formatValue(value)}</span>
          </div>
        )) : <div className="empty-state">{t('common.noMetadata')}</div>}
      </div>
    </div>
  );
}

function DetailPage() {
  const navigate = useNavigate();
  const routeLocation = useLocation();
  const { t } = useTranslation();
  const state = routeLocation.state as { fallback?: Partial<DrilldownResponse>; from?: string } | null;
  const [, , kind = '', encodedId = ''] = routeLocation.pathname.split('/');
  const id = decodeURIComponent(encodedId);
  const decodedKind = decodeURIComponent(kind);
  const fallback = state?.fallback;
  const [detail, setDetail] = useState<DrilldownResponse | null>(
    fallback
      ? {
          kind: decodedKind,
          id,
          title: fallback.title ?? `${decodedKind}:${id}`,
          subtitle: fallback.subtitle ?? '',
          summary: fallback.summary ?? {},
          metadata: fallback.metadata ?? {},
          related_posts: fallback.related_posts ?? [],
          related_jobs: fallback.related_jobs ?? [],
          quality_flags: fallback.quality_flags ?? [],
          raw_payload: fallback.raw_payload ?? {},
          metadata_status: fallback.metadata_status,
          available_fields: fallback.available_fields,
          missing_fields: fallback.missing_fields,
        }
      : null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    api.analytics.drilldown({ kind: decodedKind, id })
      .then((response) => {
        if (active) {
          setDetail(response);
        }
      })
      .catch((err: Error) => {
        if (active) {
          setError(err.message);
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [decodedKind, id]);

  if (!detail && loading) {
    return <div className="panel"><div className="loading-strip">{t('detail.loading')}</div></div>;
  }
  if (!detail) {
    return <div className="panel"><div className="empty-state">{error ?? t('detail.notFound')}</div></div>;
  }

  const relatedPostColumns = columnsForRows(detail.related_posts);
  const relatedJobColumns = columnsForRows(detail.related_jobs);
  const sourceUrl = String(detail.metadata.url ?? detail.metadata.canonical_url ?? detail.raw_payload.url ?? '');
  const contentText = String(detail.metadata.content ?? detail.metadata.excerpt ?? detail.raw_payload.content ?? '');
  const metricRows: Array<[string, string | number]> = [
    ['Platform', String(detail.metadata.platform ?? '-')],
    ['Board / Forum', String(detail.metadata.board_or_forum ?? '-')],
    ['Published', String(detail.metadata.published_at ?? detail.metadata.created_at ?? '-')],
    ['Comments', Number(detail.metadata.comment_count ?? 0)],
    ['Likes', Number(detail.metadata.like_count ?? 0)],
    ['Views', Number(detail.metadata.view_count ?? 0)],
    ['Content Hash', String(detail.metadata.content_hash ?? '-')],
  ];

  return (
    <section className="detail-page">
      <div className="panel wide-panel detail-hero">
        <div>
          <p className="eyebrow">{detail.kind} / {detail.id}</p>
          <h2>{detail.title}</h2>
          <span>{detail.subtitle}</span>
        </div>
        <div className="detail-actions">
          <button className="demo-toggle" type="button" onClick={() => navigate(state?.from ?? pagePaths.overview)}>
            {t('detail.backToWorkbench')}
          </button>
          {sourceUrl && (
            <a className="primary-action" href={sourceUrl} target="_blank" rel="noreferrer">
              <FileText size={16} />
              {t('detail.sourceUrl')}
            </a>
          )}
        </div>
      </div>

      {loading && <div className="loading-strip">{t('detail.loading')}</div>}
      {error && <div className="endpoint-matrix"><button className="endpoint-error" type="button">{error}</button></div>}

      <div className="detail-grid">
        {detail.kind === 'post' && (
          <div className="panel wide-panel article-detail-panel">
            <div className="panel-header"><h2>{detail.title}</h2></div>
            <p className="article-content">{contentText || t('detail.noContent')}</p>
          </div>
        )}
        {detail.kind === 'post' && (
          <div className="panel">
            <div className="panel-header"><h2>{t('common.metadata')}</h2></div>
            <div className="metadata-list">
              {metricRows.map(([label, value]) => (
                <div className="metadata-row" key={label}>
                  <strong>{label}</strong>
                  <span>{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        <div className="panel">
          <div className="metadata-status">
            <strong>{t('metadata.status')} / Metadata</strong>
            <span>{detail.metadata_status ?? 'available'}</span>
            <small>{t('common.fields')}: {(detail.available_fields ?? []).join(', ') || '-'}</small>
          </div>
          <InsightSection title={String(t('common.summary'))} payload={detail.summary} />
        </div>
        <div className="panel">
          <InsightSection title={String(t('common.metadata'))} payload={detail.metadata} />
        </div>
        {detail.quality_flags.length > 0 && (
          <div className="panel">
            <div className="detail-section">
              <strong>{t('common.qualityFlags')}</strong>
              <TagList items={detail.quality_flags} tone="danger" />
            </div>
          </div>
        )}
        <div className="panel wide-panel">
          <div className="panel-header"><h2>{t('common.relatedPosts')}</h2></div>
          <DataTable
            columns={relatedPostColumns}
            data={detail.related_posts}
            onRowSelect={(row) => row.id && navigate(`/detail/post/${encodeURIComponent(String(row.id))}`, { state: { from: routeLocation.pathname } })}
          />
        </div>
        <div className="panel wide-panel">
          <div className="panel-header"><h2>{t('common.relatedJobs')}</h2></div>
          <DataTable
            columns={relatedJobColumns}
            data={detail.related_jobs}
            onRowSelect={(row) => row.id && navigate(`/detail/job/${encodeURIComponent(String(row.id))}`, { state: { from: routeLocation.pathname } })}
          />
        </div>
        <div className="panel wide-panel">
          <div className="panel-header"><h2>{t('common.rawPayload')}</h2></div>
          <pre className="json-panel">{JSON.stringify(detail.raw_payload, null, 2)}</pre>
        </div>
      </div>
    </section>
  );
}

function InterviewDemoGuide({
  activePage,
  story,
}: {
  activePage: PageKey;
  story: DemoStoryAnalytics | null;
}) {
  const { t } = useTranslation();
  return (
    <div className="demo-guide">
      <div>
        <p className="eyebrow">{t('demo.mode')}</p>
        <strong>{t(`demo.guide.${activePage}`, { defaultValue: t('demo.guide.fallback') })}</strong>
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
  onDrilldown,
}: {
  story: DemoStoryAnalytics | null;
  onRunDemo: () => void;
  running: boolean;
  onDrilldown: (kind: string, id: string, fallback?: Partial<DrilldownResponse>) => void;
}) {
  const { t } = useTranslation();
  const [selectedStep, setSelectedStep] = useState<DemoStoryStep | null>(null);
  const activeStep = selectedStep ?? story?.walkthrough_steps[0] ?? null;
  return (
    <section className="story-layout" data-tour="demo-workflow">
      <div className="panel wide-panel story-hero">
        <div>
          <p className="eyebrow">{t('demo.eyebrow')}</p>
          <h2>{story?.title ?? t('demo.fallbackTitle')}</h2>
          <p>{story?.subtitle ?? t('demo.fallbackSubtitle')}</p>
        </div>
        <button className="primary-action large-action" type="button" onClick={onRunDemo} disabled={running}>
          <PlayCircle size={18} />
          {running ? t('demo.generating') : t('demo.runWorkflow')}
        </button>
      </div>

      <div className="demo-proof-grid">
        {(story?.proof_cards ?? []).map((card) => (
          <button
            className="proof-card"
            type="button"
            key={card.title}
            onClick={() => onDrilldown(card.drilldown_kind, card.drilldown_id, {
              title: card.title,
              summary: { value: card.value },
              metadata: card as unknown as Record<string, unknown>,
            })}
          >
            <span>{card.value}</span>
            <strong>{card.title}</strong>
            <small>{card.caption}</small>
          </button>
        ))}
      </div>

      <div className="panel wide-panel demo-path-panel">
        <div className="panel-header">
          <h2>Recommended demo path</h2>
          <span className="pill">{story?.evidence_metrics?.keywords ?? 0} taxonomy keywords</span>
        </div>
        <div className="demo-path">
          {(story?.recommended_demo_path ?? []).map((item, index) => (
            <div className="demo-path-step" key={item}>
              <span>{index + 1}</span>
              <strong>{item}</strong>
            </div>
          ))}
        </div>
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
          <h2>{t('demo.capabilities')}</h2>
          <span className="pill">{t('demo.talkingPoints')}</span>
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
  const { t } = useTranslation();
  if (!step) {
    return <div className="panel"><div className="empty-state">{t('demo.emptyStory')}</div></div>;
  }
  return (
    <aside className="panel story-detail-panel">
      <div className="panel-header">
        <h2>{step.label}</h2>
        <StatusBadge value={step.status} />
      </div>
      <p className="detail-purpose">{step.purpose}</p>
      <div className="detail-section">
        <strong>{t('demo.inputs')}</strong>
        <TagList items={step.inputs} />
      </div>
      <div className="detail-section">
        <strong>{t('demo.outputs')}</strong>
        <TagList items={step.outputs} />
      </div>
      <div className="detail-section">
        <strong>{t('demo.artifacts')}</strong>
        <TagList items={[...step.tables, step.artifact ?? 'runtime diagnostics']} />
      </div>
      <div className="detail-section">
        <strong>{t('demo.failures')}</strong>
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
  const { t } = useTranslation();
  return (
    <section className="page-grid analytics-grid">
      <div className="wide-panel" data-tour="architecture-map">
        <StoryGraphPanel graph={graph} title={String(t('architecture.map'))} onDrilldown={onDrilldown} />
      </div>
      <aside className="panel wide-panel">
        <div className="panel-header"><h2>{t('architecture.narrative')}</h2></div>
        <div className="metadata-list">
          <div className="metadata-row"><strong>Sources</strong><span>{t('architecture.sources')}</span></div>
          <div className="metadata-row"><strong>Crawler Core</strong><span>{t('architecture.core')}</span></div>
          <div className="metadata-row"><strong>Storage</strong><span>{t('architecture.storage')}</span></div>
          <div className="metadata-row"><strong>Presentation</strong><span>{t('architecture.presentation')}</span></div>
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
  const { t } = useTranslation();
  return (
    <section className="page-grid analytics-grid">
      <div className="wide-panel">
        <StoryGraphPanel graph={graph} title={String(t('lifecycle.title'))} onDrilldown={onDrilldown} />
      </div>
      <div className="panel">
        <div className="panel-header"><h2>{t('lifecycle.explanation')}</h2></div>
        <div className="metadata-list">
          <div className="metadata-row"><strong>Raw response</strong><span>{t('lifecycle.raw')}</span></div>
          <div className="metadata-row"><strong>Parsed item</strong><span>{t('lifecycle.parsed')}</span></div>
          <div className="metadata-row"><strong>Normalized post</strong><span>{t('lifecycle.normalized')}</span></div>
          <div className="metadata-row"><strong>Analysis output</strong><span>{t('lifecycle.output')}</span></div>
        </div>
      </div>
      <div className="panel">
        <div className="panel-header"><h2>{t('lifecycle.mix')}</h2></div>
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
  const { t, i18n } = useTranslation();
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const nodes = (graph?.nodes ?? []).map((node) => ({
    id: node.id,
    type: 'enhanced',
    position: node.position ?? { x: 0, y: 0 },
    data: { label: localizedField(node as unknown as Record<string, unknown>, 'label', i18n.language) || node.id, ...node },
    className: `flow-node story-node-${node.type ?? 'default'}`,
  })) as Node[];
  const edges = (graph?.edges ?? []).map((edge, index) => ({ id: edge.id ?? `${edge.source}-${edge.target}-${index}`, ...edge })) as Edge[];
  return (
    <div className="story-graph-grid">
      <div className="panel flow-panel story-flow-panel">
        <div className="panel-header">
          <h2>{title}</h2>
          <span className="pill">{t('common.clickVisual')}</span>
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
      <NodeDetailPanel node={selectedNode ?? (graph?.nodes[0] ?? null)} title={String(t('workflow.selectedNode'))} />
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
  const { t, i18n } = useTranslation();
  const areaData = pivotSeries(dashboard?.daily_platform_volume ?? [], 'platform');
  const platforms = uniqueGroups(dashboard?.daily_platform_volume ?? [], 'platform');
  const ratio = dashboard?.demo_live_ratio ?? { demo: 0, live: 0, total: 0 };
  const topPostColumns: ColumnDef<Record<string, unknown>>[] = [
    { accessorKey: 'platform', header: String(t('common.platform')) },
    { accessorKey: 'title', header: String(t('common.title')) },
    { accessorKey: 'engagement_score', header: 'Score' },
    { accessorKey: 'comment_count', header: String(t('common.comments')) },
  ];

  return (
    <section className="page-grid analytics-grid">
      <button className="panel wide-panel interactive-panel" type="button" onClick={() => onDrilldown('kpi', 'daily_platform_volume', { title: String(t('overview.dailyVolume')), raw_payload: { rows: dashboard?.daily_platform_volume ?? [] } })}>
        <div className="panel-header">
          <h2>{t('overview.dailyVolume')}</h2>
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

      <button className="panel interactive-panel" type="button" onClick={() => onDrilldown('kpi', 'platform_distribution', { title: String(t('overview.platformDistribution')), raw_payload: { rows: dashboard?.platform_distribution ?? [] } })}>
        <div className="panel-header">
          <h2>{t('overview.platformDistribution')}</h2>
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

      <button className="panel interactive-panel" type="button" onClick={() => onDrilldown('kpi', 'demo_live_ratio', { title: String(t('overview.demoLiveRatio')), summary: ratio })}>
        <div className="panel-header">
          <h2>{t('overview.demoLiveRatio')}</h2>
        </div>
        <div className="ratio-meter">
          <div style={{ width: `${ratio.total ? (ratio.demo / ratio.total) * 100 : 0}%` }} />
        </div>
        <div className="metadata-list">
          <div className="metadata-row"><strong>{t('overview.demoRecords')}</strong><span>{ratio.demo}</span></div>
          <div className="metadata-row"><strong>{t('overview.liveRecords')}</strong><span>{ratio.live}</span></div>
          <div className="metadata-row"><strong>{t('overview.totalRecords')}</strong><span>{ratio.total}</span></div>
        </div>
      </button>

      <button className="panel interactive-panel" type="button" onClick={() => onDrilldown('kpi', 'crawl_status_counts', { title: String(t('overview.crawlOutcome')), raw_payload: { rows: dashboard?.crawl_status_counts ?? [] } })}>
        <div className="panel-header">
          <h2>{t('overview.crawlOutcome')}</h2>
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

      <button className="panel interactive-panel" type="button" onClick={() => onDrilldown('keyword', dashboard?.top_keywords?.[0]?.keyword ?? 'AI', { title: String(t('overview.topKeywords')), raw_payload: { rows: dashboard?.top_keywords ?? [] } })}>
        <div className="panel-header">
          <h2>{t('overview.topKeywords')}</h2>
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
          <h2>{t('overview.latestHotPosts')}</h2>
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
          <h2>{t('overview.recentTimeline')}</h2>
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
  const { t } = useTranslation();
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
          <h2>{t('source.catalogSummary')}</h2>
        </div>
        <div className="metadata-list">
          <div className="metadata-row">
            <strong>{t('source.configured')}</strong>
            <span>{catalog.length}</span>
          </div>
          <div className="metadata-row">
            <strong>{t('source.enabled')}</strong>
            <span>{catalog.filter((source) => source.enabled).length}</span>
          </div>
          <div className="metadata-row">
            <strong>{t('source.databaseBacked')}</strong>
            <span>{catalog.filter((source) => source.database_backed).length}</span>
          </div>
        </div>
      </div>
      <div className="panel wide-panel">
        <div className="panel-header">
          <h2>{t('source.catalog')}</h2>
          <span className="pill">{t('source.yamlTargets')}</span>
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
  const { t, i18n } = useTranslation();
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const nodes = (crawlFlow?.nodes ?? []).map((node) => ({
    ...node,
    type: 'enhanced',
    data: {
      ...node.data,
      label: localizedField((node.data ?? {}) as Record<string, unknown>, 'label', i18n.language),
      purpose: localizedField((node.data ?? {}) as Record<string, unknown>, 'purpose', i18n.language),
      inputs: localizedList((node.data ?? {}) as Record<string, unknown>, 'inputs', i18n.language),
      outputs: localizedList((node.data ?? {}) as Record<string, unknown>, 'outputs', i18n.language),
      failure_modes: localizedList((node.data ?? {}) as Record<string, unknown>, 'failure_modes', i18n.language),
    },
    className: `flow-node flow-node-${String(node.data?.status ?? 'unknown').replaceAll('_', '-')}`,
  })) as Node[];
  const edges = (crawlFlow?.edges ?? []) as Edge[];

  return (
    <section className="flow-layout">
      <div className="panel flow-panel" data-tour="workflow-graph">
        <div className="panel-header">
          <h2>{t('workflow.graph')}</h2>
          {workflow?.latest_error && <span className="pill">{t('workflow.latestStop')}</span>}
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
      <NodeDetailPanel node={selectedNode ?? (crawlFlow?.nodes?.[0] ?? null)} title={String(t('workflow.nodeDetail'))} />
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
  const { t } = useTranslation();
  const sourceData = pivotSeries(timeSeries?.daily_by_source ?? [], 'source');
  const sources = uniqueGroups(timeSeries?.daily_by_source ?? [], 'source').slice(0, 6);
  return (
    <section className="page-grid">
      <div className="panel wide-panel">
        <div className="panel-header">
          <h2>{t('trends.daily')}</h2>
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
        <div className="panel-header"><h2>{t('trends.source')}</h2></div>
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
      <SimpleList title={String(t('trends.boards'))} rows={(trends?.top_boards ?? []).map((item) => [item.board_or_forum, item.count])} />
    </section>
  );
}

function KeywordPage({
  keywords,
  topics,
  network,
  insights,
  heatmap,
  onDrilldown,
  t,
}: {
  keywords: KeywordAnalytics | null;
  topics: TopicAnalytics | null;
  network: KeywordNetworkAnalytics | null;
  insights: KeywordInsightsAnalytics | null;
  heatmap: KeywordHeatmapAnalytics | null;
  onDrilldown: (kind: string, id: string, fallback?: Partial<DrilldownResponse>) => void;
  t: (key: string) => string;
}) {
  const [selectedNode, setSelectedNode] = useState<KeywordNetworkAnalytics['nodes'][number] | null>(null);
  const heatmapMax = Math.max(...(heatmap?.cells ?? []).map((cell) => cell.count), 1);
  const phraseColumns: ColumnDef<Record<string, unknown>>[] = [
    { accessorKey: 'keyword', header: String(t('common.keyword')) },
    { accessorKey: 'count', header: String(t('common.count')) },
  ];
  const legend = Array.from(
    new Map((network?.nodes ?? []).map((node) => [node.group ?? 'Topic', node.color ?? '#64748b'])),
  );

  return (
    <section className="page-grid analytics-grid">
      <div className="panel wide-panel topic-overview-panel">
        <div className="panel-header">
          <h2>Topic Overview</h2>
          <span className="pill">
            {topics?.taxonomy_size.topics ?? 0} topics / {topics?.taxonomy_size.keywords ?? 0} keywords
          </span>
        </div>
        <div className="topic-card-grid">
          {(topics?.topics ?? []).map((topic) => (
            <button
              className="topic-card"
              type="button"
              key={topic.topic_id}
              onClick={() => onDrilldown('topic', topic.topic_id, {
                title: topic.topic_name,
                metadata: topic as unknown as Record<string, unknown>,
              })}
              style={{ borderColor: topic.color }}
            >
              <span style={{ background: topic.color }} />
              <strong>{topic.topic_name}</strong>
              <small>{topic.count} posts</small>
              <em>{topic.top_keywords.slice(0, 4).map((item) => item.keyword).join(' / ')}</em>
            </button>
          ))}
        </div>
      </div>
      <div className="panel">
        <div className="panel-header"><h2>{t('keyword.frequency')}</h2></div>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={keywords?.keywords ?? []} layout="vertical">
            <XAxis type="number" allowDecimals={false} />
            <YAxis type="category" dataKey="keyword" width={90} />
            <Tooltip />
            <Bar dataKey="count" fill="var(--color-primary)" radius={[0, 6, 6, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="panel wide-panel network-panel" data-tour="keyword-network">
        <div className="panel-header"><h2>{t('keyword.network')}</h2><span className="pill">{t('keyword.groups')}</span></div>
        <div className="network-legend" aria-label={t('network.legend')}>
          {legend.map(([group, color]) => (
            <span key={group}><i style={{ background: color }} />{group}</span>
          ))}
        </div>
        <KeywordBubbleMap
          network={network}
          selectedKeyword={selectedNode?.id}
          onNodeClick={(node) => {
            setSelectedNode(node);
            onDrilldown('keyword', node.id, {
              title: node.label,
              metadata: node as unknown as Record<string, unknown>,
            });
          }}
        />
      </div>
      <div className="panel wide-panel">
        <div className="panel-header"><h2>{t('keyword.heatmap')}</h2></div>
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
        <div className="panel-header"><h2>{t('keyword.phrases')}</h2></div>
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
        <div className="panel-header"><h2>{t('keyword.insightPanel')}</h2></div>
        {selectedNode ? (
          <KeywordInsightPanel node={selectedNode} t={t} />
        ) : (
          <KeywordInsightCards insights={insights} t={t} />
        )}
      </div>
    </section>
  );
}

function KeywordBubbleMap({
  network,
  selectedKeyword,
  onNodeClick,
}: {
  network: KeywordNetworkAnalytics | null;
  selectedKeyword?: string;
  onNodeClick: (node: KeywordNetworkAnalytics['nodes'][number]) => void;
}) {
  const { t } = useTranslation();
  const svgRef = useRef<SVGSVGElement | null>(null);
  const viewportRef = useRef<SVGGElement | null>(null);
  const zoomBehaviorRef = useRef<ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  const nodes = (network?.nodes ?? []).slice(0, 30);
  const links = network?.links ?? [];
  const width = 900;
  const height = 480;
  const centerX = width / 2;
  const centerY = height / 2;
  const maxValue = Math.max(...nodes.map((node) => node.value), 1);
  const positioned = nodes.map((node, index) => {
    const ring = index < 1 ? 0 : index < 7 ? 1 : 2;
    const ringIndex = ring === 0 ? 0 : index - (ring === 1 ? 1 : 7);
    const ringCount = ring === 0 ? 1 : ring === 1 ? 6 : Math.max(nodes.length - 7, 1);
    const angle = ring === 0 ? 0 : (Math.PI * 2 * ringIndex) / ringCount - Math.PI / 2;
    const distance = ring === 0 ? 0 : ring === 1 ? 145 : 290;
    const radius = Math.max(42, Math.min(78, 36 + Math.sqrt(node.value / maxValue) * 46));
    return {
      ...node,
      x: centerX + Math.cos(angle) * distance,
      y: centerY + Math.sin(angle) * distance,
      radius,
    };
  });
  const byId = new Map(positioned.map((node) => [node.id, node]));

  useEffect(() => {
    if (!svgRef.current || !viewportRef.current) return;
    const behavior = zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.7, 3.2])
      .on('zoom', (event: { transform: ZoomTransform }) => {
        select(viewportRef.current).attr('transform', event.transform.toString());
        setZoomLevel(Number(event.transform.k.toFixed(2)));
      });
    zoomBehaviorRef.current = behavior;
    select(svgRef.current).call(behavior);
    return () => {
      select(svgRef.current).on('.zoom', null);
    };
  }, [nodes.length]);

  function resetZoom() {
    if (!svgRef.current || !zoomBehaviorRef.current) return;
    select(svgRef.current).transition().duration(220).call(zoomBehaviorRef.current.transform, zoomIdentity);
  }

  return (
    <div className="bubble-map-shell">
      <div className="bubble-toolbar">
        <button type="button" onClick={resetZoom}>{t('keyword.resetView')}</button>
        <span>{t('keyword.zoomLevel')}: {Math.round(zoomLevel * 100)}%</span>
      </div>
      <svg ref={svgRef} className="keyword-bubble-map" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Keyword co-occurrence bubble map">
        <defs>
          <filter id="bubbleShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="8" stdDeviation="8" floodColor="#0f172a" floodOpacity="0.18" />
          </filter>
        </defs>
        <g ref={viewportRef}>
          <g className="bubble-links">
            {links.slice(0, 40).map((link) => {
              const source = byId.get(String(link.source));
              const target = byId.get(String(link.target));
              if (!source || !target) return null;
              return (
                <line
                  key={`${link.source}-${link.target}`}
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  strokeWidth={Math.max(1, Math.min(7, link.value))}
                />
              );
            })}
          </g>
          <g className="bubble-nodes">
            {positioned.map((node) => {
              const lines = wrapBubbleLabel(node.label, node.radius);
              const selected = selectedKeyword === node.id;
              return (
                <g
                  className={selected ? 'keyword-bubble selected' : 'keyword-bubble'}
                  key={node.id}
                  role="button"
                  tabIndex={0}
                  transform={`translate(${node.x} ${node.y})`}
                  onClick={() => onNodeClick(node)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') onNodeClick(node);
                  }}
                >
                  <title>{node.insight_summary ?? node.label}</title>
                  <circle r={node.radius} fill={node.color ?? '#2563eb'} />
                  <circle className="bubble-ring" r={node.radius + 4} />
                  <text textAnchor="middle" dominantBaseline="middle">
                    {lines.map((line, index) => (
                      <tspan
                        x="0"
                        dy={index === 0 ? `${-(lines.length - 1) * 9}` : '18'}
                        key={line}
                      >
                        {line}
                      </tspan>
                    ))}
                  </text>
                  <text className="bubble-count" textAnchor="middle" y={node.radius - 14}>{node.value}</text>
                </g>
              );
            })}
          </g>
        </g>
      </svg>
    </div>
  );
}

function KeywordInsightPanel({
  node,
  t,
}: {
  node: KeywordNetworkAnalytics['nodes'][number];
  t: (key: string) => string;
}) {
  return (
    <div className="keyword-insight-panel">
      <p>{node.insight_summary ?? '-'}</p>
      <div className="metadata-list">
        <div className="metadata-row"><strong>{t('keyword.relatedPosts')}</strong><span>{node.related_post_count ?? node.value}</span></div>
        <div className="metadata-row"><strong>{t('keyword.cooccurrenceStrength')}</strong><span>{node.cooccurrence_strength ?? 0}</span></div>
      </div>
      <MiniDistribution title={t('keyword.relatedTerms')} rows={(node.top_related_terms ?? []).map((item) => [item.keyword, item.count])} />
      <MiniDistribution title={t('keyword.platformDistribution')} rows={(node.platform_distribution ?? []).map((item) => [item.platform, item.count])} />
      <MiniDistribution title={t('keyword.boardDistribution')} rows={(node.board_distribution ?? []).map((item) => [item.board_or_forum, item.count])} />
      <div className="detail-section">
        <strong>{t('keyword.evidencePosts')}</strong>
        <div className="evidence-list">
          {(node.evidence_posts ?? node.samples ?? []).slice(0, 4).map((post) => (
            <span key={String(post.post_id ?? post.title)}>{String(post.title ?? '-')}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

function KeywordInsightCards({
  insights,
  t,
}: {
  insights: KeywordInsightsAnalytics | null;
  t: (key: string) => string;
}) {
  return (
    <div className="keyword-insight-cards">
      {(insights?.cards ?? []).slice(0, 4).map((card) => (
        <div className="highlight-card insight-card" key={card.keyword}>
          <i style={{ background: card.color ?? '#64748b' }} />
          <div>
            <strong>{card.title}</strong>
            <span>{card.summary}</span>
          </div>
        </div>
      ))}
      {!insights?.cards?.length && <div className="empty-state">{t('common.noData')}</div>}
    </div>
  );
}

function MiniDistribution({ title, rows }: { title: string; rows: Array<[string, number]> }) {
  const max = Math.max(...rows.map(([, count]) => count), 1);
  return (
    <div className="mini-distribution">
      <strong>{title}</strong>
      {rows.length ? rows.slice(0, 5).map(([label, count]) => (
        <div className="mini-bar" key={label}>
          <span>{label}</span>
          <b style={{ width: `${Math.max(8, (count / max) * 100)}%` }} />
          <em>{count}</em>
        </div>
      )) : <small>-</small>}
    </div>
  );
}

function wrapBubbleLabel(label: string, radius: number): string[] {
  const maxChars = radius > 64 ? 7 : 5;
  if (label.length <= maxChars) return [label];
  const chunks: string[] = [];
  for (let index = 0; index < label.length; index += maxChars) {
    chunks.push(label.slice(index, index + maxChars));
  }
  return chunks.slice(0, 3);
}

function EngagementPage({
  engagement,
  onDrilldown,
}: {
  engagement: EngagementAnalytics | null;
  onDrilldown: (kind: string, id: string | number, fallback?: Partial<DrilldownResponse>) => void;
}) {
  const { t } = useTranslation();
  return (
    <section className="page-grid">
      <div className="panel wide-panel">
        <div className="panel-header"><h2>{t('engagement.distribution')}</h2></div>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={(engagement?.top_posts ?? []).slice(0, 12)}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="platform" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="engagement_score" fill="var(--color-primary)" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <SimpleList
        title={String(t('engagement.average'))}
        rows={(engagement?.average_score_by_platform ?? []).map((item) => [item.platform, item.average_engagement_score])}
      />
      <SimpleList
        title={String(t('engagement.missing'))}
        rows={Object.entries(engagement?.missing_metrics ?? {})}
      />
      <div className="panel wide-panel">
        <div className="panel-header">
          <h2>{t('engagement.topPosts')}</h2>
        </div>
        <div className="ranked-list">
          {(engagement?.top_posts ?? []).slice(0, 12).map((post) => (
            <button className="ranked-row interactive-row" type="button" key={post.id} onClick={() => onDrilldown('post', post.id, { title: post.title, metadata: post as unknown as Record<string, unknown> })}>
              <div>
                <strong>{post.title}</strong>
                <span>{post.platform} / comments {post.comment_count} / likes {post.like_count}</span>
              </div>
              <b>{post.engagement_score}</b>
            </button>
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
  const { t } = useTranslation();
  const platformRows = platforms?.platforms ?? [];
  const radarData = platformRows.map((row) => ({
    platform: row.platform,
    volume: row.post_count,
    engagement: row.average_engagement_score,
    content: row.average_content_length,
    success: row.crawl_success_rate ?? 0,
  }));
  const sourceColumns: ColumnDef<Record<string, unknown>>[] = [
    { accessorKey: 'display_name', header: String(t('common.source')) },
    { accessorKey: 'platform', header: String(t('common.platform')) },
    { accessorKey: 'post_count', header: 'Posts' },
    { accessorKey: 'success_rate', header: 'Success %' },
    { accessorKey: 'failed_count', header: 'Failed' },
    { accessorKey: 'last_status', header: 'Last Status' },
  ];

  return (
    <section className="page-grid analytics-grid">
      <div className="panel">
        <div className="panel-header"><h2>{t('platform.volume')}</h2></div>
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
        <div className="panel-header"><h2>{t('platform.radar')}</h2></div>
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
        <div className="panel-header"><h2>{t('platform.contentLength')}</h2></div>
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
        <div className="panel-header"><h2>{t('platform.successRate')}</h2></div>
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
        <div className="panel-header"><h2>{t('platform.health')}</h2></div>
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
  const { t, i18n } = useTranslation();
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [activeTable, setActiveTable] = useState<keyof DataQualityTableAnalytics>('missing_content');
  const lineageNodes = (lineage?.nodes ?? []).map((node, index) => ({
    id: node.id,
    type: 'enhanced',
    position: { x: index * 190, y: index % 2 ? 140 : 20 },
    data: {
      label: `${localizedField(node as unknown as Record<string, unknown>, 'label', i18n.language) || node.id} (${node.count ?? 0})`,
      ...node,
    },
    className: `flow-node lineage-node-${node.type ?? 'default'}`,
  })) as Node[];
  const lineageEdges = (lineage?.edges ?? []).map((edge, index) => ({ id: edge.id ?? `edge-${index}`, ...edge })) as Edge[];
  const rows = (table?.[activeTable] ?? []) as Array<Record<string, unknown>>;
  const columns = columnsForRows(rows);

  return (
    <section className="page-grid analytics-grid">
      <div className="panel wide-panel flow-panel lineage-panel">
        <div className="panel-header"><h2>{t('quality.lineage')}</h2></div>
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
      <NodeDetailPanel node={selectedNode ?? (lineage?.nodes?.[0] ?? null)} title={String(t('quality.nodeDetail'))} />
      <SimpleList title={String(t('quality.checks'))} rows={(quality?.checks ?? []).map((item) => [item.name, item.count])} />
      <SimpleList title={String(t('quality.policyEvents'))} rows={(quality?.policy_events ?? []).map((item) => [item.category, item.count])} />
      <div className="panel wide-panel">
        <div className="panel-header"><h2>{t('quality.tables')}</h2></div>
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

function ReportsCenter({
  reports,
  running,
  lastRun,
  onGenerate,
  onDrilldown,
  t,
}: {
  reports: ReportSummary[];
  running: boolean;
  lastRun: ExcelReportRunResponse | null;
  onGenerate: () => void;
  onDrilldown: (kind: string, id: string, fallback?: Partial<DrilldownResponse>) => void;
  t: (key: string) => string;
}) {
  return (
    <section className="dashboard-grid" data-tour="report-center">
      <div className="panel">
        <div className="panel-header">
          <h2>{t('reports.generator')}</h2>
          <button className="primary-action" type="button" onClick={onGenerate} disabled={running}>
            <FileSpreadsheet size={16} />
            {running ? t('reports.generating') : t('reports.generate')}
          </button>
          {lastRun?.download_url && (
            <a
              className="demo-toggle"
              href={api.reportsApi.downloadUrl(lastRun.output_path)}
              download
            >
              <FileSpreadsheet size={16} />
              {t('reports.download')}
            </a>
          )}
        </div>
        <div className="metadata-list">
          <div className="metadata-row"><strong>{t('reports.output')}</strong><span>{lastRun?.output_path ?? 'data/exports/analysis_report.xlsx'}</span></div>
          <div className="metadata-row"><strong>{t('reports.status')}</strong><span>{lastRun?.download_url ? t('reports.downloadReady') : '-'}</span></div>
          <div className="metadata-row"><strong>{t('reports.rows')}</strong><span>{lastRun?.row_count ?? '-'}</span></div>
          <div className="metadata-row"><strong>{t('reports.matches')}</strong><span>{lastRun?.keyword_match_count ?? '-'}</span></div>
        </div>
      </div>
      <ReportsPanel
        reports={reports}
        onSelectReport={(report) => onDrilldown('report', report.path, {
          title: report.path,
          subtitle: report.report_type,
          metadata: report as unknown as Record<string, unknown>,
        })}
      />
      <div className="panel">
        <div className="panel-header">
          <h2>{t('reports.sheets')}</h2>
        </div>
        <div className="metadata-list">
          {['Summary', 'Raw Data', 'Daily Trend', 'Keyword Matches', 'Top Posts', 'Platform Comparison', 'Data Quality', 'Crawl Runs'].map((sheet) => (
            <div className="metadata-row" key={sheet}>
              <strong>{sheet}</strong>
              <span>{t('reports.ready')}</span>
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
  complianceSummary,
  onVerifyDcard,
  onVerifyPtt,
  onVerifyNews,
  onDiagnoseDcard,
  onDrilldown,
  t,
}: {
  jobs: CrawlJobResponse[];
  quality: DataQualityAnalytics | null;
  complianceSummary: ComplianceSummary | null;
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
  onDrilldown: (kind: string, id: string | number, fallback?: Partial<DrilldownResponse>) => void;
  t: (key: string) => string;
}) {
  return (
    <section className="page-grid analytics-grid" data-tour="compliance-summary">
      <ControlPanel
        onVerifyDcard={onVerifyDcard}
        onVerifyPtt={onVerifyPtt}
        onVerifyNews={onVerifyNews}
        onDiagnoseDcard={onDiagnoseDcard}
      />
      <div className="panel">
        <div className="panel-header"><h2>{t('compliance.summary')}</h2></div>
        <div className="metadata-list">
          {Object.entries(complianceSummary?.summary ?? {}).map(([key, value]) => (
            <button className="metadata-row interactive-row" type="button" key={key} onClick={() => onDrilldown('quality', key, { title: key, summary: { value } })}>
              <strong>{key}</strong><span>{value}</span>
            </button>
          ))}
        </div>
      </div>
      <SimpleList title={String(t('compliance.stopConditions'))} rows={(quality?.policy_events ?? []).map((item) => [item.category, item.count])} />
      <div className="panel wide-panel">
        <div className="panel-header">
          <h2>{t('compliance.outcomes')}</h2>
        </div>
        <div className="job-list">
          {jobs.map((job) => (
            <button className="job-row interactive-row" type="button" key={job.id} onClick={() => onDrilldown('job', job.id, { title: `${job.source} / ${job.job_type}`, metadata: job as unknown as Record<string, unknown> })}>
              <div>
                <div className="job-title">{job.source} / {job.job_type}</div>
                <div className="job-meta">{job.error_category ?? 'no policy event'} / {job.error_reason ?? 'ok'}</div>
              </div>
              <StatusBadge value={job.error_category ?? job.status} />
            </button>
          ))}
        </div>
      </div>
      <div className="panel wide-panel">
        <div className="panel-header"><h2>{t('compliance.rules')}</h2></div>
        <div className="highlight-grid">
          {(complianceSummary?.governance_rules ?? []).map((rule) => (
            <div className="highlight-card" key={rule}><ShieldCheck size={17} /><span>{rule}</span></div>
          ))}
        </div>
      </div>
    </section>
  );
}

function SettingsPage({ status }: { status: string }) {
  const { t } = useTranslation();
  return (
    <section className="page-grid">
      <div className="panel">
        <div className="panel-header">
          <h2>{t('settings.backend')}</h2>
        </div>
        <div className="metadata-list">
          <div className="metadata-row">
            <strong>{t('settings.apiStatus')}</strong>
            <span>{status}</span>
          </div>
          <div className="metadata-row">
            <strong>{t('settings.apiBase')}</strong>
            <span>{api.runtime.baseUrl()}</span>
          </div>
        </div>
      </div>
      <div className="panel">
        <div className="panel-header">
          <h2>{t('settings.commands')}</h2>
        </div>
        <code className="command-block">dcard-crawler seed-demo-data --rows 10000 --reset-demo</code>
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
  const { t } = useTranslation();
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });
  if (!data.length) {
    return <div className="empty-state">{t('common.noRows')}</div>;
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
              className={onRowSelect ? 'clickable-row interactive-row' : undefined}
              key={row.id}
              role={onRowSelect ? 'button' : undefined}
              tabIndex={onRowSelect ? 0 : undefined}
              onClick={() => onRowSelect?.(row.original)}
              onKeyDown={(event) => {
                if (!onRowSelect) return;
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  onRowSelect(row.original);
                }
              }}
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
  const { t, i18n } = useTranslation();
  const payload = (node?.data ?? node ?? {}) as Record<string, unknown>;
  const displayPayload = Object.fromEntries(
    Object.entries({
      ...payload,
      label: localizedField(payload, 'label', i18n.language) || payload.label,
      purpose: localizedField(payload, 'purpose', i18n.language) || payload.purpose,
      inputs: localizedList(payload, 'inputs', i18n.language) ?? payload.inputs,
      outputs: localizedList(payload, 'outputs', i18n.language) ?? payload.outputs,
      failure_modes: localizedList(payload, 'failure_modes', i18n.language) ?? payload.failure_modes,
    }).filter(([key]) => !key.endsWith('_zh') && !key.endsWith('_en')),
  );
  return (
    <aside className="panel node-detail-panel">
      <div className="panel-header"><h2>{title}</h2></div>
      {node ? (
        <div className="metadata-list">
          {Object.entries(displayPayload).map(([key, value]) => (
            <div className="metadata-row" key={key}>
              <strong>{key}</strong>
              <span>{formatValue(value)}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">{t('common.clickNode')}</div>
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
  const { t } = useTranslation();
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
        )) : <div className="empty-state">{t('common.noData')}</div>}
      </div>
    </div>
  );
}

function PostDrawer({ post, onClose }: { post: PostResponse; onClose: () => void }) {
  const { t } = useTranslation();
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
        <p>{post.content || post.excerpt || t('detail.noContent')}</p>
        <div className="metadata-list">
          <div className="metadata-row"><strong>{t('common.source')}</strong><span>{post.source}</span></div>
          <div className="metadata-row"><strong>{t('detail.externalId')}</strong><span>{post.external_id}</span></div>
          <div className="metadata-row"><strong>{t('common.published')}</strong><span>{post.published_at ?? '-'}</span></div>
          <div className="metadata-row"><strong>{t('common.comments')}</strong><span>{post.comment_count}</span></div>
          <div className="metadata-row"><strong>{t('detail.likes')}</strong><span>{post.like_count}</span></div>
          <div className="metadata-row"><strong>{t('detail.views')}</strong><span>{post.view_count}</span></div>
          <div className="metadata-row"><strong>{t('detail.contentHash')}</strong><span>{post.content_hash ?? '-'}</span></div>
          <div className="metadata-row"><strong>URL</strong><span>{post.url ?? '-'}</span></div>
        </div>
        {post.url && <a className="external-link" href={post.url} target="_blank" rel="noreferrer"><FileText size={16} /> {t('detail.sourceUrl')}</a>}
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

function localizedField(payload: Record<string, unknown>, field: string, language: string): string {
  const suffix = language === 'zh' ? 'zh' : 'en';
  return String(payload[`${field}_${suffix}`] ?? payload[field] ?? '');
}

function localizedList(payload: Record<string, unknown>, field: string, language: string): unknown {
  const suffix = language === 'zh' ? 'zh' : 'en';
  return payload[`${field}_${suffix}`] ?? payload[field];
}
