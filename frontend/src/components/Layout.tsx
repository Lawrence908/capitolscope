import React, { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Bars3Icon, ChevronDownIcon, XMarkIcon } from '@heroicons/react/24/outline';
import DarkModeToggle from './DarkModeToggle';
import NotificationBell from './notifications/NotificationBell';
import { HubFooter } from './HubFooter';
import { useAuth } from '../contexts/AuthContext';
import { usePublicHome } from '../hooks/usePublicHome';
import { affiliation, fmtAmountRange } from './ui';
import type { PublicTrade } from '../types/public';

interface LayoutProps {
  children: React.ReactNode;
}

type Tier = 'free' | 'pro' | 'premium' | 'enterprise';

// Public data pages: open to everyone.
const PRIMARY_NAV: { name: string; href: string; match: string[] }[] = [
  { name: 'Latest', href: '/', match: ['/'] },
  { name: 'Members', href: '/members', match: ['/members'] },
  { name: 'Trades', href: '/trades', match: ['/trades', '/transactions', '/t/', '/assets'] },
  { name: 'Late filers', href: '/late', match: ['/late'] },
];

// Signed-in tools (tier gating unchanged from the previous sidebar).
const TOOLS_NAV: { name: string; href: string; tier: Tier }[] = [
  { name: 'Dashboard', href: '/dashboard', tier: 'free' },
  { name: 'Analytics', href: '/analytics', tier: 'pro' },
  { name: 'Scrutiny', href: '/scrutiny', tier: 'free' },
  { name: 'Mirror', href: '/mirror', tier: 'pro' },
  { name: 'Compare', href: '/compare', tier: 'free' },
  { name: 'Alerts', href: '/alerts', tier: 'free' },
  { name: 'Data quality', href: '/data-quality', tier: 'free' },
];

const TIER_LABEL: Record<Tier, string> = { free: 'Free', pro: 'Pro', premium: 'Premium', enterprise: 'Enterprise' };

