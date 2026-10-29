import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Activity,
  AlertCircle,
  Archive,
  BarChart2,
  CheckCircle2,
  Crosshair,
  Flame,
  Layers,
  Link2,
  Loader2,
  MapPin,
  Maximize2,
  RefreshCw,
  RotateCcw,
  Shield,
  Sigma,
  SlidersHorizontal,
  Table as TableIcon,
  Target,
  TrendingUp,
  Trophy,
  X,
} from 'lucide-react';
import {
  EDAAnalysisResponse,
  EDACatalogResponse,
  EDAFigureItem,
  EDAFilterOptionsResponse,
  EDASummaryResponse,
} from '../types';
import { EDAQuery, fetchEDAAnalysis, fetchEDACatalog, fetchEDAFilters, fetchEDASummary } from '../api/eda';
import { ChartFrame, MinimumControl } from '../components/eda/ChartFrame';
import {
  AnomaliesView,
  BattingView,
  BowlingView,
  BoundariesView,
  CorrelationsView,
  DismissalsView,
  InningsOrderView,
  InningsScoresView,
  MatchesRunsView,
  PhasesView,
  ScoringTrendsView,
  TeamComparisonView,
  TossView,
  VenuesView,
} from '../components/eda/AreaViews';
import { PickedPlayer, PlayerComparison } from '../components/eda/PlayerComparison';
import { FOCUS_RING } from '../components/player/playerFormat';
import { fmtCount } from '../utils/format';

type Tab = 'full_history' | 'focused_studies';

const ICON = 'w-4 h-4 text-[#D9B15F]';
const SELECT = `bg-[#101114] border border-[#D9B15F]/30 rounded-lg px-2.5 py-1.5 text-xs text-[#F6F6F3] max-w-full min-w-0 ${FOCUS_RING}`;

const VENUE_MINIMUMS = [1, 3, 5, 10, 20].map((v) => ({ value: v, label: v === 1 ? 'Any' : `${v}+` }));
const BAT_MINIMUMS = [1, 6, 10, 20].map((v) => ({ value: v, label: `${v}+ ball${v === 1 ? '' : 's'}` }));
const BOWL_MINIMUMS = [1, 6, 12, 24].map((v) => ({ value: v, label: `${v}+ ball${v === 1 ? '' : 's'}` }));

const numberParam = (v: string | null): number | undefined => {
  if (v === null || v === '') return undefined;
  const n = Number(v);
  return Number.isInteger(n) ? n : undefined;
};

/** Filters live in the URL so a view can be shared and reloaded. */
const readQuery = (params: URLSearchParams): EDAQuery => ({
  season_from: numberParam(params.get('from')),
  season_to: numberParam(params.get('to')),
  team: params.get('team') || undefined,
  venue: params.get('venue') || undefined,
  venue_min_matches: numberParam(params.get('vmin')),
  bat_min_balls: numberParam(params.get('bmin')),
  bowl_min_balls: numberParam(params.get('wmin')),
});

const QUERY_PARAMS: Record<keyof EDAQuery, string> = {
  season_from: 'from',
  season_to: 'to',
  team: 'team',
  venue: 'venue',
  venue_min_matches: 'vmin',
  bat_min_balls: 'bmin',
  bowl_min_balls: 'wmin',
};

