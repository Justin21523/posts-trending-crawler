import { Activity, Database, FileText, RadioTower } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { DashboardSummary } from '../api/types';

type SummaryCardsProps = {
  summary: DashboardSummary | null;
  onSelectMetric?: (key: string, label: string, value: string | number) => void;
};

export function SummaryCards({ summary, onSelectMetric }: SummaryCardsProps) {
  const { t } = useTranslation();
  const counts = summary?.counts ?? {};
  const cards = [
    { key: 'total_sources', label: t('metrics.total_sources'), value: counts.sources ?? 0, icon: Database },
    { key: 'total_posts', label: t('metrics.total_posts'), value: counts.posts ?? 0, icon: FileText },
    { key: 'total_crawl_runs', label: t('metrics.total_crawl_runs'), value: counts.crawl_jobs ?? 0, icon: Activity },
    { key: 'api_health', label: t('metrics.api_health'), value: summary?.health.database_ready ? t('common.ready') : t('metrics.schema_needed'), icon: RadioTower },
  ];

  return (
    <section className="summary-grid" aria-label="Crawler summary">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <button className="metric-card interactive-panel" type="button" key={card.label} onClick={() => onSelectMetric?.(card.key, card.label, card.value)}>
            <div className="metric-icon">
              <Icon size={18} />
            </div>
            <div>
              <div className="metric-label">{card.label}</div>
              <div className="metric-value">{card.value}</div>
            </div>
          </button>
        );
      })}
    </section>
  );
}
