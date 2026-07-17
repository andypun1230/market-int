import { SegmentedControl } from '@/components/ui/SegmentedControl';

type TimeIntervalSelectorProps<T extends string> = {
  intervals: readonly T[];
  selected: T;
  onChange: (value: T) => void;
  label?: string;
};

export function TimeIntervalSelector<T extends string>({
  intervals,
  label = 'Interval',
  onChange,
  selected,
}: TimeIntervalSelectorProps<T>) {
  return (
    <SegmentedControl
      label={label}
      options={intervals.map((interval) => ({ key: interval, label: interval }))}
      selectedKey={selected}
      variant="switch"
      onChange={(value) => onChange(value as T)}
    />
  );
}
