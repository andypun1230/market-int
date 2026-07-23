import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { FreshnessText } from '@/components/ui/ConfidenceFreshness';
import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';
import { useUserFacingDataState } from '@/features/trust/UserFacingDataStateProvider';
import type { UserFacingDataStateKey } from '@/features/trust/userFacingDataState';

export function DataStateSummary({ diagnostic = false }: { diagnostic?: boolean }) {
  const { dataState } = useUserFacingDataState();
  return (
    <DashboardCard title="Data status" accentColor={toneColor(dataState.state)}>
      <View accessibilityLabel={`Data status: ${dataState.headline}. ${dataState.explanation}`} style={styles.stack}>
        <View style={styles.header}>
          <StatusBadge label={dataState.headline} tone={tone(dataState.state)} />
          <FreshnessText value={dataState.freshness} />
        </View>
        <Text style={styles.explanation}>{dataState.explanation}</Text>
        <Text style={styles.detail}>{dataState.providerSummary}</Text>
        <Text style={styles.detail}>{dataState.availabilitySummary}</Text>
        {dataState.recommendedAction ? <Text style={styles.action}>{dataState.recommendedAction}</Text> : null}
        {diagnostic ? (
          <View style={styles.diagnostics}>
            <Text style={styles.diagnosticTitle}>Diagnostics</Text>
            <Text style={styles.detail}>Reason: {dataState.reasonCodes.join(', ') || 'none'}</Text>
            <Text style={styles.detail}>Mode: {String(dataState.technicalDetail.configuredMode ?? 'unavailable')}</Text>
          </View>
        ) : null}
      </View>
    </DashboardCard>
  );
}

function tone(state: UserFacingDataStateKey): Tone {
  if (state === 'live') return 'success';
  if (state === 'failed' || state === 'unavailable') return 'danger';
  if (state === 'partial' || state === 'live_cached' || state === 'stale' || state === 'test' || state === 'scenario') return 'warning';
  return 'muted';
}

function toneColor(state: UserFacingDataStateKey) {
  const next = tone(state);
  return next === 'success' ? Theme.colors.success : next === 'danger' ? Theme.colors.danger : next === 'warning' ? Theme.colors.warning : Theme.colors.accent;
}

const styles = StyleSheet.create({
  action: { color: Theme.colors.warning, fontSize: Typography.small.fontSize, fontWeight: Typography.weights.strong, lineHeight: 18 },
  detail: { color: Theme.colors.textMuted, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.emphasis, lineHeight: 17 },
  diagnostics: { borderTopColor: Theme.colors.border, borderTopWidth: 1, gap: Spacing.half, paddingTop: Spacing.one },
  diagnosticTitle: { color: Theme.colors.text, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.strong, textTransform: 'uppercase' },
  explanation: { color: Theme.colors.text, fontSize: Typography.control.fontSize, fontWeight: Typography.weights.emphasis, lineHeight: 20 },
  header: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.one, justifyContent: 'space-between' },
  stack: { gap: Spacing.one },
});
