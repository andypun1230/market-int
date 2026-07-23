import { useMemo, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from "react-native";

import { DashboardCard } from "@/components/cards/DashboardCard";
import { AppIcon } from "@/components/ui/AppIcon";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Spacing, Theme, Typography } from "@/constants/theme";
import {
  comparisonSelectionLimit,
  formatNullableMetric,
  type CanonicalGroupItem,
  type CanonicalGroupTimeframe,
  type CanonicalGroupType,
} from "@/features/sectors/groupIntelligence";
import { useCanonicalGroupComparison } from "@/hooks/useGroupIntelligence";

const TIMEFRAMES: CanonicalGroupTimeframe[] = ["1D", "1W", "1M", "3M", "6M", "1Y"];

export function CanonicalGroupComparisonView({
  entityType,
  initialIds = [],
  initialTimeframe = "1M",
  items,
  registryLoading = false,
  onOpenItem,
  onSelectionChange,
}: {
  entityType: CanonicalGroupType;
  initialIds?: string[];
  initialTimeframe?: CanonicalGroupTimeframe;
  items: CanonicalGroupItem[];
  registryLoading?: boolean;
  onOpenItem: (item: CanonicalGroupItem) => void;
  onSelectionChange?: (ids: string[], timeframe: CanonicalGroupTimeframe) => void;
}) {
  const { width } = useWindowDimensions();
  const maximum = comparisonSelectionLimit(width);
  const [selectedIds, setSelectedIds] = useState(() => [...new Set(initialIds)].slice(0, maximum));
  const [timeframe, setTimeframe] = useState<CanonicalGroupTimeframe>(initialTimeframe);
  const activeSelectedIds = useMemo(() => selectedIds.slice(0, maximum), [maximum, selectedIds]);
  const { data, error, loading } = useCanonicalGroupComparison(entityType, activeSelectedIds, timeframe, activeSelectedIds.length >= 2);
  const selected = useMemo(() => new Set(activeSelectedIds), [activeSelectedIds]);
  function toggle(item: CanonicalGroupItem) {
    const next = activeSelectedIds.includes(item.id)
      ? activeSelectedIds.filter((id) => id !== item.id)
      : activeSelectedIds.length < maximum ? [...activeSelectedIds, item.id] : activeSelectedIds;
    setSelectedIds(next);
    onSelectionChange?.(next, timeframe);
  }

  if (registryLoading && !items.length) {
    return <DashboardCard title="Loading comparison"><Text style={styles.note}>Loading available entities…</Text></DashboardCard>;
  }

  return (
    <View style={styles.stack}>
      <DashboardCard
        title={`${entityType === "sector" ? "Sector" : "Theme"} comparison`}
        subtitle={`Same-type comparison · select 2–${maximum} on this screen size.`}
        accentColor={Theme.colors.accent}>
        <View style={styles.badges}>
          <StatusBadge label="Published data" tone="info" />
          <StatusBadge label={`${activeSelectedIds.length}/${maximum} selected`} tone={activeSelectedIds.length >= 2 ? "success" : "muted"} />
        </View>
        <View accessibilityLabel="Comparison timeframe" style={styles.options}>
          {TIMEFRAMES.map((value) => (
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ selected: timeframe === value }}
              key={value}
              onPress={() => {
                setTimeframe(value);
                onSelectionChange?.(activeSelectedIds, value);
              }}
              style={[styles.chip, timeframe === value && styles.chipActive]}>
              <Text style={[styles.chipText, timeframe === value && styles.chipTextActive]}>{value}</Text>
            </Pressable>
          ))}
        </View>
        {items.length ? (
          <View style={styles.candidates}>
            {items.map((item) => {
              const active = selected.has(item.id);
              const disabled = !active && activeSelectedIds.length >= maximum;
              return (
                <Pressable
                  accessibilityLabel={`${active ? "Remove" : "Add"} ${item.name} ${entityType} comparison`}
                  accessibilityRole="checkbox"
                  accessibilityState={{ checked: active, disabled }}
                  disabled={disabled}
                  key={item.id}
                  onPress={() => toggle(item)}
                  style={[styles.candidate, active && styles.candidateActive, disabled && styles.disabled]}>
                  <View style={styles.candidateText}>
                    <Text style={styles.name}>{item.name}</Text>
                    <Text style={styles.meta}>#{item.rank ?? "N/A"} · {item.state} · {item.availability.state}</Text>
                  </View>
                  <View style={styles.selectMark}>
                    <AppIcon color={active ? Theme.colors.accent : Theme.colors.textMuted} name={active ? "check" : "add"} size={18} />
                  </View>
                </Pressable>
              );
            })}
          </View>
        ) : (
          <Text style={styles.note}>No published {entityType} entities are available for comparison.</Text>
        )}
      </DashboardCard>

      {activeSelectedIds.length < 2 ? (
        <DashboardCard title="Select entities" subtitle="Choose at least two entities of the same type.">
          <Text style={styles.note}>No metrics are inferred while the comparison is incomplete.</Text>
        </DashboardCard>
      ) : loading && !data ? (
        <DashboardCard title="Loading comparison"><Text style={styles.note}>Loading comparison data…</Text></DashboardCard>
      ) : data ? (
        <DashboardCard
          title={`${data.timeframe} comparison`}
          subtitle={`${data.items.length} entities · ${error ? 'Cached after refresh failure' : data.status}`}
          accentColor={data.status === "available" ? Theme.colors.success : Theme.colors.warning}>
          <ScrollView horizontal={width < 900} showsHorizontalScrollIndicator={false}>
            <View style={[styles.table, width >= 900 && styles.tableWide]}>
              <MetricRow label="Identity" items={data.items} value={(item) => item.name} onOpenItem={onOpenItem} />
              <MetricRow label="State" items={data.items} value={(item) => item.state} />
              <MetricRow label={`${timeframe} performance`} items={data.items} value={(item) => formatNullableMetric(item.performance[timeframe], "%")} />
              <MetricRow label="Relative strength" items={data.items} value={(item) => formatNullableMetric(item.relative_strength)} />
              <MetricRow label="Relative momentum" items={data.items} value={(item) => formatNullableMetric(item.relative_momentum)} />
              <MetricRow label="Breadth > 20 EMA" items={data.items} value={(item) => formatNullableMetric(item.breadth.above_20, "%")} />
              <MetricRow label="Breadth > 50 EMA" items={data.items} value={(item) => formatNullableMetric(item.breadth.above_50, "%")} />
              <MetricRow label="Breadth > 200 EMA" items={data.items} value={(item) => formatNullableMetric(item.breadth.above_200, "%")} />
              <MetricRow label="A/D ratio" items={data.items} value={(item) => formatNullableMetric(item.breadth.advance_decline_ratio)} />
              <MetricRow label="Persistence" items={data.items} value={(item) => item.persistence.available ? `${item.persistence.snapshot_count} snapshots` : "N/A"} />
              <MetricRow label="Rank / change" items={data.items} value={(item) => `#${item.rank ?? "N/A"} / ${formatNullableMetric(item.rank_change)}`} />
              <MetricRow label="Confidence" items={data.items} value={(item) => `${item.confidence.data.label} data · ${item.confidence.signal.label} signal`} />
              <MetricRow label="Freshness" items={data.items} value={(item) => `${item.freshness.state} · ${item.freshness.as_of ?? "N/A"}`} />
              <MetricRow label="Availability" items={data.items} value={(item) => item.availability.state} />
            </View>
          </ScrollView>
        </DashboardCard>
      ) : error ? (
        <DashboardCard title="Comparison failed"><Text style={styles.note}>{error}</Text></DashboardCard>
      ) : null}
    </View>
  );
}

