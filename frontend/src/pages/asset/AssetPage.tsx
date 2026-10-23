import React, { useEffect, useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import apiClient from '../../services/api';
import type { TickerPageData } from '../../types';
import { Panel, Spinner, StatTile } from '../../components/ui';
import DisclosureRow from '../../components/trades/DisclosureRow';
import PriceTradeChart from '../../components/trades/PriceTradeChart';
import { isFutureDated, longDate } from '../../components/trades/feed';

type Side = 'all' | 'buy' | 'sell';
const PAGE = 50;

const AssetPage: React.FC = () => {
  const { ticker: rawTicker } = useParams<{ ticker: string }>();
  const ticker = (rawTicker || '').trim().toUpperCase();
  const [data, setData] = useState<TickerPageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [side, setSide] = useState<Side>('all');
  const [shown, setShown] = useState(PAGE);

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;
    setData(null);
    setError(null);
    setLoading(true);
    setSide('all');
    setShown(PAGE);
    apiClient
      .getTickerPage(ticker)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setError(`Data for ${ticker} could not be loaded. Try again in a moment.`))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  useEffect(() => {
    document.title = `${ticker}${data?.security?.name ? `: ${data.security.name}` : ''} congressional trades | CapitolScope`;
  }, [ticker, data?.security?.name]);

  const trades = useMemo(() => (data?.trades ?? []).filter((t) => !isFutureDated(t)), [data]);
  const filtered = useMemo(
    () =>
      side === 'all'
        ? trades
        : trades.filter((t) => (t.transaction_type || '').toUpperCase().startsWith(side === 'buy' ? 'P' : 'S')),
    [trades, side],
  );

  if (loading) return <Spinner label={`Loading ${ticker}`} />;

  const crumb = (
    <nav className="font-ui text-sm text-content-muted" aria-label="Breadcrumb">
      <Link to="/trades" className="hover:text-accent">
        All trades
      </Link>
      <span className="px-1.5 text-content-faint">/</span>
      <span className="text-content">{ticker}</span>
    </nav>
  );

  if (error || !data) {
    return (
      <div>
        {crumb}
        <div role="alert" className="mt-6 border-l-4 border-accent bg-surface-inset px-4 py-3 font-ui text-sm text-content">
          {error || `No data for ${ticker}.`}
        </div>
      </div>
    );
  }

  const s = data.stats;
  const name = data.security?.name;
  const sector = data.security?.sector;

  return (
    <div>
      {crumb}

      <header className="mt-4 border-b-[3px] border-content pb-6">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div className="min-w-0">
            <div className="font-ui text-[11px] font-semibold uppercase tracking-[0.12em] text-accent">Ticker</div>
            <h1 className="mt-1 break-all font-display text-[clamp(4rem,13vw,9rem)] font-extrabold leading-[0.82] text-content">
              {ticker}
            </h1>
            <p className="mt-3 font-ui text-lg text-content-muted">
              {name || 'Security not matched to a listed company'}
              {sector ? <span className="text-content-faint">, {sector}</span> : null}
            </p>
          </div>
          {data.latest_close != null && (
            <StatTile label="Last close" value={`$${data.latest_close.toLocaleString('en-US')}`} hint={longDate(data.latest_close_date)} size="lg" />
          )}
        </div>

        <div className="mt-6 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-5">
          <StatTile label="Trades" value={s.trades.toLocaleString()} />
          <StatTile label="Members" value={s.members.toLocaleString()} />
          <StatTile label="Bought / sold" value={`${s.buys.toLocaleString()} / ${s.sells.toLocaleString()}`} />
          <StatTile
            label="Filed late"
            value={s.late.toLocaleString()}
            tone={s.late > 0 ? 'accent' : 'default'}
            hint="past the 45-day limit"
          />
          <StatTile label="Most recent trade" value={s.latest_trade_date ? longDate(s.latest_trade_date) : 'None'} size="sm" />
        </div>
      </header>

      {data.prices.length > 1 && (
        <Panel title="Price and congressional trades" className="mt-8" bodyClassName="px-1 py-4">
          <PriceTradeChart prices={data.prices} trades={trades} />
        </Panel>
      )}

      <Panel
        title="Disclosed trades"
        className="mt-8"
        right={
          <div className="flex gap-1" role="group" aria-label="Filter by side">
            {(
              [
                ['all', 'All'],
                ['buy', 'Bought'],
                ['sell', 'Sold'],
              ] as [Side, string][]
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                aria-pressed={side === id}
                onClick={() => {
                  setSide(id);
                  setShown(PAGE);
                }}
                className={`border-2 px-2 py-0.5 font-ui text-xs font-semibold transition-colors ${
                  side === id ? 'border-content bg-content text-surface' : 'border-line text-content-muted hover:border-content'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        }
      >
        {filtered.length === 0 ? (
          <p className="py-10 text-center font-ui text-sm text-content-faint">
            No disclosed congressional trades in {ticker}
            {side !== 'all' ? ' for this side' : ''}.
          </p>
        ) : (
          <>
            {filtered.slice(0, shown).map((t, i, arr) => {
              const year = (t.transaction_date || '').slice(0, 4);
              const newYear = i === 0 || (arr[i - 1].transaction_date || '').slice(0, 4) !== year;
              return (
                <React.Fragment key={t.id}>
                  {newYear && (
                    <h3 className="border-b border-line pb-1 pt-4 font-display text-xl font-extrabold leading-none text-content">
                      {year || 'Date unknown'}
                    </h3>
                  )}
                  <DisclosureRow trade={t} hideTicker />
                </React.Fragment>
              );
            })}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-3 font-ui text-sm text-content-muted">
              <span>
                Showing {Math.min(shown, filtered.length).toLocaleString()} of {filtered.length.toLocaleString()}
                {data.total > trades.length ? ` (most recent ${trades.length.toLocaleString()} of ${data.total.toLocaleString()})` : ''}
              </span>
              {shown < filtered.length && (
                <button type="button" onClick={() => setShown((n) => n + PAGE)} className="btn-secondary text-sm">
                  Show more
                </button>
              )}
            </div>
          </>
        )}
      </Panel>

      <p className="mt-6 max-w-[80ch] font-ui text-xs text-content-faint">
        Source: House Clerk and Senate eFD periodic transaction reports. Members report ranges, not exact amounts.
        Trades are matched to this ticker by the symbol in the filing or by the security it was resolved to.
      </p>
    </div>
  );
};

export default AssetPage;
