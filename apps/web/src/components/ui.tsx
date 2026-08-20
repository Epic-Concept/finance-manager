import type { ReactNode } from 'react';

export function Card({ children }: { children: ReactNode }) {
  return <section className="card">{children}</section>;
}

export function Button({
  children,
  primary = false,
  onClick,
  type = 'button',
}: {
  children: ReactNode;
  primary?: boolean;
  onClick?: () => void;
  type?: 'button' | 'submit';
}) {
  return (
    <button type={type} className={primary ? 'btn primary' : 'btn'} onClick={onClick}>
      {children}
    </button>
  );
}

export function TierMark({ strength }: { strength: number }) {
  const filled = Math.max(0, Math.min(4, strength + 1));
  const dots = `${'·'.repeat(filled)}${' '.repeat(4 - filled)}`;
  const labels = ['NONE', 'WEAK', 'STRONG', 'PROOF'];
  return (
    <span className="tier" data-testid="tier-mark">
      {dots} {labels[Math.min(3, strength)] ?? 'NONE'}
    </span>
  );
}

export function StatLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <span className="muted">{label}</span>
      <span className="mono">{value}</span>
    </div>
  );
}

export function LedgerTable({
  headers,
  rows,
}: {
  headers: string[];
  rows: string[][];
}) {
  if (rows.length === 0) {
    return <p className="empty">Nothing here yet.</p>;
  }
  return (
    <table className="ledger">
      <thead>
        <tr>
          {headers.map((h) => (
            <th key={h}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i}>
            {row.map((cell, j) => (
              <td key={j} className={j === 0 ? 'mono' : undefined}>
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
