import { useEffect, useRef, useState } from 'react';
import { api, type Cohort } from '../api';
import { Button, Card } from './ui';

export function CohortCard({
  title,
  coverage,
}: {
  title: string;
  coverage?: number;
}) {
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [singletons, setSingletons] = useState<number[]>([]);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [empty, setEmpty] = useState(false);
  const [categoryId, setCategoryId] = useState('1');
  const [expression, setExpression] = useState('');
  const categoryRef = useRef<HTMLInputElement>(null);

  async function load() {
    try {
      const data = await api<{ items: Cohort[]; singletons: number[] }>(
        '/api/v1/cohorts'
      );
      setCohorts(data.items);
      setSingletons(data.singletons);
      setEmpty(data.items.length === 0);
      setIndex(0);
      const first = data.items[0];
      setExpression(first?.expression ?? '');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load cohorts');
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const current = cohorts[index];

  useEffect(() => {
    if (current) setExpression(current.expression);
  }, [current]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const tag = (event.target as HTMLElement | null)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      if (event.key === 'c') void resolve('confirm');
      if (event.key === 's') void resolve('skip');
      if (event.key === 'e') categoryRef.current?.focus();
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  async function resolve(action: 'confirm' | 'skip' | 'change') {
    if (!current) return;
    await api(`/api/v1/cohorts/${current.cohort_id}/resolve`, {
      method: 'POST',
      body: JSON.stringify({
        action,
        category_id: Number(categoryId) || 1,
        expression,
      }),
    });
    await load();
  }

  if (error) return <p className="empty">{error}</p>;
  if (empty && singletons.length > 0) {
    return (
      <Card>
        <p className="muted">{title} · singleton residual</p>
        <h2 className="display">Leftovers</h2>
        <p className="muted">
          {singletons.length} transactions did not form a cohort. Resolve them
          one at a time from the review API when you have a spare minute.
        </p>
        <p className="mono">{singletons.slice(0, 12).join(', ')}</p>
      </Card>
    );
  }
  if (empty) return <p className="empty">Queue is clear. Nothing to review.</p>;
  if (!current) return <p className="empty">Loading…</p>;

  return (
    <Card>
      <p className="muted">
        {title} · {index + 1} of {cohorts.length}
      </p>
      <h2 className="display">{current.cluster_key}</h2>
      <p className="mono">
        {current.size} transactions · {current.stage} · {current.source}
      </p>
      {coverage !== undefined && (
        <div className="coverage" aria-hidden>
          <span style={{ width: `${Math.round(coverage * 100)}%` }} />
        </div>
      )}
      <ul className="muted">
        {current.sample_descriptions.slice(0, 5).map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ul>
      <label className="field">
        <span className="hint">CEL (edit to split / specialize)</span>
        <textarea
          className="mono"
          rows={3}
          value={expression}
          onChange={(e) => setExpression(e.target.value)}
        />
      </label>
      <p className="hint">
        labelled FPs {current.labelled_false_positives} · dry-run size{' '}
        {current.size}
      </p>
      <label className="field">
        <span className="hint">Category id</span>
        <input
          ref={categoryRef}
          className="mono"
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
        />
      </label>
      <div className="actions">
        <Button primary onClick={() => void resolve('confirm')}>
          Confirm <span className="hint">c</span>
        </Button>
        <Button onClick={() => void resolve('change')}>
          Change <span className="hint">e</span>
        </Button>
        <Button onClick={() => void resolve('skip')}>
          Skip <span className="hint">s</span>
        </Button>
      </div>
    </Card>
  );
}
