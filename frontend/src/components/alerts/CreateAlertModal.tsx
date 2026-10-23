import React, { useState } from 'react';
import { MemberAlertForm } from './MemberAlertForm';
import { AmountAlertForm } from './AmountAlertForm';
import { TickerAlertForm } from './TickerAlertForm';
import type { CreateAlertData } from '../../hooks/useAlerts';

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
      icon: 'M',
      example: 'MTG, Nancy Pelosi, etc.',
    },
    {
      id: 'amount_threshold',
      name: 'Large Trades',
      description: 'Get notified when any member makes trades above a certain amount',
      icon: '$',
      example: '$1M+, $500K+, etc.',
    },
    {
      id: 'ticker_trades',
      name: 'Stock Alerts',
      description: 'Get notified when any member trades a specific stock',
      icon: 'T',
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
      } as CreateAlertData);
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
      <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto border-2 border-content bg-surface-raised">
        <div className="bg-slab p-6 text-slab-on">
          <h2 className="font-display text-4xl font-extrabold leading-none text-slab-on">Create a trade alert</h2>
        </div>
        
        <div className="p-6">
          {!selectedType ? (
            <div className="space-y-4">
              <p className="mb-6 font-ui text-sm text-content-muted">
                Choose the type of trade alert you want to create
              </p>
              
              {alertTypes.map((type) => (
                <button
                  key={type.id}
                  onClick={() => setSelectedType(type.id)}
                  className="w-full border-2 border-line p-5 text-left transition-colors hover:border-content hover:bg-surface-inset"
                >
                  <div className="flex items-start space-x-4">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center bg-slab font-display text-2xl font-extrabold text-slab-on">{type.icon}</div>
                    <div className="flex-1">
                      <h3 className="mb-1 font-display text-2xl font-extrabold leading-none text-content">
                        {type.name}
                      </h3>
                      <p className="mb-2 font-ui text-sm text-content-muted">
                        {type.description}
                      </p>
                      <p className="font-ui text-xs font-semibold text-content-faint">
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
                  className="font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-accent hover:text-accent-strong"
                >
                  ← Back
                </button>
                <h3 className="font-display text-2xl font-extrabold leading-none text-content">
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
            className="btn-outline"
          >
            Cancel
          </button>
          {selectedType && (
            <button
              onClick={handleSubmit}
              disabled={isSubmitting || !formData || Object.keys(formData).length === 0}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Creating…' : 'Create alert'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
