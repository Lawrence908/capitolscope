import React, { useEffect, useState } from 'react';
import { apiClient } from '../../services/api';
import type { SecurityCoverage } from '../../types';
import { Panel, StatTile, Spinner } from '../ui/scaffold';

const fmtInt = (n: number) => n.toLocaleString();

const SecurityCoveragePanel: React.FC = () => {
  const [data, setData] = useState<SecurityCoverage | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    apiClient
      .getSecurityCoverage()
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {
        if (!cancelled) setData(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <Panel title="Security matching coverage">
        <Spinner label="Loading coverage" />
      </Panel>
    );
  }
  if (!data) return null;

  const rateTone = data.match_rate >= 60 ? 'accent' : data.match_rate >= 40 ? 'brass' : 'coral';

  return (
    <Panel
      title="Security matching coverage"
      right={
        <span className="font-data text-[11px] uppercase tracking-[0.12em] text-content-faint">
          ceiling on portfolio &amp; signal accuracy
        </span>
      }
      bodyClassName="p-4"
    >
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatTile label="Match rate" value={`${data.match_rate.toFixed(1)}%`} tone={rateTone} />
        <StatTile
          label="Matched trades"
          value={fmtInt(data.matched_trades)}
          hint={`of ${fmtInt(data.total_trades)}`}
        />
        <StatTile label="Un-tickered" value={fmtInt(data.untickered_trades)} />
        <StatTile
          label="Priced securities"
          value={fmtInt(data.securities_priced)}
          hint={`of ${fmtInt(data.securities_total)}`}
        />
      </div>

      <div className="mb-2 font-data text-[10px] uppercase tracking-[0.14em] text-content-faint">
        Coverage by asset type
      </div>
      <div className="space-y-2">
        {data.by_asset_type.map((a) => (
          <div key={a.asset_type} className="flex items-center gap-3">
            <span className="w-28 shrink-0 truncate font-data text-xs text-content-muted">
              {a.asset_type}
            </span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-inset">
              <div
                className="h-full rounded-full bg-accent"
                style={{ width: `${Math.min(100, a.match_rate ?? 0)}%` }}
              />
            </div>
            <span className="w-32 shrink-0 text-right font-data text-[11px] tabular-nums text-content-faint">
              {fmtInt(a.matched)}/{fmtInt(a.total)}
              {a.match_rate != null && ` · ${a.match_rate.toFixed(0)}%`}
            </span>
          </div>
        ))}
      </div>
    </Panel>
  );
};

export default SecurityCoveragePanel;
