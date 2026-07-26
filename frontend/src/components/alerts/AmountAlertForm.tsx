import React, { useState, useEffect } from 'react';

interface AmountAlertFormData {
  name: string;
  threshold_value: number;
}

interface AmountAlertFormProps {
  onDataChange: (data: Partial<AmountAlertFormData>) => void;
}

export const AmountAlertForm: React.FC<AmountAlertFormProps> = ({ onDataChange }) => {
  const [alertName, setAlertName] = useState('');
  const [thresholdAmount, setThresholdAmount] = useState<number | ''>('');
  const [selectedThreshold, setSelectedThreshold] = useState<string>('');

  const commonThresholds = [
    { value: 50000, label: '$50,000+', description: 'Moderate trades' },
    { value: 100000, label: '$100,000+', description: 'Significant trades' },
    { value: 250000, label: '$250,000+', description: 'Large trades' },
    { value: 500000, label: '$500,000+', description: 'Very large trades' },
    { value: 1000000, label: '$1,000,000+', description: 'Million dollar trades' },
  ];

  useEffect(() => {
    if (thresholdAmount && alertName) {
      onDataChange({
        name: alertName,
        threshold_value: typeof thresholdAmount === 'number' ? thresholdAmount : 0,
      });
    } else {
      onDataChange({});
    }
  }, [thresholdAmount, alertName, onDataChange]);

  const handleThresholdSelect = (amount: number, label: string) => {
    setThresholdAmount(amount);
    setSelectedThreshold(amount.toString());
    
    // Auto-generate alert name if not set
    if (!alertName) {
      setAlertName(`Large Trades ${label}`);
    }
  };

  const handleCustomAmountChange = (value: string) => {
    setSelectedThreshold('custom');
    const numValue = parseFloat(value.replace(/[^0-9.]/g, ''));
    setThresholdAmount(isNaN(numValue) ? '' : numValue);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <div className="space-y-6">
      {/* Threshold Selection */}
      <div>
        <label className="block text-sm font-medium text-content-muted mb-3">
          Amount Threshold
        </label>
        
        <div className="space-y-3">
          {commonThresholds.map((threshold) => (
            <button
              key={threshold.value}
              onClick={() => handleThresholdSelect(threshold.value, threshold.label)}
              className={`w-full flex items-center justify-between p-4 border rounded-lg text-left transition-colors ${
                selectedThreshold === threshold.value.toString()
                  ? 'border-accent bg-accent/10'
                  : 'border-line hover:border-line'
              }`}
            >
              <div>
                <div className="font-semibold text-content">{threshold.label}</div>
                <div className="text-sm text-content-muted">{threshold.description}</div>
              </div>
              <div className={`w-5 h-5 rounded-full border-2 ${
                selectedThreshold === threshold.value.toString()
                  ? 'border-accent bg-accent'
                  : 'border-line'
              }`}>
                {selectedThreshold === threshold.value.toString() && (
                  <div className="w-full h-full rounded-full bg-surface-raised scale-50"></div>
                )}
              </div>
            </button>
          ))}
          
          {/* Custom Amount */}
          <div className={`border rounded-lg p-4 ${
            selectedThreshold === 'custom' ? 'border-accent bg-accent/10' : 'border-line'
          }`}>
            <div className="flex items-center space-x-3">
              <button
                onClick={() => setSelectedThreshold('custom')}
                className={`w-5 h-5 rounded-full border-2 ${
                  selectedThreshold === 'custom'
                    ? 'border-accent bg-accent'
                    : 'border-line'
                }`}
              >
                {selectedThreshold === 'custom' && (
                  <div className="w-full h-full rounded-full bg-surface-raised scale-50"></div>
                )}
              </button>
              <div className="flex-1">
                <label className="block text-sm font-semibold text-content mb-2">
                  Custom Amount
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <span className="text-content-faint sm:text-sm">$</span>
                  </div>
                  <input
                    type="text"
                    value={typeof thresholdAmount === 'number' && selectedThreshold === 'custom' 
                      ? thresholdAmount.toLocaleString() : ''}
                    onChange={(e) => handleCustomAmountChange(e.target.value)}
                    placeholder="Enter amount"
                    className="block w-full pl-7 pr-12 py-2 border border-line rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Alert Name */}
      <div>
        <label className="block text-sm font-medium text-content-muted mb-2">
          Alert Name
        </label>
        <input
          type="text"
          value={alertName}
          onChange={(e) => setAlertName(e.target.value)}
          placeholder="Enter a name for this alert"
          className="w-full px-4 py-2 border border-line rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent"
        />
        <p className="text-sm text-content-faint mt-1">
          Give your alert a descriptive name so you can easily identify it
        </p>
      </div>

      {/* Preview */}
      {thresholdAmount && alertName && (
        <div className="bg-accent/10 border border-accent/30 rounded-lg p-4">
          <h4 className="font-medium text-accent mb-2">Alert Preview</h4>
          <p className="text-accent">
            You will receive notifications whenever any congress member files a trade disclosure 
            for <span className="font-semibold">{formatCurrency(Number(thresholdAmount))} or more</span>.
          </p>
        </div>
      )}
    </div>
  );
};
