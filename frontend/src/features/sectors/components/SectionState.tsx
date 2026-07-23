import { StyleSheet, Text, View } from 'react-native';

import { EmptyState } from '@/components/ui/EmptyState';
import { Spacing, Theme, Typography } from '@/constants/theme';

type SectionEmptyStateProps = {
  actionLabel?: string;
  message?: string;
  onAction?: () => void;
  title: string;
};

type SectionErrorStateProps = {
  developmentDetails?: string;
  message: string;
  onRetry?: () => void;
};

export function SectionEmptyState(props: SectionEmptyStateProps) {
  return <EmptyState {...props} />;
}

export function SectionErrorState({ developmentDetails, message, onRetry }: SectionErrorStateProps) {
  return (
    <EmptyState
      actionLabel={onRetry ? 'Retry' : undefined}
      message={__DEV__ && developmentDetails ? `${message}\n${developmentDetails}` : message}
      onAction={onRetry}
      title="Unable to load this section"
    />
  );
}

export function SectionPartialState({ message }: { message: string }) {
  return (
    <View style={styles.partial}>
      <Text style={styles.partialText}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  partial: {
    backgroundColor: Theme.colors.warningSoft,
    borderColor: Theme.colors.warning,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    padding: Spacing.two,
  },
  partialText: {
    color: Theme.colors.warning,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 17,
  },
});
