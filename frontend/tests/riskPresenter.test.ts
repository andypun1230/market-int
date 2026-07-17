import {
  assessRiskPlanTrust,
  buildRiskDashboard,
} from '../src/features/stock-detail/risk/riskPresenter';
import type { RiskPlan, SupportResistanceResponse } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

const baseRiskPlan: RiskPlan = {
  atr_14: 4.2,
  current_price: 100,
  data_quality: {
    history_quality_score: 92,
    history_source: 'generated_test_data',
    overall_mode: 'mixed',
  },
  entry: 104,
  position_size_note: 'Use managed size.',
  reward_percent_target_1: 10,
  reward_percent_target_2: 18,
  risk_level: 'Moderate',
  risk_percent: 5,
  risk_reward_target_1: 2,
  risk_reward_target_2: 3.6,
  stop_loss: 95,
  summary: 'Risk is moderate.',
  symbol: 'NVDA',
  target_1: 110,
  target_2: 118,
  volatility_level: 'Moderate',
};

const baseSupportResistance: SupportResistanceResponse = {
  analysis_is_live: false,
  as_of: '2026-07-14T00:00:00Z',
  breakout_level: 103,
  current_price: 100,
  data_source: 'generated_test_data',
  fallback_used: false,
  history_is_live: false,
  history_quality_score: 91,
  is_live: false,
  moving_average_support: {
    ema_20: 98,
    ema_50: 92,
  },
  resistance_zones: [
    {
      high: 106,
      low: 103,
      reason: 'Nearby resistance',
      strength: 80,
    },
  ],
  stop_reference: 95,
  support_zones: [
    {
      high: 96,
      low: 94,
      reason: 'Support zone',
      strength: 78,
    },
  ],
  symbol: 'NVDA',
};

