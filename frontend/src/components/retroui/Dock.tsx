import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Home, BarChart2, Radio, Zap, Newspaper } from 'lucide-react';

const Dock: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const items = [
    { icon: Home, label: 'Home', path: '/' },
    { icon: BarChart2, label: 'Dash', path: '/dashboard' },
    { icon: Radio, label: 'Live', path: '/live' },
    { icon: Zap, label: 'ML', path: '/recommendations' },
    { icon: Newspaper, label: 'News', path: '/news' },
  ];

  return (
    <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 z-50">
      <div className="flex items-end space-x-2 px-4 py-2 bg-white border-retro border-retro-primary shadow-retro rounded-none">
        {items.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <button
              key={item.label}
              onClick={() => navigate(item.path)}
              className={`
                group flex flex-col items-center justify-center p-2
                transition-transform duration-200 hover:-translate-y-2
                ${isActive ? 'bg-retro-background' : ''}
              `}
            >
              <div className="border-2 border-retro-primary p-2 bg-white shadow-[2px_2px_0_#1D1D1B] group-hover:shadow-[4px_4px_0_#1D1D1B] transition-shadow">
                 <item.icon size={24} strokeWidth={2.5} />
              </div>
              <span className="text-xs font-bold mt-1 opacity-0 group-hover:opacity-100 absolute -top-8 bg-retro-primary text-white px-2 py-0.5 border border-black whitespace-nowrap">
                {item.label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default Dock;