function MetricRow({ items, label, onOpenItem, value }: {
  items: CanonicalGroupItem[];
  label: string;
  onOpenItem?: (item: CanonicalGroupItem) => void;
  value: (item: CanonicalGroupItem) => string;
}) {
  return (
    <View style={styles.row}>
      <Text style={[styles.cell, styles.labelCell]}>{label}</Text>
      {items.map((item) => onOpenItem && label === "Identity" ? (
        <Pressable accessibilityRole="button" key={item.id} onPress={() => onOpenItem(item)} style={styles.cell}>
          <Text style={styles.link}>{value(item)}</Text>
        </Pressable>
      ) : <Text key={item.id} style={styles.cell}>{value(item)}</Text>)}
    </View>
  );
}

const styles = StyleSheet.create({
  badges: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.one, marginBottom: Spacing.two },
  candidate: { alignItems: "center", borderBottomColor: Theme.colors.border, borderBottomWidth: 1, flexDirection: "row", gap: Spacing.two, minHeight: 48, paddingVertical: Spacing.two },
  candidateActive: { backgroundColor: Theme.colors.accentSoft },
  candidateText: { flex: 1 },
  candidates: { maxHeight: 360 },
  cell: { color: Theme.colors.text, fontSize: Typography.small.fontSize, fontWeight: Typography.weights.strong, padding: Spacing.two, width: 180 },
  chip: { borderColor: Theme.colors.border, borderRadius: Theme.radii.pill, borderWidth: 1, minHeight: 38, minWidth: 44, paddingHorizontal: Spacing.two, paddingVertical: 9 },
  chipActive: { backgroundColor: Theme.colors.accentSoft, borderColor: Theme.colors.accent },
  chipText: { color: Theme.colors.textMuted, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.strong, textAlign: "center" },
  chipTextActive: { color: Theme.colors.accent },
  disabled: { opacity: 0.42 },
  labelCell: { color: Theme.colors.textMuted, width: 165 },
  link: { color: Theme.colors.accent, fontSize: Typography.small.fontSize, fontWeight: Typography.weights.strong },
  meta: { color: Theme.colors.textMuted, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.emphasis },
  name: { color: Theme.colors.text, fontSize: Typography.body.fontSize, fontWeight: Typography.weights.strong },
  note: { color: Theme.colors.textMuted, fontSize: Typography.control.fontSize, fontWeight: Typography.weights.emphasis },
  options: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.one, marginBottom: Spacing.two },
  row: { borderBottomColor: Theme.colors.border, borderBottomWidth: 1, flexDirection: "row" },
  selectMark: { alignItems: "center", justifyContent: "center", width: 30 },
  stack: { gap: Spacing.three },
  table: { minWidth: 525 },
  tableWide: { flex: 1 },
});
