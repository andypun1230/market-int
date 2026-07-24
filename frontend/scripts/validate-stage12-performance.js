const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..', '..');
const performance = JSON.parse(fs.readFileSync(path.join(root, 'artifacts/stage12.2-performance.json'), 'utf8'));
const validation = JSON.parse(fs.readFileSync(path.join(root, 'artifacts/stage12.2-validation.json'), 'utf8'));
const visual = JSON.parse(fs.readFileSync(path.join(root, 'artifacts/stage12.2-visual-acceptance.json'), 'utf8'));

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

assert(performance.stage === '12.2', 'Stage 12.2 performance artifact stage mismatch.');
assert(performance.baseline_commit === 'e2de1f415260593541e641ee2c4cb3f2382a7634', 'Stage 12.2 baseline commit mismatch.');
for (const [route, result] of Object.entries(performance.routes)) {
  if (result.hard_budget_ms == null) continue;
  assert(result.decision_ready_p50_ms <= result.hard_budget_ms, `${route} p50 exceeds its hard budget.`);
  assert(result.decision_ready_p95_ms <= result.hard_budget_ms, `${route} p95 exceeds its hard budget.`);
}
assert(performance.contracts.theme_summary.gzip_bytes < 1_000_000, 'Theme summary exceeds compressed hard budget.');
assert(performance.contracts.theme_rotation.gzip_bytes < 500_000, 'Theme rotation exceeds compressed hard budget.');
assert(performance.bundle.initial_gzip_bytes < performance.bundle.baseline_gzip_bytes, 'Initial JavaScript did not improve.');
assert(performance.bundle.home_unused_percent < performance.bundle.baseline_home_unused_percent, 'Home unused JavaScript did not improve.');
assert(validation.required_checks.stage12_2_focused_tests === 'PASS', 'Focused Stage 12.2 tests did not pass.');
assert(validation.required_checks.frontend_full_suite === 'PASS', 'Frontend regression did not pass.');
assert(visual.cases.length >= 20 && visual.cases.every((item) => item.result === 'PASS'), 'Visual acceptance is incomplete.');
assert(visual.screenshot_count >= 20, 'At least 20 screenshots are required.');

console.log('PASS Stage 12.2 web performance budgets and fresh validation artifacts');
