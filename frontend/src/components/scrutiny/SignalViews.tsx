import React from 'react';
import type {
  ClusterEvent,
  ConflictMember,
  TopConflict,
  DisclosureLag,
  DossierOrigin,
} from '../../types/scrutiny';
import {
  fmtMoney,
  fmtSigned,
  PartyTag,
  Eyebrow,
  partyMeta,
  NameButton,
  TickerButton,
  TradeStamp,
  StatTile,
} from '../ui';

/**
 * Signed return: sign plus arrow, never green/red. Negatives take the
 * accent, positives stay ink.
 */
export const SignedReturn: React.FC<{ value: number | null | undefined; className?: string }> = ({
  value,
  className = '',
}) =>
  value == null ? (
    <span className={`tabular-nums text-content-faint ${className}`}>–</span>
  ) : (
    <span className={`tabular-nums ${value < 0 ? 'text-accent' : 'text-content'} ${className}`}>
      {value < 0 ? '▼' : '▲'} {fmtSigned(value)}
    </span>
  );

/** BUY/SELL direction as a Bulletin stamp (filled vs outlined). */
const DirectionStamp: React.FC<{ direction: string; short?: boolean }> = ({ direction, short }) =>
  short ? (
    <span
      className={`inline-flex h-[18px] w-[18px] items-center justify-center border-2 border-content font-display text-[12px] font-extrabold leading-none ${
        direction === 'BUY' ? 'bg-content text-surface' : 'text-content'
      }`}
      title={direction === 'BUY' ? 'Bought' : 'Sold'}
    >
      {direction === 'BUY' ? 'B' : 'S'}
    </span>
  ) : (
    <TradeStamp type={direction === 'BUY' ? 'P' : 'S'} />
  );

type SelectFn = (name: string, origin?: DossierOrigin) => void;
type TickerFn = (ticker: string) => void;

// ---------- Clusters ----------
const PartyMix: React.FC<{ mix: Record<string, number> }> = ({ mix }) => (
  <div className="flex items-center gap-2">
    {Object.entries(mix).map(([p, n]) => {
      const m = partyMeta(p);
      return (
        <span key={p} className="font-ui text-[11px] font-semibold tabular-nums text-content-muted" title={m.name}>
          {m.label.charAt(0)}
          {n}
        </span>
      );
    })}
  </div>
);

export const ClusterFeed: React.FC<{
  clusters: ClusterEvent[];
  onSelectMember?: SelectFn;
  onSelectTicker?: TickerFn;
}> = ({ clusters, onSelectMember, onSelectTicker }) => (
  <div className="grid grid-cols-1 gap-x-6 sm:grid-cols-2 xl:grid-cols-3">
    {clusters.map((c, i) => (
      <div
        key={`${c.ticker}-${c.direction}-${c.window_start}-${i}`}
        className="border-b border-line py-4"
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <TickerButton
              ticker={c.ticker}
              onClick={onSelectTicker}
              className="font-display text-3xl font-extrabold leading-none text-content hover:text-accent"
            />
            <DirectionStamp direction={c.direction} />
          </div>
          <span
            className="font-ui text-xs font-semibold tabular-nums text-content-faint"
            title="base-popularity-weighted notability"
          >
            ★ {c.notability_score.toFixed(2)}
          </span>
        </div>

        <div className="mt-3 flex items-end gap-1.5">
          <span className="font-display text-5xl font-extrabold tabular-nums leading-none text-content">
            {c.member_count}
          </span>
          <span className="pb-0.5 font-ui text-xs text-content-faint">
            of {c.ticker_popularity} who trade it
          </span>
        </div>

        <div className="mt-3 flex items-center justify-between font-ui text-[11px] text-content-faint">
          <span className="tabular-nums">
            {c.window_start} → {c.window_end.slice(5)}
          </span>
          <PartyMix mix={c.party_breakdown} />
        </div>

        <div className="mt-3 flex items-center justify-between border-t border-line pt-3">
          <span className="truncate font-ui text-[12px] text-content-faint">
            led by{' '}
            <NameButton
              name={c.lead_member}
              onClick={onSelectMember}
              origin={{ tab: 'clusters', label: `the ${c.ticker} ${c.direction} cluster` }}
              className="font-semibold text-content"
            />
          </span>
          <SignedReturn value={c.avg_return_30d} className="font-ui text-sm font-semibold" />
        </div>
      </div>
    ))}
  </div>
);

