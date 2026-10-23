import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import apiClient from '../../services/api';
import type { TradeDetail } from '../../types';
import {
  DISCLOSURE_LIMIT_DAYS,
  DisclosureGauge,
  HatchMark,
  PartyTag,
  Spinner,
  affiliation,
  daysToDisclose,
  fmtAmountRange,
} from '../../components/ui';
import DisclosureRow from '../../components/trades/DisclosureRow';
import { OWNER_LABEL, isFutureDated, longDate, memberTitle, xIntentUrl } from '../../components/trades/feed';

const verbOf = (type: string | null | undefined): { stamp: string; verb: string } => {
  const t = (type || '').toUpperCase();
  if (t.startsWith('P')) return { stamp: 'BOUGHT', verb: 'bought' };
  if (t.startsWith('S')) return { stamp: 'SOLD', verb: 'sold' };
  if (t.startsWith('E')) return { stamp: 'EXCHANGED', verb: 'exchanged' };
  return { stamp: 'TRADED', verb: 'traded' };
};

/** Card-size stamp: BOUGHT is a filled ink box, SOLD an outlined one. */
const BigStamp: React.FC<{ type: string | null | undefined }> = ({ type }) => {
  const { stamp } = verbOf(type);
  const filled = stamp === 'BOUGHT';
  return (
    <span
      className={`inline-block border-[3px] border-content px-3 pb-0.5 pt-1 font-display text-4xl font-extrabold uppercase leading-none tracking-[0.04em] sm:text-5xl ${
        filled ? 'bg-content text-surface' : 'text-content'
      }`}
    >
      {stamp}
    </span>
  );
};

// Inside the inverted slab the gauge's ink must be the slab's foreground.
const SLAB_GAUGE_VARS = {
  '--content': 'var(--on-slab)',
  '--content-faint': 'var(--slab-muted)',
  '--surface-inset': 'var(--slab-muted)',
} as React.CSSProperties;

const SLAB_HATCH_VARS = { '--hatch': 'var(--on-slab)' } as React.CSSProperties;

const ShareButtons: React.FC<{ text: string }> = ({ text }) => {
  const [copied, setCopied] = useState(false);
  const url = typeof window !== 'undefined' ? window.location.href : '';
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = url;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };
  return (
    <>
      <button type="button" onClick={copy} className="btn-secondary text-sm" aria-live="polite">
        {copied ? 'Link copied' : 'Copy link'}
      </button>
      <a href={xIntentUrl(text, url)} target="_blank" rel="noopener noreferrer" className="btn-secondary text-sm">
        Post on X
      </a>
    </>
  );
};