function run() {
  const testTrust = assessRiskPlanTrust(baseRiskPlan, baseSupportResistance);
  assert(testTrust.state === 'test_compatible', 'generated test data can lead the risk tab');
  assert(testTrust.shouldShowRiskReward, 'test-compatible risk can show reward interpretation');
  assert(testTrust.shouldShowPositionSizing, 'test-compatible risk can show position sizing guidance');

  const dashboard = buildRiskDashboard({
    riskPlan: baseRiskPlan,
    supportResistance: baseSupportResistance,
  });
  assert(dashboard.invalidationLevel === 95, 'current invalidation uses support/resistance stop reference');
  assert(dashboard.confirmationLevel === 103, 'current confirmation uses support/resistance breakout level');
  assert(dashboard.downsidePercent === 5, 'downside percent derives from current price and invalidation');
  assert(dashboard.rewards.length === 2, 'trusted targets are interpreted');
  assert(dashboard.positionGuidance.state === 'reduced', 'moderate risk produces reduced sizing guidance');
  assert(dashboard.decisionContext.dataTrust === 'test_compatible', 'decision context separates data trust');
  assert(dashboard.decisionContext.modeledRisk === 'moderate', 'decision context separates modeled risk');
  assert(!dashboard.summary.includes('Generated Test Data'), 'summary does not embed the test data disclaimer');
  assert(dashboard.summary.length < 180, 'risk summary stays compact');

  const confirmedLowDashboard = buildRiskDashboard({
    riskPlan: {
      ...baseRiskPlan,
      current_price: 105,
      risk_level: 'Low',
      risk_percent: 3,
      volatility_level: 'Low',
    },
    supportResistance: {
      ...baseSupportResistance,
      breakout_level: 103,
      current_price: 105,
      stop_reference: 101,
    },
  });
  assert(confirmedLowDashboard.decisionContext.modeledRisk === 'low', 'low risk is normalized');
  assert(confirmedLowDashboard.decisionContext.setupConfirmation === 'confirmed', 'current price above confirmation is confirmed');
  assert(confirmedLowDashboard.positionGuidance.state === 'standard', 'low risk confirmed setup produces standard guidance');
  assert(!confirmedLowDashboard.positionGuidance.explanation.includes('mixed'), 'test-compatible data alone does not force mixed wording');
  assert(confirmedLowDashboard.positionGuidance.explanation.includes('Low volatility'), 'standard guidance names supportive factors');

  const pendingLowDashboard = buildRiskDashboard({
    riskPlan: {
      ...baseRiskPlan,
      risk_level: 'Low',
      volatility_level: 'Low',
    },
    supportResistance: {
      ...baseSupportResistance,
      breakout_level: 103,
      current_price: 100,
      stop_reference: 97,
    },
  });
  assert(pendingLowDashboard.decisionContext.setupConfirmation === 'awaiting_confirmation', 'price below confirmation is pending');
  assert(pendingLowDashboard.positionGuidance.state === 'reduced', 'low risk pending confirmation produces reduced guidance');
  assert(pendingLowDashboard.positionGuidance.explanation.includes('confirmation'), 'reduced explanation names confirmation');

  const highRiskDashboard = buildRiskDashboard({
    riskPlan: {
      ...baseRiskPlan,
      current_price: 100,
      risk_level: 'High',
      volatility_level: 'High',
    },
    supportResistance: {
      ...baseSupportResistance,
      breakout_level: 98,
      current_price: 100,
      stop_reference: 88,
    },
  });
  assert(highRiskDashboard.positionGuidance.state === 'conservative', 'high risk produces conservative guidance');

  const currentPriceLevel = confirmedLowDashboard.riskLevels.find((level) => level.role === 'current');
  assert(currentPriceLevel?.label.includes('Current Price'), 'current price appears in current risk levels');
  assert(currentPriceLevel?.description === 'Reference', 'current price uses concise reference label');
  assert(confirmedLowDashboard.riskLevels[0].value >= confirmedLowDashboard.riskLevels[1].value, 'risk levels are ordered high to low');
  assert(confirmedLowDashboard.riskLevels.every((level) => level.description.length <= 24), 'level descriptions stay compact');
  assert(!confirmedLowDashboard.factors.some((factor) => factor.label.toLowerCase() === 'low risk'), 'risk drivers do not repeat low risk as a factor');
  assert(confirmedLowDashboard.factors.some((factor) => factor.tone === 'success'), 'protective factors are available for grouping');

  const mockRiskPlan: RiskPlan = {
    ...baseRiskPlan,
    data_quality: {
      history_source: 'mock',
      mock_dependencies: ['pattern'],
      overall_mode: 'mock',
    },
  };
  const mockTrust = assessRiskPlanTrust(mockRiskPlan, undefined);
  assert(mockTrust.state === 'mock', 'mock risk plan is demoted');
  assert(!mockTrust.shouldShowRiskReward, 'mock risk plan hides risk/reward');
  const mockDashboard = buildRiskDashboard({ riskPlan: mockRiskPlan });
  assert(mockDashboard.illustrativeLevels.length > 0, 'mock levels remain available as illustrative context');
  assert(mockDashboard.riskLevels.length === 0, 'mock levels are not shown as current risk levels');

  const fallbackTrust = assessRiskPlanTrust(
    {
      ...baseRiskPlan,
      data_quality: {
        fallback_dependencies: ['history'],
        overall_mode: 'mixed',
      },
    },
    {
      ...baseSupportResistance,
      data_source: 'mock-fallback',
      fallback_used: true,
    },
  );
  assert(fallbackTrust.state === 'source_incompatible', 'fallback dependencies are source incompatible');
  assert(!fallbackTrust.shouldLeadRiskTab, 'fallback dependencies cannot lead the risk tab');
  const fallbackDashboard = buildRiskDashboard({
    riskPlan: {
      ...baseRiskPlan,
      data_quality: {
        fallback_dependencies: ['history'],
        overall_mode: 'mixed',
      },
    },
    supportResistance: {
      ...baseSupportResistance,
      data_source: 'mock-fallback',
      fallback_used: true,
    },
  });
  assert(fallbackDashboard.positionGuidance.state === 'unavailable', 'incompatible data makes sizing unavailable');

  const liveTrust = assessRiskPlanTrust(
    {
      ...baseRiskPlan,
      data_quality: {
        history_source: 'polygon',
        overall_mode: 'live',
      },
    },
    {
      ...baseSupportResistance,
      analysis_is_live: true,
      data_source: 'polygon',
      history_is_live: true,
      is_live: true,
    },
  );
  assert(liveTrust.state === 'current_compatible', 'live compatible data is current compatible');
}

run();
