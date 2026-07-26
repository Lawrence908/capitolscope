import React, { useCallback, useEffect, useState } from 'react';
import { apiClient } from '../../services/api';
import type { CongressMember, MemberComparisonResult, MemberComparisonEntry } from '../../types';
import { PageHeader, Panel, Spinner } from '../../components/ui/scaffold';
import { PartyTag } from '../../components/ui/primitives';
import { fmtMoney } from '../../components/ui/format';
import { MemberPicker, MemberChip } from '../../components/members/MemberPicker';

const pct = (n: number | null | undefined, signed = false): string => {
  if (n == null) return '—';
  const s = `${n.toFixed(1)}%`;
  return signed && n >= 0 ? `+${s}` : s;
};
const returnTone = (n: number | null | undefined): string =>
  n == null ? 'text-content' : n >= 0 ? 'text-accent' : 'text-sev-flag';

const MemberColumn: React.FC<{ entry: MemberComparisonEntry }> = ({ entry }) => {
  const t = entry.totals;
  return (
    <div className="min-w-[240px] flex-1 border-l border-line px-4 py-3 first:border-l-0">
      <div className="mb-3 flex items-center gap-2">
        <PartyTag party={entry.member?.party} />
        <span className="truncate font-ui text-sm font-medium text-content">
          {entry.member?.name || entry.member_id.slice(0, 8)}
        </span>
      </div>
      <div className="space-y-1.5 font-data text-sm tabular-nums">
        <div className="flex justify-between">
          <span className="text-content-faint">Value</span>
          <span className="text-content">{fmtMoney(t.market_value)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-content-faint">Return</span>
          <span className={returnTone(t.return_pct)}>{pct(t.return_pct, true)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-content-faint">Holdings</span>
          <span className="text-content">{t.holdings_count}</span>
        </div>
      </div>
      {entry.top_holdings.length > 0 && (
        <div className="mt-4">
          <div className="mb-1.5 font-data text-[10px] uppercase tracking-[0.14em] text-content-faint">
            Top holdings
          </div>
          <ul className="space-y-1">
            {entry.top_holdings.map((h) => (
              <li key={h.security_id} className="flex items-center justify-between gap-2">
                <span className="truncate font-data text-xs text-content">{h.ticker || '—'}</span>
                <span className="shrink-0 font-data text-xs tabular-nums text-content-faint">
                  {fmtMoney(h.market_value)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

const ComparePage: React.FC = () => {
  const [selected, setSelected] = useState<CongressMember[]>([]);
  const [result, setResult] = useState<MemberComparisonResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nameById = useCallback(
    (id: string) => selected.find((m) => m.id === id)?.full_name || id.slice(0, 8),
    [selected]
  );

  useEffect(() => {
    if (selected.length < 2) {
      setResult(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiClient
      .compareMemberPortfolios(selected.map((m) => m.id))
      .then((data) => {
        if (!cancelled) setResult(data);
      })
      .catch(() => {
        if (!cancelled) setError('Failed to compare members.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selected]);

  const addMember = (m: CongressMember) => {
    setSelected((prev) =>
      prev.some((x) => x.id === m.id) || prev.length >= 5 ? prev : [...prev, m]
    );
  };
  const removeMember = (id: string) =>
    setSelected((prev) => prev.filter((m) => m.id !== id));

  return (
    <div>
      <PageHeader
        eyebrow="Portfolio"
        title="Compare Members"
        subtitle="Pick 2–5 members to compare their reconstructed portfolios side by side, and see the securities they hold in common. Values are approximations reconstructed from disclosed trades."
      />

      {error && (
        <div className="mb-4 rounded-md border border-sev-flag/40 px-4 py-3 font-ui text-sm text-sev-flag">
          {error}
        </div>
      )}

      <div className="mb-6 max-w-xl">
        <Panel title="Members" bodyClassName="p-4 space-y-3">
          {selected.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {selected.map((m) => (
                <MemberChip
                  key={m.id}
                  label={m.full_name}
                  party={m.party}
                  onRemove={() => removeMember(m.id)}
                />
              ))}
            </div>
          )}
          {selected.length < 5 ? (
            <MemberPicker excludeIds={new Set(selected.map((m) => m.id))} onAdd={addMember} />
          ) : (
            <p className="font-ui text-xs text-content-faint">Maximum of 5 members.</p>
          )}
          {selected.length < 2 && (
            <p className="font-ui text-xs text-content-faint">Add at least 2 members to compare.</p>
          )}
        </Panel>
      </div>

      {loading ? (
        <Spinner label="Reconstructing portfolios" />
      ) : result ? (
        <div className="space-y-6">
          <Panel title="Side by side">
            <div className="flex overflow-x-auto">
              {result.members.map((entry) => (
                <MemberColumn key={entry.member_id} entry={entry} />
              ))}
            </div>
          </Panel>

          <Panel
            title="Held in common"
            right={
              <span className="font-data text-[11px] uppercase tracking-[0.12em] text-content-faint">
                {result.overlap.count} securities
              </span>
            }
          >
            {result.overlap.count === 0 ? (
              <p className="px-4 py-10 text-center font-ui text-sm text-content-faint">
                No securities held by more than one of these members.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-line font-data text-[10px] uppercase tracking-[0.14em] text-content-faint">
                      <th className="px-4 py-2">Ticker</th>
                      <th className="px-4 py-2">Held by</th>
                      <th className="px-4 py-2 text-right">Combined value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {result.overlap.common_securities.map((c) => (
                      <tr key={c.security_id} className="hover:bg-surface-inset">
                        <td className="px-4 py-2">
                          <span className="font-data text-sm text-content">{c.ticker || '—'}</span>
                          {c.name && (
                            <span className="ml-2 font-ui text-xs text-content-faint">{c.name}</span>
                          )}
                        </td>
                        <td className="px-4 py-2 font-ui text-xs text-content-muted">
                          {c.held_by.map((id) => nameById(id)).join(', ')}
                        </td>
                        <td className="px-4 py-2 text-right font-data text-sm tabular-nums text-content">
                          {fmtMoney(c.combined_value)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </div>
      ) : (
        <Panel>
          <p className="px-4 py-16 text-center font-ui text-sm text-content-faint">
            Add 2 or more members above to see the comparison.
          </p>
        </Panel>
      )}
    </div>
  );
};

export default ComparePage;
