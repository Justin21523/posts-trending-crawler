import { FileJson } from 'lucide-react';
import type { ReportSummary } from '../api/types';
import { StatusBadge } from './StatusBadge';

type ReportsPanelProps = {
  reports: ReportSummary[];
  onSelectReport?: (report: ReportSummary) => void;
};

export function ReportsPanel({ reports, onSelectReport }: ReportsPanelProps) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Reports</h2>
      </div>
      <div className="report-list">
        {reports.length === 0 ? (
          <div className="empty-state">No reports yet.</div>
        ) : (
          reports.map((report) => (
            <button className="report-row interactive-row" type="button" key={report.path} onClick={() => onSelectReport?.(report)}>
              <FileJson size={17} />
              <div className="report-main">
                <strong>{report.report_type}</strong>
                <span>{report.path}</span>
              </div>
              <StatusBadge value={report.status ?? report.platform} />
            </button>
          ))
        )}
      </div>
    </section>
  );
}
