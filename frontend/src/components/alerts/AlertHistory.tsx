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

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'sent':
        return '✅';
      case 'failed':
        return '❌';
      case 'pending':
        return '⏳';
      default:
        return '📧';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'sent':
        return 'text-accent bg-accent/10';
      case 'failed':
        return 'text-sev-flag bg-sev-flag/10';
      case 'pending':
        return 'text-sev-watch bg-sev-watch/10';
      default:
        return 'text-content-muted bg-surface-inset';
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
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent mx-auto"></div>
        <p className="text-content-muted mt-2">Loading notification history...</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-lg font-semibold text-content">Alert History</h3>
          <p className="text-content-muted">View your notification delivery history and status</p>
        </div>
        
        <div className="flex space-x-4">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="border border-line rounded-lg px-3 py-2 text-sm"
          >
            <option value="1d">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
          </select>
          
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-line rounded-lg px-3 py-2 text-sm"
          >
            <option value="all">All Status</option>
            <option value="sent">Delivered</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending</option>
          </select>
        </div>
      </div>

      {notifications.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-content-faint text-6xl mb-4">📬</div>
          <h3 className="text-lg font-medium text-content mb-2">No notifications found</h3>
          <p className="text-content-muted">
            No notifications have been sent in the selected time period.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {notifications.map((notification) => (
            <div
              key={notification.id}
              className="bg-surface-raised border border-line rounded-lg p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <span className="text-lg">
                      {getStatusIcon(notification.delivery_status)}
                    </span>
                    <h4 className="font-semibold text-content">
                      {notification.alert_name}
                    </h4>
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(notification.delivery_status)}`}>
                      {notification.delivery_status.charAt(0).toUpperCase() + notification.delivery_status.slice(1)}
                    </span>
                  </div>
                  
                  <div className="text-content-muted mb-3">
                    <strong>{notification.trade_details.member_name}</strong> made a{' '}
                    {notification.trade_details.transaction_type?.toLowerCase()} of{' '}
                    {notification.trade_details.ticker && (
                      <span className="font-medium">{notification.trade_details.ticker}</span>
                    )}
                    {notification.trade_details.amount && (
                      <span> worth {formatCurrency(notification.trade_details.amount)}</span>
                    )}
                  </div>
                  
                  <div className="flex items-center text-sm text-content-faint space-x-4">
                    <span>📅 {formatDate(notification.triggered_at)}</span>
                    <span>📧 Email notification</span>
                  </div>
                  
                  {notification.error_message && (
                    <div className="mt-3 p-3 bg-sev-flag/10 border border-sev-flag/30 rounded-lg">
                      <p className="text-sm text-sev-flag">
                        <strong>Error:</strong> {notification.error_message}
                      </p>
                    </div>
                  )}
                </div>
                
                <div className="flex space-x-2">
                  {notification.delivery_status === 'failed' && (
                    <button className="px-3 py-1 text-xs font-medium text-sev-info bg-sev-info/10 hover:bg-sev-info/10 rounded">
                      Retry
                    </button>
                  )}
                  <button className="px-3 py-1 text-xs font-medium text-content-muted bg-surface-inset hover:bg-surface-inset rounded">
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
