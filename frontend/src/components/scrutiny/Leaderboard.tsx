import React from 'react';
import type { ScrutinyMember } from '../../types/scrutiny';
import { FactorBar, PartyTag, FACTOR_COLORS, FACTOR_LABELS, FACTOR_ORDER } from './primitives';

const scoreTier = (s: number) => {
  if (s >= 80) return '#d6707b'; // flag
  if (s >= 65) return '#cca85a'; // watch
  return '#90a29d'; // muted
};

export const Leaderboard: React.FC<{
  members: ScrutinyMember[];
  selected?: string;
  onSelect: (m: ScrutinyMember) => void;
}> = ({ members, selected, onSelect }) => {
  return (
    <div className="divide-y divide-ink-600">
      {members.map((m, i) => {
        const contributions = {
          edge: m.factors.edge.contribution,
          event: m.factors.event.contribution,
          conflict: m.factors.conflict.contribution,
          cluster: m.factors.cluster.contribution,
          lag: m.factors.lag.contribution,
          size: m.factors.size.contribution,
        };
        const active = selected === m.member;
        return (
          <button
            key={m.member}
            onClick={() => onSelect(m)}
            className={`group grid w-full grid-cols-[2.2rem_1fr_auto] items-center gap-4 px-4 py-3 text-left transition-colors ${
              active ? 'bg-ink-800' : 'hover:bg-ink-850'
            }`}
          >
            {/* rank */}
            <span className="font-data text-xs tabular-nums text-fog-500">
              {String(i + 1).padStart(2, '0')}
            </span>

            {/* member + fingerprint */}
            <div className="min-w-0">
              <div className="flex items-center gap-2.5">
                <span className="truncate font-ui font-600 text-fog-200 group-hover:text-white">
                  {m.member}
                </span>
                <PartyTag party={m.party} />
                <span className="font-data text-[10px] tracking-wide text-fog-500 tabular-nums">
                  {m.trades} trades
                </span>
              </div>
              <div className="mt-2 max-w-md">
                <FactorBar contributions={contributions} />
              </div>
            </div>

            {/* score */}
            <div className="text-right">
              <span
                className="font-data text-2xl font-500 tabular-nums leading-none"
                style={{ color: scoreTier(m.scrutiny_score) }}
              >
                {m.scrutiny_score.toFixed(1)}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
};

export const LegendRow: React.FC = () => (
  <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 px-4 py-2.5 border-b border-ink-600 bg-ink-900">
    {FACTOR_ORDER.map((k) => (
      <span key={k} className="flex items-center gap-1.5 font-data text-[10px] uppercase tracking-[0.12em] text-fog-500">
        <span className="h-2 w-2 rounded-[2px]" style={{ background: FACTOR_COLORS[k] }} />
        {FACTOR_LABELS[k]}
      </span>
    ))}
    <span className="ml-auto font-data text-[10px] uppercase tracking-[0.12em] text-fog-500">
      Composite score →
    </span>
  </div>
);
