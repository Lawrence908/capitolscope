import React from 'react';
import { DISCLOSURE_LIMIT_DAYS, gaugeCaption } from './format';

/* ------------------------------------------------------------------ *
 * Bulletin primitives: the disclosure gauge, buy/sell stamps and the
 * hatch mark. Theme-aware via the semantic tokens in index.css.
 * ------------------------------------------------------------------ */

// Dial geometry: a 180 degree fuel gauge. 0 to 45 days fills the first 150
// degrees; the last 30 degrees is the red "late" zone. Late filings move
// into the red zone on a scale that pegs at LATE_PEG_DAYS past the limit.
const ON_TIME_SWEEP = 150;
const LATE_PEG_DAYS = 180;

const angleForDays = (days: number): number => {
  if (days <= DISCLOSURE_LIMIT_DAYS) {
    return 180 - (Math.max(0, days) / DISCLOSURE_LIMIT_DAYS) * ON_TIME_SWEEP;
  }
  const over = Math.min(1, (days - DISCLOSURE_LIMIT_DAYS) / LATE_PEG_DAYS);
  return 180 - ON_TIME_SWEEP - over * (180 - ON_TIME_SWEEP);
};

const point = (cx: number, cy: number, r: number, deg: number) => {
  const rad = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy - r * Math.sin(rad) };
};

const arc = (cx: number, cy: number, r: number, fromDeg: number, toDeg: number) => {
  const a = point(cx, cy, r, fromDeg);
  const b = point(cx, cy, r, toDeg);
  const large = Math.abs(fromDeg - toDeg) > 180 ? 1 : 0;
  // Sweep clockwise on screen (decreasing math angle).
  return `M${a.x.toFixed(2)},${a.y.toFixed(2)} A${r},${r} 0 ${large} 1 ${b.x.toFixed(2)},${b.y.toFixed(2)}`;
};

type GaugeSize = 'xs' | 'sm' | 'md' | 'lg';

const SIZES: Record<GaugeSize, { w: number; r: number; stroke: number; ticks: boolean; labels: boolean }> = {
  xs: { w: 44, r: 18, stroke: 4, ticks: false, labels: false },
  sm: { w: 64, r: 26, stroke: 5, ticks: true, labels: false },
  md: { w: 140, r: 58, stroke: 9, ticks: true, labels: true },
  lg: { w: 260, r: 108, stroke: 14, ticks: true, labels: true },
};

/**
 * Fuel-style gauge for days from trade to disclosure. The needle sweeps
 * 0 to 45 days; anything past the legal limit pegs into the red zone and
 * the needle turns red.
 */
