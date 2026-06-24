import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { DashboardSummary, SourceResponse } from '../api/types';

type SourceOverviewProps = {
  sources: SourceResponse[];
  summary: DashboardSummary | null;
};

export function SourceOverview({ sources, summary }: SourceOverviewProps) {
  const platformData = Object.entries(summary?.platforms ?? {}).map(([name, value]) => ({
    name,
    value,
  }));

  return (
    <section className="panel source-panel">
      <div className="panel-header">
        <h2>Sources</h2>
      </div>
      <div className="source-layout">
        <div className="source-list">
          {sources.length === 0 ? (
            <div className="empty-state">No sources yet.</div>
          ) : (
            sources.map((source) => (
              <div className="source-row" key={source.id}>
                <div>
                  <strong>{source.name}</strong>
                  <span>{source.source_type}</span>
                </div>
                <span className={source.enabled ? 'pill pill-green' : 'pill'}>{source.enabled ? 'enabled' : 'off'}</span>
              </div>
            ))
          )}
        </div>
        <div className="chart-box">
          {platformData.length === 0 ? (
            <div className="empty-state">No platform data.</div>
          ) : (
            <ResponsiveContainer width="100%" height={190}>
              <BarChart data={platformData} layout="vertical" margin={{ top: 10, right: 12, bottom: 10, left: 10 }}>
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="name" width={54} tickLine={false} axisLine={false} />
                <Bar dataKey="value" fill="#2563eb" radius={[0, 6, 6, 0]} />
                <Tooltip />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </section>
  );
}
