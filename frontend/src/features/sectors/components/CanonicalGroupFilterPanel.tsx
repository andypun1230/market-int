import { Pressable, StyleSheet, Text, View } from "react-native";

import { DashboardCard } from "@/components/cards/DashboardCard";
import { Spacing, Theme, Typography } from "@/constants/theme";
import {
  DEFAULT_CANONICAL_GROUP_FILTERS,
  type CanonicalGroupFilters,
} from "@/features/sectors/groupIntelligence";

export function CanonicalGroupFilterPanel({
  filters,
  onChange,
  resultCount,
  totalCount,
}: {
  filters: CanonicalGroupFilters;
  onChange: (filters: CanonicalGroupFilters) => void;
  resultCount: number;
  totalCount: number;
}) {
  return (
    <DashboardCard
      title="Canonical Filters"
      subtitle={`${resultCount} of ${totalCount} entities match. Filters use published snapshot fields.`}
      accentColor={Theme.colors.accent}>
      <View style={styles.stack}>
        <Options
          label="State / quadrant"
          options={["all", "leading", "improving", "weakening", "lagging"] as const}
          selected={filters.quadrant}
          onSelect={(quadrant) => onChange({ ...filters, quadrant })}
        />
        <Options
          label="Rank"
          options={[null, 3, 5, 10] as const}
          selected={filters.rankMaximum}
          format={(value) => value === null ? "All" : `Top ${value}`}
          onSelect={(rankMaximum) => onChange({ ...filters, rankMaximum })}
        />
        <Options
          label="Breadth above 50 EMA"
          options={[null, 50, 65] as const}
          selected={filters.breadthMinimum}
          format={(value) => value === null ? "All" : `≥ ${value}%`}
          onSelect={(breadthMinimum) => onChange({ ...filters, breadthMinimum })}
        />
        <Options
          label="Relative momentum"
          options={[null, 50, 100] as const}
          selected={filters.momentumMinimum}
          format={(value) => value === null ? "All" : `≥ ${value}`}
          onSelect={(momentumMinimum) => onChange({ ...filters, momentumMinimum })}
        />
        <Options
          label="Movement"
          options={["all", "gaining", "losing", "stable"] as const}
          selected={filters.movement}
          onSelect={(movement) => onChange({ ...filters, movement })}
        />
        <Options
          label="Availability"
          options={["all", "available", "partial", "unavailable"] as const}
          selected={filters.availability}
          onSelect={(availability) => onChange({ ...filters, availability })}
        />
        <View style={styles.options}>
          <Toggle label="Saved only" active={filters.savedOnly} onPress={() => onChange({ ...filters, savedOnly: !filters.savedOnly })} />
          <Toggle label="Strong rank movement" active={filters.strongMovement} onPress={() => onChange({ ...filters, strongMovement: !filters.strongMovement })} />
          <Toggle label="Recent transition" active={filters.recentTransition} onPress={() => onChange({ ...filters, recentTransition: !filters.recentTransition })} />
        </View>
        <Pressable
          accessibilityRole="button"
          onPress={() => onChange(DEFAULT_CANONICAL_GROUP_FILTERS)}
          style={({ pressed }) => [styles.reset, pressed && styles.pressed]}>
          <Text style={styles.resetText}>Reset filters</Text>
        </Pressable>
      </View>
    </DashboardCard>
  );
}

function Options<T extends string | number | null>({
  format = defaultFormat,
  label,
  onSelect,
  options,
  selected,
}: {
  format?: (value: T) => string;
  label: string;
  onSelect: (value: T) => void;
  options: readonly T[];
  selected: T;
}) {
  return (
    <View style={styles.group}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.options}>
        {options.map((option) => {
          const active = option === selected;
          return (
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ selected: active }}
              key={String(option)}
              onPress={() => onSelect(option)}
              style={({ pressed }) => [styles.option, active && styles.optionActive, pressed && styles.pressed]}>
              <Text style={[styles.optionText, active && styles.optionTextActive]}>{format(option)}</Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

function Toggle({ active, label, onPress }: { active: boolean; label: string; onPress: () => void }) {
  return (
    <Pressable accessibilityRole="checkbox" accessibilityState={{ checked: active }} onPress={onPress} style={[styles.option, active && styles.optionActive]}>
      <Text style={[styles.optionText, active && styles.optionTextActive]}>{label}</Text>
    </Pressable>
  );
}

function defaultFormat(value: string | number | null) {
  if (value === null || value === "all") return "All";
  return String(value).replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
}

const styles = StyleSheet.create({
  group: { gap: Spacing.one },
  label: { color: Theme.colors.text, fontSize: Typography.control.fontSize, fontWeight: Typography.weights.strong },
  option: { backgroundColor: Theme.colors.cardMuted, borderColor: Theme.colors.border, borderRadius: Theme.radii.pill, borderWidth: 1, paddingHorizontal: Spacing.two, paddingVertical: 7 },
  optionActive: { backgroundColor: Theme.colors.accentSoft, borderColor: Theme.colors.accent },
  optionText: { color: Theme.colors.textMuted, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.strong },
  optionTextActive: { color: Theme.colors.accent },
  options: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.one },
  pressed: { opacity: 0.78 },
  reset: { alignItems: "center", alignSelf: "flex-start", borderColor: Theme.colors.warning, borderRadius: Theme.radii.small, borderWidth: 1, minHeight: 44, paddingHorizontal: Spacing.three, paddingVertical: Spacing.two },
  resetText: { color: Theme.colors.warning, fontSize: Typography.small.fontSize, fontWeight: Typography.weights.strong },
  stack: { gap: Spacing.three },
});
