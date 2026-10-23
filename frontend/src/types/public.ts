// Shapes returned by the anonymous /api/v1/public/* feed (app/src/api/public.py).
// Amounts are cents; dates are ISO yyyy-mm-dd.
import type { CongressionalTrade } from './index';

export interface PublicTrade extends CongressionalTrade {
  member_id: string;
  member_district?: string | null;
  days_to_disclose: number | null;
}

export interface PublicHeadlineStats {
  week_trades: number;
  week_members: number;
  month_trades: number;
  month_members: number;
  month_amount_min: number | null;
  month_amount_max: number | null;
  median_days_to_disclose_30d: number | null;
  late_this_year: number;
  late_this_year_members: number;
  year: number;
  last_filing_date: string | null;
}

export interface NotableFiling {
  kind: 'late' | 'bracket' | 'committee';
  label: string;
  headline: string;
  committee?: string;
  sector?: string | null;
  trade: PublicTrade;
}

export interface ActiveMember {
  member_id: string;
  member_name: string;
  member_party: string | null;
  member_state: string | null;
  member_chamber: string | null;
  member_district: string | null;
  trades: number;
  buys: number;
  sells: number;
}

export interface PublicHome {
  generated_at: string;
  disclosure_limit_days: number;
  stats: PublicHeadlineStats;
  latest: PublicTrade[];
  latest_window_days: number;
  notable: NotableFiling[];
  notable_window_days: number;
  most_active: ActiveMember[];
  most_active_window_days: number;
}

export interface LateFiler {
  member_id: string;
  member_name: string;
  member_party: string | null;
  member_state: string | null;
  member_chamber: string | null;
  member_district: string | null;
  late_count: number;
  worst_days: number;
  median_days: number;
  filings_in_window: number | null;
  latest_late_filing: string | null;
  trades: PublicTrade[];
}

export interface PublicLate {
  generated_at: string;
  window_days: number;
  disclosure_limit_days: number;
  total_late: number;
  member_count: number;
  median_days: number | null;
  worst_days: number | null;
  members: LateFiler[];
}
