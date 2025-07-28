import React from 'react';
import { Link } from 'react-router-dom';

const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <div className="h-8 w-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h1 className="ml-3 text-xl font-bold text-gray-900 dark:text-white">CapitolScope</h1>
            </div>
            <div className="flex items-center space-x-4">
              <Link
                to="/login"
                className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
              >
                Sign in
              </Link>
              <Link
                to="/register"
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="text-center">
            <h1 className="text-4xl font-extrabold text-gray-900 dark:text-white sm:text-5xl md:text-6xl">
              Congressional Trading
              <span className="text-blue-600"> Transparency</span>
            </h1>
            <p className="mt-6 text-xl text-gray-600 dark:text-gray-400 max-w-3xl mx-auto">
              Track and analyze congressional trading activity in real-time. Discover patterns, 
              monitor portfolios, and stay informed about the financial activities of your elected officials.
            </p>
            <div className="mt-10 flex justify-center space-x-4">
              <Link
                to="/register"
                className="bg-blue-600 text-white px-8 py-3 rounded-md text-lg font-medium hover:bg-blue-700 transition-colors"
              >
                Start Exploring
              </Link>
              <Link
                to="/login"
                className="border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 px-8 py-3 rounded-md text-lg font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                Sign In
              </Link>
            </div>
          </div>

          {/* Features */}
          <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="mx-auto h-12 w-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <svg className="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">Real-time Data</h3>
              <p className="mt-2 text-gray-600 dark:text-gray-400">
                Access up-to-date congressional trading information with comprehensive filtering and search capabilities.
              </p>
            </div>

            <div className="text-center">
              <div className="mx-auto h-12 w-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <svg className="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">Member Profiles</h3>
              <p className="mt-2 text-gray-600 dark:text-gray-400">
                Detailed profiles of congress members with their trading history, portfolio analysis, and performance metrics.
              </p>
            </div>

            <div className="text-center">
              <div className="mx-auto h-12 w-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <svg className="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">Advanced Analytics</h3>
              <p className="mt-2 text-gray-600 dark:text-gray-400">
                Powerful analytics tools to identify patterns, trends, and correlations in congressional trading activity.
              </p>
            </div>
          </div>

          {/* Beta Notice */}
          <div className="mt-16 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-8">
            <div className="text-center">
              <h3 className="text-lg font-medium text-blue-800 dark:text-blue-200">
                🚀 Currently in Beta
              </h3>
              <p className="mt-2 text-blue-700 dark:text-blue-300">
                CapitolScope is currently in beta testing. Sign up now to get early access and help us improve the platform.
              </p>
              <div className="mt-4">
                <Link
                  to="/register"
                  className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 dark:text-blue-200 dark:bg-blue-800 dark:hover:bg-blue-700 transition-colors"
                >
                  Join Beta
                </Link>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default LandingPage; 