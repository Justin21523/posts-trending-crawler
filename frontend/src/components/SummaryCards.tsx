import { Activity, Database, FileText, RadioTower } from 'lucide-react';
import type { DashboardSummary } from '../api/types';

type SummaryCardsProps = {
  summary: DashboardSummary | null;
};

export function SummaryCards({ summary }: SummaryCardsProps) {
  const counts = summary?.counts ?? {};
  const cards = [
    { label: 'Sources', value: counts.sources ?? 0, icon: Database },
    { label: 'Posts', value: counts.posts ?? 0, icon: FileText },
    { label: 'Crawl Jobs', value: counts.crawl_jobs ?? 0, icon: Activity },
    { label: 'API Health', value: summary?.health.database_ready ? 'Ready' : 'Schema needed', icon: RadioTower },
  ];

  return (
    <section className="summary-grid" aria-label="Crawler summary">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div className="metric-card" key={card.label}>
            <div className="metric-icon">
              <Icon size={18} />
            </div>
            <div>
              <div className="metric-label">{card.label}</div>
              <div className="metric-value">{card.value}</div>
            </div>
          </div>
        );
      })}
    </section>
  );
}
