import {
  AIChatRequest,
  AIChatResponse,
  DashboardComparisonResponse,
  DailyReport,
  DecisionDashboardResponse,
  FearGreedResponse,
  HomeDashboardResponse,
  IndexesResponse,
  IndustryGroupResponse,
  IntelligenceStatus,
  InstitutionalDashboardResponse,
  IndustryRotationResponse,
  InstitutionalActivityResponse,
  LeadershipResponse,
  LiquidityDashboardResponse,
  LiveQuotesResponse,
  MarketBrief,
  MarketAISummary,
  MarketBreadthResponse,
  MarketCapRotationResponse,
  MarketHealthResponse,
  MarketCoreSnapshot,
  MarketRegime,
  MarketSentimentResponse,
  MoneyFlowResponse,
  MultiTimeframeItem,
  MultiTimeframeResponse,
  OptionsIntelligenceResponse,
  PatternResponse,
  ProbabilityResponse,
  ProviderStatus,
  ProviderCacheStatus,
  RegenerateTestDataRequest,
  RegenerateTestDataResponse,
  HistoryData,
  QuoteData,
  RelativeStrengthResponse,
  RiskPlan,
  RiskPlanResponse,
  RiskResponse,
  SectorResponse,
  SectorEtfResponse,
  SectorDashboardResponse,
  SectorsSummaryResponse,
  SymbolLiquidityResponse,
  SymbolOptionsIntelligence,
  StockAnalysisAggregate,
  StockRatingResponse,
  SupportResistanceResponse,
  ServiceCacheStatus,
  TrendlineResponse,
  TestDataScenariosResponse,
  TestDataStatus,
  UniverseStatus,
  VolumeAnalysis,
  VolumeAnalysisResponse,
  WatchlistResponse,
  WatchlistSummaryResponse,
} from '@/types/market';
import { cachedRequest } from '@/services/requestCache';
import { API_URL } from '@/services/apiConfig';
import type { CopilotChatRequest, CopilotChatResponse } from '@/features/copilot/types';

type RequestOptions = {
  timeoutMs?: number;
};

export { API_URL };

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = 10_000 } = options;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const started = Date.now();

  logRequest('GET', path);
  try {
    const response = await fetch(`${API_URL}${path}`, {
      signal: controller.signal,
    }).finally(() => clearTimeout(timeout));

    if (!response.ok) {
      throw await buildApiError('GET', path, response);
    }

    logSuccess('GET', path, response.status, started);
    return response.json() as Promise<T>;
  } catch (error) {
    logError('GET', path, error, started);
    throw error;
  }
}

async function post<TRequest, TResponse>(
  path: string,
  body: TRequest,
  options: RequestOptions = {},
): Promise<TResponse> {
  const { timeoutMs = 30_000 } = options;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const started = Date.now();

  logRequest('POST', path);
  try {
    const response = await fetch(`${API_URL}${path}`, {
      body: JSON.stringify(body),
      headers: {
        'Content-Type': 'application/json',
      },
      method: 'POST',
      signal: controller.signal,
    }).finally(() => clearTimeout(timeout));

    if (!response.ok) {
      throw await buildApiError('POST', path, response);
    }

    logSuccess('POST', path, response.status, started);
    return response.json() as Promise<TResponse>;
  } catch (error) {
    logError('POST', path, error, started);
    throw error;
  }
}

async function postWithoutBody<TResponse>(path: string): Promise<TResponse> {
  const started = Date.now();

  logRequest('POST', path);
  try {
    const response = await fetch(`${API_URL}${path}`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw await buildApiError('POST', path, response);
    }

    logSuccess('POST', path, response.status, started);
    return response.json() as Promise<TResponse>;
  } catch (error) {
    logError('POST', path, error, started);
    throw error;
  }
}

async function buildApiError(method: string, path: string, response: Response): Promise<Error> {
  const body = await safeReadResponseBody(response);
  return new Error(
    `${method} ${path} failed with HTTP ${response.status}${body ? `: ${body}` : ''}`,
  );
}

