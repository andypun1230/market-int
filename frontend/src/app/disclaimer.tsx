import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { Spacing, Theme } from '@/constants/theme';

const DISCLAIMERS = [
  'Market Intelligence is provided for informational and educational purposes only. It does not provide personalized investment, financial, legal, or tax advice.',
  'Market data, indicators, ratings, reports, AI-generated content, and rules-based analysis may be delayed, incomplete, or inaccurate.',
  'Nothing in the app is a recommendation to buy, sell, or hold any security or financial instrument.',
  'Investing involves risk, including the possible loss of principal. Past performance does not guarantee future results.',
  'Users are responsible for conducting their own research and consulting qualified professionals before making financial decisions.',
  'No guarantee is made regarding data accuracy, data availability, notification timing, report completeness, or AI output quality.',
  'Simulated or mock data is for interface development and education only and must not be treated as live market data.',
  'The app provider is not liable for trading losses or decisions made from app content.',
];

export default function FinancialDisclaimerScreen() {
  return (
    <AppScreen showBackButton title="Financial Disclaimer" subtitle="Important educational-use limitations.">
      <DashboardCard title="Educational Use Only" accentColor={Theme.colors.warning}>
        <View style={styles.stack}>
          {DISCLAIMERS.map((item) => (
            <View key={item} style={styles.item}>
              <View style={styles.bullet} />
              <Text style={styles.text}>{item}</Text>
            </View>
          ))}
        </View>
      </DashboardCard>
    </AppScreen>
  );
}

const styles = StyleSheet.create({
  bullet: {
    backgroundColor: Theme.colors.warning,
    borderRadius: 4,
    height: 8,
    marginTop: 7,
    width: 8,
  },
  item: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  stack: {
    gap: Spacing.two,
  },
  text: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 14,
    lineHeight: 22,
  },
});
