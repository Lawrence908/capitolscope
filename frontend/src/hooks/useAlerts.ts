import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../services/api';

export interface TradeAlert {
  id: string;
  name: string;
  alert_type: 'member_trades' | 'amount_threshold' | 'ticker_trades';
  target_id?: number;
  target_symbol?: string;
  target_name?: string;
  threshold_value?: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AlertStats {
  activeAlerts: number;
  notificationsToday: number;
  totalTriggered: number;
  deliveryRate: number;
}

export interface CreateAlertData {
  alert_type: 'member_trades' | 'amount_threshold' | 'ticker_trades';
  name: string;
  target_id?: number;
  target_symbol?: string;
  target_name?: string;
  threshold_value?: number;
}

export const useAlerts = () => {
  const [alerts, setAlerts] = useState<TradeAlert[]>([]);
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      // TODO: Replace with actual API call when notification endpoints are implemented
      // const response = await apiClient.client.get('/api/v1/notifications/alerts/rules');
      // setAlerts(response.data.data?.items || []);
      
      // Mock data for development - remove when API is ready
      const mockAlerts: TradeAlert[] = [
        {
          id: '1',
          name: 'MTG Trade Alert',
          alert_type: 'member_trades',
          target_id: 123,
          target_name: 'Marjorie Taylor Greene',
          is_active: true,
          created_at: '2024-01-15T10:00:00Z',
          updated_at: '2024-01-15T10:00:00Z',
        },
        {
          id: '2',
          name: 'Large Trades $1M+',
          alert_type: 'amount_threshold',
          threshold_value: 1000000,
          is_active: true,
          created_at: '2024-01-14T10:00:00Z',
          updated_at: '2024-01-14T10:00:00Z',
        },
      ];
      
      setAlerts(mockAlerts);
      setError(null);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load alerts';
      setError(errorMessage);
      console.error('Failed to fetch alerts:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = useCallback(async () => {
    try {
      // Mock stats for now - implement when analytics endpoint is ready
      setStats({
        activeAlerts: alerts.filter(a => a.is_active).length,
        notificationsToday: 0,
        totalTriggered: 0,
        deliveryRate: 95,
      });
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  }, [alerts]);

  const createAlert = async (alertData: CreateAlertData): Promise<TradeAlert> => {
    // TODO: Replace with actual API call when notification endpoints are implemented
    /*
    const endpoint = {
      member_trades: `/api/v1/notifications/alerts/member/${alertData.target_id}`,
      amount_threshold: '/api/v1/notifications/alerts/amount',
      ticker_trades: `/api/v1/notifications/alerts/ticker/${alertData.target_symbol}`,
    }[alertData.alert_type];

    const response = await apiClient.client.post(endpoint, alertData);
    const newAlert = response.data.data;
    */
    
    // Mock implementation for development
    const newAlert: TradeAlert = {
      id: Date.now().toString(),
      name: alertData.name,
      alert_type: alertData.alert_type,
      target_id: alertData.target_id,
      target_symbol: alertData.target_symbol,
      target_name: alertData.target_name,
      threshold_value: alertData.threshold_value,
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    
    // Update local state
    setAlerts(prev => [...prev, newAlert]);
    
    return newAlert;
  };

  const updateAlert = async (alertId: string, updates: Partial<TradeAlert>): Promise<TradeAlert> => {
    // TODO: Replace with actual API call when notification endpoints are implemented
    // const response = await apiClient.client.put(`/api/v1/notifications/alerts/rules/${alertId}`, updates);
    // const updatedAlert = response.data.data;
    
    // Mock implementation for development
    const currentAlert = alerts.find(alert => alert.id === alertId);
    if (!currentAlert) {
      throw new Error('Alert not found');
    }
    
    const updatedAlert = { ...currentAlert, ...updates, updated_at: new Date().toISOString() };
    
    // Update local state
    setAlerts(prev => prev.map(alert => alert.id === alertId ? updatedAlert : alert));
    
    return updatedAlert;
  };

  const deleteAlert = async (alertId: string): Promise<void> => {
    // TODO: Replace with actual API call when notification endpoints are implemented
    // await apiClient.client.delete(`/api/v1/notifications/alerts/rules/${alertId}`);
    
    // Mock implementation for development - just update local state
    setAlerts(prev => prev.filter(alert => alert.id !== alertId));
  };

  const toggleAlert = async (alertId: string, isActive: boolean): Promise<void> => {
    await updateAlert(alertId, { is_active: isActive });
  };

  useEffect(() => {
    fetchAlerts();
  }, []);

  useEffect(() => {
    if (alerts.length >= 0) {
      fetchStats();
    }
  }, [alerts, fetchStats]);

  return {
    alerts,
    stats,
    loading,
    error,
    refetch: fetchAlerts,
    createAlert,
    updateAlert,
    deleteAlert,
    toggleAlert,
  };
};
