import {
  getMarketNewsIntelligence,
  getMarketSessionNarrative,
  getSectorNewsIntelligence,
  getSecurityNewsIntelligence,
  getThemeNewsIntelligence,
  getWatchlistNewsIntelligence,
} from '@/services/api';
import { normalizeNewsIntelligence } from '@/features/context-intelligence/newsIntelligenceNormalizer';
import { normalizeSessionNarrative } from '@/features/context-intelligence/sessionNarrativePresenter';

export const contextIntelligenceClient = {
  async marketNews(limit = 5) {
    return normalizeNewsIntelligence(await getMarketNewsIntelligence(limit));
  },

  async marketSession(interval: '5m' | '15m' = '5m') {
    return normalizeSessionNarrative(await getMarketSessionNarrative(interval));
  },

  async securityNews(symbol: string, limit = 5) {
    return normalizeNewsIntelligence(await getSecurityNewsIntelligence(symbol, limit));
  },

  async sectorNews(sectorId: string, limit = 5) {
    return normalizeNewsIntelligence(await getSectorNewsIntelligence(sectorId, limit));
  },

  async themeNews(themeId: string, limit = 5) {
    return normalizeNewsIntelligence(await getThemeNewsIntelligence(themeId, limit));
  },

  async watchlistNews(symbols: string[], limit = 10) {
    return normalizeNewsIntelligence(await getWatchlistNewsIntelligence(symbols, limit));
  },
};
