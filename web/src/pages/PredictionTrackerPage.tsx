import React from 'react';
import { PageShell } from '../components/PageShell';
import { ListChecks } from 'lucide-react';

export const PredictionTrackerPage: React.FC = () => {
  return (
    <PageShell
      title="Prediction Tracker"
      subtitle="Zero-login browser localStorage verification, scoring calibration, and 2026 replay."
      badgeText="Holdout Forecasts Ready"
      description="Evaluates user and model forecast quality without requiring accounts or logins. Uses standard Brier score formulation with optional outcome reconciliation."
      plannedFeatures={[
        "Local history table of user forecasts stored safely in browser localStorage",
        "Outcome reconciliation modal (Record actual wickets/runs to compute Brier scores)",
        "Model Brier Score vs Constant Rate Reference calibration comparison cards",
        "2026 Holdout Season Historical Replay mode (73 matches, 2,581 wicket checkpoints)"
      ]}
      icon={ListChecks}
    />
  );
};
