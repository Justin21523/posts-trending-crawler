import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useTranslation } from 'react-i18next';
import type { DashboardSummary, SourceResponse } from '../api/types';

type SourceOverviewProps = {
  sources: SourceResponse[];
  summary: DashboardSummary | null;
  onSelectSource?: (source: SourceResponse) => void;
};

export function SourceOverview({ sources, summary, onSelectSource }: SourceOverviewProps) {
  const { t } = useTranslation();
  const platformData = Object.entries(summary?.platforms ?? {}).map(([name, value]) => ({
    name,
    value,
  }));

  return (
    <section className="panel source-panel">
      <div className="panel-header">
        <h2>{t('source.title')}</h2>
      </div>
      <div className="source-layout">
        <div className="source-list">
          {sources.length === 0 ? (
            <div className="empty-state">{t('source.noSources')}</div>
          ) : (
            sources.map((source) => (
              <button className="source-row interactive-row" type="button" key={source.id} onClick={() => onSelectSource?.(source)}>
                <div>
                  <strong>{source.name}</strong>
                  <span>{source.source_type}</span>
                </div>
                <span className={source.enabled ? 'pill pill-green' : 'pill'}>{source.enabled ? t('common.enabled') : t('common.disabled')}</span>
              </button>
            ))
          )}
        </div>
        <div className="chart-box">
          {platformData.length === 0 ? (
            <div className="empty-state">{t('source.noPlatform')}</div>
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
