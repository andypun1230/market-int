const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const read = (relative) => fs.readFileSync(path.join(root, relative), 'utf8');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function color(source, name) {
  const match = source.match(new RegExp(`${name}:\\s*'(#(?:[0-9A-Fa-f]{6}))'`));
  if (!match) throw new Error(`Missing color token ${name}`);
  return match[1];
}

function luminance(hex) {
  const channels = hex.match(/[0-9a-f]{2}/gi).map((value) => Number.parseInt(value, 16) / 255);
  const linear = channels.map((value) => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

function ratio(foreground, background) {
  const values = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
  return (values[0] + 0.05) / (values[1] + 0.05);
}

const theme = read('src/constants/theme.ts');
const css = read('src/global.css');
const policy = read('src/architecture/accessibilityPolicy.ts');
const terminology = read('src/architecture/terminologyRegistry.ts');
const dates = read('src/features/trust/dateFreshnessPresentation.ts');
const motion = read('src/hooks/useReducedMotion.ts');
const motionPolicy = read('src/features/preferences/reducedMotionPolicy.ts');

const contrastPairs = [
  ['purple-soft', color(theme, 'purple'), color(theme, 'purpleSoft'), 4.5],
  ['danger-soft', color(theme, 'danger'), color(theme, 'dangerSoft'), 4.5],
  ['muted-card-elevated', color(theme, 'textMuted'), color(theme, 'cardElevated'), 4.5],
  ['focus-background', color(theme, 'focus'), color(theme, 'background'), 3],
];
for (const [name, foreground, background, minimum] of contrastPairs) {
  assert(ratio(foreground, background) >= minimum, `${name} contrast is below ${minimum}:1`);
}

assert(css.includes(':focus-visible') && css.includes('var(--focus-ring)'), 'canonical focus-visible selector is missing');
assert(css.includes(':focus:not(:focus-visible)'), 'pointer focus suppression is missing');
assert(policy.includes("owner: 'global.css focus-visible and AppButton native fallback'"), 'focus owner is not registered');

const touchContracts = [
  ['src/components/ui/AppButton.tsx', 'minHeight: 44'],
  ['src/components/ui/AppButton.tsx', 'minWidth: Theme.accessibility.minimumTouchTarget'],
  ['src/app/(tabs)/index.tsx', 'minHeight: 44'],
  ['src/features/command/components/UniversalCommandHeader.tsx', 'height: 44'],
  ['src/features/reports/components/ReportHistorySection.tsx', 'height: 44'],
  ['src/features/stock-detail/components/StockMiniChart.tsx', 'minHeight: 44'],
  ['src/components/charts/RotationQuadrantChart.tsx', 'Theme.accessibility.minimumTouchTarget'],
];
for (const [file, contract] of touchContracts) assert(read(file).includes(contract), `${file} is missing touch contract ${contract}`);

const essentialSmallTextOwners = [
  ['src/app/(tabs)/index.tsx', 'sparklineUnavailable'],
  ['src/app/(tabs)/index.tsx', 'factorDirection'],
  ['src/app/(tabs)/watchlist.tsx', 'summaryMetricLabel'],
  ['src/components/ui/ConfidenceIndicator.tsx', 'scoreLabel'],
  ['src/components/watchlist/RiskPlanSection.tsx', 'summaryScoreLabel'],
  ['src/features/watchlist/components/WatchlistSignalBadge.tsx', 'statusText'],
  ['src/features/reports/components/ReportDocumentPreview.tsx', 'researchChainNodeType'],
];
for (const [file, styleName] of essentialSmallTextOwners) {
  const source = read(file);
  const style = source.match(new RegExp(`${styleName}:[\\s\\S]{0,220}?fontSize:\\s*Typography\\.([A-Za-z]+)\\.fontSize`));
  assert(style && !['chartAxis', 'chartMicro'].includes(style[1]), `${file} keeps essential ${styleName} below the semantic minimum`);
}

for (const phrase of ['No saved stocks', 'No saved sectors', 'No saved themes', 'No matching results', 'No alerts', 'Report not generated']) {
  assert(terminology.includes(phrase), `terminology registry is missing ${phrase}`);
}
assert(!read('src/features/command/components/UniversalCommandHeader.tsx').includes('No matching destinations.'), 'search empty-state drift remains');
assert(!read('src/features/reports/components/ReportLandingCard.tsx').includes('Generate Updated Research'), 'report action terminology drift remains');

for (const exportName of ['dateFreshnessLabel', 'formatLocalizedDate', 'formatLocalizedDateTime']) {
  assert(dates.includes(`function ${exportName}`), `shared date owner is missing ${exportName}`);
}
assert(dates.includes('now?: Date') && dates.includes('timeZone?: string'), 'date owner is not deterministic or timezone-aware');
assert(motion.includes('resolveReducedMotion(preferences.appearance.reduceMotion, systemPreference)') && motionPolicy.includes('appPreference || platformPreference'), 'reduced motion does not combine app and platform preferences');
assert(read('src/components/ui/DetailModal.tsx').includes("animationType={reduceMotion ? 'none' : 'slide'}"), 'detail modal ignores reduced motion');
assert(read('src/features/command/components/UniversalCommandHeader.tsx').includes("animationType={reduceMotion ? 'none' : 'fade'}"), 'search modal ignores reduced motion');

const sourceFiles = [];
function collect(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) collect(absolute);
    else if (/\.(ts|tsx)$/.test(entry.name)) sourceFiles.push(absolute);
  }
}
collect(path.join(root, 'src'));
for (const file of sourceFiles) {
  const source = fs.readFileSync(file, 'utf8');
  assert(!/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/.test(source), `${path.relative(root, file)} contains a control character`);
}

console.log(`PASS Stage 11.2C accessibility source validation (${sourceFiles.length} source files)`);
console.log(`Contrast: ${contrastPairs.map(([name, foreground, background]) => `${name} ${ratio(foreground, background).toFixed(2)}:1`).join('; ')}`);
console.log('Focus, touch, essential text, terminology, dates, reduced motion, and control-character contracts pass.');
