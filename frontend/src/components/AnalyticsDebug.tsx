import React from 'react';
import { useAuth } from '../contexts/AuthContext';

const AnalyticsDebug: React.FC = () => {
  const { user, isLoading, isAuthenticated } = useAuth();

  if (isLoading) {
    return (
      <div className="card p-4">
        <p className="text-content-faint">Loading user data...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="card p-4">
        <p className="text-sev-flag">Not authenticated</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="card p-4">
        <p className="text-sev-flag">No user data available</p>
      </div>
    );
  }

  const subscriptionTier = user.subscription_tier?.toLowerCase();
  const isPremium = subscriptionTier === 'premium' || subscriptionTier === 'enterprise';
  const isPro = subscriptionTier === 'pro' || isPremium;
  const isFree = subscriptionTier === 'free' || !subscriptionTier;

  return (
    <div className="card p-4 lg:p-6">
      <h3 className="text-lg font-semibold text-content mb-4">Analytics Access Debug</h3>
      
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-content-faint">User ID:</span>
          <span className="text-content font-mono text-sm">{user.id}</span>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-content-faint">Email:</span>
          <span className="text-content">{user.email}</span>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-content-faint">Subscription Tier:</span>
          <span className="text-content font-medium capitalize">{subscriptionTier || 'free'}</span>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-content-faint">Is Free:</span>
          <span className={isFree ? 'text-sev-flag' : 'text-accent'}>
            {isFree ? 'Yes' : 'No'}
          </span>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-content-faint">Is Pro:</span>
          <span className={isPro ? 'text-accent' : 'text-sev-flag'}>
            {isPro ? 'Yes' : 'No'}
          </span>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-content-faint">Is Premium:</span>
          <span className={isPremium ? 'text-accent' : 'text-sev-flag'}>
            {isPremium ? 'Yes' : 'No'}
          </span>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-content-faint">Can Access Analytics:</span>
          <span className={isPro ? 'text-accent' : 'text-sev-flag'}>
            {isPro ? 'Yes' : 'No'}
          </span>
        </div>
      </div>
      
      {isFree && (
        <div className="mt-4 p-3 bg-sev-watch/10 dark:bg-sev-watch/10 border border-sev-watch/30 dark:border-sev-watch/30 rounded-lg">
          <p className="text-sev-watch dark:text-sev-watch text-sm">
            You're on the free tier. You need Pro or higher to access Analytics.
          </p>
        </div>
      )}
      
      {isPro && (
        <div className="mt-4 p-3 bg-accent/10 dark:bg-accent/10 border border-accent/30 dark:border-accent/30 rounded-lg">
          <p className="text-accent dark:text-accent text-sm">
            You should be able to access Analytics. If you can't see it, there might be a technical issue.
          </p>
        </div>
      )}
    </div>
  );
};

export default AnalyticsDebug;
