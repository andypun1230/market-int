import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import type { CopilotSourceState } from '@/features/copilot/types';

export function CopilotSourceBadge({ sourceState }: { sourceState: CopilotSourceState }) {
  return <StatusBadge label={labelForSource(sourceState)} tone={toneForSource(sourceState)} />;
}

function labelForSource(sourceState: CopilotSourceState) {
  switch (sourceState) {
    case 'live':
      return 'Live context';
    case 'cached':
      return 'Cached context';
    case 'stale':
      return 'Stale context';
    case 'mock':
      return 'Mock context';
    case 'test':
      return 'Test context';
    case 'partial':
      return 'Partial context';
    case 'mixed':
      return 'Mixed context';
    case 'delayed':
      return 'Delayed context';
    default:
      return 'Context limited';
  }
}

function toneForSource(sourceState: CopilotSourceState): Tone {
  switch (sourceState) {
    case 'live':
      return 'success';
    case 'cached':
    case 'mixed':
      return 'info';
    case 'stale':
    case 'test':
    case 'mock':
    case 'partial':
    case 'delayed':
      return 'warning';
    default:
      return 'muted';
  }
}
