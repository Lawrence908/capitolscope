import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { apiClient } from '../../services/api';
import type {
  CongressMember, MirrorPortfolio, MirrorHoldingsResult, EquityCurveResult,
} from '../../types';
import { PageHeader, Panel, Spinner } from '../../components/ui/scaffold';
import { fmtMoney } from '../../components/ui/format';
import { MemberPicker, MemberChip } from '../../components/members/MemberPicker';
import LineChart from '../../components/charts/LineChart';

/** Format an already-percentage number (e.g. 68.85 -> "+68.9%"). */
const pct = (n: number | null | undefined, signed = false): string => {
  if (n == null) return '—';
  const s = `${n.toFixed(1)}%`;
  return signed && n >= 0 ? `+${s}` : s;
};

const toneForReturn = (n: number | null | undefined): string =>
  n == null ? 'text-content' : n >= 0 ? 'text-accent' : 'text-sev-flag';

// ---- main page -------------------------------------------------------------

const MirrorPage: React.FC = () => {
  const [mirrors, setMirrors] = useState<MirrorPortfolio[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [holdings, setHoldings] = useState<MirrorHoldingsResult | null>(null);
  const [loadingHoldings, setLoadingHoldings] = useState(false);
  const [performance, setPerformance] = useState<EquityCurveResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // create form
  const [newName, setNewName] = useState('');
  const [newMembers, setNewMembers] = useState<CongressMember[]>([]);
  const [creating, setCreating] = useState(false);

  const selected = useMemo(
    () => mirrors.find((m) => m.id === selectedId) || null,
    [mirrors, selectedId]
  );

  const loadMirrors = useCallback(async () => {
    try {
      const list = await apiClient.getMirrorPortfolios();
      setMirrors(list);
      setSelectedId((prev) => prev ?? (list[0]?.id ?? null));
    } catch {
      setError('Failed to load mirror portfolios.');
    }
  }, []);

  useEffect(() => {
    void loadMirrors();
  }, [loadMirrors]);

  const loadHoldings = useCallback(async (id: string) => {
    setLoadingHoldings(true);
    setHoldings(null);
    try {
      setHoldings(await apiClient.getMirrorHoldings(id));
    } catch {
      setError('Failed to compute holdings.');
    } finally {
      setLoadingHoldings(false);
    }
  }, []);

  const loadPerformance = useCallback(async (id: string) => {
    setPerformance(null);
    try {
      setPerformance(await apiClient.getMirrorPerformance(id));
    } catch {
      /* performance is non-critical; leave it null */
    }
  }, []);

  useEffect(() => {
    if (selectedId) {
      void loadHoldings(selectedId);
      void loadPerformance(selectedId);
    }
  }, [selectedId, loadHoldings, loadPerformance]);

  const createMirror = async () => {
    if (!newName.trim() || newMembers.length === 0) return;
    setCreating(true);
    try {
      const created = await apiClient.createMirrorPortfolio({
        name: newName.trim(),
        member_ids: newMembers.map((m) => m.id),
      });
      setNewName('');
      setNewMembers([]);
      await loadMirrors();
      setSelectedId(created.id);
    } catch {
      setError('Failed to create mirror portfolio.');
    } finally {
      setCreating(false);
    }
  };

  const removeMemberFromSelected = async (memberId: string) => {
    if (!selected) return;
    const next = selected.member_ids.filter((id) => id !== memberId);
    try {
      await apiClient.setMirrorMembers(selected.id, next);
      await loadMirrors();
      await loadHoldings(selected.id);
    } catch {
      setError('Failed to update members.');
    }
  };

  const addMemberToSelected = async (m: CongressMember) => {
    if (!selected || selected.member_ids.includes(m.id)) return;
    try {
      await apiClient.setMirrorMembers(selected.id, [...selected.member_ids, m.id]);
      await loadMirrors();
      await loadHoldings(selected.id);
    } catch {
      setError('Failed to update members.');
    }
  };

  const deleteSelected = async () => {
    if (!selected) return;
    try {
      await apiClient.deleteMirrorPortfolio(selected.id);
      setSelectedId(null);
      setHoldings(null);
      await loadMirrors();
    } catch {
      setError('Failed to delete mirror portfolio.');
    }
  };

  const totals = holdings?.totals;

  return (
    <div>
      <PageHeader
        eyebrow="Portfolio"
        title="Mirror Portfolios"
        subtitle="Combine any set of members into one synthetic portfolio. Positions are reconstructed from disclosed trades and valued at the latest close — an approximation of what mirroring those members would look like."
        stats={
          totals
            ? [
                { label: 'Market value', value: fmtMoney(totals.market_value) },
                { label: 'Total return', value: pct(totals.return_pct, true), tone: (totals.return_pct ?? 0) >= 0 ? 'accent' : 'flag' },
                { label: 'Holdings', value: String(totals.holdings_count) },
              ]
            : undefined
        }
      />

      {error && (
        <div className="mb-4 rounded-md border border-sev-flag/40 px-4 py-3 font-ui text-sm text-sev-flag">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[340px_1fr]">
        {/* left: mirror list + create */}
        <div className="space-y-6">
          <Panel title="Your mirrors">
            {mirrors.length === 0 ? (
              <p className="px-4 py-4 font-ui text-sm text-content-faint">No mirrors yet. Create one below.</p>
            ) : (
              <ul className="divide-y divide-line">
                {mirrors.map((m) => (
                  <li key={m.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(m.id)}
                      className={`flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-surface-inset ${
                        m.id === selectedId ? 'bg-surface-inset' : ''
                      }`}
                    >
                      <span className="font-ui text-sm text-content">{m.name}</span>
                      <span className="font-data text-[11px] uppercase tracking-[0.12em] text-content-faint">
                        {m.member_count} member{m.member_count === 1 ? '' : 's'}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Create mirror" bodyClassName="p-4 space-y-3">
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Portfolio name"
              className="w-full rounded-md border border-line bg-surface px-3 py-2 font-ui text-sm text-content placeholder:text-content-faint focus:border-accent focus:outline-none"
            />
            {newMembers.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {newMembers.map((m) => (
                  <MemberChip
                    key={m.id}
                    label={m.full_name}
                    party={m.party}
                    onRemove={() => setNewMembers((prev) => prev.filter((x) => x.id !== m.id))}
                  />
                ))}
              </div>
            )}
            <MemberPicker
              excludeIds={new Set(newMembers.map((m) => m.id))}
              onAdd={(m) => setNewMembers((prev) => (prev.some((x) => x.id === m.id) ? prev : [...prev, m]))}
            />
            <button
              type="button"
              disabled={creating || !newName.trim() || newMembers.length === 0}
              onClick={createMirror}
              className="w-full rounded-md bg-accent px-4 py-2 font-data text-xs uppercase tracking-[0.12em] text-[#071310] transition-opacity hover:opacity-90 disabled:opacity-40"
            >
              {creating ? 'Creating…' : 'Create mirror'}
            </button>
          </Panel>
        </div>

        {/* right: selected mirror holdings */}
        <div>
          {!selected ? (
            <Panel>
              <p className="px-4 py-16 text-center font-ui text-sm text-content-faint">
                Select or create a mirror portfolio to see combined holdings.
              </p>
            </Panel>
          ) : (
            <div className="space-y-6">
              <Panel
                title={selected.name}
                right={
                  <button
                    type="button"
                    onClick={deleteSelected}
                    className="font-data text-[11px] uppercase tracking-[0.12em] text-content-faint hover:text-sev-flag"
                  >
                    Delete
                  </button>
                }
                bodyClassName="p-4 space-y-3"
              >
                <div className="flex flex-wrap gap-1.5">
                  {selected.members.length === 0 ? (
                    <span className="font-ui text-sm text-content-faint">No members — add some below.</span>
                  ) : (
                    selected.members.map((m) => (
                      <MemberChip
                        key={m.member_id}
                        label={m.name || m.member_id.slice(0, 8)}
                        party={m.party}
                        onRemove={() => removeMemberFromSelected(m.member_id)}
                      />
                    ))
                  )}
                </div>
                <MemberPicker excludeIds={new Set(selected.member_ids)} onAdd={addMemberToSelected} />
              </Panel>

              {performance && performance.series.length > 1 && (
                <Panel
                  title="Performance vs SPY"
                  right={
                    performance.summary.vs_spy_pct != null ? (
                      <span
                        className={`font-data text-[11px] uppercase tracking-[0.12em] ${
                          performance.summary.vs_spy_pct >= 0 ? 'text-accent' : 'text-sev-flag'
                        }`}
                      >
                        {pct(performance.summary.vs_spy_pct, true)} vs SPY
                      </span>
                    ) : undefined
                  }
                  bodyClassName="p-4"
                >
                  <LineChart
                    height={320}
                    data={{
                      labels: performance.series.map((p) => p.date.slice(0, 7)),
                      datasets: [
                        {
                          label: 'Mirror',
                          data: performance.series.map((p) => p.portfolio_value),
                          borderColor: '#1f9e88',
                          backgroundColor: 'rgba(31,158,136,0.12)',
                          borderWidth: 2,
                          fill: true,
                          tension: 0.25,
                        },
                        {
                          label: 'SPY (same cash flows)',
                          data: performance.series.map((p) => p.spy_value ?? Number.NaN),
                          borderColor: '#9aa5b1',
                          borderWidth: 1.5,
                          fill: false,
                          tension: 0.25,
                        },
                      ],
                    }}
                  />
                </Panel>
              )}

              <Panel
                title="Combined holdings"
                right={
                  holdings?.meta ? (
                    <span className="font-data text-[11px] uppercase tracking-[0.12em] text-content-faint">
                      {holdings.meta.priced_trades} priced trades
                    </span>
                  ) : undefined
                }
              >
                {loadingHoldings ? (
                  <Spinner label="Reconstructing positions" />
                ) : !holdings || holdings.holdings.length === 0 ? (
                  <p className="px-4 py-12 text-center font-ui text-sm text-content-faint">
                    No priced holdings. Add members with matched, priced trades.
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left">
                      <thead>
                        <tr className="border-b border-line font-data text-[10px] uppercase tracking-[0.14em] text-content-faint">
                          <th className="px-4 py-2">Ticker</th>
                          <th className="px-4 py-2 text-right">Shares</th>
                          <th className="px-4 py-2 text-right">Cost basis</th>
                          <th className="px-4 py-2 text-right">Market value</th>
                          <th className="px-4 py-2 text-right">Return</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-line">
                        {holdings.holdings.map((h) => (
                          <tr key={h.security_id} className="hover:bg-surface-inset">
                            <td className="px-4 py-2">
                              <span className="font-data text-sm text-content">{h.ticker || '—'}</span>
                              {h.name && (
                                <span className="ml-2 font-ui text-xs text-content-faint">{h.name}</span>
                              )}
                            </td>
                            <td className="px-4 py-2 text-right font-data text-sm tabular-nums text-content-muted">
                              {h.shares.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                            </td>
                            <td className="px-4 py-2 text-right font-data text-sm tabular-nums text-content-muted">
                              {fmtMoney(h.cost_basis)}
                            </td>
                            <td className="px-4 py-2 text-right font-data text-sm tabular-nums text-content">
                              {fmtMoney(h.market_value)}
                            </td>
                            <td className={`px-4 py-2 text-right font-data text-sm tabular-nums ${toneForReturn(h.return_pct)}`}>
                              {pct(h.return_pct, true)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Panel>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MirrorPage;
