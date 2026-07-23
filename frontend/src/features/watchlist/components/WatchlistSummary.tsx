import { DecisionSummaryCard } from '@/components/ui/DecisionSummaryCard';
import { decisionSummary } from '@/features/trust/decisionSummary';
import type { WatchlistCountModel } from '@/features/watchlist/watchlistCounts';
import { buildWatchlistDecisionBrief } from '@/features/watchlist/watchlistDecision';
import type { ClassifiedWatchlistItem } from '@/features/watchlist/types';

export function WatchlistBrief({ counts, items }: { counts: WatchlistCountModel; items: ClassifiedWatchlistItem[] }) {
  const brief = buildWatchlistDecisionBrief(items);
  const maintenanceCount = brief.staleCount + brief.partialCount + brief.unavailableCount;
  return <DecisionSummaryCard summary={decisionSummary({
    id: 'watchlist.summary', title: 'Watchlist decision summary',
    currentState: `${brief.immediateCount} action now · ${brief.improvingCount} improving · ${brief.deterioratingCount} weakening`,
    whatChanged: `${counts.displayed} displayed · ${counts.locallySaved} locally saved · ${counts.analyzed} analyzed`,
    preferredAction: brief.immediateCount ? `Review active trading triggers: ${symbolSummary(brief.immediateSymbols)}.` : 'Monitor for a clearer trading trigger.',
    mainRisk: maintenanceCount ? `Data maintenance: ${brief.staleCount} need refresh · ${brief.partialCount} partial · ${brief.unavailableCount} unavailable.` : 'No data-maintenance issue is currently flagged.',
    invalidation: null, freshness: maintenanceCount ? `${maintenanceCount} items require data maintenance` : 'Displayed analysis is current',
    confidence: null, confidenceLabel: 'Confidence shown per item', evidence: null,
    availability: brief.unavailableCount ? 'partial' : brief.staleCount ? 'stale' : brief.partialCount ? 'partial' : 'available',
    contradiction: null, whatWouldChange: 'New trading signals or refreshed analysis can change these groups.',
    methodology: [`Eligible: ${counts.eligible}`, `Catalyst request: ${counts.catalystRequested}`, counts.catalystScopeExplanation],
  })} />;
}

function symbolSummary(symbols: string[]) {
  return symbols.length ? symbols.join(', ') : 'None';
}
