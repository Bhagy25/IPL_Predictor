import React, { useEffect, useState, useCallback } from 'react';
import { HeroCollage } from '../components/HeroCollage';
import { KPICards } from '../components/KPICards';
import { PerspectiveCharts } from '../components/PerspectiveCharts';
import { TeamRecordsTable } from '../components/TeamRecordsTable';
import { Database, Calendar, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { OverviewSummaryResponse, OverviewChartsResponse } from '../types';
import { fetchOverviewSummary, fetchOverviewCharts } from '../api/overview';

export const IPLOverviewPage: React.FC = () => {
  const [summary, setSummary] = useState<OverviewSummaryResponse | null>(null);
  const [charts, setCharts] = useState<OverviewChartsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, chartRes] = await Promise.all([
        fetchOverviewSummary(),
        fetchOverviewCharts(),
      ]);
      setSummary(sumRes);
      setCharts(chartRes);
    } catch (err: any) {
      console.error('Failed to load IPL overview data:', err);
      setError(err?.message || 'Unable to connect to Python analytical backend');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadData();
    return () => controller.abort();
  }, [loadData]);

  const isConnected = !loading && !error && summary !== null;

  // Archive line built from the API: matches, seasons, deliveries and runs
  const metric = (id: string) => summary?.metrics.find((m) => m.id === id)?.value ?? '—';
  const archiveLine = summary
    ? `${metric('matches')} matches · ${summary.coverage.seasons_count} seasons (${summary.coverage.seasons_span}) · ` +
      `${metric('deliveries')} recorded deliveries · ${metric('runs')} team runs verified.`
    : '';

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
                A historical view of the Indian Premier League. Every season, every innings, in perspective.
              </p>
            </div>

            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#151619] border border-[#D9B15F]/30 text-xs font-medium text-[#D9B15F] self-start sm:self-center shadow-gold-pill">
              <Calendar className="w-3.5 h-3.5 text-[#D9B15F]" />
              <span>Historical dashboard</span>
            </div>
          </div>

          {/* Status Alert Banner */}
          {loading ? (
            <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-4 sm:p-5 flex items-center justify-between gap-3 shadow-sm animate-pulse">
              <div className="flex items-center gap-3">
                <Database className="w-5 h-5 text-[#D9B15F] flex-shrink-0 animate-spin" />
                <div>
                  <p className="text-xs sm:text-sm font-semibold text-[#F6F6F3]">
                    Connecting to Python analytical backend...
                  </p>
                  <p className="text-xs text-[#B9B9B3] mt-0.5">
                    Fetching verified metrics, seasonal distributions, and franchise records.
                  </p>
                </div>
              </div>
              <span className="inline-flex items-center px-3 py-1 rounded-full text-[11px] font-semibold tracking-wider uppercase bg-black/50 text-[#D9B15F] border border-[#D9B15F]/30">
                Connecting
              </span>
            </div>
          ) : error ? (
            <div className="bg-[#1C1517] border border-red-500/30 rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs sm:text-sm font-semibold text-red-200">
                    Analytical backend unreachable ({error})
                  </p>
                  <p className="text-xs text-red-300/75 mt-0.5">
                    FastAPI server on 127.0.0.1:8000 is not responding. Please ensure the backend is running.
                  </p>
                </div>
              </div>
              <button
                onClick={loadData}
                className="self-start sm:self-center inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-[#2A1B1E] hover:bg-[#3A2227] text-red-200 border border-red-500/40 transition-colors cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retry connection</span>
              </button>
            </div>
          ) : isConnected ? (
            <div className="bg-[#151619] border border-[#D9B15F]/35 rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-[#D9B15F] flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs sm:text-sm font-semibold text-[#F6F6F3]">
                    Backend connected &middot; Verified IPL historical archive
                  </p>
                  <p className="text-xs text-[#B9B9B3] mt-0.5">
                    {archiveLine}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2.5 self-start sm:self-center">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold tracking-wider uppercase bg-[#0D0E10] text-[#D9B15F] border border-[#D9B15F]/40 shadow-gold-pill">
                  <span className="w-2 h-2 rounded-full bg-[#D9B15F]" />
                  Historical archive connected &middot; Port 8000
                </span>
              </div>
            </div>
          ) : null}
        </div>

        {/* 3. 8 KPI Metric Cards */}
        <section aria-label="IPL Key Performance Indicators">
          <KPICards metrics={summary?.metrics} loading={loading} />
        </section>

        {/* 4. Perspective Charts */}
        <section aria-label="The IPL in Perspective Charts">
          <PerspectiveCharts chartsData={charts} loading={loading} />
        </section>

        {/* 5. Team Records Table */}
        <section aria-label="Verified Team Records">
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
