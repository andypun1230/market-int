# Stage 8.75 Theme Intelligence Validation Report

Result: **PASS WITH CONDITIONS**

Baseline commit: `30dc780de6c004e239fe5d768bcc4cc098464573`

Taxonomy version: `2026.07.1`

## Launch taxonomy

| ID | Name | Parent sectors | Constituents | Core | Status | Coverage | Benchmarks | Known limitations |
|---|---|---|---:|---:|---|---|---|---|
| artificial_intelligence | Artificial Intelligence | information_technology, communication_services | 10 | 2 | active | market analytics unavailable until governed history is published | SPY, QQQ, XLK | Current-basket mappings; historical membership reconstruction is not yet available. |
| semiconductors | Semiconductors | information_technology | 10 | 7 | active | market analytics unavailable until governed history is published | SPY, QQQ, SOXX | Current-basket mappings; historical membership reconstruction is not yet available. |
| memory_storage | Memory & Storage | information_technology | 7 | 4 | active | market analytics unavailable until governed history is published | SPY, QQQ, XLK | Current-basket mappings; historical membership reconstruction is not yet available. |
| data_centers | Data Centers | real_estate, information_technology, industrials | 9 | 3 | active | market analytics unavailable until governed history is published | SPY, QQQ, XLRE | Current-basket mappings; historical membership reconstruction is not yet available. |
| cloud_computing | Cloud Computing | information_technology, communication_services | 9 | 4 | active | market analytics unavailable until governed history is published | SPY, QQQ, SKYY | Current-basket mappings; historical membership reconstruction is not yet available. |
| enterprise_software | Enterprise Software | information_technology | 9 | 7 | active | market analytics unavailable until governed history is published | SPY, QQQ, IGV | Current-basket mappings; historical membership reconstruction is not yet available. |
| cybersecurity | Cybersecurity | information_technology | 7 | 6 | active | market analytics unavailable until governed history is published | SPY, QQQ, CIBR | Current-basket mappings; historical membership reconstruction is not yet available. |
| networking_infrastructure | Networking Infrastructure | information_technology, communication_services | 9 | 4 | active | market analytics unavailable until governed history is published | SPY, QQQ, XLK | Current-basket mappings; historical membership reconstruction is not yet available. |
| robotics_automation | Robotics & Automation | industrials, information_technology | 9 | 4 | active | market analytics unavailable until governed history is published | SPY, XLI, ROBO | Current-basket mappings; historical membership reconstruction is not yet available. |
| digital_advertising | Digital Advertising | communication_services, information_technology | 9 | 5 | active | market analytics unavailable until governed history is published | SPY, QQQ, XLC | Current-basket mappings; historical membership reconstruction is not yet available. |
| ecommerce | E-commerce | consumer_discretionary, information_technology | 9 | 7 | active | market analytics unavailable until governed history is published | SPY, QQQ, IBUY | Current-basket mappings; historical membership reconstruction is not yet available. |
| digital_payments | Digital Payments | financials, information_technology | 9 | 5 | active | market analytics unavailable until governed history is published | SPY, XLF, IPAY | Current-basket mappings; historical membership reconstruction is not yet available. |
| online_travel | Online Travel | consumer_discretionary, communication_services | 7 | 7 | active | market analytics unavailable until governed history is published | SPY, XLY, AWAY | Current-basket mappings; historical membership reconstruction is not yet available. |
| gaming_interactive_media | Gaming & Interactive Media | communication_services, information_technology | 8 | 4 | active | market analytics unavailable until governed history is published | SPY, XLC, HERO | Current-basket mappings; historical membership reconstruction is not yet available. |
| streaming_digital_entertainment | Streaming & Digital Entertainment | communication_services | 8 | 3 | active | market analytics unavailable until governed history is published | SPY, XLC, QQQ | Current-basket mappings; historical membership reconstruction is not yet available. |
| aerospace_defense | Aerospace & Defense | industrials | 9 | 6 | active | market analytics unavailable until governed history is published | SPY, XLI, ITA | Current-basket mappings; historical membership reconstruction is not yet available. |
| space_economy | Space Economy | industrials, communication_services | 8 | 6 | active | market analytics unavailable until governed history is published | SPY, XLI, ARKX | Current-basket mappings; historical membership reconstruction is not yet available. |
| drones_autonomous_systems | Drones & Autonomous Systems | industrials, information_technology | 8 | 2 | active | market analytics unavailable until governed history is published | SPY, XLI, ARKQ | Current-basket mappings; historical membership reconstruction is not yet available. |
| nuclear_energy | Nuclear Energy | energy, utilities, industrials | 9 | 7 | active | market analytics unavailable until governed history is published | SPY, XLU, URA | Current-basket mappings; historical membership reconstruction is not yet available. |
| grid_modernization | Grid Modernization | industrials, utilities, information_technology | 9 | 4 | active | market analytics unavailable until governed history is published | SPY, XLI, GRID | Current-basket mappings; historical membership reconstruction is not yet available. |
| clean_energy | Clean Energy | energy, utilities, industrials, information_technology | 9 | 6 | active | market analytics unavailable until governed history is published | SPY, ICLN, TAN | Current-basket mappings; historical membership reconstruction is not yet available. |
| electric_vehicles_batteries | Electric Vehicles & Batteries | consumer_discretionary, industrials, materials | 10 | 6 | active | market analytics unavailable until governed history is published | SPY, XLY, DRIV | Current-basket mappings; historical membership reconstruction is not yet available. |
| biotechnology | Biotechnology | health_care | 10 | 8 | active | market analytics unavailable until governed history is published | SPY, XLV, XBI | Current-basket mappings; historical membership reconstruction is not yet available. |
| obesity_metabolic_health | Obesity & Metabolic Health | health_care | 8 | 3 | active | market analytics unavailable until governed history is published | SPY, XLV, XBI | Current-basket mappings; historical membership reconstruction is not yet available. |
| medical_technology | Medical Technology | health_care | 9 | 8 | active | market analytics unavailable until governed history is published | SPY, XLV, IHI | Current-basket mappings; historical membership reconstruction is not yet available. |
| cryptocurrency_infrastructure | Cryptocurrency Infrastructure | financials, information_technology | 9 | 7 | active | market analytics unavailable until governed history is published | SPY, QQQ, BITQ | Current-basket mappings; historical membership reconstruction is not yet available. |

