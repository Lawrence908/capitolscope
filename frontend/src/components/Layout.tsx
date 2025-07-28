import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  ChartBarIcon,
  UserGroupIcon,
  DocumentMagnifyingGlassIcon,
  CogIcon,
  HomeIcon,
  UserCircleIcon,
  ArrowRightOnRectangleIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import DarkModeToggle from './DarkModeToggle';
import { useAuth } from '../contexts/AuthContext';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

  // Check if user has premium subscription (handle both lowercase and uppercase)
  const subscriptionTier = user?.subscription_tier?.toLowerCase();
  const isPremium = subscriptionTier === 'premium' || subscriptionTier === 'enterprise';
  const isPro = subscriptionTier === 'pro' || isPremium;
  const isFree = subscriptionTier === 'free' || !subscriptionTier;
  
  // Debug logging
  console.log('User data:', {
    user: user,
    subscription_tier: user?.subscription_tier,
    subscriptionTier,
    isPremium,
    isPro,
    isFree
  });

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
    { name: 'Trade Browser', href: '/trades', icon: DocumentMagnifyingGlassIcon },
    { name: 'Members', href: '/members', icon: UserGroupIcon },
    { name: 'Analytics', href: '/analytics', icon: ChartBarIcon },
    { name: 'Data Quality', href: '/data-quality', icon: CogIcon },
  ];

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  const handleLogout = () => {
    logout();
    setShowUserMenu(false);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-gray-800 shadow-lg transition-colors duration-200">
        <div className="flex h-16 items-center justify-center border-b border-gray-200 dark:border-gray-700">
          <h1 className="text-xl font-bold text-primary-700 dark:text-primary-400">CapitolScope</h1>
        </div>
        
        <nav className="mt-8 px-4">
          <ul className="space-y-2">
            {navigation.map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.name}>
                  <Link
                    to={item.href}
                    className={`flex items-center px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                      isActive(item.href)
                        ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                        : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-gray-100'
                    }`}
                  >
                    <Icon className="mr-3 h-5 w-5" />
                    {item.name}
                  </Link>
                </li>
              );
            })}
          </ul>
          
          {/* Premium Upgrade Section for Free Users */}
          {isFree && (
            <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
              <div className="bg-gradient-to-r from-yellow-400 to-orange-500 p-4 rounded-lg shadow-lg">
                <div className="flex items-center mb-2">
                  <SparklesIcon className="h-5 w-5 text-white mr-2" />
                  <span className="text-white text-sm font-semibold">Upgrade to Pro</span>
                </div>
                <p className="text-yellow-100 text-xs mb-3">
                  Unlock trade alerts, analytics, and more
                </p>
                <Link
                  to="/premium"
                  className="block w-full bg-white text-orange-600 text-xs font-semibold py-2 px-3 rounded text-center hover:bg-gray-50 transition-colors duration-200"
                >
                  View Plans
                </Link>
              </div>
            </div>
          )}
        </nav>
      </div>

      {/* Main content */}
      <div className="ml-64">
        {/* Header */}
        <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 transition-colors duration-200">
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                  {navigation.find(item => isActive(item.href))?.name || 'CapitolScope'}
                </h1>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Congressional trading transparency platform
                </p>
              </div>
              
              <div className="flex items-center space-x-4">
                {/* Premium Upgrade Button for Free Users */}
                {isFree && (
                  <Link
                    to="/premium"
                    className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-yellow-400 to-orange-500 hover:from-yellow-500 hover:to-orange-600 text-white text-sm font-medium rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105"
                  >
                    <SparklesIcon className="h-4 w-4 mr-2" />
                    Upgrade to Pro
                  </Link>
                )}
                
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Last updated: {new Date().toLocaleDateString()}
                </div>
                <DarkModeToggle />
                
                {/* User Menu */}
                <div className="relative">
                  <button
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className="flex items-center space-x-2 text-sm text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
                  >
                    <UserCircleIcon className="h-6 w-6" />
                    <span className="hidden md:block">
                      {user?.display_name || user?.email || 'User'}
                    </span>
                  </button>
                  
                  {showUserMenu && (
                    <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg py-1 z-50 border border-gray-200 dark:border-gray-700">
                      <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {user?.display_name || user?.email}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {isFree ? 'Free Plan' : isPremium ? 'Premium Plan' : isPro ? 'Pro Plan' : 'Enterprise Plan'}
                        </p>
                      </div>
                      
                      <Link
                        to="/profile"
                        className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                        onClick={() => setShowUserMenu(false)}
                      >
                        Profile Settings
                      </Link>
                      
                      <button
                        onClick={handleLogout}
                        className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                      >
                        <div className="flex items-center">
                          <ArrowRightOnRectangleIcon className="h-4 w-4 mr-2" />
                          Sign out
                        </div>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-6">
          {children}
        </main>
      </div>
      
      {/* Overlay to close user menu when clicking outside */}
      {showUserMenu && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowUserMenu(false)}
        />
      )}
    </div>
  );
};

export default Layout; 