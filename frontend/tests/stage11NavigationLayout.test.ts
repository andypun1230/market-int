import {
  horizontalGutter,
  maximumContentWidth,
  modalBottomInset,
  pageBottomInset,
  selectedItemScrollOffset,
  viewportClass,
  widthPolicyForRoute,
} from '../src/architecture/layoutPolicy';
import { STATE_PRESENTATION_REGISTRY } from '../src/architecture/statePresentationRegistry';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

function run() {
  assert(pageBottomInset({ isPrimary: true, platform: 'web', safeAreaBottom: 0 }) === 86, 'web primary content reserves the 70px bar and 16px breathing space');
  assert(pageBottomInset({ isPrimary: true, platform: 'ios', safeAreaBottom: 34 }) === 108, 'native primary content reserves bar, safe area, and breathing space');
  assert(pageBottomInset({ isPrimary: false, platform: 'ios', safeAreaBottom: 34 }) === 50, 'stack screens receive safe area once without a tab-bar inset');
  assert(modalBottomInset(34) === 50, 'modal actions receive one safe-area inset plus breathing space');

  assert(viewportClass(320) === 'mobile' && horizontalGutter(320) === 16, '320px uses mobile gutters');
  assert(viewportClass(768) === 'tablet' && horizontalGutter(768) === 24, 'tablet uses tablet gutters');
  assert(viewportClass(1440) === 'desktop' && horizontalGutter(1440) === 32, 'desktop uses desktop gutters');
  assert(maximumContentWidth('full_width_analytical') === 1440, 'wide analytical content has the registered maximum');
  assert(maximumContentWidth('constrained_analytical') === 1100, 'narrative analytical content has the registered maximum');
  assert(maximumContentWidth('constrained_settings') === 800, 'settings content has the registered maximum');
  assert(maximumContentWidth('modal_content') === 760, 'modal content has the registered maximum');
  assert(widthPolicyForRoute('/market') === 'full_width_analytical', 'Market remains intentionally wide');
  assert(widthPolicyForRoute('/report') === 'constrained_analytical', 'Reports use readable analytical width');
  assert(widthPolicyForRoute('/settings') === 'constrained_settings', 'Settings uses constrained settings width');

  const first = selectedItemScrollOffset({ contentWidth: 735, itemWidth: 96, itemX: 0, viewportWidth: 273 });
  const middle = selectedItemScrollOffset({ contentWidth: 735, itemWidth: 94, itemX: 394, viewportWidth: 273 });
  const last = selectedItemScrollOffset({ contentWidth: 735, itemWidth: 80, itemX: 655, viewportWidth: 273 });
  const resized = selectedItemScrollOffset({ contentWidth: 735, itemWidth: 94, itemX: 394, viewportWidth: 500 });
  assert(first === 0, 'first item never over-scrolls');
  assert(middle === 304.5, 'middle and deep-linked items center where practical');
  assert(last === 462, 'last item clamps to the content edge');
  assert(resized === 191, 'selection offset recalculates after resize/orientation changes');
  assert(selectedItemScrollOffset({ contentWidth: 260, itemWidth: 80, itemX: 170, viewportWidth: 320 }) === 0, 'non-overflowing navigation does not scroll');

  const requiredStates = [
    'empty',
    'no_search_results',
    'unavailable',
    'partial',
    'failed',
    'maintenance',
    'permission_restricted',
    'not_generated',
    'no_saved_entities',
    'no_qualifying_results',
  ];
  assert(requiredStates.every((state) => state in STATE_PRESENTATION_REGISTRY), 'all non-loaded state types have one presentation owner');
  assert(STATE_PRESENTATION_REGISTRY.failed.tone !== STATE_PRESENTATION_REGISTRY.empty.tone, 'failed and empty states remain semantically distinct');
  assert(STATE_PRESENTATION_REGISTRY.maintenance.tone !== 'danger', 'maintenance is distinct from trading urgency');

  console.log('PASS Stage 11.2B navigation, inset, width, selection, modal, and state contracts');
}

run();
