import { ENTITY_ROUTING_REGISTRY, buildEntityDestination } from '../src/architecture/entityRoutingRegistry';
import { duplicateInteractionIds } from '../src/architecture/interactionRegistry';
import { STATIC_ROUTE_REGISTRY } from '../src/architecture/navigationRegistry';
import { duplicateIntelligenceOutputs } from '../src/architecture/ownershipRegistry';
import { ACTIVE_PREFERENCE_PATHS, SETTINGS_CONSUMER_REGISTRY, validatePreferenceShape } from '../src/architecture/settingsConsumerRegistry';
import { DEFAULT_PREFERENCES } from '../src/features/preferences/appPreferencesModel';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

function run() {
  assert(duplicateIntelligenceOutputs().length === 0, 'every registered intelligence output has one owner');
  assert(duplicateInteractionIds().length === 0, 'every registered interaction has one contract');
  assert(validatePreferenceShape(DEFAULT_PREFERENCES), 'every persisted preference has at least one downstream consumer');
  assert(ACTIVE_PREFERENCE_PATHS.every((path) => SETTINGS_CONSUMER_REGISTRY[path].consumers.length > 0), 'preference consumers are named');

  const stock = buildEntityDestination('stock', { stockTab: 'technical', symbol: 'nvda' });
  assert(stock.pathname === '/watchlist' && stock.params.symbol === 'NVDA' && stock.params.detailTab === 'technical', 'stock has one canonical detail destination');
  const sector = buildEntityDestination('sector', { entityId: 'energy', entityName: 'Energy' });
  assert(sector.pathname === '/sectors' && sector.params.entityKind === 'sector', 'sector has one canonical detail destination');
  const theme = buildEntityDestination('theme', { entityId: 'cybersecurity', entityName: 'Cybersecurity' });
  assert(theme.pathname === '/sectors' && theme.params.entityKind === 'theme', 'theme has one canonical detail destination');
  const report = buildEntityDestination('report', { reportId: 'daily-1' });
  assert(report.pathname === '/report' && report.params.reportId === 'daily-1', 'report has one canonical detail destination');

  Object.values(ENTITY_ROUTING_REGISTRY).forEach((entry) => {
    assert(STATIC_ROUTE_REGISTRY.includes(entry.pathname), `${entry.owner} uses a registered route`);
  });
  console.log('PASS architecture ownership, routing, interaction, and settings registries');
}

run();
