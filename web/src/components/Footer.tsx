import React, { useEffect, useState } from 'react';
import { fetchHealth, HealthResponse } from '../api/overview';

export const Footer: React.FC = () => {
  const [archive, setArchive] = useState<HealthResponse['archive']>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal)
      .then((health) => setArchive(health.archive))
      .catch(() => { if (!controller.signal.aborted) setArchive(null); });
    return () => controller.abort();
  }, []);

  return (
    <footer className="w-full bg-[#070708] border-t border-white/[0.08] mt-16 sm:mt-24">
      <div className="max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Left Side */}
        <div className="space-y-1 text-center sm:text-left">
          <div className="text-lg font-bold text-[#F6F6F3] flex items-center justify-center sm:justify-start gap-1">
            Cricket<span className="text-[#D9B15F]">Lens</span>
          </div>
          <p className="text-xs text-[#B9B9B3]/70">
            IPL archive{archive && <> &middot; {archive.first_season}–{archive.last_season}</>}
          </p>
        </div>

        {/* Right Side */}
        <div className="text-xs text-[#9A9A94] font-medium tracking-wide">
          Cricsheet ball-by-ball data
        </div>
      </div>
    </footer>
  );
};
