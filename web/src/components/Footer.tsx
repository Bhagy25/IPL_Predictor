import React, { useEffect, useState } from 'react';
import { fetchHealth, HealthResponse } from '../api/overview';

// Re-check now and then so the status follows the backend starting or stopping
const RECHECK_MS = 60_000;

export const Footer: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [reachable, setReachable] = useState<boolean | null>(null);

  useEffect(() => {
    let ctl = new AbortController();
    const check = () => {
      ctl.abort();
      ctl = new AbortController();
      fetchHealth(ctl.signal)
        .then((h) => { setHealth(h); setReachable(true); })
        .catch((e: Error) => { if (e.name !== 'AbortError') { setHealth(null); setReachable(false); } });
    };
    check();
    const timer = window.setInterval(check, RECHECK_MS);
    return () => { window.clearInterval(timer); ctl.abort(); };
  }, []);

  const archive = health?.archive;
  const status = reachable === null ? 'checking…' : !reachable ? 'unavailable' : health?.status === 'healthy' ? 'connected' : 'connected (degraded)';
  const dot = reachable === null ? 'bg-[#8E8E88]' : !reachable ? 'bg-red-400' : health?.status === 'healthy' ? 'bg-emerald-400' : 'bg-[#D9B15F]';

  return (
    <footer className="w-full bg-[#070708] border-t border-white/[0.08] mt-16 sm:mt-24">
      <div className="max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Left Side */}
        <div className="space-y-1 text-center sm:text-left">
          <div className="text-lg font-bold text-[#F6F6F3] flex items-center justify-center sm:justify-start gap-1">
            Cricket<span className="text-[#D9B15F]">Lens</span>
          </div>
          {/* Span and status come from /api/health; nothing here is typed in */}
          <p className="text-xs text-[#B9B9B3]/70" role="status">
            Historical archive &middot; Cricsheet ball-by-ball data
            {archive ? <> &middot; {archive.first_season}–{archive.last_season}</> : null}
            {' '}&middot;{' '}
            <span className="inline-flex items-center gap-1.5">
              API: <span className={`w-1.5 h-1.5 rounded-full inline-block ${dot}`} aria-hidden="true" /> {status}
            </span>
          </p>
        </div>

        {/* Right Side */}
        <div className="text-xs text-[#B9B9B3]/60 font-medium tracking-wide">
          IPL historical analytics &middot; College EDA &amp; ML Project
        </div>
      </div>
    </footer>
  );
};
