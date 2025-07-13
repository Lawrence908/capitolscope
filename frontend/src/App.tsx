import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import TradeBrowser from './components/TradeBrowser';

// Placeholder components for routes we haven't implemented yet
const Members = () => (
  <div className="card p-6">
    <h2 className="text-xl font-semibold text-gray-900 mb-4">Members</h2>
    <p className="text-gray-600">Member profiles and trading history coming soon...</p>
  </div>
);

const Analytics = () => (
  <div className="card p-6">
    <h2 className="text-xl font-semibold text-gray-900 mb-4">Analytics</h2>
    <p className="text-gray-600">Advanced analytics and visualizations coming soon...</p>
  </div>
);

const DataQuality = () => (
  <div className="card p-6">
    <h2 className="text-xl font-semibold text-gray-900 mb-4">Data Quality</h2>
    <p className="text-gray-600">Data quality dashboard coming soon...</p>
  </div>
);

const App: React.FC = () => {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/trades" element={<TradeBrowser />} />
          <Route path="/members" element={<Members />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/data-quality" element={<DataQuality />} />
        </Routes>
      </Layout>
    </Router>
  );
};

export default App;
