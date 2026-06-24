import { Play, Radar } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { DiagnosticsResponse, VerifyResponse } from '../api/types';

type ControlPanelProps = {
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
};

export function ControlPanel({ onVerifyDcard, onVerifyPtt, onVerifyNews, onDiagnoseDcard }: ControlPanelProps) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState<string | null>(null);
  const [result, setResult] = useState<string>(t('compliance.noRun'));

  async function run(label: string, action: () => Promise<VerifyResponse | DiagnosticsResponse>) {
    setBusy(label);
    setResult(`${t('compliance.running')} ${label}...`);
    try {
      const response = await action();
      setResult(`${label}: ${response.report_path}`);
    } catch (error) {
      setResult(`${label}: ${(error as Error).message}`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="panel control-panel">
      <div className="panel-header">
        <h2>{t('compliance.control')}</h2>
      </div>
      <div className="control-grid">
        <button onClick={() => run('Dcard verify', () => onVerifyDcard({ forum: 'trending', mode: 'latest', max_posts: 3 }))} disabled={busy !== null}>
          <Play size={16} /> Dcard
        </button>
        <button onClick={() => run('PTT verify', () => onVerifyPtt({ board: 'Stock', max_pages: 1, max_posts: 3, allow_robots_unavailable: true, allow_over18_public_confirm: false }))} disabled={busy !== null}>
          <Play size={16} /> PTT
        </button>
        <button onClick={() => run('News RSS verify', () => onVerifyNews({ source_name: 'cna-technology', feed_url: 'https://feeds.feedburner.com/rsscna/technology', max_articles: 3 }))} disabled={busy !== null}>
          <Play size={16} /> News
        </button>
        <button onClick={() => run('Dcard diagnostics', () => onDiagnoseDcard({ forum: 'trending' }))} disabled={busy !== null}>
          <Radar size={16} /> {t('compliance.diagnose')}
        </button>
      </div>
      <div className="run-result">{result}</div>
    </section>
  );
}
