import React from 'react';
import type { ScrutinyMember } from '../../types/scrutiny';
import { FactorBar, PartyTag, FACTOR_COLORS, FACTOR_LABELS, FACTOR_ORDER } from '../ui';

// Score emphasis: red only for the top tier, ink for watch, faint below.
const scoreTier = (s: number) => {
  if (s >= 80) return 'text-accent';
  if (s >= 65) return 'text-content';
  return 'text-content-faint';
};

export const Leaderboard: React.FC<{
  members: ScrutinyMember[];
  selected?: string;
  onSelect: (m: ScrutinyMember) => void;
}> = ({ members, selected, onSelect }) => {
  return (
    <div className="divide-y divide-line">
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
            className={`group grid w-full grid-cols-[2.2rem_1fr_auto] items-center gap-4 px-3 py-3 text-left transition-colors ${
              active ? 'bg-surface-inset shadow-[inset_3px_0_0_var(--accent)]' : 'hover:bg-surface-inset'
            }`}
          >
            {/* rank */}
            <span className="font-display text-xl font-extrabold leading-none tabular-nums text-content-faint">
              {String(i + 1).padStart(2, '0')}
            </span>

            {/* member + fingerprint */}
            <div className="min-w-0">
              <div className="flex items-center gap-2.5">
                <span className="truncate font-ui font-bold text-content group-hover:text-accent">
                  {m.member}
                </span>
                <PartyTag party={m.party} />
                <span className="font-ui text-[11px] text-content-faint tabular-nums">
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
                className={`font-display text-3xl font-extrabold tabular-nums leading-none ${scoreTier(m.scrutiny_score)}`}
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
  <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 border-b border-line bg-surface-raised px-3 py-2.5">
    {FACTOR_ORDER.map((k) => (
      <span key={k} className="flex items-center gap-1.5 font-ui text-[11px] font-semibold uppercase tracking-[0.08em] text-content-faint">
        <span className="h-2.5 w-2.5" style={{ background: FACTOR_COLORS[k] }} />
        {FACTOR_LABELS[k]}
      </span>
    ))}
    <span className="ml-auto font-ui text-[11px] font-semibold uppercase tracking-[0.08em] text-content-faint">
      Composite score →
    </span>
  </div>
);
