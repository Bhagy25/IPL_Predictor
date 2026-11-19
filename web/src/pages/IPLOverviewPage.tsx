import React, { useEffect, useState, useCallback } from 'react';
import { HeroCollage } from '../components/HeroCollage';
import { KPICards } from '../components/KPICards';
import { PerspectiveCharts } from '../components/PerspectiveCharts';
import { TeamRecordsTable } from '../components/TeamRecordsTable';
import { Calendar, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { OverviewSummaryResponse, OverviewChartsResponse } from '../types';
import { fetchOverviewSummary, fetchOverviewCharts } from '../api/overview';

export const IPLOverviewPage: React.FC = () => {
  const [summary, setSummary] = useState<OverviewSummaryResponse | null>(null);
  const [charts, setCharts] = useState<OverviewChartsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState(false);
  const [reload, setReload] = useState(0);

  const loadData = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(false);
    try {
      const [sumRes, chartRes] = await Promise.all([
        fetchOverviewSummary(signal),
        fetchOverviewCharts(signal),
      ]);
      setSummary(sumRes);
      setCharts(chartRes);
    } catch (err) {
      // Requests cancelled because the page was left are not failures
      if (signal?.aborted) return;
      console.error('Failed to load IPL overview data:', err);
      setError(true);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadData(controller.signal);
    return () => controller.abort();
  }, [loadData, reload]);

  return (
    <div className="space-y-12 sm:space-y-16">
      {/* 1. Cinematic Hero with Stadium, Trophy & Players Collage */}
      <HeroCollage />

      {/* 2. Main Overview Content Container */}
      <div className="max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-8 space-y-12 sm:space-y-16">
        
        {/* Section Header */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2">
            <div>
              <div className="flex items-center gap-3">
                <span className="w-1.5 h-6 bg-[#D9B15F] rounded-full inline-block" />
                <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#F6F6F3]">
                  IPL Overview
                </h2>
              </div>
              <p className="text-xs sm:text-sm text-[#B9B9B3] mt-1 ml-4 sm:ml-5">
                Season by season scoring, match results and franchise records from the IPL archive.
              </p>
            </div>

            {summary && (
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#151619] border border-[#D9B15F]/30 text-xs font-medium text-[#D9B15F] self-start sm:self-center shadow-gold-pill">
                <Calendar className="w-3.5 h-3.5 text-[#D9B15F]" aria-hidden="true" />
                <span>{summary.coverage.seasons_span}</span>
              </div>
            )}
          </div>

          {/* Status Alert Banner */}
          {loading ? (
            <div role="status" className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-4 sm:p-5 flex items-center gap-3 shadow-sm">
              <Loader2 className="w-5 h-5 text-[#D9B15F] flex-shrink-0 animate-spin" aria-hidden="true" />
              <p className="text-xs sm:text-sm font-semibold text-[#F6F6F3]">Loading IPL statistics…</p>
            </div>
          ) : error ? (
            <div className="bg-[#1C1517] border border-red-500/30 rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
              <div role="alert" className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
                <p className="text-xs sm:text-sm font-semibold text-red-200">Couldn’t load IPL statistics.</p>
              </div>
              <button
                type="button"
                onClick={() => setReload((n) => n + 1)}
                className="self-start sm:self-center inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-[#2A1B1E] hover:bg-[#3A2227] text-red-200 border border-red-500/40 transition-colors cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Retry</span>
              </button>
            </div>
          ) : null}
        </div>

        {/* 3. 8 KPI Metric Cards */}
        <section aria-label="IPL archive statistics">
          <KPICards metrics={summary?.metrics} loading={loading} />
        </section>

        {/* 4. Perspective Charts */}
        <section aria-label="The IPL in Perspective Charts">
          <PerspectiveCharts chartsData={charts} loading={loading} />
        </section>

        {/* 5. Team Records Table */}
        <section aria-label="IPL Franchise Records">
          <TeamRecordsTable
            records={charts?.team_records}
            window={charts?.team_records_window}
            champions={charts?.champions}
            loading={loading}
          />
        </section>

        {/* 6. QA Component States Showcase (Hidden from standard view as per Stage 4.3A) */}
        {/* <section aria-label="Component States Showcase">
          <ComponentStatesShowcase />
        </section> */}

      </div>
    </div>
  );
};
