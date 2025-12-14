import React from 'react';

const LoadingSpinner: React.FC<{ text?: string }> = ({ text = "Loading..." }) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 space-y-4">
        {/* Retro hourglass or geometric shape animation */}
        <div className="relative w-16 h-16 border-retro border-retro-primary animate-spin-slow" style={{ animationDuration: '3s' }}>
            <div className="absolute inset-0 border-retro border-retro-primary transform rotate-45"></div>
            <div className="absolute inset-2 bg-retro-primary opacity-20"></div>
        </div>
        <div className="w-48 h-6 border-retro border-retro-primary p-1 bg-white">
            <div className="h-full bg-retro-primary animate-pulse w-full origin-left transform scale-x-50"></div>
        </div>
      <p className="font-bold text-retro-primary uppercase tracking-wider">{text}</p>
    </div>
  );
};

export default LoadingSpinner;
