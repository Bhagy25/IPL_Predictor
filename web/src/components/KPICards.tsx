import React from 'react';
import { 
  Trophy, 
  Eye, 
  Activity, 
  Shield, 
  User, 
  MapPin, 
  TrendingUp, 
  Target 
} from 'lucide-react';
import { KPIMetric } from '../types';

interface KPICardsProps {
  metrics?: KPIMetric[];
  loading?: boolean;
}

const defaultMetrics: KPIMetric[] = [
  { id: 'seasons', label: 'Seasons covered', value: null, statusText: 'Awaiting data', iconName: 'Trophy' },
  { id: 'matches', label: 'Matches analyzed', value: null, statusText: 'Awaiting data', iconName: 'Eye' },
  { id: 'deliveries', label: 'Recorded deliveries', value: null, statusText: 'Awaiting data', iconName: 'Activity' },
  { id: 'teams', label: 'Teams', value: null, statusText: 'Awaiting data', iconName: 'Shield' },
  { id: 'players', label: 'Players', value: null, statusText: 'Awaiting data', iconName: 'User' },
  { id: 'venues', label: 'Venues', value: null, statusText: 'Awaiting data', iconName: 'MapPin' },
  { id: 'runs', label: 'Total runs', value: null, statusText: 'Awaiting data', iconName: 'TrendingUp' },
  { id: 'wickets', label: 'Total wickets', value: null, statusText: 'Awaiting data', iconName: 'Target' },
];

const iconMap: Record<string, React.ElementType> = {
  Trophy,
  Eye,
  Activity,
  Shield,
  User,
  MapPin,
  TrendingUp,
  Target,
};

export const KPICards: React.FC<KPICardsProps> = ({ 
  metrics = defaultMetrics, 
  loading = false 
}) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
      {metrics.map((metric) => {
        const IconComponent = iconMap[metric.iconName] || Trophy;
        const definitionId = `kpi-definition-${metric.id}`;
        return (
          <div
            key={metric.id}
            // Focusable when it has a definition, so keyboard users can open the tooltip too
            tabIndex={metric.description ? 0 : undefined}
            aria-describedby={metric.description ? definitionId : undefined}
            className="group relative bg-[#151619] hover:bg-[#1E1F22] border border-white/[0.08] hover:border-[#D9B15F]/40 rounded-2xl p-4 sm:p-5 transition-all duration-200 shadow-sm flex flex-col justify-between focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D9B15F]"
          >
            {/* Top row: Label + Icon */}
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs sm:text-[13px] font-medium text-[#B9B9B3]">
                {metric.label}
              </span>
              <div className="w-7 h-7 rounded-lg bg-black/40 border border-white/[0.06] flex items-center justify-center text-[#D9B15F]/80 group-hover:text-[#D9B15F] transition-colors">
                <IconComponent className="w-3.5 h-3.5" />
              </div>
            </div>

            {/* Middle: Prominent Value / Loading Skeleton */}
            <div className="my-3 sm:my-4">
              {loading ? (
                <div className="h-8 w-20 bg-white/[0.06] rounded animate-pulse" />
              ) : (
                <div className="text-2xl sm:text-3xl font-bold tracking-tight text-[#F6F6F3]">
                  {metric.value !== null ? metric.value : '—'}
                </div>
              )}
            </div>

            {/* Bottom: Status Pill / Notice */}
            <div className="flex items-center gap-1.5 text-[11px] text-[#D9B15F]/80">
              <span className="w-1.5 h-1.5 rounded-full bg-[#D9B15F]/60" />
              <span>{metric.statusText}</span>
            </div>

            {/* Definition tooltip, shown on hover and keyboard focus */}
            {metric.description && (
              <div
                id={definitionId}
                role="tooltip"
                className="pointer-events-none absolute left-2 right-2 top-full mt-2 z-30 rounded-xl border border-[#D9B15F]/40 bg-[#0D0E10] p-3 text-[11px] leading-relaxed text-[#F6F6F3] shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible group-focus:opacity-100 group-focus:visible transition-opacity"
              >
                {metric.description}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
