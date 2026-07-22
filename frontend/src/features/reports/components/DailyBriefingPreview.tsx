import { SymbolView } from 'expo-symbols';
import { StyleSheet, Text, View } from 'react-native';

import { EmptyState } from '@/components/ui/EmptyState';
import { ExpandableSection } from '@/components/ui/ExpandableSection';
import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import { AskCopilotButton } from '@/features/copilot/components/AskCopilotButton';
import { createCopilotContext } from '@/features/copilot/context/buildScreenContext';
import { buildDailyBriefing } from '@/features/reports/dailyBriefingModel';
import type { DailyReportRecord } from '@/features/reports/reportLibraryModel';
import { ReportDocumentPreview } from '@/features/reports/components/ReportDocumentPreview';

export function DailyBriefingPreview({
  initialSectionId,
  record,
}: {
  initialSectionId?: string;
  record: DailyReportRecord;
}) {
  const report = record.snapshot;
  if (!report) return <EmptyState title="Preview unavailable" message="This report snapshot is not available." />;
  if (report.report_document && ['daily-report-pdf-v6', 'daily-report-pdf-v7'].includes(report.report_document.pdf_format_version)) {
    return <ReportDocumentPreview document={report.report_document} initialSectionId={initialSectionId} />;
  }
  const briefing = buildDailyBriefing(report);
  const copilotContext = createCopilotContext({
    payload: {
      confidence: report.recommendation_confidence,
      conviction: report.market_conviction,
      marketDate: record.metadata.marketDate,
      reportChanges: report.report_changes,
      reportId: report.report_id,
      reportNarrative: report.report_narrative,
      scenarioPlan: report.scenario_plan,
      watchlistRanking: report.watchlist_summary,
    },
    routeName: '/report',
    screenTitle: `Daily Market Intelligence Briefing · ${record.metadata.marketDate}`,
    screenType: 'report',
    sourceState: record.metadata.sourceState,
  });

  return (
    <View style={styles.stack}>
      <AskCopilotButton context={copilotContext} prompt="Explain this briefing and its key trade-offs." />
      <View style={styles.cover}>
        <Text style={styles.eyebrow}>DAILY MARKET INTELLIGENCE</Text>
        <Text style={styles.title}>The Briefing</Text>
        <Text style={styles.date}>{formatMarketDate(record.metadata.marketDate)} · Version {record.metadata.version}</Text>
        <Text style={styles.coverNarrative}>{briefing.narrative}</Text>
        <View style={styles.badgeRow}>
          <StatusBadge label={briefing.regime} tone="success" />
          <StatusBadge label={`${briefing.confidence.label} confidence`} tone={confidenceTone(briefing.confidence.score)} />
          <StatusBadge label={briefing.appendix.sourceState} tone={sourceTone(briefing.appendix.sourceState)} />
        </View>
      </View>

      <ExpandableSection defaultExpanded summary={briefing.highestConviction} title="Executive Summary">
        <View style={styles.sectionStack}>
          <LabeledText label="Overall Thesis" value={briefing.narrative} />
          <View style={styles.metricRow}>
            <Metric label="Confidence" value={briefing.confidence.score === null ? briefing.confidence.label : `${Math.round(briefing.confidence.score)}% · ${briefing.confidence.label}`} />
            <Metric label="Highest Conviction" value={briefing.highestConviction} />
            <Metric label="Largest Risk" value={briefing.majorRisk} warning />
          </View>
          <SignalList items={briefing.drivers} title="Primary Drivers" />
          {briefing.confidence.reason ? <LabeledText label="Why This Confidence" value={briefing.confidence.reason} /> : null}
        </View>
      </ExpandableSection>

      <ExpandableSection summary={briefing.changes.summary} title="What Changed Today">
        {briefing.changes.items.length ? (
          <View style={styles.sectionStack}>
            {briefing.changes.items.map((item, index) => (
              <View key={`${item.label}-${index}`} style={styles.changeRow}>
                <View style={styles.changeHeader}>
                  <Text style={styles.itemTitle}>{item.label}</Text>
                  <StatusBadge label={capitalize(item.direction)} tone={directionTone(item.direction)} />
                </View>
                <Text style={styles.transition}>{item.previous}  →  {item.current}</Text>
                {item.reason ? <Text style={styles.body}>{item.reason}</Text> : null}
              </View>
            ))}
          </View>
        ) : <EvidenceFallback text={briefing.changes.summary} />}
      </ExpandableSection>

      <ExpandableSection summary={briefing.crossMarket[0] ?? 'Cross-engine evidence is limited.'} title="Why It Happened">
        {briefing.crossMarket.length ? <RelationshipFlow items={briefing.crossMarket} /> : <EvidenceFallback text="No supported cross-signal relationship is available for this report." />}
      </ExpandableSection>

      <ExpandableSection summary="Connected evidence across market engines" title="Cross-Market Analysis">
        <View style={styles.sectionStack}>
          <LabeledText label="Market Posture" value={briefing.regime} />
          <LabeledText label="Leadership Link" value={briefing.highestConviction} />
          <LabeledText label="Risk Constraint" value={briefing.majorRisk} />
          <SignalList items={briefing.crossMarket} title="Confirmed Relationships" />
        </View>
      </ExpandableSection>

      <ExpandableSection summary={briefing.leadership.current[0] ?? briefing.primaryTheme} title="Leadership Intelligence">
        <View style={styles.metricRow}>
          <NamedList items={briefing.leadership.current} label="Current Leaders" tone="success" />
          <NamedList items={briefing.leadership.emerging} label="Emerging" tone="info" />
          <NamedList items={briefing.leadership.weakening} label="Weakening" tone="warning" />
          <NamedList items={briefing.leadership.monitor} label="Monitor Next" tone="muted" />
        </View>
      </ExpandableSection>

      <ExpandableSection summary={briefing.majorRisk} title="Risk Assessment">
        <View style={styles.sectionStack}>
          <SignalList items={briefing.risks.warnings} title="Hidden Weaknesses" tone="warning" />
          <SignalList items={briefing.risks.confirmations} title="Hidden Strengths" tone="success" />
          <SignalList items={briefing.risks.invalidation} title="Thesis Invalidation" tone="danger" />
        </View>
      </ExpandableSection>

      <ExpandableSection summary={`${briefing.scenarios.length} evidence-based scenarios`} title="Scenario Planning">
        {briefing.scenarios.length ? <View style={styles.sectionStack}>{briefing.scenarios.map((scenario) => (
          <View key={scenario.name} style={styles.scenario}>
            <View style={styles.changeHeader}>
              <Text style={styles.itemTitle}>{scenario.name}</Text>
              {scenario.probability ? <StatusBadge label={scenario.probability} tone="muted" /> : null}
            </View>
            <LabeledText label="Conditions" value={scenario.conditions} />
            <LabeledText label="Expectation" value={scenario.expectation} />
            <LabeledText label="What Changes It" value={scenario.invalidation} />
            <LabeledText label="Response" value={scenario.response} />
          </View>
        ))}</View> : <EvidenceFallback text="Scenario confidence is unavailable for this report." />}
      </ExpandableSection>

      <ExpandableSection summary={`${briefing.watchlist.length} personalized priorities`} title="Watchlist Intelligence">
        {briefing.watchlist.length ? <View style={styles.sectionStack}>{briefing.watchlist.map((item) => (
          <View key={`${item.category}-${item.symbol}`} style={styles.watchRow}>
            <View style={styles.symbolBox}><Text style={styles.symbol}>{item.symbol}</Text></View>
            <View style={styles.watchCopy}>
              <Text style={styles.itemEyebrow}>{item.category}</Text>
              <Text style={styles.body}>{item.detail}</Text>
            </View>
          </View>
        ))}</View> : <EvidenceFallback text="No personal watchlist or supported fallback ideas were available when this report was frozen." />}
      </ExpandableSection>

      <ExpandableSection summary={`${briefing.tomorrow.length + briefing.checklist.length} items to verify`} title="Tomorrow's Checklist">
        <View style={styles.sectionStack}>
          {briefing.checklist.map((item) => <ChecklistRow key={item.label} label={item.label} status={item.status} value={item.value} />)}
          {briefing.tomorrow.map((item, index) => <ChecklistRow key={`${item}-${index}`} label={item} status="Watch" value={null} />)}
          {!briefing.checklist.length && !briefing.tomorrow.length ? <EvidenceFallback text="No next-session checklist evidence is available." /> : null}
        </View>
      </ExpandableSection>

      <ExpandableSection summary={`${briefing.appendix.sourceState} provenance · methodology and data notes`} title="Appendix">
        <View style={styles.sectionStack}>
          <LabeledText label="Frozen Report ID" value={report.report_id ?? record.id} />
          <LabeledText label="Report Schema" value={report.report_schema_version ?? 'Unavailable'} />
          <LabeledText label="PDF Format" value={report.report_pdf_format_version ?? 'Unavailable'} />
          <LabeledText label="Source State" value={briefing.appendix.sourceState} />
          <SignalList items={briefing.appendix.notes} title="Data & Methodology Notes" />
          <Text style={styles.disclaimer}>Informational and educational use only. Not financial advice.</Text>
        </View>
      </ExpandableSection>
    </View>
  );
}

