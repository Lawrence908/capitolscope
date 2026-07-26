import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../services/api';

export interface TradeAlert {
  id: string;
  name: string;
  alert_type: 'member_trades' | 'amount_threshold' | 'ticker_trades';
  target_id?: number;
  /** Congress member UUID for member_trades (API) */
  target_member_id?: string;
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
  /** Prefer this for member alerts (UUID string) */
  target_member_id?: string;
  target_symbol?: string;
  target_name?: string;
  threshold_value?: number;
}

const ALERT_TYPES = ['member_trades', 'amount_threshold', 'ticker_trades'] as const;

function mapApiRuleToTradeAlert(r: Record<string, unknown>): TradeAlert {
  const rawType = String(r.alert_type ?? '');
  const alert_type = ALERT_TYPES.includes(rawType as (typeof ALERT_TYPES)[number])
    ? (rawType as TradeAlert['alert_type'])
    : 'member_trades';

  return {
    id: String(r.id),
    name: String(r.name ?? 'Alert'),
    alert_type,
    target_id: typeof r.target_id === 'number' ? r.target_id : undefined,
    target_member_id: r.target_member_id ? String(r.target_member_id) : undefined,
    target_symbol: r.target_symbol ? String(r.target_symbol) : undefined,
    target_name: r.target_name ? String(r.target_name) : undefined,
    threshold_value: typeof r.threshold_value === 'number' ? r.threshold_value : undefined,
    is_active: Boolean(r.is_active),
    created_at: String(r.created_at ?? ''),
    updated_at: String(r.updated_at ?? ''),
  };
}

export const useAlerts = () => {
  const [alerts, setAlerts] = useState<TradeAlert[]>([]);
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAlerts = useCallback(async (opts?: { silent?: boolean }) => {
    try {
      if (!opts?.silent) {
        setLoading(true);
      }
      setError(null);
      const { items } = await apiClient.getAlertRules(100);
      const mapped = (items as Record<string, unknown>[]).map(mapApiRuleToTradeAlert);
      setAlerts(mapped);
    } catch (err: unknown) {
      const errorMessage =
        err && typeof err === 'object' && 'detail' in err
          ? String((err as { detail: string }).detail)
          : err instanceof Error
            ? err.message
            : 'Failed to load alerts';
      setError(errorMessage);
      console.error('Failed to fetch alerts:', err);
      setAlerts([]);
    } finally {
      if (!opts?.silent) {
        setLoading(false);
      }
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      setStats({
        activeAlerts: alerts.filter((a) => a.is_active).length,
        notificationsToday: 0,
        totalTriggered: 0,
        deliveryRate: 95,
      });
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  }, [alerts]);

  const createAlert = async (alertData: CreateAlertData): Promise<TradeAlert> => {
    let newId: string | undefined;

    switch (alertData.alert_type) {
      case 'member_trades': {
        const mid =
          alertData.target_member_id ??
          (alertData.target_id != null ? String(alertData.target_id) : '');
        if (!mid) {
          throw new Error('Member is required for member trade alerts');
        }
        const env = (await apiClient.createMemberAlert(mid, {
          name: alertData.name,
          member_name: alertData.target_name,
        })) as { data?: { alert_rule_id?: number } };
        newId =
          env?.data?.alert_rule_id != null ? String(env.data.alert_rule_id) : undefined;
        break;
      }
      case 'amount_threshold': {
        if (alertData.threshold_value == null || Number.isNaN(Number(alertData.threshold_value))) {
          throw new Error('A valid threshold amount is required');
        }
        const env = (await apiClient.createAmountAlert({
          name: alertData.name,
          threshold: Number(alertData.threshold_value),
        })) as { data?: { alert_rule_id?: number } };
        newId =
          env?.data?.alert_rule_id != null ? String(env.data.alert_rule_id) : undefined;
        break;
      }
      case 'ticker_trades': {
        const sym = alertData.target_symbol?.trim();
        if (!sym) {
          throw new Error('Ticker symbol is required');
        }
        const env = (await apiClient.createTickerAlert(sym.toUpperCase(), {
          name: alertData.name,
          company_name: alertData.target_name,
        })) as { data?: { alert_rule_id?: number } };
        newId =
          env?.data?.alert_rule_id != null ? String(env.data.alert_rule_id) : undefined;
        break;
      }
      default:
        throw new Error('Unknown alert type');
    }

    await fetchAlerts({ silent: true });
    const fresh = await apiClient.getAlertRules(100);
    const mapped = (fresh.items as Record<string, unknown>[]).map(mapApiRuleToTradeAlert);
    const created =
      (newId && mapped.find((a) => a.id === newId)) ||
      mapped.find((a) => a.name === alertData.name) ||
      mapped[mapped.length - 1];
    if (!created) {
      throw new Error('Alert created but could not refresh list');
    }
    return created;
  };

  const updateAlert = async (alertId: string, updates: Partial<TradeAlert>): Promise<TradeAlert> => {
    await apiClient.updateAlertRule(alertId, updates as Record<string, unknown>);
    await fetchAlerts({ silent: true });
    const refreshed = (await apiClient.getAlertRules(100)).items as Record<string, unknown>[];
    const found = refreshed.map(mapApiRuleToTradeAlert).find((a) => a.id === alertId);
    if (!found) {
      throw new Error('Alert not found after update');
    }
    return found;
  };

  const deleteAlert = async (alertId: string): Promise<void> => {
    await apiClient.deleteAlertRule(alertId);
    await fetchAlerts({ silent: true });
  };

  const toggleAlert = async (alertId: string, isActive: boolean): Promise<void> => {
    await apiClient.updateAlertRule(alertId, { is_active: isActive });
    await fetchAlerts({ silent: true });
  };

  useEffect(() => {
    void fetchAlerts();
  }, [fetchAlerts]);

  useEffect(() => {
    void fetchStats();
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
