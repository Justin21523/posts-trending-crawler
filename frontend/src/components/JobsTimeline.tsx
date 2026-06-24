import { useTranslation } from 'react-i18next';
import type { CrawlJobResponse } from '../api/types';
import { StatusBadge } from './StatusBadge';

type JobsTimelineProps = {
  jobs: CrawlJobResponse[];
  onSelectJob?: (job: CrawlJobResponse) => void;
};

export function JobsTimeline({ jobs, onSelectJob }: JobsTimelineProps) {
  const { t } = useTranslation();
  const statusCounts = jobs.reduce<Record<string, number>>((acc, job) => {
    acc[job.status] = (acc[job.status] ?? 0) + 1;
    return acc;
  }, {});
  const total = Math.max(jobs.length, 1);
  return (
    <section className="page-grid">
      <div className="panel wide-panel">
        <div className="panel-header">
          <h2>{t('page.runs')}</h2>
          <span className="pill">{jobs.length} {t('common.rows')}</span>
        </div>
        <div className="status-distribution">
          {Object.entries(statusCounts).map(([status, count]) => (
            <button
              className={`status-segment status-segment-${status.replaceAll('_', '-')}`}
              key={status}
              style={{ flexGrow: count / total }}
              type="button"
              onClick={() => jobs.find((job) => job.status === status) && onSelectJob?.(jobs.find((job) => job.status === status)!)}
            >
              <strong>{status}</strong>
              <span>{count}</span>
            </button>
          ))}
        </div>
      </div>
      <div className="panel wide-panel">
        <div className="job-list">
          {jobs.length === 0 ? (
            <div className="empty-state">{t('common.noData')}</div>
          ) : (
            jobs.map((job) => (
              <button className="job-row interactive-row" type="button" key={job.id} onClick={() => onSelectJob?.(job)}>
                <div>
                  <div className="job-title">#{job.id} {job.source}</div>
                  <div className="job-meta">
                    {job.job_type} · {t('common.requests')} {job.request_count} · {t('common.items')} {job.item_count}
                  </div>
                  {job.error_reason ? <div className="job-error">{job.error_reason}</div> : null}
                </div>
                <StatusBadge value={job.status} />
              </button>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