function Metric({ label, value, warning = false }: { label: string; value: string; warning?: boolean }) {
  return <View style={styles.metric}><Text style={styles.metricLabel}>{label}</Text><Text style={[styles.metricValue, warning && styles.warning]}>{value}</Text></View>;
}

function LabeledText({ label, value }: { label: string; value: string }) {
  return <View style={styles.labeled}><Text style={styles.itemEyebrow}>{label}</Text><Text style={styles.body}>{value}</Text></View>;
}

function SignalList({ items, title, tone = 'accent' }: { items: string[]; title: string; tone?: 'accent' | 'success' | 'warning' | 'danger' }) {
  if (!items.length) return <EvidenceFallback text={`${title} evidence is unavailable.`} />;
  const color = tone === 'success' ? Theme.colors.success : tone === 'warning' ? Theme.colors.warning : tone === 'danger' ? Theme.colors.danger : Theme.colors.accent;
  return <View style={styles.labeled}><Text style={styles.itemEyebrow}>{title}</Text>{items.map((item, index) => <View key={`${item}-${index}`} style={styles.bulletRow}><View style={[styles.bullet, { backgroundColor: color }]} /><Text style={styles.body}>{item}</Text></View>)}</View>;
}

function NamedList({ items, label, tone }: { items: string[]; label: string; tone: Tone }) {
  return <View style={styles.namedList}><StatusBadge label={label} tone={tone} /><Text style={styles.namedValue}>{items.length ? items.join('\n') : 'No qualified signal'}</Text></View>;
}

