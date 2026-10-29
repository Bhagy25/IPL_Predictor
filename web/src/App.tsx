import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { IPLOverviewPage } from './pages/IPLOverviewPage';
import { TeamAnalysisPage } from './pages/TeamAnalysisPage';
import { PlayerExplorerPage } from './pages/PlayerExplorerPage';
import { StatisticsEDAPage } from './pages/StatisticsEDAPage';
import { PredictionArenaPage } from './pages/PredictionArenaPage';
import { PredictionTrackerPage } from './pages/PredictionTrackerPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col bg-[#070708] text-[#F6F6F3]">
        {/* Sticky Header with 6 Nav Routes */}
        <Navbar />

        {/* Dynamic Route Content */}
        <main className="flex-grow">
          <Routes>
            <Route path="/" element={<IPLOverviewPage />} />
            <Route path="/overview" element={<Navigate to="/" replace />} />
            <Route path="/teams" element={<TeamAnalysisPage />} />
            <Route path="/players" element={<PlayerExplorerPage />} />
            <Route path="/eda" element={<StatisticsEDAPage />} />
            <Route path="/predict" element={<PredictionArenaPage />} />
            <Route path="/tracker" element={<PredictionTrackerPage />} />
            {/* Fallback to home */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>

        {/* Global Footer */}
        <Footer />
      </div>
    </BrowserRouter>
  );
};

export default App;
