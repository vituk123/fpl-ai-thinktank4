import React, { useState, useEffect } from 'react';
import { useAppContext } from '../../context/AppContext';
import { useNavigate, useLocation } from 'react-router-dom';
import { Battery, Wifi } from 'lucide-react';
import PillNav from './PillNav';

const MacMenuBar: React.FC = () => {
  const { entryInfo, logout, isAuthenticated } = useAppContext();
  const navigate = useNavigate();
  const location = useLocation();
  const [time, setTime] = useState(new Date());
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const formattedTime = time.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: false
  });

  const day = time.toLocaleDateString('en-US', { weekday: 'short' });

  // Menu items for PillNav (Home removed - logo serves as home)
  const navItems = isAuthenticated ? [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Live', href: '/live' },
    { label: 'ML', href: '/recommendations' },
    { label: 'News', href: '/news' },
  ] : [];

  // Desktop view (original Mac menu bar)
  if (!isMobile) {
    return (
      <div className="fixed top-0 left-0 right-0 h-9 bg-white border-b-retro border-retro-primary z-50 flex justify-between items-center px-4 select-none">
        <div className="flex items-center space-x-6 h-full">
          {/* Logo / Home */}
          <button onClick={() => navigate(isAuthenticated ? '/dashboard' : '/')} className="flex items-center justify-center h-full hover:opacity-80 transition-opacity">
              <img src="/logo1.png" alt="FPL OPTIMIZER" className="h-[34px] w-auto" />
          </button>

          {isAuthenticated && (
              <nav className="hidden md:flex space-x-6 h-full items-center">
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

  // Mobile view (PillNav with retro styling)
  return (
    <>
      <PillNav
        logo="/logo1.png"
        logoAlt="FPL OPTIMIZER"
        items={navItems}
        homeHref={isAuthenticated ? '/dashboard' : '/'}
        activeHref={location.pathname}
        className="retro-pill-nav"
        ease="power2.easeOut"
        baseColor="#1D1D1B"
        pillColor="#fff"
        hoveredPillTextColor="#fff"
        pillTextColor="#1D1D1B"
        initialLoadAnimation={true}
      />
      {/* Status bar on mobile */}
      <div className="fixed top-[36px] left-0 right-0 h-6 bg-white border-b-retro border-retro-primary z-40 flex justify-end items-center px-4 select-none">
        <div className="flex items-center space-x-2 text-xs font-bold">
          {isAuthenticated && entryInfo && (
            <div className="flex items-center border-r-2 border-retro-primary pr-2 mr-2">
              <span className="font-bold text-xs truncate max-w-[100px]">{entryInfo.name}</span>
              <button onClick={logout} className="ml-2 text-[10px] uppercase border-2 border-retro-primary px-1 hover:bg-retro-error hover:text-white transition-colors">Logout</button>
            </div>
          )}
          <Wifi size={12} strokeWidth={3} />
          <Battery size={12} strokeWidth={3} />
          <span className="text-xs">{day} {formattedTime}</span>
        </div>
      </div>
    </>
  );
};

export default MacMenuBar;