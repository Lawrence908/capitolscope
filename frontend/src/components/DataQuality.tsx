import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Link } from 'react-router-dom';
import { SparklesIcon } from '@heroicons/react/24/outline';
import PremiumFeatureWrapper from './PremiumFeatureWrapper';
import DataQualityDashboard from './DataQualityDashboard';

const DataQuality: React.FC = () => {
  const { user } = useAuth();
  
  // Check subscription tier
  const subscriptionTier = user?.subscription_tier?.toLowerCase();
  const isPremium = subscriptionTier === 'premium' || subscriptionTier === 'enterprise';
  const isPro = subscriptionTier === 'pro' || isPremium;
  const isFree = subscriptionTier === 'free' || !subscriptionTier;

  return (
    <div className="space-y-4 lg:space-y-6">
      {/* Premium Upgrade Banner for Free Users */}
      {isFree && (
        <div className="card p-4 lg:p-6 bg-neon-gradient rounded-lg shadow-glow-primary">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center">
              <SparklesIcon className="h-5 w-5 lg:h-6 lg:w-6 text-bg-primary mr-2 lg:mr-3" />
              <div>
                <h4 className="text-base lg:text-lg font-bold text-bg-primary mb-1">Unlock Data Quality Insights</h4>
                <p className="text-bg-primary/80 text-xs lg:text-sm">
                  Get access to comprehensive data quality metrics and validation tools
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

      <PremiumFeatureWrapper featureName="Data Quality Dashboard" requiredTier="pro" showBadge={false}>
        <DataQualityDashboard />
      </PremiumFeatureWrapper>
    </div>
  );
};

export default DataQuality; 