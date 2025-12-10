import { useState, useEffect } from 'react';

/**
 * Hook for retro UI effects (CRT, scanlines, etc.)
 */
export const useRetro = (options = {}) => {
  const {
    enableCRT = true,
    enableScanlines = true,
    enableGlow = true,
  } = options;

  const [effects, setEffects] = useState({
    crt: enableCRT,
    scanlines: enableScanlines,
    glow: enableGlow,
  });

  const toggleEffect = (effectName) => {
    setEffects(prev => ({
      ...prev,
      [effectName]: !prev[effectName],
    }));
  };

  const enableAll = () => {
    setEffects({
      crt: true,
      scanlines: true,
      glow: true,
    });
  };

  const disableAll = () => {
    setEffects({
      crt: false,
      scanlines: false,
      glow: false,
    });
  };

  return {
    effects,
    toggleEffect,
    enableAll,
    disableAll,
  };
};

export default useRetro;

