import React from 'react';
import type { ScrutinyMember, DossierOrigin } from '../../types/scrutiny';
import {
  Meter,
  PartyTag,
  Eyebrow,
  fmtPct,
  fmtSigned,
  fmtMoney,
  FACTOR_COLORS,
} from '../ui';

const Row: React.FC<{
  factorKey: 'edge' | 'event' | 'conflict' | 'cluster' | 'lag' | 'size';
  title: string;
  percentile: number;
  weight: number;
  contribution: number;
  detail: React.ReactNode;
}> = ({ factorKey, title, percentile, weight, contribution, detail }) => (
  <div className="py-4 border-b border-line last:border-b-0">
    <div className="flex items-baseline justify-between">
      <div className="flex items-center gap-2">
        <span className="h-2.5 w-2.5 rounded-[2px]" style={{ background: FACTOR_COLORS[factorKey] }} />
        <span className="font-ui font-semibold text-content">{title}</span>
        <span className="font-data text-[10px] text-content-faint tracking-wide">
          w{(weight * 100).toFixed(0)}
        </span>
      </div>
      <span className="font-data text-sm tabular-nums text-content-muted">
        +{contribution.toFixed(1)}
        <span className="text-content-faint text-[10px]"> pts</span>
      </span>
    </div>
    <div className="mt-2">
      <Meter value={percentile} color={FACTOR_COLORS[factorKey]} />
      <div className="mt-1.5 flex items-center justify-between font-data text-[11px] text-content-faint">
        <span>{detail}</span>
        <span className="tabular-nums">{(percentile * 100).toFixed(0)}th pctile</span>
      </div>
    </div>
  </div>
);

const BackLink: React.FC<{ origin?: DossierOrigin | null; onBack?: () => void }> = ({
  origin,
  onBack,
}) =>
  origin && onBack ? (
    <button
      type="button"
      onClick={onBack}
      className="group mb-3 flex items-center gap-1.5 font-data text-[11px] tracking-wide text-verdigris-500 transition-colors hover:text-verdigris-400"
    >
      <span className="transition-transform group-hover:-translate-x-0.5">←</span>
      Back to {origin.label}
    </button>
  ) : null;

export const MemberDossier: React.FC<{
  member: ScrutinyMember | null;
  missingName?: string | null;
  origin?: DossierOrigin | null;
  onBack?: () => void;
}> = ({ member, missingName, origin, onBack }) => {
  if (!member) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 px-8 text-center">
        {origin && onBack && (
          <div className="w-full text-left">
            <BackLink origin={origin} onBack={onBack} />
          </div>
        )}
        {missingName ? (
          <>
            <div className="font-display text-lg text-content">{missingName}</div>
            <div className="font-data text-[11px] uppercase tracking-[0.16em] text-sev-watch">
              Not in the scored cohort
            </div>
            <p className="font-ui text-sm text-content-faint max-w-[26ch]">
              This member has fewer than 10 price-matched trades, so the composite score is not yet
              computed. Their activity still appears in the signal views.
            </p>
          </>
        ) : (
          <>
            <div className="font-data text-[11px] uppercase tracking-[0.2em] text-content-faint">
              Select a subject
            </div>
            <p className="font-ui text-sm text-content-faint max-w-[22ch]">
              Every score decomposes into named, sourced factors. Pick a member to open the dossier.
            </p>
          </>
        )}
      </div>
    );
  }
  const f = member.factors;
  return (
    <div className="flex h-full flex-col">
      {/* header */}
      <div className="border-b border-line px-6 pb-5 pt-6">
        <BackLink origin={origin} onBack={onBack} />
        <Eyebrow>Dossier</Eyebrow>
        <h2 className="mt-2 font-display text-2xl leading-tight text-content">{member.member}</h2>
        <div className="mt-2 flex items-center gap-2.5 font-data text-[11px] text-content-faint">
          <PartyTag party={member.party} />
          <span>{member.chamber || '—'}</span>
          <span>·</span>
          <span className="tabular-nums">{member.trades} scored trades</span>
        </div>
        <div className="mt-4 flex items-end gap-3">
          <span className="font-data text-5xl font-medium tabular-nums leading-none text-brass-500">
            {member.scrutiny_score.toFixed(1)}
          </span>
          <span className="pb-1 font-data text-[10px] uppercase tracking-[0.16em] text-content-faint">
            Scrutiny<br />score
          </span>
        </div>
      </div>

      {/* factors */}
      <div className="flex-1 overflow-y-auto px-6">
        <Row
          factorKey="edge"
          title="Trading edge"
          percentile={f.edge.percentile}
          weight={f.edge.weight}
          contribution={f.edge.contribution}
          detail={`α ${fmtSigned(f.edge.avg_alpha_30d)} · t=${f.edge.t_stat}`}
        />
        <Row
          factorKey="event"
          title="Pre-earnings positioning"
          percentile={f.event.percentile}
          weight={f.event.weight}
          contribution={f.event.contribution}
          detail={`${f.event.pre_earnings_trades} trades · ${fmtPct(
            f.event.pre_earnings_rate,
            0,
          )} within 10d of a print`}
        />
        <Row
          factorKey="conflict"
          title="Committee conflict"
          percentile={f.conflict.percentile}
          weight={f.conflict.weight}
          contribution={f.conflict.contribution}
          detail={`${f.conflict.conflict_trades} trades · ${fmtPct(f.conflict.conflict_rate, 0)} of book`}
        />
        <Row
          factorKey="cluster"
          title="Herding involvement"
          percentile={f.cluster.percentile}
          weight={f.cluster.weight}
          contribution={f.cluster.contribution}
          detail={`notability ${f.cluster.cluster_involvement.toFixed(2)}`}
        />
        <Row
          factorKey="lag"
          title="Disclosure lag"
          percentile={f.lag.percentile}
          weight={f.lag.weight}
          contribution={f.lag.contribution}
          detail={`${fmtPct(f.lag.late_pct, 0)} late · ${f.lag.avg_lag_days ?? '—'}d avg`}
        />
        <Row
          factorKey="size"
          title="Size anomaly"
          percentile={f.size.percentile}
          weight={f.size.weight}
          contribution={f.size.contribution}
          detail={`z=${f.size.size_z} · ${fmtMoney(f.size.biggest)} vs ${fmtMoney(
            f.size.median_notional,
          )} median`}
        />
      </div>

      <div className="border-t border-line px-6 py-3">
        <p className="font-ui text-[11px] leading-relaxed text-content-faint">
          A lead for scrutiny, not a verdict. Score is percentile-ranked within the scored cohort;
          edge is benchmark-adjusted and significance-weighted.
        </p>
      </div>
    </div>
  );
};