export const DisclosureGauge: React.FC<{
  days: number | null | undefined;
  size?: GaugeSize;
  /** Big centred value under the dial (md/lg only). */
  showValue?: boolean;
  /** Override the value text (e.g. "10 days" median). */
  valueLabel?: React.ReactNode;
  className?: string;
}> = ({ days, size = 'sm', showValue = size === 'md' || size === 'lg', valueLabel, className = '' }) => {
  const g = SIZES[size];
  const pad = g.stroke / 2 + (g.labels ? 14 : 2);
  const cx = g.w / 2;
  const cy = g.r + pad;
  const h = cy + (g.labels ? 16 : g.stroke / 2 + 2);
  const known = days != null;
  const late = known && (days as number) > DISCLOSURE_LIMIT_DAYS;
  const needleDeg = known ? angleForDays(days as number) : 180;
  const limitDeg = 180 - ON_TIME_SWEEP;
  const tip = point(cx, cy, g.r - g.stroke * 0.2, needleDeg);
  const label = gaugeCaption(days);

  return (
    <span className={`inline-flex flex-col items-center ${className}`}>
      <svg
        width={g.w}
        height={h}
        viewBox={`0 0 ${g.w} ${h}`}
        role="img"
        aria-label={label}
        className="block overflow-visible"
      >
        <title>{label}</title>
        {/* on-time track */}
        <path d={arc(cx, cy, g.r, 180, limitDeg)} fill="none" stroke="var(--surface-inset)" strokeWidth={g.stroke} />
        {/* late zone, always visible like a fuel gauge's red band */}
        <path d={arc(cx, cy, g.r, limitDeg, 0)} fill="none" stroke="var(--accent)" strokeOpacity={0.28} strokeWidth={g.stroke} />
        {/* filled progress */}
        {known && (days as number) > 0 && (
          <path
            d={arc(cx, cy, g.r, 180, Math.max(needleDeg, limitDeg))}
            fill="none"
            stroke="var(--content)"
            strokeWidth={g.stroke}
          />
        )}
        {late && (
          <path d={arc(cx, cy, g.r, limitDeg, needleDeg)} fill="none" stroke="var(--accent)" strokeWidth={g.stroke} />
        )}
        {/* ticks at 0, 15, 30, 45 days */}
        {g.ticks &&
          [0, 15, 30, 45].map((d) => {
            const deg = angleForDays(d);
            const a = point(cx, cy, g.r + g.stroke / 2 + 1, deg);
            const b = point(cx, cy, g.r + g.stroke / 2 + (d === 45 ? 7 : 4), deg);
            return (
              <line
                key={d}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke={d === 45 ? 'var(--accent)' : 'var(--content-faint)'}
                strokeWidth={d === 45 ? 2 : 1}
              />
            );
          })}
        {g.labels && (
          <>
            <text x={point(cx, cy, g.r, 180).x} y={cy + 13} textAnchor="middle" fontSize={10} fill="var(--content-faint)" fontFamily="Libre Franklin, sans-serif">
              0
            </text>
            <text
              x={point(cx, cy, g.r + g.stroke + 10, limitDeg).x}
              y={point(cx, cy, g.r + g.stroke + 10, limitDeg).y}
              textAnchor="middle"
              fontSize={10}
              fontWeight={700}
              fill="var(--accent)"
              fontFamily="Libre Franklin, sans-serif"
            >
              45
            </text>
            <text x={point(cx, cy, g.r, 0).x} y={cy + 13} textAnchor="middle" fontSize={10} fontWeight={700} fill="var(--accent)" fontFamily="Libre Franklin, sans-serif">
              LATE
            </text>
          </>
        )}
        {/* needle + hub */}
        {known && (
          <>
            <line
              x1={cx}
              y1={cy}
              x2={tip.x}
              y2={tip.y}
              stroke={late ? 'var(--accent)' : 'var(--content)'}
              strokeWidth={Math.max(1.5, g.stroke * 0.32)}
              strokeLinecap="square"
            />
            <circle cx={cx} cy={cy} r={Math.max(2.5, g.stroke * 0.5)} fill={late ? 'var(--accent)' : 'var(--content)'} />
          </>
        )}
      </svg>
      {showValue && (
        <span
          className={`-mt-1 font-display font-extrabold leading-none tabular-nums ${
            size === 'lg' ? 'text-5xl' : 'text-2xl'
          } ${late ? 'text-accent' : 'text-content'}`}
        >
          {valueLabel ?? (known ? `${days} day${days === 1 ? '' : 's'}` : '—')}
        </span>
      )}
    </span>
  );
};

/** BOUGHT is a filled ink box, SOLD an outlined one. Never red/green. */
export const TradeStamp: React.FC<{ type: string | null | undefined; className?: string }> = ({
  type,
  className = '',
}) => {
  const t = (type || '').trim().toUpperCase();
  const label = t.startsWith('P') ? 'BOUGHT' : t.startsWith('S') ? 'SOLD' : t.startsWith('E') ? 'EXCHANGED' : '—';
  const filled = label === 'BOUGHT';
  return (
    <span
      className={`inline-block border-2 border-content px-1.5 py-px font-display text-[13px] font-extrabold uppercase leading-tight tracking-[0.04em] ${
        filled ? 'bg-content text-surface' : 'text-content'
      } ${className}`}
    >
      {label}
    </span>
  );
};

/** Hatched block: the one mark that means "filed after the 45-day limit". */
export const HatchMark: React.FC<{ className?: string; title?: string }> = ({ className = 'h-3 w-6', title }) => (
  <span className={`hatch inline-block align-middle ${className}`} role={title ? 'img' : undefined} aria-label={title} />
);
