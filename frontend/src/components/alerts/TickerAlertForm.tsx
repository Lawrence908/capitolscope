import React, { useState, useEffect } from 'react';

interface TickerAlertFormData {
  name: string;
  target_symbol: string;
  target_name: string;
}

interface TickerAlertFormProps {
  onDataChange: (data: Partial<TickerAlertFormData>) => void;
}

interface StockInfo {
  symbol: string;
  name: string;
  price?: number;
  change?: number;
}

export const TickerAlertForm: React.FC<TickerAlertFormProps> = ({ onDataChange }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStock, setSelectedStock] = useState<StockInfo | null>(null);
  const [alertName, setAlertName] = useState('');
  // const [isSearching, setIsSearching] = useState(false);

  // Mock stock data - in a real app, this would come from a stock API
  const popularStocks = [
    { symbol: 'AAPL', name: 'Apple Inc.' },
    { symbol: 'TSLA', name: 'Tesla, Inc.' },
    { symbol: 'NVDA', name: 'NVIDIA Corporation' },
    { symbol: 'MSFT', name: 'Microsoft Corporation' },
    { symbol: 'GOOGL', name: 'Alphabet Inc.' },
    { symbol: 'AMZN', name: 'Amazon.com, Inc.' },
    { symbol: 'META', name: 'Meta Platforms, Inc.' },
    { symbol: 'NFLX', name: 'Netflix, Inc.' },
  ];

  const [searchResults, setSearchResults] = useState<StockInfo[]>([]);

  const searchStocks = (query: string) => {
    if (query.length < 1) {
      setSearchResults([]);
      return;
    }

    const filtered = popularStocks.filter(stock =>
      stock.symbol.toLowerCase().includes(query.toLowerCase()) ||
      stock.name.toLowerCase().includes(query.toLowerCase())
    );
    
    setSearchResults(filtered);
  };

  // searchStocks is a pure filter over a static list; intentionally re-run only
  // when the query changes (adding it as a dep would re-run every render).
  useEffect(() => {
    searchStocks(searchQuery);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery]);

  useEffect(() => {
    if (selectedStock && alertName) {
      onDataChange({
        name: alertName,
        target_symbol: selectedStock.symbol,
        target_name: selectedStock.name,
      });
    } else {
      onDataChange({});
    }
  }, [selectedStock, alertName, onDataChange]);

  const handleStockSelect = (stock: StockInfo) => {
    setSelectedStock(stock);
    setSearchQuery('');
    setSearchResults([]);
    
    // Auto-generate alert name if not set
    if (!alertName) {
      setAlertName(`${stock.symbol} Trade Alert`);
    }
  };

  const handleManualEntry = () => {
    if (searchQuery.trim()) {
      const stock = {
        symbol: searchQuery.toUpperCase(),
        name: `${searchQuery.toUpperCase()} Stock`,
      };
      handleStockSelect(stock);
    }
  };

  return (
    <div className="space-y-6">
      {/* Stock Selection */}
      <div>
        <label className="block text-sm font-medium text-content-muted mb-2">
          Select Stock Symbol
        </label>
        
        {selectedStock ? (
          <div className="flex items-center justify-between p-4 border border-line rounded-lg bg-surface-inset">
            <div>
              <h3 className="font-semibold text-content">
                {selectedStock.symbol}
              </h3>
              <p className="text-sm text-content-muted">
                {selectedStock.name}
              </p>
            </div>
            <button
              onClick={() => setSelectedStock(null)}
              className="text-content-faint hover:text-content-muted"
            >
              ✕
            </button>
          </div>
        ) : (
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value.toUpperCase())}
              placeholder="Search for a stock symbol (e.g., TSLA, AAPL)..."
              className="w-full px-4 py-2 border border-line rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent"
            />
            
            {searchQuery && searchResults.length === 0 && (
              <div className="absolute top-full left-0 right-0 bg-surface-raised border border-line rounded-lg mt-1 p-3 shadow-lg">
                <div className="text-center">
                  <p className="text-content-muted mb-2">No matches found</p>
                  <button
                    onClick={handleManualEntry}
                    className="text-accent hover:text-accent-strong font-medium"
                  >
                    Add "{searchQuery}" manually
                  </button>
                </div>
              </div>
            )}
            
            {searchResults.length > 0 && (
              <div className="absolute top-full left-0 right-0 bg-surface-raised border border-line rounded-lg mt-1 max-h-64 overflow-y-auto z-10 shadow-lg">
                {searchResults.map((stock) => (
                  <button
                    key={stock.symbol}
                    onClick={() => handleStockSelect(stock)}
                    className="w-full flex items-center justify-between p-3 hover:bg-surface-inset text-left"
                  >
                    <div>
                      <div className="font-semibold text-content">
                        {stock.symbol}
                      </div>
                      <div className="text-sm text-content-muted">
                        {stock.name}
                      </div>
                    </div>
                    <div className="text-sm text-content-faint">
                      Stock
                    </div>
                  </button>
                ))}
                {searchQuery && !searchResults.some(s => s.symbol === searchQuery.toUpperCase()) && (
                  <button
                    onClick={handleManualEntry}
                    className="w-full p-3 border-t border-line text-left hover:bg-surface-inset"
                  >
                    <div className="text-accent font-medium">
                      Add "{searchQuery}" manually
                    </div>
                    <div className="text-sm text-content-faint">
                      Enter custom symbol
                    </div>
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Popular Stocks */}
      {!selectedStock && !searchQuery && (
        <div>
          <label className="block text-sm font-medium text-content-muted mb-3">
            Popular Stocks
          </label>
          <div className="grid grid-cols-2 gap-2">
            {popularStocks.slice(0, 8).map((stock) => (
              <button
                key={stock.symbol}
                onClick={() => handleStockSelect(stock)}
                className="p-3 border border-line rounded-lg hover:border-accent hover:bg-accent/10 text-left transition-colors"
              >
                <div className="font-semibold text-content">{stock.symbol}</div>
                <div className="text-xs text-content-muted truncate">{stock.name}</div>
              </button>
            ))}
          </div>
        </div>
      )}

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
      {selectedStock && alertName && (
        <div className="bg-accent-2/10 border border-accent-2/30 rounded-lg p-4">
          <h4 className="font-medium text-accent-2 mb-2">Alert Preview</h4>
          <p className="text-accent-2">
            You will receive notifications whenever any congress member files a trade disclosure 
            for <span className="font-semibold">{selectedStock.symbol}</span> ({selectedStock.name}).
          </p>
        </div>
      )}
    </div>
  );
};
