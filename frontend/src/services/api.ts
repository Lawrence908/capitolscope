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
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
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
      per_page: perPage.toString(),
    });

    // Add filters to params
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.append(key, value.toString());
      }
    });

    const response = await this.client.get(`/api/v1/members/?${params}`);
    return response.data.data;
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
  async getAlertRules(): Promise<any> {
    const response = await this.client.get('/api/v1/notifications/alerts/rules');
    return response.data;
  }

  async createMemberAlert(memberId: number, alertData: any): Promise<any> {
    const response = await this.client.post(`/api/v1/notifications/alerts/member/${memberId}`, alertData);
    return response.data;
  }

  async createAmountAlert(alertData: any): Promise<any> {
    const response = await this.client.post('/api/v1/notifications/alerts/amount', alertData);
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
}

// Create and export a singleton instance
export const apiClient = new APIClient();
export default apiClient; 