import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import NavBar from './components/NavBar';
import Home from './pages/Home';
import Protect from './pages/Protect';
import Policies from './pages/Policies';
import Evidence from './pages/Evidence';
import Audit from './pages/Audit';

const NotFound: React.FC = () => (
  <div className="alert alert-warning" role="alert">
    <h5 className="alert-heading">Page not found</h5>
    <p className="mb-0">The page you are looking for does not exist.</p>
  </div>
);

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <NavBar />
      <main className="container my-4">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/protect" element={<Protect />} />
          <Route path="/policies" element={<Policies />} />
          <Route path="/evidence" element={<Evidence />} />
          <Route path="/audit" element={<Audit />} />
          <Route path="/home" element={<Navigate to="/" replace />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
};

export default App;
