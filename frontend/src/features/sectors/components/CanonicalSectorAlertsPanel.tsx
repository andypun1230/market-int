import { useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { DashboardCard } from "@/components/cards/DashboardCard";
import { DetailModal } from "@/components/ui/DetailModal";
import { AlertList } from "@/components/ui/AlertList";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Spacing, Theme, Typography } from "@/constants/theme";
import type { CanonicalSectorAlert } from "@/features/sectors/groupIntelligence";
import { formatLocalizedDateTime } from "@/features/trust/dateFreshnessPresentation";
import { useCanonicalSectorAlerts } from "@/hooks/useGroupIntelligence";

const GROUPS = ["leadership", "momentum", "breadth", "risk"] as const;

export function CanonicalSectorAlertsPanel({ onOpenSector }: { onOpenSector: (sectorId: string) => void }) {
  const { data, error, loading } = useCanonicalSectorAlerts();
  const [selected, setSelected] = useState<CanonicalSectorAlert | null>(null);
  const grouped = useMemo(() => new Map(GROUPS.map((group) => [group, data?.items.filter((item) => item.group === group) ?? []])), [data]);
  return (
    <>
      <View style={styles.stack}>
        {loading && !data ? <DashboardCard title="Sector Alerts"><Text style={styles.note}>Loading sector alerts…</Text></DashboardCard> : null}
        {error ? <DashboardCard title="Sector Alerts unavailable"><Text style={styles.note}>{error}</Text></DashboardCard> : null}
        {data ? GROUPS.map((group) => {
          const alerts = grouped.get(group) ?? [];
          if (!alerts.length) return null;
          return (
            <DashboardCard key={group} title={`${humanize(group)} alerts`} subtitle="Prioritized by severity." accentColor={group === "risk" ? Theme.colors.warning : Theme.colors.accent}>
              <AlertList
                alerts={alerts.map((alert) => ({
                  id: alert.id,
                  title: `${alert.entity.name} · ${humanize(alert.type)}`,
                  message: alert.explanation,
                  metadata: `${alert.detected_at ? formatLocalizedDateTime(alert.detected_at) : "date unavailable"} · ${alert.confidence.label} confidence`,
                  onPress: () => setSelected(alert),
                  severity: alert.severity,
                }))}
                emptyMessage="No alerts"
              />
            </DashboardCard>
          );
        }) : null}
        {data && !data.items.length ? (
          <DashboardCard title="Sector Alerts" subtitle="Deterministic transition and divergence engine">
            <Text style={styles.note}>No sector alert threshold is met. More published observations may be required.</Text>
          </DashboardCard>
        ) : null}
      </View>
      <DetailModal
        visible={Boolean(selected)}
        title={selected ? `${selected.entity.name} · ${humanize(selected.type)}` : "Sector alert"}
        subtitle={selected ? `${selected.severity} severity · ${selected.detected_at ? formatLocalizedDateTime(selected.detected_at) : "date unavailable"}` : undefined}
        onClose={() => setSelected(null)}>
        {selected ? (
          <View style={styles.stack}>
            <View style={styles.badges}>
              <StatusBadge label={selected.direction} tone={selected.direction === "positive" ? "success" : selected.direction === "negative" ? "warning" : "info"} />
              <StatusBadge label={selected.confidence.label} tone="muted" />
              <StatusBadge label={selected.freshness.state} tone="info" />
            </View>
            <Section title="Explanation" body={selected.explanation} />
            <Section title="Why it matters" body={selected.why_it_matters} />
            <Section title="Confirmation" body={selected.confirmation} />
            <Section title="Invalidation" body={selected.invalidation} />
            <View style={styles.evidence}>
              <Text style={styles.heading}>Evidence</Text>
              {Object.entries(selected.evidence).map(([key, value]) => (
                <Text key={key} style={styles.note}>{humanize(key)}: {value ?? "N/A"}</Text>
              ))}
            </View>
            <Pressable
              accessibilityRole="button"
              onPress={() => {
                const id = selected.entity.id;
                setSelected(null);
                onOpenSector(id);
              }}
              style={({ pressed }) => [styles.openButton, pressed && styles.pressed]}>
              <Text style={styles.openText}>Open sector detail</Text>
            </Pressable>
          </View>
        ) : null}
      </DetailModal>
    </>
  );
}

function Section({ body, title }: { body: string; title: string }) {
  return <View style={styles.section}><Text style={styles.heading}>{title}</Text><Text style={styles.body}>{body}</Text></View>;
}

function humanize(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

const styles = StyleSheet.create({
  badges: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.one },
  body: { color: Theme.colors.text, fontSize: Typography.control.fontSize, fontWeight: Typography.weights.emphasis },
  evidence: { backgroundColor: Theme.colors.cardMuted, borderRadius: Theme.radii.small, gap: Spacing.one, padding: Spacing.two },
  heading: { color: Theme.colors.text, fontSize: Typography.control.fontSize, fontWeight: Typography.weights.strong },
  note: { color: Theme.colors.textMuted, fontSize: Typography.small.fontSize, fontWeight: Typography.weights.emphasis },
  openButton: { alignItems: "center", backgroundColor: Theme.colors.accent, borderRadius: Theme.radii.small, minHeight: 44, padding: Spacing.two },
  openText: { color: Theme.colors.background, fontSize: Typography.control.fontSize, fontWeight: Typography.weights.strong },
  pressed: { opacity: 0.78 },
  section: { gap: Spacing.one },
  stack: { gap: Spacing.three },
});
