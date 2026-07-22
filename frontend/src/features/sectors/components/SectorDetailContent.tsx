import { ScrollView, StyleSheet, Text, View } from "react-native";
import { DashboardCard } from "@/components/cards/DashboardCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { MetricTile } from "@/components/ui/MetricTile";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Spacing, Theme } from "@/constants/theme";
import { AskCopilotButton } from "@/features/copilot/components/AskCopilotButton";
import { createCopilotContext } from "@/features/copilot/context/buildScreenContext";
import { EntityCatalystsCard } from "@/features/context-intelligence/components/ContextIntelligenceCards";
import { useSectorDetail } from "@/hooks/useSectorSnapshot";
import {
  formatClassification,
  formatCoverage,
  formatNullableCount,
  formatNullablePercent,
  sourceLabel,
  type SectorId,
} from "@/features/sectors/sectorSnapshot";
import { WatchlistBookmarkButton } from "@/features/watchlist/WatchlistBookmarkButton";
import { rotationTrailMethodology } from "@/features/sectors/rotationCopy";

export function SectorDetailContent({ sectorId }: { sectorId: SectorId }) {
  const { detail, loading, error } = useSectorDetail(sectorId);
  if (loading)
    return <Text style={styles.muted}>Loading durable sector snapshot.</Text>;
  if (!detail?.sector)
    return (
      <EmptyState
        title="Sector unavailable"
        message={error ?? "No durable sector snapshot is available."}
      />
    );
  const row = detail.sector;
  const b = row.breadth;
  const conclusion = leadershipConclusion(row);
  const rsTrend = relativeStrengthTrend(detail.rotationMovement);
  const rotation =
    detail.rotationSeries.find((series) => series.interval === "3M") ??
    detail.rotationSeries[0] ??
    null;
  const analysed =
    b.advancing === null || b.declining === null || b.unchanged === null
      ? null
      : b.advancing + b.declining + b.unchanged;
  return (
    <ScrollView
      contentContainerStyle={styles.stack}
      showsVerticalScrollIndicator={false}
    >
      <View style={styles.badges}>
        <StatusBadge label={`#${row.rank}`} tone="info" />
        <StatusBadge
          label={formatClassification(row.classification)}
          tone={tone(row.classification)}
        />
        <StatusBadge
          label={`Composite ${row.compositeScore?.toFixed(1) ?? "N/A"}`}
          tone="purple"
        />
        <StatusBadge label={sourceLabel(detail)} tone="muted" />
      </View>
      <AskCopilotButton
        context={createCopilotContext({
          payload: { detail, selectedSector: row },
          routeName: "/sectors",
          screenTitle: `${row.displayName} Sector Detail`,
          screenType: "sector",
          sourceState: detail.sourceState,
        })}
        prompt={`Why is ${row.displayName} ${row.classification.toLowerCase()}, and what would invalidate that view?`}
      />
      <WatchlistBookmarkButton
        id={row.sectorId}
        name={row.displayName}
        type="sector"
      />
      <Text style={styles.context}>
        S&P 100 · {detail.marketDate} ·{" "}
        {detail.providerHistory ?? "provider unavailable"} ·{" "}
        {formatCoverage(detail.coverage.constituentCoverage)} constituent
        coverage
      </Text>
      <Text style={styles.context}>Snapshot {detail.snapshotId}</Text>
      <EntityCatalystsCard
        enabled
        entityId={sectorId}
        key={sectorId}
        kind="sector"
      />
      <DashboardCard
        title="Performance Summary"
        accentColor={Theme.colors.success}
      >
        <Grid
          values={[
            ["1D", formatNullablePercent(row.returns["1D"])],
            ["1W", formatNullablePercent(row.returns["1W"])],
            ["1M", formatNullablePercent(row.returns["1M"])],
            ["3M", formatNullablePercent(row.returns["3M"])],
            ["6M", formatNullablePercent(row.returns["6M"])],
            ["1Y", formatNullablePercent(row.returns["1Y"])],
          ]}
        />
      </DashboardCard>
      <DashboardCard
        title="Relative Strength"
        accentColor={Theme.colors.accent}
      >
        <Grid
          values={[
            ["vs SPY 1M", formatNullablePercent(row.relativeStrength.vsSpy1M)],
            ["vs SPY 3M", formatNullablePercent(row.relativeStrength.vsSpy3M)],
            ["RS Trend", rsTrend],
            ["Confidence", row.confidence],
          ]}
        />
      </DashboardCard>
      <DashboardCard
        title="Breadth Participation"
        accentColor={Theme.colors.warning}
      >
        <Grid
          values={[
            [
              "Members",
              `${formatNullableCount(row.eligibleMembers)}/${formatNullableCount(row.totalMembers)}`,
            ],
            [
              "Representativeness",
              row.representativeness.label ?? "Unavailable",
            ],
            ["Above 20 EMA", formatNullablePercent(row.breadth.above20)],
            ["Above 50 EMA", formatNullablePercent(row.breadth.above50)],
            ["Above 200 EMA", formatNullablePercent(row.breadth.above200)],
            [
              "Participation",
              formatNullablePercent(row.participation.positive),
            ],
            ["Data Confidence", row.dataConfidence.label ?? "Unavailable"],
            ["Signal Confidence", row.signalConfidence.label ?? "Unavailable"],
          ]}
        />
        <Text style={styles.muted}>
          {row.representativeness.reason ??
            row.participation.definition ??
            "Breadth representativeness is unavailable."}
        </Text>
      </DashboardCard>
      <DashboardCard
        title="Advancers vs Decliners"
        accentColor={Theme.colors.accent}
      >
        <Grid
          values={[
            ["Advancing", formatNullableCount(b.advancing)],
            ["Declining", formatNullableCount(b.declining)],
            ["Unchanged", formatNullableCount(b.unchanged)],
            ["Analysed", formatNullableCount(analysed)],
            ["A/D Ratio", b.adRatioDisplay ?? b.adRatio?.toFixed(2) ?? "N/A"],
            [
              "52W Highs/Lows",
              `${formatNullableCount(b.highs)}/${formatNullableCount(b.lows)}`,
            ],
          ]}
        />
      </DashboardCard>
      <DashboardCard
        title="Why It Ranks Here"
        accentColor={Theme.colors.purple}
      >
        <Text style={styles.sectionLabel}>Supportive factors</Text>
        {conclusion.supportive.map((item) => (
          <Text key={item} style={styles.body}>
            • {item}
          </Text>
        ))}
        <Text style={styles.sectionLabel}>Risks</Text>
        {conclusion.risks.map((item) => (
          <Text key={item} style={styles.body}>
            • {item}
          </Text>
        ))}
        {row.warnings.map((warning) => (
          <Text key={warning} style={styles.warning}>
            {warning}
          </Text>
        ))}
      </DashboardCard>
      <DashboardCard
        title="Relevant Stocks"
        subtitle={`${detail.constituents.length}/${formatNullableCount(row.totalMembers)} active S&P 100 constituents`}
        accentColor={Theme.colors.success}
      >
        {detail.constituents.length ? (
          detail.constituents.map((item) => (
            <View key={item.ticker} style={styles.stock}>
              <View>
                <Text style={styles.ticker}>{item.ticker}</Text>
                <Text style={styles.muted}>{item.companyName}</Text>
                {item.relevance ? (
                  <Text style={styles.relevance}>{item.relevance}</Text>
                ) : null}
              </View>
              <View style={styles.stockActions}>
                <Text style={styles.stockReturn}>
                  {formatNullablePercent(item.returns["1M"])}
                </Text>
                <WatchlistBookmarkButton
                  id={item.ticker}
                  name={item.companyName}
                  type="stock"
                />
              </View>
            </View>
          ))
        ) : (
          <Text style={styles.muted}>
            No constituents match the current filters.
          </Text>
        )}
      </DashboardCard>
      <DashboardCard
        title="How This Tail Is Calculated"
        accentColor={Theme.colors.accent}
      >
        {rotation?.currentPoint ? (
          <>
            <Grid
              values={[
                ["ETF", row.etfSymbol],
                ["Benchmark", rotation.benchmark],
                ["Profile", capitalize(rotation.profile)],
                [
                  "Relative Trend",
                  rotation.currentPoint.relativeTrend.toFixed(2),
                ],
                [
                  "Relative Momentum",
                  rotation.currentPoint.relativeMomentum.toFixed(2),
                ],
                [
                  "Quadrant",
                  capitalize(
                    rotation.currentPoint.relativeTrend >= 100 &&
                      rotation.currentPoint.relativeMomentum >= 100
                      ? "leading"
                      : rotation.currentPoint.relativeTrend >= 100
                        ? "weakening"
                        : rotation.currentPoint.relativeMomentum < 100
                          ? "lagging"
                          : "improving",
                  ),
                ],
                ["Tail", `${rotation.trailPoints.length} real market dates`],
                [
                  "Source",
                  `${rotation.currentPoint.sourceProvider ?? "Unavailable"} adjusted daily history`,
                ],
                ["Model", rotation.modelVersion],
              ]}
            />
            <Text style={styles.body}>{rotationTrailMethodology}</Text>
          </>
        ) : (
          <Text style={styles.muted}>
            Rotation history is insufficient for this sector.
          </Text>
        )}
      </DashboardCard>
      <DashboardCard title="Breadth History" accentColor={Theme.colors.accent}>
        <Text style={styles.muted}>No breadth history is available yet.</Text>
      </DashboardCard>
      <DashboardCard
        title="Divergences & Alerts"
        accentColor={Theme.colors.warning}
      >
        <Text style={styles.muted}>
          No rule-based divergences or transition alerts are available for the
          current snapshot history.
        </Text>
      </DashboardCard>
    </ScrollView>
  );
}
function Grid({ values }: { values: [string, string][] }) {
  return (
    <View style={styles.grid}>
      {values.map(([label, value]) => (
        <MetricTile key={label} label={label} value={value} />
      ))}
    </View>
  );
}
function capitalize(value: string) {
  return value ? `${value[0].toUpperCase()}${value.slice(1)}` : "Unavailable";
}
function tone(value: string) {
  return value === "Leading"
    ? "success"
    : value === "Improving"
      ? "info"
      : value === "Weakening"
        ? "warning"
        : value === "Lagging"
          ? "danger"
          : ("muted" as const);
}
function relativeStrengthTrend(
  movement:
    import("@/features/sectors/sectorSnapshot").SectorRotationMovement | null,
) {
  if (!movement || movement.state !== "available")
    return "Insufficient snapshot history";
  if (movement.relativeStrengthChange === null)
    return "Insufficient snapshot history";
  return movement.relativeStrengthChange >= 1
    ? "Rising"
    : movement.relativeStrengthChange <= -1
      ? "Falling"
      : "Stable";
}
function leadershipConclusion(
  row: import("@/features/sectors/sectorSnapshot").SectorRow,
) {
  const supportive = [
    `Composite score ${row.compositeScore?.toFixed(1) ?? "N/A"} · rank #${row.rank}`,
    row.breadth.above200 === 100
      ? `All ${formatNullableCount(row.eligibleMembers)} eligible members are above EMA200`
      : `${formatNullablePercent(row.breadth.above50)} of eligible members are above EMA50`,
    row.breadth.advancing !== null && row.breadth.declining !== null
      ? `${row.breadth.advancing} advancing vs ${row.breadth.declining} declining`
      : "Advance/decline breadth is unavailable",
    row.returns["1M"] !== null
      ? `1M ETF return ${formatNullablePercent(row.returns["1M"])}`
      : "1M ETF return is unavailable",
  ].slice(0, 4);
  const risks = [
    row.relativeStrength.vsSpy3M !== null && row.relativeStrength.vsSpy3M < 0
      ? `3M relative strength trails SPY by ${formatNullablePercent(row.relativeStrength.vsSpy3M)}`
      : null,
    row.totalMembers !== null && row.totalMembers <= 3
      ? `Breadth reflects only ${row.totalMembers} S&P 100 constituent${row.totalMembers === 1 ? "" : "s"}`
      : null,
    row.coverageRatio !== null && row.coverageRatio < 1
      ? `Only ${formatCoverage(row.coverageRatio)} of members qualify for long indicators`
      : null,
  ].filter((item): item is string => Boolean(item));
  return {
    supportive,
    risks: risks.length
      ? risks.slice(0, 3)
      : ["No material snapshot-specific risk is currently flagged."],
  };
}
const styles = StyleSheet.create({
  stack: { gap: Spacing.three, paddingBottom: Spacing.four },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.two },
  context: { color: Theme.colors.textMuted, fontSize: 12, fontWeight: "700" },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.two },
  body: { color: Theme.colors.text, fontSize: 14, lineHeight: 20 },
  sectionLabel: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: "900",
    marginTop: Spacing.one,
  },
  warning: { color: Theme.colors.warning, fontSize: 12, fontWeight: "700" },
  muted: { color: Theme.colors.textMuted, fontSize: 13, fontWeight: "700" },
  relevance: {
    color: Theme.colors.success,
    fontSize: 12,
    fontWeight: "800",
    marginTop: 2,
  },
  stock: {
    alignItems: "center",
    borderTopColor: Theme.colors.border,
    borderTopWidth: 1,
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: Spacing.two,
  },
  stockActions: { alignItems: "flex-end", gap: Spacing.one },
  ticker: { color: Theme.colors.text, fontSize: 14, fontWeight: "900" },
  stockReturn: { color: Theme.colors.text, fontSize: 14, fontWeight: "900" },
});
