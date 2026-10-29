import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { 
  Home, 
  Users, 
  User, 
  BarChart2, 
  Zap, 
  ListChecks, 
  Menu, 
  X 
} from 'lucide-react';

interface NavItem {
  name: string;
  shortName: string;
  path: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { name: 'IPL Overview (Home)', shortName: 'IPL Overview', path: '/', icon: Home },
  { name: 'Team Analysis', shortName: 'Teams', path: '/teams', icon: Users },
  { name: 'Player Explorer', shortName: 'Players', path: '/players', icon: User },
  { name: 'Statistics & EDA', shortName: 'Statistics & EDA', path: '/eda', icon: BarChart2 },
  { name: 'Prediction Arena', shortName: 'Prediction Arena', path: '/predict', icon: Zap },
  { name: 'Prediction Tracker', shortName: 'Prediction Tracker', path: '/tracker', icon: ListChecks },
];

export const Navbar: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full bg-[#070708]/90 backdrop-blur-md border-b border-white/[0.08]">
      <div className="max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
        {/* Brand Logo */}
        <NavLink 
          to="/" 
          className="flex items-center gap-3 group focus:outline-none focus:ring-2 focus:ring-[#D9B15F] rounded-lg p-1"
        >
          <div className="relative w-10 h-10 rounded-full bg-gradient-to-br from-[#D9B15F]/20 via-[#151619] to-black border border-[#D9B15F]/40 flex items-center justify-center shadow-gold-pill group-hover:border-[#D9B15F] transition-colors">
            {/* Stylized Cricket Lens Seam */}
            <div className="w-5 h-5 rounded-full border-2 border-dashed border-[#D9B15F] flex items-center justify-center transform -rotate-45">
              <div className="w-1.5 h-1.5 rounded-full bg-[#E7C479]" />
            </div>
          </div>
          <div>
            <div className="text-xl sm:text-2xl font-bold tracking-tight text-[#F6F6F3] flex items-center">
              Cricket<span className="text-[#D9B15F]">Lens</span>
            </div>
            <p className="text-[10px] tracking-[0.2em] font-medium text-[#B9B9B3]/80 uppercase -mt-0.5">
              Historical IPL Analytics
            </p>
          </div>
        </NavLink>

        {/* Desktop Navigation */}
        <nav className="hidden xl:flex items-center gap-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => `
                  flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-medium transition-all duration-200
                  ${isActive 
                    ? 'bg-[#151619] border border-[#D9B15F] text-[#D9B15F] shadow-gold-pill' 
                    : 'text-[#B9B9B3] hover:text-[#F6F6F3] hover:bg-white/[0.04]'
                  }
                `}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Tablet Navigation (Short names) */}
        <nav className="hidden md:flex xl:hidden items-center gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => `
                  flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-xs font-medium transition-all duration-200
                  ${isActive 
                    ? 'bg-[#151619] border border-[#D9B15F] text-[#D9B15F] shadow-gold-pill' 
                    : 'text-[#B9B9B3] hover:text-[#F6F6F3] hover:bg-white/[0.04]'
                  }
                `}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{item.shortName}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Mobile menu button */}
        <div className="flex md:hidden">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg text-[#B9B9B3] hover:text-[#D9B15F] hover:bg-white/[0.05] focus:outline-none focus:ring-2 focus:ring-[#D9B15F]"
            aria-label="Toggle navigation menu"
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile menu dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-white/[0.08] bg-[#070708]/95 px-4 pt-3 pb-5 space-y-1.5 animate-fadeIn">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) => `
                  flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors
                  ${isActive 
                    ? 'bg-[#151619] border border-[#D9B15F] text-[#D9B15F]' 
                    : 'text-[#B9B9B3] hover:text-[#F6F6F3] hover:bg-white/[0.04]'
                  }
                `}
              >
                <Icon className="w-4 h-4 text-[#D9B15F]" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </div>
      )}
    </header>
  );
};
