import axios from 'axios';
import type { AxiosInstance } from 'axios';
import { logger, LogComponent } from '../core/logging';
import type {
  CongressMember,
  CongressionalTrade,
  PaginatedResponse,
  TradeFilters,
  MemberFilters,
  DataQualityStats,
  MemberProfile,
  APIError,
} from '../types';

class APIClient {
  private client: AxiosInstance;

  constructor(baseURL?: string) {
    // Resolve a safe base URL:
    // - In production, use HTTPS to avoid mixed-content issues
    // - Prefer explicitly provided baseURL, then VITE_API_URL, then HTTPS for prod, localhost for dev
    const resolvedEnvUrl = import.meta.env.VITE_API_URL as string | undefined;
    const isProd = !!import.meta.env.PROD;
    const defaultProdUrl = 'https://capitolscope.chrislawrence.ca';
    const defaultDevUrl = 'http://localhost:8001';
    
    // Force HTTPS in production to prevent mixed content issues
    let apiUrl = baseURL ?? (resolvedEnvUrl !== undefined ? resolvedEnvUrl : (isProd ? defaultProdUrl : defaultDevUrl));
    
    // Ensure HTTPS in production
    if (isProd && apiUrl.startsWith('http://')) {
      apiUrl = apiUrl.replace('http://', 'https://');
    }
    
    this.client = axios.create({
      baseURL: apiUrl,
      // 60s so a rare cold analytics compute (single-flight, ~16s) can't trip
      // the timeout even under load; warm hits still return in tens of ms.
      timeout: 60000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Attach JWT for protected routes (stored by AuthContext on login)
    this.client.interceptors.request.use((config) => {
      try {
        if (typeof localStorage !== 'undefined') {
          const raw = localStorage.getItem('capitolscope_tokens');
          if (raw) {
            const tokens = JSON.parse(raw) as { access_token?: string };
            if (tokens?.access_token) {
              config.headers.Authorization = `Bearer ${tokens.access_token}`;
            }
          }
        }
      } catch {
        /* ignore invalid token JSON */
      }
      return config;
    });

    // Add request interceptor for logging
    this.client.interceptors.request.use(
      (config) => {
        logger.apiRequest(
          config.method?.toUpperCase() || 'UNKNOWN',
          config.url || '',
          config.data
        );
        return config;
      },
      (error) => {
        logger.error(LogComponent.API, 'Request interceptor error', { error });
        return Promise.reject(error);
      }
    );

    // Add response interceptor for error handling with retry logic
    this.client.interceptors.response.use(
      (response) => {
        // Log successful responses
        logger.apiResponse(
          response.config.method?.toUpperCase() || 'UNKNOWN',
          response.config.url || '',
          response.status,
          response.data
        );
        return response;
      },
      async (error) => {
        const originalRequest = error.config;
        
        // Handle 429 Too Many Requests with retry
        if (error.response?.status === 429 && !originalRequest._retry) {
          originalRequest._retry = true;
          
          const retryAfter = error.response.headers['retry-after'] || 60;
          logger.warning(LogComponent.API, `Rate limited. Retrying after ${retryAfter} seconds...`, {
            url: originalRequest.url,
            retryAfter,
          });
          
          await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
          
          // Retry the request
          return this.client(originalRequest);
        }
        
        if (error.response) {
          const apiError: APIError = {
            detail: error.response.data?.detail || 'An error occurred',
            status_code: error.response.status,
          };
          logger.apiError(
            originalRequest.method?.toUpperCase() || 'UNKNOWN',
            originalRequest.url || '',
            apiError
          );
          return Promise.reject(apiError);
        }
        
        logger.error(LogComponent.API, 'Network Error', {
          message: error.message,
          url: originalRequest.url,
        });
        return Promise.reject(error);
      }
    );
  }

  // Health check
  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get('/health');
    return response.data;
  }

  // Congressional Members
  async getMembers(
    filters: MemberFilters = {},
    page: number = 1,
    perPage: number = 50
  ): Promise<PaginatedResponse<CongressMember>> {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: perPage.toString(),
    });

    const partyToCode: Record<string, string> = {
      Democratic: 'D',
      Republican: 'R',
      Independent: 'I',
    };
    if (filters.party && partyToCode[filters.party]) {
      params.append('parties', partyToCode[filters.party]);
    }
    if (filters.state) {
      params.append('states', filters.state);
    }
    if (filters.chamber) {
      params.append('chambers', filters.chamber);
    }
    if (filters.search) {
      params.append('search', filters.search);
    }

