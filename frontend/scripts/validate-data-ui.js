#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const projectRoot = path.resolve(__dirname, '..', '..');
const manifestPath = process.env.APPLICATION_DATA_UI_MANIFEST
  || path.join(projectRoot, 'docs', 'application-data-ui-manifest.json');

function fail(message) {
  console.error(`FAIL ${message}`);
  process.exit(1);
}

if (!fs.existsSync(manifestPath)) {
  fail(`frontend validation manifest not found: ${manifestPath}`);
}

let manifest;
try {
  manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
} catch (error) {
  fail(`manifest is not valid JSON: ${error.message}`);
}

const screenMatrix = manifest.screen_matrix || {};
const failedScreens = Object.entries(screenMatrix)
  .filter(([, counts]) => Number(counts.FAIL || 0) > 0)
  .map(([screen, counts]) => `${screen} (${counts.FAIL} failures)`);

if (failedScreens.length) {
  fail(`backend contract failures remain for screens: ${failedScreens.join(', ')}`);
}

const manualRequired = manifest.manual_required || [];
console.log('PASS frontend data contract manifest');
console.log(`Screens represented: ${Object.keys(screenMatrix).length}`);
if (manualRequired.length) {
  console.log(`MANUAL REQUIRED ${manualRequired.join('; ')}`);
}

