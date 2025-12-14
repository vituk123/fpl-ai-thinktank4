import React, { useEffect, useState, useRef } from 'react';
import { gsap } from 'gsap';
import { SplitText as GSAPSplitText } from 'gsap/SplitText';

interface LoadingLogoProps {
  text?: string;
  phases?: Array<{ message: string; duration: number }>;
}

const LoadingLogo: React.FC<LoadingLogoProps> = ({ 
  text = "Loading...",
  phases = []
}) => {
  const [currentPhase, setCurrentPhase] = useState<string>(phases.length > 0 ? phases[0].message : text);
  const textRef = useRef<HTMLDivElement>(null);
  const splitInstanceRef = useRef<GSAPSplitText | null>(null);

  useEffect(() => {
    if (phases.length === 0) {
      setCurrentPhase(text);
      return;
    }

    // Initialize with first phase
    setCurrentPhase(phases[0].message);

    // Phase-based message updates
    const startTime = Date.now();
    let totalDuration = phases.reduce((sum, phase) => sum + phase.duration, 0);
    
    const updatePhase = () => {
      const elapsed = Date.now() - startTime;
      
      // Determine current phase based on elapsed time
      let cumulativeTime = 0;
      let currentPhaseIdx = 0;
      for (let i = 0; i < phases.length; i++) {
        cumulativeTime += phases[i].duration;
        if (elapsed < cumulativeTime) {
          currentPhaseIdx = i;
          break;
        }
        if (i === phases.length - 1) {
          currentPhaseIdx = i;
        }
      }
      
      const newPhase = phases[currentPhaseIdx].message;
      if (newPhase !== currentPhase) {
        setCurrentPhase(newPhase);
      }
      
      if (elapsed < totalDuration) {
        requestAnimationFrame(updatePhase);
      }
    };
    
    const animationId = requestAnimationFrame(updatePhase);
    
    return () => cancelAnimationFrame(animationId);
  }, [phases]);

  // Animate text when phase changes
  useEffect(() => {
    if (!textRef.current) return;

    // Small delay to ensure DOM is updated
    const timeout = setTimeout(() => {
      // Clean up previous split instance
      if (splitInstanceRef.current) {
        splitInstanceRef.current.revert();
      }

      // Create new split text instance
      const split = new GSAPSplitText(textRef.current, {
        type: "chars",
      });

      splitInstanceRef.current = split;

      // Animate characters
      gsap.from(split.chars, {
        opacity: 0,
        y: 20,
        duration: 0.5,
        ease: "power3.out",
        stagger: 0.02,
      });
    }, 50);

    return () => {
      clearTimeout(timeout);
      if (splitInstanceRef.current) {
        splitInstanceRef.current.revert();
      }
    };
  }, [currentPhase]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] px-4">
      {/* Logo */}
      <div className="relative" style={{ width: '384px', height: '384px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <img
          src="/logo2.png"
          alt="FPL OPTIMIZER"
          className="w-96 h-96 object-contain"
        />
      </div>

      {/* Loading Text and Phase Message - Close to logo */}
      <div className="text-center max-w-md mt-2 space-y-1">
        <p className="font-bold text-retro-primary uppercase tracking-wider text-lg">
          Loading...
        </p>
        <div
          ref={textRef}
          className="font-bold text-retro-primary uppercase tracking-wider text-lg"
        >
          {currentPhase}
        </div>
      </div>
    </div>
  );
};

export default LoadingLogo;