async function safeReadResponseBody(response: Response): Promise<string> {
  try {
    const text = await response.text();
    return text.length > 600 ? `${text.slice(0, 600)}...` : text;
  } catch {
    return '';
  }
}

function logRequest(method: string, path: string) {
  if (isNetworkDebugEnabled()) {
    console.log(`[API REQUEST] ${method} ${path}`);
  }
}

function logSuccess(method: string, path: string, status: number, started: number) {
  if (isNetworkDebugEnabled()) {
    console.log(`[API SUCCESS] ${method} ${path} ${status} ${Date.now() - started}ms`);
  }
}

function logError(method: string, path: string, error: unknown, started: number) {
  if (isNetworkDebugEnabled()) {
    const message = error instanceof Error ? error.message : String(error);
    console.log(`[API ERROR] ${method} ${path} ${Date.now() - started}ms ${message}`);
  }
}

function isNetworkDebugEnabled(): boolean {
  return process.env.EXPO_PUBLIC_NETWORK_DEBUG === 'true';
}

export function getMarketBrief() {
  return request<MarketBrief>('/market/brief');
}

export function getMarketRegime() {
  return request<MarketRegime>('/market/regime');
}

export function getMarketIndexes() {
  return request<IndexesResponse>('/market/indexes');
}

export function getMarketBreadth() {
  return request<MarketBreadthResponse>('/market/breadth');
}

export function getInstitutionalActivity() {
  return request<InstitutionalActivityResponse>('/market/institutional-activity');
}

export function getMarketSectors() {
  return cachedRequest('sectors', () => request<SectorResponse>('/market/sectors'), 300_000);
}

export function getSectorsSummary() {
  return cachedRequest('sectors-summary', () => request<SectorsSummaryResponse>('/market/sectors/summary'), 60_000);
}

export function getSectorDashboard() {
  return cachedRequest(
    'sector-dashboard',
    () => request<SectorDashboardResponse>('/market/sector-dashboard', { timeoutMs: 10_000 }),
    300_000,
  );
}

export function getMarketWatchlist() {
  return request<WatchlistResponse>('/market/watchlist');
}

export function getWatchlistSummary() {
  return cachedRequest(
    'watchlist-summary',
    () => request<WatchlistSummaryResponse>('/watchlist/summary', { timeoutMs: 5000 }),
    60_000,
  );
}

export function getMarketPatterns() {
  return request<PatternResponse>('/market/patterns');
}

export function getMarketPatternsBySymbol(symbol: string) {
  return request<PatternResponse>(`/market/patterns/${symbol}`);
}

export function getSupportResistance(symbol: string) {
  return request<SupportResistanceResponse>(`/market/support-resistance/${symbol}`);
}

export function getTrendlines() {
  return request<TrendlineResponse[]>('/market/trendlines');
}

export function getTrendline(symbol: string) {
  return request<TrendlineResponse>(`/market/trendline/${symbol}`);
}

export function getStockAnalysis(symbol: string) {
  const normalizedSymbol = symbol.toUpperCase();
  return cachedRequest(
    `stock-analysis:v3:${normalizedSymbol}`,
    () => request<StockAnalysisAggregate>(`/market/stock-analysis/${normalizedSymbol}`, { timeoutMs: 10_000 }),
    300_000,
  );
}

export function getVolumeAnalysis() {
  return request<VolumeAnalysisResponse>('/market/volume');
}

export function getVolumeAnalysisBySymbol(symbol: string) {
  return request<VolumeAnalysis>(`/market/volume/${symbol}`);
}

export function getRiskPlans() {
  return request<RiskPlanResponse>('/market/risk-plans');
}

export function getRiskPlanBySymbol(symbol: string) {
  return request<RiskPlan>(`/market/risk-plans/${symbol}`);
}

export function getMultiTimeframe() {
  return request<MultiTimeframeResponse>('/market/multi-timeframe');
}

