import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';
import {
  buildNewsConsumerPresentation,
  intelligenceStateLabel,
} from '@/features/context-intelligence/newsIntelligenceNormalizer';
import { buildSessionConsumerPresentation } from '@/features/context-intelligence/sessionNarrativePresenter';
import {
  HOME_MARKET_EVENT_LIMIT,
  shouldRequestEntityCatalysts,
  watchlistBatchLimitation,
  watchlistSavedSymbolsLabel,
} from '@/features/context-intelligence/consumerPolicy';
import {
  useEntityNewsIntelligence,
  useMarketNewsIntelligence,
  useMarketSessionNarrative,
  useSecurityNewsIntelligence,
  useWatchlistNewsIntelligence,
} from '@/features/context-intelligence/hooks';
import type {
  IntelligenceDisplayState,
  NewsIntelligenceModel,
} from '@/features/context-intelligence/types';

export function WhatMovedMarketCard({ enabled, maxItems = HOME_MARKET_EVENT_LIMIT }: { enabled: boolean; maxItems?: number }) {
  const state = useMarketNewsIntelligence(enabled, maxItems);
  if (!enabled) return null;
  return (
    <NewsContextCard
      emptyMessage="No verified material market events are available."
      error={state.error}
      loading={state.loading}
      maxItems={Math.min(HOME_MARKET_EVENT_LIMIT, maxItems)}
      model={state.data}
      scoreKind="market"
      title="What Moved the Market"
    />
  );
}

export function MarketSessionContextCard({ enabled }: { enabled: boolean }) {
  const state = useMarketSessionNarrative(enabled);
  if (!enabled) return null;

  if (state.loading && !state.data) {
    return <LoadingCard title="Session Context" />;
  }
  if (state.error || !state.data) {
    return (
      <UnavailableCard
        message={state.error
          ? 'Session context failed to load. Other market data is unaffected.'
          : 'Session context is currently unavailable.'}
        state={state.error ? 'failed' : 'unavailable'}
        title="Session Context"
      />
    );
  }

  const presentation = buildSessionConsumerPresentation(state.data);
  return (
    <DashboardCard accentColor={accentForState(presentation.state)} title="Session Context">
      <View style={styles.stack}>
        <StatusBadge label={presentation.stateLabel} tone={toneForState(presentation.state)} />
        <Text style={styles.headline}>{presentation.headline}</Text>
        {presentation.supportingText ? <Text style={styles.body}>{presentation.supportingText}</Text> : null}
        {state.data.caveats[0] && state.data.caveats[0] !== presentation.supportingText ? (
          <Text style={styles.disclosure}>Limitation: {state.data.caveats[0]}</Text>
        ) : null}
        {state.data.causalityDisclosure ? (
          <Text style={styles.disclosure}>{state.data.causalityDisclosure}</Text>
        ) : null}
      </View>
    </DashboardCard>
  );
}

export function EntityCatalystsCard({
  kind,
  entityId,
  enabled,
  forceTestContext = false,
}: {
  kind: 'sector' | 'theme';
  entityId: string;
  enabled: boolean;
  forceTestContext?: boolean;
}) {
  const state = useEntityNewsIntelligence(
    kind,
    entityId,
    shouldRequestEntityCatalysts(enabled, forceTestContext),
    5,
  );
  if (forceTestContext) {
    return (
      <UnavailableCard
        message="This selection uses an explicit test scenario. Live catalysts are not requested or mixed into it."
        state="test"
        title="Catalysts"
      />
    );
  }
  if (!enabled) return null;
  return (
    <NewsContextCard
      emptyMessage={`No verified catalysts are available for this ${kind}.`}
      error={state.error}
      loading={state.loading}
      maxItems={5}
      model={state.data}
      scoreKind="entity"
      title="Catalysts"
    />
  );
}

export function MaterialEventsCard({
  enabled,
  symbol,
}: {
  enabled: boolean;
  symbol: string;
}) {
  const state = useSecurityNewsIntelligence(symbol, enabled, 5);
  if (!enabled) return null;
  return (
    <NewsContextCard
      emptyMessage={`No verified material events are available for ${symbol.toUpperCase()}.`}
      error={state.error}
      loading={state.loading}
      maxItems={5}
      model={state.data}
      scoreKind="entity"
      title="Material Events"
    />
  );
}

export function WatchlistCatalystsCard({
  enabled,
  scopeExplanation,
  symbols,
}: {
  enabled: boolean;
  scopeExplanation?: string;
  symbols: string[];
}) {
  const limitation = watchlistBatchLimitation(symbols);
  const state = useWatchlistNewsIntelligence(symbols, enabled && limitation === null, 10);
  if (!enabled || !symbols.length) return null;
  if (limitation) {
    return (
      <UnavailableCard
        message={limitation}
        state="unavailable"
        subtitle={watchlistSavedSymbolsLabel(symbols.length)}
        title="Watchlist Catalysts"
      />
    );
  }
  return (
    <NewsContextCard
      emptyMessage="No verified catalysts are available for the saved symbols."
      error={state.error}
      loading={state.loading}
      maxItems={5}
      model={state.data}
      scoreKind="user"
      subtitle={scopeExplanation ?? watchlistSavedSymbolsLabel(symbols.length)}
      title="Watchlist Catalysts"
    />
  );
}

