import React from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider, useAppContext } from './src/context/AppContext';
import MacMenuBar from './src/components/retroui/MacMenuBar';
import Dock from './src/components/retroui/Dock';
import Landing from './src/pages/Landing';
import Dashboard from './src/pages/Dashboard';
import LiveTracking from './src/pages/LiveTracking';
import Recommendations from './src/pages/Recommendations';
import News from './src/pages/News';

const ProtectedRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const { isAuthenticated } = useAppContext();
  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  return children;
};

const AppRoutes = () => {
    const { isAuthenticated } = useAppContext();

    return (
        <div className="min-h-screen pt-[60px] md:pt-10 font-sans text-retro-text relative">
          <MacMenuBar />
          
          <div className="relative z-10">
            <Routes>
                <Route path="/" element={isAuthenticated ? <Navigate to="/dashboard" /> : <Landing />} />
                <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
                <Route path="/live" element={<ProtectedRoute><LiveTracking /></ProtectedRoute>} />
                <Route path="/recommendations" element={<ProtectedRoute><Recommendations /></ProtectedRoute>} />
                <Route path="/news" element={<ProtectedRoute><News /></ProtectedRoute>} />
                <Route path="*" element={<Navigate to="/" />} />
            </Routes>
          </div>

          {isAuthenticated && <div className="hidden md:block"><Dock /></div>}
          
          {/* Background scanline effect */}
          <div className="fixed inset-0 pointer-events-none z-50 opacity-[0.03] bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[length:100%_2px,3px_100%]"></div>
        </div>
    )
}

function App() {
  return (
    <AppProvider>
      <HashRouter>
        <AppRoutes />
      </HashRouter>
    </AppProvider>
  );
}

export default App;