import { buildBreadthDashboard } from '../src/features/market/breadthAnalysis';
import {
  applyBreadthMockScenarioDashboard,
  BREADTH_MOCK_SCENARIOS,
  buildBreadthMockScenario,
} from '../src/features/market/breadthMockScenarios';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function run() {
  assert(BREADTH_MOCK_SCENARIOS.length === 7, 'all seven breadth mock scenarios are available');

  for (const scenarioOption of BREADTH_MOCK_SCENARIOS) {
    const scenario = buildBreadthMockScenario(scenarioOption.key);
    const market = scenario.breadth.market;
    const latest = scenario.history.at(-1);
    assert(latest, `${scenario.label} history has a latest point`);
    assert(scenario.history.length === 30, `${scenario.label} has 30 history snapshots`);
    assert(latest?.date === '2026-07-15', `${scenario.label} ends on the shared mock date`);
    assert(latest?.above20EMA === market.percent_above_20ema, `${scenario.label} 20 EMA history aligns`);
    assert(latest?.above50EMA === market.percent_above_50ema, `${scenario.label} 50 EMA history aligns`);
    assert(latest?.above200EMA === market.percent_above_200ema, `${scenario.label} 200 EMA history aligns`);
    assert(latest?.coverage === market.coverage_percent, `${scenario.label} coverage history aligns`);

    const dashboard = applyBreadthMockScenarioDashboard(
      buildBreadthDashboard(scenario.breadth, scenario.indexes),
      scenario,
    );
    assert(dashboard.overview.score === scenario.definition.breadthComposite, `${scenario.label} composite override applies`);
    assert(dashboard.overview.status === scenario.definition.state, `${scenario.label} state override applies`);
    assert(dashboard.takeaway.risk === scenario.definition.confirmation.risk, `${scenario.label} risk override applies`);
    assert(dashboard.divergence.stateLabel === scenario.definition.confirmation.stateLabel, `${scenario.label} confirmation override applies`);
  }
}

run();
