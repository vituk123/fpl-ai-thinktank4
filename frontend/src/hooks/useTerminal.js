import { useState, useEffect } from 'react';

export const useTerminal = (initialText = '', speed = 50) => {
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  const typeText = (text) => {
    setIsTyping(true);
    setDisplayedText('');
    let currentIndex = 0;

    const interval = setInterval(() => {
      if (currentIndex < text.length) {
        setDisplayedText(text.slice(0, currentIndex + 1));
        currentIndex++;
      } else {
        clearInterval(interval);
        setIsTyping(false);
      }
    }, speed);

    return () => clearInterval(interval);
  };

  const clearText = () => {
    setDisplayedText('');
    setIsTyping(false);
  };

  useEffect(() => {
    if (initialText) {
      typeText(initialText);
    }
  }, [initialText]);

  return { displayedText, isTyping, typeText, clearText };
};

export const useCursor = (isActive = true) => {
  const [showCursor, setShowCursor] = useState(true);

  useEffect(() => {
    if (!isActive) {
      setShowCursor(false);
      return;
    }

    const interval = setInterval(() => {
      setShowCursor((prev) => !prev);
    }, 530);

    return () => clearInterval(interval);
  }, [isActive]);

  return showCursor ? '_' : '';
};

export default useTerminal;

