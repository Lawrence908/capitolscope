import React from 'react';
import { useAuth } from '../contexts/AuthContext';

const AnalyticsDebug: React.FC = () => {
  const { user, isLoading, isAuthenticated } = useAuth();

  if (isLoading) {
    return (
      <div className="card p-4">
        <p className="text-neutral-400">Loading user data...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="card p-4">
        <p className="text-red-400">Not authenticated</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="card p-4">
        <p className="text-red-400">No user data available</p>
      </div>
    );
  }

  const subscriptionTier = user.subscription_tier?.toLowerCase();
  const isPremium = subscriptionTier === 'premium' || subscriptionTier === 'enterprise';
  const isPro = subscriptionTier === 'pro' || isPremium;
  const isFree = subscriptionTier === 'free' || !subscriptionTier;

  return (
    <div className="card p-4 lg:p-6">
      <h3 className="text-lg font-semibold text-neutral-100 mb-4">Analytics Access Debug</h3>
      
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-neutral-400">User ID:</span>
          <span className="text-neutral-100 font-mono text-sm">{user.id}</span>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-neutral-400">Email:</span>
          <span className="text-neutral-100">{user.email}</span>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-neutral-400">Subscription Tier:</span>
          <span className="text-neutral-100 font-medium capitalize">{subscriptionTier || 'free'}</span>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-neutral-400">Is Free:</span>
          <span className={isFree ? 'text-red-400' : 'text-green-400'}>
            {isFree ? 'Yes' : 'No'}
          </span>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-neutral-400">Is Pro:</span>
          <span className={isPro ? 'text-green-400' : 'text-red-400'}>
            {isPro ? 'Yes' : 'No'}
          </span>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-neutral-400">Is Premium:</span>
          <span className={isPremium ? 'text-green-400' : 'text-red-400'}>
            {isPremium ? 'Yes' : 'No'}
          </span>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-neutral-400">Can Access Analytics:</span>
          <span className={isPro ? 'text-green-400' : 'text-red-400'}>
            {isPro ? 'Yes' : 'No'}
          </span>
        </div>
      </div>
      
      {isFree && (
        <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
          <p className="text-amber-800 dark:text-amber-200 text-sm">
            You're on the free tier. You need Pro or higher to access Analytics.
          </p>
        </div>
      )}
      
      {isPro && (
        <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
          <p className="text-green-800 dark:text-green-200 text-sm">
            You should be able to access Analytics. If you can't see it, there might be a technical issue.
          </p>
        </div>
      )}
    </div>
  );
};

export default AnalyticsDebug;
