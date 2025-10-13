import React, { useState } from 'react';
import { useAlerts, CreateAlertData } from '../../hooks/useAlerts';
import { CreateAlertModal } from '../../components/alerts/CreateAlertModal';
import { AlertTable } from '../../components/alerts/AlertTable';
import { AlertHistory } from '../../components/alerts/AlertHistory';
import { NotificationPreferences } from '../../components/alerts/NotificationPreferences';

export const AlertDashboard: React.FC = () => {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedTab, setSelectedTab] = useState('alerts');
  const { alerts, stats, loading, error, refetch, createAlert } = useAlerts();

  const handleCreateAlert = async (alertData: CreateAlertData) => {
    try {
      await createAlert(alertData);
      setIsCreateModalOpen(false);
      // Show success notification - could use a toast library here
      console.log('Alert created successfully');
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('Failed to create alert:', errorMessage);
      // Show error notification
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-red-800 mb-2">Error Loading Alerts</h2>
            <p className="text-red-600">{error}</p>
            <button
              onClick={refetch}
              className="mt-4 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Trade Alerts</h1>
            <p className="text-gray-600 mt-2">
              Get notified when congress members make trades matching your criteria
            </p>
          </div>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-3 rounded-lg font-medium transition-colors"
          >
            Create Alert
          </button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Active Alerts</div>
            <div className="text-2xl font-bold text-gray-900 mt-2">
              {stats?.activeAlerts || 0}
            </div>
            <div className="text-sm text-gray-500 mt-1">Currently monitoring</div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Notifications Today</div>
            <div className="text-2xl font-bold text-gray-900 mt-2">
              {stats?.notificationsToday || 0}
            </div>
            <div className="text-sm text-gray-500 mt-1">Alerts triggered</div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Total Triggered</div>
            <div className="text-2xl font-bold text-gray-900 mt-2">
              {stats?.totalTriggered || 0}
            </div>
            <div className="text-sm text-gray-500 mt-1">All time</div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Delivery Rate</div>
            <div className="text-2xl font-bold text-gray-900 mt-2">
              {stats?.deliveryRate || 0}%
            </div>
            <div className="text-sm text-gray-500 mt-1">Email success rate</div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {[
              { id: 'alerts', label: 'Alerts' },
              { id: 'history', label: 'History' },
              { id: 'preferences', label: 'Preferences' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setSelectedTab(tab.id)}
                className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                  selectedTab === tab.id
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="bg-white rounded-lg shadow">
          {selectedTab === 'alerts' && (
            <AlertTable 
              alerts={alerts} 
              loading={loading} 
              onRefetch={refetch}
            />
          )}
          {selectedTab === 'history' && (
            <AlertHistory />
          )}
          {selectedTab === 'preferences' && (
            <NotificationPreferences />
          )}
        </div>

        {/* Create Alert Modal */}
        <CreateAlertModal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          onSubmit={handleCreateAlert}
        />
      </div>
    </div>
  );
};

export default AlertDashboard;
