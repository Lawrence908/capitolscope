import React, { useEffect, useState } from 'react';
import apiClient from '../../services/api';
import type { TickerDetail } from '../../types/scrutiny';
import { fmtMoney, fmtSigned, PartyTag, NameButton } from '../ui';

const retColor = (r: number | null) =>
  r == null ? '#90a29d' : r >= 0 ? '#43a897' : '#d6707b';

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
        className="absolute inset-0 bg-black/60 backdrop-blur-[1px] animate-[fadeIn_0.15s_ease]"
        onClick={onClose}
      />
      {/* panel */}
      <aside className="relative flex h-full w-full max-w-xl flex-col border-l border-line bg-surface-raised shadow-2xl animate-[slideIn_0.2s_ease]">
        <header className="border-b border-line px-6 pb-5 pt-6">
          <div className="flex items-start justify-between">
            <div>
              <span className="font-data text-[11px] uppercase tracking-[0.18em] text-verdigris-500">
                Ticker · congressional flow
              </span>
              <h2 className="mt-1.5 font-data text-3xl font-semibold tracking-tight text-content">
                {ticker}
              </h2>
              {data?.security_name && (
                <p className="mt-1 font-ui text-sm text-content-faint">
                  {data.security_name}
                  {data.sector ? ` · ${data.sector}` : ''}
                </p>
              )}
            </div>
            <button
              onClick={onClose}
              className="font-data text-xs text-content-faint hover:text-content"
              aria-label="Close"
            >
              ESC ✕
            </button>
          </div>

          {data && (
            <div className="mt-5 grid grid-cols-4 gap-3">
              {[
                { k: 'Trades', v: String(data.trade_count), c: '#e7eeec' },
                { k: 'Members', v: String(data.member_count), c: '#e7eeec' },
                { k: 'B / S', v: `${data.buys}/${data.sells}`, c: '#e7eeec' },
                { k: 'Avg 30d', v: fmtSigned(data.avg_return_30d), c: retColor(data.avg_return_30d) },
              ].map((s) => (
                <div key={s.k}>
                  <div className="font-data text-[9px] uppercase tracking-[0.1em] text-content-faint">
                    {s.k}
                  </div>
                  <div className="mt-1 font-data text-lg font-medium tabular-nums" style={{ color: s.c }}>
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
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-line border-t-verdigris-500" />
            </div>
          )}
          {error && <div className="px-6 py-4 font-ui text-sm text-sev-flag">{error}</div>}
          {data && (
            <table className="w-full">
              <thead className="sticky top-0 bg-surface-raised">
                <tr className="border-b border-line font-data text-[10px] uppercase tracking-[0.1em] text-content-faint">
                  <th className="px-6 py-2 text-left font-medium">Date</th>
                  <th className="py-2 text-left font-medium">Member</th>
                  <th className="py-2 text-left font-medium">Side</th>
                  <th className="py-2 text-right font-medium">Amount</th>
                  <th className="px-6 py-2 text-right font-medium">30d</th>
                </tr>
              </thead>
              <tbody>
                {data.trades.map((t, i) => (
                  <tr key={i} className="border-b border-surface-inset/60 hover:bg-surface-inset">
                    <td className="px-6 py-2 font-data text-[11px] tabular-nums text-content-faint">
                      {t.date}
                    </td>
                    <td className="py-2">
                      <NameButton
                        name={t.member}
                        onClick={onSelectMember}
                        className="font-ui text-[13px] text-content-muted"
                      />{' '}
                      <PartyTag party={t.party} />
                    </td>
                    <td className="py-2">
                      <span
                        className="font-data text-[10px] tracking-wide"
                        style={{ color: t.direction === 'BUY' ? '#43a897' : '#d6707b' }}
                      >
                        {t.direction}
                      </span>
                    </td>
                    <td className="py-2 text-right font-data text-[11px] tabular-nums text-brass-500">
                      {fmtMoney(t.amount)}
                    </td>
                    <td
                      className="px-6 py-2 text-right font-data text-[11px] tabular-nums"
                      style={{ color: retColor(t.signed_return_30d) }}
                    >
                      {fmtSigned(t.signed_return_30d)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <footer className="border-t border-line px-6 py-3">
          <p className="font-data text-[10px] leading-relaxed text-content-faint">
            30d is direction-aware (a well-timed sale precedes a drop). Amounts are disclosed-range
            midpoints.
          </p>
        </footer>
      </aside>
    </div>
  );
};
