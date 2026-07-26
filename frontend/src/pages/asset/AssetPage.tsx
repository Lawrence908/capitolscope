import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import apiClient from '../../services/api';
import type { TickerDetail } from '../../types/scrutiny';
import { PageHeader, Spinner, PartyTag, fmtMoney, fmtSigned } from '../../components/ui';

const retColor = (r: number | null) => (r == null ? '#90a29d' : r >= 0 ? '#43a897' : '#d6707b');

const AssetPage: React.FC = () => {
  const { ticker: rawTicker } = useParams<{ ticker: string }>();
  const ticker = (rawTicker || '').toUpperCase();
  const [data, setData] = useState<TickerDetail | null>(null);
  const [loading, setLoading] = useState(true);
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
      .catch((e) => !cancelled && setError(e?.message || 'Failed to load asset'))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  if (loading) {
    return <Spinner label={`Loading ${ticker}`} />;
  }

  if (error) {
    return (
      <div>
        <Link to="/trades" className="inline-flex items-center gap-1.5 font-ui text-sm text-content-muted transition-colors hover:text-accent">
          <ArrowLeftIcon className="h-4 w-4" /> Back to Trade Browser
        </Link>
        <div className="mt-6 rounded-md border border-sev-flag/40 px-4 py-3 status-error">
          <p className="font-ui text-sm">{error}</p>
        </div>
      </div>
    );
  }

  const stats = data
    ? [
        { label: 'Trades', value: data.trade_count.toLocaleString() },
        { label: 'Members', value: data.member_count.toLocaleString() },
        { label: 'Buys / Sells', value: `${data.buys} / ${data.sells}` },
        { label: 'Total notional', value: fmtMoney(data.total_notional) },
        {
          label: 'Avg 30d return',
          value: <span style={{ color: retColor(data.avg_return_30d) }}>{fmtSigned(data.avg_return_30d)}</span>,
        },
      ]
    : undefined;

  return (
    <div>
      <Link
        to="/trades"
        className="inline-flex items-center gap-1.5 font-ui text-sm text-content-muted transition-colors hover:text-accent"
      >
        <ArrowLeftIcon className="h-4 w-4" /> Back to Trade Browser
      </Link>

      <div className="mt-4">
        <PageHeader
          eyebrow="CapitolScope · Asset"
          title={ticker}
          subtitle={
            data?.security_name
              ? `${data.security_name}${data.sector ? ` · ${data.sector}` : ''}`
              : 'Congressional trading flow for this asset across public STOCK Act filings.'
          }
          stats={stats}
        />
      </div>

      {data && (
        <div className="card mt-6 overflow-hidden">
          {data.trades.length === 0 ? (
            <div className="p-10 text-center">
              <p className="mb-2 font-display text-lg text-content">No trades found</p>
              <p className="font-ui text-sm text-content-faint">No disclosed congressional trades for {ticker}.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-surface-inset">
                  <tr>
                    {['Date', 'Member', 'Side', 'Amount', '30d'].map((h) => (
                      <th
                        key={h}
                        className={`px-6 py-3 font-data text-[11px] uppercase tracking-[0.12em] text-content-faint ${
                          h === 'Amount' || h === '30d' ? 'text-right' : 'text-left'
                        }`}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {data.trades.map((t, i) => (
                    <tr key={i} className="transition-colors hover:bg-surface-inset">
                      <td className="whitespace-nowrap px-6 py-3 font-data text-sm tabular-nums text-content-muted">
                        {t.date}
                      </td>
                      <td className="whitespace-nowrap px-6 py-3">
                        {t.member_id ? (
                          <Link
                            to={`/members/${t.member_id}`}
                            className="font-ui text-sm text-content transition-colors hover:text-accent hover:underline"
                          >
                            {t.member}
                          </Link>
                        ) : (
                          <span className="font-ui text-sm text-content">{t.member}</span>
                        )}{' '}
                        <PartyTag party={t.party} />
                      </td>
                      <td className="whitespace-nowrap px-6 py-3">
                        <span
                          className="font-data text-xs tracking-wide"
                          style={{ color: t.direction === 'BUY' ? '#43a897' : '#d6707b' }}
                        >
                          {t.direction}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-6 py-3 text-right font-data text-sm tabular-nums text-brass-500">
                        {fmtMoney(t.amount)}
                      </td>
                      <td
                        className="whitespace-nowrap px-6 py-3 text-right font-data text-sm tabular-nums"
                        style={{ color: retColor(t.signed_return_30d) }}
                      >
                        {fmtSigned(t.signed_return_30d)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="border-t border-line bg-surface-inset px-6 py-3">
            <p className="font-data text-[10px] leading-relaxed text-content-faint">
              30d is direction-aware (a well-timed sale precedes a drop). Amounts are disclosed-range midpoints.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default AssetPage;
