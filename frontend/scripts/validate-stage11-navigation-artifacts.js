const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const artifactPath = path.join(root, 'artifacts/stage11.2b-visual-acceptance.json');
if (!fs.existsSync(artifactPath)) throw new Error('Stage 11.2B visual artifact is missing.');
const artifact = JSON.parse(fs.readFileSync(artifactPath, 'utf8'));
const fingerprint = crypto.createHash('sha256');
for (const relativePath of artifact.source_files ?? []) {
  const absolutePath = path.join(root, relativePath);
  if (!fs.existsSync(absolutePath)) throw new Error(`Visual source file is missing: ${relativePath}`);
  fingerprint.update(relativePath).update('\0').update(fs.readFileSync(absolutePath)).update('\0');
}
if (fingerprint.digest('hex') !== artifact.source_fingerprint) throw new Error('Stage 11.2B visual artifact source fingerprint is stale.');
if (artifact.checks?.length !== 30) throw new Error('Stage 11.2B requires exactly 30 accepted screenshots.');
for (const check of artifact.checks) {
  const absolutePath = path.join(root, check.path);
  if (!fs.existsSync(absolutePath)) throw new Error(`Screenshot is missing: ${check.path}`);
  const sha256 = crypto.createHash('sha256').update(fs.readFileSync(absolutePath)).digest('hex');
  if (sha256 !== check.sha256) throw new Error(`Screenshot hash changed: ${check.path}`);
  if (check.result !== 'PASS' || check.failed_checks?.length) throw new Error(`Screenshot acceptance failed: ${check.path}`);
}
if (artifact.result !== 'PASS' || artifact.failed_checks?.length) throw new Error('Stage 11.2B visual acceptance failed.');
console.log(`PASS Stage 11.2B artifact freshness (${artifact.checks.length} screenshots)`);
