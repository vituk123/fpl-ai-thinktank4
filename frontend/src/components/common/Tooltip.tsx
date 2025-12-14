import React, { useState, useRef, useEffect } from 'react';
import { HelpCircle } from 'lucide-react';

interface TooltipProps {
  text: string;
  children?: React.ReactNode;
  className?: string;
}

const Tooltip: React.FC<TooltipProps> = ({ text, children, className = '' }) => {
  const [isVisible, setIsVisible] = useState(false);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (tooltipRef.current && !tooltipRef.current.contains(event.target as Node) &&
          containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsVisible(false);
      }
    };

    if (isVisible) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isVisible]);

  // Calculate position to keep tooltip within viewport and container
  useEffect(() => {
    if (isVisible && tooltipRef.current && containerRef.current) {
      const tooltip = tooltipRef.current;
      const button = containerRef.current;
      
      // Find the nearest scrollable container or use viewport
      let scrollContainer = button.parentElement;
      while (scrollContainer && scrollContainer !== document.body) {
        const overflow = window.getComputedStyle(scrollContainer).overflow;
        if (overflow === 'auto' || overflow === 'scroll' || overflow === 'hidden') {
          break;
        }
        scrollContainer = scrollContainer.parentElement;
      }
      
      const container = scrollContainer || document.documentElement;
      const containerRect = container.getBoundingClientRect();
      const buttonRect = button.getBoundingClientRect();
      const tooltipRect = tooltip.getBoundingClientRect();
      
      // Reset positioning
      tooltip.style.left = '';
      tooltip.style.right = '';
      tooltip.style.transform = '';
      
      // Check viewport boundaries
      const viewportWidth = window.innerWidth;
      const viewportPadding = 16;
      
      // Calculate available space
      const spaceRight = viewportWidth - buttonRect.right;
      const spaceLeft = buttonRect.left;
      
      // Position tooltip - prefer left alignment, but adjust if needed
      if (tooltipRect.width > spaceRight && spaceLeft > spaceRight) {
        // Not enough space on right, align to right of button
        tooltip.style.left = 'auto';
        tooltip.style.right = '0';
      } else {
        // Default: align to left of button
        tooltip.style.left = '0';
        tooltip.style.right = 'auto';
      }
      
      // Constrain width to available space
      const maxWidth = Math.min(
        16 * 16, // 16rem = 256px default max
        viewportWidth - viewportPadding * 2,
        containerRect.width - 16
      );
      tooltip.style.maxWidth = `${maxWidth}px`;
    }
  }, [isVisible]);

  return (
    <span ref={containerRef} className={`relative inline-flex items-center ${className}`}>
      {children}
      <button
        type="button"
        className="ml-1 inline-flex items-center focus:outline-none"
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        onClick={(e) => {
          e.preventDefault();
          setIsVisible(!isVisible);
        }}
        aria-label="Show explanation"
      >
        <HelpCircle className="w-3 h-3 text-retro-primary opacity-70 hover:opacity-100 transition-opacity" />
      </button>
      {isVisible && (
        <div
          ref={tooltipRef}
          className="absolute bottom-full left-0 mb-2 p-2 bg-white border-2 border-retro-primary shadow-[4px_4px_0_rgba(0,0,0,0.1)] z-50 text-xs break-words"
          style={{ width: 'max-content' }}
          onMouseEnter={() => setIsVisible(true)}
          onMouseLeave={() => setIsVisible(false)}
        >
          {text}
        </div>
      )}
    </span>
  );
};

export default Tooltip;

