import axios, { AxiosInstance, AxiosResponse } from 'axios';
import {
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

  constructor(baseURL: string = 'http://localhost:8001') {
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor for logging
    this.client.interceptors.request.use(
      (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response) {
          const apiError: APIError = {
            detail: error.response.data?.detail || 'An error occurred',
            status_code: error.response.status,
          };
          console.error('API Error:', apiError);
          return Promise.reject(apiError);
        }
        console.error('Network Error:', error.message);
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

    const response = await this.client.get(`/api/v1/congressional/members?${params}`);
    return response.data;
  }

  async getMember(id: number): Promise<CongressMember> {
    const response = await this.client.get(`/api/v1/congressional/members/${id}`);
    return response.data;
  }

  async getMemberProfile(id: number): Promise<MemberProfile> {
    const response = await this.client.get(`/api/v1/congressional/members/${id}/profile`);
    return response.data;
  }

  // Congressional Trades
  async getTrades(
    filters: TradeFilters = {},
    page: number = 1,
    perPage: number = 50
  ): Promise<PaginatedResponse<CongressionalTrade>> {
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

    const response = await this.client.get(`/api/v1/congressional/trades?${params}`);
    return response.data;
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
    const response = await this.client.get('/api/v1/congressional/data-quality/stats');
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
    const response = await this.client.get(`/api/v1/congressional/analytics/top-trading-members?limit=${limit}`);
    return response.data;
  }

  async getTopTradedTickers(limit: number = 10): Promise<Array<{ ticker: string; count: number; total_value: number }>> {
    const response = await this.client.get(`/api/v1/congressional/analytics/top-traded-tickers?limit=${limit}`);
    return response.data;
  }

  async getTradingActivity(period: 'daily' | 'weekly' | 'monthly' = 'daily'): Promise<Array<{ date: string; count: number; volume: number }>> {
    const response = await this.client.get(`/api/v1/congressional/analytics/trading-activity?period=${period}`);
    return response.data;
  }
}

// Create and export a singleton instance
export const apiClient = new APIClient();
export default apiClient; 