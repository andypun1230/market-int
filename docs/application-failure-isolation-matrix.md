# Application Failure Isolation Matrix

This matrix documents expected behavior for recoverable provider, cache, calculation, and UI-state failures.

| Failure | Required behavior | Automated coverage |
| --- | --- | --- |
| Selected quote fails | Quote endpoint returns structured unavailable JSON; chart/history failures remain independent. | `test_api_error_contracts.py`; `validate_application_data.py` HTTP contract checks |
| Selected history fails | History endpoint returns structured unavailable JSON; quote endpoint remains independently usable. | `test_api_error_contracts.py`; history endpoint matrix |
| SPY benchmark history fails | Relative strength uses available comparisons, marks degraded coverage, and does not blank primary stock sections. | `test_phase_4_3.py` secondary benchmark regression |
| QQQ benchmark history fails | Same as SPY benchmark failure. | Relative strength metadata and stock-analysis matrix |
| Sector benchmark history fails | Relative strength score may fall back to neutral for that comparison but must expose missing benchmark coverage. | `test_phase_4_3.py` SNDK/XLK regression |
| Pattern calculation fails | Pattern section may be unavailable; support/resistance, trendline, volume, risk, RS, rating, and timeframe signals remain usable. | Stock-analysis aggregate section-level validator |
| Volume calculation fails | Volume section is recorded in `errors`; unrelated sections remain available. | Stock-analysis aggregate partial-failure contract |
| Rating calculation fails | Rating section is recorded in `errors`; technical and risk sections remain available. | Stock-analysis aggregate partial-failure contract |
| Leadership calculation fails | Leadership is optional; aggregate response remains usable. | Stock-analysis optional-field validation |
| Report dependency fails | Report must disclose missing or unavailable data and avoid fabricated live claims. | Optional report validator flag; report unit tests |
| Cache unavailable or stale | Stale-first aggregates return cached/partial data with `cache_status` and `refreshing`; no synchronous cascade. | `test_request_stability.py`; application validator partial classification |
| Provider timeout | Central provider handler returns structured unavailable response, not traceback/HTTP 500. | API error contract tests |
| Cancellation | Frontend must classify obsolete request cancellation separately from provider failure. | Manual required; listed in UI manifest |
| Malformed response | Validator detects missing fields, wrong JSON shape, raw errors, `NaN`, and infinity. | `data_quality.py`; application validator |
| Cold market structure materialization | `/market/details/structure` may return `HTTP 200` partial with `refreshing=true` until background refresh warms cache. | Application validator records as `PARTIAL`, not `FAIL` |

Current automated result: **PASS WITH CONDITIONS** because native visual and cancellation automation remain manual, and cold-cache stale-first partials are allowed by contract.
