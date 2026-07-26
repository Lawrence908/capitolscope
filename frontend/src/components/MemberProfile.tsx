import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeftIcon, DocumentTextIcon, ChartBarIcon, UserIcon } from '@heroicons/react/24/outline';
import { apiClient } from '../services/api';
import type { CongressMember, CongressionalTrade } from '../types';
import { Panel, Spinner, StatTile, PartyTag, fmtMoney } from './ui';

const Pill: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span className="rounded-sm bg-surface-inset px-2 py-0.5 font-data text-[11px] uppercase tracking-[0.1em] text-content-muted">
    {children}
  </span>
);

const MemberProfile: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [member, setMember] = useState<CongressMember | null>(null);
  const [recentTrades] = useState<CongressionalTrade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMemberData = async () => {
      if (!id) return;

      try {
        setLoading(true);
        // Use the proper getMember API endpoint
        const memberData = await apiClient.getMember(id);
        setMember(memberData);
      } catch (err) {
        setError('Failed to load member data');
        console.error('Error fetching member:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchMemberData();
  }, [id]);

  if (loading) {
    return <Spinner label="Loading profile" />;
  }

  if (error || !member) {
    return (
      <div className="card p-6">
        <Link to="/members" className="btn-secondary mb-4 inline-flex items-center text-sm">
          <ArrowLeftIcon className="mr-2 h-4 w-4" />
          Back to Members
        </Link>
        <div className="text-center">
          <h2 className="mb-2 font-display text-xl text-content">{error || 'Member not found'}</h2>
          <p className="font-ui text-sm text-content-faint">The requested member could not be found.</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <Link to="/members" className="btn-secondary inline-flex items-center text-sm">
          <ArrowLeftIcon className="mr-2 h-4 w-4" />
          Back to Members
        </Link>
        <div className="font-data text-[11px] uppercase tracking-[0.1em] text-content-faint">
          Updated {new Date().toLocaleDateString()}
        </div>
      </div>

      {/* Member Info Card */}
      <div className="card p-4 lg:p-6">
        <div className="flex flex-col items-start space-y-4 sm:flex-row sm:space-x-6 sm:space-y-0">
          <div className="flex-shrink-0">
            <div className="flex h-20 w-20 items-center justify-center rounded-full border border-line bg-surface-inset lg:h-24 lg:w-24">
              <UserIcon className="h-10 w-10 text-content-faint lg:h-12 lg:w-12" />
            </div>
          </div>
          <div className="flex-1">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
              <h1 className="font-display text-3xl font-medium text-content">{member.full_name}</h1>
              <Link
                to="/scrutiny"
                className="font-data text-[11px] uppercase tracking-[0.1em] text-accent hover:text-accent-strong"
              >
                View in Scrutiny →
              </Link>
            </div>
            <div className="mb-5 flex flex-wrap items-center gap-2">
              {member.party && <PartyTag party={member.party} />}
              {member.chamber && <Pill>{member.chamber}</Pill>}
              {member.state && <Pill>{member.state}</Pill>}
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <StatTile label="Total Trades" value={member.trade_count?.toLocaleString() || '—'} />
              <StatTile
                label="Total Volume"
                value={member.total_trade_value ? fmtMoney(member.total_trade_value / 100) : '—'}
                tone="accent"
              />
              <StatTile
                label="Portfolio Value"
                value={member.portfolio_value ? fmtMoney(member.portfolio_value / 100) : '—'}
                tone="brass"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Recent Trades */}
      <div className="mt-6">
        <Panel
          title="Recent Trades"
          right={
            <Link to="/trades" className="font-data text-[11px] uppercase tracking-[0.1em] text-accent hover:text-accent-strong">
              View all trades →
            </Link>
          }
        >
          {recentTrades.length > 0 ? (
            <div className="divide-y divide-line">
              {recentTrades.map((trade) => (
                <div key={trade.id} className="flex items-center justify-between px-4 py-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-data font-medium text-content">{trade.ticker || 'Unknown'}</span>
                      <span className="font-ui text-xs capitalize text-content-faint">{trade.transaction_type}</span>
                    </div>
                    <div className="mt-0.5 font-data text-[11px] tabular-nums text-content-faint">
                      {new Date(trade.transaction_date).toLocaleDateString()}
                    </div>
                  </div>
                  <div className="ml-2 text-right font-data text-sm tabular-nums text-content">
                    {trade.estimated_value ? fmtMoney(trade.estimated_value / 100) : '—'}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="px-4 py-10 text-center">
              <ChartBarIcon className="mx-auto mb-3 h-10 w-10 text-content-faint" />
              <p className="font-ui text-sm text-content-faint">No recent trades found</p>
            </div>
          )}
        </Panel>
      </div>

      {/* Additional sections */}
      <div className="mt-6">
        <Panel title="Additional Information">
          <div className="flex items-center gap-3 p-4">
            <DocumentTextIcon className="h-5 w-5 flex-shrink-0 text-content-faint" />
            <p className="font-ui text-sm text-content-muted">
              More detailed member information — voting records, committee assignments, and advanced
              analytics — will be available soon.
            </p>
          </div>
        </Panel>
      </div>
    </div>
  );
};

export default MemberProfile;
