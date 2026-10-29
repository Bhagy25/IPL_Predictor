import React, { useState } from 'react';
import { Loader2, Database, AlertTriangle, RefreshCw } from 'lucide-react';

export const ComponentStatesShowcase: React.FC = () => {
  const [retrying, setRetrying] = useState(false);

  const handleRetry = () => {
    setRetrying(true);
    setTimeout(() => setRetrying(false), 1200);
  };

  return (
    <div className="space-y-4 pt-4 border-t border-white/[0.06]">
      {/* Header */}
      <div className="flex items-center justify-between text-xs text-[#B9B9B3]">
        <span className="font-semibold uppercase tracking-wider text-[#F6F6F3]/80">
          Homepage component states
        </span>
        <span className="font-mono text-[11px] text-[#D9B15F]/80">
          QA / Diagnostics
        </span>
      </div>

      {/* 3 State Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        {/* State 1: Loading */}
        <div className="bg-[#151619] border border-white/[0.08] rounded-2xl p-5 space-y-3">
          <div className="flex items-center gap-2 text-xs font-medium text-[#D9B15F]">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-[#D9B15F]" />
            <span>Loading</span>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-[#F6F6F3]">
              Fetching historical data
            </h4>
            <p className="text-xs text-[#B9B9B3]/80 mt-0.5">
              Waiting for the analytical backend to respond...
            </p>
          </div>
          {/* Skeleton Pulse Lines */}
          <div className="pt-2 space-y-2">
            <div className="h-2 w-3/4 bg-white/[0.08] rounded animate-pulse" />
            <div className="h-2 w-1/2 bg-white/[0.05] rounded animate-pulse" />
          </div>
        </div>

        {/* State 2: Missing data */}
        <div className="bg-[#151619] border border-white/[0.08] rounded-2xl p-5 space-y-3">
          <div className="flex items-center gap-2 text-xs font-medium text-[#D9B15F]">
            <Database className="w-3.5 h-3.5 text-[#D9B15F]" />
            <span>Missing data</span>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-[#F6F6F3]">
              No data available
            </h4>
            <p className="text-xs text-[#B9B9B3]/80 mt-0.5">
              This view stays empty until verified records are returned.
            </p>
          </div>
          <div className="pt-1">
            <span className="inline-flex items-center text-[10px] text-[#D9B15F]/90 bg-[#D9B15F]/10 px-2 py-0.5 rounded-full border border-[#D9B15F]/20">
              Awaiting data
            </span>
          </div>
        </div>

        {/* State 3: Failed API request */}
        <div className="bg-[#151619] border border-white/[0.08] rounded-2xl p-5 space-y-3">
          <div className="flex items-center gap-2 text-xs font-medium text-red-400">
            <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
            <span>Failed API request</span>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-[#F6F6F3]">
              Unable to fetch data
            </h4>
            <p className="text-xs text-[#B9B9B3]/80 mt-0.5">
              The request failed. Retry to request the dataset again.
            </p>
          </div>
          <div className="pt-1">
            <button
              type="button"
              onClick={handleRetry}
              disabled={retrying}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-[#151619] hover:bg-white/[0.08] text-[#D9B15F] border border-[#D9B15F]/40 transition-colors focus:outline-none focus:ring-2 focus:ring-[#D9B15F]"
            >
              <RefreshCw className={`w-3 h-3 ${retrying ? 'animate-spin' : ''}`} />
              <span>{retrying ? 'Retrying...' : 'Retry request'}</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
