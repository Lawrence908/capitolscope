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

  // Square letter code per alert type (Bulletin chips, no emoji).
  const getAlertTypeIcon = (type: string) => {
    switch (type) {
      case 'member_trades':
        return 'M';
      case 'amount_threshold':
        return '$';
      case 'ticker_trades':
        return 'T';
      default:
        return '?';
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

    if (aValue == null || bValue == null) return 0;
    if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
    if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  if (loading) {
    return (
      <div className="p-8 text-center">
        <div className="mx-auto h-8 w-8 animate-spin rounded-full border-[3px] border-line border-t-accent"></div>
        <p className="mt-3 font-ui text-[11px] font-semibold uppercase tracking-[0.14em] text-content-faint">Loading alerts</p>
      </div>
    );
  }

  return (
    <div className="py-6">
      {/* Filters */}
      <div className="mb-6 flex flex-wrap gap-4">
        <div>
          <label className="mb-1 block font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-content-faint">
            Alert type
          </label>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="input-field text-sm"
          >
            <option value="all">All Types</option>
            <option value="member_trades">Member Trades</option>
            <option value="amount_threshold">Amount Threshold</option>
            <option value="ticker_trades">Ticker Trades</option>
          </select>
        </div>
        
        <div>
          <label className="mb-1 block font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-content-faint">
            Status
          </label>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="input-field text-sm"
          >
            <option value="all">All Statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
      </div>

      {/* Table */}
      {sortedAlerts.length === 0 ? (
        <div className="border-t border-line py-12 text-center">
          <h3 className="mb-2 font-display text-3xl font-extrabold leading-none text-content">No alerts found</h3>
          <p className="font-ui text-sm text-content-muted">
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
              <tr className="border-b-2 border-content font-ui text-[11px] uppercase tracking-[0.08em]">
                <th className="text-left py-3 px-4 font-bold text-content-faint">
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
                <th className="text-left py-3 px-4 font-bold text-content-faint">
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
                <th className="text-left py-3 px-4 font-bold text-content-faint">Target</th>
                <th className="text-left py-3 px-4 font-bold text-content-faint">Status</th>
                <th className="text-left py-3 px-4 font-bold text-content-faint">
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
                <th className="text-right py-3 px-4 font-bold text-content-faint">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedAlerts.map((alert) => (
                <tr key={alert.id} className="border-b border-line hover:bg-surface-inset">
                  <td className="py-4 px-4">
                    <div className="flex items-center space-x-2">
                      <span className="inline-flex h-[18px] w-[18px] items-center justify-center border-2 border-content font-display text-[12px] font-extrabold leading-none text-content">
                        {getAlertTypeIcon(alert.alert_type)}
                      </span>
                      <span className="font-ui text-sm font-semibold text-content-muted">
                        {getAlertTypeLabel(alert.alert_type)}
                      </span>
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    <div className="font-ui font-bold text-content">{alert.name}</div>
                  </td>
                  <td className="py-4 px-4">
                    <div className="font-ui text-sm text-content-muted">
                      {alert.target_name || alert.target_symbol || 
                        (alert.threshold_value ? `$${alert.threshold_value.toLocaleString()}+` : '-')}
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    <span className={`inline-flex items-center border-2 border-content px-1.5 py-px font-display text-[12px] font-extrabold uppercase leading-tight tracking-[0.04em] ${
                      alert.is_active
                        ? 'bg-content text-surface'
                        : 'text-content-faint'
                    }`}>
                      {alert.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="py-4 px-4 font-ui text-sm tabular-nums text-content-muted">
                    {formatDate(alert.created_at)}
                  </td>
                  <td className="py-4 px-4 text-right">
                    <div className="flex items-center justify-end space-x-2">
                      <button
                        onClick={() => handleToggleAlert(alert)}
                        className={`${alert.is_active ? 'btn-outline' : 'btn-secondary'} px-3 py-1 text-xs`}
                      >
                        {alert.is_active ? 'Pause' : 'Activate'}
                      </button>
                      <button
                        onClick={() => handleDeleteAlert(alert)}
                        className="btn-ghost px-3 py-1 text-xs text-accent hover:text-accent-strong"
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