const shortDate = (iso: string | null | undefined): string => {
  if (!iso) return '';
  const d = new Date(`${iso.slice(0, 10)}T00:00:00`);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

const memberTitle = (chamber: string | null | undefined): string => {
  const c = (chamber || '').toLowerCase();
  return c.startsWith('s') ? 'Sen.' : c.startsWith('h') ? 'Rep.' : '';
};

const pastVerb = (type: string | null | undefined): string => {
  const t = (type || '').trim().toUpperCase();
  return t.startsWith('P') ? 'bought' : t.startsWith('S') ? 'sold' : t.startsWith('E') ? 'exchanged' : 'reported';
};

/** One plain sentence for the LATEST strip, e.g.
 * "Rep. Rudy Yakym (R-IN) bought AAPL (Apple Inc.), $15,001 to $50,000, disclosed the same day". */
const latestSentence = (t: PublicTrade): string => {
  const who = [memberTitle(t.member_chamber), t.member_name || 'A member'].filter(Boolean).join(' ');
  const aff = affiliation(t.member_party, t.member_state);
  const ticker = t.ticker?.trim();
  const asset = ticker
    ? t.asset_name && t.asset_name.toUpperCase() !== ticker.toUpperCase()
      ? `${ticker} (${t.asset_name})`
      : ticker
    : t.asset_name || 'an undisclosed asset';
  const raw = fmtAmountRange(t.amount_min, t.amount_max);
  const range = t.amount_min == null && t.amount_max == null ? 'amount not reported' : raw.replace('–', ' to ');
  const days = t.days_to_disclose;
  const timing =
    days == null
      ? ''
      : days === 0
        ? ', disclosed the same day'
        : `, disclosed ${days} day${days === 1 ? '' : 's'} after the trade`;
  return `${who}${aff ? ` (${aff})` : ''} ${pastVerb(t.transaction_type)} ${asset}, ${range}${timing}`;
};

const Wordmark: React.FC = () => (
  <Link to="/" className="flex shrink-0 items-center gap-2.5" aria-label="CapitolScope home">
    <span aria-hidden="true" className="block h-9 w-1.5 bg-accent" />
    <span className="font-display text-[21px] font-extrabold leading-[0.82] tracking-[0.02em] text-slab-on">
      CAPITOL
      <br />
      SCOPE
    </span>
  </Link>
);

/** Newest disclosure as a single sentence under the masthead. */
const LatestStrip: React.FC = () => {
  const { data } = usePublicHome();
  const latest = data?.latest?.[0];
  return (
    <div className="border-b-[3px] border-content bg-surface">
      <div className="mx-auto flex h-12 max-w-[1320px] items-stretch px-4 sm:px-8">
        <span className="flex items-center bg-content px-4 font-display text-xl font-extrabold text-surface">LATEST</span>
        {latest ? (
          <Link
            to={`/t/${latest.id}`}
            className="flex min-w-0 items-center gap-3 px-4 font-ui text-[15px] text-content hover:text-accent"
          >
            <time className="shrink-0 font-bold" dateTime={latest.notification_date ?? undefined}>
              {shortDate(latest.notification_date)}
            </time>
            <span className="truncate">{latestSentence(latest)}</span>
          </Link>
        ) : (
          <span className="flex items-center px-4 font-ui text-[15px] text-content-faint">
            {data ? 'No new disclosures in the last two weeks.' : 'Loading the newest disclosure'}
          </span>
        )}
      </div>
    </div>
  );
};

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showTools, setShowTools] = useState(false);
  const [showMobileMenu, setShowMobileMenu] = useState(false);
  const toolsRef = useRef<HTMLDivElement>(null);
  const userRef = useRef<HTMLDivElement>(null);

  const subscriptionTier = user?.subscription_tier?.toLowerCase();
  const isPremium = subscriptionTier === 'premium' || subscriptionTier === 'enterprise';
  const isPro = subscriptionTier === 'pro' || isPremium;
  const isFree = subscriptionTier === 'free' || !subscriptionTier;

  const canAccessTier = (requiredTier: Tier) => {
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

  const isActive = (prefixes: string[]) =>
    prefixes.some((p) => (p === '/' ? location.pathname === '/' : location.pathname.startsWith(p)));
  const toolActive = TOOLS_NAV.some((t) => location.pathname.startsWith(t.href));

  // Close menus on navigation.
  useEffect(() => {
    setShowMobileMenu(false);
    setShowTools(false);
    setShowUserMenu(false);
  }, [location.pathname]);

  // Close dropdowns on outside click.
  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (toolsRef.current && !toolsRef.current.contains(e.target as Node)) setShowTools(false);
      if (userRef.current && !userRef.current.contains(e.target as Node)) setShowUserMenu(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, []);

  const handleLogout = () => {
    logout();
    setShowUserMenu(false);
    setShowMobileMenu(false);
  };

  const displayName = user?.computed_display_name || user?.email || 'Account';
  const planLabel = isFree ? 'Free plan' : isPremium ? (subscriptionTier === 'enterprise' ? 'Enterprise plan' : 'Premium plan') : 'Pro plan';
  const alertsHref = user ? '/alerts' : '/register';

  const navLinkClass = (active: boolean) =>
    `whitespace-nowrap py-1 font-ui text-[15px] font-medium transition-colors ${
      active ? 'text-slab-on shadow-[0_3px_0_var(--accent)]' : 'text-slab-muted hover:text-slab-on'
    }`;

  const renderToolLink = (item: (typeof TOOLS_NAV)[number], mobile = false) => {
    const ok = canAccessTier(item.tier);
    const active = location.pathname.startsWith(item.href);
    return (
      <Link
        key={item.href}
        to={item.href}
        className={`flex items-center justify-between gap-3 px-4 py-2 font-ui text-sm transition-colors ${
          mobile ? 'text-slab-on hover:underline' : 'text-content hover:bg-surface-inset'
        } ${active ? 'font-bold' : ''} ${ok ? '' : 'opacity-70'}`}
      >
        <span className="flex items-center gap-2">
          {active && <span aria-hidden="true" className="h-3 w-1 bg-accent" />}
          {item.name}
        </span>
        {!ok && (
          <span className="border border-current px-1.5 py-px font-ui text-[10px] font-bold uppercase tracking-[0.08em]">
            {TIER_LABEL[item.tier]}
          </span>
        )}
      </Link>
    );
  };

  return (
    <div className="flex min-h-screen flex-col bg-surface text-content transition-colors duration-300">
      <header className="slab relative z-40">
        <div className="mx-auto flex h-[68px] max-w-[1320px] items-center gap-6 px-4 sm:px-8 lg:gap-9">
          <Wordmark />

          <nav aria-label="Main" className="hidden items-center gap-6 lg:flex">
            {PRIMARY_NAV.map((item) => {
              const active = isActive(item.match);
              return (
                <Link key={item.href} to={item.href} aria-current={active ? 'page' : undefined} className={navLinkClass(active)}>
                  {item.name}
                </Link>
              );
            })}
            {user && (
              <div className="relative" ref={toolsRef}>
                <button
                  type="button"
                  onClick={() => setShowTools((v) => !v)}
                  aria-expanded={showTools}
                  aria-haspopup="menu"
                  className={`flex items-center gap-1 ${navLinkClass(toolActive)}`}
                >
                  Tools
                  <ChevronDownIcon className="h-4 w-4" />
                </button>
                {showTools && (
                  <div role="menu" className="absolute left-0 top-full z-50 mt-3 w-56 border-2 border-content bg-surface-raised py-1 shadow-xl">
                    {TOOLS_NAV.map((item) => renderToolLink(item))}
                    {isFree && (
                      <Link to="/premium" className="mt-1 block border-t border-line px-4 py-2 font-ui text-sm font-semibold text-accent hover:bg-surface-inset">
                        Upgrade to Pro
                      </Link>
                    )}
                  </div>
                )}
              </div>
            )}
          </nav>

          <div className="ml-auto flex items-center gap-2 sm:gap-3">
            <DarkModeToggle showLabel className="hidden md:inline-flex" />
            <DarkModeToggle className="md:hidden" />
            {user && <NotificationBell />}

            {user ? (
              <div className="relative hidden lg:block" ref={userRef}>
                <button
                  type="button"
                  onClick={() => setShowUserMenu((v) => !v)}
                  aria-expanded={showUserMenu}
                  aria-haspopup="menu"
                  className="flex max-w-[14rem] items-center gap-1 border-2 border-current px-3 py-1.5 font-ui text-sm font-semibold"
                >
                  <span className="truncate">{displayName}</span>
                  <ChevronDownIcon className="h-4 w-4 shrink-0" />
                </button>
                {showUserMenu && (
                  <div role="menu" className="absolute right-0 top-full z-50 mt-2 w-56 border-2 border-content bg-surface-raised py-1 text-content shadow-xl">
                    <div className="border-b border-line px-4 py-2">
                      <p className="truncate font-ui text-sm font-bold">{displayName}</p>
                      <p className="font-ui text-xs text-content-faint">{planLabel}</p>
                    </div>
                    <Link to="/profile" className="block px-4 py-2 font-ui text-sm hover:bg-surface-inset">
                      Profile settings
                    </Link>
                    {isFree && (
                      <Link to="/premium" className="block px-4 py-2 font-ui text-sm font-semibold text-accent hover:bg-surface-inset">
                        Upgrade to Pro
                      </Link>
                    )}
                    <button type="button" onClick={handleLogout} className="block w-full px-4 py-2 text-left font-ui text-sm hover:bg-surface-inset">
                      Sign out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <>
                <Link to="/login" className="hidden whitespace-nowrap font-ui text-sm font-semibold text-slab-on hover:underline sm:inline">
                  Sign in
                </Link>
                <Link to={alertsHref} className="btn-primary hidden whitespace-nowrap text-sm sm:inline-block">
                  Get alerts
                </Link>
              </>
            )}

            <button
              type="button"
              onClick={() => setShowMobileMenu((v) => !v)}
              aria-expanded={showMobileMenu}
              aria-label={showMobileMenu ? 'Close menu' : 'Open menu'}
              className="p-1.5 text-slab-on lg:hidden"
            >
              {showMobileMenu ? <XMarkIcon className="h-7 w-7" /> : <Bars3Icon className="h-7 w-7" />}
            </button>
          </div>
        </div>

        {/* Mobile menu: drops down inside the slab */}
        {showMobileMenu && (
          <div className="border-t border-slab-muted lg:hidden">
            <nav aria-label="Main" className="mx-auto max-w-[1320px] px-4 pb-4 pt-2 sm:px-8">
              {PRIMARY_NAV.map((item) => {
                const active = isActive(item.match);
                return (
                  <Link
                    key={item.href}
                    to={item.href}
                    aria-current={active ? 'page' : undefined}
                    className={`flex items-center gap-3 py-2.5 font-display text-2xl font-extrabold ${
                      active ? 'text-slab-on' : 'text-slab-muted hover:text-slab-on'
                    }`}
                  >
                    <span aria-hidden="true" className={`h-5 w-1 ${active ? 'bg-accent' : 'bg-transparent'}`} />
                    {item.name}
                  </Link>
                );
              })}

              {user ? (
                <>
                  <div className="mt-3 border-t border-slab-muted pt-3 font-ui text-[11px] font-semibold uppercase tracking-[0.12em] text-slab-muted">
                    Tools
                  </div>
                  <div className="-mx-4">
                    {TOOLS_NAV.map((item) => renderToolLink(item, true))}
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-3 border-t border-slab-muted pt-3 font-ui text-sm">
                    <span className="mr-auto truncate text-slab-muted">
                      {displayName}, {planLabel.toLowerCase()}
                    </span>
                    <Link to="/profile" className="font-semibold text-slab-on hover:underline">
                      Profile
                    </Link>
                    {isFree && (
                      <Link to="/premium" className="font-semibold text-slab-on hover:underline">
                        Upgrade
                      </Link>
                    )}
                    <button type="button" onClick={handleLogout} className="font-semibold text-slab-on hover:underline">
                      Sign out
                    </button>
                  </div>
                </>
              ) : (
                <div className="mt-3 flex items-center gap-3 border-t border-slab-muted pt-4">
                  <Link to="/login" className="border-2 border-current px-4 py-2 font-ui text-sm font-semibold text-slab-on">
                    Sign in
                  </Link>
                  <Link to={alertsHref} className="btn-primary text-sm">
                    Get alerts
                  </Link>
                </div>
              )}
            </nav>
          </div>
        )}
      </header>

      <LatestStrip />

      <main className="flex-grow">
        <div className="mx-auto w-full max-w-[1320px] px-4 py-8 sm:px-8">{children}</div>
      </main>

      <footer className="mt-8 border-t-[3px] border-content">
        <div className="mx-auto flex max-w-[1320px] flex-col gap-4 px-4 py-6 font-ui text-[13px] text-content-faint sm:px-8 md:flex-row md:items-start md:justify-between">
          <p className="max-w-[70ch]">
            Source: House Clerk and Senate eFD periodic transaction reports. Members report ranges, not exact
            amounts. A filing is late when it lands more than 45 days after the trade; amended filings are not
            counted as late.
          </p>
          <nav aria-label="Footer" className="flex shrink-0 flex-wrap items-center gap-x-5 gap-y-2">
            <Link to="/privacy" className="hover:text-content">
              Privacy
            </Link>
            <Link to="/terms" className="hover:text-content">
              Terms
            </Link>
            <a href="mailto:capitolscope@gmail.com" className="hover:text-content">
              Contact
            </a>
            <span>&copy; {new Date().getFullYear()} CapitolScope</span>
          </nav>
        </div>
      </footer>

      <HubFooter />
    </div>
  );
};

export default Layout;
