import React from 'react';
import { Database, ShieldAlert, Sparkles } from 'lucide-react';

interface PageShellProps {
  title: string;
  subtitle: string;
  badgeText?: string;
  description: string;
  plannedFeatures: string[];
  icon: React.ElementType;
}

export const PageShell: React.FC<PageShellProps> = ({
  title,
  subtitle,
  badgeText = 'Awaiting Python backend integration',
  description,
  plannedFeatures,
  icon: Icon,
}) => {
  return (
    <div className="max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8 animate-fadeIn">
      {/* Route Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-white/[0.08]">
        <div>
          <div className="flex items-center gap-3">
            <span className="w-1.5 h-6 bg-[#D9B15F] rounded-full inline-block" />
            <div className="w-9 h-9 rounded-xl bg-[#151619] border border-[#D9B15F]/30 flex items-center justify-center text-[#D9B15F]">
              <Icon className="w-5 h-5" />
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#F6F6F3]">
              {title}
            </h1>
          </div>
          <p className="text-sm text-[#B9B9B3] mt-2 ml-4 sm:ml-5">
            {subtitle}
          </p>
        </div>

        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#151619] border border-[#D9B15F]/30 text-xs font-medium text-[#D9B15F] self-start sm:self-center">
          <span className="w-2 h-2 rounded-full bg-[#D9B15F] animate-pulse" />
          <span>{badgeText}</span>
        </div>
      </div>

      {/* Notice Banner */}
      <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-4 sm:p-5 flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-[#D9B15F] flex-shrink-0 mt-0.5" />
        <div className="text-xs sm:text-sm text-[#B9B9B3]">
          <strong className="text-[#F6F6F3] font-semibold">Backend Connection Pending: </strong>
          This functional page shell is structurally integrated and ready for verified data models. No synthetic or invented numbers are shown.
        </div>
      </div>

      {/* Main Container Card */}
      <div className="bg-[#151619] border border-white/[0.08] rounded-2xl p-6 sm:p-8 space-y-6">
        <div>
          <h2 className="text-lg font-bold text-[#F6F6F3] flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-[#D9B15F]" />
            Feature Scope &amp; Implementation Plan
          </h2>
          <p className="text-xs sm:text-sm text-[#B9B9B3] mt-1">
            {description}
          </p>
        </div>

        {/* Planned Features List */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
          {plannedFeatures.map((feat, index) => (
            <div 
              key={index}
              className="bg-[#0D0E10] border border-white/[0.06] rounded-xl p-4 flex items-start gap-3"
            >
              <div className="w-6 h-6 rounded-lg bg-black/60 border border-[#D9B15F]/25 flex items-center justify-center text-[#D9B15F] text-xs font-mono font-bold flex-shrink-0 mt-0.5">
                {index + 1}
              </div>
              <div>
                <p className="text-xs sm:text-sm font-medium text-[#F6F6F3]">
                  {feat}
                </p>
                <p className="text-[11px] text-[#B9B9B3]/70 mt-0.5">
                  Analytical logic audited &amp; verified in Stage 1–3 Python modules.
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Empty State Callout */}
        <div className="border border-dashed border-white/[0.1] rounded-xl p-8 flex flex-col items-center justify-center text-center space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-[#0D0E10] border border-[#D9B15F]/30 flex items-center justify-center text-[#D9B15F] shadow-gold-pill">
            <Database className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-sm sm:text-base font-semibold text-[#F6F6F3]">
              Awaiting Stage 4/5 Analytical Pipeline Integration
            </h3>
            <p className="text-xs text-[#B9B9B3]/75 max-w-md mx-auto mt-1">
              Data endpoints from FastAPI will populate this view without modifying existing Python model weights or re-training.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
