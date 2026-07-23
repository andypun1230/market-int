const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const read = (relative) => fs.readFileSync(path.join(root, relative), 'utf8');
const failures = [];
const requireText = (relative, text, reason) => {
  if (!read(relative).includes(text)) failures.push(`${relative}: ${reason}`);
};

requireText('src/components/ui/AppScreen.tsx', 'pageBottomInset', 'AppScreen must own shared page-bottom containment');
requireText('src/components/ui/AppScreen.tsx', 'widthPolicyForRoute', 'AppScreen must own semantic route width selection');
requireText('src/components/app-tabs.web.tsx', 'LAYOUT_POLICY', 'web bottom navigation must consume the shared policy');
requireText('src/components/ui/DetailModal.tsx', "maximumContentWidth('modal_content')", 'detail modals must consume the modal width policy');
requireText('src/components/ui/DetailModal.tsx', 'modalBottomInset', 'detail modals must own their safe bottom spacing independently');
requireText('src/components/ui/HorizontalSelectionBar.tsx', 'selectedItemScrollOffset', 'horizontal navigation must reveal its selected item');
requireText('src/components/ui/SegmentedControl.tsx', 'selectedItemScrollOffset', 'overflowing segmented navigation must reveal its selected item');
requireText('src/app/(tabs)/market.tsx', '<HorizontalSelectionBar', 'Market secondary navigation must use the shared selected-visibility owner');
requireText('src/components/ui/EmptyState.tsx', 'STATE_PRESENTATION_REGISTRY', 'empty-state rendering must consume the shared state registry');
requireText('src/components/ui/SkeletonCard.tsx', "'summary' | 'chart' | 'list' | 'detail'", 'loading placeholders must use structural geometry variants');
requireText('src/app/+not-found.tsx', 'Return Home', 'the app must provide an integrated unmatched-route recovery action');

const appScreens = fs.readdirSync(path.join(root, 'src/app'), { recursive: true })
  .filter((entry) => typeof entry === 'string' && entry.endsWith('.tsx'));
for (const relative of appScreens) {
  const source = read(path.join('src/app', relative));
  if (/maxWidth:\s*(?:7[0-9]{2}|8[0-9]{2}|9[0-9]{2}|1[0-9]{3})/.test(source)) {
    failures.push(`src/app/${relative}: screen-level content maximum must come from the shared width policy`);
  }
  if (source.includes('\0')) failures.push(`src/app/${relative}: contains a NUL character`);
}

const detailModal = read('src/components/ui/DetailModal.tsx');
if (detailModal.includes("edges={['left', 'right', 'bottom']}")) {
  failures.push('src/components/ui/DetailModal.tsx: safe-area bottom would be owned twice');
}
if (!detailModal.includes('StyleSheet.absoluteFill')) {
  failures.push('src/components/ui/DetailModal.tsx: backdrop dismissal target is missing');
}

if (failures.length) {
  console.error(`FAIL Stage 11.2B navigation/layout validation (${failures.length})`);
  failures.forEach((failure) => console.error(`- ${failure}`));
  process.exit(1);
}

console.log('PASS Stage 11.2B navigation/layout source validation');
console.log('Bottom containment, selected navigation, semantic widths, modal policy, typed states, and unmatched-route recovery are registered.');
