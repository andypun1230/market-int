import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { Spacing, Theme } from '@/constants/theme';

import { AIConfidenceBadge } from './AIConfidenceBadge';
import { AIHeadline } from './AIHeadline';
import { AIBulletList } from './AIBulletList';
import { AISection } from './AISection';

type AIInsightCardProps = {
  compact?: boolean;
  confidence?: number | null;
  disclaimer?: string;
  generatedBy?: string;
  headline?: string;
  keyPoints?: string[];
  nextUpdate?: string;
  opportunities?: string[];
  risks?: string[];
  strengths?: string[];
  summary?: string;
  title: string;
  whatToWatch?: string[];
};

export function AIInsightCard({
  compact = false,
  confidence,
  disclaimer,
  generatedBy,
  headline,
  keyPoints,
  nextUpdate,
  opportunities,
  risks,
  strengths,
  summary,
  title,
  whatToWatch,
}: AIInsightCardProps) {
  const primaryPositiveItems = strengths?.length ? strengths : opportunities;

  return (
    <DashboardCard title={title} accentColor={Theme.colors.purple}>
      <View style={styles.stack}>
        <AIHeadline headline={headline} label={title} summary={summary} />
        <AIConfidenceBadge
          confidence={confidence}
          generatedBy={generatedBy}
          nextUpdate={nextUpdate}
        />

        {keyPoints?.length ? (
          <AISection title="Executive Summary">
            <AIBulletList items={keyPoints} tone="info" />
          </AISection>
        ) : null}

        {!compact && primaryPositiveItems?.length ? (
          <AISection title={strengths?.length ? 'Strengths' : 'Opportunities'}>
            <AIBulletList items={primaryPositiveItems} tone="success" />
          </AISection>
        ) : null}

        {!compact && risks?.length ? (
          <AISection title="Risks">
            <AIBulletList items={risks} tone="warning" />
          </AISection>
        ) : null}

        {!compact && whatToWatch?.length ? (
          <AISection title="What to Watch">
            <AIBulletList items={whatToWatch} tone="purple" />
          </AISection>
        ) : null}

        {disclaimer ? <Text style={styles.disclaimer}>{disclaimer}</Text> : null}
      </View>
    </DashboardCard>
  );
}

const styles = StyleSheet.create({
  disclaimer: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
    lineHeight: 16,
  },
  stack: {
    gap: Spacing.twoAndHalf,
  },
});
