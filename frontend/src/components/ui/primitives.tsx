import React from 'react';
import type { DossierOrigin } from '../../types/scrutiny';
import { partyMeta, FACTOR_COLORS, FACTOR_LABELS, FACTOR_ORDER } from './format';

/* ------------------------------------------------------------------ *
 * Shared design-system components — the "Scrutiny" oversight-dossier
 * language, made theme-aware (light + dark) via semantic tokens.
 * All bar/meter tracks use `bg-surface-inset`; accents use `text-accent`
 * so everything works in both themes. Consumed site-wide.
 * (Formatters + palette constants live in ./format.)
 * ------------------------------------------------------------------ */

// ---- party badge ----
export const PartyTag: React.FC<{ party: string | null | undefined; className?: string }> = ({
  party,
  className = '',
}) => {
  const m = partyMeta(party);
  return (
    <span
      className={`font-data text-[10px] tracking-[0.14em] px-1.5 py-0.5 rounded-sm ${className}`}
      style={{ color: m.color, background: `${m.color}1a` }}
    >
      {m.label}
    </span>
  );
};

// ---- factor fingerprint bar (stacked contributions out of 100) ----
export const FactorBar: React.FC<{
  contributions: Record<string, number>;
  height?: number;
}> = ({ contributions, height = 8 }) => (
  <div
    className="flex w-full overflow-hidden rounded-[3px] bg-surface-inset"
    style={{ height }}
    role="img"
    aria-label="factor contribution breakdown"
  >
    {FACTOR_ORDER.map((k) => {
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

// ---- percentile / ratio meter (single value 0..1) ----
export const Meter: React.FC<{ value: number; color?: string; height?: number }> = ({
  value,
  color,
  height = 6,
}) => (
  <div className="w-full rounded-full bg-surface-inset overflow-hidden" style={{ height }}>
    <div
      className="h-full rounded-full transition-[width] duration-500"
      style={{
        width: `${Math.max(2, Math.min(1, value) * 100)}%`,
        background: color || 'var(--accent)',
      }}
    />
  </div>
);

// ---- clickable member name (deep-link to dossier) ----
export const NameButton: React.FC<{
  name: string;
  onClick?: (name: string, origin?: DossierOrigin) => void;
  origin?: DossierOrigin;
  className?: string;
}> = ({ name, onClick, origin, className = '' }) =>
  onClick ? (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onClick(name, origin);
      }}
      className={`text-left transition-colors hover:text-accent-strong hover:underline decoration-accent underline-offset-2 ${className}`}
      title={`Open ${name}'s dossier`}
    >
      {name}
    </button>
  ) : (
    <span className={className}>{name}</span>
  );

// ---- clickable ticker (opens the ticker drawer) ----
export const TickerButton: React.FC<{
  ticker: string;
  onClick?: (ticker: string) => void;
  className?: string;
}> = ({ ticker, onClick, className = '' }) =>
  onClick ? (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onClick(ticker);
      }}
      className={`transition-colors hover:text-accent-strong ${className}`}
      title={`${ticker} congressional flow`}
    >
      {ticker}
    </button>
  ) : (
    <span className={className}>{ticker}</span>
  );

// ---- small mono eyebrow label ----
export const Eyebrow: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className = '',
}) => (
  <span className={`font-data text-[11px] tracking-[0.18em] uppercase text-accent ${className}`}>
    {children}
  </span>
);
