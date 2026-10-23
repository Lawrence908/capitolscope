import React from 'react';
import { useAuth } from '../contexts/AuthContext';

const AnalyticsDebug: React.FC = () => {
  const { user, isLoading, isAuthenticated } = useAuth();

  if (isLoading) {
    return (
      <div className="section-rule py-4 font-ui text-sm">
        <p className="text-content-faint">Loading user data</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="section-rule py-4 font-ui text-sm">
        <p className="text-accent">Not authenticated</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="section-rule py-4 font-ui text-sm">
        <p className="text-accent">No user data available</p>
      </div>
    );
  }

  const subscriptionTier = user.subscription_tier?.toLowerCase();
  const isPremium = subscriptionTier === 'premium' || subscriptionTier === 'enterprise';
  const isPro = subscriptionTier === 'pro' || isPremium;
  const isFree = subscriptionTier === 'free' || !subscriptionTier;

  return (
    <div className="section-rule py-4 font-ui text-sm">
      <h3 className="mb-4 font-display text-2xl font-extrabold leading-none text-content">Analytics access debug</h3>
      
      <div className="divide-y divide-line border-t border-line">
        <div className="flex items-center justify-between py-2">
          <span className="text-content-faint">User ID:</span>
          <span className="text-content font-mono text-sm">{user.id}</span>
        </div>
        
        <div className="flex items-center justify-between py-2">
          <span className="text-content-faint">Email:</span>
          <span className="text-content">{user.email}</span>
        </div>
        
        <div className="flex items-center justify-between py-2">
          <span className="text-content-faint">Subscription Tier:</span>
          <span className="text-content font-medium capitalize">{subscriptionTier || 'free'}</span>
        </div>
        
        <div className="flex items-center justify-between py-2">
          <span className="text-content-faint">Is Free:</span>
          <span className={isFree ? 'text-accent' : 'text-content'}>
            {isFree ? 'Yes' : 'No'}
          </span>
        </div>
        
        <div className="flex items-center justify-between py-2">
          <span className="text-content-faint">Is Pro:</span>
          <span className={isPro ? 'text-content' : 'text-accent'}>
            {isPro ? 'Yes' : 'No'}
          </span>
        </div>
        
        <div className="flex items-center justify-between py-2">
          <span className="text-content-faint">Is Premium:</span>
          <span className={isPremium ? 'text-content' : 'text-accent'}>
            {isPremium ? 'Yes' : 'No'}
          </span>
        </div>
        
        <div className="flex items-center justify-between py-2">
          <span className="text-content-faint">Can Access Analytics:</span>
          <span className={isPro ? 'text-content' : 'text-accent'}>
            {isPro ? 'Yes' : 'No'}
          </span>
        </div>
      </div>
      
      {isFree && (
        <div className="mt-4 border-l-4 border-accent bg-surface-inset p-3">
          <p className="text-sm text-content">
            You're on the free tier. You need Pro or higher to access Analytics.
          </p>
        </div>
      )}
      
      {isPro && (
        <div className="mt-4 border-l-4 border-content bg-surface-inset p-3">
          <p className="text-sm text-content">
            You should be able to access Analytics. If you can't see it, there might be a technical issue.
          </p>
        </div>
      )}
    </div>
  );
};

export default AnalyticsDebug;
