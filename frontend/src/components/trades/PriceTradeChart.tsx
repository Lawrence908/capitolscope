import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { CongressionalTrade } from '../../types';
import { longDate } from './feed';

type Range = '1y' | '5y' | 'all';
const RANGES: { id: Range; label: string; years: number | null }[] = [
  { id: '1y', label: '1Y', years: 1 },
  { id: '5y', label: '5Y', years: 5 },
  { id: 'all', label: 'All', years: null },
];

const HEIGHT = 260;
const PAD = { top: 12, right: 52, bottom: 26, left: 8 };

const usd = (n: number) => `$${Math.round(n).toLocaleString('en-US')}`;

/** Width of an element, tracked with ResizeObserver (so text never scales). */
const useWidth = (): [React.RefObject<HTMLDivElement>, number] => {
  const ref = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(720);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    setW(el.clientWidth || 720);
    if (typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver((entries) => {
      const cw = entries[0]?.contentRect.width;
      if (cw) setW(cw);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, w];
};

interface Marker {
  key: string;
  date: string;
  x: number;
  y: number;
  kind: 'buy' | 'sell' | 'other';
  trades: CongressionalTrade[];
}

/**
 * Daily close (whole dollars) as an ink line, with each disclosed
 * congressional trade marked on its transaction date: filled for buys,
 * outlined for sells. Click a marker to open the trade.
 */
const PriceTradeChart: React.FC<{
  prices: [string, number][];
  trades: CongressionalTrade[];
  className?: string;
}> = ({ prices, trades, className = '' }) => {
  const navigate = useNavigate();
  const [ref, width] = useWidth();
  // Default to 5Y unless every trade is older than that window.
  const [range, setRange] = useState<Range>(() => {
    const lastPrice = prices[prices.length - 1]?.[0];
    if (!lastPrice) return 'all';
    const cutoff = `${Number(lastPrice.slice(0, 4)) - 5}${lastPrice.slice(4, 10)}`;
    return trades.some((t) => (t.transaction_date || '') >= cutoff) ? '5y' : 'all';
  });
  const [hover, setHover] = useState<number | null>(null);

  const series = useMemo(() => {
    const years = RANGES.find((r) => r.id === range)?.years;
    if (!years || prices.length === 0) return prices;
    const last = new Date(`${prices[prices.length - 1][0]}T00:00:00`);
    last.setFullYear(last.getFullYear() - years);
    const cutoff = last.toISOString().slice(0, 10);
    return prices.filter(([d]) => d >= cutoff);
  }, [prices, range]);

  const geo = useMemo(() => {
    if (series.length < 2) return null;
    const innerW = Math.max(10, width - PAD.left - PAD.right);
    const innerH = HEIGHT - PAD.top - PAD.bottom;
    const t0 = Date.parse(series[0][0]);
    const t1 = Date.parse(series[series.length - 1][0]);
    const closes = series.map(([, c]) => c);
    let lo = Math.min(...closes);
    let hi = Math.max(...closes);
    if (hi === lo) {
      hi += 1;
      lo = Math.max(0, lo - 1);
    }
    const padY = (hi - lo) * 0.06;
    lo = Math.max(0, lo - padY);
    hi += padY;
    const x = (iso: string) => PAD.left + ((Date.parse(iso) - t0) / Math.max(1, t1 - t0)) * innerW;
    const y = (v: number) => PAD.top + (1 - (v - lo) / (hi - lo)) * innerH;
    const path = series.map(([d, c], i) => `${i ? 'L' : 'M'}${x(d).toFixed(1)},${y(c).toFixed(1)}`).join('');

    // Close on or before a date (series is ascending).
    const closeAt = (iso: string): number | null => {
      let loI = 0;
      let hiI = series.length - 1;
      if (iso < series[0][0]) return null;
      while (loI < hiI) {
        const mid = Math.ceil((loI + hiI) / 2);
        if (series[mid][0] <= iso) loI = mid;
        else hiI = mid - 1;
      }
      return series[loI][1];
    };

    const groups = new Map<string, Marker>();
    for (const t of trades) {
      const d = (t.transaction_date || '').slice(0, 10);
      if (!d || d < series[0][0] || d > series[series.length - 1][0]) continue;
      const c = closeAt(d);
      if (c == null) continue;
      const tt = (t.transaction_type || '').toUpperCase();
      const kind: Marker['kind'] = tt.startsWith('P') ? 'buy' : tt.startsWith('S') ? 'sell' : 'other';
      const key = `${d}-${kind}`;
      const g = groups.get(key);
      if (g) g.trades.push(t);
      else groups.set(key, { key, date: d, x: x(d), y: y(c), kind, trades: [t] });
    }

    // Y ticks: 4 evenly spaced whole-dollar levels.
    const yTicks = [0, 1, 2, 3].map((i) => lo + ((hi - lo) * i) / 3);
    // X ticks: one per year (or per quarter for short ranges).
    const startYear = new Date(series[0][0]).getUTCFullYear();
    const endYear = new Date(series[series.length - 1][0]).getUTCFullYear();
    const span = endYear - startYear;
    const step = span > 8 ? 2 : 1;
    const xTicks: { x: number; label: string }[] = [];
    if (span >= 1) {
      for (let yr = startYear + 1; yr <= endYear; yr += step) xTicks.push({ x: x(`${yr}-01-01`), label: String(yr) });
    } else {
      xTicks.push({ x: x(series[0][0]), label: longDate(series[0][0]) });
    }

    return { innerW, innerH, x, y, path, markers: [...groups.values()], yTicks, xTicks };
  }, [series, trades, width]);

  const last = series[series.length - 1];
  const hovered = hover != null ? series[hover] : null;

  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!geo || series.length < 2) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const px = e.clientX - rect.left;
    const frac = Math.min(1, Math.max(0, (px - PAD.left) / geo.innerW));
    const t0 = Date.parse(series[0][0]);
    const t1 = Date.parse(series[series.length - 1][0]);
    const target = t0 + frac * (t1 - t0);
    let best = 0;
    let bestD = Infinity;
    // Linear scan is fine for <= ~1500 points.
    for (let i = 0; i < series.length; i++) {
      const dd = Math.abs(Date.parse(series[i][0]) - target);
      if (dd < bestD) {
        bestD = dd;
        best = i;
      }
    }
    setHover(best);
  };

  return (
    <div className={className}>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <p className="font-ui text-sm text-content-muted" aria-live="polite">
          {hovered ? (
            <>
              <span className="font-display text-xl font-extrabold text-content">{usd(hovered[1])}</span> close on {longDate(hovered[0])}
            </>
          ) : last ? (
            <>
              <span className="font-display text-xl font-extrabold text-content">{usd(last[1])}</span> last close, {longDate(last[0])}
            </>
          ) : null}
        </p>
        <div className="flex gap-1" role="group" aria-label="Chart range">
          {RANGES.map((r) => (
            <button
              key={r.id}
              type="button"
              aria-pressed={range === r.id}
              onClick={() => setRange(r.id)}
              className={`border-2 px-2 py-0.5 font-display text-sm font-extrabold transition-colors ${
                range === r.id ? 'border-content bg-content text-surface' : 'border-line text-content-muted hover:border-content'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      <div ref={ref} className="mt-2 w-full">
        {!geo ? (
          <div className="flex h-40 items-center justify-center bg-surface-inset font-ui text-sm text-content-faint">
            No price history for this range.
          </div>
        ) : (
          <svg
            width={width}
            height={HEIGHT}
            viewBox={`0 0 ${width} ${HEIGHT}`}
            role="img"
            aria-label={`Daily closing price${last ? `, last ${usd(last[1])}` : ''}, with ${geo.markers.length} trade markers`}
            className="block"
            onMouseMove={onMove}
            onMouseLeave={() => setHover(null)}
          >
            {geo.yTicks.map((v, i) => (
              <g key={i}>
                <line x1={PAD.left} x2={PAD.left + geo.innerW} y1={geo.y(v)} y2={geo.y(v)} stroke="var(--line)" strokeWidth={1} />
                <text x={PAD.left + geo.innerW + 6} y={geo.y(v) + 4} fontSize={11} fill="var(--content-faint)" fontFamily="Libre Franklin, sans-serif">
                  {usd(v)}
                </text>
              </g>
            ))}
            {geo.xTicks.map((t) => (
              <text
                key={t.label}
                x={t.x}
                y={HEIGHT - 6}
                fontSize={11}
                textAnchor="middle"
                fill="var(--content-faint)"
                fontFamily="Libre Franklin, sans-serif"
              >
                {t.label}
              </text>
            ))}
            <path d={geo.path} fill="none" stroke="var(--content)" strokeWidth={1.75} strokeLinejoin="round" />
            {hovered && (
              <line
                x1={geo.x(hovered[0])}
                x2={geo.x(hovered[0])}
                y1={PAD.top}
                y2={PAD.top + geo.innerH}
                stroke="var(--content-faint)"
                strokeDasharray="3 3"
              />
            )}
            {geo.markers.map((m) => {
              const n = m.trades.length;
              const label = `${m.kind === 'buy' ? 'Bought' : m.kind === 'sell' ? 'Sold' : 'Exchanged'} ${longDate(m.date)}: ${n} trade${
                n === 1 ? '' : 's'
              } (${[...new Set(m.trades.map((t) => t.member_name).filter(Boolean))].slice(0, 3).join(', ')})`;
              const r = n > 1 ? 5.5 : 4.5;
              const common = {
                role: 'link',
                tabIndex: 0,
                style: { cursor: 'pointer' },
                onClick: () => navigate(`/t/${m.trades[0].id}`),
                onKeyDown: (e: React.KeyboardEvent) => {
                  if (e.key === 'Enter') navigate(`/t/${m.trades[0].id}`);
                },
              } as const;
              return m.kind === 'other' ? (
                <rect
                  key={m.key}
                  {...common}
                  x={m.x - r}
                  y={m.y - r}
                  width={r * 2}
                  height={r * 2}
                  fill="var(--surface)"
                  stroke="var(--content)"
                  strokeWidth={2}
                >
                  <title>{label}</title>
                </rect>
              ) : (
                <circle
                  key={m.key}
                  {...common}
                  cx={m.x}
                  cy={m.y}
                  r={r}
                  fill={m.kind === 'buy' ? 'var(--content)' : 'var(--surface)'}
                  stroke="var(--content)"
                  strokeWidth={2}
                >
                  <title>{label}</title>
                </circle>
              );
            })}
          </svg>
        )}
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1 font-ui text-xs text-content-muted">
        <span className="inline-flex items-center gap-1.5">
          <svg width="12" height="12" aria-hidden="true">
            <circle cx="6" cy="6" r="4.5" fill="var(--content)" stroke="var(--content)" strokeWidth="1.5" />
          </svg>
          Bought
        </span>
        <span className="inline-flex items-center gap-1.5">
          <svg width="12" height="12" aria-hidden="true">
            <circle cx="6" cy="6" r="4.5" fill="var(--surface)" stroke="var(--content)" strokeWidth="1.5" />
          </svg>
          Sold
        </span>
        <span className="text-content-faint">
          Daily close in whole dollars. Markers sit on the trade date; larger markers mean several trades that day.
        </span>
      </div>
    </div>
  );
};

export default PriceTradeChart;
