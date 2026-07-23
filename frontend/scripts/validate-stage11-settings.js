const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const source = (relativePath) => fs.readFileSync(path.join(root, relativePath), 'utf8');
const assert = (condition, message) => {
  if (!condition) throw new Error(message);
};

const appearance = source('src/app/appearance.tsx');
const language = source('src/app/language-region.tsx');
const notifications = source('src/app/notifications.tsx');
const settings = source('src/app/settings.tsx');
const about = source('src/app/about.tsx');
const dataSources = source('src/app/data-sources.tsx');
const dataUsage = source('src/app/data-usage.tsx');
const more = source('src/app/(tabs)/more.tsx');
const dataStateProvider = source('src/features/trust/UserFacingDataStateProvider.tsx');

assert(appearance.includes('Not available in beta') && appearance.includes('disabled'), 'unfinished system appearance must be visibly disabled');
assert(language.includes('Not available in beta') && language.includes('disabled'), 'untranslated language must be visibly disabled');
assert(notifications.includes('Not available in beta') && !notifications.includes('onValueChange'), 'notifications must not expose an active preference');
assert(settings.includes('testScenariosEnabled ? <DashboardCard') && settings.includes('Scenario Controls (Development only)'), 'scenario controls must be gated and development-only');
assert(about.includes('testScenariosEnabled ? <SettingsRow') && dataSources.includes('testScenariosEnabled ? <SettingsRow'), 'scenario state must be absent from beta About and Data Sources');
assert(dataStateProvider.includes('testScenariosEnabled\n      ? Promise.allSettled'), 'shared data state must not request scenario status in beta mode');
assert(dataUsage.includes('clearRequestCache()') && dataUsage.includes('next request may take longer'), 'cache clear must cover frontend/backend data and explain the consequence');
assert([settings, about, dataSources, more].every((text) => text.includes('dataState.headline')), 'all four trust surfaces must use the shared data-state headline');

console.log('PASS Stage 11.3 settings source contracts');
