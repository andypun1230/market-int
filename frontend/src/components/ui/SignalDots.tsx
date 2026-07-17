import { StyleSheet, Text, View } from 'react-native';

import { getToneColors, type Tone } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';

type Signal = {
  label: string;
  tone: Tone;
};

type SignalDotsProps = {
  signals: Signal[];
  showLabels?: boolean;
};

export function SignalDots({ signals, showLabels = false }: SignalDotsProps) {
  return (
    <View style={styles.row}>
      {signals.map((signal) => {
        const colors = getToneColors(signal.tone);

        return (
          <View key={signal.label} style={styles.item}>
            <View
              style={[
                styles.dot,
                { backgroundColor: colors.text, borderColor: colors.border },
              ]}
            />
            {showLabels ? <Text style={styles.label}>{signal.label}</Text> : null}
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  item: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.one,
  },
  dot: {
    borderRadius: 5,
    borderWidth: 1,
    height: 10,
    width: 10,
  },
  label: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '800',
  },
});
