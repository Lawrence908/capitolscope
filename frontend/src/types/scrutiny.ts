// Types for the Scrutiny analytics surface.

export interface ScrutinyFactor {
  weight: number;
  percentile: number;
  contribution: number; // points out of 100
  [key: string]: number | string | null;
}

export interface ScrutinyMember {
  member: string;
  party: string | null;
  chamber: string | null;
  scrutiny_score: number;
  trades: number;
  factors: {
    edge: ScrutinyFactor & { avg_alpha_30d: number; t_stat: number };
    conflict: ScrutinyFactor & { conflict_rate: number; conflict_trades: number };
    cluster: ScrutinyFactor & { cluster_involvement: number };
    lag: ScrutinyFactor & { late_pct: number | null; avg_lag_days: number | null };
  };
}

export interface ScrutinyResponse {
  weights: Record<string, number>;
  members_scored: number;
  scores: ScrutinyMember[];
}

export interface ClusterEvent {
  ticker: string;
  direction: 'BUY' | 'SELL';
  window_start: string;
  window_end: string;
  span_days: number;
  member_count: number;
  trade_count: number;
  members: string[];
  party_breakdown: Record<string, number>;
  total_notional: number | null;
  avg_return_30d: number | null;
  lead_member: string;
  lead_date: string;
  ticker_popularity: number;
  concentration: number;
  notability_score: number;
}

export interface ConflictMember {
  member: string;
  party: string | null;
  conflict_trades: number;
  conflicted_notional: number;
  top_sectors: string[];
  avg_return_30d: number | null;
}

export interface TopConflict {
  member: string;
  party: string | null;
  ticker: string;
  sector: string;
  direction: 'BUY' | 'SELL';
  date: string;
  notional: number;
  committee: string | null;
  signed_return_30d: number | null;
}

export interface LagFiler {
  member: string;
  party: string | null;
  chamber: string | null;
  late: number;
  total: number;
  avg_lag_days: number;
}

export interface DisclosureLag {
  trades_with_lag: number;
  avg_lag_days: number | null;
  median_lag_days: number | null;
  late_filings: number;
  late_pct: number | null;
  stock_act_limit_days: number;
  worst_late_filers: LagFiler[];
}
