const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const sourceRoot = path.join(root, 'src');

function walk(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name);
    return entry.isDirectory() ? walk(target) : [target];
  });
}

function relative(file) {
  return path.relative(root, file).replaceAll(path.sep, '/');
}

function fail(message, failures) {
  failures.push(message);
}

const files = walk(sourceRoot).filter((file) => /\.tsx?$/.test(file));
const tsxFiles = files.filter((file) => file.endsWith('.tsx'));
const failures = [];

for (const file of tsxFiles) {
  const source = fs.readFileSync(file, 'utf8');
  if (/fontSize:\s*\d+/.test(source)) fail(`${relative(file)} contains an arbitrary font size`, failures);
  if (/fontWeight:\s*['"]\d+['"]/.test(source)) fail(`${relative(file)} contains an arbitrary font weight`, failures);
  if (/[★☆⌄⌃▸▾≡☷↻✓●○]/.test(source)) fail(`${relative(file)} contains a textual UI glyph`, failures);
  if (source.includes('›') && relative(file) !== 'src/components/charts/RotationQuadrantChart.tsx') {
    fail(`${relative(file)} contains an unregistered trajectory glyph`, failures);
  }
}

const expectedHeavyOwners = new Set([
  'src/components/ui/AppScreen.tsx',
  'src/components/ui/DecisionSummaryCard.tsx',
  'src/components/ui/HeroDecisionCard.tsx',
  'src/features/command/components/UniversalCommandHeader.tsx',
  'src/features/stock-detail/components/StockDetailHeader.tsx',
]);
const heavyOwners = new Set(tsxFiles
  .filter((file) => fs.readFileSync(file, 'utf8').includes('Typography.weights.heavy'))
  .map(relative));
if (heavyOwners.size !== expectedHeavyOwners.size || [...heavyOwners].some((file) => !expectedHeavyOwners.has(file))) {
  fail(`heavy typography owners differ from the registered decision/title set: ${[...heavyOwners].join(', ')}`, failures);
}

const button = fs.readFileSync(path.join(sourceRoot, 'components/ui/AppButton.tsx'), 'utf8');
for (const contract of ['minHeight: 44', 'ActivityIndicator', 'accessibilityState', 'onFocus', 'styles.focused', 'styles.pressed', 'styles.disabled']) {
  if (!button.includes(contract)) fail(`AppButton is missing ${contract}`, failures);
}

for (const consumer of ['EmptyState.tsx', 'ErrorState.tsx', 'LoadingState.tsx', 'SkeletonCard.tsx']) {
  const source = fs.readFileSync(path.join(sourceRoot, 'components/ui', consumer), 'utf8');
  if (!source.includes('CARD_SURFACE')) fail(`${consumer} does not reuse CARD_SURFACE`, failures);
}

if (failures.length) {
  console.error(`FAIL Stage 11.2A visual-system validation (${failures.length})`);
  failures.forEach((failure) => console.error(`- ${failure}`));
  process.exit(1);
}

console.log(`PASS Stage 11.2A visual-system validation (${tsxFiles.length} TSX files)`);
console.log('Typography: zero arbitrary sizes/weights; 5 registered heavy-weight owners.');
console.log('Buttons: canonical variants include 44px, loading, disabled, pressed, and focus contracts.');
console.log('Cards: four state surfaces reuse the DashboardCard surface primitive.');
console.log('Icons: zero unregistered textual UI glyphs; one registered analytical chart marker.');
