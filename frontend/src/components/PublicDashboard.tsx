import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import DisclosureRow from './trades/DisclosureRow';
import { DisclosureGauge, HatchMark, PartyTag, Spinner, TradeStamp, affiliation, fmtAmountRange, fmtMoney } from './ui';
import { useAuth } from '../contexts/AuthContext';
import { usePublicHome } from '../hooks/usePublicHome';
import type { ActiveMember, NotableFiling, PublicHome, PublicTrade } from '../types/public';

/* ------------------------------------------------------------------ *
 * Homepage: "This week in congressional trading". All data comes from the
 * anonymous /public/home feed; everything here is public record.
 * ------------------------------------------------------------------ */

const FEED_PREVIEW = 30;

const parseDay = (iso: string) => new Date(`${iso.slice(0, 10)}T00:00:00`);

const longDate = (iso: string | null | undefined): string => {
  if (!iso) return '';
  const d = parseDay(iso);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

const startOfToday = () => {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
};

const relativeLabel = (iso: string): string => {
  const days = Math.round((startOfToday().getTime() - parseDay(iso).getTime()) / 86_400_000);
  if (days <= 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 7) return 'This week';
  if (days < 14) return 'Last week';
  return '';
};

const memberTitle = (chamber: string | null | undefined): string => {
  const c = (chamber || '').toLowerCase();
  return c.startsWith('s') ? 'Sen.' : c.startsWith('h') ? 'Rep.' : '';
};

/** Cents to a compact dollar figure: 310000000 -> "$3.1M". */
const compactCents = (cents: number | null | undefined) => (cents == null ? 'n/a' : fmtMoney(cents / 100));

// ---------------------------------------------------------------- hero
const Tally: React.FC<{ value: React.ReactNode; caption: React.ReactNode; children?: React.ReactNode; className?: string }> = ({
  value,
  caption,
  children,
  className = '',
}) => (
  <div className={`border-t-[3px] border-content py-3.5 ${className}`}>
    <div className="font-display text-5xl font-extrabold leading-[0.9] tabular-nums text-content sm:text-6xl">{value}</div>
    <p className="mt-1.5 max-w-[26ch] font-ui text-sm text-content-muted">{caption}</p>
    {children}
  </div>
);

const Hero: React.FC<{ home: PublicHome }> = ({ home }) => {
  const s = home.stats;
  return (
    <section className="grid gap-10 border-b-[3px] border-content pb-10 pt-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] lg:gap-12">
      <div>
        <h1 className="font-display text-[clamp(56px,9vw,132px)] font-extrabold leading-[0.84] tracking-[-0.005em] text-content">
          This week in congressional trading
        </h1>
        <p className="mt-8 max-w-[44ch] font-ui text-lg text-content-muted sm:text-[19px]">
          Every stock trade members of Congress report under the STOCK Act, from House and Senate periodic
          transaction reports.
          {s.last_filing_date ? ` Most recent filing received ${longDate(s.last_filing_date)}.` : ''}
        </p>
      </div>

      <div className="grid grid-cols-2 content-end">
        <Tally
          className="pr-5"
          value={s.week_trades.toLocaleString()}
          caption={`trade${s.week_trades === 1 ? '' : 's'} disclosed in the last 7 days by ${s.week_members} member${s.week_members === 1 ? '' : 's'}`}
        />
        <Tally
          className="border-l border-l-line pl-5"
          value={s.month_trades.toLocaleString()}
          caption={
            <>
              trades disclosed in 30 days
              {s.month_amount_min != null && s.month_amount_max != null
                ? `, ${compactCents(s.month_amount_min)} to ${compactCents(s.month_amount_max)} reported`
                : ''}
            </>
          }
        />
        <div className="border-t-[3px] border-content py-3.5 pr-5">
          <DisclosureGauge
            days={s.median_days_to_disclose_30d}
            size="md"
            valueLabel={s.median_days_to_disclose_30d == null ? 'n/a' : `${s.median_days_to_disclose_30d} days`}
          />
          <p className="mt-1.5 max-w-[26ch] font-ui text-sm text-content-muted">
            median wait from trade to disclosure, last 30 days
          </p>
        </div>
        <Tally
          className="border-l border-l-line pl-5"
          value={
            <Link to="/late" className="hover:text-accent">
              {s.late_this_year.toLocaleString()}
            </Link>
          }
          caption={`trades disclosed after the 45-day limit in ${s.year}, by ${s.late_this_year_members} member${s.late_this_year_members === 1 ? '' : 's'}`}
        >
          <HatchMark className="mt-2 block h-2.5 w-full" title="Late filings" />
        </Tally>
      </div>
    </section>
  );
};

// ---------------------------------------------------------------- notable
// Rules between cards for the 1 / 2 / 4 column layouts.
const NOTABLE_BORDERS = [
  '',
  'border-t border-line sm:border-t-0 sm:border-l sm:pl-5',
  'border-t border-line lg:border-t-0 lg:border-l lg:pl-5',
  'border-t border-line sm:border-l sm:pl-5 lg:border-t-0',
];

const NotableCard: React.FC<{ card: NotableFiling; index: number }> = ({ card, index }) => {
  const t: PublicTrade = card.trade;
  return (
    <article className={`flex flex-col gap-2.5 py-5 sm:pr-5 ${NOTABLE_BORDERS[index] ?? NOTABLE_BORDERS[1]}`}>
      <div className="flex items-center gap-2 font-ui text-[13px] font-bold text-content">
        {card.kind === 'late' ? (
          <HatchMark className="h-2.5 w-[22px]" />
        ) : (
          <span aria-hidden="true" className="inline-block h-2.5 w-[22px] bg-content" />
        )}
        {card.label}
      </div>
      <h3 className="font-display text-[28px] font-extrabold leading-[0.98] text-content">
        <Link to={`/t/${t.id}`} className="hover:text-accent">
          {card.headline}
        </Link>
      </h3>
      <div className="flex flex-wrap items-center gap-2 font-ui text-sm text-content-muted">
        {t.member_party && <PartyTag party={t.member_party} />}
        <Link to={`/members/${t.member_id}`} className="hover:text-content">
          {[memberTitle(t.member_chamber), t.member_name].filter(Boolean).join(' ')}
          {affiliation(t.member_party, t.member_state) ? `, ${affiliation(t.member_party, t.member_state)}` : ''}
        </Link>
      </div>
      <div className="mt-auto font-display text-2xl font-extrabold leading-[1.15] text-content">
        <TradeStamp type={t.transaction_type} className="mr-1.5 align-middle" />
        {t.ticker || 'NO TICKER'}
        <br />
        <span className="tabular-nums">{fmtAmountRange(t.amount_min, t.amount_max)}</span>
      </div>
      <p className="font-ui text-sm text-content-muted">
        Traded {longDate(t.transaction_date)}. Filed {longDate(t.notification_date)}.
      </p>
    </article>
  );
};

const SectionHead: React.FC<{ title: string; note?: React.ReactNode }> = ({ title, note }) => (
  <div className="mb-1.5 flex flex-wrap items-end justify-between gap-x-4 gap-y-1">
    <h2 className="font-display text-[40px] font-extrabold leading-none text-content">{title}</h2>
    {note && <p className="font-ui text-sm text-content-muted">{note}</p>}
  </div>
);

const Notable: React.FC<{ home: PublicHome }> = ({ home }) => {
  if (!home.notable.length) return null;
  return (
    <section className="pt-8">
      <SectionHead
        title="Notable filings"
        note={`Chosen for size, lateness or committee overlap. Filed in the last ${home.notable_window_days} days.`}
      />
      <div className="grid border-y-[3px] border-content sm:grid-cols-2 lg:grid-cols-4">
        {home.notable.map((card, i) => (
          <NotableCard key={`${card.kind}-${card.trade.id}`} card={card} index={i} />
        ))}
      </div>
    </section>
  );
};

// ---------------------------------------------------------------- feed
const LatestFeed: React.FC<{ home: PublicHome }> = ({ home }) => {
  const [showAll, setShowAll] = useState(false);
  const rows = showAll ? home.latest : home.latest.slice(0, FEED_PREVIEW);

  const groups = useMemo(() => {
    const out: { date: string; trades: PublicTrade[] }[] = [];
    for (const t of rows) {
      const d = (t.notification_date || '').slice(0, 10);
      const last = out[out.length - 1];
      if (last && last.date === d) last.trades.push(t);
      else out.push({ date: d, trades: [t] });
    }
    return out;
  }, [rows]);

  return (
    <section>
      <SectionHead title="Latest disclosures" note="Newest filing first. The gauge shows days from trade to disclosure; 45 is the limit." />
      <div className="border-t-[3px] border-content">
        {groups.length === 0 && (
          <p className="py-6 font-ui text-sm text-content-muted">No disclosures filed in the last {home.latest_window_days} days.</p>
        )}
        {groups.map((g) => (
          <div key={g.date}>
            <div className="flex items-baseline gap-3 border-b border-line pb-1.5 pt-3.5 font-ui text-sm font-bold text-content">
              Filed {longDate(g.date)}
              <span className="font-normal text-content-faint">{relativeLabel(g.date)}</span>
            </div>
            {g.trades.map((t) => (
              <DisclosureRow key={t.id} trade={t} />
            ))}
          </div>
        ))}
      </div>
      <div className="mt-6 flex flex-wrap gap-3">
        {!showAll && home.latest.length > FEED_PREVIEW && (
          <button type="button" onClick={() => setShowAll(true)} className="btn-secondary text-sm">
            Show all {home.latest.length} from the last {home.latest_window_days} days
          </button>
        )}
        <Link to="/trades" className="bg-content px-4 py-2 font-ui text-sm font-semibold text-surface hover:opacity-90">
          Browse every trade
        </Link>
      </div>
    </section>
  );
};

// ---------------------------------------------------------------- most active
const ActiveRow: React.FC<{ m: ActiveMember; max: number }> = ({ m, max }) => {
  const width = max > 0 ? Math.max(6, (m.trades / max) * 100) : 0;
  return (
    <div className="grid grid-cols-[22px_minmax(0,1fr)_auto] items-center gap-x-2.5 gap-y-1 border-b border-line py-2.5">
      {m.member_party ? <PartyTag party={m.member_party} /> : <span />}
      <Link to={`/members/${m.member_id}`} className="truncate font-ui text-[15px] font-semibold text-content hover:text-accent">
        {m.member_name} <span className="font-normal text-content-faint">{affiliation(m.member_party, m.member_state)}</span>
      </Link>
      <span className="font-display text-[28px] font-extrabold leading-none tabular-nums text-content">{m.trades}</span>
      <div
        className="col-span-2 col-start-2 flex h-2.5 gap-0.5"
        style={{ width: `${width}%` }}
        role="img"
        aria-label={`${m.buys} buys, ${m.sells} sells`}
        title={`${m.buys} buys, ${m.sells} sells`}
      >
        {m.buys > 0 && <span className="bg-content" style={{ flex: m.buys }} />}
        {m.sells > 0 && <span className="border-2 border-content" style={{ flex: m.sells }} />}
      </div>
    </div>
  );
};

const MostActive: React.FC<{ home: PublicHome }> = ({ home }) => {
  const max = Math.max(0, ...home.most_active.map((m) => m.trades));
  return (
    <section>
      <SectionHead title="Most active" note={`Trades disclosed, last ${home.most_active_window_days} days`} />
      <div className="border-t-[3px] border-content">
        {home.most_active.length === 0 ? (
          <p className="py-6 font-ui text-sm text-content-muted">No disclosures in this window.</p>
        ) : (
          home.most_active.map((m) => <ActiveRow key={m.member_id} m={m} max={max} />)
        )}
      </div>
      <div className="mt-2.5 flex gap-4 font-ui text-[13px] text-content-muted">
        <span className="flex items-center gap-1.5">
          <span aria-hidden="true" className="inline-block h-2.5 w-3.5 bg-content" />
          Buys
        </span>
        <span className="flex items-center gap-1.5">
          <span aria-hidden="true" className="inline-block h-2.5 w-3.5 border-2 border-content" />
          Sells
        </span>
      </div>
    </section>
  );
};

const AlertsCta: React.FC = () => {
  const { user } = useAuth();
  return (
    <div className="mt-9 bg-surface-inset p-5">
      <h3 className="font-display text-[26px] font-extrabold leading-none text-content">Know the day they file</h3>
      <p className="mb-3.5 mt-2 font-ui text-sm text-content-muted">
        The data here is free to browse. A free account adds email alerts when a new disclosure names the
        members or tickers you follow, plus the comparison and scrutiny tools.
      </p>
      <Link to={user ? '/alerts' : '/register'} className="btn-secondary inline-block text-sm">
        Get alerts
      </Link>
    </div>
  );
};

// ---------------------------------------------------------------- page
const PublicDashboard: React.FC = () => {
  const { data: home, error } = usePublicHome();

  if (error) {
    return (
      <div className="section-rule py-10">
        <p className="font-ui text-content-muted">{error} Please try again in a moment.</p>
      </div>
    );
  }
  if (!home) return <Spinner label="Loading the latest disclosures" />;

  return (
    <div>
      <Hero home={home} />
      <Notable home={home} />
      <div className="grid gap-12 pb-8 pt-9 lg:grid-cols-[minmax(0,1fr)_380px]">
        <LatestFeed home={home} />
        <aside>
          <MostActive home={home} />
          <AlertsCta />
        </aside>
      </div>
    </div>
  );
};

export default PublicDashboard;
