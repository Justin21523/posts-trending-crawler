import { RefreshCw } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { api, type PostFilters } from './api/client';
import type {
  CrawlJobResponse,
  DashboardSummary,
  PostResponse,
  ReportSummary,
  SourceResponse,
} from './api/types';
import { ControlPanel } from './components/ControlPanel';
import { JobsTimeline } from './components/JobsTimeline';
import { PostsExplorer } from './components/PostsExplorer';
import { ReportsPanel } from './components/ReportsPanel';
import { SourceOverview } from './components/SourceOverview';
import { SummaryCards } from './components/SummaryCards';

export function App() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [sources, setSources] = useState<SourceResponse[]>([]);
  const [posts, setPosts] = useState<PostResponse[]>([]);
  const [jobs, setJobs] = useState<CrawlJobResponse[]>([]);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [filters, setFilters] = useState<PostFilters>({ limit: 50 });
  const [loadingPosts, setLoadingPosts] = useState(false);
  const [status, setStatus] = useState('Connecting to backend...');

  const loadCore = useCallback(async () => {
    try {
      const [nextSummary, nextSources, nextJobs, nextReports] = await Promise.all([
        api.summary(),
        api.sources(),
        api.jobs(),
        api.reports(),
      ]);
      setSummary(nextSummary);
      setSources(nextSources);
      setJobs(nextJobs);
      setReports(nextReports);
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
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Taiwan public data crawler</p>
          <h1>Forum & News Analytics Workbench</h1>
        </div>
        <div className="topbar-actions">
          <span className="api-status">{status}</span>
          <button className="icon-button" onClick={() => void loadCore()} aria-label="Refresh dashboard">
            <RefreshCw size={17} />
          </button>
        </div>
      </header>

      <SummaryCards summary={summary} />

      <section className="dashboard-grid">
        <SourceOverview sources={sources} summary={summary} />
        <ControlPanel
          onVerifyDcard={(payload) => refreshAfterRun(api.verifyDcard(payload))}
          onVerifyPtt={(payload) => refreshAfterRun(api.verifyPtt(payload))}
          onVerifyNews={(payload) => refreshAfterRun(api.verifyNewsRss(payload))}
          onDiagnoseDcard={(payload) => refreshAfterRun(api.diagnoseDcard(payload))}
        />
        <JobsTimeline jobs={jobs} />
        <ReportsPanel reports={reports} />
        <PostsExplorer
          posts={posts}
          filters={filters}
          loading={loadingPosts}
          onFiltersChange={(nextFilters) => setFilters({ ...nextFilters, limit: 50 })}
        />
      </section>
    </main>
  );
}
