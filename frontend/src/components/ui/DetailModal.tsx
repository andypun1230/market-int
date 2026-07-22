import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { AccessibilityInfo, Modal, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';

type DetailModalProps = {
  children: ReactNode;
  onClose: () => void;
  scrollHeader?: ReactNode;
  stickyHeader?: ReactNode;
  subtitle?: string;
  title: string;
  visible: boolean;
};

export function DetailModal({
  children,
  onClose,
  scrollHeader,
  stickyHeader,
  subtitle,
  title,
  visible,
}: DetailModalProps) {
  const hasStickyHeader = stickyHeader != null;
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    const subscription = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduceMotion);
    return () => subscription.remove();
  }, []);

  return (
    <Modal animationType={reduceMotion ? 'none' : 'slide'} onRequestClose={onClose} transparent visible={visible}>
      <View style={styles.backdrop}>
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.sheet}>
            <View style={styles.handle} />
            <View style={styles.header}>
              <View style={styles.titleBlock}>
                <Text style={styles.title}>{title}</Text>
                {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
              </View>
              <Pressable
                accessibilityLabel={`Close ${title}`}
                accessibilityRole="button"
                hitSlop={8}
                onPress={onClose}
                style={styles.closeButton}>
                <Text style={styles.closeText}>Close</Text>
              </Pressable>
            </View>

            <ScrollView
              contentContainerStyle={hasStickyHeader ? styles.stickyContent : styles.content}
              showsVerticalScrollIndicator={false}
              stickyHeaderIndices={hasStickyHeader ? [1] : undefined}>
              {hasStickyHeader ? <View style={styles.scrollHeader}>{scrollHeader}</View> : null}
              {hasStickyHeader ? <View style={styles.stickyHeader}>{stickyHeader}</View> : null}
              {hasStickyHeader ? <View style={styles.scrollBody}>{children}</View> : children}
            </ScrollView>
          </View>
        </SafeAreaView>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    backgroundColor: 'rgba(2, 6, 23, 0.78)',
    flex: 1,
    justifyContent: 'flex-end',
  },
  safeArea: {
    flex: 1,
    justifyContent: 'flex-end',
    paddingHorizontal: Spacing.one,
  },
  sheet: {
    backgroundColor: Theme.colors.background,
    borderColor: Theme.colors.border,
    borderTopLeftRadius: Theme.radii.card,
    borderTopRightRadius: Theme.radii.card,
    borderWidth: 1,
    maxHeight: '88%',
    overflow: 'hidden',
  },
  handle: {
    alignSelf: 'center',
    backgroundColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    height: 4,
    marginTop: Spacing.two,
    width: 42,
  },
  header: {
    alignItems: 'flex-start',
    borderBottomColor: Theme.colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.three,
    paddingBottom: Spacing.twoAndHalf,
    paddingTop: Spacing.two,
  },
  titleBlock: {
    flex: 1,
    gap: Spacing.one,
  },
  title: {
    color: Theme.colors.text,
    fontSize: 20,
    fontWeight: '900',
    lineHeight: 26,
  },
  subtitle: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    lineHeight: 19,
  },
  closeButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    justifyContent: 'center',
    minHeight: 44,
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.one,
  },
  closeText: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '900',
  },
  content: {
    gap: Spacing.three,
    padding: Spacing.three,
    paddingBottom: Spacing.five,
  },
  scrollBody: {
    gap: Spacing.three,
    paddingBottom: Spacing.five,
    paddingHorizontal: Spacing.three,
    paddingTop: Spacing.three,
  },
  scrollHeader: {
    gap: Spacing.three,
    paddingHorizontal: Spacing.three,
    paddingTop: Spacing.three,
    paddingBottom: Spacing.three,
  },
  stickyContent: {
    paddingBottom: 0,
  },
  stickyHeader: {
    backgroundColor: Theme.colors.background,
    borderBottomColor: Theme.colors.border,
    borderBottomWidth: 1,
    elevation: 6,
    paddingHorizontal: Spacing.one,
    paddingVertical: Spacing.two,
    shadowColor: '#000000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.18,
    shadowRadius: 6,
    zIndex: 20,
  },
});
