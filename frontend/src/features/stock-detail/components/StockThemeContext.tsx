import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';
import type { SymbolThemeMappingsResponse } from '@/types/market';

export function StockThemeContext({ mappings }: { mappings: SymbolThemeMappingsResponse | null | undefined }) {
  const items = mappings?.items ?? [];
  return (
    <DashboardCard title="Theme Exposure" subtitle={`Canonical taxonomy ${mappings?.taxonomy_version ?? 'unavailable'}`} accentColor={Theme.colors.purple}>
      {items.length ? items.map((item, index) => (
        <View key={item.theme_id} style={styles.row}>
          <View style={styles.copy}>
            <Text style={styles.name}>{item.theme_name ?? item.theme_id}</Text>
            <Text style={styles.rationale}>{item.rationale}</Text>
          </View>
          <StatusBadge label={`${index === 0 ? 'Primary · ' : ''}${item.exposure}`} tone={item.exposure === 'core' ? 'success' : item.exposure === 'significant' ? 'info' : 'muted'} />
        </View>
      )) : <Text style={styles.unavailable}>No canonical theme mapping is available for this symbol.</Text>}
    </DashboardCard>
  );
}

const styles = StyleSheet.create({
  copy: { flex: 1, gap: Spacing.half },
  name: { color: Theme.colors.text, fontSize: Typography.control.fontSize, fontWeight: Typography.weights.strong },
  rationale: { color: Theme.colors.textMuted, fontSize: Typography.small.fontSize, lineHeight: 17 },
  row: { alignItems: 'flex-start', borderTopColor: Theme.colors.border, borderTopWidth: 1, flexDirection: 'row', gap: Spacing.two, paddingVertical: Spacing.two },
  unavailable: { color: Theme.colors.textMuted, fontSize: Typography.control.fontSize },
});
