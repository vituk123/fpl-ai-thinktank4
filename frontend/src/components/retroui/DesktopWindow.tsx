import React, { ReactNode } from 'react';
import { X, Minus, Maximize2 } from 'lucide-react';

interface DesktopWindowProps {
  title: string;
  children: ReactNode;
  onClose?: () => void;
  className?: string;
  isMaximized?: boolean;
}

const DesktopWindow: React.FC<DesktopWindowProps> = ({ 
  title, 
  children, 
  onClose, 
  className = "",
  isMaximized = false
}) => {
  return (
    <div 
        className={`
            bg-white border-retro border-retro-primary shadow-retro 
            flex flex-col overflow-hidden transition-all duration-200
            ${isMaximized ? 'w-full h-full' : ''}
            ${className}
        `}
    >
      {/* Window Header */}
      <div className="flex items-center justify-between border-b-retro border-retro-primary h-8 px-2 bg-white relative select-none">
         {/* Stripes Pattern Background for Header Title Area - Mimicking the HTML CSS */}
         <div className="absolute inset-0 opacity-10 pointer-events-none bg-[url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAYAAACp8Z5+AAAAIklEQVQIW2NkQAKrVq36zwjjgzj//v37zwjjgzj//v37zwAA9cYY8X6wE04AAAAASUVORK5CYII=')]"></div>
         
        {/* Title Centered */}
        <div className="flex-1 flex justify-center items-center z-10">
             <div className="px-4 py-0.5 bg-retro-primary text-white text-xs font-bold uppercase tracking-widest transform -skew-x-12">
                <span className="block transform skew-x-12">{title}</span>
             </div>
        </div>

        {/* Controls */}
        <div className="absolute right-2 top-0 bottom-0 flex items-center space-x-1 z-20">
            {onClose && (
                <button 
                    onClick={onClose}
                    className="p-0.5 border-[1.5px] border-retro-primary hover:bg-retro-error hover:text-white transition-colors"
                >
                    <X size={12} strokeWidth={4} />
                </button>
            )}
        </div>
        
        {/* Fake controls left */}
        <div className="absolute left-2 top-0 bottom-0 flex items-center space-x-1 z-20">
             <div className="w-3 h-3 border-[1.5px] border-retro-primary bg-white"></div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4 custom-scrollbar relative">
        {children}
      </div>
    </div>
  );
};

export default DesktopWindow;