function RelationshipFlow({ items }: { items: string[] }) {
  return <View style={styles.sectionStack}>{items.map((item, index) => <View key={`${item}-${index}`} style={styles.flowItem}><View style={styles.flowIndex}><Text style={styles.flowIndexText}>{index + 1}</Text></View><Text style={styles.body}>{item}</Text></View>)}</View>;
}

function ChecklistRow({ label, status, value }: { label: string; status: string; value: string | null }) {
  const positive = /pass|favorable/i.test(status);
  const danger = /fail/i.test(status);
  const color = positive ? Theme.colors.success : danger ? Theme.colors.danger : Theme.colors.warning;
  return <View style={styles.checkRow}><SymbolView name={positive ? 'checkmark.circle.fill' : danger ? 'xmark.circle.fill' : 'circle'} size={18} tintColor={color} weight="bold" /><Text style={styles.checkLabel}>{label}</Text>{value ? <Text style={styles.checkValue}>{value}</Text> : null}<StatusBadge label={status} tone={positive ? 'success' : danger ? 'danger' : 'warning'} /></View>;
}

function EvidenceFallback({ text }: { text: string }) {
  return <View style={styles.fallback}><SymbolView name="info.circle" size={17} tintColor={Theme.colors.textMuted} /><Text style={styles.fallbackText}>{text}</Text></View>;
}

function formatMarketDate(value: string) {
  const parsed = new Date(`${value}T12:00:00`);
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat('en-US', { day: 'numeric', month: 'long', year: 'numeric' }).format(parsed);
}

function confidenceTone(value: number | null): Tone {
  if (value === null) return 'muted';
  if (value >= 80) return 'success';
  if (value >= 60) return 'info';
  return 'warning';
}

function sourceTone(value: string): Tone {
  if (value.toLowerCase() === 'live') return 'success';
  if (/mock|unavailable/.test(value.toLowerCase())) return 'danger';
  return 'warning';
}

function directionTone(value: string): Tone {
  if (/improv|new/.test(value)) return 'success';
  if (/weak/.test(value)) return 'danger';
  return 'warning';
}

function capitalize(value: string) { return value.charAt(0).toUpperCase() + value.slice(1); }

