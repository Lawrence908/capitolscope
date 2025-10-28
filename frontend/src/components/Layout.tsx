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
  Bars3Icon,
  XMarkIcon,
  StarIcon,
  BellIcon,
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
  const [showMobileMenu, setShowMobileMenu] = useState(false);

  // Check if user has premium subscription (handle both lowercase and uppercase)
  const subscriptionTier = user?.subscription_tier?.toLowerCase();
  const isPremium = subscriptionTier === 'premium' || subscriptionTier === 'enterprise';
  const isPro = subscriptionTier === 'pro' || isPremium;
  const isFree = subscriptionTier === 'free' || !subscriptionTier;
  
  // Helper function to check if user can access a specific tier
  const canAccessTier = (requiredTier: string) => {
    switch (requiredTier) {
      case 'free':
        return true;
      case 'pro':
        return isPro;
      case 'premium':
        return isPremium;
      case 'enterprise':
        return subscriptionTier === 'enterprise';
      default:
        return false;
    }
  };
  
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
    { name: 'Dashboard', href: '/dashboard', icon: HomeIcon, tier: 'free' },
    { name: 'Trade Browser', href: '/trades', icon: DocumentMagnifyingGlassIcon, tier: 'free' },
    { name: 'Members', href: '/members', icon: UserGroupIcon, tier: 'free' },
    { name: 'Trade Alerts', href: '/alerts', icon: BellIcon, tier: 'free' },
    { name: 'Analytics', href: '/analytics', icon: ChartBarIcon, tier: 'pro' },
    { name: 'Data Quality', href: '/data-quality', icon: CogIcon, tier: 'free' },
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
    setShowMobileMenu(false);
  };

  const closeMobileMenu = () => {
    setShowMobileMenu(false);
  };

  return (
    <div className="min-h-screen bg-bg-light-primary dark:bg-bg-primary text-neutral-900 dark:text-neutral-100 transition-colors duration-300 flex flex-col">
      {/* Mobile menu overlay */}
      {showMobileMenu && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="fixed inset-0 bg-black bg-opacity-50" onClick={closeMobileMenu} />
          <div className="fixed inset-y-0 left-0 w-64 sidebar shadow-lg transition-colors duration-300">
            <div className="flex h-16 items-center justify-between px-4 border-b border-neutral-200 dark:border-neutral-700">
              <div className="flex items-center space-x-3">
                <img 
                  src="/favicon-64x64.png" 
                  alt="CapitolScope Logo" 
                  className="h-8 w-8 rounded-lg"
                  loading="lazy"
                  width="32"
                  height="32"
                />
                <h1 className="text-lg font-bold text-primary-600 dark:text-primary-400">CapitolScope</h1>
              </div>
              <button
                onClick={closeMobileMenu}
                className="text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>
            
            <nav className="mt-4 px-4">
              <ul className="space-y-2">
                {navigation.map((item) => {
                  const Icon = item.icon;
                  const canAccess = canAccessTier(item.tier);
                  return (
                    <li key={item.name}>
                      <Link
                        to={item.href}
                        onClick={closeMobileMenu}
                        className={`flex items-center justify-between px-4 py-3 text-sm font-medium rounded-lg transition-all ${
                          isActive(item.href)
                            ? 'nav-link-active'
                            : canAccess 
                              ? 'nav-link hover:bg-neutral-100 dark:hover:bg-neutral-800'
                              : 'text-neutral-400 dark:text-neutral-500 hover:text-neutral-500 dark:hover:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 opacity-60'
                        }`}
                      >
                        <div className="flex items-center">
                          <Icon className="mr-3 h-5 w-5" />
                          {item.name}
                        </div>
                        {!canAccess && item.tier !== 'free' && (
                          <div className="flex items-center text-xs text-warning bg-yellow-50 dark:bg-yellow-900/20 px-2 py-1 rounded-full">
                            <StarIcon className="h-3 w-3 mr-1" />
                            {item.tier === 'pro' ? 'Pro' : item.tier === 'premium' ? 'Premium' : 'Enterprise'}
                          </div>
                        )}
                      </Link>
                    </li>
                  );
                })}
              </ul>
              
              {/* Premium Upgrade Section for Free Users */}
              {isFree && (
                <div className="mt-6 pt-4 border-t border-neutral-200 dark:border-neutral-700">
                  <div className="card-elevated p-4">
                    <div className="flex items-center mb-2">
                      <SparklesIcon className="h-5 w-5 text-primary-600 dark:text-primary-400 mr-2" />
                      <span className="text-primary-600 dark:text-primary-400 text-sm font-semibold">Upgrade to Pro</span>
                    </div>
                    <p className="text-muted text-xs mb-3">
                      Unlock trade alerts, analytics, and more
                    </p>
                    <Link
                      to="/premium"
                      onClick={closeMobileMenu}
                      className="btn-primary text-xs py-2 px-3 text-center block w-full"
                    >
                      View Plans
                    </Link>
                  </div>
                </div>
              )}
            </nav>
          </div>
        </div>
      )}

      {/* Desktop Sidebar */}
      <div className="hidden lg:block fixed inset-y-0 left-0 z-50 w-64 sidebar shadow-lg transition-colors duration-300">
        <div className="flex h-16 items-center justify-center border-b border-neutral-200 dark:border-neutral-700">
          <div className="flex items-center space-x-3">
            <img 
              src="/favicon-64x64.png" 
              alt="CapitolScope Logo" 
              className="h-10 w-10 rounded-lg"
              loading="lazy"
              width="40"
              height="40"
            />
            <h1 className="text-xl font-bold text-primary-600 dark:text-primary-400">CapitolScope</h1>
          </div>
        </div>
        
        <nav className="mt-8 px-4">
          <ul className="space-y-2">
            {navigation.map((item) => {
              const Icon = item.icon;
              const canAccess = canAccessTier(item.tier);
              return (
                <li key={item.name}>
                  <Link
                    to={item.href}
                    className={`flex items-center justify-between px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                      isActive(item.href)
                        ? 'nav-link-active'
                        : canAccess 
                          ? 'nav-link hover:bg-neutral-100 dark:hover:bg-neutral-800'
                          : 'text-neutral-400 dark:text-neutral-500 hover:text-neutral-500 dark:hover:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 opacity-60'
                    }`}
                  >
                    <div className="flex items-center">
                      <Icon className="mr-3 h-5 w-5" />
                      {item.name}
                    </div>
                    {!canAccess && item.tier !== 'free' && (
                      <div className="flex items-center text-xs text-warning bg-yellow-50 dark:bg-yellow-900/20 px-2 py-1 rounded-full">
                        <StarIcon className="h-3 w-3 mr-1" />
                        {item.tier === 'pro' ? 'Pro' : item.tier === 'premium' ? 'Premium' : 'Enterprise'}
                      </div>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
          
          {/* Premium Upgrade Section for Free Users */}
          {isFree && (
            <div className="mt-8 pt-6 border-t border-neutral-200 dark:border-neutral-700">
              <div className="card-elevated p-4">
                <div className="flex items-center mb-2">
                  <SparklesIcon className="h-5 w-5 text-primary-600 dark:text-primary-400 mr-2" />
                  <span className="text-primary-600 dark:text-primary-400 text-sm font-semibold">Upgrade to Pro</span>
                </div>
                <p className="text-muted text-xs mb-3">
                  Unlock trade alerts, analytics, and more
                </p>
                <Link
                  to="/premium"
                  className="btn-primary text-xs py-2 px-3 text-center block w-full"
                >
                  View Plans
                </Link>
              </div>
            </div>
          )}
        </nav>
      </div>

      {/* Main content */}
      <div className="lg:ml-64 flex min-h-screen flex-col">
        {/* Header */}
        <header className="header shadow-sm transition-colors duration-300">
          <div className="px-4 lg:px-6 py-4">
            <div className="flex items-center justify-between">
              {/* Mobile menu button and title */}
              <div className="flex items-center space-x-4">
                <button
                  onClick={() => setShowMobileMenu(true)}
                  className="lg:hidden text-neutral-500 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100"
                >
                  <Bars3Icon className="h-6 w-6" />
                </button>
                <div>
                  <h1 className="text-xl lg:text-2xl font-semibold text-heading">
                    {navigation.find(item => isActive(item.href))?.name || 'CapitolScope'}
                  </h1>
                  <p className="text-xs lg:text-sm text-muted mt-1 hidden sm:block">
                    Congressional trading transparency platform
                  </p>
                </div>
              </div>
              
              <div className="flex items-center space-x-2 lg:space-x-4">
                {/* Premium Upgrade Button for Free Users */}
                {isFree && (
                  <Link
                    to="/premium"
                    className="hidden sm:inline-flex items-center px-3 lg:px-4 py-2 btn-primary text-xs lg:text-sm font-medium transition-all duration-200"
                  >
                    <SparklesIcon className="h-4 w-4 mr-1 lg:mr-2" />
                    <span className="hidden lg:inline">Upgrade to Pro</span>
                    <span className="lg:hidden">Pro</span>
                  </Link>
                )}
                
                <div className="hidden lg:block text-sm text-muted">
                  Last updated: {new Date().toLocaleDateString()}
                </div>
                <DarkModeToggle />
                
                {/* User Menu */}
                <div className="relative">
                  <button
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className="flex items-center space-x-2 text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 transition-colors"
                  >
                    <UserCircleIcon className="h-6 w-6" />
                    <span className="hidden md:block">
                      {user?.computed_display_name || user?.email || 'User'}
                    </span>
                  </button>
                  
                  {showUserMenu && (
                    <div className="absolute right-0 mt-2 w-48 card-elevated shadow-lg py-1 z-50">
                      <div className="px-4 py-2 border-b border-neutral-200 dark:border-neutral-700">
                        <p className="text-sm font-medium text-heading">
                          {user?.computed_display_name || user?.email}
                        </p>
                        <p className="text-xs text-muted">
                          {isFree ? 'Free Plan' : isPremium ? 'Premium Plan' : isPro ? 'Pro Plan' : 'Enterprise Plan'}
                        </p>
                      </div>
                      
                      <Link
                        to="/profile"
                        className="block px-4 py-2 text-sm text-body hover:bg-neutral-100 dark:hover:bg-neutral-800"
                        onClick={() => setShowUserMenu(false)}
                      >
                        Profile Settings
                      </Link>
                      
                      <button
                        onClick={handleLogout}
                        className="block w-full text-left px-4 py-2 text-sm text-body hover:bg-neutral-100 dark:hover:bg-neutral-800"
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
        <main className="content-area p-4 lg:p-6 flex-grow">
          {children}
        </main>
        
        {/* Footer */}
        <footer className="sidebar border-t border-neutral-200 dark:border-neutral-700 mt-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="flex flex-col md:flex-row justify-between items-center">
              <div className="flex items-center mb-4 md:mb-0">
                <img 
                  src="/capitol-scope-logo.png" 
                  alt="CapitolScope Logo" 
                  className="h-8 w-8 rounded-lg"
                  loading="lazy"
                  width="32"
                  height="32"
                />
                <span className="ml-3 text-sm text-muted">
                  © 2025 CapitolScope. All rights reserved.
                </span>
              </div>
              
              <div className="flex items-center space-x-6">
                <Link
                  to="/privacy"
                  className="text-sm text-muted hover:text-neutral-700 dark:hover:text-neutral-300 transition-colors"
                >
                  Privacy Policy
                </Link>
                <Link
                  to="/terms"
                  className="text-sm text-muted hover:text-neutral-700 dark:hover:text-neutral-300 transition-colors"
                >
                  Terms of Service
                </Link>
                <a
                  href="mailto:capitolscope@gmail.com"
                  className="text-sm text-muted hover:text-neutral-700 dark:hover:text-neutral-300 transition-colors"
                >
                  Support
                </a>
              </div>
            </div>
          </div>
        </footer>
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