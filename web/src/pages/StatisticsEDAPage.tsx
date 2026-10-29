import React, { useEffect, useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  BarChart2,
  Table as TableIcon,
  Maximize2,
  X,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Loader2,
  TrendingUp,
  MapPin,
  Flame,
  Shield,
  Layers,
  Archive,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { EDAFigureItem, EDACatalogResponse, EDASummaryResponse, EDAFullHistoryResponse } from '../types';
import { fetchEDACatalog, fetchEDASummary, fetchEDAFullHistory } from '../api/eda';

export const StatisticsEDAPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = (searchParams.get('tab') as 'full_history' | 'research_archive') || 'full_history';

  // State
  const [activeTab, setActiveTab] = useState<'full_history' | 'research_archive'>(initialTab);
  const [fullHistory, setFullHistory] = useState<EDAFullHistoryResponse | null>(null);
  const [catalog, setCatalog] = useState<EDACatalogResponse | null>(null);
  const [summary, setSummary] = useState<EDASummaryResponse | null>(null);

  // Sub-tab for full history or archive view
  const [archiveSubView, setArchiveSubView] = useState<'gallery' | 'tables'>('gallery');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [selectedFigure, setSelectedFigure] = useState<EDAFigureItem | null>(null);
  
  // Loading and error states
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Load datasets
  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [histRes, catRes, sumRes] = await Promise.all([
        fetchEDAFullHistory(),
        fetchEDACatalog(),
        fetchEDASummary(),
      ]);
      setFullHistory(histRes);
      setCatalog(catRes);
      setSummary(sumRes);
    } catch (err: any) {
      setError(err?.message || 'Failed to load Statistics & EDA data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Filter figures by category
  const filteredFigures = useMemo(() => {
    if (!catalog) return [];
    if (selectedCategory === 'All') return catalog.figures;
    return catalog.figures.filter(f => f.category === selectedCategory);
  }, [catalog, selectedCategory]);

  const categories = useMemo(() => {
    if (!catalog) return ['All'];
    return ['All', ...catalog.categories];
  }, [catalog]);

  // Handle escape key to close modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSelectedFigure(null);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="space-y-10 sm:space-y-12 max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-16">
      
      {/* 1. Page Header */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#D9B15F]/20">
          <div>
            <div className="flex items-center gap-3">
              <span className="w-1.5 h-6 bg-[#D9B15F] rounded-full inline-block" />
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#F6F6F3]">
                Statistics &amp; EDA Lab
              </h1>
            </div>
            <p className="text-xs sm:text-sm text-[#B9B9B3] mt-1 ml-4 sm:ml-5">
              Comprehensive tournament-wide exploratory data analysis across all 19 IPL seasons (2008–2026) alongside the Stage 2 research archive.
            </p>
          </div>

          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#151619] border border-[#D9B15F]/30 text-xs font-medium text-[#D9B15F] self-start sm:self-center shadow-gold-pill">
            <Layers className="w-3.5 h-3.5 text-[#D9B15F]" />
            <span>19 Seasons &middot; 1,243 Matches &middot; 295,557 Balls</span>
          </div>
        </div>

        {error && (
          <div className="bg-[#1C1517] border border-red-500/30 rounded-2xl p-4 sm:p-5 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <p className="text-xs sm:text-sm font-semibold text-red-200">
                {error}
              </p>
            </div>
            <button
              onClick={loadData}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-[#2A1B1E] hover:bg-[#3A2227] text-red-200 border border-red-500/40"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          </div>
        )}
      </div>

      {/* 2. Top-Level Mode Navigation (Full History vs Stage 2 Research Archive) */}
      <section aria-label="EDA Primary Tabs" className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-3 sm:p-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="inline-flex rounded-xl bg-[#101114] p-1 border border-[#D9B15F]/20">
            <button
              onClick={() => {
                setActiveTab('full_history');
                setSearchParams({ tab: 'full_history' });
              }}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'full_history'
                  ? 'bg-[#D9B15F] text-[#0D0E10] shadow-sm'
                  : 'text-[#B9B9B3] hover:text-[#F6F6F3]'
              }`}
            >
              <BarChart2 className="w-3.5 h-3.5" />
              <span>Complete IPL History (2008–2026)</span>
            </button>

            <button
              onClick={() => {
                setActiveTab('research_archive');
                setSearchParams({ tab: 'research_archive' });
              }}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'research_archive'
                  ? 'bg-[#D9B15F] text-[#0D0E10] shadow-sm'
                  : 'text-[#B9B9B3] hover:text-[#F6F6F3]'
              }`}
            >
              <Archive className="w-3.5 h-3.5" />
              <span>Stage 2 Research Archive (2018–2025 Cohort)</span>
            </button>
          </div>

          <span className="text-xs text-[#8E8E88] font-mono px-2">
            {activeTab === 'full_history'
              ? 'Covering all 19 editions: 2008 through 2026'
              : 'Focused study used for ML feature engineering'}
          </span>
        </div>
      </section>

      {/* ================================================================= */}
      {/* TAB 1: COMPLETE IPL HISTORY (2008–2026) — 15 ANALYSIS AREAS */}
      {/* ================================================================= */}
      {activeTab === 'full_history' && (
        <div className="space-y-8">
          {loading ? (
            <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-16 text-center flex flex-col items-center justify-center gap-3 animate-pulse">
              <Loader2 className="w-8 h-8 text-[#D9B15F] animate-spin" />
              <p className="text-sm font-semibold text-[#F6F6F3]">Computing 19-season canonical metrics...</p>
            </div>
          ) : fullHistory && (
            <>
              {/* Section 1: Season Scoring Evolution & Matches */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                
                {/* Scoring Evolution Chart */}
                <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 sm:p-6 space-y-4">
                  <div className="flex items-center justify-between border-b border-[#D9B15F]/15 pb-3">
                    <div>
                      <h3 className="text-sm sm:text-base font-bold text-[#F6F6F3] flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-[#D9B15F]" />
                        Tournament Run Rate Evolution (2008–2026)
                      </h3>
                      <p className="text-xs text-[#B9B9B3] mt-0.5">Average runs scored per 6 legal deliveries by season</p>
                    </div>
                  </div>
                  
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={fullHistory.season_evolution} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#25262B" />
                        <XAxis dataKey="season" stroke="#8E8E88" tick={{ fontSize: 11 }} />
                        <YAxis stroke="#8E8E88" tick={{ fontSize: 11 }} domain={[7, 10]} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#151619', borderColor: '#D9B15F', borderRadius: '8px', fontSize: '12px' }}
                          formatter={(val: any) => [`${val} runs/over`, 'Tournament Run Rate']}
                        />
                        <Line type="monotone" dataKey="run_rate" stroke="#D9B15F" strokeWidth={2.5} dot={{ fill: '#D9B15F', r: 3 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* First Innings Mean Scoring Trends */}
                <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 sm:p-6 space-y-4">
                  <div className="flex items-center justify-between border-b border-[#D9B15F]/15 pb-3">
                    <div>
                      <h3 className="text-sm sm:text-base font-bold text-[#F6F6F3] flex items-center gap-2">
                        <Flame className="w-4 h-4 text-[#D9B15F]" />
                        First Innings Scoring Average (19 Seasons)
                      </h3>
                      <p className="text-xs text-[#B9B9B3] mt-0.5">Mean 1st innings total by edition (2008–2026)</p>
                    </div>
                  </div>

                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={fullHistory.first_innings_trends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#25262B" />
                        <XAxis dataKey="season" stroke="#8E8E88" tick={{ fontSize: 11 }} />
                        <YAxis stroke="#8E8E88" tick={{ fontSize: 11 }} domain={[130, 200]} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#151619', borderColor: '#D9B15F', borderRadius: '8px', fontSize: '12px' }}
                          formatter={(val: any) => [`${val} runs`, 'Mean 1st Innings']}
                        />
                        <Bar dataKey="mean_runs" fill="#C89B3C" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

              </div>

              {/* Section 2: Era-by-Era Phase Scoring Patterns */}
              <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 sm:p-6 space-y-4">
                <div className="flex items-center justify-between border-b border-[#D9B15F]/15 pb-3">
                  <div>
                    <h3 className="text-sm sm:text-base font-bold text-[#F6F6F3] flex items-center gap-2">
                      <Layers className="w-4 h-4 text-[#D9B15F]" />
                      Phase Scoring Efficiency Across Tournament Eras
                    </h3>
                    <p className="text-xs text-[#B9B9B3] mt-0.5">
                      Powerplay (overs 1–6), Middle (overs 7–16), and Death (overs 17–20) run rates across 5 historical eras
                    </p>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#101114] text-[#B9B9B3] uppercase font-bold tracking-wider border-b border-[#D9B15F]/20">
                      <tr>
                        <th className="py-2.5 px-3">Tournament Era</th>
                        <th className="py-2.5 px-3">Phase</th>
                        <th className="py-2.5 px-3 text-center">Total Runs</th>
                        <th className="py-2.5 px-3 text-center">Legal Balls</th>
                        <th className="py-2.5 px-3 text-center">Wickets Lost</th>
                        <th className="py-2.5 px-3 text-right">Run Rate (RPO)</th>
                        <th className="py-2.5 px-3 text-right">Wickets / Over</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#D9B15F]/10">
                      {fullHistory.era_phase_patterns.map((ep, idx) => (
                        <tr key={idx} className="hover:bg-[#1A1B1F]">
                          <td className="py-2 px-3 font-semibold text-[#F6F6F3]">{ep.era}</td>
                          <td className="py-2 px-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              ep.phase.startsWith('Powerplay')
                                ? 'bg-amber-950/50 text-amber-300 border border-amber-500/20'
                                : ep.phase.startsWith('Middle')
                                ? 'bg-blue-950/50 text-blue-300 border border-blue-500/20'
                                : 'bg-rose-950/50 text-rose-300 border border-rose-500/20'
                            }`}>
                              {ep.phase}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-center font-mono text-[#D9B15F]">{ep.runs.toLocaleString()}</td>
                          <td className="py-2 px-3 text-center text-[#B9B9B3]">{ep.legal_balls.toLocaleString()}</td>
                          <td className="py-2 px-3 text-center text-rose-300">{ep.wickets.toLocaleString()}</td>
                          <td className="py-2 px-3 text-right font-black text-[#F6F6F3]">{ep.run_rate}</td>
                          <td className="py-2 px-3 text-right font-mono text-[#B9B9B3]">{ep.wickets_per_six_balls}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Section 3: Boundary Evolution & Toss / Chasing */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                
                {/* Boundary Percentage Over Time */}
                <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 sm:p-6 space-y-4">
                  <div className="flex items-center justify-between border-b border-[#D9B15F]/15 pb-3">
                    <div>
                      <h3 className="text-sm sm:text-base font-bold text-[#F6F6F3] flex items-center gap-2">
                        <Flame className="w-4 h-4 text-[#D9B15F]" />
                        Boundary Run Contribution (%)
                      </h3>
                      <p className="text-xs text-[#B9B9B3] mt-0.5">Percentage of total runs scored strictly via 4s and 6s</p>
                    </div>
                  </div>

                  <div className="h-60 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={fullHistory.boundaries_by_season} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#25262B" />
                        <XAxis dataKey="season" stroke="#8E8E88" tick={{ fontSize: 11 }} />
                        <YAxis stroke="#8E8E88" tick={{ fontSize: 11 }} domain={[50, 68]} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#151619', borderColor: '#D9B15F', borderRadius: '8px', fontSize: '12px' }}
                          formatter={(val: any) => [`${val}%`, 'Boundary Runs %']}
                        />
                        <Line type="monotone" dataKey="boundary_run_pct" stroke="#F59E0B" strokeWidth={2.5} dot={{ fill: '#F59E0B', r: 3 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Toss Decisions & Chasing Outcomes */}
                <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 sm:p-6 space-y-4">
                  <div className="flex items-center justify-between border-b border-[#D9B15F]/15 pb-3">
                    <div>
                      <h3 className="text-sm sm:text-base font-bold text-[#F6F6F3] flex items-center gap-2">
                        <Shield className="w-4 h-4 text-[#D9B15F]" />
                        Toss Decisions &amp; Chasing Win Rates
                      </h3>
                      <p className="text-xs text-[#B9B9B3] mt-0.5">Evolution of chasing win % across 1,243 decided matches</p>
                    </div>
                  </div>

                  <div className="h-60 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={fullHistory.toss_and_chasing} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#25262B" />
                        <XAxis dataKey="season" stroke="#8E8E88" tick={{ fontSize: 11 }} />
                        <YAxis stroke="#8E8E88" tick={{ fontSize: 11 }} domain={[30, 70]} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#151619', borderColor: '#D9B15F', borderRadius: '8px', fontSize: '12px' }}
                          formatter={(val: any) => [`${val}%`, 'Chasing Win %']}
                        />
                        <Bar dataKey="chasing_win_pct" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

              </div>

              {/* Section 4: Venue First-Innings Par Scoring */}
              <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 sm:p-6 space-y-4">
                <div className="flex items-center justify-between border-b border-[#D9B15F]/15 pb-3">
                  <div>
                    <h3 className="text-sm sm:text-base font-bold text-[#F6F6F3] flex items-center gap-2">
                      <MapPin className="w-4 h-4 text-[#D9B15F]" />
                      Ground / Venue First-Innings Par Scoring (Minimum 10 Matches)
                    </h3>
                    <p className="text-xs text-[#B9B9B3] mt-0.5">
                      Empirical first-innings scoring benchmarks sorted from highest scoring to lowest
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {fullHistory.venue_par.slice(0, 12).map((vp, idx) => (
                    <div key={idx} className="bg-[#121316] border border-[#D9B15F]/10 rounded-xl p-3.5 space-y-1.5">
                      <div className="flex items-start justify-between gap-2">
                        <span className="text-xs font-bold text-[#F6F6F3] line-clamp-1">{vp.venue}</span>
                        <span className="text-[10px] text-[#B9B9B3] font-mono whitespace-nowrap">{vp.first_innings_count} inns</span>
                      </div>
                      <div className="flex items-center justify-between text-xs pt-1">
                        <span className="text-[#8E8E88]">Mean / Median:</span>
                        <span className="font-mono text-[#D9B15F] font-black">{vp.mean_runs} / {vp.median_runs}</span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-[#B9B9B3]">
                        <span>Range:</span>
                        <span className="font-mono">{vp.min_runs} to {vp.max_runs}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Section 5: All-Time Leaders (2008–2026) */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                
                {/* Top 10 All-Time Batters */}
                <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 space-y-3">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-[#D9B15F] flex items-center gap-2">
                    <Flame className="w-4 h-4 text-[#D9B15F]" />
                    All-Time Run Leaders (2008–2026)
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-[#101114] text-[#B9B9B3] uppercase font-bold tracking-wider border-b border-[#D9B15F]/20">
                        <tr>
                          <th className="py-2 px-3">#</th>
                          <th className="py-2 px-3">Batter</th>
                          <th className="py-2 px-3 text-center">Innings</th>
                          <th className="py-2 px-3 text-center">4s / 6s</th>
                          <th className="py-2 px-3 text-right">Runs</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#D9B15F]/10">
                        {fullHistory.top_all_time_batters.map((b, idx) => (
                          <tr key={idx} className="hover:bg-[#1A1B1F]">
                            <td className="py-2 px-3 text-[#8E8E88] font-mono">{idx + 1}</td>
                            <td className="py-2 px-3 font-extrabold text-[#F6F6F3]">{b.batter}</td>
                            <td className="py-2 px-3 text-center text-[#B9B9B3]">{b.innings}</td>
                            <td className="py-2 px-3 text-center text-[#B9B9B3]">{b.fours} / {b.sixes}</td>
                            <td className="py-2 px-3 text-right font-black text-[#D9B15F]">{b.runs.toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Top 10 All-Time Bowlers */}
                <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 space-y-3">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-2">
                    <Shield className="w-4 h-4 text-emerald-400" />
                    All-Time Wicket Leaders (2008–2026)
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-[#101114] text-[#B9B9B3] uppercase font-bold tracking-wider border-b border-[#D9B15F]/20">
                        <tr>
                          <th className="py-2 px-3">#</th>
                          <th className="py-2 px-3">Bowler</th>
                          <th className="py-2 px-3 text-center">Innings</th>
                          <th className="py-2 px-3 text-center">Economy</th>
                          <th className="py-2 px-3 text-right">Wickets</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#D9B15F]/10">
                        {fullHistory.top_all_time_bowlers.map((w, idx) => (
                          <tr key={idx} className="hover:bg-[#1A1B1F]">
                            <td className="py-2 px-3 text-[#8E8E88] font-mono">{idx + 1}</td>
                            <td className="py-2 px-3 font-extrabold text-[#F6F6F3]">{w.bowler}</td>
                            <td className="py-2 px-3 text-center text-[#B9B9B3]">{w.innings}</td>
                            <td className="py-2 px-3 text-center font-mono text-[#D9B15F]">{w.economy}</td>
                            <td className="py-2 px-3 text-right font-black text-emerald-400">{w.wickets}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

              </div>
            </>
          )}
        </div>
      )}

      {/* ================================================================= */}
      {/* TAB 2: STAGE 2 RESEARCH ARCHIVE (2018–2025 COHORT) */}
      {/* ================================================================= */}
      {activeTab === 'research_archive' && (
        <div className="space-y-6">
          
          {/* Explicit Research Disclosure Banner */}
          <div className="bg-[#121316] border border-[#D9B15F]/30 rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-xs font-bold uppercase text-[#D9B15F]">
                <Archive className="w-4 h-4 text-[#D9B15F]" />
                <span>Stage 2 Focused Research Archive</span>
              </div>
              <p className="text-xs text-[#B9B9B3] mt-1 max-w-2xl">
                These 20 analytical figures and statistical matrices represent the controlled exploratory study (2018–2025 cohort) conducted during Stage 2 to establish feature distributions, correlation structures, and model hypotheses for Stage 3 ML development.
              </p>
            </div>

            <div className="inline-flex rounded-lg bg-[#101114] p-1 border border-[#D9B15F]/20 self-start sm:self-center">
              <button
                onClick={() => setArchiveSubView('gallery')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold cursor-pointer ${
                  archiveSubView === 'gallery' ? 'bg-[#D9B15F] text-[#0D0E10]' : 'text-[#B9B9B3]'
                }`}
              >
                Gallery (20 Figures)
              </button>
              <button
                onClick={() => setArchiveSubView('tables')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold cursor-pointer ${
                  archiveSubView === 'tables' ? 'bg-[#D9B15F] text-[#0D0E10]' : 'text-[#B9B9B3]'
                }`}
              >
                Data Tables &amp; Audits
              </button>
            </div>
          </div>

          {archiveSubView === 'gallery' && (
            <div className="space-y-6">
              {/* Category Pills */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold text-[#8E8E88] uppercase tracking-wider mr-1">Category:</span>
                {categories.map(c => (
                  <button
                    key={c}
                    onClick={() => setSelectedCategory(c)}
                    className={`px-3 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                      selectedCategory === c
                        ? 'bg-[#D9B15F] text-[#0D0E10] shadow-sm'
                        : 'bg-[#151619] text-[#B9B9B3] hover:text-[#F6F6F3] border border-[#D9B15F]/15'
                    }`}
                  >
                    {c}
                  </button>
                ))}
              </div>

              {/* Gallery Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredFigures.map(fig => (
                  <div
                    key={fig.id}
                    className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl overflow-hidden flex flex-col hover:border-[#D9B15F]/50 transition-all shadow-sm"
                  >
                    <div
                      className="relative bg-[#0E0F12] border-b border-[#D9B15F]/15 aspect-[16/10] overflow-hidden group cursor-pointer"
                      onClick={() => setSelectedFigure(fig)}
                    >
                      <img
                        src={`/api/eda/figures/${fig.id}.png`}
                        alt={fig.title}
                        className="w-full h-full object-contain p-2 group-hover:scale-[1.02] transition-transform duration-300"
                      />
                      <button className="absolute top-2.5 right-2.5 p-1.5 rounded-lg bg-[#0E0F12]/80 text-[#D9B15F] opacity-0 group-hover:opacity-100 transition-opacity">
                        <Maximize2 className="w-4 h-4" />
                      </button>
                    </div>

                    <div className="p-4 sm:p-5 flex-1 flex flex-col justify-between space-y-3">
                      <div>
                        <div className="flex items-center justify-between text-[11px] text-[#B9B9B3] mb-1">
                          <span className="font-mono text-[#D9B15F] font-bold">Fig {fig.figure_num}</span>
                          <span className="px-2 py-0.5 rounded bg-[#101114] border border-[#D9B15F]/15 text-[10px]">
                            {fig.category}
                          </span>
                        </div>
                        <h4 className="text-sm font-bold text-[#F6F6F3] line-clamp-1">{fig.title}</h4>
                        <p className="text-xs text-[#B9B9B3] mt-1 line-clamp-2">{fig.description}</p>
                      </div>

                      <div className="pt-2 border-t border-[#D9B15F]/10 flex items-center justify-between text-[11px] text-[#8E8E88]">
                        <span>{fig.coverage_span}</span>
                        <span className="font-mono">{fig.sample_size}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {archiveSubView === 'tables' && summary && (
            <div className="space-y-6">
              {/* Correlation Matrix Table */}
              <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 space-y-3">
                <h4 className="text-sm font-bold text-[#F6F6F3] flex items-center gap-2">
                  <TableIcon className="w-4 h-4 text-[#D9B15F]" />
                  First-Innings Correlation Matrix (Pearson &amp; Spearman)
                </h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#101114] text-[#B9B9B3] uppercase font-bold tracking-wider border-b border-[#D9B15F]/20">
                      <tr>
                        <th className="py-2 px-3">Variable</th>
                        {summary.correlations.variables.map(v => (
                          <th key={v} className="py-2 px-3 text-right capitalize">{v}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#D9B15F]/10">
                      {summary.correlations.variables.map(rVar => (
                        <tr key={rVar} className="hover:bg-[#1A1B1F]">
                          <td className="py-2 px-3 font-semibold text-[#F6F6F3] capitalize">{rVar}</td>
                          {summary.correlations.variables.map(cVar => {
                            const val = summary.correlations.pearson[rVar]?.[cVar];
                            return (
                              <td key={cVar} className="py-2 px-3 text-right font-mono">
                                {val == null ? (
                                  <span className="text-[#B9B9B3]">—</span>
                                ) : (
                                  <span className={val > 0.4 ? 'text-emerald-400 font-bold' : val < -0.3 ? 'text-rose-400 font-bold' : 'text-[#B9B9B3]'}>
                                    {val.toFixed(2)}
                                  </span>
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Data Quality Missingness Audit */}
              <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 space-y-3">
                <h4 className="text-sm font-bold text-[#F6F6F3] flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#D9B15F]" />
                  Data Quality &amp; Feature Missingness Audit
                </h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#101114] text-[#B9B9B3] uppercase font-bold tracking-wider border-b border-[#D9B15F]/20">
                      <tr>
                        <th className="py-2 px-3">Feature Name</th>
                        <th className="py-2 px-3 text-center">Dataset Scope</th>
                        <th className="py-2 px-3 text-center">Missing Count</th>
                        <th className="py-2 px-3 text-right">Missingness %</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#D9B15F]/10">
                      {summary.missingness_audit.map((m, idx) => (
                        <tr key={idx} className="hover:bg-[#1A1B1F]">
                          <td className="py-2 px-3 font-mono text-[#F6F6F3]">{m.feature}</td>
                          <td className="py-2 px-3 text-center text-[#B9B9B3]">{m.scope}</td>
                          <td className="py-2 px-3 text-center font-mono">{m.missing_count}</td>
                          <td className="py-2 px-3 text-right font-bold text-emerald-400">{m.missing_pct}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

        </div>
      )}

      {/* 3. Modal Lightbox for Figure Inspection */}
      {selectedFigure && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
          <div className="relative bg-[#151619] border border-[#D9B15F]/40 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-4 shadow-2xl">
            <div className="flex items-start justify-between border-b border-[#D9B15F]/20 pb-3">
              <div>
                <span className="text-xs font-mono text-[#D9B15F] font-bold">Figure {selectedFigure.figure_num} &middot; {selectedFigure.category}</span>
                <h3 className="text-lg font-bold text-[#F6F6F3] mt-0.5">{selectedFigure.title}</h3>
              </div>
              <button
                onClick={() => setSelectedFigure(null)}
                className="p-1.5 rounded-lg bg-[#101114] text-[#B9B9B3] hover:text-[#F6F6F3] cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="bg-[#0E0F12] rounded-xl p-2 border border-[#D9B15F]/15">
              <img
                src={`/api/eda/figures/${selectedFigure.id}.png`}
                alt={selectedFigure.title}
                className="w-full h-auto max-h-[55vh] object-contain mx-auto"
              />
            </div>

            <div className="space-y-2 text-xs text-[#B9B9B3]">
              <p>{selectedFigure.description}</p>
              {selectedFigure.key_findings && (
                <ul className="list-disc list-inside space-y-1 text-[#F6F6F3] pt-1">
                  {selectedFigure.key_findings.map((f, idx) => (
                    <li key={idx}>{f}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
