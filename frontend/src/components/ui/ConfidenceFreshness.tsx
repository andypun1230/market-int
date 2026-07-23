import { StyleSheet, Text } from 'react-native';

import { Theme, Typography } from '@/constants/theme';
import { freshnessLabel } from '@/features/trust/confidenceFreshnessPresentation';

export {
  availabilityLabel,
  confidenceLabel,
  evidenceFreshnessLabel,
  freshnessLabel,
  providerLabel,
} from '@/features/trust/confidenceFreshnessPresentation';

export function FreshnessText({ value }: { value?: string | null }) {
  return <Text style={styles.freshness}>{freshnessLabel(value)}</Text>;
}

const styles = StyleSheet.create({
  freshness: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.emphasis,
    lineHeight: Typography.caption.lineHeight,
  },
});
