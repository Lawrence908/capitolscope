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
  Squares2X2Icon,
} from '@heroicons/react/24/outline';
import DarkModeToggle from './DarkModeToggle';
import { Eyebrow } from './ui';
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

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: HomeIcon, tier: 'free' },
    { name: 'Trade Browser', href: '/trades', icon: DocumentMagnifyingGlassIcon, tier: 'free' },
    { name: 'Members', href: '/members', icon: UserGroupIcon, tier: 'free' },
    { name: 'Scrutiny', href: '/scrutiny', icon: SparklesIcon, tier: 'free' },
    { name: 'Trade Alerts', href: '/alerts', icon: BellIcon, tier: 'free' },
    { name: 'Analytics', href: '/analytics', icon: ChartBarIcon, tier: 'pro' },
    { name: 'Mirror', href: '/mirror', icon: Squares2X2Icon, tier: 'pro' },
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

  const Wordmark = ({ size = 'lg' }: { size?: 'sm' | 'lg' }) => (
    <div className="flex items-center space-x-3">
      <img
        src="/favicon-64x64.png"
        alt="CapitolScope Logo"
        className={`${size === 'lg' ? 'h-9 w-9' : 'h-8 w-8'} rounded-md`}
        loading="lazy"
        width={size === 'lg' ? 36 : 32}
        height={size === 'lg' ? 36 : 32}
      />
      <span className="font-display text-lg font-medium tracking-tight text-content">
        Capitol<span className="text-accent">Scope</span>
      </span>
    </div>
  );

  const NavList = ({ onNavigate }: { onNavigate?: () => void }) => (
    <ul className="space-y-1">
      {navigation.map((item) => {
        const Icon = item.icon;
        const canAccess = canAccessTier(item.tier);
        const active = isActive(item.href);
        return (
          <li key={item.name}>
            <Link
              to={item.href}
              onClick={onNavigate}
              className={`flex items-center justify-between rounded-md px-4 py-2.5 font-ui text-sm font-medium transition-colors ${
                active
                  ? 'nav-link-active'
                  : canAccess
                    ? 'nav-link hover:bg-surface-inset'
                    : 'nav-link opacity-60 hover:bg-surface-inset'
              }`}
            >
              <div className="flex items-center">
                <Icon className="mr-3 h-5 w-5" />
                {item.name}
              </div>
              {!canAccess && item.tier !== 'free' && (
                <span className="flex items-center rounded-sm bg-surface-inset px-1.5 py-0.5 font-data text-[10px] uppercase tracking-[0.1em] text-accent-2">
                  <StarIcon className="mr-1 h-3 w-3" />
                  {item.tier === 'pro' ? 'Pro' : item.tier === 'premium' ? 'Premium' : 'Enterprise'}
                </span>
              )}
            </Link>
          </li>
        );
      })}
    </ul>
  );

  const UpgradeCard = ({ onNavigate }: { onNavigate?: () => void }) => (
    <div className="card p-4">
      <div className="mb-2 flex items-center">
        <SparklesIcon className="mr-2 h-5 w-5 text-accent" />
        <span className="font-display text-sm font-medium text-content">Upgrade to Pro</span>
      </div>
      <p className="mb-3 font-ui text-xs text-content-faint">
        Unlock trade alerts, analytics, and more
      </p>
      <Link to="/premium" onClick={onNavigate} className="btn-primary block w-full px-3 py-2 text-center text-xs">
        View Plans
      </Link>
    </div>
  );

  const activeName = navigation.find((item) => isActive(item.href))?.name || 'CapitolScope';

  return (
    <div className="flex min-h-screen flex-col bg-surface text-content transition-colors duration-300">
      {/* Mobile menu overlay */}
      {showMobileMenu && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="fixed inset-0 bg-black/60" onClick={closeMobileMenu} />
          <div className="sidebar fixed inset-y-0 left-0 w-64 border-r shadow-lg">
            <div className="flex h-16 items-center justify-between border-b border-line px-4">
              <Wordmark size="sm" />
              <button
                onClick={closeMobileMenu}
                className="text-content-faint transition-colors hover:text-content"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>

            <nav className="mt-4 px-3">
              <NavList onNavigate={closeMobileMenu} />
              {isFree && (
                <div className="mt-6 border-t border-line pt-4">
                  <UpgradeCard onNavigate={closeMobileMenu} />
                </div>
              )}
            </nav>
          </div>
        </div>
      )}

      {/* Desktop Sidebar */}
      <div className="sidebar fixed inset-y-0 left-0 z-50 hidden w-64 border-r lg:block">
        <div className="flex h-16 items-center border-b border-line px-5">
          <Wordmark />
        </div>

        <nav className="mt-6 px-3">
          <NavList />
          {isFree && (
            <div className="mt-8 border-t border-line pt-6">
              <UpgradeCard />
            </div>
          )}
        </nav>
      </div>

      {/* Main content */}
      <div className="flex min-h-screen flex-col lg:ml-64">
        {/* Header */}
        <header className="header border-b">
          <div className="px-4 py-4 lg:px-6">
            <div className="flex items-center justify-between">
              {/* Mobile menu button and title */}
              <div className="flex items-center space-x-4">
                <button
                  onClick={() => setShowMobileMenu(true)}
                  className="text-content-faint transition-colors hover:text-content lg:hidden"
                >
                  <Bars3Icon className="h-6 w-6" />
                </button>
                <div>
                  <Eyebrow>CapitolScope · Oversight</Eyebrow>
                  <h1 className="mt-0.5 font-display text-2xl font-medium leading-tight text-content">
                    {activeName}
                  </h1>
                </div>
              </div>

              <div className="flex items-center space-x-2 lg:space-x-4">
                {/* Premium Upgrade Button for Free Users */}
                {isFree && (
                  <Link
                    to="/premium"
                    className="btn-primary hidden items-center px-3 py-2 text-xs sm:inline-flex lg:px-4 lg:text-sm"
                  >
                    <SparklesIcon className="mr-1 h-4 w-4 lg:mr-2" />
                    <span className="hidden lg:inline">Upgrade to Pro</span>
                    <span className="lg:hidden">Pro</span>
                  </Link>
                )}

                <div className="hidden font-data text-[11px] uppercase tracking-[0.1em] text-content-faint lg:block">
                  Updated {new Date().toLocaleDateString()}
                </div>
                <DarkModeToggle />

                {/* User Menu */}
                <div className="relative">
                  <button
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className="flex items-center space-x-2 font-ui text-sm text-content-muted transition-colors hover:text-content"
                  >
                    <UserCircleIcon className="h-6 w-6" />
                    <span className="hidden md:block">
                      {user?.computed_display_name || user?.email || 'User'}
                    </span>
                  </button>

                  {showUserMenu && (
                    <div className="card-elevated absolute right-0 z-50 mt-2 w-52 py-1 shadow-lg">
                      <div className="border-b border-line px-4 py-2">
                        <p className="font-ui text-sm font-medium text-content">
                          {user?.computed_display_name || user?.email}
                        </p>
                        <p className="font-data text-[11px] uppercase tracking-[0.1em] text-content-faint">
                          {isFree ? 'Free Plan' : isPremium ? 'Premium Plan' : isPro ? 'Pro Plan' : 'Enterprise Plan'}
                        </p>
                      </div>

                      <Link
                        to="/profile"
                        className="block px-4 py-2 font-ui text-sm text-content-muted transition-colors hover:bg-surface-inset hover:text-content"
                        onClick={() => setShowUserMenu(false)}
                      >
                        Profile Settings
                      </Link>

                      <button
                        onClick={handleLogout}
                        className="block w-full px-4 py-2 text-left font-ui text-sm text-content-muted transition-colors hover:bg-surface-inset hover:text-content"
                      >
                        <div className="flex items-center">
                          <ArrowRightOnRectangleIcon className="mr-2 h-4 w-4" />
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
        <main className="content-area flex-grow p-4 lg:p-6">{children}</main>

        {/* Footer */}
        <footer className="sidebar mt-auto border-t">
          <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
            <div className="flex flex-col items-center justify-between md:flex-row">
              <div className="mb-4 flex items-center md:mb-0">
                <img
                  src="/capitol-scope-logo.png"
                  alt="CapitolScope Logo"
                  className="h-8 w-8 rounded-md"
                  loading="lazy"
                  width="32"
                  height="32"
                />
                <span className="ml-3 font-ui text-sm text-content-faint">
                  © {new Date().getFullYear()} CapitolScope. All rights reserved.
                </span>
              </div>

              <div className="flex items-center space-x-6">
                <Link to="/privacy" className="font-ui text-sm text-content-faint transition-colors hover:text-content">
                  Privacy Policy
                </Link>
                <Link to="/terms" className="font-ui text-sm text-content-faint transition-colors hover:text-content">
                  Terms of Service
                </Link>
                <a
                  href="mailto:capitolscope@gmail.com"
                  className="font-ui text-sm text-content-faint transition-colors hover:text-content"
                >
                  Support
                </a>
              </div>
            </div>
          </div>
        </footer>
      </div>

      {/* Overlay to close user menu when clicking outside */}
      {showUserMenu && <div className="fixed inset-0 z-40" onClick={() => setShowUserMenu(false)} />}
    </div>
  );
};

export default Layout;
