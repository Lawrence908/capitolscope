/* ------------------------------------------------------------------ *
 * Formatting + palette constants for the design system (non-component
 * exports, kept separate so component files stay fast-refresh clean).
 * ------------------------------------------------------------------ */

// ---- formatters ----
export const fmtMoney = (n: number | null | undefined): string => {
  if (n == null) return '–';
  const abs = Math.abs(n);
  if (abs >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `$${(n / 1e3).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
};

/** Disclosed amount range from cents, e.g. 1500100/5000000 -> "$15,001–$50,000". */
export const fmtAmountRange = (
  minCents: number | null | undefined,
  maxCents: number | null | undefined,
): string => {
  const usd = (c: number) => `$${Math.round(c / 100).toLocaleString('en-US')}`;
  if (minCents == null && maxCents == null) return '–';
  if (minCents != null && maxCents != null && maxCents !== minCents) return `${usd(minCents)}–${usd(maxCents)}`;
  if (minCents != null && maxCents == null) return `${usd(minCents)}+`;
  return usd((minCents ?? maxCents) as number);
};

export const fmtPct = (n: number | null | undefined, digits = 1): string =>
  n == null ? '–' : `${(n * 100).toFixed(digits)}%`;

export const fmtSigned = (n: number | null | undefined): string => {
  if (n == null) return '–';
  const v = (n * 100).toFixed(1);
  return `${n >= 0 ? '+' : ''}${v}%`;
};

// ---- party ----
// Neutrality rule: parties are never color-coded (red is the brand accent).
// Charts that must separate parties use matched neutral grays plus labels.
export const partyMeta = (p: string | null | undefined) => {
  // Match single-letter codes (D/R/I) and full names (Democratic/Republican/
  // Independent) by first letter, so every disclosure format resolves.
  const key = (p || '').trim().toUpperCase();
  if (key.startsWith('D')) return { label: 'D', name: 'Democrat', color: '#4a4f57' };
  if (key.startsWith('R')) return { label: 'R', name: 'Republican', color: '#9ca1a9' };
  if (key.startsWith('I')) return { label: 'I', name: 'Independent', color: '#757b84' };
  return { label: '?', name: 'Unknown', color: '#c4c8ce' };
};

/** "R-AL", "D-NJ-5" style affiliation tag; falls back gracefully. */
export const affiliation = (
  party: string | null | undefined,
  state: string | null | undefined,
  district?: string | null,
): string => {
  const p = partyMeta(party).label;
  const parts = [p === '?' ? null : p, state || null, district || null].filter(Boolean);
  return parts.join('-');
};

// ---- factor fingerprint palette (stacked contributions out of 100) ----
// Bulletin: factors are an ink-to-gray ramp (stacked in FACTOR_ORDER), with
// brand red reserved for committee conflict, the most consequential factor.
export const FACTOR_COLORS: Record<string, string> = {
  edge: '#121417', // trading edge / alpha
  event: '#4a4f57', // pre-earnings positioning
  conflict: '#c5302a', // committee conflict
  cluster: '#757b84', // herding involvement
  lag: '#9ca1a9', // disclosure lag
  size: '#c4c8ce', // trade-size anomaly
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

// ---- disclosure timing ----
/** The STOCK Act deadline: transactions must be disclosed within 45 days. */
export const DISCLOSURE_LIMIT_DAYS = 45;

export const daysToDisclose = (
  transactionDate: string | null | undefined,
  notificationDate: string | null | undefined,
): number | null => {
  if (!transactionDate || !notificationDate) return null;
  const t = Date.parse(transactionDate);
  const n = Date.parse(notificationDate);
  if (Number.isNaN(t) || Number.isNaN(n)) return null;
  return Math.max(0, Math.round((n - t) / 86_400_000));
};

export const gaugeCaption = (days: number | null | undefined): string => {
  if (days == null) return 'Disclosure date unknown';
  if (days === 0) return 'Disclosed same day';
  if (days > DISCLOSURE_LIMIT_DAYS) return `${days - DISCLOSURE_LIMIT_DAYS} days late`;
  return `Disclosed in ${days} day${days === 1 ? '' : 's'}`;
};

// ---- asset category (trades without a listed ticker) ----
const ASSET_CATEGORY_LABEL: Record<string, string> = {
  STOCK: 'STOCK',
  ETF: 'ETF',
  MUTUAL_FUND: 'FUND',
  OPTION: 'OPTION',
  BOND: 'BOND',
  CASH: 'CASH',
  PRIVATE: 'PRIVATE',
  CRYPTOCURRENCY: 'CRYPTO',
  REAL_ESTATE: 'REAL ESTATE',
  REIT: 'REIT',
};

/** Short label for an asset with no ticker, e.g. "BOND", "PRIVATE". */
export const assetCategoryLabel = (assetType: string | null | undefined): string =>
  ASSET_CATEGORY_LABEL[(assetType || '').toUpperCase()] ?? 'OTHER ASSET';
