import React, { useState, useEffect, useRef } from 'react';
import '../styles/components.css';
import '../styles/animations.css';

const CommandLine = ({ onCommand, prompt = 'user@mainframe:~$', className = '' }) => {
  const [input, setInput] = useState('');
  const [history, setHistory] = useState([]);
  const inputRef = useRef(null);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      const command = input.trim();
      if (command) {
        setHistory([...history, { command, timestamp: new Date() }]);
        if (onCommand) {
          onCommand(command);
        }
        setInput('');
      }
    }
  };

  return (
    <div className={`command-line ${className}`}>
      <div className="command-history">
        {history.map((item, idx) => (
          <div key={idx} className="command-entry">
            <span className="prompt">{prompt}</span>
            <span className="command">{item.command}</span>
          </div>
        ))}
      </div>
      <div className="command-input-wrapper">
        <span className="prompt">{prompt}</span>
        <input
          ref={inputRef}
          type="text"
          className="command-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          autoFocus
        />
        <span className="cursor"></span>
      </div>
    </div>
  );
};

export default CommandLine;

