import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { DashboardCard } from "@/components/cards/DashboardCard";
import { ConfidenceIndicator } from "@/components/ui/ConfidenceIndicator";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Spacing, Theme } from "@/constants/theme";
import {
  formatNullableMetric,
  type BreadthHistoryTimeframe,
  type CanonicalGroupType,
} from "@/features/sectors/groupIntelligence";
import { useCanonicalBreadthHistory, useCanonicalDivergences } from "@/hooks/useGroupIntelligence";

const TIMEFRAMES: BreadthHistoryTimeframe[] = ["1M", "3M", "6M", "1Y"];

export function CanonicalBreadthHistoryPanel({ entityId, entityType }: { entityId: string; entityType: CanonicalGroupType }) {
  const [timeframe, setTimeframe] = useState<BreadthHistoryTimeframe>("3M");
  const history = useCanonicalBreadthHistory(entityType, entityId, timeframe);
  const divergences = useCanonicalDivergences(entityType, entityId, timeframe);
  const first = history.data?.observations[0];
  const latest = history.data?.observations.at(-1);

  return (
    <View style={styles.stack}>
      <DashboardCard title="Breadth History" subtitle="Published immutable snapshots only; missing measures remain N/A." accentColor={Theme.colors.accent}>
        <View accessibilityLabel="Breadth history timeframe" style={styles.options}>
          {TIMEFRAMES.map((value) => (
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ selected: timeframe === value }}
              key={value}
              onPress={() => setTimeframe(value)}
              style={[styles.chip, timeframe === value && styles.chipActive]}>
              <Text style={[styles.chipText, timeframe === value && styles.chipTextActive]}>{value}</Text>
            </Pressable>
          ))}
        </View>
        {history.loading && !history.data ? <Text style={styles.note}>Loading canonical history…</Text> : null}
        {history.error ? <Text style={styles.note}>Breadth history failed: {history.error}</Text> : null}
        {history.data ? (
          <View style={styles.stack}>
            <View style={styles.badges}>
              <StatusBadge label={history.data.status} tone={history.data.status === "available" ? "success" : history.data.status === "partial" ? "warning" : "muted"} />
              <StatusBadge label={`${history.data.observation_count} snapshots`} tone="info" />
            </View>
            {first && latest ? (
              <View style={styles.metrics}>
                <HistoryMetric label="> 20 EMA" first={first.above_20} latest={latest.above_20} suffix="%" />
                <HistoryMetric label="> 50 EMA" first={first.above_50} latest={latest.above_50} suffix="%" />
                <HistoryMetric label="> 200 EMA" first={first.above_200} latest={latest.above_200} suffix="%" />
                <HistoryMetric label="A/D ratio" first={first.advance_decline_ratio} latest={latest.advance_decline_ratio} />
                <HistoryMetric label="Highs − lows" first={first.highs_minus_lows} latest={latest.highs_minus_lows} />
              </View>
            ) : <Text style={styles.note}>No published breadth observations exist for this entity and timeframe.</Text>}
            <View style={styles.interpretation}>
              <Text style={styles.heading}>Authoritative interpretation</Text>
              <Text style={styles.body}>{history.data.interpretation.conclusion}</Text>
              <ConfidenceIndicator
                confidence={confidenceScore(history.data.interpretation.confidence)}
                generatedBy="rules"
                nextUpdate={`Evidence through ${history.data.interpretation.freshness ?? "N/A"}`}
              />
              <Text style={styles.note}>As of {history.data.interpretation.freshness ?? "N/A"} · evidence: {history.data.interpretation.evidence.length} available changes</Text>
            </View>
            <Text style={styles.note}>{history.data.limitation}</Text>
          </View>
        ) : null}
      </DashboardCard>

      <DashboardCard title="Divergence Alerts" subtitle="Deterministic price, breadth, rotation, and concentration rules." accentColor={Theme.colors.warning}>
        {divergences.loading && !divergences.data ? <Text style={styles.note}>Evaluating canonical observations…</Text> : null}
        {divergences.error ? <Text style={styles.note}>Divergence analysis failed: {divergences.error}</Text> : null}
        {divergences.data?.items.length ? divergences.data.items.map((alert) => (
          <View key={alert.id} style={styles.alert}>
            <View style={styles.badges}>
              <StatusBadge label={alert.direction} tone={alert.direction === "positive" ? "success" : alert.direction === "negative" ? "warning" : "info"} />
              <StatusBadge label={alert.severity} tone={alert.severity === "high" ? "warning" : "muted"} />
            </View>
            <Text style={styles.heading}>{humanize(alert.rule_id)}</Text>
            <Text style={styles.body}>{alert.explanation}</Text>
            <Text style={styles.note}>Why it matters: {alert.why_it_matters}</Text>
            <Text style={styles.note}>Confirm: {alert.confirmation}</Text>
            <Text style={styles.note}>Invalidate: {alert.invalidation}</Text>
          </View>
        )) : divergences.data ? <Text style={styles.note}>No deterministic divergence threshold is currently met.</Text> : null}
      </DashboardCard>
    </View>
  );
}

function HistoryMetric({ first, label, latest, suffix = "" }: { first: number | null; label: string; latest: number | null; suffix?: string }) {
  const change = first !== null && latest !== null ? latest - first : null;
  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{formatNullableMetric(latest, suffix)}</Text>
      <Text style={styles.note}>{formatNullableMetric(first, suffix)} → {formatNullableMetric(latest, suffix)} · Δ {formatNullableMetric(change)}</Text>
    </View>
  );
}

function humanize(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function confidenceScore(value: string) {
  if (value === "high") return 90;
  if (value === "moderate") return 70;
  if (value === "low") return 40;
  return null;
}

const styles = StyleSheet.create({
  alert: { borderTopColor: Theme.colors.border, borderTopWidth: 1, gap: Spacing.one, paddingTop: Spacing.two },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.one },
  body: { color: Theme.colors.text, fontSize: 13, fontWeight: "700" },
  chip: { borderColor: Theme.colors.border, borderRadius: Theme.radii.pill, borderWidth: 1, minHeight: 40, minWidth: 48, paddingHorizontal: Spacing.two, paddingVertical: 10 },
  chipActive: { backgroundColor: Theme.colors.accentSoft, borderColor: Theme.colors.accent },
  chipText: { color: Theme.colors.textMuted, fontSize: 11, fontWeight: "900", textAlign: "center" },
  chipTextActive: { color: Theme.colors.accent },
  heading: { color: Theme.colors.text, fontSize: 14, fontWeight: "900" },
  interpretation: { backgroundColor: Theme.colors.cardMuted, borderRadius: Theme.radii.small, gap: Spacing.one, padding: Spacing.two },
  metric: { backgroundColor: Theme.colors.cardMuted, borderRadius: Theme.radii.small, flexBasis: "46%", flexGrow: 1, gap: 3, padding: Spacing.two },
  metricLabel: { color: Theme.colors.textMuted, fontSize: 10, fontWeight: "900", textTransform: "uppercase" },
  metricValue: { color: Theme.colors.text, fontSize: 16, fontWeight: "900" },
  metrics: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.two },
  note: { color: Theme.colors.textMuted, fontSize: 11, fontWeight: "700" },
  options: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.one },
  stack: { gap: Spacing.three },
});
