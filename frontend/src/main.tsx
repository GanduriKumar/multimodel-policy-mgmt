import React from 'react';
import ReactDOM from 'react-dom/client';

// Bootstrap CSS (global)
import 'bootstrap/dist/css/bootstrap.min.css';

// Optional: your global styles
import './index.css';

import App from './App';

// Mount the React app
const rootEl = document.getElementById('root');
if (!rootEl) {
  throw new Error('Root element #root not found in index.html');
}

ReactDOM.createRoot(rootEl).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);