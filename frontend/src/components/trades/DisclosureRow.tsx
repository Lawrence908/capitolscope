import React from 'react';
import { Link } from 'react-router-dom';
import type { CongressionalTrade } from '../../types';
import {
  DisclosureGauge,
  PartyTag,
  TradeStamp,
  affiliation,
  daysToDisclose,
  fmtAmountRange,
  gaugeCaption,
} from '../ui';

const OWNER_LABEL: Record<string, string> = { SP: 'spouse', JT: 'joint', DC: 'dependent child' };

const shortDate = (iso: string | null | undefined): string => {
  if (!iso) return '';
  const d = new Date(`${iso.slice(0, 10)}T00:00:00`);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

const memberTitle = (chamber: string | null | undefined): string =>
  (chamber || '').toLowerCase().startsWith('s') ? 'Sen.' : (chamber || '').toLowerCase().startsWith('h') ? 'Rep.' : '';

/**
 * One disclosed trade in the Bulletin feed: big condensed ticker + stamp,
 * who and what, the disclosed amount range, and a disclosure gauge.
 * Used by the homepage, trade browser, ticker and member pages.
 */
const DisclosureRow: React.FC<{
  trade: CongressionalTrade;
  /** Hide the member line (e.g. on that member's own profile). */
  hideMember?: boolean;
  /** Hide the ticker block (e.g. on that ticker's page). */
  hideTicker?: boolean;
}> = ({ trade, hideMember = false, hideTicker = false }) => {
  const days = daysToDisclose(trade.transaction_date, trade.notification_date);
  const ticker = trade.ticker?.trim();
  const asset = trade.asset_name || ticker || 'Undisclosed asset';
  const owner = trade.owner ? OWNER_LABEL[trade.owner] : undefined;
  const amended = (trade.filing_status || '').toUpperCase().startsWith('A');

  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 border-b border-line py-3 sm:grid-cols-[7.5rem_minmax(0,1fr)_auto_auto]">
      {!hideTicker && (
        <div className="col-span-2 flex items-center gap-2 sm:col-span-1 sm:flex-col sm:items-start sm:gap-1">
          {ticker ? (
            <Link
              to={`/assets/${encodeURIComponent(ticker)}`}
              className="font-display text-3xl font-extrabold leading-none text-content hover:text-accent"
            >
              {ticker}
            </Link>
          ) : (
            <span className="font-display text-xl font-extrabold leading-none text-content-faint">NO TICKER</span>
          )}
          <TradeStamp type={trade.transaction_type} />
        </div>
      )}

      <div className={`min-w-0 ${hideTicker ? 'col-span-1 sm:col-span-2' : ''}`}>
        {!hideMember && (
          <div className="flex items-center gap-2">
            <PartyTag party={trade.member_party} />
            {trade.member_id ? (
              <Link to={`/members/${trade.member_id}`} className="truncate font-ui text-sm font-bold text-content hover:text-accent">
                {memberTitle(trade.member_chamber)} {trade.member_name || 'Unknown member'}
              </Link>
            ) : (
              <span className="truncate font-ui text-sm font-bold text-content">{trade.member_name || 'Unknown member'}</span>
            )}
            <span className="shrink-0 font-ui text-xs text-content-faint">
              {affiliation(trade.member_party, trade.member_state)}
            </span>
          </div>
        )}
        <Link to={`/t/${trade.id}`} className="mt-0.5 block truncate font-ui text-sm text-content-muted hover:text-content">
          {hideTicker && <TradeStamp type={trade.transaction_type} className="mr-2 align-middle" />}
          {asset}
          {trade.transaction_date ? `, traded ${shortDate(trade.transaction_date)}` : ''}
          {owner ? ` (${owner})` : ''}
          {amended ? ' (amended filing)' : ''}
        </Link>
      </div>

      <div className="text-right font-display text-xl font-extrabold leading-none tabular-nums text-content">
        {fmtAmountRange(trade.amount_min, trade.amount_max)}
      </div>

      <div className="hidden w-28 flex-col items-center sm:flex">
        {/* Amended filings are never counted as late: the filing date is the
            amendment's, not the original disclosure's. */}
        <DisclosureGauge days={amended ? null : days} size="sm" />
        <span className={`mt-0.5 font-ui text-[11px] ${!amended && days != null && days > 45 ? 'font-bold text-accent' : 'text-content-faint'}`}>
          {amended ? 'Amended filing' : gaugeCaption(days)}
        </span>
      </div>
    </div>
  );
};

export default DisclosureRow;
