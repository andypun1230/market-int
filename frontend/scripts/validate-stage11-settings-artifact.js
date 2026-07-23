const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const workspace = path.resolve(__dirname, '../..');
const sourceFiles = [
  'frontend/package.json',
  'frontend/scripts/validate-stage11-settings-artifact.js',
  'frontend/scripts/validate-stage11-settings.js',
  'frontend/src/app/(tabs)/more.tsx',
  'frontend/src/app/about.tsx',
  'frontend/src/app/appearance.tsx',
  'frontend/src/app/data-sources.tsx',
  'frontend/src/app/data-usage.tsx',
  'frontend/src/app/language-region.tsx',
  'frontend/src/app/notifications.tsx',
  'frontend/src/app/privacy.tsx',
  'frontend/src/app/settings.tsx',
  'frontend/src/architecture/settingsBetaRegistry.ts',
  'frontend/src/components/ui/SettingsRow.tsx',
  'frontend/src/features/preferences/appPreferencesModel.ts',
  'frontend/src/features/trust/UserFacingDataStateProvider.tsx',
  'frontend/tests/appPreferences.test.ts',
  'frontend/tests/stage11SettingsBetaReadiness.test.ts',
];
const requiredDocuments = [
  'docs/stage11.3-settings-beta-readiness-report.md',
  'docs/stage11.3-settings-consumer-registry.md',
  'docs/stage11.3-beta-settings-classification.md',
  'docs/validation/stage11.3-validation-report.md',
];

const hash = crypto.createHash('sha256');
for (const relativePath of sourceFiles) {
  const absolutePath = path.join(workspace, relativePath);
  if (!fs.existsSync(absolutePath)) throw new Error(`Missing Stage 11.3 source: ${relativePath}`);
  hash.update(relativePath).update('\0').update(fs.readFileSync(absolutePath)).update('\0');
}

for (const relativePath of requiredDocuments) {
  if (!fs.existsSync(path.join(workspace, relativePath))) throw new Error(`Missing Stage 11.3 document: ${relativePath}`);
}

const artifactPath = path.join(workspace, 'artifacts/stage11.3-validation.json');
const artifact = JSON.parse(fs.readFileSync(artifactPath, 'utf8'));
const fingerprint = hash.digest('hex');
if (artifact.source_fingerprint !== fingerprint) {
  throw new Error(`Stale Stage 11.3 artifact fingerprint: expected ${fingerprint}, found ${artifact.source_fingerprint}`);
}
if (artifact.classification !== 'PASS' || artifact.failed_checks.length !== 0 || !artifact.stage_11_3_ready_to_freeze) {
  throw new Error('Stage 11.3 artifact does not record a strict PASS freeze decision.');
}

console.log(`PASS Stage 11.3 artifact freshness (${sourceFiles.length} source files)`);
