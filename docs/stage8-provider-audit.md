# Stage 8 Provider Audit

The canonical field-by-field provider audit is [stage8-data-and-provider-audit.md](./stage8-data-and-provider-audit.md).

## Outcome

- Live-capable today: Finnhub current quotes and Polygon adjusted daily OHLCV through the existing adapters.
- Not available today: production news, filings, earnings, corporate announcements, official economic calendar, and intraday OHLCV.
- Production News Intelligence: the default singleton has an explicit unavailable provider and no metadata repository, so it returns typed unavailable state. Previously validated metadata can be read only from a separately constructed service with an explicitly injected repository through the cache-only methods.
- Production Session Narrative: typed `daily_only` availability and daily-source provenance where supported, otherwise unavailable. It does not generate session-phase prose from daily bars.
- Test mode: explicit hermetic news events and intraday bars; never relabelled live.
- Model calls: not required and not used by the deterministic Stage 8 pipeline.

No existing credential is treated as proof of news or intraday entitlement. No article bodies are retained.
