import React, { useEffect, useState } from 'react';
import apiClient from '../services/api';
import { DataQualityStats } from '../types';

const DataQuality: React.FC = () => {
  const [stats, setStats] = useState<DataQualityStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await apiClient.getDataQualityStats();
        setStats(response.data);
      } catch (err) {
        setError('Failed to load data quality stats');
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="flex">
          <span className="text-red-400 font-bold mr-2">!</span>
          <div className="ml-3">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!stats) {
    return <div className="p-6">No data available.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">Data Quality Overview</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-4">
          <div className="bg-blue-100 dark:bg-blue-900 p-4 rounded">
            <div className="text-sm text-gray-600 dark:text-gray-300">Total Trades</div>
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.total_trades.toLocaleString()}</div>
          </div>
          <div className="bg-green-100 dark:bg-green-900 p-4 rounded">
            <div className="text-sm text-gray-600 dark:text-gray-300">Trades With Ticker</div>
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.trades_with_ticker.toLocaleString()}</div>
          </div>
          <div className="bg-yellow-100 dark:bg-yellow-900 p-4 rounded">
            <div className="text-sm text-gray-600 dark:text-gray-300">Trades Without Ticker</div>
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.trades_without_ticker.toLocaleString()}</div>
          </div>
          <div className="bg-red-100 dark:bg-red-900 p-4 rounded">
            <div className="text-sm text-gray-600 dark:text-gray-300">Null Ticker %</div>
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.null_ticker_percentage.toFixed(2)}%</div>
          </div>
        </div>
      </div>

      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Unique Entities</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-300">Unique Members</div>
            <div className="text-xl font-bold text-gray-900 dark:text-gray-100">{stats.unique_members.toLocaleString()}</div>
          </div>
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-300">Unique Tickers</div>
            <div className="text-xl font-bold text-gray-900 dark:text-gray-100">{stats.unique_tickers.toLocaleString()}</div>
          </div>
        </div>
      </div>

      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Party Distribution</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(stats.party_distribution).map(([party, count]) => (
            <div key={party} className="text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{count}</div>
              <div className="text-sm text-gray-600 dark:text-gray-400">{party}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Chamber Distribution</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(stats.chamber_distribution).map(([chamber, count]) => (
            <div key={chamber} className="text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{count}</div>
              <div className="text-sm text-gray-600 dark:text-gray-400">{chamber}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Amount Ranges</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Range</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Count</th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {Object.entries(stats.amount_ranges).map(([range, count]) => (
                <tr key={range}>
                  <td className="px-6 py-4 whitespace-nowrap">{range}</td>
                  <td className="px-6 py-4 whitespace-nowrap">{count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default DataQuality; 