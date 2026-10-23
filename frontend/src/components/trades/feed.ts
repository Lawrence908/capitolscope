/* ------------------------------------------------------------------ *
 * Non-component helpers for the trade feeds, trade permalink and ticker
 * page (kept out of component files so fast refresh stays clean).
 * ------------------------------------------------------------------ */
import type { CongressionalTrade } from '../../types';

/** Square Bulletin input: 2px ink box, red on focus. */
export const BULLETIN_INPUT =
  'w-full rounded-none border-2 border-content bg-surface px-3 py-2 font-ui text-sm text-content placeholder:text-content-faint focus:border-accent focus:outline-none focus:ring-0';

/** Small caps label above a filter control. */
export const BULLETIN_LABEL = 'mb-1 block font-ui text-[11px] font-semibold uppercase tracking-[0.08em] text-content-faint';

const parseIso = (iso: string | null | undefined): Date | null => {
  if (!iso) return null;
  const d = new Date(`${iso.slice(0, 10)}T00:00:00`);
  return Number.isNaN(d.getTime()) ? null : d;
};

/** "Oct 21, 2026"; empty string when unknown. */
export const longDate = (iso: string | null | undefined): string => {
  const d = parseIso(iso);
  return d ? d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '';
};

/** "Tuesday" / "Oct 21" style weekday for feed date headers. */
export const weekday = (iso: string | null | undefined): string => {
  const d = parseIso(iso);
  return d ? d.toLocaleDateString('en-US', { weekday: 'long' }) : '';
};

export const todayIso = (): string => {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
};

/** Future-dated transactions are source parse errors; feeds never show them. */
export const isFutureDated = (t: Pick<CongressionalTrade, 'transaction_date'>, today = todayIso()): boolean =>
  !!t.transaction_date && t.transaction_date.slice(0, 10) > today;

export const memberTitle = (chamber: string | null | undefined): string => {
  const c = (chamber || '').toLowerCase();
  return c.startsWith('s') ? 'Sen.' : c.startsWith('h') ? 'Rep.' : '';
};

export const OWNER_LABEL: Record<string, string> = {
  SP: 'Spouse',
  JT: 'Joint',
  DC: 'Dependent child',
  C: 'Self',
};

export interface DateGroup<T> {
  date: string;
  items: T[];
}

/**
 * Consecutive runs of trades sharing a date (the list is already sorted by
 * that date server-side, so grouping preserves order and pagination).
 */
export const groupByDate = <T extends CongressionalTrade>(
  trades: T[],
  field: 'notification_date' | 'transaction_date',
): DateGroup<T>[] => {
  const out: DateGroup<T>[] = [];
  for (const t of trades) {
    const key = (t[field] || '').slice(0, 10);
    const last = out[out.length - 1];
    if (last && last.date === key) last.items.push(t);
    else out.push({ date: key, items: [t] });
  }
  return out;
};

/** "https://x.com/intent/post?text=...&url=..." */
export const xIntentUrl = (text: string, url: string): string =>
  `https://x.com/intent/post?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`;
