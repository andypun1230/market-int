const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const artifactPath = path.join(root, 'artifacts/stage11.2c-visual-acceptance.json');
const validationPath = path.join(root, 'artifacts/stage11.2c-validation.json');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

assert(fs.existsSync(artifactPath), 'Stage 11.2C visual acceptance artifact is missing.');
assert(fs.existsSync(validationPath), 'Stage 11.2C validation artifact is missing.');

const artifact = JSON.parse(fs.readFileSync(artifactPath, 'utf8'));
const validation = JSON.parse(fs.readFileSync(validationPath, 'utf8'));
const fingerprint = crypto.createHash('sha256');
for (const relativePath of artifact.source_files ?? []) {
  const absolutePath = path.join(root, relativePath);
  assert(fs.existsSync(absolutePath), `Visual source file is missing: ${relativePath}`);
  fingerprint.update(relativePath).update('\0').update(fs.readFileSync(absolutePath)).update('\0');
}
const sourceFingerprint = fingerprint.digest('hex');
assert(sourceFingerprint === artifact.source_fingerprint, 'Stage 11.2C visual artifact source fingerprint is stale.');
assert(validation.source_fingerprint === sourceFingerprint, 'Stage 11.2C validation artifact source fingerprint is stale.');
assert(artifact.checks?.length === 30, 'Stage 11.2C requires exactly 30 accepted screenshots.');

for (const check of artifact.checks) {
  const absolutePath = path.join(root, check.path);
  assert(fs.existsSync(absolutePath), `Screenshot is missing: ${check.path}`);
  const sha256 = crypto.createHash('sha256').update(fs.readFileSync(absolutePath)).digest('hex');
  assert(sha256 === check.sha256, `Screenshot hash changed: ${check.path}`);
  for (const field of ['viewport', 'state', 'expected_contrast', 'expected_touch_targets', 'expected_focus', 'expected_typography', 'required_checks', 'failed_checks', 'result']) {
    assert(Object.hasOwn(check, field), `Screenshot check is missing ${field}: ${check.path}`);
  }
  assert(check.result === 'PASS' && check.failed_checks.length === 0, `Screenshot acceptance failed: ${check.path}`);
}

assert(artifact.result === 'PASS' && artifact.failed_checks.length === 0, 'Stage 11.2C visual acceptance failed.');
assert(validation.classification === 'PASS' && validation.failed_checks.length === 0, 'Stage 11.2C validation failed.');
console.log(`PASS Stage 11.2C artifact freshness (${artifact.checks.length} screenshots)`);
