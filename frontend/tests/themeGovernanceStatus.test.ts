import { normalizeThemeId } from '../src/features/themes/themeIds';
import { themeGovernancePresentation } from '../src/features/themes/themeStatus';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

const gate = themeGovernancePresentation({
  status: 'awaiting_review',
  pilot_themes: [
    { theme_id: 'memory_storage', display_name: 'Memory & Storage', review_status: 'awaiting_review' },
    { theme_id: 'cybersecurity', display_name: 'Cybersecurity', review_status: 'awaiting_review' },
  ],
});

assert(gate.title === 'Theme Intelligence is awaiting review', 'all pre-review Theme screens use the shared review title');
assert(gate.pilotThemes.map((theme) => theme.displayName).join(',') === 'Memory & Storage,Cybersecurity', 'the review gate uses backend pilot status rather than fixture data');
assert(gate.body.includes('Reviewed theme definitions'), 'the review gate explains the approval prerequisite');
assert(normalizeThemeId('memory-storage') === 'memory_storage', 'legacy kebab aliases normalize at the frontend boundary');
assert(normalizeThemeId('memory_storage') === 'memory_storage', 'canonical IDs remain stable');
assert(normalizeThemeId('Memory & Storage') === null, 'display names are not permissive aliases');
