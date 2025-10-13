import React, { useState, useEffect } from 'react';

interface NotificationSettings {
  email_enabled: boolean;
  email_address: string;
  frequency: 'immediate' | 'daily_digest' | 'weekly_digest';
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
}

export const NotificationPreferences: React.FC = () => {
  const [settings, setSettings] = useState<NotificationSettings>({
    email_enabled: true,
    email_address: '',
    frequency: 'immediate',
    quiet_hours_enabled: false,
    quiet_hours_start: '22:00',
    quiet_hours_end: '08:00',
  });
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [testEmailSent, setTestEmailSent] = useState(false);

  useEffect(() => {
    // Load settings from API or localStorage
    // For now, using mock data
    const savedSettings = localStorage.getItem('notification_preferences');
    if (savedSettings) {
      setSettings(JSON.parse(savedSettings));
    }
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // Save to API
      // await apiClient.updateNotificationPreferences(settings);
      
      // For now, save to localStorage
      localStorage.setItem('notification_preferences', JSON.stringify(settings));
      setLastSaved(new Date());
    } catch (error) {
      console.error('Failed to save preferences:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestEmail = async () => {
    if (!settings.email_address) {
      alert('Please enter an email address first');
      return;
    }

    try {
      // Send test email
      // await apiClient.sendTestNotification(settings.email_address);
      setTestEmailSent(true);
      setTimeout(() => setTestEmailSent(false), 3000);
    } catch (error) {
      console.error('Failed to send test email:', error);
    }
  };

  return (
    <div className="p-6 space-y-8">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Notification Preferences</h3>
        <p className="text-gray-600 mb-6">
          Configure how and when you want to receive trade alert notifications.
        </p>
      </div>

      {/* Email Settings */}
      <div className="bg-gray-50 rounded-lg p-6">
        <h4 className="font-medium text-gray-900 mb-4 flex items-center">
          <span className="mr-2">📧</span>
          Email Notifications
        </h4>
        
        <div className="space-y-4">
          <div className="flex items-center">
            <input
              type="checkbox"
              id="email_enabled"
              checked={settings.email_enabled}
              onChange={(e) => setSettings({ ...settings, email_enabled: e.target.checked })}
              className="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
            />
            <label htmlFor="email_enabled" className="ml-2 text-gray-700">
              Enable email notifications
            </label>
          </div>

          {settings.email_enabled && (
            <div className="ml-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email Address
                </label>
                <div className="flex space-x-2">
                  <input
                    type="email"
                    value={settings.email_address}
                    onChange={(e) => setSettings({ ...settings, email_address: e.target.value })}
                    placeholder="your-email@example.com"
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                  <button
                    onClick={handleTestEmail}
                    disabled={!settings.email_address}
                    className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {testEmailSent ? '✓ Sent' : 'Test'}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Notification Frequency
                </label>
                <div className="space-y-2">
                  {[
                    { value: 'immediate', label: 'Immediate', description: 'Send notifications as soon as trades are detected' },
                    { value: 'daily_digest', label: 'Daily Digest', description: 'Send a summary email once per day' },
                    { value: 'weekly_digest', label: 'Weekly Digest', description: 'Send a summary email once per week' },
                  ].map((option) => (
                    <label key={option.value} className="flex items-start space-x-3 cursor-pointer">
                      <input
                        type="radio"
                        name="frequency"
                        value={option.value}
                        checked={settings.frequency === option.value}
                        onChange={(e) => setSettings({ ...settings, frequency: e.target.value as 'immediate' | 'daily_digest' | 'weekly_digest' })}
                        className="mt-1 h-4 w-4 text-primary-600 border-gray-300 focus:ring-primary-500"
                      />
                      <div>
                        <div className="font-medium text-gray-900">{option.label}</div>
                        <div className="text-sm text-gray-600">{option.description}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Quiet Hours */}
      <div className="bg-gray-50 rounded-lg p-6">
        <h4 className="font-medium text-gray-900 mb-4 flex items-center">
          <span className="mr-2">🌙</span>
          Quiet Hours
        </h4>
        
        <div className="space-y-4">
          <div className="flex items-center">
            <input
              type="checkbox"
              id="quiet_hours_enabled"
              checked={settings.quiet_hours_enabled}
              onChange={(e) => setSettings({ ...settings, quiet_hours_enabled: e.target.checked })}
              className="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
            />
            <label htmlFor="quiet_hours_enabled" className="ml-2 text-gray-700">
              Enable quiet hours (no immediate notifications during these hours)
            </label>
          </div>

          {settings.quiet_hours_enabled && (
            <div className="ml-6 grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Start Time
                </label>
                <input
                  type="time"
                  value={settings.quiet_hours_start}
                  onChange={(e) => setSettings({ ...settings, quiet_hours_start: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  End Time
                </label>
                <input
                  type="time"
                  value={settings.quiet_hours_end}
                  onChange={(e) => setSettings({ ...settings, quiet_hours_end: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Save Button */}
      <div className="flex items-center justify-between pt-6 border-t border-gray-200">
        <div className="text-sm text-gray-600">
          {lastSaved && (
            <span>Last saved: {lastSaved.toLocaleString()}</span>
          )}
        </div>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving ? 'Saving...' : 'Save Preferences'}
        </button>
      </div>
    </div>
  );
};
