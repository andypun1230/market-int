export type RovingTabKeyEvent = {
  currentTarget: HTMLElement;
  key: string;
  preventDefault: () => void;
};

export function nextRovingTabIndex(current: number, count: number, key: string) {
  if (count <= 0) return current;
  if (key === 'Home') return 0;
  if (key === 'End') return count - 1;
  if (key === 'ArrowRight') return (current + 1) % count;
  if (key === 'ArrowLeft') return (current - 1 + count) % count;
  return current;
}

export function webRovingTabProps({
  count,
  enabled,
  index,
  onSelect,
  selected,
}: {
  count: number;
  enabled: boolean;
  index: number;
  onSelect: (index: number) => void;
  selected: boolean;
}) {
  if (!enabled) return {};
  return {
    onKeyDown: (event: RovingTabKeyEvent) => {
      const nextIndex = nextRovingTabIndex(index, count, event.key);
      if (nextIndex === index && !['Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      onSelect(nextIndex);
      const tabs = event.currentTarget.parentElement?.querySelectorAll<HTMLElement>('[role="tab"]');
      tabs?.[nextIndex]?.focus();
    },
    tabIndex: selected ? 0 as const : -1 as const,
  };
}