const TradePage: React.FC = () => {
  const { tradeId } = useParams<{ tradeId: string }>();
  const [trade, setTrade] = useState<TradeDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!tradeId) return;
    let cancelled = false;
    setLoading(true);
    setTrade(null);
    setNotFound(false);
    setError(null);
    apiClient
      .getTradeDetail(tradeId)
      .then((d) => !cancelled && setTrade(d))
      .catch((e) => {
        if (cancelled) return;
        if (e?.response?.status === 404) setNotFound(true);
        else setError('This trade could not be loaded. Try again in a moment.');
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [tradeId]);

  const ticker = trade?.ticker?.trim() || trade?.security?.ticker || '';
  const m = trade?.member;
  const title = memberTitle(m?.chamber);
  const fullName = [title, m?.name || trade?.member_name || 'Unknown member'].filter(Boolean).join(' ');
  const aff = affiliation(m?.party, m?.state);
  const amount = trade ? fmtAmountRange(trade.amount_min, trade.amount_max) : '';
  const { verb } = verbOf(trade?.transaction_type);
  const company = trade?.security?.name || trade?.asset_name || trade?.raw_asset_description || '';

  useEffect(() => {
    if (trade) document.title = `${fullName} ${verb} ${ticker || company} | CapitolScope`;
  }, [trade, fullName, verb, ticker, company]);

  if (loading) return <Spinner label="Loading trade" />;

  if (notFound || (!trade && !error)) {
    return (
      <div className="py-12">
        <div className="font-ui text-[11px] font-semibold uppercase tracking-[0.12em] text-accent">Trade</div>
        <h1 className="mt-2 font-display text-6xl font-extrabold leading-[0.9] text-content">Trade not found</h1>
        <p className="mt-3 max-w-[60ch] font-ui text-content-muted">
          No disclosed trade matches this link. It may have been removed after a filing was corrected.
        </p>
        <Link to="/trades" className="btn-primary mt-6 inline-block">
          Browse all trades
        </Link>
      </div>
    );
  }

  if (error || !trade) {
    return (
      <div role="alert" className="mt-6 border-l-4 border-accent bg-surface-inset px-4 py-3 font-ui text-sm text-content">
        {error}
      </div>
    );
  }

  const days = trade.days_to_disclose ?? daysToDisclose(trade.transaction_date, trade.notification_date);
  const amended = trade.is_amended;
  const late = trade.is_late;
  const owner = trade.owner && trade.owner !== 'C' ? OWNER_LABEL[trade.owner] : null;
  const p = trade.prices;
  const priceLine =
    p && p.at_trade != null
      ? `$${p.at_trade.toLocaleString('en-US')} a share then${
          p.at_disclosure != null ? `, $${p.at_disclosure.toLocaleString('en-US')} at disclosure` : ''
        }`
      : null;

  const shareText = `${fullName}${aff ? ` (${aff})` : ''} ${verb} ${amount} of ${ticker || company}${
    trade.transaction_date ? ` on ${longDate(trade.transaction_date)}` : ''
  }.${
    trade.notification_date
      ? ` Disclosed ${longDate(trade.notification_date)}${days != null && !amended ? `: ${days} day${days === 1 ? '' : 's'} later` : ''}.`
      : ''
  }${late ? ` The limit is ${DISCLOSURE_LIMIT_DAYS}.` : ''}`;

  const sameFiling = trade.related.same_filing.items.filter((t) => !isFutureDated(t));
  const sameTicker = trade.related.same_ticker_by_member.items.filter((t) => !isFutureDated(t));

  return (
    <div>
      <nav className="font-ui text-sm text-content-muted" aria-label="Breadcrumb">
        <Link to="/trades" className="hover:text-accent">
          All trades
        </Link>
        {m?.id && (
          <>
            <span className="px-1.5 text-content-faint">/</span>
            <Link to={`/members/${m.id}`} className="hover:text-accent">
              {m.name}
            </Link>
          </>
        )}
        {ticker && (
          <>
            <span className="px-1.5 text-content-faint">/</span>
            <span className="text-content">{ticker}</span>
          </>
        )}
      </nav>

      {/* The card: web twin of the shareable trade card. */}
      <article className="mt-4 border border-l-[8px] border-line border-l-accent bg-surface-raised">
        <div className="px-5 pb-6 pt-5 sm:px-10 sm:pt-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex min-w-0 items-center gap-2.5">
              <PartyTag party={m?.party} />
              {m?.id ? (
                <Link to={`/members/${m.id}`} className="font-ui text-xl font-bold text-content hover:text-accent sm:text-2xl">
                  {fullName}
                  {aff ? `, ${aff}` : ''}
                </Link>
              ) : (
                <span className="font-ui text-xl font-bold text-content sm:text-2xl">
                  {fullName}
                  {aff ? `, ${aff}` : ''}
                </span>
              )}
            </div>
            <div className="font-ui sm:text-right">
              <div className="text-lg font-bold text-content">
                {amended ? 'Amended filing' : 'Disclosed'} {longDate(trade.notification_date) || 'date unknown'}
              </div>
              <div className="text-content-muted">Traded {longDate(trade.transaction_date) || 'date unknown'}</div>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap items-end gap-x-8 gap-y-4">
            {ticker ? (
              <Link
                to={`/assets/${encodeURIComponent(ticker)}`}
                className="break-all font-display text-[clamp(5rem,17vw,11rem)] font-extrabold leading-[0.8] text-content hover:text-accent"
              >
                {ticker}
              </Link>
            ) : (
              <span className="font-display text-[clamp(2.5rem,7vw,4.5rem)] font-extrabold leading-[0.9] text-content">
                {company || 'Undisclosed asset'}
              </span>
            )}
            <div className="pb-1">
              <BigStamp type={trade.transaction_type} />
              {ticker && company && <p className="mt-3 font-ui text-xl text-content-muted">{company}</p>}
              {priceLine && <p className="font-ui text-xl text-content-muted">{priceLine}</p>}
            </div>
          </div>

          <div className="mt-5 font-display text-[clamp(2.75rem,7vw,4.75rem)] font-extrabold leading-none tabular-nums text-content">
            {amount}
          </div>

          <dl className="mt-5 grid grid-cols-1 gap-x-8 gap-y-2 font-ui text-sm sm:grid-cols-[auto_1fr]">
            {owner && (
              <>
                <dt className="font-semibold text-content-faint">Owner</dt>
                <dd className="text-content">{owner}</dd>
              </>
            )}
            {trade.raw_asset_description && (
              <>
                <dt className="font-semibold text-content-faint">As filed</dt>
                <dd className="text-content">{trade.raw_asset_description}</dd>
              </>
            )}
            {(trade.security?.sector || trade.asset_type) && (
              <>
                <dt className="font-semibold text-content-faint">Asset</dt>
                <dd className="text-content">
                  {[trade.asset_type, trade.security?.sector].filter(Boolean).join(', ')}
                </dd>
              </>
            )}
            {trade.comment && /[a-z0-9]/i.test(trade.comment) && (
              <>
                <dt className="font-semibold text-content-faint">Filer comment</dt>
                <dd className="text-content">{trade.comment}</dd>
              </>
            )}
          </dl>
        </div>

        {/* Disclosure timing slab */}
        <div className="slab grid grid-cols-1 items-center gap-6 px-5 py-6 sm:grid-cols-[minmax(0,1fr)_auto] sm:px-10">
          <div>
            <div className="font-display text-6xl font-extrabold uppercase leading-none tabular-nums sm:text-7xl">
              {amended ? 'Amended' : days != null ? `${days} day${days === 1 ? '' : 's'}` : 'Unknown'}
            </div>
            <p className="mt-2 font-ui text-base text-slab-muted">
              {amended
                ? `Traded ${longDate(trade.transaction_date)}, amended filing ${longDate(trade.notification_date)}.`
                : days != null
                  ? `Traded ${longDate(trade.transaction_date)}, disclosed ${longDate(trade.notification_date)}: ${days} day${
                      days === 1 ? '' : 's'
                    } to disclose; the limit is ${DISCLOSURE_LIMIT_DAYS}.`
                  : 'The disclosure date is not recorded for this trade.'}
            </p>
            {late && (
              <p className="mt-3 flex items-center gap-3 font-ui text-base font-bold" style={SLAB_HATCH_VARS}>
                <HatchMark className="h-4 w-10" />
                Filed {trade.days_late} day{trade.days_late === 1 ? '' : 's'} past the {DISCLOSURE_LIMIT_DAYS}-day STOCK Act limit.
              </p>
            )}
            {amended && (
              <p className="mt-3 max-w-[60ch] font-ui text-sm text-slab-muted">
                This is an amended filing. Its date is when the amendment was filed, so the gap from the trade is not
                counted as a late disclosure.
              </p>
            )}
          </div>
          <div style={SLAB_GAUGE_VARS} className="justify-self-center">
            <DisclosureGauge days={amended ? null : days} size="lg" showValue={false} />
          </div>
        </div>
      </article>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        {trade.document_url ? (
          <a href={trade.document_url} target="_blank" rel="noopener noreferrer" className="btn-primary text-sm">
            View original filing
          </a>
        ) : (
          <span className="font-ui text-sm text-content-faint">Original filing link unavailable</span>
        )}
        <ShareButtons text={shareText} />
      </div>
      {trade.doc_id && (
        <p className="mt-2 font-ui text-xs text-content-faint">
          {m?.chamber === 'Senate' ? 'Senate eFD report' : 'House Clerk document'} {trade.doc_id}
          {trade.document_url_derived ? '. Link built from the document id.' : ''}
        </p>
      )}

      <div className="mt-10 grid grid-cols-1 gap-10 lg:grid-cols-2">
        <section className="section-rule">
          <div className="flex items-baseline justify-between gap-3 py-3">
            <h2 className="font-display text-3xl font-extrabold leading-none text-content">Other trades in this filing</h2>
            {trade.related.same_filing.total > 0 && (
              <span className="font-ui text-sm text-content-faint">{trade.related.same_filing.total.toLocaleString()}</span>
            )}
          </div>
          {sameFiling.length === 0 ? (
            <p className="border-t border-line py-6 font-ui text-sm text-content-faint">This filing reports no other trades.</p>
          ) : (
            <div className="border-t border-line">
              {sameFiling.map((t) => (
                <DisclosureRow key={t.id} trade={t} hideMember />
              ))}
              {trade.related.same_filing.total > sameFiling.length && (
                <p className="pt-3 font-ui text-xs text-content-faint">
                  Showing {sameFiling.length} of {trade.related.same_filing.total.toLocaleString()}.
                </p>
              )}
            </div>
          )}
        </section>

        {ticker && (
          <section className="section-rule">
            <div className="flex items-baseline justify-between gap-3 py-3">
              <h2 className="font-display text-3xl font-extrabold leading-none text-content">
                Other {ticker} trades by {m?.name || 'this member'}
              </h2>
              {trade.related.same_ticker_by_member.total > 0 && (
                <span className="font-ui text-sm text-content-faint">
                  {trade.related.same_ticker_by_member.total.toLocaleString()}
                </span>
              )}
            </div>
            {sameTicker.length === 0 ? (
              <p className="border-t border-line py-6 font-ui text-sm text-content-faint">
                No other disclosed {ticker} trades by this member.
              </p>
            ) : (
              <div className="border-t border-line">
                {sameTicker.map((t) => (
                  <DisclosureRow key={t.id} trade={t} hideMember hideTicker />
                ))}
              </div>
            )}
            <Link to={`/assets/${encodeURIComponent(ticker)}`} className="mt-3 inline-block font-ui text-sm font-semibold text-content hover:text-accent">
              All congressional trades in {ticker}
            </Link>
          </section>
        )}
      </div>

      <p className="mt-10 max-w-[80ch] font-ui text-xs text-content-faint">
        Source: House Clerk and Senate eFD periodic transaction reports. Members report ranges, not exact amounts.
        Share prices are daily closes in whole dollars.
      </p>
    </div>
  );
};

export default TradePage;
