import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { AuthProvider } from './contexts/AuthContext';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import TradeBrowser from './components/TradeBrowser';
import MembersBrowser from './components/MembersBrowser';
import MemberProfile from './components/MemberProfile';
import DataQuality from './components/DataQuality';
import LoginPage from './components/LoginPage';
import RegisterPage from './components/RegisterPage';
import ForgotPasswordPage from './components/ForgotPasswordPage';
import ResetPasswordPage from './components/ResetPasswordPage';
import LandingPage from './components/LandingPage';
import ProfileSettings from './components/ProfileSettings';
import PremiumSignup from './components/PremiumSignup';
import ProtectedRoute from './components/ProtectedRoute';

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
      <AuthProvider>
        <Router>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={
              <ProtectedRoute requireAuth={false}>
                <LoginPage />
              </ProtectedRoute>
            } />
            <Route path="/register" element={
              <ProtectedRoute requireAuth={false}>
                <RegisterPage />
              </ProtectedRoute>
            } />
            <Route path="/forgot-password" element={
              <ProtectedRoute requireAuth={false}>
                <ForgotPasswordPage />
              </ProtectedRoute>
            } />
            <Route path="/reset-password" element={
              <ProtectedRoute requireAuth={false}>
                <ResetPasswordPage />
              </ProtectedRoute>
            } />
            
            {/* Protected routes */}
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <Layout>
                  <Dashboard />
                </Layout>
              </ProtectedRoute>
            } />
            <Route path="/trades" element={
              <ProtectedRoute>
                <Layout>
                  <TradeBrowser />
                </Layout>
              </ProtectedRoute>
            } />
            <Route path="/members" element={
              <ProtectedRoute>
                <Layout>
                  <MembersBrowser />
                </Layout>
              </ProtectedRoute>
            } />
            <Route path="/members/:id" element={
              <ProtectedRoute>
                <Layout>
                  <MemberProfile />
                </Layout>
              </ProtectedRoute>
            } />
            <Route path="/analytics" element={
              <ProtectedRoute>
                <Layout>
                  <Analytics />
                </Layout>
              </ProtectedRoute>
            } />
            <Route path="/data-quality" element={
              <ProtectedRoute>
                <Layout>
                  <DataQuality />
                </Layout>
              </ProtectedRoute>
            } />
            <Route path="/profile" element={
              <ProtectedRoute>
                <Layout>
                  <ProfileSettings />
                </Layout>
              </ProtectedRoute>
            } />
            <Route path="/premium" element={
              <ProtectedRoute>
                <PremiumSignup />
              </ProtectedRoute>
            } />
            
            {/* Catch all route - redirect to landing page */}
            <Route path="*" element={<LandingPage />} />
          </Routes>
        </Router>
      </AuthProvider>
    </ThemeProvider>
  );
};

export default App;
