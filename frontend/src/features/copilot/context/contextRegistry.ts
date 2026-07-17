import type { CopilotContext } from '@/features/copilot/types';

export function buildStarterPrompts(context: CopilotContext): string[] {
  if (context.focusedMetric) {
    return [
      `Explain ${context.focusedMetric.title}.`,
      'Why is it not higher?',
      'What would change this view?',
      'What is the main caution?',
    ];
  }
  switch (context.screenType) {
    case 'home':
      return [
        'Explain today’s playbook.',
        'Why is Conviction not higher?',
        'What is the biggest market risk?',
        'What would invalidate today’s view?',
      ];
    case 'market':
      return [
        'Is breadth confirming the index trend?',
        'Why is market health rated this way?',
        'Which market signal is weakest?',
        'What is the main cross-asset pressure?',
      ];
    case 'sector':
    case 'theme':
      return [
        'Why is this group leading?',
        'Is leadership broad or concentrated?',
        'What would weaken this group?',
        'Compare with another leader.',
      ];
    case 'watchlist':
      return [
        'Rank my watchlist.',
        'Which name has the strongest alignment?',
        'Which stock is weakening?',
        'Compare my top three watchlist names.',
      ];
    case 'stock':
      return [
        'Explain this stock’s setup.',
        'What is the main risk?',
        'Is this stock extended?',
        'What would invalidate the setup?',
      ];
    case 'report':
      return [
        'Explain this report in simple terms.',
        'Why is Conviction only 77?',
        'Explain the scenario probabilities.',
        'What changed since the previous report?',
      ];
    default:
      return [
        'What should I watch today?',
        'What is the main risk?',
        'Explain today’s market.',
        'What would invalidate the current view?',
      ];
  }
}
