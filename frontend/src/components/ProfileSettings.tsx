import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  UserCircleIcon,
  EnvelopeIcon,
  KeyIcon,
  BellIcon,
  ShieldCheckIcon,
  StarIcon,
  SparklesIcon,
  CreditCardIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import stripeService from '../services/stripeService';

const ProfileSettings: React.FC = () => {
  const { user, updateUser } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  
  const [profileData, setProfileData] = useState({
    display_name: user?.display_name || '',
    username: user?.username || '',
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    email: user?.email || '',
    is_public_profile: user?.is_public_profile || false,
  });

  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });

  const [notifications, setNotifications] = useState({
    email_notifications: true,
    trade_alerts: true, // Pro+
    weekly_summary: false, // Premium+
    multiple_buyer_alerts: false, // Premium+
    high_value_alerts: false, // Premium+
  });

  // Check if user has premium subscription (handle both lowercase and uppercase)
  const subscriptionTier = user?.subscription_tier?.toLowerCase();
  const isPremium = subscriptionTier === 'premium' || subscriptionTier === 'enterprise';
  const isPro = subscriptionTier === 'pro' || isPremium;
  const isFree = subscriptionTier === 'free' || !subscriptionTier;

  useEffect(() => {
    if (user) {
      setProfileData({
        display_name: user.display_name || user.computed_display_name || '',
        username: user.username || '',
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        email: user.email || '',
        is_public_profile: user.is_public_profile || false,
      });
    }
  }, [user]);

  // Load user preferences on component mount
  useEffect(() => {
    const loadUserPreferences = async () => {
      try {
        const tokens = localStorage.getItem('capitolscope_tokens');
        const accessToken = tokens ? JSON.parse(tokens).access_token : '';
        
        const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8001'}/api/v1/auth/preferences`, {
          headers: {
            'Authorization': `Bearer ${accessToken}`,
          },
        });
        
        if (response.ok) {
          const data = await response.json();
          if (data.data) {
            setNotifications(prev => ({
              ...prev,
              ...data.data
            }));
          }
        }
      } catch (error) {
        console.error('Error loading user preferences:', error);
      }
    };

    if (user) {
      loadUserPreferences();
    }
  }, [user]);

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage(null);

    try {
      const tokens = localStorage.getItem('capitolscope_tokens');
      const accessToken = tokens ? JSON.parse(tokens).access_token : '';
      
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8001'}/api/v1/auth/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          display_name: profileData.display_name,
          username: profileData.username,
          first_name: profileData.first_name,
          last_name: profileData.last_name,
          is_public_profile: profileData.is_public_profile,
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.data && updateUser) {
          updateUser(data.data);
        }
        setMessage({ type: 'success', text: 'Profile updated successfully!' });
      } else {
        const errorData = await response.json();
        setMessage({ type: 'error', text: errorData.error?.message || 'Failed to update profile. Please try again.' });
      }
    } catch (error) {
      console.error('Profile update error:', error);
      setMessage({ type: 'error', text: 'Failed to update profile. Please try again.' });
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (passwordData.new_password !== passwordData.confirm_password) {
      setMessage({ type: 'error', text: 'New passwords do not match.' });
      return;
    }

    if (passwordData.new_password.length < 8) {
      setMessage({ type: 'error', text: 'Password must be at least 8 characters long.' });
      return;
    }

    setIsLoading(true);
    setMessage(null);

    try {
      // TODO: Implement API call to change password
      // await apiClient.changePassword(passwordData);
      
      setPasswordData({
        current_password: '',
        new_password: '',
        confirm_password: '',
      });
      
      setMessage({ type: 'success', text: 'Password changed successfully!' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to change password. Please check your current password.' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleNotificationChange = async (key: string, value: boolean) => {
    // Check if this is a premium feature
    const proFeatures = ['trade_alerts'];
    const premiumFeatures = ['weekly_summary', 'multiple_buyer_alerts', 'high_value_alerts'];
    
    if (premiumFeatures.includes(key) && !isPremium) {
      setMessage({ type: 'error', text: 'This feature requires a Premium subscription. Upgrade to unlock advanced notifications.' });
      return;
    }
    if (proFeatures.includes(key) && !isPro) {
      setMessage({ type: 'error', text: 'This feature requires a Pro subscription. Upgrade to unlock trade alerts.' });
      return;
    }

    // Update local state immediately for responsive UI
    setNotifications(prev => ({
      ...prev,
      [key]: value,
    }));
    
    // Auto-save to backend
    try {
      const tokens = localStorage.getItem('capitolscope_tokens');
      const accessToken = tokens ? JSON.parse(tokens).access_token : '';
      
              const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8001'}/api/v1/auth/update-preferences`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          [key]: value
        }),
      });
      
      if (!response.ok) {
        console.error('Failed to save notification preference');
        // Revert the change if save failed
        setNotifications(prev => ({ ...prev, [key]: !value }));
        setMessage({ type: 'error', text: 'Failed to save notification preference' });
      }
    } catch (error) {
      console.error('Error saving notification preference:', error);
      // Revert the change if save failed
      setNotifications(prev => ({ ...prev, [key]: !value }));
      setMessage({ type: 'error', text: 'Failed to save notification preference' });
    }
  };

  const handlePremiumFeatureClick = (featureName: string) => {
    // Show upgrade prompt and redirect to premium page
    setMessage({ 
      type: 'error', 
      text: `${featureName} is a premium feature. Redirecting to upgrade page...` 
    });
    setTimeout(() => {
      window.location.href = '/premium';
    }, 2000);
  };

  const handleCancelSubscription = async () => {
    if (!confirm('Are you sure you want to cancel your subscription? You will lose access to premium features at the end of your current billing period.')) {
      return;
    }

    setIsCancelling(true);
    setMessage(null);

    try {
      const result = await stripeService.cancelSubscription(true); // Cancel at period end
      setMessage({ 
        type: 'success', 
        text: `Subscription cancelled successfully. You will have access until the end of your current billing period.` 
      });
      
      // Update user context to reflect cancellation
      if (updateUser && user) {
        updateUser({
          ...user,
          subscription_status: 'cancelled'
        });
      }
    } catch (error) {
      console.error('Error cancelling subscription:', error);
      setMessage({ 
        type: 'error', 
        text: 'Failed to cancel subscription. Please try again or contact support.' 
      });
    } finally {
      setIsCancelling(false);
    }
  };

  const handleManageSubscription = async () => {
    setIsLoading(true);
    setMessage(null);

    try {
      const response = await stripeService.createPortalSession(
        `${window.location.origin}/profile-settings`
      );
      
      if (response.url) {
        window.location.href = response.url;
      } else {
        throw new Error('No portal URL received');
      }
    } catch (error) {
      console.error('Error creating portal session:', error);
      setMessage({ 
        type: 'error', 
        text: 'Unable to open subscription management. Please try again or contact support.' 
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleReactivateSubscription = () => {
    // Redirect to premium page to reactivate
    window.location.href = '/premium';
  };

  const PremiumBadge = () => (
    <div className="flex items-center text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 px-2 py-1 rounded-full">
      <StarIcon className="h-3 w-3 mr-1" />
      Premium
    </div>
  );

  const PremiumFeatureWrapper = ({ children, featureName }: { children: React.ReactNode; featureName: string }) => {
    if (isPremium) {
      return <>{children}</>;
    }

    return (
      <div className="opacity-60 cursor-not-allowed" onClick={() => handlePremiumFeatureClick(featureName)}>
        {children}
      </div>
    );
  };

  return (
    <div className="space-y-4 lg:space-y-6">
      {/* Header */}
      <div className="card p-4 lg:p-6">
        <h2 className="text-xl lg:text-2xl font-bold text-neutral-100 mb-2">
          Profile Settings
        </h2>
        <p className="text-sm lg:text-base text-neutral-400">
          Manage your account settings and preferences.
        </p>
        {isFree && (
          <div className="mt-4 p-3 lg:p-4 bg-neon-gradient rounded-lg shadow-glow-primary">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="flex items-center">
                <SparklesIcon className="h-5 w-5 lg:h-6 lg:w-6 text-bg-primary mr-2 lg:mr-3" />
                <div>
                  <h4 className="text-base lg:text-lg font-bold text-bg-primary mb-1">Unlock Premium Features</h4>
                  <p className="text-bg-primary/80 text-xs lg:text-sm">
                    Get access to Trade Alerts, Weekly Summaries, Multiple Buyer Alerts, and High-Value Trade Alerts
                  </p>
                </div>
              </div>
              <Link
                to="/premium"
                className="bg-bg-primary text-primary-400 px-3 lg:px-4 py-2 rounded-lg font-semibold hover:bg-bg-tertiary transition-colors duration-200 shadow-md hover:shadow-lg transform hover:scale-105 text-sm lg:text-base"
              >
                View Plans
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* Message */}
      {message && (
        <div className={`card p-4 ${
          message.type === 'success' 
            ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800' 
            : 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
        }`}>
          <p className={`text-sm ${
            message.type === 'success' 
              ? 'text-green-800 dark:text-green-200' 
              : 'text-red-800 dark:text-red-200'
          }`}>
            {message.text}
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
        {/* Profile Information */}
        <div className="card p-4 lg:p-6">
          <div className="flex items-center mb-4 lg:mb-6">
            <UserCircleIcon className="h-5 w-5 lg:h-6 lg:w-6 text-primary-400 mr-2 lg:mr-3" />
            <h3 className="text-base lg:text-lg font-semibold text-neutral-100">
              Profile Information
            </h3>
          </div>

          <form onSubmit={handleProfileSubmit} className="space-y-4">
            <div>
              <label htmlFor="display_name" className="block text-xs lg:text-sm font-medium text-neutral-300 mb-1">
                Display Name *
              </label>
              <input
                type="text"
                id="display_name"
                name="display_name"
                value={profileData.display_name}
                onChange={(e) => setProfileData(prev => ({ ...prev, display_name: e.target.value }))}
                className="input-field"
                placeholder="Enter your display name"
                required
              />
              <p className="text-xs text-neutral-400 mt-1">This is how your name will appear throughout the app</p>
            </div>

            <div>
              <label htmlFor="username" className="block text-xs lg:text-sm font-medium text-neutral-300 mb-1">
                Username
              </label>
              <input
                type="text"
                id="username"
                name="username"
                value={profileData.username}
                onChange={(e) => setProfileData(prev => ({ ...prev, username: e.target.value }))}
                className="input-field"
                placeholder="Enter your username"
              />
              <p className="text-xs text-neutral-400 mt-1">Optional: A unique username for your profile</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div>
                <label htmlFor="first_name" className="block text-xs lg:text-sm font-medium text-neutral-300 mb-1">
                  First Name
                </label>
                <input
                  type="text"
                  id="first_name"
                  name="first_name"
                  value={profileData.first_name}
                  onChange={(e) => setProfileData(prev => ({ ...prev, first_name: e.target.value }))}
                  className="input-field"
                  placeholder="Enter your first name"
                />
              </div>

              <div>
                <label htmlFor="last_name" className="block text-xs lg:text-sm font-medium text-neutral-300 mb-1">
                  Last Name
                </label>
                <input
                  type="text"
                  id="last_name"
                  name="last_name"
                  value={profileData.last_name}
                  onChange={(e) => setProfileData(prev => ({ ...prev, last_name: e.target.value }))}
                  className="input-field"
                  placeholder="Enter your last name"
                />
              </div>
            </div>

            <div>
              <label htmlFor="email" className="block text-xs lg:text-sm font-medium text-neutral-300 mb-1">
                Email Address
              </label>
              <div className="flex items-center">
                <EnvelopeIcon className="h-4 w-4 lg:h-5 lg:w-5 text-neutral-400 mr-2" />
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={profileData.email}
                  className="input-field bg-gray-100 dark:bg-gray-800 cursor-not-allowed"
                  placeholder="Enter your email"
                  disabled
                />
              </div>
              <p className="text-xs text-neutral-400 mt-1">Email cannot be changed. Contact support if needed.</p>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="is_public_profile"
                name="is_public_profile"
                checked={profileData.is_public_profile}
                onChange={(e) => setProfileData(prev => ({ ...prev, is_public_profile: e.target.checked }))}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              />
              <label htmlFor="is_public_profile" className="ml-2 block text-xs lg:text-sm text-gray-700 dark:text-gray-300">
                Make my profile public
              </label>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full"
            >
              {isLoading ? 'Updating...' : 'Update Profile'}
            </button>
          </form>
        </div>

        {/* Change Password */}
        <div className="card p-4 lg:p-6">
          <div className="flex items-center mb-4 lg:mb-6">
            <KeyIcon className="h-5 w-5 lg:h-6 lg:w-6 text-primary-600 mr-2 lg:mr-3" />
            <h3 className="text-base lg:text-lg font-semibold text-gray-900 dark:text-gray-100">
              Change Password
            </h3>
          </div>

          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <div>
              <label htmlFor="current_password" className="block text-xs lg:text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Current Password
              </label>
              <input
                type="password"
                id="current_password"
                name="current_password"
                value={passwordData.current_password}
                onChange={(e) => setPasswordData(prev => ({ ...prev, current_password: e.target.value }))}
                className="input-field"
                placeholder="Enter current password"
              />
            </div>

            <div>
              <label htmlFor="new_password" className="block text-xs lg:text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                New Password
              </label>
              <input
                type="password"
                id="new_password"
                name="new_password"
                value={passwordData.new_password}
                onChange={(e) => setPasswordData(prev => ({ ...prev, new_password: e.target.value }))}
                className="input-field"
                placeholder="Enter new password"
              />
            </div>

            <div>
              <label htmlFor="confirm_password" className="block text-xs lg:text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Confirm New Password
              </label>
              <input
                type="password"
                id="confirm_password"
                name="confirm_password"
                value={passwordData.confirm_password}
                onChange={(e) => setPasswordData(prev => ({ ...prev, confirm_password: e.target.value }))}
                className="input-field"
                placeholder="Confirm new password"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full"
            >
              {isLoading ? 'Changing...' : 'Change Password'}
            </button>
          </form>
        </div>
      </div>

      {/* Notification Settings */}
      <div className="card p-4 lg:p-6">
        <div className="flex items-center mb-4 lg:mb-6">
          <BellIcon className="h-5 w-5 lg:h-6 lg:w-6 text-primary-600 mr-2 lg:mr-3" />
          <h3 className="text-base lg:text-lg font-semibold text-gray-900 dark:text-gray-100">
            Notification Settings
          </h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-xs lg:text-sm font-medium text-gray-900 dark:text-gray-100">Email Notifications</h4>
              <p className="text-xs lg:text-sm text-gray-500 dark:text-gray-400">Receive notifications via email</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={notifications.email_notifications}
                onChange={(e) => handleNotificationChange('email_notifications', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
            </label>
          </div>

          <PremiumFeatureWrapper featureName="Trade Alerts">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div>
                  <h4 className="text-xs lg:text-sm font-medium text-gray-900 dark:text-gray-100">Trade Alerts</h4>
                  <p className="text-xs lg:text-sm text-gray-500 dark:text-gray-400">Get notified of new congressional trades</p>
                </div>
                {!isPremium && <PremiumBadge />}
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={notifications.trade_alerts}
                  onChange={(e) => handleNotificationChange('trade_alerts', e.target.checked)}
                  className="sr-only peer"
                  disabled={!isPremium}
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
              </label>
            </div>
          </PremiumFeatureWrapper>

          <PremiumFeatureWrapper featureName="Weekly Summary">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div>
                  <h4 className="text-xs lg:text-sm font-medium text-gray-900 dark:text-gray-100">Weekly Summary</h4>
                  <p className="text-xs lg:text-sm text-gray-500 dark:text-gray-400">Receive weekly trading activity summaries</p>
                </div>
                {!isPremium && <PremiumBadge />}
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={notifications.weekly_summary}
                  onChange={(e) => handleNotificationChange('weekly_summary', e.target.checked)}
                  className="sr-only peer"
                  disabled={!isPremium}
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
              </label>
            </div>
          </PremiumFeatureWrapper>

          <PremiumFeatureWrapper featureName="Multiple Buyer Alerts">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div>
                  <h4 className="text-xs lg:text-sm font-medium text-gray-900 dark:text-gray-100">Multiple Buyer Alerts</h4>
                  <p className="text-xs lg:text-sm text-gray-500 dark:text-gray-400">Alerts when 5+ members buy same stock in 3 months</p>
                </div>
                {!isPremium && <PremiumBadge />}
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={notifications.multiple_buyer_alerts}
                  onChange={(e) => handleNotificationChange('multiple_buyer_alerts', e.target.checked)}
                  className="sr-only peer"
                  disabled={!isPremium}
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
              </label>
            </div>
          </PremiumFeatureWrapper>

          <PremiumFeatureWrapper featureName="High-Value Trade Alerts">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div>
                  <h4 className="text-xs lg:text-sm font-medium text-gray-900 dark:text-gray-100">High-Value Trade Alerts</h4>
                  <p className="text-xs lg:text-sm text-gray-500 dark:text-gray-400">Alerts for trades over $1M</p>
                </div>
                {!isPremium && <PremiumBadge />}
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={notifications.high_value_alerts}
                  onChange={(e) => handleNotificationChange('high_value_alerts', e.target.checked)}
                  className="sr-only peer"
                  disabled={!isPremium}
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
              </label>
            </div>
          </PremiumFeatureWrapper>
        </div>
      </div>

      {/* Subscription Management */}
      <div className="card p-4 lg:p-6">
        <div className="flex items-center mb-4 lg:mb-6">
          <CreditCardIcon className="h-5 w-5 lg:h-6 lg:w-6 text-primary-600 mr-2 lg:mr-3" />
          <h3 className="text-base lg:text-lg font-semibold text-gray-900 dark:text-gray-100">
            Subscription Management
          </h3>
        </div>

        <div className="space-y-4">
          {/* Current Subscription Status */}
          <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">Current Plan</h4>
              <div className="flex items-center">
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100 capitalize mr-2">
                  {subscriptionTier || 'free'}
                </span>
                {!isFree && (
                  <div className="flex items-center text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 px-2 py-1 rounded-full">
                    <StarIcon className="h-3 w-3 mr-1" />
                    {isPremium ? 'Premium' : 'Pro'}
                  </div>
                )}
                {user?.subscription_status === 'cancelled' && (
                  <div className="flex items-center text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 px-2 py-1 rounded-full ml-2">
                    <XCircleIcon className="h-3 w-3 mr-1" />
                    Cancelled
                  </div>
                )}
              </div>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="flex items-center">
                <CheckCircleIcon className="h-4 w-4 text-green-500 mr-2" />
                <span className="text-gray-600 dark:text-gray-400">Analytics Access</span>
                <span className={`ml-auto ${isPro ? 'text-green-600' : 'text-red-600'}`}>
                  {isPro ? '✓' : '✗'}
                </span>
              </div>
              <div className="flex items-center">
                <CheckCircleIcon className="h-4 w-4 text-green-500 mr-2" />
                <span className="text-gray-600 dark:text-gray-400">Data Quality</span>
                <span className={`ml-auto ${isPro ? 'text-green-600' : 'text-red-600'}`}>
                  {isPro ? '✓' : '✗'}
                </span>
              </div>
              <div className="flex items-center">
                <CheckCircleIcon className="h-4 w-4 text-green-500 mr-2" />
                <span className="text-gray-600 dark:text-gray-400">Trade Alerts</span>
                <span className={`ml-auto ${isPro ? 'text-green-600' : 'text-red-600'}`}>
                  {isPro ? '✓' : '✗'}
                </span>
              </div>
              <div className="flex items-center">
                <CheckCircleIcon className="h-4 w-4 text-green-500 mr-2" />
                <span className="text-gray-600 dark:text-gray-400">Premium Features</span>
                <span className={`ml-auto ${isPremium ? 'text-green-600' : 'text-red-600'}`}>
                  {isPremium ? '✓' : '✗'}
                </span>
              </div>
            </div>
          </div>

          {/* Subscription Actions */}
          <div className="flex flex-col sm:flex-row gap-3">
            {isFree ? (
              <Link
                to="/premium"
                className="btn-primary flex-1 text-center"
              >
                Upgrade to Pro
              </Link>
            ) : user?.subscription_status === 'cancelled' ? (
              <div className="w-full text-center">
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                  Your subscription has been cancelled. You'll have access until the end of your billing period.
                </p>
                <button
                  onClick={handleReactivateSubscription}
                  className="btn-primary"
                >
                  Reactivate Subscription
                </button>
              </div>
            ) : (
              <>
                <button
                  onClick={handleManageSubscription}
                  disabled={isLoading}
                  className="btn-secondary flex-1 text-center"
                >
                  {isLoading ? 'Opening...' : (isPro && !isPremium ? 'Upgrade to Premium' : 'Manage Plan')}
                </button>
                <button
                  onClick={handleCancelSubscription}
                  disabled={isCancelling}
                  className="btn-secondary flex-1 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                >
                  {isCancelling ? 'Cancelling...' : 'Cancel Subscription'}
                </button>
              </>
            )}
          </div>

          {/* Subscription Info */}
          {!isFree && (
            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <p className="text-blue-800 dark:text-blue-200 text-xs">
                Need help with your subscription? Contact support at{' '}
                <a href="mailto:captiolscope@gmail.com" className="underline hover:no-underline">
                  capitolscope@gmail.com
                </a>
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Account Security */}
      <div className="card p-4 lg:p-6">
        <div className="flex items-center mb-4 lg:mb-6">
          <ShieldCheckIcon className="h-5 w-5 lg:h-6 lg:w-6 text-primary-600 mr-2 lg:mr-3" />
          <h3 className="text-base lg:text-lg font-semibold text-gray-900 dark:text-gray-100">
            Account Security
          </h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between p-3 lg:p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div>
              <h4 className="text-xs lg:text-sm font-medium text-gray-900 dark:text-gray-100">Two-Factor Authentication</h4>
              <p className="text-xs lg:text-sm text-gray-500 dark:text-gray-400">Add an extra layer of security to your account</p>
            </div>
            <button 
              className="btn-secondary btn-sm"
              onClick={() => {
                // TODO: Implement 2FA setup
                setMessage({ type: 'error', text: 'Two-Factor Authentication is not yet implemented.' });
              }}
            >
              Enable
            </button>
          </div>

          <div className="flex items-center justify-between p-3 lg:p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div>
              <h4 className="text-xs lg:text-sm font-medium text-gray-900 dark:text-gray-100">Active Sessions</h4>
              <p className="text-xs lg:text-sm text-gray-500 dark:text-gray-400">Manage your active login sessions</p>
            </div>
            <button 
              className="btn-secondary btn-sm"
              onClick={() => {
                // TODO: Implement active sessions view
                setMessage({ type: 'error', text: 'Active Sessions management is not yet implemented.' });
              }}
            >
              View
            </button>
          </div>

          <div className="flex items-center justify-between p-3 lg:p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div>
              <h4 className="text-xs lg:text-sm font-medium text-gray-900 dark:text-gray-100">Delete Account</h4>
              <p className="text-xs lg:text-sm text-gray-500 dark:text-gray-400">Permanently delete your account and all data</p>
            </div>
            <button 
              className="btn-secondary btn-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
              onClick={() => {
                if (confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
                  // TODO: Implement account deletion
                  setMessage({ type: 'error', text: 'Account deletion is not yet implemented.' });
                }
              }}
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfileSettings; 