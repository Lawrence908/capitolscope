import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Link } from 'react-router-dom';
import { SparklesIcon } from '@heroicons/react/24/outline';
import PremiumFeatureWrapper from './PremiumFeatureWrapper';
import DataQualityDashboard from './DataQualityDashboard';

const DataQuality: React.FC = () => {
  const { user } = useAuth();
  
  // Check subscription tier (free users see the upgrade banner)
  const subscriptionTier = user?.subscription_tier?.toLowerCase();
  const isFree = subscriptionTier === 'free' || !subscriptionTier;

  return (
    <div className="space-y-4 lg:space-y-6">
      {/* Premium Upgrade Banner for Free Users */}
      {isFree && (
        <div className="flex flex-col gap-4 rounded-md border border-accent/40 bg-accent/10 p-4 sm:flex-row sm:items-center sm:justify-between lg:p-6">
          <div className="flex items-center">
            <SparklesIcon className="mr-3 h-6 w-6 flex-shrink-0 text-accent" />
            <div>
              <h4 className="font-display text-lg font-medium text-content">Unlock Data Quality Insights</h4>
              <p className="font-ui text-sm text-content-muted">
                Comprehensive data quality metrics and validation tools.
              </p>
            </div>
          </div>
          <Link to="/premium" className="btn-primary whitespace-nowrap px-4 py-2 text-sm">
            View Plans
          </Link>
        </div>
      )}

      <PremiumFeatureWrapper featureName="Data Quality Dashboard" requiredTier="pro" showBadge={false}>
        <DataQualityDashboard />
      </PremiumFeatureWrapper>
    </div>
  );
};

export default DataQuality; 