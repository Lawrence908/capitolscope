import React, { useState, useEffect } from 'react';
import { apiClient } from '../../services/api';

interface NotificationSettings {
  email_enabled: boolean;
  email_address: string;
  frequency: 'immediate' | 'daily_digest' | 'weekly_digest';
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
}

// Map between the UI's frequency values and the API's cadence values.
const UI_TO_API: Record<NotificationSettings['frequency'], 'instant' | 'daily' | 'weekly'> = {
  immediate: 'instant',
  daily_digest: 'daily',
  weekly_digest: 'weekly',
};
const API_TO_UI: Record<'instant' | 'daily' | 'weekly', NotificationSettings['frequency']> = {
  instant: 'immediate',
  daily: 'daily_digest',
  weekly: 'weekly_digest',
};

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
    // Quiet-hours are UI-only (not modeled server-side), so keep them local.
    const savedSettings = localStorage.getItem('notification_preferences');
    const local = savedSettings ? JSON.parse(savedSettings) : {};
    // Channel + cadence come from the API.
    apiClient
      .getSubscriptions()
      .then((sub) => {
        setSettings((prev) => ({
          ...prev,
          ...local,
          email_enabled: sub.email_enabled,
          frequency: API_TO_UI[sub.email_frequency] ?? 'immediate',
        }));
      })
      .catch((error) => {
        console.error('Failed to load preferences:', error);
        if (savedSettings) setSettings((prev) => ({ ...prev, ...local }));
      });
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // Server-backed fields: channel toggle + digest cadence.
      await apiClient.updateSubscriptions({
        email_enabled: settings.email_enabled,
        email_frequency: UI_TO_API[settings.frequency],
      });
      // Quiet-hours remain local-only for now.
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
    <div className="space-y-8 py-6">
      <div>
        <h3 className="mb-2 font-display text-3xl font-extrabold leading-none text-content">Notification preferences</h3>
        <p className="font-ui text-sm text-content-muted">
          Configure how and when you want to receive trade alert notifications.
        </p>
      </div>

      {/* Email Settings */}
      <div className="border-t-[3px] border-content pt-5">
        <h4 className="mb-4 font-display text-2xl font-extrabold leading-none text-content">
          Email notifications
        </h4>
        
        <div className="space-y-4">
          <div className="flex items-center">
            <input
              type="checkbox"
              id="email_enabled"
              checked={settings.email_enabled}
              onChange={(e) => setSettings({ ...settings, email_enabled: e.target.checked })}
              className="h-4 w-4 text-accent border-line rounded focus:ring-accent"
            />
            <label htmlFor="email_enabled" className="ml-2 text-content-muted">
              Enable email notifications
            </label>
          </div>

          {settings.email_enabled && (
            <div className="ml-6 space-y-4">
              <div>
                <label className="mb-1 block font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-content-faint">
                  Email Address
                </label>
                <div className="flex space-x-2">
                  <input
                    type="email"
                    value={settings.email_address}
                    onChange={(e) => setSettings({ ...settings, email_address: e.target.value })}
                    placeholder="your-email@example.com"
                    className="input-field flex-1"
                  />
                  <button
                    onClick={handleTestEmail}
                    disabled={!settings.email_address}
                    className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {testEmailSent ? '✓ Sent' : 'Test'}
                  </button>
                </div>
              </div>

              <div>
                <label className="mb-2 block font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-content-faint">
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
                        className="mt-1 h-4 w-4 text-accent border-line focus:ring-accent"
                      />
                      <div>
                        <div className="font-ui font-bold text-content">{option.label}</div>
                        <div className="text-sm text-content-muted">{option.description}</div>
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
      <div className="border-t-[3px] border-content pt-5">
        <h4 className="mb-4 font-display text-2xl font-extrabold leading-none text-content">
          Quiet hours
        </h4>
        
        <div className="space-y-4">
          <div className="flex items-center">
            <input
              type="checkbox"
              id="quiet_hours_enabled"
              checked={settings.quiet_hours_enabled}
              onChange={(e) => setSettings({ ...settings, quiet_hours_enabled: e.target.checked })}
              className="h-4 w-4 text-accent border-line rounded focus:ring-accent"
            />
            <label htmlFor="quiet_hours_enabled" className="ml-2 text-content-muted">
              Enable quiet hours (no immediate notifications during these hours)
            </label>
          </div>

          {settings.quiet_hours_enabled && (
            <div className="ml-6 grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1 block font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-content-faint">
                  Start Time
                </label>
                <input
                  type="time"
                  value={settings.quiet_hours_start}
                  onChange={(e) => setSettings({ ...settings, quiet_hours_start: e.target.value })}
                  className="input-field"
                />
              </div>
              <div>
                <label className="mb-1 block font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-content-faint">
                  End Time
                </label>
                <input
                  type="time"
                  value={settings.quiet_hours_end}
                  onChange={(e) => setSettings({ ...settings, quiet_hours_end: e.target.value })}
                  className="input-field"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Save Button */}
      <div className="flex items-center justify-between pt-6 border-t border-line">
        <div className="text-sm text-content-muted">
          {lastSaved && (
            <span>Last saved: {lastSaved.toLocaleString()}</span>
          )}
        </div>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving ? 'Saving...' : 'Save Preferences'}
        </button>
      </div>
    </div>
  );
};