export function getMultiTimeframeBySymbol(symbol: string) {
  return request<MultiTimeframeItem>(`/market/multi-timeframe/${symbol}`);
}

export function getRelativeStrength() {
  return request<RelativeStrengthResponse>('/market/relative-strength');
}

export function getStockRatings() {
  return request<StockRatingResponse>('/market/stock-ratings');
}

export function getMarketRisk() {
  return request<RiskResponse>('/market/risk');
}

export function getMarketHealth() {
  return request<MarketHealthResponse>('/market/health');
}

export function getMarketCoreSnapshot() {
  return cachedRequest(
    'market-core-snapshot',
    () => request<MarketCoreSnapshot>('/market/core-snapshot', { timeoutMs: 5000 }),
    60_000,
  );
}

export function getHomeDashboard() {
  return cachedRequest(
    'home-dashboard',
    () => request<HomeDashboardResponse>('/home/dashboard', { timeoutMs: 5000 }),
    60_000,
  );
}

export function getDecisionDashboard() {
  return cachedRequest(
    'market:decision-dashboard',
    () => request<DecisionDashboardResponse>('/market/decision-dashboard'),
    120_000,
  );
}

export function getMarketDecisionDetails() {
  return cachedRequest(
    'market-details-decision',
    () => request<Record<string, unknown>>('/market/details/decision', { timeoutMs: 10_000 }),
    120_000,
  );
}

export function getMarketInstitutionalDetails() {
  return cachedRequest(
    'market-details-institutional',
    () => request<Record<string, unknown>>('/market/details/institutional', { timeoutMs: 10_000 }),
    300_000,
  );
}

export function getMarketStructureDetails() {
  return cachedRequest(
    'market-details-structure',
    () => request<Record<string, unknown>>('/market/details/structure', { timeoutMs: 10_000 }),
    300_000,
  );
}

export function getMarketProbabilities() {
  return request<ProbabilityResponse>('/market/probabilities');
}

export function getMarketLeadership() {
  return request<LeadershipResponse>('/market/leadership');
}

export function getMarketComparison() {
  return request<DashboardComparisonResponse>('/market/comparison');
}

export function getIndustryRotation() {
  return cachedRequest('industry-rotation', () => request<IndustryRotationResponse>('/market/industry-rotation'), 300_000);
}

export function getSectorEtfs() {
  return cachedRequest('sector-etfs', () => request<SectorEtfResponse>('/market/sector-etfs'), 300_000);
}

export function getIndustryGroups() {
  return cachedRequest('industry-groups', () => request<IndustryGroupResponse>('/market/industry-groups'), 300_000);
}

export function getMarketCapRotation() {
  return request<MarketCapRotationResponse>('/market/cap-rotation');
}

export function getFearGreed() {
  return request<FearGreedResponse>('/market/fear-greed');
}

export function getMarketSentiment() {
  return request<MarketSentimentResponse>('/market/sentiment');
}

export function getMoneyFlow() {
  return request<MoneyFlowResponse>('/market/money-flow');
}

export function getMarketInstitutional() {
  return request<InstitutionalDashboardResponse>('/market/institutional');
}

export function getMarketInstitutionalBySymbol(symbol: string) {
  return request<InstitutionalDashboardResponse>(`/market/institutional/${symbol}`);
}

export function getOptionsIntelligence() {
  return request<OptionsIntelligenceResponse>('/market/options');
}

export function getOptionsIntelligenceBySymbol(symbol: string) {
  return request<SymbolOptionsIntelligence>(`/market/options/${symbol}`);
}

export function getLiquidityDashboard() {
  return request<LiquidityDashboardResponse>('/market/liquidity');
}

export function getLiquidityDashboardBySymbol(symbol: string) {
  return request<SymbolLiquidityResponse>(`/market/liquidity/${symbol}`);
}

export function getDailyReport() {
  return request<DailyReport>('/report/daily');
}

export function getDailyReportPdfUrl() {
  return `${API_URL}/report/daily/pdf`;
}

