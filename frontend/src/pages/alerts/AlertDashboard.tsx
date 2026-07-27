import React, { useState } from 'react';
import { useAlerts } from '../../hooks/useAlerts';
import type { CreateAlertData } from '../../hooks/useAlerts';
import { CreateAlertModal } from '../../components/alerts/CreateAlertModal';
import { AlertTable } from '../../components/alerts/AlertTable';
import { AlertHistory } from '../../components/alerts/AlertHistory';
import { NotificationPreferences } from '../../components/alerts/NotificationPreferences';
import { PageHeader, StatTile, Tabs, Spinner } from '../../components/ui';

type Tab = 'alerts' | 'history' | 'preferences';

export const AlertDashboard: React.FC = () => {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedTab, setSelectedTab] = useState<Tab>('alerts');
  const { alerts, stats, loading, error, refetch, createAlert, toggleAlert, deleteAlert } = useAlerts();

  const handleCreateAlert = async (alertData: CreateAlertData) => {
    try {
      await createAlert(alertData);
      setIsCreateModalOpen(false);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('Failed to create alert:', errorMessage);
    }
  };

  if (loading) {
    return <Spinner label="Loading alerts" />;
  }

  if (error) {
    return (
      <div className="rounded-md border border-sev-flag/40 p-6 status-error">
        <h2 className="mb-2 font-display text-lg text-content">Error Loading Alerts</h2>
        <p className="font-ui text-sm">{error}</p>
        <button onClick={() => refetch()} className="btn-primary mt-4 text-sm">
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        eyebrow="CapitolScope · Alerts"
        title="Trade Alerts"
        subtitle="Get notified when congress members make trades matching your criteria — by member, ticker, or amount."
        actions={
          <button onClick={() => setIsCreateModalOpen(true)} className="btn-primary text-sm">
            Create Alert
          </button>
        }
      />

      {/* Stats */}
      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-4">
        <div className="card p-5">
          <StatTile label="Active Alerts" value={stats?.activeAlerts || 0} tone="accent" hint="Currently monitoring" />
        </div>
        <div className="card p-5">
          <StatTile label="Notifications Today" value={stats?.notificationsToday || 0} hint="Alerts triggered" />
        </div>
        <div className="card p-5">
          <StatTile label="Total Triggered" value={stats?.totalTriggered || 0} hint="All time" />
        </div>
        <div className="card p-5">
          <StatTile label="Delivery Rate" value={`${stats?.deliveryRate || 0}%`} tone="brass" hint="Email success rate" />
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-6 border-b border-line">
        <Tabs
          items={[
            { id: 'alerts', label: 'Alerts' },
            { id: 'history', label: 'History' },
            { id: 'preferences', label: 'Preferences' },
          ]}
          active={selectedTab}
          onChange={setSelectedTab}
        />
      </div>

      {/* Tab Content */}
      <div className="card overflow-hidden">
        {selectedTab === 'alerts' && (
          <AlertTable
            alerts={alerts}
            loading={loading}
            onRefetch={refetch}
            onToggleAlert={toggleAlert}
            onDeleteAlert={deleteAlert}
          />
        )}
        {selectedTab === 'history' && <AlertHistory />}
        {selectedTab === 'preferences' && <NotificationPreferences />}
      </div>

      {/* Create Alert Modal */}
      <CreateAlertModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateAlert}
      />
    </div>
  );
};

export default AlertDashboard;
