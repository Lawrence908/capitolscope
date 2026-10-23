import React, { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../../services/api';

interface AlertNotification {
  id: string;
  alert_id: string;
  alert_name: string;
  alert_type: string;
  triggered_at: string;
  trade_details: {
    member_name: string;
    ticker?: string;
    amount?: number;
    transaction_type?: string;
  };
  delivery_status: 'sent' | 'failed' | 'pending';
  delivery_method: 'email';
  error_message?: string;
}

export const AlertHistory: React.FC = () => {
  const [notifications, setNotifications] = useState<AlertNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState('7d');
  const [statusFilter, setStatusFilter] = useState('all');

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const days = Number(dateRange.replace('d', '')) || 7;
      const data = (await apiClient.getAlertNotifications({
        days,
        status: statusFilter,
      })) as AlertNotification[];
      setNotifications(data);
    } catch (error) {
      console.error('Failed to load notifications:', error);
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  }, [dateRange, statusFilter]);

  useEffect(() => {
    void loadNotifications();
  }, [loadNotifications]);

  // Bulletin status stamps: delivered = filled ink, failed = red outline,
  // pending = ink outline.
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'sent':
        return 'border-content bg-content text-surface';
      case 'failed':
        return 'border-accent text-accent';
      case 'pending':
        return 'border-content text-content';
      default:
        return 'border-line text-content-muted';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  if (loading) {
    return (
      <div className="p-8 text-center">
        <div className="mx-auto h-8 w-8 animate-spin rounded-full border-[3px] border-line border-t-accent"></div>
        <p className="mt-3 font-ui text-[11px] font-semibold uppercase tracking-[0.14em] text-content-faint">Loading notification history</p>
      </div>
    );
  }

  return (
    <div className="py-6">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h3 className="font-display text-3xl font-extrabold leading-none text-content">Alert history</h3>
          <p className="mt-1 font-ui text-sm text-content-muted">Your notification delivery history and status</p>
        </div>
        
        <div className="flex space-x-4">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="input-field text-sm"
          >
            <option value="1d">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
          </select>
          
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="input-field text-sm"
          >
            <option value="all">All Status</option>
            <option value="sent">Delivered</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending</option>
          </select>
        </div>
      </div>

      {notifications.length === 0 ? (
        <div className="border-t border-line py-12 text-center">
          <h3 className="mb-2 font-display text-3xl font-extrabold leading-none text-content">No notifications found</h3>
          <p className="font-ui text-sm text-content-muted">
            No notifications have been sent in the selected time period.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-line border-t-2 border-content">
          {notifications.map((notification) => (
            <div
              key={notification.id}
              className="py-5 transition-colors hover:bg-surface-inset"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h4 className="font-display text-xl font-extrabold leading-none text-content">
                      {notification.alert_name}
                    </h4>
                    <span className={`border-2 px-1.5 py-px font-display text-[12px] font-extrabold uppercase leading-tight tracking-[0.04em] ${getStatusColor(notification.delivery_status)}`}>
                      {notification.delivery_status.charAt(0).toUpperCase() + notification.delivery_status.slice(1)}
                    </span>
                  </div>
                  
                  <div className="mb-3 font-ui text-sm text-content-muted">
                    <strong>{notification.trade_details.member_name}</strong> made a{' '}
                    {notification.trade_details.transaction_type?.toLowerCase()} of{' '}
                    {notification.trade_details.ticker && (
                      <span className="font-medium">{notification.trade_details.ticker}</span>
                    )}
                    {notification.trade_details.amount && (
                      <span> worth {formatCurrency(notification.trade_details.amount)}</span>
                    )}
                  </div>
                  
                  <div className="flex items-center space-x-4 font-ui text-xs text-content-faint">
                    <span className="tabular-nums">{formatDate(notification.triggered_at)}</span>
                    <span>Email notification</span>
                  </div>
                  
                  {notification.error_message && (
                    <div className="mt-3 border-l-4 border-accent bg-surface-inset p-3">
                      <p className="font-ui text-sm text-content">
                        <strong>Error:</strong> {notification.error_message}
                      </p>
                    </div>
                  )}
                </div>
                
                <div className="flex space-x-2">
                  {notification.delivery_status === 'failed' && (
                    <button className="btn-secondary px-3 py-1 text-xs">
                      Retry
                    </button>
                  )}
                  <button className="btn-outline px-3 py-1 text-xs">
                    View Details
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
