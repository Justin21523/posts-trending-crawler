import type { CrawlJobResponse } from '../api/types';
import { StatusBadge } from './StatusBadge';

type JobsTimelineProps = {
  jobs: CrawlJobResponse[];
};

export function JobsTimeline({ jobs }: JobsTimelineProps) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Crawl Jobs</h2>
      </div>
      <div className="job-list">
        {jobs.length === 0 ? (
          <div className="empty-state">No crawl jobs yet.</div>
        ) : (
          jobs.map((job) => (
            <div className="job-row" key={job.id}>
              <div>
                <div className="job-title">#{job.id} {job.source}</div>
                <div className="job-meta">{job.job_type} · requests {job.request_count} · items {job.item_count}</div>
                {job.error_reason ? <div className="job-error">{job.error_reason}</div> : null}
              </div>
              <StatusBadge value={job.status} />
            </div>
          ))
        )}
      </div>
    </section>
  );
}
