import type { ReactNode } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { Spacing } from '@/constants/theme';

type DetailTab = {
  content: ReactNode;
  key: string;
  label: string;
};

type TabbedDetailPanelProps = {
  initialKey?: string;
  onChange?: (key: string) => void;
  tabs: DetailTab[];
};

export function TabbedDetailPanel({ initialKey, onChange, tabs }: TabbedDetailPanelProps) {
  const firstKey = tabs[0]?.key ?? '';
  const [selectedKey, setSelectedKey] = useState(initialKey ?? firstKey);
  const selectedTab = useMemo(
    () => tabs.find((tab) => tab.key === selectedKey) ?? tabs[0],
    [selectedKey, tabs],
  );

  useEffect(() => {
    if (selectedTab?.key) {
      onChange?.(selectedTab.key);
    }
  }, [onChange, selectedTab?.key]);

  if (!tabs.length) {
    return null;
  }

  return (
    <View style={styles.container}>
      <SegmentedControl
        options={tabs.map((tab) => ({ key: tab.key, label: tab.label }))}
        selectedKey={selectedTab.key}
        onChange={setSelectedKey}
      />
      <View style={styles.content}>{selectedTab.content}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: Spacing.three,
  },
  content: {
    gap: Spacing.three,
  },
});
