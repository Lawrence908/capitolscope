import React, { useState } from 'react';
import { MemberAlertForm } from './MemberAlertForm';
import { AmountAlertForm } from './AmountAlertForm';
import { TickerAlertForm } from './TickerAlertForm';
import { CreateAlertData } from '../../hooks/useAlerts';

interface CreateAlertModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (alertData: CreateAlertData) => Promise<void>;
}

export const CreateAlertModal: React.FC<CreateAlertModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [selectedType, setSelectedType] = useState<string>('');
  const [formData, setFormData] = useState<Record<string, unknown>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const alertTypes = [
    {
      id: 'member_trades',
      name: 'Member Trades',
      description: 'Get notified when a specific congress member makes trades',
      icon: '👤',
      example: 'MTG, Nancy Pelosi, etc.',
    },
    {
      id: 'amount_threshold',
      name: 'Large Trades',
      description: 'Get notified when any member makes trades above a certain amount',
      icon: '💰',
      example: '$1M+, $500K+, etc.',
    },
    {
      id: 'ticker_trades',
      name: 'Stock Alerts',
      description: 'Get notified when any member trades a specific stock',
      icon: '📈',
      example: 'TSLA, AAPL, NVDA, etc.',
    },
  ];

  const handleSubmit = async () => {
    if (!selectedType || !formData) return;

    setIsSubmitting(true);
    try {
      await onSubmit({
        alert_type: selectedType as 'member_trades' | 'amount_threshold' | 'ticker_trades',
        ...formData,
      });
      // Reset form
      setSelectedType('');
      setFormData({});
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderForm = () => {
    switch (selectedType) {
      case 'member_trades':
        return <MemberAlertForm onDataChange={setFormData} />;
      case 'amount_threshold':
        return <AmountAlertForm onDataChange={setFormData} />;
      case 'ticker_trades':
        return <TickerAlertForm onDataChange={setFormData} />;
      default:
        return null;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-surface-raised rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-line">
          <h2 className="text-xl font-semibold text-content">Create New Trade Alert</h2>
        </div>
        
        <div className="p-6">
          {!selectedType ? (
            <div className="space-y-4">
              <p className="text-content-muted text-center mb-6">
                Choose the type of trade alert you want to create
              </p>
              
              {alertTypes.map((type) => (
                <button
                  key={type.id}
                  onClick={() => setSelectedType(type.id)}
                  className="w-full p-6 border border-line rounded-lg hover:border-accent hover:bg-accent/10 transition-colors text-left"
                >
                  <div className="flex items-start space-x-4">
                    <div className="text-2xl">{type.icon}</div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-lg text-content mb-2">
                        {type.name}
                      </h3>
                      <p className="text-content-muted mb-2">
                        {type.description}
                      </p>
                      <p className="text-sm text-accent font-medium">
                        Example: {type.example}
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="space-y-6">
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setSelectedType('')}
                  className="text-content-faint hover:text-content-muted text-sm"
                >
                  ← Back
                </button>
                <h3 className="font-semibold text-lg">
                  {alertTypes.find(t => t.id === selectedType)?.name}
                </h3>
              </div>
              
              {renderForm()}
            </div>
          )}
        </div>
        
        <div className="p-6 border-t border-line flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-content-muted border border-line rounded-lg hover:bg-surface-inset"
          >
            Cancel
          </button>
          {selectedType && (
            <button
              onClick={handleSubmit}
              disabled={isSubmitting || !formData || Object.keys(formData).length === 0}
              className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent-strong disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Creating...' : 'Create Alert'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
