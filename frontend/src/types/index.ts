// Congressional Member Types
export interface CongressMember {
  id: string; // Changed from number to string (UUID)
  bioguide_id?: string | null;
  first_name: string;
  last_name: string;
  full_name: string;
  party?: string | null;
  state?: string | null;
  district?: string | null;
  chamber?: string | null;
  office?: string | null;
  phone?: string | null;
  url?: string | null;
  image_url?: string | null;
  twitter_account?: string | null;
  facebook_account?: string | null;
  youtube_account?: string | null;
  in_office?: boolean;
  next_election?: string | null;
  trade_count?: number | null; // Changed from total_trades
  total_trade_value?: number | null; // Changed from total_value
  portfolio_value?: number | null;
  created_at: string;
  updated_at: string;
}

// Congressional Trade Types
export interface CongressionalTrade {
  id: string;
  member_id?: string;
  member_name?: string;
  member_party?: string;
  member_chamber?: string;
  member_state?: string;
  ticker?: string | null;
  asset_name?: string | null;
  asset_type?: string | null;
  transaction_type?: string | null;
  transaction_date?: string | null;
  notification_date?: string | null;
  amount_min?: number | null;
  amount_max?: number | null;
  amount_exact?: number | null;
  estimated_value?: number | null;
  filing_status?: string | null;
  owner?: string | null;
  created_at?: string;
  updated_at?: string;
}

// API Response Types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface TradeFilters {
  member_ids?: string[];
  member_names?: string[];
  parties?: string[];
  chambers?: string[];
  states?: string[];
  tickers?: string[];
  asset_types?: string[];
  transaction_types?: string[];
  owners?: string[];
  transaction_date_from?: string;
  transaction_date_to?: string;
  notification_date_from?: string;
  notification_date_to?: string;
  amount_min?: number;
  amount_max?: number;
  amount_range?: string;
  search?: string;
  sort_by?: 'transaction_date' | 'notification_date' | 'amount' | 'member_name' | 'ticker' | 'transaction_type';
  sort_order?: 'asc' | 'desc';
  page?: number;
  limit?: number;
  include_member?: boolean;
  include_security?: boolean;
  include_performance?: boolean;
}

export interface MemberFilters {
  party?: string;
  state?: string;
  chamber?: 'House' | 'Senate';
  in_office?: boolean;
  search?: string;
}

// Data Quality Types
export interface DataQualityStats {
  total_trades: number;
  trades_with_ticker: number;
  trades_without_ticker: number;
  null_ticker_percentage: number;
  unique_members: number;
  unique_tickers: number;
  amount_ranges: Record<string, number>;
  party_distribution: Record<string, number>;
  chamber_distribution: Record<string, number>;
  // Additional fields for enhanced data quality dashboard
  null_ticker_count?: number;
  null_amount_count?: number;
  null_member_count?: number;
}

// Chart Data Types
export interface ChartData {
  labels: string[];
  datasets: {
    label: string;
    data: number[];
    backgroundColor?: string | string[];
    borderColor?: string | string[];
    borderWidth?: number;
  }[];
}

// Member Profile Types
export interface MemberProfile extends CongressMember {
  recent_trades: CongressionalTrade[];
  trade_stats: {
    total_trades: number;
    total_value: number;
    avg_trade_value: number;
    purchase_count: number;
    sale_count: number;
    most_traded_tickers: Array<{
      ticker: string;
      count: number;
      total_value: number;
    }>;
  };
}

// Error Types
export interface APIError {
  detail: string;
  status_code: number;
} 
// ---- Mirror portfolios (Pro+) ----
export interface MirrorMemberRef {
  member_id: string;
  name?: string | null;
  party?: string | null;
  state?: string | null;
}

export interface MirrorPortfolio {
  id: string;
  name: string;
  description?: string | null;
  is_active: boolean;
  member_ids: string[];
  members: MirrorMemberRef[];
  member_count: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface MirrorHolding {
  security_id: string;
  ticker?: string | null;
  name?: string | null;
  sector?: string | null;
  shares: number;
  cost_basis: number;
  current_price: number;
  market_value: number;
  unrealized_gain: number;
  return_pct: number | null;
}

export interface SectorAllocation {
  sector: string;
  market_value: number;
  weight_pct: number | null;
}

export interface MirrorHoldingsTotals {
  market_value: number;
  cost_basis: number;
  unrealized_gain: number;
  realized_gain: number;
  return_pct: number | null;
  holdings_count: number;
}

export interface MemberComparisonEntry {
  member_id: string;
  member?: { id: string; name?: string | null; party?: string | null; state?: string | null; chamber?: string | null };
  totals: MirrorHoldingsTotals;
  sector_allocation: SectorAllocation[];
  top_holdings: MirrorHolding[];
}

export interface MemberComparisonResult {
  members: MemberComparisonEntry[];
  overlap: {
    count: number;
    common_securities: {
      security_id: string;
      ticker?: string | null;
      name?: string | null;
      held_by: string[];
      combined_value: number;
    }[];
  };
}

export interface MirrorHoldingsResult {
  holdings: MirrorHolding[];
  sector_allocation?: SectorAllocation[];
  totals: MirrorHoldingsTotals;
  meta?: { member_count: number; priced_trades: number };
  mirror?: MirrorPortfolio;
  member?: {
    id: string;
    name?: string | null;
    party?: string | null;
    state?: string | null;
    chamber?: string | null;
  };
}

// ---- In-app notifications (bell) ----
export interface InboxNotification {
  id: string;
  title: string;
  message: string;
  type: string | null;
  priority: string;
  is_read: boolean;
  read_at?: string | null;
  created_at?: string | null;
  extra_data: Record<string, unknown>;
}

export interface InboxResult {
  items: InboxNotification[];
  total: number;
  unread: number;
}

export interface NotificationSubscription {
  email_enabled: boolean;
  push_enabled: boolean;
  sms_enabled: boolean;
  trade_alerts: boolean;
  portfolio_updates: boolean;
  market_alerts: boolean;
  newsletter: boolean;
  email_frequency: 'instant' | 'daily' | 'weekly';
  alert_threshold: number;
}
