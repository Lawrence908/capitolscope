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

  useEffect(() => {
    searchStocks(searchQuery);
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
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select Stock Symbol
        </label>
        
        {selectedStock ? (
          <div className="flex items-center justify-between p-4 border border-gray-300 rounded-lg bg-gray-50">
            <div>
              <h3 className="font-semibold text-gray-900">
                {selectedStock.symbol}
              </h3>
              <p className="text-sm text-gray-600">
                {selectedStock.name}
              </p>
            </div>
            <button
              onClick={() => setSelectedStock(null)}
              className="text-gray-400 hover:text-gray-600"
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
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            
            {searchQuery && searchResults.length === 0 && (
              <div className="absolute top-full left-0 right-0 bg-white border border-gray-300 rounded-lg mt-1 p-3 shadow-lg">
                <div className="text-center">
                  <p className="text-gray-600 mb-2">No matches found</p>
                  <button
                    onClick={handleManualEntry}
                    className="text-primary-600 hover:text-primary-700 font-medium"
                  >
                    Add "{searchQuery}" manually
                  </button>
                </div>
              </div>
            )}
            
            {searchResults.length > 0 && (
              <div className="absolute top-full left-0 right-0 bg-white border border-gray-300 rounded-lg mt-1 max-h-64 overflow-y-auto z-10 shadow-lg">
                {searchResults.map((stock) => (
                  <button
                    key={stock.symbol}
                    onClick={() => handleStockSelect(stock)}
                    className="w-full flex items-center justify-between p-3 hover:bg-gray-50 text-left"
                  >
                    <div>
                      <div className="font-semibold text-gray-900">
                        {stock.symbol}
                      </div>
                      <div className="text-sm text-gray-600">
                        {stock.name}
                      </div>
                    </div>
                    <div className="text-sm text-gray-500">
                      Stock
                    </div>
                  </button>
                ))}
                {searchQuery && !searchResults.some(s => s.symbol === searchQuery.toUpperCase()) && (
                  <button
                    onClick={handleManualEntry}
                    className="w-full p-3 border-t border-gray-200 text-left hover:bg-gray-50"
                  >
                    <div className="text-primary-600 font-medium">
                      Add "{searchQuery}" manually
                    </div>
                    <div className="text-sm text-gray-500">
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
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Popular Stocks
          </label>
          <div className="grid grid-cols-2 gap-2">
            {popularStocks.slice(0, 8).map((stock) => (
              <button
                key={stock.symbol}
                onClick={() => handleStockSelect(stock)}
                className="p-3 border border-gray-300 rounded-lg hover:border-primary-300 hover:bg-primary-50 text-left transition-colors"
              >
                <div className="font-semibold text-gray-900">{stock.symbol}</div>
                <div className="text-xs text-gray-600 truncate">{stock.name}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Alert Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Alert Name
        </label>
        <input
          type="text"
          value={alertName}
          onChange={(e) => setAlertName(e.target.value)}
          placeholder="Enter a name for this alert"
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
        />
        <p className="text-sm text-gray-500 mt-1">
          Give your alert a descriptive name so you can easily identify it
        </p>
      </div>

      {/* Preview */}
      {selectedStock && alertName && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <h4 className="font-medium text-purple-900 mb-2">Alert Preview</h4>
          <p className="text-purple-800">
            You will receive notifications whenever any congress member files a trade disclosure 
            for <span className="font-semibold">{selectedStock.symbol}</span> ({selectedStock.name}).
          </p>
        </div>
      )}
    </div>
  );
};
