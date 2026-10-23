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
      <div className="border-l-4 border-accent bg-surface-inset p-6">
        <h2 className="mb-2 font-display text-3xl font-extrabold leading-none text-content">Error loading alerts</h2>
        <p className="font-ui text-sm text-content-muted">{error}</p>
        <button onClick={() => refetch()} className="btn-primary mt-4 text-sm">
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        eyebrow="Alerts"
        title="Trade Alerts"
        subtitle="Get notified when congress members make trades matching your criteria: by member, ticker or amount."
        actions={
          <button onClick={() => setIsCreateModalOpen(true)} className="btn-primary text-sm">
            Create Alert
          </button>
        }
      />

      {/* Stats */}
      <div className="section-rule mb-8 grid grid-cols-2 md:grid-cols-4">
        {[
          { label: 'Active alerts', value: stats?.activeAlerts || 0, hint: 'Currently monitoring' },
          { label: 'Notifications today', value: stats?.notificationsToday || 0, hint: 'Alerts triggered' },
          { label: 'Total triggered', value: stats?.totalTriggered || 0, hint: 'All time' },
          { label: 'Delivery rate', value: `${stats?.deliveryRate || 0}%`, hint: 'Email success rate' },
        ].map((s, i) => (
          <div key={s.label} className={`border-b border-line py-4 pr-4 ${i > 0 ? 'md:border-l md:pl-4' : ''} ${i % 2 === 1 ? 'border-l pl-4' : ''}`}>
            <StatTile label={s.label} value={s.value} hint={s.hint} size="lg" />
          </div>
        ))}
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
      <div className="section-rule overflow-hidden">
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
