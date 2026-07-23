import {
  BUTTON_CONTRACT,
  BUTTON_VARIANTS,
  CONFIDENCE_FRESHNESS_CONTRACT,
  ICON_EXCEPTIONS,
  SEMANTIC_TYPOGRAPHY_ROLES,
  SHARED_CARD_SURFACES,
  TYPOGRAPHY_EXCEPTIONS,
} from '../src/architecture/visualSystemRegistry';
import {
  availabilityLabel,
  confidenceLabel,
  evidenceFreshnessLabel,
  freshnessLabel,
  providerLabel,
} from '../src/features/trust/confidenceFreshnessPresentation';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

function run() {
  assert(BUTTON_VARIANTS.join(',') === 'primary,secondary,neutral,danger,icon,compact', 'canonical button variants are stable');
  assert(BUTTON_CONTRACT.minimumTouchTarget === 44, 'button family enforces a 44px touch target');
  assert(BUTTON_CONTRACT.states.includes('loading') && BUTTON_CONTRACT.states.includes('focused'), 'button state contract includes loading and focus');
  assert(SEMANTIC_TYPOGRAPHY_ROLES.includes('control') && SEMANTIC_TYPOGRAPHY_ROLES.includes('heroValue'), 'semantic typography covers controls and hero values');
  assert(TYPOGRAPHY_EXCEPTIONS.length === 1 && TYPOGRAPHY_EXCEPTIONS[0].roles.every((role) => role.startsWith('chart')), 'sub-minimum type exceptions are chart-only');
  assert(SHARED_CARD_SURFACES.length === 5, 'shared card surface consumers are registered');
  assert(ICON_EXCEPTIONS.length === 1 && ICON_EXCEPTIONS[0].owner === 'RotationQuadrantChart', 'only the analytical trajectory mark is exempted from AppIcon');

  assert(confidenceLabel({ confidence: 74.6 }) === '75/100 confidence', 'confidence is rounded and consistently qualified');
  assert(confidenceLabel({ confidence: 62, fallback: 'Evidence quality high' }) === '62/100 evidence quality', 'evidence-quality qualifier is preserved');
  assert(confidenceLabel({ fallback: 'Moderate confidence' }) === 'Moderate confidence', 'text-only confidence remains available');
  assert(confidenceLabel({}) === 'Confidence unavailable', 'missing confidence has canonical wording');
  assert(freshnessLabel() === 'Last update unavailable', 'missing freshness has canonical wording');
  assert(freshnessLabel('Evidence through Jul 22') === 'Evidence through Jul 22', 'domain-specific evidence-through wording is preserved');
  assert(availabilityLabel('partial_data') === 'Partial Data', 'availability enums use display casing');
  assert(providerLabel('openai') === 'OpenAI', 'provider names use canonical casing');
  assert(evidenceFreshnessLabel('mixed') === 'Partial evidence', 'evidence freshness wording is canonical');
  assert(CONFIDENCE_FRESHNESS_CONTRACT.confidenceOwner === 'confidenceLabel', 'confidence presentation has one owner');

  console.log('PASS Stage 11.2A visual-system contracts and confidence/freshness formatting');
}

run();