function NewsContextCard({
  emptyMessage,
  error,
  loading,
  maxItems,
  model,
  scoreKind,
  subtitle,
  title,
}: {
  emptyMessage: string;
  error: string | null;
  loading: boolean;
  maxItems: number;
  model: NewsIntelligenceModel | null;
  scoreKind: 'market' | 'entity' | 'user';
  subtitle?: string;
  title: string;
}) {
  if (loading && !model) return <LoadingCard subtitle={subtitle} title={title} />;
  if (error || !model) {
    return (
      <UnavailableCard
        message={error
          ? 'Context intelligence failed to load. Other screen data is unaffected.'
          : 'Context intelligence is currently unavailable.'}
        state={error ? 'failed' : 'unavailable'}
        subtitle={subtitle}
        title={title}
      />
    );
  }

  const presentation = buildNewsConsumerPresentation({ emptyMessage, maxItems, model, title });
  return (
    <DashboardCard accentColor={accentForState(presentation.state)} subtitle={subtitle} title={presentation.title}>
      <View style={styles.stack}>
        <StatusBadge label={presentation.stateLabel} tone={toneForState(presentation.state)} />
        {presentation.message ? <Text style={styles.body}>{presentation.message}</Text> : null}
        {presentation.items.map((item) => {
          const score = item.materiality[scoreKind];
          return (
            <View key={item.id} style={styles.eventRow}>
              <Text style={styles.headline}>{item.headline}</Text>
              <View style={styles.metadataRow}>
                <Text style={styles.metadata}>{item.sourceName} · {formatSourceQuality(item.sourceQuality)}{formatPublishedDate(item.publishedAt)}</Text>
                {score !== null ? <Text style={styles.score}>Materiality {score}</Text> : null}
              </View>
              {item.affectedEntities.length ? (
                <Text numberOfLines={1} style={styles.metadata}>Affected: {item.affectedEntities.join(', ')}</Text>
              ) : null}
              {item.reactionSummary ? <Text style={styles.reaction}>Observed reaction: {item.reactionSummary}</Text> : null}
              {item.state !== presentation.state ? (
                <StatusBadge label={intelligenceStateLabel(item.state)} tone={toneForState(item.state)} />
              ) : null}
            </View>
          );
        })}
        {model.contradictions.length ? (
          <Text style={styles.disclosure}>Contradiction noted: {model.contradictions[0]}</Text>
        ) : null}
        {model.limitations.length && presentation.message !== model.limitations[0] ? (
          <Text style={styles.disclosure}>Limitation: {model.limitations[0]}</Text>
        ) : null}
      </View>
    </DashboardCard>
  );
}

function LoadingCard({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <DashboardCard accentColor={Theme.colors.accent} subtitle={subtitle} title={title}>
      <StatusBadge label="Loading" tone="info" />
    </DashboardCard>
  );
}

function UnavailableCard({
  message,
  state,
  subtitle,
  title,
}: {
  message: string;
  state: IntelligenceDisplayState;
  subtitle?: string;
  title: string;
}) {
  return (
    <DashboardCard accentColor={accentForState(state)} subtitle={subtitle} title={title}>
      <View style={styles.stack}>
        <StatusBadge label={intelligenceStateLabel(state)} tone={toneForState(state)} />
        <Text style={styles.body}>{message}</Text>
      </View>
    </DashboardCard>
  );
}

function formatPublishedDate(value: string | null): string {
  if (!value) return '';
  return ` · ${value.slice(0, 10)}`;
}

function formatSourceQuality(value: NewsIntelligenceModel['events'][number]['sourceQuality']): string {
  if (value === 'primary') return 'Primary source';
  if (value === 'high_confidence_secondary') return 'High-confidence secondary';
  return 'Supporting secondary';
}

function toneForState(state: IntelligenceDisplayState): Tone {
  if (state === 'live') return 'success';
  if (state === 'delayed' || state === 'cached') return 'info';
  if (state === 'failed') return 'danger';
  if (state === 'unavailable') return 'muted';
  return 'warning';
}

function accentForState(state: IntelligenceDisplayState): string {
  if (state === 'live') return Theme.colors.success;
  if (state === 'delayed' || state === 'cached') return Theme.colors.accent;
  if (state === 'failed') return Theme.colors.danger;
  if (state === 'unavailable') return Theme.colors.border;
  return Theme.colors.warning;
}

const styles = StyleSheet.create({
  body: {
    color: Theme.colors.textMuted,
    fontSize: Typography.control.fontSize,
    lineHeight: 19,
  },
  disclosure: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontStyle: 'italic',
    lineHeight: 16,
  },
  eventRow: {
    borderTopColor: Theme.colors.border,
    borderTopWidth: 1,
    gap: Spacing.one,
    paddingTop: Spacing.two,
  },
  headline: {
    color: Theme.colors.text,
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 20,
  },
  metadata: {
    color: Theme.colors.textMuted,
    flexShrink: 1,
    fontSize: Typography.caption.fontSize,
    lineHeight: 15,
  },
  metadataRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  reaction: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    lineHeight: 17,
  },
  score: {
    color: Theme.colors.accent,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
  },
  stack: {
    gap: Spacing.two,
  },
});
