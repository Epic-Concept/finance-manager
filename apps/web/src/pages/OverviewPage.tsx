import { useEffect, useState } from 'react';
import { api, type Rule, type Stats } from '../api';
import { LedgerTable, StatLine } from '../components/ui';

export function OverviewPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [rules, setRules] = useState<Rule[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api<Stats>('/api/v1/stats'),
      api<{ items: Rule[] }>('/api/v1/rules'),
    ])
      .then(([s, r]) => {
        setStats(s);
        setRules(r.items);
      })
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Unable to load overview')
      );
  }, []);

  if (error) return <p className="empty">{error}</p>;
  if (!stats) return <p className="empty">Loading…</p>;

  return (
    <>
      <h1 className="display">Overview</h1>
      <StatLine label="Coverage" value={`${Math.round(stats.coverage * 100)}%`} />
      <StatLine
        label="Auto-apply rate"
        value={`${Math.round(stats.auto_apply_rate * 100)}%`}
      />
      <StatLine label="Pending review" value={String(stats.pending_review)} />
      <StatLine label="Cohort depth" value={String(stats.pending_cohorts)} />
      <h2 className="display" style={{ marginTop: '1.5rem', fontSize: '1.3rem' }}>
        Rules
      </h2>
      <LedgerTable
        headers={['CEL', 'Category']}
        rows={rules.map((r) => [r.expression, String(r.category_id)])}
      />
    </>
  );
}
