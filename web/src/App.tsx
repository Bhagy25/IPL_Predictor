import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';

// Each route is its own chunk, loaded the first time it is visited
const IPLOverviewPage = lazy(() => import('./pages/IPLOverviewPage').then((m) => ({ default: m.IPLOverviewPage })));
const TeamAnalysisPage = lazy(() => import('./pages/TeamAnalysisPage').then((m) => ({ default: m.TeamAnalysisPage })));
const PlayerExplorerPage = lazy(() => import('./pages/PlayerExplorerPage').then((m) => ({ default: m.PlayerExplorerPage })));
const StatisticsEDAPage = lazy(() => import('./pages/StatisticsEDAPage').then((m) => ({ default: m.StatisticsEDAPage })));
const PredictionArenaPage = lazy(() => import('./pages/PredictionArenaPage').then((m) => ({ default: m.PredictionArenaPage })));
const PredictionTrackerPage = lazy(() => import('./pages/PredictionTrackerPage').then((m) => ({ default: m.PredictionTrackerPage })));

/** Shown while a route's chunk downloads: the same spinner and text the pages use for their own loading states. */
const RouteLoading: React.FC = () => (
  <div className="max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-16">
    <p role="status" className="text-sm text-[#B9B9B3] flex items-center gap-2">
      <Loader2 className="w-4 h-4 animate-spin text-[#D9B15F]" aria-hidden="true" /> Loading page…
    </p>
  </div>
);

export const App: React.FC = () => {
  return (
    // Opt in to the React Router v7 behaviour named by its future-flag warnings
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <div className="min-h-screen flex flex-col bg-[#070708] text-[#F6F6F3]">
        {/* Sticky Header with 6 Nav Routes */}
        <Navbar />

        {/* Dynamic Route Content */}
        <main className="flex-grow">
          <Suspense fallback={<RouteLoading />}>
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
          </Suspense>
        </main>

        {/* Global Footer */}
        <Footer />
      </div>
    </BrowserRouter>
  );
};

export default App;