export function getMarketAISummary() {
  return cachedRequest(
    'ai:market-summary',
    () => request<MarketAISummary>('/ai/market-summary'),
    60_000,
  );
}

export function askAIChat(message: string, symbol?: string) {
  const body: AIChatRequest = {
    message,
    symbol: symbol || undefined,
  };

  return post<AIChatRequest, AIChatResponse>('/ai/chat', body);
}

export function postCopilotChat(body: CopilotChatRequest) {
  return post<CopilotChatRequest, CopilotChatResponse>('/copilot/chat', body, { timeoutMs: 30_000 });
}

export function getProviderStatus() {
  return request<ProviderStatus>('/system/provider-status');
}

export function getTestDataStatus() {
  return request<TestDataStatus>('/test-data/status');
}

export function getTestDataScenarios() {
  return request<TestDataScenariosResponse>('/test-data/scenarios');
}

export function regenerateTestData(body: RegenerateTestDataRequest) {
  return post<RegenerateTestDataRequest, RegenerateTestDataResponse>(
    '/test-data/regenerate',
    body,
    { timeoutMs: 30_000 },
  );
}

export function getProviderCacheStatus() {
  return request<ProviderCacheStatus>('/system/provider-cache');
}

export function getMarketDataCacheStatus() {
  return request<ProviderCacheStatus>('/market-data/cache/status');
}

export function getServiceCacheStatus() {
  return request<ServiceCacheStatus>('/system/service-cache');
}

export function getUniverseStatus() {
  return request<UniverseStatus>('/system/universe-status');
}

export function getIntelligenceStatus() {
  return request<IntelligenceStatus>('/system/intelligence-status');
}

export function clearProviderCache() {
  return postWithoutBody<ProviderCacheStatus>('/system/provider-cache/clear');
}

export function clearMarketDataCache(domain?: string) {
  const query = domain ? `?domain=${encodeURIComponent(domain)}` : '';
  return postWithoutBody<ProviderCacheStatus>(`/market-data/cache/invalidate${query}`);
}

export function cleanupMarketDataCache() {
  return postWithoutBody<Record<string, unknown>>('/market-data/cache/cleanup');
}

export function clearServiceCache(prefix?: string) {
  const query = prefix ? `?prefix=${encodeURIComponent(prefix)}` : '';
  return postWithoutBody<ServiceCacheStatus>(`/system/service-cache/clear${query}`);
}

export function getLiveQuote(symbol: string) {
  return request<QuoteData>(`/market/live/quote/${symbol}`);
}

export function getLiveHistory(symbol: string, resolution = 'D', days = 240) {
  const normalizedSymbol = symbol.toUpperCase();
  return cachedRequest(
    `live-history:v3:${normalizedSymbol}:${resolution}:${days}`,
    () => request<HistoryData>(
      `/market/live/history/${normalizedSymbol}?resolution=${encodeURIComponent(resolution)}&days=${days}`,
      { timeoutMs: 10_000 },
    ).then((history) => assertCompatibleHistoryRange(history, days)),
    300_000,
  );
}

function assertCompatibleHistoryRange(history: HistoryData, requestedDays: number): HistoryData {
  const returnedCandles = history.returned_candles ?? history.candles?.length ?? 0;
  if (requestedDays >= 300) {
    const minimumCandles = Math.min(220, Math.round(requestedDays * 0.6));
    if (returnedCandles < minimumCandles) {
      throw new Error(
        `History range underfilled: ${returnedCandles} candles returned for ${requestedDays} requested days.`,
      );
    }
  }
  if (requestedDays >= 120) {
    const minimumCandles = Math.min(90, Math.round(requestedDays * 0.5));
    if (returnedCandles < minimumCandles) {
      throw new Error(
        `History range underfilled: ${returnedCandles} candles returned for ${requestedDays} requested days.`,
      );
    }
  }
  return history;
}

export function getLiveQuotes(symbols: string[]) {
  return request<LiveQuotesResponse>(
    `/market/live/quotes?symbols=${encodeURIComponent(symbols.join(','))}`,
  );
}
