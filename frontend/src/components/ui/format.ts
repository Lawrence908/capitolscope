/* ------------------------------------------------------------------ *
 * Formatting + palette constants for the design system (non-component
 * exports, kept separate so component files stay fast-refresh clean).
 * ------------------------------------------------------------------ */

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
  // Match single-letter codes (D/R/I) and full names (Democratic/Republican/
  // Independent) by first letter, so every disclosure format resolves.
  const key = (p || '').trim().toUpperCase();
  if (key.startsWith('D')) return { label: 'DEM', color: '#7aa8d6' };
  if (key.startsWith('R')) return { label: 'REP', color: '#d6707b' };
  if (key.startsWith('I')) return { label: 'IND', color: '#cca85a' };
  return { label: '—', color: '#90a29d' };
};

// ---- factor fingerprint palette (stacked contributions out of 100) ----
export const FACTOR_COLORS: Record<string, string> = {
  edge: '#43a897', // verdigris — trading edge / alpha
  event: '#e0906a', // coral — pre-earnings positioning
  conflict: '#d6707b', // oxblood — committee conflict
  cluster: '#7aa8d6', // steel — herding involvement
  lag: '#cca85a', // brass — disclosure lag
  size: '#9d8bc4', // amethyst — trade-size anomaly
};

export const FACTOR_LABELS: Record<string, string> = {
  edge: 'Edge',
  event: 'Pre-earnings',
  conflict: 'Conflict',
  cluster: 'Cluster',
  lag: 'Lag',
  size: 'Size',
};

export const FACTOR_ORDER = ['edge', 'event', 'conflict', 'cluster', 'lag', 'size'];
