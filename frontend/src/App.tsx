import React, { Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { AuthProvider } from './contexts/AuthContext';
import { ErrorBoundary } from './components/ErrorBoundary';
import Layout from './components/Layout';
import LoginPage from './components/LoginPage';
import RegisterPage from './components/RegisterPage';
import ForgotPasswordPage from './components/ForgotPasswordPage';
import ResetPasswordPage from './components/ResetPasswordPage';
import PublicDashboard from './components/PublicDashboard';
import ProtectedRoute from './components/ProtectedRoute';
import PremiumRoute from './components/PremiumRoute';
import PrivacyPolicy from './components/PrivacyPolicy';
import TermsOfService from './components/TermsOfService';

// Lazy load components to reduce initial bundle size
const Dashboard = React.lazy(() => import('./components/Dashboard'));
const TradeBrowser = React.lazy(() => import('./components/TradeBrowser'));
const MembersBrowser = React.lazy(() => import('./components/MembersBrowser'));
const MemberProfile = React.lazy(() => import('./components/MemberProfile'));
const DataQuality = React.lazy(() => import('./components/DataQuality'));
const Analytics = React.lazy(() => import('./components/Analytics'));
const ProfileSettings = React.lazy(() => import('./components/ProfileSettings'));
const PremiumSignup = React.lazy(() => import('./components/PremiumSignup'));
const AlertDashboard = React.lazy(() => import('./pages/alerts/AlertDashboard'));
const ScrutinyCommand = React.lazy(() => import('./pages/scrutiny/ScrutinyCommand'));
const MirrorPage = React.lazy(() => import('./pages/mirror/MirrorPage'));
const AssetPage = React.lazy(() => import('./pages/asset/AssetPage'));
const ComparePage = React.lazy(() => import('./pages/compare/ComparePage'));
const TradePage = React.lazy(() => import('./pages/trade/TradePage'));
const LateFilersPage = React.lazy(() => import('./pages/late/LateFilersPage'));
const SocialQueuePage = React.lazy(() => import('./pages/admin/SocialQueuePage'));

// Loading component for Suspense fallback
const LoadingSpinner = () => (
  <div className="flex min-h-[16rem] items-center justify-center bg-surface">
    <div className="h-8 w-8 animate-spin rounded-full border-2 border-line border-t-accent" />
  </div>
);

const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <Router>
            <Routes>
            {/* Public routes */}
            <Route path="/" element={
              <Layout>
                <PublicDashboard />
              </Layout>
            } />
            <Route path="/landing" element={<Navigate to="/" replace />} />
            <Route path="/privacy" element={<PrivacyPolicy />} />
            <Route path="/terms" element={<TermsOfService />} />
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
            
            {/* Protected routes with lazy loading */}
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<LoadingSpinner />}>
                    <Dashboard />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            } />
            <Route path="/trades" element={
                <Layout>
                  <Suspense fallback={<LoadingSpinner />}>
                    <TradeBrowser />
                  </Suspense>
                </Layout>
            } />
            <Route path="/transactions" element={
                <Layout>
                  <Suspense fallback={<LoadingSpinner />}>
                    <TradeBrowser />
                  </Suspense>
                </Layout>
            } />
            <Route path="/assets/:ticker" element={
                <Layout>
                  <Suspense fallback={<LoadingSpinner />}>
                    <AssetPage />
                  </Suspense>
                </Layout>
            } />
            <Route path="/members" element={
                <Layout>
                  <Suspense fallback={<LoadingSpinner />}>
                    <MembersBrowser />
                  </Suspense>
                </Layout>
            } />
            <Route path="/members/:id" element={
                <Layout>
                  <Suspense fallback={<LoadingSpinner />}>
                    <MemberProfile />
                  </Suspense>
                </Layout>
            } />
            <Route path="/analytics" element={
              <ProtectedRoute>
                <PremiumRoute requiredTier="pro">
                  <Layout>
                    <Suspense fallback={<LoadingSpinner />}>
                      <Analytics />
                    </Suspense>
                  </Layout>
                </PremiumRoute>
              </ProtectedRoute>
            } />
            {/* Scrutiny command center — now inside the shared shell */}
            <Route path="/scrutiny" element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<LoadingSpinner />}>
                    <ScrutinyCommand />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            } />
            <Route path="/mirror" element={
              <ProtectedRoute>
                <PremiumRoute requiredTier="pro">
                  <Layout>
                    <Suspense fallback={<LoadingSpinner />}>
                      <MirrorPage />
                    </Suspense>
                  </Layout>
                </PremiumRoute>
              </ProtectedRoute>
            } />
            <Route path="/compare" element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<LoadingSpinner />}>
                    <ComparePage />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            } />
            <Route path="/data-quality" element={
              <ProtectedRoute>
                <PremiumRoute requiredTier="pro">
                  <Layout>
                    <Suspense fallback={<LoadingSpinner />}>
                      <DataQuality />
                    </Suspense>
                  </Layout>
                </PremiumRoute>
              </ProtectedRoute>
            } />
            <Route path="/profile" element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<LoadingSpinner />}>
                    <ProfileSettings />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            } />
            <Route path="/premium" element={
              <ProtectedRoute>
                <Suspense fallback={<LoadingSpinner />}>
                  <PremiumSignup />
                </Suspense>
              </ProtectedRoute>
            } />
            <Route path="/alerts" element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<LoadingSpinner />}>
                    <AlertDashboard />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            } />
            
            {/* Admin: X post review queue (API enforces the admin role) */}
            <Route path="/admin/social" element={
              <ProtectedRoute>
                <Layout>
                  <Suspense fallback={<LoadingSpinner />}>
                    <SocialQueuePage />
                  </Suspense>
                </Layout>
              </ProtectedRoute>
            } />

            {/* Public data pages: open to everyone (shareable from X). Tools stay gated. */}
            <Route path="/t/:tradeId" element={
              <Layout>
                <Suspense fallback={<LoadingSpinner />}>
                  <TradePage />
                </Suspense>
              </Layout>
            } />
            <Route path="/late" element={
              <Layout>
                <Suspense fallback={<LoadingSpinner />}>
                  <LateFilersPage />
                </Suspense>
              </Layout>
            } />

            {/* Catch all route: redirect to the homepage */}
            <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Router>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
};

export default App;
