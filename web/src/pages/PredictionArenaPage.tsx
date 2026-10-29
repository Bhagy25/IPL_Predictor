import React from 'react';
import { PageShell } from '../components/PageShell';
import { Zap } from 'lucide-react';

export const PredictionArenaPage: React.FC = () => {
  return (
    <PageShell
      title="Prediction Arena"
      subtitle="Probabilistic ML inference: Next-Over Wicket Risk &amp; Batter Milestone Forecasting."
      badgeText="Two Trained Models Ready"
      description="Interactive inference engine connected to serialized deployment models (wicket_deployment_through_2026.joblib &amp; batter_deployment_through_2026.joblib). Manual scenario inputs only—no external live feeds."
      plannedFeatures={[
        "Next-Over Wicket Risk Predictor (Inputs: overs 1–19, runs, wickets, last over context, venue)",
        "Pre-Match Batter Milestone Predictor (Inputs: player, opponent, venue, date with strictly prior-date form)",
        "Mathematical guarantee enforcement: P(50+) <= P(30+) from single 3-class classifier",
        "Direct 'Save to Tracker' button with local browser state persistence"
      ]}
      icon={Zap}
    />
  );
};
