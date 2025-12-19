import React, { useState, useEffect, useRef } from 'react';
import { useAppContext } from '../../context/AppContext';
import { useNavigate, useLocation } from 'react-router-dom';
import { Battery, Wifi, Menu, X } from 'lucide-react';

const MacMenuBar: React.FC = () => {
  const { entryInfo, logout, isAuthenticated } = useAppContext();
  const navigate = useNavigate();
  const location = useLocation();
  const [time, setTime] = useState(new Date());
  const [isMobile, setIsMobile] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
      if (window.innerWidth > 768) {
        setIsMenuOpen(false);
      }
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };

    if (isMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isMenuOpen]);

  const formattedTime = time.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: false
  });

  const day = time.toLocaleDateString('en-US', { weekday: 'short' });

  // Menu items
  const navItems = isAuthenticated ? [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Live', href: '/live' },
    { label: 'ML', href: '/recommendations' },
    { label: 'News', href: '/news' },
  ] : [];

  // Desktop view (original Mac menu bar)
  if (!isMobile) {
  return (
      <div className="fixed top-0 left-0 right-0 h-9 bg-white border-b-retro border-retro-primary z-50 flex justify-between items-center pl-8 pr-4 select-none overflow-visible">
        <div className="flex items-center h-full overflow-visible">
        {/* Logo / Home */}
          <button onClick={() => navigate(isAuthenticated ? '/dashboard' : '/')} className="flex items-center justify-center hover:opacity-80 transition-opacity overflow-hidden p-0 m-0" style={{ clipPath: 'inset(0 0 0 0)' }}>
              <img src="/logo1.png" alt="FPL OPTIMIZER" className="h-[204px] w-auto" style={{ marginTop: '-100px', marginBottom: '-84px', marginLeft: '-20px', marginRight: '0', display: 'block' }} />
        </button>
        {isAuthenticated && (
              <nav className="hidden md:flex space-x-6 h-full items-center ml-4">
                <div className="relative group h-full flex items-center cursor-pointer">
                    <span className="font-bold text-sm">Dashboard</span>
                    <div className="absolute top-full left-0 bg-white border-retro border-retro-primary shadow-retro hidden group-hover:block min-w-[150px]">
                        <button onClick={() => navigate('/dashboard')} className="block w-full text-left px-4 py-2 hover:bg-retro-primary hover:text-white text-sm font-medium">Overview</button>
                        <button onClick={() => navigate('/live')} className="block w-full text-left px-4 py-2 hover:bg-retro-primary hover:text-white text-sm font-medium">Live Tracking</button>
                    </div>
                </div>
                 <div className="relative group h-full flex items-center cursor-pointer">
                    <span className="font-bold text-sm">Optimize</span>
                    <div className="absolute top-full left-0 bg-white border-retro border-retro-primary shadow-retro hidden group-hover:block min-w-[150px]">
                        <button onClick={() => navigate('/recommendations')} className="block w-full text-left px-4 py-2 hover:bg-retro-primary hover:text-white text-sm font-medium">Transfers</button>
                    </div>
                </div>
                <button onClick={() => navigate('/news')} className="font-bold text-sm hover:underline decoration-2">News</button>
            </nav>
        )}
      </div>

      <div className="flex items-center space-x-4">
        {isAuthenticated && entryInfo && (
            <div className="hidden sm:flex items-center border-r-2 border-retro-primary pr-4 mr-2">
                <span className="font-bold text-sm truncate max-w-[150px]">{entryInfo.name}</span>
                <button onClick={logout} className="ml-3 text-xs uppercase border-2 border-retro-primary px-1 hover:bg-retro-error hover:text-white transition-colors">Logout</button>
            </div>
        )}
        <div className="flex items-center space-x-2 text-sm font-bold">
             <Wifi size={16} strokeWidth={3} />
             <Battery size={16} strokeWidth={3} />
            <span>{day} {formattedTime}</span>
        </div>
      </div>
    </div>
    );
  }

  // Mobile view (custom dropdown menu with retro styling)
  return (
    <>
      <div className="fixed top-0 left-0 right-0 h-9 bg-white border-b-retro border-retro-primary z-50 flex items-center justify-between pl-4 sm:pl-8 pr-2 sm:pr-4 select-none overflow-visible">
        {/* Logo */}
        <button 
          onClick={() => {
            navigate(isAuthenticated ? '/dashboard' : '/');
            setIsMenuOpen(false);
          }} 
          className="flex items-center justify-center hover:opacity-80 transition-opacity flex-shrink-0 overflow-visible p-0 m-0"
        >
          <img src="/logo1.png" alt="FPL OPTIMIZER" className="h-[204px] w-auto" style={{ marginTop: '-100px', marginBottom: '-84px', marginLeft: '-20px', marginRight: '0' }} />
        </button>

        {/* Status elements - between logo and menu button */}
        <div className="flex items-center space-x-1 sm:space-x-2 text-xs font-bold flex-1 justify-end mr-2 min-w-0">
          {isAuthenticated && entryInfo && (
            <div className="flex items-center pr-1 sm:pr-2 mr-1 sm:mr-2 min-w-0">
              <span className="font-bold text-[10px] sm:text-xs whitespace-nowrap">{entryInfo.name}</span>
              <button onClick={logout} className="ml-1 sm:ml-2 text-[8px] sm:text-[10px] uppercase border-2 border-retro-primary px-0.5 sm:px-1 hover:bg-retro-error hover:text-white transition-colors flex-shrink-0">Logout</button>
            </div>
          )}
          <Wifi size={10} strokeWidth={3} className="hidden sm:block sm:w-3 sm:h-3 flex-shrink-0" />
          <Battery size={10} strokeWidth={3} className="hidden sm:block sm:w-3 sm:h-3 flex-shrink-0" />
          <span className="text-[10px] sm:text-xs whitespace-nowrap flex-shrink-0">{day} {formattedTime}</span>
        </div>

        {/* Menu Toggle Button */}
        {isAuthenticated && (
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="flex items-center justify-center h-7 w-7 border-2 border-retro-primary bg-white hover:bg-retro-primary hover:text-white transition-colors flex-shrink-0"
            aria-label="Toggle menu"
          >
            {isMenuOpen ? (
              <X size={16} strokeWidth={3} />
            ) : (
              <Menu size={16} strokeWidth={3} />
            )}
          </button>
        )}
      </div>

      {/* Dropdown Menu */}
      {isAuthenticated && isMenuOpen && (
        <div 
          ref={menuRef}
          className="fixed top-9 left-0 right-0 bg-white border-b-2 border-retro-primary shadow-[4px_4px_0_rgba(0,0,0,0.1)] z-40"
        >
          <nav className="flex flex-col">
            {navItems.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <button
                  key={item.href}
                  onClick={() => {
                    navigate(item.href);
                    setIsMenuOpen(false);
                  }}
                  className={`
                    w-full text-left px-4 py-3 font-bold text-sm uppercase tracking-wider
                    border-b-2 border-retro-primary
                    transition-colors
                    ${isActive 
                      ? 'bg-retro-primary text-white' 
                      : 'bg-white text-retro-primary hover:bg-retro-background'
                    }
                  `}
                >
                  {item.label}
                </button>
              );
            })}
          </nav>
        </div>
      )}
    </>
  );
};

export default MacMenuBar;
