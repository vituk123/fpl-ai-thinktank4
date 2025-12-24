import React, { useState, useEffect, useRef } from 'react';
import { useAppContext } from '../../context/AppContext';
import { useNavigate, useLocation } from 'react-router-dom';
import { Battery, Wifi, Menu, X } from 'lucide-react';
import { usePrefetch } from '../../hooks/usePrefetch';

const MacMenuBar: React.FC = () => {
  const { entryInfo, logout, isAuthenticated } = useAppContext();
  const navigate = useNavigate();
  const location = useLocation();
  const { prefetchRoute } = usePrefetch();
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
    { label: 'Gameweek Points Tracking', href: '/live' },
    { label: 'Team Optimization', href: '/recommendations' },
    // { label: 'News', href: '/news' }, // Disabled
  ] : [];

  // Desktop view (original Mac menu bar)
  if (!isMobile) {
  return (
      <div className="fixed top-0 left-0 right-0 h-9 bg-white border-b-retro border-retro-primary z-50 flex justify-between items-center pl-8 pr-4 select-none overflow-visible">
        <div className="flex items-center h-full overflow-visible">
        {/* Logo / Home */}
          <button onClick={() => navigate(isAuthenticated ? '/dashboard' : '/')} className="flex items-center justify-center hover:opacity-80 transition-opacity overflow-hidden p-0 m-0" style={{ clipPath: 'inset(0 0 0 0)' }}>
              <img src="/logo1.png" alt="FPL OPTIMIZER" width="1024" height="1024" loading="eager" className="h-[204px] w-auto" style={{ marginTop: '-100px', marginBottom: '-84px', marginLeft: '-20px', marginRight: '0', display: 'block' }} />
        </button>
        {isAuthenticated && (
              <nav className="hidden md:flex space-x-6 h-full items-center ml-4">
                <div className="relative group h-full flex items-center cursor-pointer" onMouseEnter={() => { prefetchRoute('/dashboard'); prefetchRoute('/live'); }}>
                    <span className="font-bold text-sm">Dashboard</span>
                    <div className="absolute top-full left-0 bg-white border-retro border-retro-primary shadow-retro hidden group-hover:block min-w-[150px] z-50">
                        <button 
                          onClick={() => navigate('/dashboard')} 
                          onMouseEnter={() => prefetchRoute('/dashboard')}
                          onTouchStart={(e) => {
                            e.stopPropagation();
                            navigate('/dashboard');
                          }}
                          className="block w-full text-left px-4 py-2 hover:bg-retro-primary hover:text-white active:bg-retro-primary active:text-white text-sm font-medium touch-manipulation"
                          style={{ touchAction: 'manipulation', WebkitTapHighlightColor: 'transparent', minHeight: '44px' }}
                        >
                          Overview
                        </button>
                        <button 
                          onClick={() => navigate('/live')} 
                          onMouseEnter={() => prefetchRoute('/live')}
                          onTouchStart={(e) => {
                            e.stopPropagation();
                            navigate('/live');
                          }}
                          className="block w-full text-left px-4 py-2 hover:bg-retro-primary hover:text-white active:bg-retro-primary active:text-white text-sm font-medium touch-manipulation"
                          style={{ touchAction: 'manipulation', WebkitTapHighlightColor: 'transparent', minHeight: '44px' }}
                        >
                          Gameweek Points Tracking
                        </button>
                    </div>
                </div>
                 <div className="relative group h-full flex items-center cursor-pointer" onMouseEnter={() => prefetchRoute('/recommendations')}>
                    <span className="font-bold text-sm">Optimize</span>
                    <div className="absolute top-full left-0 bg-white border-retro border-retro-primary shadow-retro hidden group-hover:block min-w-[150px] z-50">
                        <button 
                          onClick={() => navigate('/recommendations')} 
                          onMouseEnter={() => prefetchRoute('/recommendations')}
                          onTouchStart={(e) => {
                            e.stopPropagation();
                            navigate('/recommendations');
                          }}
                          className="block w-full text-left px-4 py-2 hover:bg-retro-primary hover:text-white active:bg-retro-primary active:text-white text-sm font-medium touch-manipulation"
                          style={{ touchAction: 'manipulation', WebkitTapHighlightColor: 'transparent', minHeight: '44px' }}
                        >
                          Team Optimization
                        </button>
                    </div>
                </div>
                {/* News button disabled */}
                {false && <button onClick={() => navigate('/news')} className="font-bold text-sm hover:underline decoration-2">News</button>}
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
      <div className="fixed top-0 left-0 right-0 h-9 bg-white border-b-retro border-retro-primary z-50 flex items-center justify-between pl-2 sm:pl-4 pr-2 select-none overflow-hidden">
        {/* Logo */}
        <button 
          onClick={() => {
            navigate(isAuthenticated ? '/dashboard' : '/');
            setIsMenuOpen(false);
          }}
          onTouchStart={(e) => {
            e.stopPropagation();
            navigate(isAuthenticated ? '/dashboard' : '/');
            setIsMenuOpen(false);
          }}
          className="flex items-center justify-center hover:opacity-80 active:opacity-60 transition-opacity flex-shrink-0 overflow-visible p-0 m-0 touch-manipulation"
          style={{ touchAction: 'manipulation', WebkitTapHighlightColor: 'transparent', minWidth: '60px' }}
        >
          <img src="/logo1.png" alt="FPL OPTIMIZER" width="1024" height="1024" loading="eager" className="h-[204px] w-auto" style={{ marginTop: '-100px', marginBottom: '-84px', marginLeft: '-20px', marginRight: '0' }} />
        </button>

        {/* Status elements - between logo and menu button */}
        <div className="flex items-center gap-1 text-xs font-bold flex-1 justify-end mr-1 sm:mr-2 min-w-0 overflow-hidden">
          {isAuthenticated && entryInfo && (
            <div className="flex items-center gap-1 min-w-0 flex-shrink">
              <span 
                className="font-bold text-[9px] sm:text-[10px] whitespace-nowrap truncate max-w-[80px] sm:max-w-[120px]"
                title={entryInfo.name}
              >
                {entryInfo.name}
              </span>
              <button 
                onClick={logout}
                onTouchStart={(e) => {
                  e.stopPropagation();
                  logout();
                }}
                className="text-[7px] sm:text-[8px] uppercase border-2 border-retro-primary px-1 py-0.5 hover:bg-retro-error hover:text-white active:bg-retro-error active:text-white transition-colors flex-shrink-0 touch-manipulation whitespace-nowrap"
                style={{ touchAction: 'manipulation', WebkitTapHighlightColor: 'transparent', minHeight: '20px', lineHeight: '1' }}
              >
                Out
              </button>
            </div>
          )}
          <div className="flex items-center gap-1 flex-shrink-0">
            <Wifi size={10} strokeWidth={3} className="hidden sm:block sm:w-3 sm:h-3" />
            <Battery size={10} strokeWidth={3} className="hidden sm:block sm:w-3 sm:h-3" />
            <span className="text-[9px] sm:text-[10px] whitespace-nowrap">{day} {formattedTime}</span>
          </div>
        </div>

        {/* Menu Toggle Button */}
        {isAuthenticated && (
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            onTouchStart={(e) => {
              e.stopPropagation();
              setIsMenuOpen(!isMenuOpen);
            }}
            className="flex items-center justify-center h-7 w-7 border-2 border-retro-primary bg-white hover:bg-retro-primary hover:text-white active:bg-retro-primary active:text-white transition-colors flex-shrink-0 touch-manipulation"
            style={{ touchAction: 'manipulation', WebkitTapHighlightColor: 'transparent' }}
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
          style={{ 
            maxWidth: '100vw', 
            width: '100%',
            overflowX: 'auto',
            overflowY: 'visible',
            touchAction: 'pan-x',
            WebkitOverflowScrolling: 'touch'
          }}
        >
          <nav className="flex flex-col" style={{ minWidth: '100%', width: '100%' }}>
            {navItems.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <button
                  key={item.href}
                  onClick={() => {
                    navigate(item.href);
                    setIsMenuOpen(false);
                  }}
                  onMouseEnter={() => prefetchRoute(item.href)}
                  onTouchStart={(e) => {
                    e.stopPropagation();
                    navigate(item.href);
                    setIsMenuOpen(false);
                  }}
                  className={`
                    w-full text-left px-4 py-3 font-bold text-sm uppercase tracking-wider
                    border-b-2 border-retro-primary
                    transition-colors touch-manipulation
                    whitespace-nowrap
                    ${isActive 
                      ? 'bg-retro-primary text-white' 
                      : 'bg-white text-retro-primary hover:bg-retro-background active:bg-retro-background'
                    }
                  `}
                  style={{ 
                    touchAction: 'manipulation', 
                    WebkitTapHighlightColor: 'transparent', 
                    minHeight: '44px',
                    width: '100%',
                    maxWidth: '100%'
                  }}
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