const styles = StyleSheet.create({
  badgeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two, marginTop: Spacing.three },
  body: { color: Theme.colors.text, flex: 1, fontSize: 14, lineHeight: 21 },
  bullet: { borderRadius: 4, height: 7, marginTop: 7, width: 7 },
  bulletRow: { alignItems: 'flex-start', flexDirection: 'row', gap: Spacing.two },
  changeHeader: { alignItems: 'center', flexDirection: 'row', gap: Spacing.two, justifyContent: 'space-between' },
  changeRow: { borderBottomColor: Theme.colors.border, borderBottomWidth: 1, gap: Spacing.two, paddingBottom: Spacing.twoAndHalf },
  checkLabel: { color: Theme.colors.text, flex: 1, fontSize: 13, fontWeight: '800' },
  checkRow: { alignItems: 'center', borderBottomColor: Theme.colors.border, borderBottomWidth: 1, flexDirection: 'row', gap: Spacing.two, minHeight: 40, paddingVertical: Spacing.two },
  checkValue: { color: Theme.colors.textMuted, fontSize: 12, fontWeight: '800' },
  cover: { backgroundColor: Theme.colors.cardElevated, borderColor: Theme.colors.border, borderRadius: Theme.radii.card, borderWidth: 1, padding: Spacing.four },
  coverNarrative: { color: Theme.colors.text, fontSize: 16, fontWeight: '700', lineHeight: 25, marginTop: Spacing.three },
  date: { color: Theme.colors.textMuted, fontSize: 12, fontWeight: '800', marginTop: Spacing.one },
  disclaimer: { color: Theme.colors.textMuted, fontSize: 11, lineHeight: 17 },
  eyebrow: { color: Theme.colors.accent, fontSize: 11, fontWeight: '900' },
  fallback: { alignItems: 'center', backgroundColor: Theme.colors.cardMuted, borderRadius: Theme.radii.small, flexDirection: 'row', gap: Spacing.two, padding: Spacing.twoAndHalf },
  fallbackText: { color: Theme.colors.textMuted, flex: 1, fontSize: 13, lineHeight: 19 },
  flowIndex: { alignItems: 'center', backgroundColor: Theme.colors.accentSoft, borderRadius: 15, height: 30, justifyContent: 'center', width: 30 },
  flowIndexText: { color: Theme.colors.accent, fontSize: 12, fontWeight: '900' },
  flowItem: { alignItems: 'flex-start', flexDirection: 'row', gap: Spacing.twoAndHalf },
  itemEyebrow: { color: Theme.colors.textMuted, fontSize: 11, fontWeight: '900' },
  itemTitle: { color: Theme.colors.text, flex: 1, fontSize: 14, fontWeight: '900' },
  labeled: { gap: Spacing.two },
  metric: { backgroundColor: Theme.colors.cardMuted, borderRadius: Theme.radii.small, flexBasis: '47%', gap: Spacing.one, minWidth: 150, padding: Spacing.twoAndHalf },
  metricLabel: { color: Theme.colors.textMuted, fontSize: 11, fontWeight: '800' },
  metricRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  metricValue: { color: Theme.colors.text, fontSize: 14, fontWeight: '900', lineHeight: 20 },
  namedList: { backgroundColor: Theme.colors.cardMuted, borderRadius: Theme.radii.small, flexBasis: '47%', gap: Spacing.two, minWidth: 150, padding: Spacing.twoAndHalf },
  namedValue: { color: Theme.colors.text, fontSize: 13, fontWeight: '800', lineHeight: 21 },
  scenario: { backgroundColor: Theme.colors.cardMuted, borderRadius: Theme.radii.small, gap: Spacing.twoAndHalf, padding: Spacing.three },
  sectionStack: { gap: Spacing.three },
  stack: { gap: Spacing.three },
  symbol: { color: Theme.colors.accent, fontSize: 13, fontWeight: '900' },
  symbolBox: { alignItems: 'center', backgroundColor: Theme.colors.accentSoft, borderRadius: Theme.radii.small, justifyContent: 'center', minHeight: 38, minWidth: 56, paddingHorizontal: Spacing.two },
  title: { color: Theme.colors.text, fontSize: 28, fontWeight: '900', marginTop: Spacing.one },
  transition: { color: Theme.colors.accent, fontSize: 15, fontWeight: '900' },
  warning: { color: Theme.colors.warning },
  watchCopy: { flex: 1, gap: Spacing.one },
  watchRow: { alignItems: 'center', borderBottomColor: Theme.colors.border, borderBottomWidth: 1, flexDirection: 'row', gap: Spacing.twoAndHalf, paddingBottom: Spacing.twoAndHalf },
});
