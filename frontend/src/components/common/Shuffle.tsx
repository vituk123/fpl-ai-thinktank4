import React, { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';

interface ShuffleProps {
  text: string;
  shuffleDirection?: 'left' | 'right';
  duration?: number;
  animationMode?: 'evenodd' | 'all';
  shuffleTimes?: number;
  ease?: string;
  stagger?: number;
  threshold?: number;
  triggerOnce?: boolean;
  triggerOnHover?: boolean;
  respectReducedMotion?: boolean;
  className?: string;
}

const Shuffle: React.FC<ShuffleProps> = ({
  text,
  shuffleDirection = 'right',
  duration = 0.35,
  animationMode = 'evenodd',
  shuffleTimes = 1,
  ease = 'power3.out',
  stagger = 0.03,
  threshold = 0.1,
  triggerOnce = true,
  respectReducedMotion = true,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hasAnimated, setHasAnimated] = useState(false);
  const textRef = useRef<string>(text);

  useEffect(() => {
    if (text !== textRef.current) {
      textRef.current = text;
      setHasAnimated(false);
    }
  }, [text]);

  useEffect(() => {
    if (!containerRef.current) return;
    if (triggerOnce && hasAnimated) return;
    if (respectReducedMotion && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return;
    }

    const chars = text.split('');
    const spans = containerRef.current.querySelectorAll('span');
    
    if (spans.length === 0) return;

    // Reset positions
    spans.forEach((span, index) => {
      gsap.set(span, {
        x: 0,
        opacity: 1,
      });
    });

    // Create shuffle animation
    const tl = gsap.timeline();
    
    spans.forEach((span, index) => {
      const shouldAnimate = animationMode === 'all' || 
        (animationMode === 'evenodd' && index % 2 === (shuffleDirection === 'right' ? 0 : 1));
      
      if (shouldAnimate) {
        const direction = shuffleDirection === 'right' ? 20 : -20;
        
        for (let i = 0; i < shuffleTimes; i++) {
          tl.to(span, {
            x: direction,
            opacity: 0.3,
            duration: duration / shuffleTimes / 2,
            ease: ease,
          }, index * stagger + i * (duration / shuffleTimes));
          tl.to(span, {
            x: 0,
            opacity: 1,
            duration: duration / shuffleTimes / 2,
            ease: ease,
          }, index * stagger + i * (duration / shuffleTimes) + duration / shuffleTimes / 2);
        }
      }
    });

    if (triggerOnce) {
      setHasAnimated(true);
    }

    return () => {
      tl.kill();
    };
  }, [text, hasAnimated, shuffleDirection, duration, animationMode, shuffleTimes, ease, stagger, triggerOnce, respectReducedMotion]);

  return (
    <div
      ref={containerRef}
      className={`inline-block font-bold text-retro-primary uppercase tracking-wider text-lg ${className}`}
      style={{ fontFamily: 'inherit' }}
    >
      {text.split('').map((char, index) => (
        <span
          key={`${text}-${index}`}
          className="inline-block"
          style={{ display: 'inline-block' }}
        >
          {char === ' ' ? '\u00A0' : char}
        </span>
      ))}
    </div>
  );
};

export default Shuffle;

