import type { ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { Spacing, Theme, Typography } from '@/constants/theme';

export function WatchlistSectionHeader({
  subtitle,
  title,
}: {
  subtitle: string;
  title: string;
}) {
  return (
    <View style={styles.sectionHeader}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <Text style={styles.sectionSubtitle}>{subtitle}</Text>
    </View>
  );
}

export function WarningCard({ message, title }: { message: string; title: string }) {
  return (
    <DashboardCard accentColor={Theme.colors.warning}>
      <Text style={styles.warningTitle}>{title}</Text>
      <Text style={styles.errorText}>{message}</Text>
    </DashboardCard>
  );
}

export function InfoTile({
  label,
  value,
  valueColor,
}: {
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <View style={styles.infoTile}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={[styles.infoValue, valueColor ? { color: valueColor } : null]}>{value}</Text>
    </View>
  );
}

export function DetailGrid({ children }: { children: ReactNode }) {
  return <View style={styles.detailGrid}>{children}</View>;
}

export function ZoneSection({
  children,
  title,
  titleAccessory,
}: {
  children: ReactNode;
  title: string;
  titleAccessory?: ReactNode;
}) {
  return (
    <View style={styles.zoneSection}>
      {titleAccessory ? (
        <View style={styles.sectionTitleRow}>
          <Text style={styles.zoneSectionTitle}>{title}</Text>
          {titleAccessory}
        </View>
      ) : (
        <Text style={styles.zoneSectionTitle}>{title}</Text>
      )}
      {children}
    </View>
  );
}

export function SectionSummary({ children }: { children: ReactNode }) {
  return <Text style={styles.sectionSummary}>{children}</Text>;
}

export function NarrativeList({
  items,
  title,
  tone,
}: {
  items: string[];
  title: string;
  tone: 'success' | 'warning';
}) {
  const color = tone === 'success' ? Theme.colors.success : Theme.colors.warning;

  return (
    <View style={styles.narrativeBox}>
      <Text style={[styles.narrativeTitle, { color }]}>{title}</Text>
      {(items.length ? items : ['N/A']).map((item, index) => (
        <Text key={`${item}-${index}`} style={styles.narrativeItem}>
          {item}
        </Text>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  sectionHeader: {
    gap: Spacing.one,
    marginTop: Spacing.two,
  },
  sectionTitle: {
    color: Theme.colors.text,
    fontSize: Typography.detailTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
  sectionSubtitle: {
    color: Theme.colors.textMuted,
    fontSize: Typography.body.fontSize,
    lineHeight: 20,
  },
  warningTitle: {
    color: Theme.colors.warning,
    fontSize: Typography.supportTitle.fontSize,
    fontWeight: Typography.weights.strong,
    marginBottom: Spacing.one,
  },
  errorText: {
    color: Theme.colors.text,
    fontSize: Typography.body.fontSize,
    lineHeight: 20,
  },
  detailGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  infoTile: {
    backgroundColor: Theme.colors.cardMuted,
    borderRadius: Theme.radii.small,
    flexGrow: 1,
    minWidth: '47%',
    padding: Spacing.twoAndHalf,
  },
  infoLabel: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
    marginBottom: Spacing.one,
    textTransform: 'uppercase',
  },
  infoValue: {
    color: Theme.colors.text,
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 21,
  },
  zoneSection: {
    borderColor: Theme.colors.border,
    borderTopWidth: 1,
    gap: Spacing.two,
    marginTop: Spacing.three,
    paddingTop: Spacing.three,
  },
  sectionTitleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  zoneSectionTitle: {
    color: Theme.colors.text,
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
  },
  sectionSummary: {
    color: Theme.colors.textMuted,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.emphasis,
    lineHeight: 20,
    marginTop: Spacing.two,
  },
  narrativeBox: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.one,
    padding: Spacing.twoAndHalf,
  },
  narrativeTitle: {
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
    textTransform: 'uppercase',
  },
  narrativeItem: {
    color: Theme.colors.text,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.emphasis,
    lineHeight: 19,
  },
});
