const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const artifactPath = path.join(root, 'artifacts/stage10.2-visual-acceptance.json');
if (!fs.existsSync(artifactPath)) throw new Error('Stage 10.2 visual acceptance artifact is missing.');
const artifact = JSON.parse(fs.readFileSync(artifactPath, 'utf8'));
const fingerprint = crypto.createHash('sha256');
for (const relativePath of artifact.source_files ?? []) {
  const absolutePath = path.join(root, relativePath);
  if (!fs.existsSync(absolutePath)) throw new Error(`Visual source file is missing: ${relativePath}`);
  fingerprint.update(relativePath).update('\0').update(fs.readFileSync(absolutePath)).update('\0');
}
if (fingerprint.digest('hex') !== artifact.source_fingerprint) {
  throw new Error('Stage 10.2 visual artifact is stale: source fingerprint changed.');
}
const capturedAt = Date.parse(artifact.captured_at);
if (!Number.isFinite(capturedAt)) throw new Error('Stage 10.2 visual artifact has an invalid capture timestamp.');
for (const check of artifact.checks ?? []) {
  const absolutePath = path.join(root, check.path);
  if (!fs.existsSync(absolutePath)) throw new Error(`Screenshot is missing: ${check.path}`);
  const bytes = fs.readFileSync(absolutePath);
  const sha256 = crypto.createHash('sha256').update(bytes).digest('hex');
  if (sha256 !== check.sha256) throw new Error(`Screenshot hash changed after acceptance: ${check.path}`);
  if (fs.statSync(absolutePath).mtimeMs > capturedAt + 1000) {
    throw new Error(`Visual artifact predates its screenshot: ${check.path}`);
  }
  const latestSourceMtime = (check.source_files ?? artifact.source_files ?? [])
    .map((relativePath) => fs.statSync(path.join(root, relativePath)).mtimeMs)
    .reduce((latest, value) => Math.max(latest, value), 0);
  if (fs.statSync(absolutePath).mtimeMs + 1000 < latestSourceMtime) {
    throw new Error(`Screenshot predates its accepted source: ${check.path}`);
  }
}
if (artifact.result !== 'PASS' || (artifact.failed_checks ?? []).length) {
  throw new Error('Stage 10.2 visual acceptance did not pass.');
}
console.log(`PASS Stage 10.2 visual artifact freshness (${artifact.checks.length} screenshots)`);
