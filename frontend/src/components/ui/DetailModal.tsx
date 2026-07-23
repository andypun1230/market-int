import type { ReactNode } from 'react';
import { useEffect, useRef } from 'react';
import { KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';

import { horizontalGutter, maximumContentWidth, modalBottomInset } from '@/architecture/layoutPolicy';
import { AppButton } from '@/components/ui/AppButton';
import { Spacing, Theme, Typography } from '@/constants/theme';
import { useReducedMotion } from '@/hooks/useReducedMotion';

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
  const reduceMotion = useReducedMotion();
  const insets = useSafeAreaInsets();
  const { width: viewportWidth } = useWindowDimensions();
  const returnFocusRef = useRef<HTMLElement | null>(null);

  const restoreFocus = () => {
    if (typeof document === 'undefined') return;
    const originalTrigger = returnFocusRef.current;
    const originalLabel = originalTrigger?.getAttribute('aria-label')?.toLocaleLowerCase() ?? '';
    if (originalTrigger
      && originalTrigger !== document.body
      && originalTrigger.isConnected
      && !originalLabel.startsWith('close ')
      && !originalLabel.startsWith('dismiss ')) {
      originalTrigger.focus();
      return;
    }

    // Canonical routing can replace the launch surface (for example Search ->
    // Stock Detail -> Watchlist). Restore to the matching visible entity
    // control when the original search result no longer exists.
    const titleKey = title.toLocaleLowerCase();
    const entityControl = [...document.querySelectorAll<HTMLElement>('[aria-label]')]
      .find((element) => {
        const label = element.getAttribute('aria-label')?.toLocaleLowerCase() ?? '';
        const rect = element.getBoundingClientRect();
        return label.includes(titleKey)
          && !label.startsWith('close ')
          && !label.startsWith('dismiss ')
          && rect.width > 0
          && rect.height > 0;
      });
    entityControl?.focus();
  };

  const close = () => {
    onClose();
    if (typeof window !== 'undefined') window.setTimeout(restoreFocus, reduceMotion ? 50 : 500);
  };

  useEffect(() => {
    if (typeof document === 'undefined') return;
    if (visible) {
      returnFocusRef.current = document.activeElement as HTMLElement | null;
      const focusTimer = window.setTimeout(() => {
        const closeControl = [...document.querySelectorAll<HTMLElement>('[aria-label]')]
          .find((element) => element.getAttribute('aria-label') === `Close ${title}`);
        closeControl?.focus();
      }, 50);
      return () => window.clearTimeout(focusTimer);
    }
  }, [title, visible]);

  const contentBottom = modalBottomInset(insets.bottom);
  const sideGutter = horizontalGutter(viewportWidth);

  return (
    <Modal animationType={reduceMotion ? 'none' : 'slide'} onRequestClose={close} transparent visible={visible}>
      <View style={styles.backdrop}>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.keyboardAvoidingView}>
          <SafeAreaView edges={['left', 'right']} style={[styles.safeArea, { paddingHorizontal: sideGutter }]}>
          <View accessibilityLabel={title} accessibilityViewIsModal role="dialog" style={styles.sheet}>
            <View accessibilityElementsHidden aria-hidden importantForAccessibility="no-hide-descendants" style={styles.handle} />
            <View style={styles.header}>
              <View style={styles.titleBlock}>
                <Text style={styles.title}>{title}</Text>
                {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
              </View>
              <AppButton
                accessibilityLabel={`Close ${title}`}
                label="Close"
                onPress={close}
                style={styles.closeButton}
                variant="neutral"
              />
            </View>

            <ScrollView
              contentContainerStyle={hasStickyHeader
                ? [styles.stickyContent, { paddingBottom: contentBottom }]
                : [styles.content, { paddingBottom: contentBottom }]}
              showsVerticalScrollIndicator={false}
              stickyHeaderIndices={hasStickyHeader ? [1] : undefined}>
              {hasStickyHeader ? <View style={styles.scrollHeader}>{scrollHeader}</View> : null}
              {hasStickyHeader ? <View style={styles.stickyHeader}>{stickyHeader}</View> : null}
              {hasStickyHeader ? <View style={styles.scrollBody}>{children}</View> : children}
            </ScrollView>
          </View>
          </SafeAreaView>
        </KeyboardAvoidingView>
        <Pressable
          accessibilityLabel={`Dismiss ${title}`}
          accessibilityRole="button"
          onPress={close}
          style={[StyleSheet.absoluteFill, styles.backdropDismissal]}
        />
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
  backdropDismissal: {
    zIndex: 0,
  },
  safeArea: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'flex-end',
    pointerEvents: 'box-none',
    width: '100%',
  },
  keyboardAvoidingView: {
    flex: 1,
    justifyContent: 'flex-end',
    pointerEvents: 'box-none',
    zIndex: 1,
  },
  sheet: {
    backgroundColor: Theme.colors.background,
    borderColor: Theme.colors.border,
    borderTopLeftRadius: Theme.radii.card,
    borderTopRightRadius: Theme.radii.card,
    borderWidth: 1,
    maxWidth: maximumContentWidth('modal_content'),
    maxHeight: '88%',
    minHeight: 280,
    overflow: 'hidden',
    width: '100%',
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
    fontSize: Typography.detailTitle.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 26,
  },
  subtitle: {
    color: Theme.colors.textMuted,
    fontSize: Typography.control.fontSize,
    lineHeight: 19,
  },
  closeButton: {
    paddingHorizontal: Spacing.twoAndHalf,
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
