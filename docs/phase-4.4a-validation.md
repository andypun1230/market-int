# Phase 4.4A Validation

## Automated Validator

Run:

```bash
cd backend
python3 scripts/validate_phase_4_4a.py --mode test --warm
```

Root make target:

```bash
make validate-phase-4-4a
```

The validator checks:

- Home/Core/Market index values share the same snapshot payload
- `SPY`, `QQQ`, `IWM`, and `DIA` are present
- alias history requests route to provider-bound symbols
- watchlist warm read is served without repository quote/history fetches
- watchlist response includes membership hash, coverage, unavailable symbols, and status

## Expected Provider Routing

Raw index aliases should never be sent to Polygon stock aggregates directly:

- `SPX` routes as `SPY`
- `NDX` routes as `QQQ`
- `IXIC` routes as `QQQ`
- `RUT` routes as `IWM`
- `DJI` routes as `DIA`

## Consistency Matrix

| Surface | Index Source | Watchlist Source |
| --- | --- | --- |
| Home | MarketSnapshot `indexes` section | MarketSnapshot or compact summary |
| Market Indexes | MarketSnapshot `indexes` section | Not applicable |
| Watchlist | Not applicable | Repository quote/cache summary |
| Stock Detail | Existing StockAnalysisSnapshot | Existing quote/cache path |

## Performance Targets

Warm targets:

- Home indexes: under 500 ms
- Market Indexes: under 500 ms
- Watchlist summary: under 800 ms
- Warm provider calls: zero
- Watchlist initial history calls: zero

## Live Validation Notes

For live validation use:

```bash
cd backend
QUOTE_DATA_PROVIDER=finnhub \
HISTORY_DATA_PROVIDER=polygon \
MARKET_DATA_ALLOW_MOCK_FALLBACK=false \
python3 scripts/validate_phase_4_4a.py --mode live --warm
```

Cold live quote latency may vary by provider. Any unavailable symbol should be reported in `symbols_unavailable` without a 500 response.
