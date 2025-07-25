import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import TradeBrowser from './components/TradeBrowser';
import MembersBrowser from './components/MembersBrowser';
import DataQuality from './components/DataQuality';

// Placeholder components for routes we haven't implemented yet
const Analytics = () => (
  <div className="card p-6">
    <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">Analytics</h2>
    <p className="text-gray-600 dark:text-gray-400">Advanced analytics and visualizations coming soon...</p>
  </div>
);

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/trades" element={<TradeBrowser />} />
            <Route path="/members" element={<MembersBrowser />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/data-quality" element={<DataQuality />} />
          </Routes>
        </Layout>
      </Router>
    </ThemeProvider>
  );
};

export default App;
