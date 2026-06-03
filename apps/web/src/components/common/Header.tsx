'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Bell, Menu, Search, X } from 'lucide-react';
import type { AlertEvent } from '@neuroquant/types';
import { alertsApi } from '@/lib/api-client';
import { usePriceFeed } from '@/hooks/usePriceFeed';

/**
 * Header Component
 * 
 * Global navigation header with:
 * - Logo/branding
 * - Navigation links
 * - Search (command palette)
 * - Notifications bell
 * - User profile dropdown
 * - WebSocket connection status
 */

const Header = (): JSX.Element => {
  const [showSearchPalette, setShowSearchPalette] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showMobileNav, setShowMobileNav] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const { status: connectionStatus } = usePriceFeed(['NIFTY50']);

  const navItems = [
    { href: '/', label: 'Terminal' },
    { href: '/markets', label: 'Markets' },
    { href: '/portfolio', label: 'Portfolio' },
    { href: '/portfolio/funds', label: 'Funds' },
    { href: '/backtest-lab', label: 'Backtest Lab' },
    { href: '/research', label: 'Research' },
    { href: '/model-monitor', label: 'Model Monitor' },
    { href: '/alerts', label: 'Alerts' },
  ];

  useEffect(() => {
    let mounted = true;

    async function loadNotifications(): Promise<void> {
      try {
        const data = await alertsApi.getHistory(8);
        if (!mounted) {
          return;
        }
        setAlerts(data);
      } catch {
        if (mounted) {
          setAlerts([]);
        }
      }
    }

    void loadNotifications();
    const intervalId = setInterval(() => {
      void loadNotifications();
    }, 15_000);

    return () => {
      mounted = false;
      clearInterval(intervalId);
    };
  }, []);

  return (
    <>
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-40 border-b border-[#1E2532] bg-[linear-gradient(90deg,rgba(10,11,14,0.98),rgba(15,23,36,0.94))] backdrop-blur-md">
        <div className="flex items-center justify-between px-4 py-3 sm:px-6">
          {/* Logo & Branding */}
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="w-10 h-10 bg-gradient-to-br from-[#00D4FF] to-[#00E676] rounded-lg flex items-center justify-center font-bold text-[#0A0B0E] text-lg">
              NQ
            </div>
            <span className="text-xl font-bold text-[#E8EAED] font-clash hidden sm:inline">
              NeuroQuant
            </span>
          </Link>

          {/* Main Navigation */}
          <nav className="hidden xl:flex items-center gap-6">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="text-sm text-[#8B9BB4] hover:text-[#00D4FF] transition-colors"
              >
                {item.label}
              </Link>
            ))}
          </nav>

          {/* Right side items */}
          <div className="flex items-center gap-2 sm:gap-4">
            {/* Search */}
            <button
              onClick={() => setShowSearchPalette(!showSearchPalette)}
              className="hidden sm:flex items-center gap-2 px-3 py-2 bg-[#161B24] border border-[#1E2532] rounded-lg hover:border-[#00D4FF] transition-all group"
            >
              <Search className="h-4 w-4 text-[#8B9BB4]" />
              <span className="text-xs text-[#8B9BB4]">Search</span>
            </button>

            {/* Connection Status */}
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  connectionStatus === 'connected' ? 'bg-[#00E676] animate-pulse' : 'bg-[#FF3B3B]'
                }`}
              />
              <span className="text-xs text-[#8B9BB4] hidden sm:inline">
                {connectionStatus === 'connected' ? 'Live' : 'Offline'}
              </span>
            </div>

            {/* Notifications */}
            <div className="relative">
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className="relative p-2 hover:bg-[#161B24] rounded-lg transition-colors"
              >
                <Bell className="h-5 w-5 text-[#E8EAED]" />
                {alerts.length > 0 && (
                  <div className="absolute top-1 right-1 w-4 h-4 bg-[#FF3B3B] rounded-full text-xs text-white flex items-center justify-center font-bold">
                    {Math.min(alerts.length, 9)}
                  </div>
                )}
              </button>

              {/* Notifications Dropdown */}
              {showNotifications && (
                <div className="absolute top-full right-0 mt-2 w-80 bg-[#161B24] border border-[#1E2532] rounded-lg shadow-lg z-50">
                  <div className="p-4 border-b border-[#1E2532]">
                    <h3 className="font-semibold text-[#E8EAED]">Notifications</h3>
                  </div>
                  <div className="max-h-96 overflow-y-auto">
                    {alerts.slice(0, 5).map((alert) => (
                      <div
                        key={alert.id}
                        className="p-4 border-b border-[#1E2532] hover:bg-[#0A0B0E] cursor-pointer transition-colors"
                      >
                        <p className="text-sm text-[#E8EAED]">{alert.message}</p>
                        <p className="text-xs text-[#8B9BB4]">{alert.symbol} • {new Date(alert.triggered_at).toLocaleTimeString()}</p>
                      </div>
                    ))}
                  </div>
                  <div className="p-3 border-t border-[#1E2532] text-center">
                    <Link
                      href="/alerts"
                      className="text-xs text-[#00D4FF] hover:text-[#00E676]"
                    >
                      View all alerts
                    </Link>
                  </div>
                </div>
              )}
            </div>

            {/* User Profile */}
            <button className="w-8 h-8 rounded-full bg-gradient-to-br from-[#00D4FF] to-[#00E676] text-[#0A0B0E] font-bold text-sm hover:shadow-lg transition-all">
              U
            </button>

            {/* Mobile Menu */}
            <button
              onClick={() => setShowMobileNav((prev) => !prev)}
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-[#1E2532] bg-[#161B24] text-[#E8EAED] xl:hidden"
              aria-label="Toggle navigation"
            >
              {showMobileNav ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {showMobileNav ? (
          <div className="border-t border-[#1E2532] bg-[#0E1320] px-4 py-3 xl:hidden">
            <div className="grid grid-cols-2 gap-2">
              {navItems.map((item) => (
                <Link
                  key={`mobile-${item.href}`}
                  href={item.href}
                  onClick={() => setShowMobileNav(false)}
                  className="rounded border border-[#1E2532] bg-[#161B24] px-3 py-2 text-xs text-[#8B9BB4] hover:border-[#00D4FF] hover:text-[#E8EAED]"
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
        ) : null}
      </header>

      {/* Search Command Palette */}
      {showSearchPalette && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-32 bg-black/50">
          <button
            onClick={() => setShowSearchPalette(false)}
            className="absolute inset-0 cursor-default"
            aria-label="Close search"
          />

          <div className="relative w-full max-w-xl bg-[#161B24] border border-[#1E2532] rounded-lg shadow-xl">
            <div className="p-4 border-b border-[#1E2532]">
              <input
                type="text"
                placeholder="Search stocks, symbols, pages..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                autoFocus
                className="w-full bg-transparent text-[#E8EAED] placeholder-[#8B9BB4] outline-none font-jbmono"
              />
            </div>
            <div className="max-h-96 overflow-y-auto p-4 space-y-2">
              <div className="text-sm text-[#8B9BB4] text-center py-8">
                Type to search...
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default Header;