    const response = await this.client.get(`/api/v1/members/?${params}`);
    const raw = response.data?.data;
    const empty: PaginatedResponse<CongressMember> = {
      items: [],
      total: 0,
      page,
      per_page: perPage,
      pages: 0,
      has_next: false,
      has_prev: false,
    };
    if (!raw) {
      return empty;
    }
    const meta = raw.meta ?? {};
    return {
      items: raw.items ?? [],
      total: meta.total ?? 0,
      page: meta.page ?? page,
      per_page: meta.per_page ?? perPage,
      pages: meta.pages ?? 0,
      has_next: Boolean(meta.has_next),
      has_prev: Boolean(meta.has_prev),
    };
  }

  async getMember(id: string): Promise<CongressMember> {
    const response = await this.client.get(`/api/v1/members/${id}`);
    return response.data.data; // Extract the data field from the response envelope
  }

  async getMemberProfile(id: number): Promise<MemberProfile> {
    const response = await this.client.get(`/api/v1/members/${id}/profile`);
    return response.data;
  }

  // Congressional Trades
  async getTrades(
    filters: TradeFilters = {},
    page: number = 1,
    limit: number = 50
  ): Promise<PaginatedResponse<CongressionalTrade>> {
    const params = new URLSearchParams();
    params.append('page', page.toString());
    params.append('limit', limit.toString());
    
    // Handle amount_range filter
    const { amount_range, ...otherFilters } = filters;
    if (amount_range) {
      const [min, max] = amount_range.split('-');
      if (min) {
        params.append('amount_min', (parseInt(min) * 100).toString()); // Convert to cents
      }
      if (max && max !== '+') {
        params.append('amount_max', (parseInt(max) * 100).toString()); // Convert to cents
      }
      // Handle the case where max is '+' (unlimited upper bound)
      if (max === '+') {
        // Don't set amount_max, which means no upper limit
        // The backend will handle this as "greater than amount_min"
      }
    }
    
    Object.entries(otherFilters).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') return;
      if (Array.isArray(value)) {
        value.forEach((v) => params.append(key, v.toString()));
      } else {
        params.append(key, value.toString());
      }
    });
    const response = await this.client.get(`/api/v1/trades?${params}`);
    return response.data.data;
  }

  async getTrade(id: number): Promise<CongressionalTrade> {
    const response = await this.client.get(`/api/v1/congressional/trades/${id}`);
    return response.data;
  }

  async getMemberTrades(
    memberId: number,
    page: number = 1,
    perPage: number = 50
  ): Promise<PaginatedResponse<CongressionalTrade>> {
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: perPage.toString(),
    });

    const response = await this.client.get(
      `/api/v1/congressional/members/${memberId}/trades?${params}`
    );
    return response.data;
  }

  // Data Quality
  async getDataQualityStats(): Promise<DataQualityStats> {
    const response = await this.client.get('/api/v1/trades/data-quality/stats');
    return response.data;
  }

  // Search
  async searchTrades(query: string, page: number = 1, perPage: number = 50): Promise<PaginatedResponse<CongressionalTrade>> {
    const params = new URLSearchParams({
      q: query,
      page: page.toString(),
      per_page: perPage.toString(),
    });

    const response = await this.client.get(`/api/v1/congressional/trades/search?${params}`);
    return response.data;
  }

  async searchMembers(query: string, page: number = 1, perPage: number = 50): Promise<PaginatedResponse<CongressMember>> {
    const params = new URLSearchParams({
      q: query,
      page: page.toString(),
      per_page: perPage.toString(),
    });

    const response = await this.client.get(`/api/v1/congressional/members/search?${params}`);
    return response.data;
  }

  // Analytics
  async getTopTradingMembers(limit: number = 10): Promise<CongressMember[]> {
    const response = await this.client.get(`/api/v1/trades/analytics/top-trading-members?limit=${limit}`);
    return response.data.data;
  }

  async getTopTradedTickers(limit: number = 10): Promise<Array<{ ticker: string; count: number; total_value: number }>> {
    const response = await this.client.get(`/api/v1/trades/analytics/top-traded-tickers?limit=${limit}`);
    return response.data.data;
  }

  async getTradingActivity(period: 'daily' | 'weekly' | 'monthly' = 'daily'): Promise<Array<{ date: string; count: number; volume: number }>> {
    const response = await this.client.get(`/api/v1/congressional/analytics/trading-activity?period=${period}`);
    return response.data.data;
  }

  async getPartyDistribution(): Promise<Record<string, number>> {
    const response = await this.client.get('/api/v1/trades/analytics/party-distribution');
    return response.data.data;
  }

  async getChamberDistribution(): Promise<Record<string, number>> {
    const response = await this.client.get('/api/v1/trades/analytics/chamber-distribution');
    return response.data.data;
  }

  async getAmountDistribution(): Promise<Record<string, number>> {
    const response = await this.client.get('/api/v1/trades/analytics/amount-distribution');
    return response.data.data;
  }

  async getVolumeOverTime(period: 'daily' | 'weekly' | 'monthly' = 'daily'): Promise<Array<{ date: string; count: number; volume: number }>> {
    const response = await this.client.get(`/api/v1/trades/analytics/volume-over-time?period=${period}`);
    return response.data.data;
  }

  // Notification Alerts
  async getAlertRules(limit: number = 100): Promise<{ items: unknown[] }> {
    const response = await this.client.get(
      `/api/v1/notifications/alerts/rules?limit=${encodeURIComponent(String(limit))}`
    );
    const inner = response.data?.data;
    return { items: inner?.items ?? [] };
  }

  async createMemberAlert(
    memberId: string,
    alertData: Record<string, unknown>
  ): Promise<unknown> {
    const response = await this.client.post(
      `/api/v1/notifications/alerts/member/${encodeURIComponent(memberId)}`,
      alertData
    );
    return response.data;
  }

  async createAmountAlert(payload: {
    name?: string;
    threshold: number;
    description?: string;
  }): Promise<unknown> {
    const response = await this.client.post('/api/v1/notifications/alerts/amount', payload);
    return response.data;
  }

  async createTickerAlert(symbol: string, alertData: any): Promise<any> {
    const response = await this.client.post(`/api/v1/notifications/alerts/ticker/${symbol}`, alertData);
    return response.data;
  }

  async updateAlertRule(ruleId: string, updates: any): Promise<any> {
    const response = await this.client.put(`/api/v1/notifications/alerts/rules/${ruleId}`, updates);
    return response.data;
  }

  async deleteAlertRule(ruleId: string): Promise<void> {
    await this.client.delete(`/api/v1/notifications/alerts/rules/${ruleId}`);
  }

  async getAlertStats(): Promise<{
    active_alerts: number;
    notifications_today: number;
    total_triggered: number;
    delivery_rate: number;
  }> {
    const response = await this.client.get('/api/v1/notifications/alerts/stats');
    return response.data?.data ?? {
      active_alerts: 0,
      notifications_today: 0,
      total_triggered: 0,
      delivery_rate: 0,
    };
  }

  async getAlertNotifications(params?: {
    days?: number;
    status?: string;
  }): Promise<unknown[]> {
    const query = new URLSearchParams();
    if (params?.days != null) query.set('days', String(params.days));
    if (params?.status && params.status !== 'all') query.set('status', params.status);
    const qs = query.toString();
    const response = await this.client.get(
      `/api/v1/notifications/alerts/notifications${qs ? `?${qs}` : ''}`
    );
    return (response.data?.data as unknown[]) ?? [];
  }

  // ---- Scrutiny analytics ----
  async getScrutinyScores(minTrades = 10, limit = 100): Promise<import('../types/scrutiny').ScrutinyResponse> {
    const res = await this.client.get(`/api/v1/analytics/scrutiny?min_trades=${minTrades}&limit=${limit}`);
    return res.data?.data;
  }

  async getClusters(params: { windowDays?: number; minMembers?: number; limit?: number; rankBy?: string } = {}) {
    const q = new URLSearchParams({
      window_days: String(params.windowDays ?? 14),
      min_members: String(params.minMembers ?? 3),
      limit: String(params.limit ?? 60),
      rank_by: params.rankBy ?? 'notability_score',
    });
    const res = await this.client.get(`/api/v1/analytics/clusters?${q}`);
    return res.data?.data as { clusters_found: number; clusters: import('../types/scrutiny').ClusterEvent[] };
  }

  async getConflicts(minConflicts = 3, limit = 60) {
    const res = await this.client.get(`/api/v1/analytics/conflicts?min_conflicts=${minConflicts}&limit=${limit}`);
    return res.data?.data as {
      total_conflict_trades: number;
      members_flagged: number;
      leaderboard: import('../types/scrutiny').ConflictMember[];
      top_conflicts: import('../types/scrutiny').TopConflict[];
    };
  }

  async getDisclosureLag(): Promise<import('../types/scrutiny').DisclosureLag> {
    const res = await this.client.get(`/api/v1/analytics/disclosure-lag`);
    return res.data?.data;
  }

  async getTickerTrades(ticker: string): Promise<import('../types/scrutiny').TickerDetail> {
    const res = await this.client.get(`/api/v1/analytics/ticker/${encodeURIComponent(ticker)}`);
    return res.data?.data;
  }
}

// Create and export a singleton instance
export const apiClient = new APIClient();
export default apiClient; 