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
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Create New Trade Alert</h2>
        </div>
        
        <div className="p-6">
          {!selectedType ? (
            <div className="space-y-4">
              <p className="text-gray-600 text-center mb-6">
                Choose the type of trade alert you want to create
              </p>
              
              {alertTypes.map((type) => (
                <button
                  key={type.id}
                  onClick={() => setSelectedType(type.id)}
                  className="w-full p-6 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors text-left"
                >
                  <div className="flex items-start space-x-4">
                    <div className="text-2xl">{type.icon}</div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-lg text-gray-900 mb-2">
                        {type.name}
                      </h3>
                      <p className="text-gray-600 mb-2">
                        {type.description}
                      </p>
                      <p className="text-sm text-primary-600 font-medium">
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
                  className="text-gray-500 hover:text-gray-700 text-sm"
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
        
        <div className="p-6 border-t border-gray-200 flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          {selectedType && (
            <button
              onClick={handleSubmit}
              disabled={isSubmitting || !formData || Object.keys(formData).length === 0}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Creating...' : 'Create Alert'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
