import type { ReactElement, ReactNode } from 'react';
import { useRouter } from 'expo-router';
import { SymbolView } from 'expo-symbols';
import { Pressable, SafeAreaView, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { RefreshControlProps, StyleProp, ViewStyle } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';

type AppScreenProps = {
  children: ReactNode;
  contentStyle?: StyleProp<ViewStyle>;
  refreshControl?: ReactElement<RefreshControlProps>;
  scroll?: boolean;
  showBackButton?: boolean;
  subtitle?: string;
  title?: string;
};

export function AppScreen({
  children,
  contentStyle,
  refreshControl,
  scroll = true,
  showBackButton = false,
  subtitle,
  title,
}: AppScreenProps) {
  const router = useRouter();
  const handleBack = () => {
    if (router.canGoBack()) {
      router.back();
      return;
    }
    router.replace('/');
  };

  const content = (
    <>
      {title || showBackButton ? (
        <View style={styles.header}>
          <View style={styles.titleRow}>
            {showBackButton ? (
              <Pressable
                accessibilityLabel="Go back"
                accessibilityRole="button"
                hitSlop={8}
                onPress={handleBack}
                style={({ pressed }) => [styles.backButton, pressed && styles.backButtonPressed]}>
                <SymbolView
                  name="chevron.left"
                  size={17}
                  tintColor={Theme.colors.text}
                  weight="bold"
                />
              </Pressable>
            ) : null}
            {title ? <Text style={styles.title}>{title}</Text> : null}
          </View>
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
      ) : null}
      {children}
    </>
  );

  return (
    <SafeAreaView style={styles.container}>
      {scroll ? (
        <ScrollView
          contentContainerStyle={[styles.content, contentStyle]}
          refreshControl={refreshControl}>
          {content}
        </ScrollView>
      ) : (
        <View style={[styles.content, styles.flexContent, contentStyle]}>{content}</View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Theme.colors.background,
    flex: 1,
  },
  content: {
    gap: Spacing.three,
    padding: Spacing.three,
    paddingBottom: Spacing.six,
  },
  flexContent: {
    flex: 1,
  },
  header: {
    gap: Spacing.one,
    paddingTop: Spacing.two,
  },
  titleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  backButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    height: 36,
    justifyContent: 'center',
    width: 36,
  },
  backButtonPressed: {
    opacity: 0.72,
  },
  title: {
    color: Theme.colors.textInverse,
    flex: 1,
    fontSize: 29,
    fontWeight: '900',
  },
  subtitle: {
    color: Theme.colors.textInverseMuted,
    fontSize: 15,
    lineHeight: 22,
  },
});