## Release gates

- focused tests: passed
- stage7 frozen corpus: passed
- stage7 runtime: passed
- stage7 reference: passed
- stage7 5 semantic equivalence: passed
- stage8 regression: passed
- full backend: passed
- frontend typecheck: passed
- frontend lint: passed
- frontend data ui: passed
- frontend route export: passed
- agent registry: passed
- benchmark: passed

## Performance

Hermetic local measurements only; zero network calls and zero model calls. These are not production latency claims.

| Operation | p50 ms | p95 ms |
|---|---:|---:|
| api symbol mapping | 0.7605 | 0.8882 |
| api theme detail | 7.6261 | 7.9895 |
| api theme directory | 14.6011 | 15.0725 |
| copilot theme retrieval | 12.441 | 12.8265 |
| full theme ranking | 12.2164 | 12.7298 |
| report theme candidate retrieval | 0.8569 | 0.9142 |
| single theme detail | 6.298 | 6.4577 |
| symbol to theme lookup | 0.0065 | 0.0067 |
| taxonomy retrieval | 0.3131 | 0.4014 |

## Known conditions

- Only the original human-reviewed pilot themes can have live snapshots until providers publish governed history for the expanded taxonomy.
- Unavailable launch themes are directory-ready but are excluded from rankings, Reports, and strong Copilot conclusions.
- Historical analytics use current membership; historical membership reconstruction remains future work.

## Reproduction

`make validate-stage8-75 PYTHON=python3`
