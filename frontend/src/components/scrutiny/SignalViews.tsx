import React from 'react';
import type {
  ClusterEvent,
  ConflictMember,
  TopConflict,
  DisclosureLag,
} from '../../types/scrutiny';
import { fmtMoney, fmtSigned, PartyTag, Eyebrow, partyMeta, NameButton } from './primitives';

const retColor = (r: number | null) =>
  r == null ? '#90a29d' : r >= 0 ? '#43a897' : '#d6707b';

type SelectFn = (name: string) => void;

// ---------- Clusters ----------
const PartyMix: React.FC<{ mix: Record<string, number> }> = ({ mix }) => (
  <div className="flex items-center gap-1">
    {Object.entries(mix).map(([p, n]) => {
      const m = partyMeta(p);
      return (
        <span key={p} className="font-data text-[10px] tabular-nums" style={{ color: m.color }}>
          {m.label.charAt(0)}
          {n}
        </span>
      );
    })}
  </div>
);

export const ClusterFeed: React.FC<{ clusters: ClusterEvent[]; onSelectMember?: SelectFn }> = ({
  clusters,
  onSelectMember,
}) => (
  <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2 xl:grid-cols-3">
    {clusters.map((c, i) => (
      <div
        key={`${c.ticker}-${c.direction}-${c.window_start}-${i}`}
        className="rounded-md border border-ink-600 bg-ink-850 p-4 transition-colors hover:border-verdigris-600"
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <span className="font-data text-lg font-600 tracking-tight text-fog-200">{c.ticker}</span>
            <span
              className="font-data text-[10px] tracking-[0.1em] px-1.5 py-0.5 rounded-sm"
              style={{
                color: c.direction === 'BUY' ? '#43a897' : '#d6707b',
                background: c.direction === 'BUY' ? '#16302b' : '#331a1e',
              }}
            >
              {c.direction}
            </span>
          </div>
          <span
            className="font-data text-xs tabular-nums text-fog-500"
            title="base-popularity-weighted notability"
          >
            ★ {c.notability_score.toFixed(2)}
          </span>
        </div>

        <div className="mt-3 flex items-end gap-1.5">
          <span className="font-data text-3xl font-500 tabular-nums leading-none text-fog-200">
            {c.member_count}
          </span>
          <span className="pb-0.5 font-ui text-xs text-fog-500">
            of {c.ticker_popularity} who trade it
          </span>
        </div>

        <div className="mt-3 flex items-center justify-between font-data text-[11px] text-fog-500">
          <span className="tabular-nums">
            {c.window_start} → {c.window_end.slice(5)}
          </span>
          <PartyMix mix={c.party_breakdown} />
        </div>

        <div className="mt-3 flex items-center justify-between border-t border-ink-700 pt-3">
          <span className="truncate font-ui text-[11px] text-fog-500">
            led by{' '}
            <NameButton name={c.lead_member} onClick={onSelectMember} className="text-fog-300" />
          </span>
          <span className="font-data text-sm tabular-nums" style={{ color: retColor(c.avg_return_30d) }}>
            {fmtSigned(c.avg_return_30d)}
          </span>
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
}> = ({ leaderboard, topConflicts, onSelectMember }) => (
  <div className="grid grid-cols-1 gap-6 p-4 lg:grid-cols-[1.1fr_1fr]">
    <div>
      <Eyebrow>Flagged members · by conflicted notional</Eyebrow>
      <div className="mt-3 divide-y divide-ink-600 rounded-md border border-ink-600 bg-ink-850">
        {leaderboard.map((m) => (
          <div key={m.member} className="flex items-center gap-3 px-4 py-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <NameButton
                  name={m.member}
                  onClick={onSelectMember}
                  className="truncate font-ui font-600 text-fog-200"
                />
                <PartyTag party={m.party} />
              </div>
              <div className="mt-1 font-data text-[11px] text-fog-500">
                {m.top_sectors.join(' · ')}
              </div>
            </div>
            <div className="text-right">
              <div className="font-data text-sm tabular-nums text-brass-500">
                {fmtMoney(m.conflicted_notional)}
              </div>
              <div className="font-data text-[10px] tabular-nums text-fog-500">
                {m.conflict_trades} trades
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>

    <div>
      <Eyebrow>Notable individual conflicts</Eyebrow>
      <div className="mt-3 divide-y divide-ink-600 rounded-md border border-ink-600 bg-ink-850">
        {topConflicts.slice(0, 14).map((c, i) => (
          <div key={i} className="flex items-center gap-3 px-4 py-2.5">
            <span
              className="font-data text-[10px] tracking-wide px-1.5 py-0.5 rounded-sm"
              style={{
                color: c.direction === 'BUY' ? '#43a897' : '#d6707b',
                background: c.direction === 'BUY' ? '#16302b' : '#331a1e',
              }}
            >
              {c.direction.charAt(0)}
            </span>
            <span className="font-data font-600 text-fog-200 w-14">{c.ticker}</span>
            <div className="min-w-0 flex-1">
              <NameButton
                name={c.member}
                onClick={onSelectMember}
                className="block truncate font-ui text-[13px] text-fog-300"
              />
              <div className="truncate font-data text-[10px] text-fog-500">
                {c.sector} · {c.committee}
              </div>
            </div>
            <span className="font-data text-xs tabular-nums text-brass-500">{fmtMoney(c.notional)}</span>
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
  return (
    <div className="p-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { k: 'Avg lag', v: `${lag.avg_lag_days ?? '—'}d`, c: '#e7eeec' },
          { k: 'Median lag', v: `${lag.median_lag_days ?? '—'}d`, c: '#e7eeec' },
          { k: 'Late filings', v: lag.late_filings.toLocaleString(), c: '#d6707b' },
          { k: 'Late share', v: lag.late_pct == null ? '—' : `${(lag.late_pct * 100).toFixed(1)}%`, c: '#d6a24e' },
        ].map((s) => (
          <div key={s.k} className="rounded-md border border-ink-600 bg-ink-850 p-4">
            <div className="font-data text-[10px] uppercase tracking-[0.12em] text-fog-500">{s.k}</div>
            <div className="mt-2 font-data text-2xl font-500 tabular-nums" style={{ color: s.c }}>
              {s.v}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6">
        <Eyebrow>Worst late filers · vs the {lag.stock_act_limit_days}-day STOCK Act clock</Eyebrow>
        <div className="mt-3 space-y-2">
          {lag.worst_late_filers.map((f) => (
            <div key={f.member} className="flex items-center gap-3">
              <div className="w-48 shrink-0 truncate">
                <NameButton
                  name={f.member}
                  onClick={onSelectMember}
                  className="font-ui text-[13px] text-fog-200"
                />{' '}
                <PartyTag party={f.party} />
              </div>
              <div className="relative h-5 flex-1 rounded-sm bg-ink-800">
                {/* 45-day limit marker */}
                <div
                  className="absolute top-0 bottom-0 w-px bg-fog-500/50"
                  style={{ left: `${(lag.stock_act_limit_days / maxLag) * 100}%` }}
                  title={`${lag.stock_act_limit_days}-day limit`}
                />
                <div
                  className="h-full rounded-sm"
                  style={{
                    width: `${(f.avg_lag_days / maxLag) * 100}%`,
                    background: 'linear-gradient(90deg,#cca85a,#d6707b)',
                  }}
                />
              </div>
              <span className="w-24 shrink-0 text-right font-data text-[11px] tabular-nums text-fog-400">
                {f.avg_lag_days}d · {f.late}/{f.total}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