// ---------- Conflicts ----------
export const ConflictsView: React.FC<{
  leaderboard: ConflictMember[];
  topConflicts: TopConflict[];
  onSelectMember?: SelectFn;
  onSelectTicker?: TickerFn;
}> = ({ leaderboard, topConflicts, onSelectMember, onSelectTicker }) => (
  <div className="grid grid-cols-1 gap-8 pt-4 lg:grid-cols-[1.1fr_1fr]">
    <div>
      <Eyebrow>Flagged members · by conflicted notional</Eyebrow>
      <div className="mt-3 divide-y divide-line border-t-2 border-content">
        {leaderboard.map((m) => (
          <div key={m.member} className="flex items-center gap-3 py-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <PartyTag party={m.party} />
                <NameButton
                  name={m.member}
                  onClick={onSelectMember}
                  origin={{ tab: 'conflicts', label: 'the conflicts view' }}
                  className="truncate font-ui font-bold text-content"
                />
              </div>
              <div className="mt-1 font-ui text-[11px] text-content-faint">
                {m.top_sectors.join(' · ')}
              </div>
            </div>
            <div className="text-right">
              <div className="font-display text-2xl font-extrabold leading-none tabular-nums text-content">
                {fmtMoney(m.conflicted_notional)}
              </div>
              <div className="mt-0.5 font-ui text-[11px] tabular-nums text-content-faint">
                {m.conflict_trades} trades
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>

    <div>
      <Eyebrow>Notable individual conflicts</Eyebrow>
      <div className="mt-3 divide-y divide-line border-t-2 border-content">
        {topConflicts.slice(0, 14).map((c, i) => (
          <div key={i} className="flex items-center gap-3 py-2.5">
            <DirectionStamp direction={c.direction} short />
            <TickerButton
              ticker={c.ticker}
              onClick={onSelectTicker}
              className="w-16 text-left font-display text-xl font-extrabold leading-none text-content hover:text-accent"
            />
            <div className="min-w-0 flex-1">
              <NameButton
                name={c.member}
                onClick={onSelectMember}
                origin={{ tab: 'conflicts', label: `the ${c.ticker} conflict` }}
                className="block truncate font-ui text-[13px] font-semibold text-content"
              />
              <div className="truncate font-ui text-[11px] text-content-faint">
                {c.sector} · {c.committee}
              </div>
            </div>
            <span className="font-display text-lg font-extrabold leading-none tabular-nums text-content">{fmtMoney(c.notional)}</span>
          </div>
        ))}
      </div>
    </div>
  </div>
);

// ---------- Disclosure lag ----------
export const LagView: React.FC<{ lag: DisclosureLag; onSelectMember?: SelectFn }> = ({
  lag,
  onSelectMember,
}) => {
  const maxLag = Math.max(...lag.worst_late_filers.map((f) => f.avg_lag_days), lag.stock_act_limit_days);
  const limitPct = (lag.stock_act_limit_days / maxLag) * 100;
  return (
    <div className="pt-2">
      <div className="grid grid-cols-2 sm:grid-cols-4">
        {[
          { k: 'Avg lag', v: lag.avg_lag_days == null ? '–' : `${lag.avg_lag_days}d`, tone: 'default' as const },
          { k: 'Median lag', v: lag.median_lag_days == null ? '–' : `${lag.median_lag_days}d`, tone: 'default' as const },
          { k: 'Late filings', v: lag.late_filings.toLocaleString(), tone: 'accent' as const },
          { k: 'Late share', v: lag.late_pct == null ? '–' : `${(lag.late_pct * 100).toFixed(1)}%`, tone: 'default' as const },
        ].map((s, i) => (
          <div key={s.k} className={`border-b border-line py-4 ${i > 0 ? 'sm:border-l sm:pl-4' : ''} ${i % 2 === 1 ? 'border-l pl-4' : ''}`}>
            <StatTile label={s.k} value={s.v} tone={s.tone} size="lg" />
          </div>
        ))}
      </div>

      <div className="mt-8">
        <Eyebrow>Worst late filers · vs the {lag.stock_act_limit_days}-day STOCK Act clock</Eyebrow>
        <div className="mt-2 flex items-center gap-4 font-ui text-[11px] text-content-faint">
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-5 bg-content" /> within the limit
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="hatch inline-block h-2.5 w-5" /> past the limit
          </span>
        </div>
        <div className="mt-3 space-y-2.5">
          {lag.worst_late_filers.map((f) => {
            const totalPct = (f.avg_lag_days / maxLag) * 100;
            const onTimePct = Math.min(totalPct, limitPct);
            return (
              <div key={f.member} className="flex items-center gap-3">
                <div className="flex w-52 shrink-0 items-center gap-2 truncate">
                  <PartyTag party={f.party} />
                  <NameButton
                    name={f.member}
                    onClick={onSelectMember}
                    origin={{ tab: 'lag', label: 'the disclosure-lag view' }}
                    className="truncate font-ui text-[13px] font-semibold text-content"
                  />
                </div>
                <div className="relative h-5 flex-1 bg-surface-inset">
                  <div className="absolute inset-y-0 left-0 bg-content" style={{ width: `${onTimePct}%` }} />
                  {totalPct > limitPct && (
                    <div
                      className="hatch absolute inset-y-0"
                      style={{ left: `${limitPct}%`, width: `${totalPct - limitPct}%` }}
                    />
                  )}
                  {/* 45-day limit marker */}
                  <div
                    className="absolute -bottom-1 -top-1 w-0.5 bg-accent"
                    style={{ left: `${limitPct}%` }}
                    title={`${lag.stock_act_limit_days}-day limit`}
                  />
                </div>
                <span className="w-24 shrink-0 text-right font-ui text-[11px] tabular-nums text-content-muted">
                  <span className="font-bold text-content">{f.avg_lag_days}d</span> · {f.late}/{f.total}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
