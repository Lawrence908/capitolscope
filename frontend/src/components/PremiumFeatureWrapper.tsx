import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { StarIcon } from '@heroicons/react/24/outline';

interface PremiumFeatureWrapperProps {
  children: React.ReactNode;
  featureName: string;
  requiredTier?: 'pro' | 'premium' | 'enterprise';
  showBadge?: boolean;
  className?: string;
}

const PremiumFeatureWrapper: React.FC<PremiumFeatureWrapperProps> = ({ 
  children, 
  featureName, 
  requiredTier = 'pro',
  showBadge = true,
  className = ''
}) => {
  const { user } = useAuth();
  const navigate = useNavigate();

  // Check if user has the required subscription tier
  const hasRequiredTier = () => {
    if (!user) return false;
    
    const subscriptionTier = user.subscription_tier?.toLowerCase();
    
    switch (requiredTier) {
      case 'pro':
        return ['pro', 'premium', 'enterprise'].includes(subscriptionTier);
      case 'premium':
        return ['premium', 'enterprise'].includes(subscriptionTier);
      case 'enterprise':
        return subscriptionTier === 'enterprise';
      default:
        return false;
    }
  };

  const PremiumBadge = () => (
    <div className="inline-flex items-center border-2 border-content px-1.5 py-px font-display text-[12px] font-extrabold uppercase leading-tight tracking-[0.04em] text-content">
      <StarIcon className="mr-1 h-3 w-3" />
      {requiredTier === 'pro' ? 'Pro' : requiredTier === 'premium' ? 'Premium' : 'Enterprise'}
    </div>
  );

  const handlePremiumFeatureClick = () => {
    if (!hasRequiredTier()) {
      // Show upgrade prompt and redirect to premium page
      navigate('/premium', { 
        state: { 
          from: window.location.pathname, 
          requiredTier,
          featureName 
        } 
      });
    }
  };

  if (hasRequiredTier()) {
    return <div className={className}>{children}</div>;
  }

  return (
    <div 
      className={`opacity-60 cursor-not-allowed ${className}`} 
      onClick={handlePremiumFeatureClick}
      title={`${featureName} requires a ${requiredTier} subscription`}
    >
      {children}
      {showBadge && <PremiumBadge />}
    </div>
  );
};

export default PremiumFeatureWrapper;
