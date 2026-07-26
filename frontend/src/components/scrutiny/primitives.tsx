import React from 'react';

// ---- formatters ----
export const fmtMoney = (n: number | null | undefined): string => {
  if (n == null) return '—';
  const abs = Math.abs(n);
  if (abs >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `$${(n / 1e3).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
};

export const fmtPct = (n: number | null | undefined, digits = 1): string =>
  n == null ? '—' : `${(n * 100).toFixed(digits)}%`;

export const fmtSigned = (n: number | null | undefined): string => {
  if (n == null) return '—';
  const v = (n * 100).toFixed(1);
  return `${n >= 0 ? '+' : ''}${v}%`;
};

// ---- party ----
export const partyMeta = (p: string | null | undefined) => {
  const key = (p || '').toUpperCase();
  if (key === 'D') return { label: 'DEM', color: '#7aa8d6' };
  if (key === 'R') return { label: 'REP', color: '#d6707b' };
  if (key === 'I') return { label: 'IND', color: '#cca85a' };
  return { label: '—', color: '#90a29d' };
};

export const PartyTag: React.FC<{ party: string | null | undefined }> = ({ party }) => {
  const m = partyMeta(party);
  return (
    <span
      className="font-data text-[10px] tracking-[0.14em] px-1.5 py-0.5 rounded-sm"
      style={{ color: m.color, background: `${m.color}1a` }}
    >
      {m.label}
    </span>
  );
};

// ---- factor fingerprint bar (stacked contributions out of 100) ----
export const FACTOR_COLORS: Record<string, string> = {
  edge: '#43a897', // verdigris — trading edge / alpha
  conflict: '#d6707b', // oxblood — committee conflict
  cluster: '#7aa8d6', // steel — herding involvement
  lag: '#cca85a', // brass — disclosure lag
};

export const FACTOR_LABELS: Record<string, string> = {
  edge: 'Edge',
  conflict: 'Conflict',
  cluster: 'Cluster',
  lag: 'Lag',
};

export const FactorBar: React.FC<{
  contributions: Record<string, number>;
  height?: number;
}> = ({ contributions, height = 8 }) => {
  const order = ['edge', 'conflict', 'cluster', 'lag'];
  return (
    <div
      className="flex w-full overflow-hidden rounded-[3px] bg-ink-700"
      style={{ height }}
      role="img"
      aria-label="factor contribution breakdown"
    >
      {order.map((k) => {
        const pct = contributions[k] || 0;
        return (
          <div
            key={k}
            style={{ width: `${pct}%`, background: FACTOR_COLORS[k] }}
            title={`${FACTOR_LABELS[k]}: ${pct.toFixed(1)} pts`}
          />
        );
      })}
    </div>
  );
};

// ---- percentile meter (single factor) ----
export const Meter: React.FC<{ value: number; color: string }> = ({ value, color }) => (
  <div className="h-1.5 w-full rounded-full bg-ink-700 overflow-hidden">
    <div
      className="h-full rounded-full transition-[width] duration-500"
      style={{ width: `${Math.max(2, value * 100)}%`, background: color }}
    />
  </div>
);

// ---- clickable member name (deep-link to dossier) ----
export const NameButton: React.FC<{
  name: string;
  onClick?: (name: string) => void;
  className?: string;
}> = ({ name, onClick, className = '' }) =>
  onClick ? (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onClick(name);
      }}
      className={`text-left transition-colors hover:text-verdigris-400 hover:underline decoration-verdigris-500/50 underline-offset-2 ${className}`}
      title={`Open ${name}'s dossier`}
    >
      {name}
    </button>
  ) : (
    <span className={className}>{name}</span>
  );

// ---- small mono label ----
export const Eyebrow: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className = '',
}) => (
  <span
    className={`font-data text-[11px] tracking-[0.18em] uppercase text-verdigris-500 ${className}`}
  >
    {children}
  </span>
);
