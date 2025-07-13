// Congressional Member Types
export interface CongressMember {
  id: number;
  bioguide_id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  party: 'Republican' | 'Democratic' | 'Independent' | string;
  state: string;
  district?: string;
  chamber: 'House' | 'Senate';
  office?: string;
  phone?: string;
  url?: string;
  image_url?: string;
  twitter_account?: string;
  facebook_account?: string;
  youtube_account?: string;
  in_office: boolean;
  next_election?: string;
  total_trades?: number;
  total_value?: number;
  created_at: string;
  updated_at: string;
}

// Congressional Trade Types
export interface CongressionalTrade {
  id: number;
  member_id: number;
  member?: CongressMember;
  disclosure_date: string;
  transaction_date: string;
  owner: 'SP' | 'JT' | 'DC' | 'C';
  ticker?: string;
  asset_description: string;
  asset_type: string;
  type: 'purchase' | 'sale' | 'exchange';
  amount: string;
  amount_min?: number;
  amount_max?: number;
  comment?: string;
  ptr_link?: string;
  created_at: string;
  updated_at: string;
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
  member_id?: number;
  ticker?: string;
  asset_type?: string;
  type?: 'purchase' | 'sale' | 'exchange';
  owner?: 'SP' | 'JT' | 'DC' | 'C';
  party?: string;
  state?: string;
  chamber?: 'House' | 'Senate';
  date_from?: string;
  date_to?: string;
  amount_min?: number;
  amount_max?: number;
  search?: string;
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