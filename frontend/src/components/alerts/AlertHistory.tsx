import React, { useState, useEffect } from 'react';

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

  // Mock data for demonstration
  const mockNotifications: AlertNotification[] = [
    {
      id: '1',
      alert_id: 'alert-1',
      alert_name: 'MTG Trade Alert',
      alert_type: 'member_trades',
      triggered_at: '2024-01-15T14:30:00Z',
      trade_details: {
        member_name: 'Marjorie Taylor Greene',
        ticker: 'TSLA',
        amount: 15000,
        transaction_type: 'Purchase',
      },
      delivery_status: 'sent',
      delivery_method: 'email',
    },
    {
      id: '2',
      alert_id: 'alert-2',
      alert_name: 'Large Trades $100K+',
      alert_type: 'amount_threshold',
      triggered_at: '2024-01-14T09:15:00Z',
      trade_details: {
        member_name: 'Nancy Pelosi',
        ticker: 'NVDA',
        amount: 250000,
        transaction_type: 'Sale',
      },
      delivery_status: 'sent',
      delivery_method: 'email',
    },
    {
      id: '3',
      alert_id: 'alert-3',
      alert_name: 'AAPL Trade Alert',
      alert_type: 'ticker_trades',
      triggered_at: '2024-01-13T16:45:00Z',
      trade_details: {
        member_name: 'John Doe',
        ticker: 'AAPL',
        amount: 50000,
        transaction_type: 'Purchase',
      },
      delivery_status: 'failed',
      delivery_method: 'email',
      error_message: 'Invalid email address',
    },
  ];

  useEffect(() => {
    // Load notifications from API
    const loadNotifications = async () => {
      setLoading(true);
      try {
        // await apiClient.getAlertNotifications({ date_range: dateRange, status: statusFilter });
        // For now, use mock data
        setNotifications(mockNotifications);
      } catch (error) {
        console.error('Failed to load notifications:', error);
      } finally {
        setLoading(false);
      }
    };

    loadNotifications();
  }, [dateRange, statusFilter, mockNotifications]);

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
        return 'text-green-600 bg-green-100';
      case 'failed':
        return 'text-red-600 bg-red-100';
      case 'pending':
        return 'text-yellow-600 bg-yellow-100';
      default:
        return 'text-gray-600 bg-gray-100';
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
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
        <p className="text-gray-600 mt-2">Loading notification history...</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Alert History</h3>
          <p className="text-gray-600">View your notification delivery history and status</p>
        </div>
        
        <div className="flex space-x-4">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="1d">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
          </select>
          
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
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
          <div className="text-gray-400 text-6xl mb-4">📬</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No notifications found</h3>
          <p className="text-gray-600">
            No notifications have been sent in the selected time period.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {notifications.map((notification) => (
            <div
              key={notification.id}
              className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <span className="text-lg">
                      {getStatusIcon(notification.delivery_status)}
                    </span>
                    <h4 className="font-semibold text-gray-900">
                      {notification.alert_name}
                    </h4>
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(notification.delivery_status)}`}>
                      {notification.delivery_status.charAt(0).toUpperCase() + notification.delivery_status.slice(1)}
                    </span>
                  </div>
                  
                  <div className="text-gray-700 mb-3">
                    <strong>{notification.trade_details.member_name}</strong> made a{' '}
                    {notification.trade_details.transaction_type?.toLowerCase()} of{' '}
                    {notification.trade_details.ticker && (
                      <span className="font-medium">{notification.trade_details.ticker}</span>
                    )}
                    {notification.trade_details.amount && (
                      <span> worth {formatCurrency(notification.trade_details.amount)}</span>
                    )}
                  </div>
                  
                  <div className="flex items-center text-sm text-gray-500 space-x-4">
                    <span>📅 {formatDate(notification.triggered_at)}</span>
                    <span>📧 Email notification</span>
                  </div>
                  
                  {notification.error_message && (
                    <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                      <p className="text-sm text-red-700">
                        <strong>Error:</strong> {notification.error_message}
                      </p>
                    </div>
                  )}
                </div>
                
                <div className="flex space-x-2">
                  {notification.delivery_status === 'failed' && (
                    <button className="px-3 py-1 text-xs font-medium text-blue-700 bg-blue-100 hover:bg-blue-200 rounded">
                      Retry
                    </button>
                  )}
                  <button className="px-3 py-1 text-xs font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded">
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
