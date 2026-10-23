import React, { useEffect, useState } from 'react';
import apiClient from '../../services/api';
import type { TickerDetail } from '../../types/scrutiny';
import { fmtMoney, PartyTag, NameButton } from '../ui';
import { SignedReturn } from './SignalViews';

export const TickerDrawer: React.FC<{
  ticker: string | null;
  onClose: () => void;
  onSelectMember?: (name: string) => void;
}> = ({ ticker, onClose, onSelectMember }) => {
  const [data, setData] = useState<TickerDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;
    setData(null);
    setError(null);
    setLoading(true);
    apiClient
      .getTickerTrades(ticker)
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(e?.message || 'Failed to load ticker'))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  // Escape to close
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    if (ticker) window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [ticker, onClose]);

  if (!ticker) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* scrim */}
      <div
        className="absolute inset-0 bg-black/60 animate-[fadeIn_0.15s_ease]"
        onClick={onClose}
      />
      {/* panel */}
      <aside className="relative flex h-full w-full max-w-xl flex-col border-l-[3px] border-content bg-surface-raised shadow-2xl animate-[slideIn_0.2s_ease]">
        <header className="bg-slab px-6 pb-5 pt-6 text-slab-on">
          <div className="flex items-start justify-between">
            <div>
              <span className="font-ui text-[11px] font-bold uppercase tracking-[0.12em] text-accent">
                Ticker · congressional flow
              </span>
              <h2 className="mt-1.5 font-display text-7xl font-extrabold leading-[0.85] text-slab-on">
                {ticker}
              </h2>
              {data?.security_name && (
                <p className="mt-2 font-ui text-sm text-slab-muted">
                  {data.security_name}
                  {data.sector ? ` · ${data.sector}` : ''}
                </p>
              )}
            </div>
            <button
              onClick={onClose}
              className="border-2 border-slab-on px-2 py-1 font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-slab-on hover:bg-slab-on hover:text-slab"
              aria-label="Close"
            >
              ESC ✕
            </button>
          </div>

          {data && (
            <div className="mt-5 grid grid-cols-4 gap-3 border-t border-slab-muted pt-4">
              {[
                { k: 'Trades', v: String(data.trade_count) },
                { k: 'Members', v: String(data.member_count) },
                { k: 'B / S', v: `${data.buys}/${data.sells}` },
                {
                  k: 'Avg 30d',
                  v:
                    data.avg_return_30d == null
                      ? '–'
                      : `${data.avg_return_30d < 0 ? '▼' : '▲'} ${(data.avg_return_30d >= 0 ? '+' : '') + (data.avg_return_30d * 100).toFixed(1)}%`,
                },
              ].map((s) => (
                <div key={s.k}>
                  <div className="font-ui text-[10px] font-semibold uppercase tracking-[0.08em] text-slab-muted">
                    {s.k}
                  </div>
                  <div className="mt-1 font-display text-2xl font-extrabold leading-none tabular-nums text-slab-on">
                    {s.v}
                  </div>
                </div>
              ))}
            </div>
          )}
        </header>

        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="flex h-40 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-[3px] border-line border-t-accent" />
            </div>
          )}
          {error && <div className="mx-6 my-4 border-l-4 border-accent bg-surface-inset px-4 py-3 font-ui text-sm text-content">{error}</div>}
          {data && (
            <table className="w-full">
              <thead className="sticky top-0 bg-surface-raised">
                <tr className="border-b-2 border-content font-ui text-[11px] uppercase tracking-[0.08em] text-content-faint">
                  <th className="px-6 py-2 text-left font-bold">Date</th>
                  <th className="py-2 text-left font-bold">Member</th>
                  <th className="py-2 text-left font-bold">Side</th>
                  <th className="py-2 text-right font-bold">Amount</th>
                  <th className="px-6 py-2 text-right font-bold">30d</th>
                </tr>
              </thead>
              <tbody>
                {data.trades.map((t, i) => (
                  <tr key={i} className="border-b border-line hover:bg-surface-inset">
                    <td className="px-6 py-2 font-ui text-[11px] tabular-nums text-content-faint">
                      {t.date}
                    </td>
                    <td className="py-2">
                      <span className="inline-flex items-center gap-2">
                        <PartyTag party={t.party} />
                        <NameButton
                          name={t.member}
                          onClick={onSelectMember}
                          className="font-ui text-[13px] font-semibold text-content"
                        />
                      </span>
                    </td>
                    <td className="py-2">
                      <span
                        className={`inline-block border-2 border-content px-1 font-display text-[12px] font-extrabold uppercase leading-tight tracking-[0.04em] ${
                          t.direction === 'BUY' ? 'bg-content text-surface' : 'text-content'
                        }`}
                      >
                        {t.direction === 'BUY' ? 'Bought' : 'Sold'}
                      </span>
                    </td>
                    <td className="py-2 text-right font-display text-base font-extrabold tabular-nums text-content">
                      {fmtMoney(t.amount)}
                    </td>
                    <td className="px-6 py-2 text-right">
                      <SignedReturn value={t.signed_return_30d} className="font-ui text-[12px] font-semibold" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <footer className="border-t border-line px-6 py-3">
          <p className="font-ui text-[11px] leading-relaxed text-content-faint">
            30d is direction-aware (a well-timed sale precedes a drop). Amounts are disclosed-range
            midpoints.
          </p>
        </footer>
      </aside>
    </div>
  );
};
