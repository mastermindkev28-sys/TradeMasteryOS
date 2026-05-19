'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import SignOutButton from '@/components/SignOutButton';

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: 'fa-chart-line' },
  { href: '/dashboard', label: 'Table of Contents', icon: 'fa-list' },
  { href: '/dashboard', label: 'Trading Plan', icon: 'fa-clipboard-list' },
  { href: '/dashboard', label: 'Daily Log', icon: 'fa-sun', badge: 'New' },
  { href: '/database', label: 'Trade Database', icon: 'fa-database' },
  { href: '/dashboard', label: 'Psychology', icon: 'fa-brain' },
  { href: '/dashboard', label: 'Goals', icon: 'fa-bullseye' },
  { href: '/dashboard', label: 'Analytics', icon: 'fa-chart-bar' },
  { href: '/dashboard', label: 'Landing Page', icon: 'fa-star' },
  { href: '/dashboard', label: 'Setup Guide', icon: 'fa-book' },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <nav className="sidebar">
      <div className="sb-logo">
        <div className="sb-logo-mark">
          <div className="sb-logo-icon">📈</div>
          <span className="sb-logo-text">TradingOS</span>
        </div>
        <div className="sb-logo-sub">v2.0 · Trading Journal</div>
      </div>

      <div className="sb-section">
        <div className="sb-section-label">Overview</div>
        <Link className={`nav-btn ${pathname === '/dashboard' ? 'active' : ''}`} href="/dashboard">
          <i className="fa-solid fa-chart-line"></i> Dashboard
        </Link>
        <Link className={`nav-btn ${pathname === '/dashboard' ? 'active' : ''}`} href="/dashboard">
          <i className="fa-solid fa-list"></i> Table of Contents
        </Link>
      </div>

      <div className="sb-section">
        <div className="sb-section-label">Core</div>
        <Link className={`nav-btn ${pathname === '/plan' ? 'active' : ''}`} href="/plan">
          <i className="fa-solid fa-clipboard-list"></i> Trading Plan
        </Link>
        <Link className={`nav-btn ${pathname === '/daily' ? 'active' : ''}`} href="/daily">
          <i className="fa-solid fa-sun"></i> Daily Log <span className="nb">New</span>
        </Link>
        <Link className={`nav-btn ${pathname === '/database' ? 'active' : ''}`} href="/database">
          <i className="fa-solid fa-database"></i> Trade Database
        </Link>
      </div>

      <div className="sb-section">
        <div className="sb-section-label">Gold Bot</div>
        <Link className={`nav-btn ${pathname === '/bot' ? 'active' : ''}`} href="/bot">
          <i className="fa-solid fa-robot"></i> Bot Control <span className="nb">Live</span>
        </Link>
      </div>

      <div className="sb-section">
        <div className="sb-section-label">Growth</div>
        <Link className={`nav-btn ${pathname === '/psychology' ? 'active' : ''}`} href="/psychology">
          <i className="fa-solid fa-brain"></i> Psychology
        </Link>
        <Link className={`nav-btn ${pathname === '/goals' ? 'active' : ''}`} href="/goals">
          <i className="fa-solid fa-bullseye"></i> Goals
        </Link>
        <Link className={`nav-btn ${pathname === '/analytics' ? 'active' : ''}`} href="/analytics">
          <i className="fa-solid fa-chart-bar"></i> Analytics
        </Link>
      </div>

      <div className="sb-section">
        <div className="sb-section-label">Product</div>
        <Link className={`nav-btn ${pathname === '/landing' ? 'active' : ''}`} href="/landing">
          <i className="fa-solid fa-star"></i> Landing Page
        </Link>
        <Link className={`nav-btn ${pathname === '/pricing' ? 'active' : ''}`} href="/pricing">
          <i className="fa-solid fa-tags"></i> Pricing
        </Link>
        <Link className={`nav-btn ${pathname === '/terms' ? 'active' : ''}`} href="/terms">
          <i className="fa-solid fa-file-contract"></i> Terms
        </Link>
        <Link className={`nav-btn ${pathname === '/refund-policy' ? 'active' : ''}`} href="/refund-policy">
          <i className="fa-solid fa-hand-holding-dollar"></i> Refund Policy
        </Link>
        <Link className={`nav-btn ${pathname === '/privacy' ? 'active' : ''}`} href="/privacy">
          <i className="fa-solid fa-shield-halved"></i> Privacy Policy
        </Link>
        <Link className={`nav-btn ${pathname === '/setup' ? 'active' : ''}`} href="/setup">
          <i className="fa-solid fa-book"></i> Setup Guide
        </Link>
      </div>

      <div className="sb-section">
        <div className="sb-section-label">Account</div>
        <SignOutButton />
      </div>
    </nav>
  );
}
