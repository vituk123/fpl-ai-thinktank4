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
  const spinnerRef = useRef<HTMLDivElement>(null);
  const phaseIndexRef = useRef<number>(0);

  // Animate circular spinner
  useEffect(() => {
    if (!spinnerRef.current) return;

    const spinner = spinnerRef.current;
    gsap.to(spinner, {
      rotation: 360,
      duration: 1,
      ease: "none",
      repeat: -1,
    });

    return () => {
      gsap.killTweensOf(spinner);
    };
  }, []);

  useEffect(() => {
    if (phases.length === 0) {
      setCurrentPhase(text);
      phaseIndexRef.current = 0;
      return;
    }

    // Initialize with first phase
    phaseIndexRef.current = 0;
    setCurrentPhase(phases[0].message);

    // Phase-based message updates - change every 1.5 seconds, loop continuously
    const intervalId = setInterval(() => {
      phaseIndexRef.current = (phaseIndexRef.current + 1) % phases.length; // Loop back to start
      setCurrentPhase(phases[phaseIndexRef.current].message);
    }, 1500); // Change every 1.5 seconds
    
    return () => clearInterval(intervalId);
  }, [phases, text]);

  // Animate text when phase changes - new animation style
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

      // New animation: fade in with scale and rotation
      gsap.from(split.chars, {
        opacity: 0,
        scale: 0,
        rotation: -180,
        y: 30,
        duration: 0.6,
        ease: "back.out(1.7)",
        stagger: {
          amount: 0.3,
          from: "center"
        },
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

      {/* Loading Spinner and Phase Message - Close to logo */}
      <div className="text-center max-w-md mt-2 space-y-2">
        {/* Animated Circular Loading Icon */}
        <div className="flex items-center justify-center">
          <div
            ref={spinnerRef}
            className="w-8 h-8 border-4 border-retro-primary border-t-transparent rounded-full"
            style={{ borderWidth: '4px' }}
          />
        </div>
        {/* Phase Message */}
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
