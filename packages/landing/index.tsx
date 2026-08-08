import React from 'react';
import ReactDOM from 'react-dom/client';
import './i18n'; // Initialize i18n
import App from './App';
import { initPostHog } from './services/posthog';

// Initialise PostHog as early as possible (before React mounts) so the
// first pageview is captured. The wrapper is a no-op when
// VITE_POSTHOG_PROJECT_KEY is unset.
initPostHog();

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