import React from 'react';
import ReactDOM from 'react-dom/client';
import './src/index.css';
import App from './App';
import * as serviceWorker from './src/serviceWorker';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error("Could not find root element to mount to");
}

const root = ReactDOM.createRoot(rootElement);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Register service worker in production
if (import.meta.env.PROD) {
  serviceWorker.register();
} else {
  // Unregister service worker in development
  serviceWorker.unregister();
}