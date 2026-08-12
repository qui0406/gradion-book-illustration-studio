import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Auth from './pages/Auth';
import ProjectList from './pages/ProjectList';
import NewProject from './pages/NewProject';
import ProjectDetail from './pages/ProjectDetail';
import './index.css';

function RequireAuth({ children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/auth" replace />;
  return children;
}

function AppRoutes() {
  const { user } = useAuth();
  return (
    <Routes>
      <Route path="/auth" element={user ? <Navigate to="/" replace /> : <Auth />} />
      <Route path="/" element={<RequireAuth><ProjectList /></RequireAuth>} />
      <Route path="/projects/new" element={<RequireAuth><NewProject /></RequireAuth>} />
      <Route path="/projects/:id" element={<RequireAuth><ProjectDetail /></RequireAuth>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
