import {
  BarChart3,
  Bell,
  BookOpen,
  Briefcase,
  CandlestickChart,
  CreditCard,
  FlaskConical,
  LayoutDashboard,
  Search,
  Settings,
  Shield,
  Wallet,
  User,
} from 'lucide-react';

export interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

export const dashboardNavItems: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Terminal', href: '/terminal', icon: CandlestickChart },
  { label: 'Markets', href: '/markets', icon: BarChart3 },
  { label: 'Research', href: '/research', icon: BookOpen },
  { label: 'Backtest Lab', href: '/backtest-lab', icon: FlaskConical },
  { label: 'Portfolio', href: '/portfolio', icon: Briefcase },
  { label: 'Screener', href: '/screener', icon: Search },
  { label: 'Alerts', href: '/alerts', icon: Bell },
  { label: 'Notifications', href: '/notifications', icon: Bell },
  { label: 'Admin', href: '/admin', icon: Shield },
  { label: 'Profile', href: '/profile', icon: User },
  { label: 'Pricing', href: '/pricing', icon: CreditCard },
  { label: 'Transactions', href: '/transactions', icon: Wallet },
  { label: 'Settings', href: '/settings', icon: Settings },
];
