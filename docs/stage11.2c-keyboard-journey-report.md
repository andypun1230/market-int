# Stage 11.2C Keyboard Journey Report

## Result

**PASS — 10/10**

| Journey | Result | Evidence |
|---|---|---|
| Launch → Home → Market → last subtab → back | PASS | End selected/focused Macro; returned Home |
| Search → AAPL → Stock Detail → close | PASS | Close initially focused; focus returned to AAPL entity control |
| Sectors → filter → result → detail → close | PASS | Top 3 filter; Energy opened; focus returned to Energy tile |
| Watchlist → sort/filter → entity → save/remove → close | PASS | Alphabetical selection; MSFT remove/add restored; modal focus returned |
| Reports → generate → preview → sections → close | PASS | End reached section 12; focus returned to Read Research |
| Copilot → question → send → clear | PASS | Response completed; Clear chat removed conversation |
| Settings → nested toggle → back | PASS | Reduce Motion toggled on/off and restored; returned Settings |
| Unmatched route → Home | PASS | Recovery action reached Home |
| Compare → select → inspect → close | PASS | Energy and Health Care selected; focus returned to Compare |
| Alert → drill-down → canonical destination | PASS | Energy alert opened canonical Energy detail; focus returned to alert |

Tab order is logical, Enter/Space activation is single-fire, horizontal tabs use roving focus, modal focus is trapped, Escape closes web modals, and no focus is hidden beneath bottom navigation.
