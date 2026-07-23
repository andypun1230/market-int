import { ACCESSIBILITY_POLICY, contrastRatio } from '../src/architecture/accessibilityPolicy';
import { TERMINOLOGY, availabilityTerm } from '../src/architecture/terminologyRegistry';
import { nextRovingTabIndex } from '../src/architecture/keyboardNavigation';
import {
  dateFreshnessLabel,
  formatLocalizedDate,
  formatLocalizedDateTime,
} from '../src/features/trust/dateFreshnessPresentation';
import { resolveReducedMotion } from '../src/features/preferences/reducedMotionPolicy';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

function run() {
  assert(
    contrastRatio('#A855F7', '#0F172A') >= ACCESSIBILITY_POLICY.contrast.normalTextMinimum,
    'purple semantic text meets normal-text contrast',
  );
  assert(
    contrastRatio('#EF4444', '#111827') >= ACCESSIBILITY_POLICY.contrast.normalTextMinimum,
    'danger semantic text meets normal-text contrast',
  );
  assert(
    contrastRatio('#38BDF8', '#0F172A') >= ACCESSIBILITY_POLICY.contrast.nonTextMinimum,
    'focus ring meets non-text contrast',
  );
  assert(ACCESSIBILITY_POLICY.touch.minimumHeight === 44 && ACCESSIBILITY_POLICY.touch.minimumWidth === 44, 'touch contract is 44 by 44');
  assert(ACCESSIBILITY_POLICY.smallText.essentialMinimum === 11, 'essential text minimum remains the caption role');

  assert(availabilityTerm('cached') === TERMINOLOGY.availability.liveCached, 'cached availability has one term');
  assert(availabilityTerm('N/A') === TERMINOLOGY.availability.unavailable, 'raw N/A states are normalized');
  assert(availabilityTerm('partial_data') === TERMINOLOGY.availability.partial, 'partial enums are normalized');

  const now = new Date('2026-07-24T12:00:00.000Z');
  const options = { locale: 'en-US', now, timeZone: 'UTC' } as const;
  assert(dateFreshnessLabel('2026-07-24T11:59:40.000Z', options) === 'Updated just now', 'just-now boundary is deterministic');
  assert(dateFreshnessLabel('2026-07-24T11:59:00.000Z', options) === 'Updated 1 minute ago', 'minute grammar is deterministic');
  assert(dateFreshnessLabel('2026-07-24T10:00:00.000Z', options) === 'Updated 2 hours ago', 'hour grammar is deterministic');
  assert(dateFreshnessLabel('2026-07-23T12:00:00.000Z', options) === 'Updated yesterday', 'yesterday grammar is deterministic');
  assert(dateFreshnessLabel('2026-07-20T12:00:00.000Z', options) === 'Updated on Jul 20, 2026', 'older updates use a localized date');
  assert(dateFreshnessLabel('2026-07-24T09:00:00.000Z', { ...options, kind: 'cached' }) === 'Cached from 9:00 AM', 'cache time is distinguished');
  assert(dateFreshnessLabel('2026-07-22', { ...options, kind: 'evidence-through' }) === 'Evidence through Jul 22, 2026', 'evidence cutoffs are not called updates');
  assert(formatLocalizedDate('2026-07-22', options) === 'Jul 22, 2026', 'date-only formatter is locale and timezone deterministic');
  assert(formatLocalizedDateTime('2026-07-22T14:30:00.000Z', options) === 'Jul 22, 2026, 2:30 PM', 'timestamp formatter respects locale policy');

  assert(resolveReducedMotion(false, false) === false, 'motion remains available when both preferences allow it');
  assert(resolveReducedMotion(true, false) && resolveReducedMotion(false, true), 'either app or platform preference reduces motion');
  assert(nextRovingTabIndex(0, 4, 'ArrowLeft') === 3, 'horizontal tabs wrap left');
  assert(nextRovingTabIndex(3, 4, 'ArrowRight') === 0, 'horizontal tabs wrap right');
  assert(nextRovingTabIndex(2, 4, 'Home') === 0 && nextRovingTabIndex(1, 4, 'End') === 3, 'horizontal tabs support Home and End');

  console.log('PASS Stage 11.2C accessibility policy, terminology, deterministic dates, contrast, and reduced motion');
}

run();