export const StatisticsEDAPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab: Tab = searchParams.get('tab') === 'focused_studies' ? 'focused_studies' : 'full_history';
  const query = useMemo(() => readQuery(searchParams), [searchParams]);
  const queryKey = JSON.stringify(query);

  const [options, setOptions] = useState<EDAFilterOptionsResponse | null>(null);
  const [analysis, setAnalysis] = useState<EDAAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const requestId = useRef(0);

  const picked: PickedPlayer[] = useMemo(() => {
    const ids = (searchParams.get('players') ?? '').split(',').filter(Boolean);
    const names = (searchParams.get('names') ?? '').split('|');
    return ids.map((id, i) => ({ id, name: names[i] || id }));
  }, [searchParams]);

  const update = useCallback((changes: Record<string, string | undefined>) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      Object.entries(changes).forEach(([k, v]) => (v === undefined || v === '' ? next.delete(k) : next.set(k, v)));
      return next;
    }, { replace: true });
  }, [setSearchParams]);

  const setQueryValue = (key: keyof EDAQuery, value: string | number | undefined) =>
    update({ [QUERY_PARAMS[key]]: value === undefined ? undefined : String(value) });

  const setPicked = (players: PickedPlayer[]) =>
    update({
      players: players.map((p) => p.id).join(',') || undefined,
      names: players.length ? players.map((p) => p.name).join('|') : undefined,
    });

  useEffect(() => {
    const controller = new AbortController();
    fetchEDAFilters(controller.signal).then(setOptions).catch(() => { /* the analysis request reports failures */ });
    return () => controller.abort();
  }, [reload]);

  // Every filter change is recomputed server-side; stale responses are ignored
  useEffect(() => {
    if (activeTab !== 'full_history') return;
    const controller = new AbortController();
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    fetchEDAAnalysis(query, controller.signal)
      .then((res) => { if (id === requestId.current) setAnalysis(res); })
      .catch((err) => {
        if (id !== requestId.current || controller.signal.aborted) return;
        setAnalysis(null);
        setError(err?.message || 'Failed to load the full-history analysis');
      })
      .finally(() => { if (id === requestId.current) setLoading(false); });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryKey, activeTab, reload]);

  const seasons = options?.seasons ?? [];
  const first = seasons[0];
  const last = seasons[seasons.length - 1];
  const filters = analysis?.filters;
  const areas = analysis?.areas;
  const totals = areas?.matches_runs.data?.totals;
  const filtered = Boolean(query.team || query.venue || (query.season_from && query.season_from !== first) || (query.season_to && query.season_to !== last));

  return (
    <div className="space-y-10 sm:space-y-12 max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-16">
      {/* 1. Page Header */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#D9B15F]/20">
          <div className="min-w-0">
            <div className="flex items-center gap-3">
              <span className="w-1.5 h-6 bg-[#D9B15F] rounded-full inline-block" />
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#F6F6F3]">
                Statistics &amp; EDA Lab
              </h1>
            </div>
            <p className="text-xs sm:text-sm text-[#B9B9B3] mt-1 ml-4 sm:ml-5">
              Filterable exploratory analysis of every IPL season{first ? ` (${first}–${last})` : ''}, recomputed from ball-by-ball data, alongside the Stage 2 research archive.
            </p>
          </div>

          {filters && totals && (
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#151619] border border-[#D9B15F]/30 text-xs font-medium text-[#D9B15F] self-start sm:self-center shadow-gold-pill max-w-full">
              <Layers className="w-3.5 h-3.5 text-[#D9B15F] flex-shrink-0" />
              <span>
                {areas?.matches_runs.coverage?.seasons.length ?? 0} seasons &middot; {fmtCount(totals.matches)} matches &middot; {fmtCount(totals.deliveries)} balls
              </span>
            </div>
          )}
        </div>
      </div>

      {/* 2. Mode navigation: live full history vs the static Stage 2 archive */}
      <section aria-label="EDA Primary Tabs" className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-3 sm:p-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="inline-flex flex-wrap rounded-xl bg-[#101114] p-1 border border-[#D9B15F]/20 max-w-full">
            {([
              ['full_history', <BarChart2 key="i" className="w-3.5 h-3.5" />, `Full-History Analysis${first ? ` (${first}–${last})` : ''}`],
              ['focused_studies', <Archive key="i" className="w-3.5 h-3.5" />, 'Focused Studies (Stage 2 research archive)'],
            ] as const).map(([id, icon, label]) => (
              <button
                key={id}
                type="button"
                aria-pressed={activeTab === id}
                onClick={() => update({ tab: id === 'full_history' ? undefined : id })}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${FOCUS_RING} ${
                  activeTab === id ? 'bg-[#D9B15F] text-[#0D0E10] shadow-sm' : 'text-[#B9B9B3] hover:text-[#F6F6F3]'
                }`}
              >
                {icon}
                <span>{label}</span>
              </button>
            ))}
          </div>
          <span className="text-xs text-[#8E8E88] font-mono px-2">
            {activeTab === 'full_history' ? 'Live: every chart recomputes for the filters' : 'Static research figures: not affected by filters'}
          </span>
        </div>
      </section>

      {activeTab === 'full_history' && (
        <div className="space-y-8">
          {/* Filter bar */}
          <section aria-label="Analysis filters" className="bg-[#151619] border border-[#D9B15F]/30 rounded-2xl p-4 sm:p-5 space-y-3 shadow-lg">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#D9B15F]">
              <SlidersHorizontal className="w-4 h-4" aria-hidden="true" />
              Filters
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-[auto_auto_minmax(0,1fr)_minmax(0,1.4fr)_auto] gap-3 items-end">
              <div className="flex flex-col gap-1 min-w-0">
                <label htmlFor="eda-from" className="text-[11px] text-[#B9B9B3] font-semibold">From season</label>
                <select id="eda-from" className={SELECT} value={query.season_from ?? first ?? ''} disabled={!options}
                  onChange={(e) => setQueryValue('season_from', Number(e.target.value) === first ? undefined : Number(e.target.value))}>
                  {seasons.map((s) => <option key={s} value={s} disabled={query.season_to !== undefined && s > query.season_to}>{s}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1 min-w-0">
                <label htmlFor="eda-to" className="text-[11px] text-[#B9B9B3] font-semibold">To season</label>
                <select id="eda-to" className={SELECT} value={query.season_to ?? last ?? ''} disabled={!options}
                  onChange={(e) => setQueryValue('season_to', Number(e.target.value) === last ? undefined : Number(e.target.value))}>
                  {seasons.map((s) => <option key={s} value={s} disabled={query.season_from !== undefined && s < query.season_from}>{s}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1 min-w-0">
                <label htmlFor="eda-team" className="text-[11px] text-[#B9B9B3] font-semibold">Team</label>
                <select id="eda-team" className={SELECT} value={query.team ?? ''} disabled={!options}
                  onChange={(e) => setQueryValue('team', e.target.value || undefined)}>
                  <option value="">All teams</option>
                  {options?.teams.map((t) => <option key={t.id} value={t.id}>{t.name} ({t.seasons_label})</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1 min-w-0">
                <label htmlFor="eda-venue" className="text-[11px] text-[#B9B9B3] font-semibold">Venue</label>
                <select id="eda-venue" className={SELECT} value={query.venue ?? ''} disabled={!options}
                  onChange={(e) => setQueryValue('venue', e.target.value || undefined)}>
                  <option value="">All venues</option>
                  {options?.venues.map((v) => <option key={v.name} value={v.name}>{v.name} ({fmtCount(v.matches)})</option>)}
                </select>
              </div>
              <button
                type="button"
                disabled={!filtered}
                onClick={() => update({ from: undefined, to: undefined, team: undefined, venue: undefined })}
                className={`col-span-2 lg:col-span-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border border-[#D9B15F]/30 text-[#D9B15F] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#D9B15F]/10 ${FOCUS_RING}`}
              >
                <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
                Reset filters
              </button>
            </div>
            <p className="text-[11px] text-[#B9B9B3] flex flex-wrap items-center gap-2" aria-live="polite">
              {loading ? (
                <><Loader2 className="w-3.5 h-3.5 animate-spin text-[#D9B15F]" aria-hidden="true" /> Recomputing…</>
              ) : filters ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#D9B15F]" aria-hidden="true" />
                  Showing <span className="font-semibold text-[#F6F6F3]">{filters.label}</span>
                  {filters.team && <span className="text-[#8E8E88]">({filters.team.name} played {filters.team.seasons_label})</span>}
                </>
              ) : null}
            </p>
          </section>

          {error && (
            <div role="alert" className="bg-[#1C1517] border border-red-500/30 rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
                <div>
                  <p className="text-xs sm:text-sm font-semibold text-red-200">Unable to load the full-history analysis</p>
                  <p className="text-xs text-red-300/80 mt-0.5">{error}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setReload((n) => n + 1)}
                className={`self-start sm:self-center inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-[#2A1B1E] hover:bg-[#3A2227] text-red-200 border border-red-500/40 ${FOCUS_RING}`}
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retry</span>
              </button>
            </div>
          )}

          {!analysis && loading && (
            <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-16 text-center flex flex-col items-center justify-center gap-3 animate-pulse">
              <Loader2 className="w-8 h-8 text-[#D9B15F] animate-spin" />
              <p className="text-sm font-semibold text-[#F6F6F3]">Computing full-history metrics…</p>
            </div>
          )}

          {analysis && filters && areas && (
            <div className={`space-y-6 transition-opacity ${loading ? 'opacity-60' : ''}`} aria-busy={loading}>
              <ChartFrame area={areas.matches_runs} filters={filters} number={1} icon={<Trophy className={ICON} aria-hidden="true" />}>
                {areas.matches_runs.data && <MatchesRunsView data={areas.matches_runs.data} />}
              </ChartFrame>
              <ChartFrame area={areas.scoring_trends} filters={filters} number={2} icon={<TrendingUp className={ICON} aria-hidden="true" />}>
                {areas.scoring_trends.data && <ScoringTrendsView data={areas.scoring_trends.data} />}
              </ChartFrame>
              <ChartFrame
                area={areas.batting_distribution}
                filters={filters}
                number={3}
                icon={<Flame className={ICON} aria-hidden="true" />}
                controls={<MinimumControl id="eda-bat-min" label="Strike rate: minimum balls faced" value={filters.bat_min_balls} options={BAT_MINIMUMS}
                  onChange={(v) => setQueryValue('bat_min_balls', v === 1 ? undefined : v)} />}
              >
                {areas.batting_distribution.data && <BattingView data={areas.batting_distribution.data} />}
              </ChartFrame>
              <ChartFrame
                area={areas.bowling}
                filters={filters}
                number={4}
                icon={<Shield className={ICON} aria-hidden="true" />}
                controls={<MinimumControl id="eda-bowl-min" label="Economy: minimum legal balls" value={filters.bowl_min_balls} options={BOWL_MINIMUMS}
                  onChange={(v) => setQueryValue('bowl_min_balls', v === 1 ? undefined : v)} />}
              >
                {areas.bowling.data && <BowlingView data={areas.bowling.data} />}
              </ChartFrame>
              <ChartFrame area={areas.phases} filters={filters} number={5} icon={<Layers className={ICON} aria-hidden="true" />}>
                {areas.phases.data && <PhasesView data={areas.phases.data} />}
              </ChartFrame>
              <ChartFrame area={areas.team_comparison} filters={filters} number={6} icon={<Trophy className={ICON} aria-hidden="true" />}>
                {areas.team_comparison.data && <TeamComparisonView data={areas.team_comparison.data} />}
              </ChartFrame>
              <PlayerComparison filters={filters} picked={picked} onPickedChange={setPicked} />
              <ChartFrame
                area={areas.venues}
                filters={filters}
                number={8}
                icon={<MapPin className={ICON} aria-hidden="true" />}
                controls={<MinimumControl id="eda-venue-min" label="Minimum matches" value={filters.venue_min_matches} options={VENUE_MINIMUMS}
                  onChange={(v) => setQueryValue('venue_min_matches', v === 1 ? undefined : v)} />}
              >
                {areas.venues.data && <VenuesView data={areas.venues.data} />}
              </ChartFrame>
              <ChartFrame area={areas.toss} filters={filters} number={9} icon={<Crosshair className={ICON} aria-hidden="true" />}>
                {areas.toss.data && <TossView data={areas.toss.data} />}
              </ChartFrame>
              <ChartFrame area={areas.innings_order} filters={filters} number={10} icon={<Target className={ICON} aria-hidden="true" />}>
                {areas.innings_order.data && <InningsOrderView data={areas.innings_order.data} teamName={filters.team?.name} />}
              </ChartFrame>
              <ChartFrame area={areas.innings_scores} filters={filters} number={11} icon={<BarChart2 className={ICON} aria-hidden="true" />}>
                {areas.innings_scores.data && <InningsScoresView data={areas.innings_scores.data} />}
              </ChartFrame>
              <ChartFrame area={areas.dismissals} filters={filters} number={12} icon={<Target className={ICON} aria-hidden="true" />}>
                {areas.dismissals.data && <DismissalsView data={areas.dismissals.data} />}
              </ChartFrame>
              <ChartFrame area={areas.boundaries} filters={filters} number={13} icon={<Activity className={ICON} aria-hidden="true" />}>
                {areas.boundaries.data && <BoundariesView data={areas.boundaries.data} />}
              </ChartFrame>
              <ChartFrame area={areas.anomalies} filters={filters} number={14} icon={<AlertCircle className={ICON} aria-hidden="true" />}>
                {areas.anomalies.data && <AnomaliesView data={areas.anomalies.data} />}
              </ChartFrame>
              <ChartFrame area={areas.correlations} filters={filters} number={15} icon={<Sigma className={ICON} aria-hidden="true" />}>
                {areas.correlations.data && <CorrelationsView data={areas.correlations.data} />}
              </ChartFrame>
            </div>
          )}
        </div>
      )}

      {activeTab === 'focused_studies' && <FocusedStudies />}
    </div>
  );
};

