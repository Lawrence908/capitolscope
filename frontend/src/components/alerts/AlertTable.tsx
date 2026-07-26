import React, { useState } from 'react';
import type { TradeAlert } from '../../hooks/useAlerts';

interface AlertTableProps {
  alerts: TradeAlert[];
  loading: boolean;
  onRefetch: () => void;
  onToggleAlert: (alertId: string, isActive: boolean) => Promise<void>;
  onDeleteAlert: (alertId: string) => Promise<void>;
}

export const AlertTable: React.FC<AlertTableProps> = ({
  alerts,
  loading,
  onToggleAlert,
  onDeleteAlert,
}) => {
  const [sortField, setSortField] = useState<keyof TradeAlert>('created_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [filterType, setFilterType] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const getAlertTypeLabel = (type: string) => {
    switch (type) {
      case 'member_trades':
        return 'Member Trades';
      case 'amount_threshold':
        return 'Amount Threshold';
      case 'ticker_trades':
        return 'Ticker Trades';
      default:
        return type;
    }
  };

  const getAlertTypeIcon = (type: string) => {
    switch (type) {
      case 'member_trades':
        return '👤';
      case 'amount_threshold':
        return '💰';
      case 'ticker_trades':
        return '📈';
      default:
        return '🔔';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const handleSort = (field: keyof TradeAlert) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const handleToggleAlert = async (alert: TradeAlert) => {
    try {
      await onToggleAlert(alert.id, !alert.is_active);
    } catch (error) {
      console.error('Failed to toggle alert:', error);
    }
  };

  const handleDeleteAlert = async (alert: TradeAlert) => {
    if (window.confirm(`Are you sure you want to delete "${alert.name}"?`)) {
      try {
        await onDeleteAlert(alert.id);
      } catch (error) {
        console.error('Failed to delete alert:', error);
      }
    }
  };

  const filteredAlerts = alerts.filter(alert => {
    if (filterType !== 'all' && alert.alert_type !== filterType) return false;
    if (filterStatus === 'active' && !alert.is_active) return false;
    if (filterStatus === 'inactive' && alert.is_active) return false;
    return true;
  });

  const sortedAlerts = [...filteredAlerts].sort((a, b) => {
    const aValue = a[sortField];
    const bValue = b[sortField];
    
    if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
    if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  if (loading) {
    return (
      <div className="p-8 text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent mx-auto"></div>
        <p className="text-content-muted mt-2">Loading alerts...</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-content-muted mb-1">
            Alert Type
          </label>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="border border-line rounded-lg px-3 py-2 text-sm"
          >
            <option value="all">All Types</option>
            <option value="member_trades">Member Trades</option>
            <option value="amount_threshold">Amount Threshold</option>
            <option value="ticker_trades">Ticker Trades</option>
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-content-muted mb-1">
            Status
          </label>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="border border-line rounded-lg px-3 py-2 text-sm"
          >
            <option value="all">All Statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
      </div>

      {/* Table */}
      {sortedAlerts.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-content-faint text-6xl mb-4">🔔</div>
          <h3 className="text-lg font-medium text-content mb-2">No alerts found</h3>
          <p className="text-content-muted">
            {alerts.length === 0 
              ? "You haven't created any alerts yet. Click 'Create Alert' to get started!"
              : "No alerts match your current filters. Try adjusting the filters above."
            }
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-line">
                <th className="text-left py-3 px-4 font-medium text-content-muted">
                  <button
                    onClick={() => handleSort('alert_type')}
                    className="flex items-center space-x-1 hover:text-content"
                  >
                    <span>Type</span>
                    {sortField === 'alert_type' && (
                      <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </button>
                </th>
                <th className="text-left py-3 px-4 font-medium text-content-muted">
                  <button
                    onClick={() => handleSort('name')}
                    className="flex items-center space-x-1 hover:text-content"
                  >
                    <span>Name</span>
                    {sortField === 'name' && (
                      <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </button>
                </th>
                <th className="text-left py-3 px-4 font-medium text-content-muted">Target</th>
                <th className="text-left py-3 px-4 font-medium text-content-muted">Status</th>
                <th className="text-left py-3 px-4 font-medium text-content-muted">
                  <button
                    onClick={() => handleSort('created_at')}
                    className="flex items-center space-x-1 hover:text-content"
                  >
                    <span>Created</span>
                    {sortField === 'created_at' && (
                      <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </button>
                </th>
                <th className="text-right py-3 px-4 font-medium text-content-muted">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedAlerts.map((alert) => (
                <tr key={alert.id} className="border-b border-line hover:bg-surface-inset">
                  <td className="py-4 px-4">
                    <div className="flex items-center space-x-2">
                      <span className="text-lg">{getAlertTypeIcon(alert.alert_type)}</span>
                      <span className="text-sm font-medium text-content-muted">
                        {getAlertTypeLabel(alert.alert_type)}
                      </span>
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    <div className="font-medium text-content">{alert.name}</div>
                  </td>
                  <td className="py-4 px-4">
                    <div className="text-content-muted">
                      {alert.target_name || alert.target_symbol || 
                        (alert.threshold_value ? `$${alert.threshold_value.toLocaleString()}+` : '-')}
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      alert.is_active
                        ? 'bg-accent/10 text-accent'
                        : 'bg-surface-inset text-content'
                    }`}>
                      {alert.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="py-4 px-4 text-content-muted">
                    {formatDate(alert.created_at)}
                  </td>
                  <td className="py-4 px-4 text-right">
                    <div className="flex items-center justify-end space-x-2">
                      <button
                        onClick={() => handleToggleAlert(alert)}
                        className={`px-3 py-1 text-xs font-medium rounded ${
                          alert.is_active
                            ? 'text-orange-700 bg-orange-100 hover:bg-orange-200'
                            : 'text-accent bg-accent/10 hover:bg-accent/10'
                        }`}
                      >
                        {alert.is_active ? 'Pause' : 'Activate'}
                      </button>
                      <button
                        onClick={() => handleDeleteAlert(alert)}
                        className="px-3 py-1 text-xs font-medium text-sev-flag bg-sev-flag/10 hover:bg-sev-flag/10 rounded"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
