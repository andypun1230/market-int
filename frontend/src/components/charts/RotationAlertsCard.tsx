import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { TestDataBadge } from '@/components/ui/TestDataBadge';
import { Spacing, Theme } from '@/constants/theme';
import type { RotationAlert } from '@/data/sectorTabTestData';
import { SectionEmptyState } from '@/features/sectors/components/SectionState';

type RotationAlertsCardProps = {
  alerts: RotationAlert[];
  title: string;
};

export function RotationAlertsCard({ alerts, title }: RotationAlertsCardProps) {
  return (
    <DashboardCard title={title} accentColor={Theme.colors.warning}>
      <View style={styles.headerRow}>
        <Text style={styles.subtitle}>Rule-based changes from the current test window.</Text>
        <TestDataBadge />
      </View>
      <View style={styles.stack}>
        {alerts.length ? (
          alerts.map((alert) => (
            <View key={alert.id} style={styles.alertRow}>
              <View>
                <Text style={styles.alertName}>{alert.name}</Text>
                <Text style={styles.alertMessage}>{alert.message}</Text>
              </View>
              <Text style={styles.alertMeta}>{alert.interval} rotation</Text>
            </View>
          ))
        ) : (
          <SectionEmptyState
            message="No major rotation changes in the selected test window."
            title="No rotation alerts"
          />
        )}
      </View>
    </DashboardCard>
  );
}

const styles = StyleSheet.create({
  alertMessage: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '800',
  },
  alertMeta: {
    color: Theme.colors.warning,
    fontSize: 11,
    fontWeight: '900',
  },
  alertName: {
    color: Theme.colors.text,
    fontSize: 14,
    fontWeight: '900',
  },
  alertRow: {
    alignItems: 'flex-start',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
    padding: Spacing.two,
  },
  headerRow: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    justifyContent: 'space-between',
    marginBottom: Spacing.two,
  },
  stack: {
    gap: Spacing.two,
  },
  subtitle: {
    color: Theme.colors.textMuted,
    flex: 1,
    fontSize: 12,
    fontWeight: '800',
    lineHeight: 17,
  },
});