// ------------------------------------------------------------------ Focused Studies (static Stage 2 archive)

const FocusedStudies: React.FC = () => {
  const [catalog, setCatalog] = useState<EDACatalogResponse | null>(null);
  const [summary, setSummary] = useState<EDASummaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [subView, setSubView] = useState<'gallery' | 'tables'>('gallery');
  const [category, setCategory] = useState('All');
  const [selected, setSelected] = useState<EDAFigureItem | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    Promise.all([fetchEDACatalog(controller.signal), fetchEDASummary(controller.signal)])
      .then(([c, s]) => { setCatalog(c); setSummary(s); })
      .catch((err) => { if (!controller.signal.aborted) setError(err?.message || 'Failed to load the Stage 2 archive'); });
    return () => controller.abort();
  }, [reload]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setSelected(null); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const categories = ['All', ...(catalog?.categories ?? [])];
  const figures = (catalog?.figures ?? []).filter((f) => category === 'All' || f.category === category);

  return (
    <section aria-labelledby="focused-studies-title" className="space-y-6 border-2 border-dashed border-[#8E8E88]/30 rounded-3xl p-3 sm:p-6 bg-[#0F1013]">
      <div className="bg-[#121316] border border-[#D9B15F]/30 rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="min-w-0">
          <h2 id="focused-studies-title" className="flex items-center gap-2 text-sm font-bold uppercase text-[#D9B15F]">
            <Archive className="w-4 h-4 text-[#D9B15F]" />
            Focused Studies (Stage 2 research archive)
          </h2>
          <p className="text-xs text-[#B9B9B3] mt-1 max-w-2xl">
            The 20 figures and tables of the Stage 2 exploratory study used to plan the Stage 3 models. Each is a static research
            artifact with its own season coverage (shown on every figure); none of them reacts to the filters of the live analysis.
            All of them exclude the 2026 holdout season.
          </p>
        </div>
        <div className="inline-flex rounded-lg bg-[#101114] p-1 border border-[#D9B15F]/20 self-start sm:self-center">
          {([['gallery', `Gallery (${catalog?.total_figures ?? 20} figures)`], ['tables', 'Data tables & audits']] as const).map(([id, label]) => (
            <button
              key={id}
              type="button"
              aria-pressed={subView === id}
              onClick={() => setSubView(id)}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold cursor-pointer ${FOCUS_RING} ${subView === id ? 'bg-[#D9B15F] text-[#0D0E10]' : 'text-[#B9B9B3]'}`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div role="alert" className="bg-[#1C1517] border border-red-500/30 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs font-semibold text-red-200">{error}</p>
          <button type="button" onClick={() => setReload((n) => n + 1)} className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-[#2A1B1E] text-red-200 border border-red-500/40 ${FOCUS_RING}`}>
            <RefreshCw className="w-3.5 h-3.5" /> Retry
          </button>
        </div>
      )}

      {subView === 'gallery' && catalog && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-[#8E8E88] uppercase tracking-wider mr-1">Category:</span>
            {categories.map((c) => (
              <button
                key={c}
                type="button"
                aria-pressed={category === c}
                onClick={() => setCategory(c)}
                className={`px-3 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer ${FOCUS_RING} ${
                  category === c ? 'bg-[#D9B15F] text-[#0D0E10] shadow-sm' : 'bg-[#151619] text-[#B9B9B3] hover:text-[#F6F6F3] border border-[#D9B15F]/15'
                }`}
              >
                {c}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {figures.map((fig) => (
              <article key={fig.id} className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl overflow-hidden flex flex-col hover:border-[#D9B15F]/50 transition-all shadow-sm">
                <button
                  type="button"
                  onClick={() => setSelected(fig)}
                  aria-label={`Enlarge figure ${fig.figure_num}: ${fig.title}`}
                  className={`relative bg-[#0E0F12] border-b border-[#D9B15F]/15 aspect-[16/10] overflow-hidden group cursor-pointer ${FOCUS_RING}`}
                >
                  <img src={`/api/eda/figures/${fig.id}.png`} alt={fig.title} loading="lazy" className="w-full h-full object-contain p-2 group-hover:scale-[1.02] transition-transform duration-300" />
                  <span className="absolute top-2.5 right-2.5 p-1.5 rounded-lg bg-[#0E0F12]/80 text-[#D9B15F]">
                    <Maximize2 className="w-4 h-4" aria-hidden="true" />
                  </span>
                </button>
                <div className="p-4 sm:p-5 flex-1 flex flex-col justify-between space-y-3">
                  <div>
                    <div className="flex items-center justify-between text-[11px] text-[#B9B9B3] mb-1 gap-2">
                      <span className="font-mono text-[#D9B15F] font-bold">Fig {fig.figure_num}</span>
                      <span className="px-2 py-0.5 rounded bg-[#101114] border border-[#D9B15F]/15 text-[10px]">{fig.category}</span>
                    </div>
                    <h3 className="text-sm font-bold text-[#F6F6F3] line-clamp-1">{fig.title}</h3>
                    <p className="text-xs text-[#B9B9B3] mt-1 line-clamp-2">{fig.description}</p>
                  </div>
                  <div className="pt-2 border-t border-[#D9B15F]/10 space-y-1 text-[11px]">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-semibold text-[#D9B15F]" title={fig.coverage_evidence ?? undefined}>Coverage: {fig.coverage_span}</span>
                      <span className="font-mono text-[#8E8E88]">{fig.sample_size}</span>
                    </div>
                    <p className="text-[10px] text-[#8E8E88] italic">{fig.static_note}</p>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>
      )}

      {subView === 'tables' && summary && (
        <div className="space-y-6">
          <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 space-y-3">
            <h3 className="text-sm font-bold text-[#F6F6F3] flex items-center gap-2">
              <TableIcon className="w-4 h-4 text-[#D9B15F]" />
              First-Innings Pearson Correlation Matrix
            </h3>
            <p className="text-[11px] text-[#8E8E88]">Coverage: 2018–2025 first innings (n = {fmtCount(summary.correlations.sample_size)}). Static research table — not affected by filters.</p>
            <div className="overflow-x-auto" role="region" aria-label="Stage 2 correlation matrix" tabIndex={0}>
              <table className="w-full text-left text-xs">
                <thead className="bg-[#101114] text-[#B9B9B3] uppercase font-bold tracking-wider border-b border-[#D9B15F]/20">
                  <tr>
                    <th scope="col" className="py-2 px-3">Variable</th>
                    {summary.correlations.variables.map((v) => <th scope="col" key={v} className="py-2 px-3 text-right capitalize">{v}</th>)}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#D9B15F]/10">
                  {summary.correlations.variables.map((r) => (
                    <tr key={r} className="hover:bg-[#1A1B1F]">
                      <th scope="row" className="py-2 px-3 font-semibold text-[#F6F6F3] capitalize">{r}</th>
                      {summary.correlations.variables.map((c) => {
                        const v = summary.correlations.pearson[r]?.[c];
                        return (
                          <td key={c} className="py-2 px-3 text-right font-mono">
                            {v == null ? <span className="text-[#B9B9B3]">—</span> : (
                              <span className={v > 0.4 ? 'text-emerald-400 font-bold' : v < -0.3 ? 'text-rose-400 font-bold' : 'text-[#B9B9B3]'}>{v.toFixed(2)}</span>
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

          <div className="bg-[#151619] border border-[#D9B15F]/20 rounded-2xl p-5 space-y-3">
            <h3 className="text-sm font-bold text-[#F6F6F3] flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-[#D9B15F]" />
              Match-Field Missingness Audit
            </h3>
            <p className="text-[11px] text-[#8E8E88]">Coverage: 2008–2025 matches (Stage 2 development data). Static research table — not affected by filters.</p>
            <div className="overflow-x-auto" role="region" aria-label="Stage 2 missingness audit" tabIndex={0}>
              <table className="w-full text-left text-xs">
                <thead className="bg-[#101114] text-[#B9B9B3] uppercase font-bold tracking-wider border-b border-[#D9B15F]/20">
                  <tr>
                    <th scope="col" className="py-2 px-3">Field</th>
                    <th scope="col" className="py-2 px-3 text-center">Missing count</th>
                    <th scope="col" className="py-2 px-3 text-center">Matches</th>
                    <th scope="col" className="py-2 px-3 text-right">Missing %</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#D9B15F]/10">
                  {summary.missingness_audit.map((m) => (
                    <tr key={String(m.field)} className="hover:bg-[#1A1B1F]">
                      <th scope="row" className="py-2 px-3 font-mono text-[#F6F6F3] font-normal">{m.field}</th>
                      <td className="py-2 px-3 text-center font-mono">{fmtCount(m.missing_count)}</td>
                      <td className="py-2 px-3 text-center font-mono">{fmtCount(m.total_records)}</td>
                      <td className="py-2 px-3 text-right font-bold text-emerald-400">{Number(m.missing_pct).toFixed(2)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="figure-dialog-title">
          <div className="relative bg-[#151619] border border-[#D9B15F]/40 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-4 shadow-2xl">
            <div className="flex items-start justify-between gap-3 border-b border-[#D9B15F]/20 pb-3">
              <div>
                <span className="text-xs font-mono text-[#D9B15F] font-bold">Figure {selected.figure_num} &middot; {selected.category} &middot; Coverage {selected.coverage_span}</span>
                <h3 id="figure-dialog-title" className="text-lg font-bold text-[#F6F6F3] mt-0.5">{selected.title}</h3>
              </div>
              <button type="button" onClick={() => setSelected(null)} aria-label="Close figure" className={`p-1.5 rounded-lg bg-[#101114] text-[#B9B9B3] hover:text-[#F6F6F3] cursor-pointer ${FOCUS_RING}`} autoFocus>
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="bg-[#0E0F12] rounded-xl p-2 border border-[#D9B15F]/15">
              <img src={`/api/eda/figures/${selected.id}.png`} alt={selected.title} className="w-full h-auto max-h-[55vh] object-contain mx-auto" />
            </div>
            <div className="space-y-2 text-xs text-[#B9B9B3]">
              <p>{selected.description}</p>
              {selected.key_findings.length > 0 && (
                <ul className="list-disc list-inside space-y-1 text-[#F6F6F3] pt-1">
                  {selected.key_findings.map((f) => <li key={f}>{f}</li>)}
                </ul>
              )}
              <p className="flex items-start gap-1.5 text-[11px] text-[#8E8E88] pt-1">
                <Link2 className="w-3 h-3 mt-0.5 flex-shrink-0" aria-hidden="true" />
                Coverage evidence: {selected.coverage_evidence} Source: reports/stage_02 · {selected.source_file}. {selected.static_note}.
              </p>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
