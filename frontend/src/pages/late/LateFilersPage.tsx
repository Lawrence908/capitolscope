import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import DisclosureRow from '../../components/trades/DisclosureRow';
import { DisclosureGauge, HatchMark, PageHeader, PartyTag, Spinner, Tabs, affiliation } from '../../components/ui';
import apiClient from '../../services/api';
import type { LateFiler, PublicLate } from '../../types/public';

/* ------------------------------------------------------------------ *
 * /late: members whose disclosures landed after the 45-day STOCK Act
 * limit, grouped by member. Public. Amended filings are excluded.
 * ------------------------------------------------------------------ */

type Window = '90' | '365' | '730' | '3650';

const WINDOWS: { id: Window; label: string; phrase: string }[] = [
  { id: '90', label: '90 days', phrase: 'in the last 90 days' },
  { id: '365', label: '1 year', phrase: 'in the last 12 months' },
  { id: '730', label: '2 years', phrase: 'in the last two years' },
  { id: '3650', label: 'All', phrase: 'in the last ten years' },
];

const PREVIEW_ROWS = 5;

const memberTitle = (chamber: string | null | undefined): string => {
  const c = (chamber || '').toLowerCase();
  return c.startsWith('s') ? 'Sen.' : c.startsWith('h') ? 'Rep.' : '';
};

const longDate = (iso: string | null | undefined): string => {
  if (!iso) return '';
  const d = new Date(`${iso.slice(0, 10)}T00:00:00`);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

const plural = (n: number, word: string) => `${n.toLocaleString()} ${word}${n === 1 ? '' : 's'}`;

const MemberBlock: React.FC<{ m: LateFiler; rank: number }> = ({ m, rank }) => {
  const [expanded, setExpanded] = useState(false);
  const rows = expanded ? m.trades : m.trades.slice(0, PREVIEW_ROWS);
  const share =
    m.filings_in_window && m.filings_in_window > 0
      ? `${plural(m.late_count, 'late trade')} of ${m.filings_in_window.toLocaleString()} disclosed in this window`
      : plural(m.late_count, 'late trade');

  return (
    <section className={`${rank > 1 ? 'section-rule' : ''} grid gap-x-10 gap-y-4 py-6 lg:grid-cols-[320px_minmax(0,1fr)]`} aria-labelledby={`late-${m.member_id}`}>
      <div>
        <div className="flex items-baseline gap-3">
          <span className="font-display text-2xl font-extrabold leading-none text-content-faint tabular-nums">{rank}</span>
          <h2 id={`late-${m.member_id}`} className="font-display text-[34px] font-extrabold leading-[0.95] text-content">
            <Link to={`/members/${m.member_id}`} className="hover:text-accent">
              {m.member_name}
            </Link>
          </h2>
        </div>
        <div className="mt-2 flex items-center gap-2 font-ui text-sm text-content-muted">
          {m.member_party && <PartyTag party={m.member_party} />}
          <span>
            {memberTitle(m.member_chamber)} {affiliation(m.member_party, m.member_state, m.member_district)}
          </span>
        </div>
        <p className="mt-3 flex items-center gap-2 font-ui text-sm font-semibold text-content">
          <HatchMark className="h-3 w-6" />
          {share}
        </p>
        {m.latest_late_filing && (
          <p className="mt-1 font-ui text-[13px] text-content-faint">Most recent late filing {longDate(m.latest_late_filing)}</p>
        )}

        <div className="mt-5 flex items-end gap-5">
          <div className="flex flex-col items-center">
            <DisclosureGauge days={m.worst_days} size="lg" valueLabel={`${m.worst_days} days`} />
            <span className="mt-1 font-ui text-xs font-semibold uppercase tracking-[0.08em] text-content-faint">Longest wait</span>
          </div>
        </div>
        <div className="mt-4 flex items-center gap-4">
          <DisclosureGauge days={m.median_days} size="md" valueLabel={`${m.median_days} days`} />
          <span className="max-w-[14ch] font-ui text-xs font-semibold uppercase tracking-[0.08em] text-content-faint">
            Median wait on late trades
          </span>
        </div>
      </div>

      <div className="min-w-0">
        <div className="border-t border-line">
          {rows.map((t) => (
            <DisclosureRow key={t.id} trade={t} hideMember />
          ))}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3 font-ui text-sm text-content-muted">
          {m.trades.length > PREVIEW_ROWS && (
            <button type="button" onClick={() => setExpanded((v) => !v)} className="btn-secondary text-sm">
              {expanded ? 'Show fewer' : `Show ${m.trades.length - PREVIEW_ROWS} more`}
            </button>
          )}
          {m.late_count > m.trades.length && (
            <span>
              Listing the {m.trades.length} longest waits of {m.late_count.toLocaleString()}.{' '}
              <Link to={`/members/${m.member_id}`} className="font-semibold text-content underline hover:text-accent">
                Full trade history
              </Link>
            </span>
          )}
        </div>
      </div>
    </section>
  );
};

const LateFilersPage: React.FC = () => {
  const [win, setWin] = useState<Window>('365');
  const [data, setData] = useState<PublicLate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    apiClient
      .getPublicLate(Number(win))
      .then((d) => {
        if (alive) setData(d ?? null);
      })
      .catch(() => {
        if (alive) setError('Late filings could not be loaded. Please try again in a moment.');
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [win]);

  const phrase = WINDOWS.find((w) => w.id === win)?.phrase ?? '';

  return (
    <div>
      <PageHeader
        eyebrow="Disclosure timing"
        title="Late filers"
        subtitle={
          <>
            The STOCK Act gives members of Congress 45 days to report a stock trade. These are the trades disclosed
            after that limit {phrase}, grouped by member. Amended filings are not counted. A late
            filing is a reporting delay; it says nothing on its own about the trade itself.
          </>
        }
        stats={
          data
            ? [
                { label: 'Late trades', value: data.total_late.toLocaleString() },
                { label: 'Members', value: data.member_count.toLocaleString() },
                { label: 'Median wait', value: data.median_days != null ? `${data.median_days} days` : 'n/a' },
                { label: 'Longest wait', value: data.worst_days != null ? `${data.worst_days} days` : 'n/a', tone: 'accent' as const },
              ]
            : undefined
        }
      >
        <Tabs className="mt-6" items={WINDOWS.map((w) => ({ id: w.id, label: w.label }))} active={win} onChange={setWin} />
      </PageHeader>

      {error ? (
        <p className="font-ui text-content-muted">{error}</p>
      ) : loading && !data ? (
        <Spinner label="Loading late filings" />
      ) : data && data.members.length === 0 ? (
        <p className="section-rule py-6 font-ui text-content-muted">No trades were disclosed after the 45-day limit {phrase}.</p>
      ) : (
        <div className={loading ? 'opacity-60 transition-opacity' : ''}>
          {data?.members.map((m, i) => (
            <MemberBlock key={m.member_id} m={m} rank={i + 1} />
          ))}
        </div>
      )}
    </div>
  );
};

export default LateFilersPage;
