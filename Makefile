PYTHON ?= python3
STAGE7_RUNTIME_OUTPUT ?= ../artifacts/stage7-agent-validation.json
STAGE7_REFERENCE_OUTPUT ?= ../artifacts/stage7-reference-evaluation.json
STAGE7_REVIEW_OUTPUT ?= ../artifacts/stage7-human-review.json
STAGE8_PERFORMANCE_OUTPUT ?= ../artifacts/stage8-performance.json
STAGE8_VALIDATION_OUTPUT ?= ../artifacts/stage8-context-intelligence-validation.json
STAGE875_PERFORMANCE_OUTPUT ?= ../artifacts/stage8.75-performance.json
STAGE875_VALIDATION_OUTPUT ?= ../artifacts/stage8.75-theme-intelligence-validation.json
STAGE875_REPORT_OUTPUT ?= ../docs/validation/stage8.75-theme-intelligence-validation-report.md
STAGE875_SYMBOL_AUDIT_OUTPUT ?= ../artifacts/stage8.75-symbol-coverage-audit.json
STAGE875_COVERAGE_OUTPUT ?= ../artifacts/stage8.75-theme-coverage-matrix.json
STAGE875_ROTATION_OUTPUT ?= ../artifacts/stage8.75-theme-rotation-validation.json
STAGE875_ROTATION_MODEL_SPEC_OUTPUT ?= ../artifacts/stage8.75-theme-rotation-model-spec.json
STAGE875_ROTATION_PARAMETERS_OUTPUT ?= ../artifacts/stage8.75-theme-rotation-parameters.json
STAGE875_ROTATION_SENSITIVITY_OUTPUT ?= ../artifacts/stage8.75-theme-rotation-sensitivity.json
STAGE875_ROTATION_SYNTHETIC_OUTPUT ?= ../artifacts/stage8.75-theme-rotation-synthetic-tests.json
STAGE875_ROTATION_COORDINATES_OUTPUT ?= ../artifacts/stage8.75-theme-rotation-coordinates.json
STAGE875_ROTATION_PERFORMANCE_OUTPUT ?= ../artifacts/stage8.75-theme-rotation-performance.json
STAGE875_ROTATION_VISUAL_ACCEPTANCE_OUTPUT ?= ../artifacts/stage8.75-theme-rotation-frontend-visual-acceptance.json
STAGE875_SECTOR_ROTATION_OUTPUT ?= ../artifacts/stage8.75-sector-rotation-validation.json
STAGE875_SECTOR_ROTATION_MODEL_SPEC_OUTPUT ?= ../artifacts/stage8.75-sector-rotation-model-spec.json
STAGE875_SECTOR_ROTATION_PARAMETERS_OUTPUT ?= ../artifacts/stage8.75-sector-rotation-parameters.json
STAGE875_SECTOR_ROTATION_SYNTHETIC_OUTPUT ?= ../artifacts/stage8.75-sector-rotation-synthetic-tests.json
STAGE875_SECTOR_ROTATION_COORDINATES_OUTPUT ?= ../artifacts/stage8.75-sector-rotation-coordinates.json
STAGE875_SECTOR_ROTATION_PERFORMANCE_OUTPUT ?= ../artifacts/stage8.75-sector-rotation-performance.json
STAGE875_SECTOR_ROTATION_REPORT_OUTPUT ?= ../docs/validation/stage8.75-sector-rotation-validation-report.md

.PHONY: validate-application-data validate-market-snapshot validate-stock-snapshot validate-phase-4-4a validate-phase-4-4b validate-phase-4-4c validate-phase-4-4c-semantics validate-phase-4-4c-release-gate validate-phase-4-4c-blockers validate-phase-4-4d validate-phase-4-4d-governance validate-phase-4-4d-pilot validate-phase-4-4d-pilot-integration validate-stage7 validate-stage75 test-stage8-news test-stage8-session test-stage8-routing test-stage8-safety test-stage8-performance validate-stage8-components validate-stage8 validate-stage8-75 audit-rotation-integrity

validate-application-data:
	cd backend && python3 -m compileall app main.py
	cd backend && python3 -m unittest discover -s tests
	cd backend && python3 scripts/validate_phase_4_1.py --mode test
	cd backend && python3 scripts/validate_phase_4_2.py --mode test
	cd backend && python3 scripts/validate_phase_4_3.py --mode test
	cd backend && python3 scripts/validate_phase_4_4b.py --test
	cd backend && python3 scripts/validate_application_data.py --mode test --json-output ../docs/application-data-integrity-validation.json
	cd frontend && npx tsc --noEmit
	cd frontend && npm run lint
	cd frontend && npm run validate:data-ui

validate-market-snapshot:
	cd backend && python3 -m compileall app main.py scripts
	cd backend && python3 -m unittest tests.test_market_snapshot_architecture
	cd backend && python3 scripts/validate_market_snapshot_performance.py --test --warm --json-output ../docs/market-snapshot-performance-validation.json

validate-stock-snapshot:
	cd backend && python3 -m compileall app main.py scripts
	cd backend && python3 -m unittest tests.test_stock_snapshot_architecture tests.test_api_error_contracts
	cd backend && python3 scripts/validate_stock_snapshot_performance.py --test --warm --restart --json-output ../docs/stock-snapshot-performance-validation.json

validate-phase-4-4a:
	cd backend && python3 -m compileall app main.py scripts
	cd backend && python3 -m unittest tests.test_market_snapshot_architecture tests.test_request_stability tests.test_market_data_repository tests.test_symbol_registry
	cd backend && python3 scripts/validate_phase_4_4a.py --mode test --warm --json-output ../docs/phase-4.4a-validation.json

validate-phase-4-4b:
	cd backend && python3 -m compileall app main.py scripts
	cd backend && python3 -m unittest tests.test_breadth_snapshot
	cd backend && python3 scripts/validate_phase_4_4b.py --test --json-output ../docs/phase-4.4b-validation.json

validate-phase-4-4c:
	cd backend && python3 -m compileall app main.py scripts
	cd backend && python3 -m unittest discover -s tests -p 'test_sector_snapshot.py'
	cd backend && python3 scripts/validate_phase_4_4c.py --test --warm --restart --json-output ../docs/phase-4.4c-validation.json

validate-phase-4-4c-semantics:
	cd backend && python3 -m compileall app main.py scripts
	cd backend && python3 -m unittest tests.test_breadth_snapshot tests.test_sector_snapshot
	cd backend && python3 scripts/validate_phase_4_4c_semantics.py --test --warm --report --json-output ../docs/phase-4.4c-semantics-validation.json

validate-phase-4-4c-release-gate:
	cd backend && python3 -m compileall app main.py scripts
	cd backend && python3 scripts/validate_phase_4_4c_release_gate.py --test --live --warm --restart --report --copilot-context --json-output ../docs/phase-4.4c-final-release-gate.json --markdown-output ../docs/phase-4.4c-final-release-gate.md

validate-phase-4-4c-blockers:
	cd backend && python3 -m compileall app main.py scripts
	cd backend && python3 scripts/validate_phase_4_4c_blockers.py --test --live --warm --restart --report --copilot-context --json-output ../docs/phase-4.4c-blockers-final.json --markdown-output ../docs/phase-4.4c-blockers-final.md

validate-phase-4-4d:
	cd backend && python3 -m compileall app main.py scripts
	cd backend && python3 -m unittest tests.test_theme_intelligence
	cd backend && python3 scripts/validate_phase_4_4d.py --test --live --warm --restart --report --copilot-context --json-output ../docs/phase-4.4d-validation.json --markdown-output ../docs/phase-4.4d-validation.md

validate-phase-4-4d-governance:
	cd backend && python3 -m compileall app main.py scripts
	cd backend && python3 -m unittest tests.test_theme_intelligence
	cd backend && python3 scripts/audit_theme_provenance.py --all-themes --mode all --json-output ../docs/phase-4.4d-theme-provenance.json --markdown-output ../docs/phase-4.4d-theme-provenance.md
	cd backend && python3 scripts/import_theme_definitions.py --theme memory_storage --definition-file data/reference/themes/memory-storage-v1.1.md --members-file data/reference/themes/memory-storage-v1.1.csv --version v1.1 --dry-run --json-output ../docs/phase-4.4d-memory-storage-v1.1-import-dry-run.json
	cd backend && python3 scripts/import_theme_definitions.py --theme cybersecurity --definition-file data/reference/themes/cybersecurity-v1.1.md --members-file data/reference/themes/cybersecurity-v1.1.csv --version v1.1 --dry-run --json-output ../docs/phase-4.4d-cybersecurity-v1.1-import-dry-run.json
	cd frontend && npx tsc --noEmit
	cd frontend && npm run lint
	cd frontend && npm run validate:data-ui
	cd frontend && npx tsx tests/themeSnapshot.test.ts && npx tsx tests/themeGovernanceStatus.test.ts

validate-phase-4-4d-pilot:
	cd backend && python3 scripts/validate_phase_4_4d.py --live --pilot --warm --restart --report --copilot-context --json-output ../docs/phase-4.4d-pilot-validation.json --markdown-output ../docs/phase-4.4d-pilot-validation.md
	cd backend && python3 scripts/audit_theme_provenance.py --all-themes --mode all --json-output ../docs/phase-4.4d-theme-provenance.json --markdown-output ../docs/phase-4.4d-theme-provenance.md
	cd backend && python3 scripts/audit_theme_scoring.py --themes memory_storage,cybersecurity --json-output ../docs/phase-4.4d-pilot-scoring-audit.json --markdown-output ../docs/phase-4.4d-pilot-scoring-audit.md

validate-phase-4-4d-pilot-integration:
	cd backend && python3 scripts/validate_phase_4_4d_pilot_integration.py --test --live --warm --restart --report --copilot-context --basket-audit --json-output ../docs/phase-4.4d-pilot-integration-final.json --markdown-output ../docs/phase-4.4d-pilot-integration-final.md

audit-rotation-integrity:
	cd backend && python3 scripts/audit_rotation_integrity.py --entity all --all-intervals --live --json-output ../docs/rotation-integrity-validation.json --csv-output ../docs/rotation-integrity-validation.csv

validate-stage7:
	cd backend && $(PYTHON) -m compileall -q app main.py scripts tests
	cd backend && $(PYTHON) -m unittest discover -s tests
	cd backend && $(PYTHON) scripts/generate_stage7_copilot_artifacts.py --check
	cd backend && $(PYTHON) -m app.copilot.evaluation.run_stage7 --mode runtime --suite full --output $(STAGE7_RUNTIME_OUTPUT)
	cd backend && $(PYTHON) -m app.copilot.evaluation.run_stage7 --mode reference --suite full --output $(STAGE7_REFERENCE_OUTPUT)
	cd backend && $(PYTHON) -m app.copilot.evaluation.review build --results $(STAGE7_REFERENCE_OUTPUT) --output $(STAGE7_REVIEW_OUTPUT)
	cd frontend && npx tsc --noEmit
	cd frontend && npm run lint
	cd frontend && npm run validate:data-ui
	cd frontend && npx tsx tests/copilotContracts.test.ts
	cd frontend && npx tsx tests/copilotTransport.test.ts
	cd frontend && npx tsx tests/copilotReducer.test.ts
	cd frontend && npx tsx tests/copilotDestinations.test.ts

validate-stage75:
	$(MAKE) validate-stage7 PYTHON=$(PYTHON) STAGE7_RUNTIME_OUTPUT=../artifacts/stage75-post-refactor-runtime-evaluation.json STAGE7_REFERENCE_OUTPUT=../artifacts/stage75-post-refactor-reference-evaluation.json STAGE7_REVIEW_OUTPUT=../artifacts/stage75-post-refactor-human-review.json
	cd frontend && npx expo export --platform web
	cd backend && $(PYTHON) -m app.copilot.evaluation.run_stage7 --mode runtime --suite full --output ../artifacts/stage75-post-refactor-runtime-evaluation.json
	cd backend && $(PYTHON) scripts/augment_stage75_runtime_actions.py --artifact ../artifacts/stage75-post-refactor-runtime-evaluation.json
	cd backend && $(PYTHON) scripts/compare_stage75_semantics.py --before ../artifacts/stage75-pre-refactor-runtime-evaluation.json --after ../artifacts/stage75-post-refactor-runtime-evaluation.json --output ../artifacts/stage75-semantic-equivalence.json
	cd backend && $(PYTHON) scripts/benchmark_stage75_engines.py --output ../artifacts/stage75-engine-performance.json

test-stage8-news:
	cd backend && $(PYTHON) -m unittest discover -s tests/stage8 -p 'test_news_*.py'

test-stage8-session:
	cd backend && $(PYTHON) -m unittest discover -s tests/stage8 -p 'test_session_*.py'

test-stage8-routing:
	cd backend && $(PYTHON) -m unittest tests.stage8.test_stage8_routing tests.stage8.test_stage8_copilot_integration tests.stage8.test_stage8_api

test-stage8-safety:
	cd backend && $(PYTHON) -m unittest tests.stage8.test_stage8_safety tests.stage8.test_stage8_failure_injection tests.stage8.test_golden_fixtures

test-stage8-performance:
	cd backend && $(PYTHON) -m unittest tests.stage8.test_stage8_performance
	cd backend && $(PYTHON) scripts/benchmark_stage8_intelligence.py --output $(STAGE8_PERFORMANCE_OUTPUT)

validate-stage8-components:
	cd backend && $(PYTHON) -m compileall -q app main.py scripts tests
	cd backend && $(PYTHON) tests/fixtures/stage8/generate_cases.py --check
	cd backend && $(PYTHON) -m unittest discover -s tests/stage8 -p 'test_*.py'
	cd frontend && npx tsc --noEmit
	cd frontend && npm run lint
	cd frontend && npm run validate:data-ui
	cd frontend && npx tsx tests/newsIntelligenceNormalizer.test.ts
	cd frontend && npx tsx tests/sessionNarrativePresenter.test.ts
	cd frontend && npx tsx tests/contextIntelligenceConsumers.test.ts
	cd frontend && npx tsx tests/newsRequestDeduplication.test.ts
	cd backend && $(PYTHON) scripts/benchmark_stage8_intelligence.py --output $(STAGE8_PERFORMANCE_OUTPUT)

validate-stage8:
	$(MAKE) validate-stage75 PYTHON=$(PYTHON)
	$(MAKE) validate-stage8-components PYTHON=$(PYTHON)
	cd backend && $(PYTHON) scripts/validate_stage8_context_intelligence.py --performance-artifact $(STAGE8_PERFORMANCE_OUTPUT) --output $(STAGE8_VALIDATION_OUTPUT)

validate-stage8-75:
	cd backend && $(PYTHON) -m compileall -q app main.py scripts tests
	cd backend && $(PYTHON) -m unittest discover -s tests/stage8_75 -p 'test_*.py'
	cd backend && $(PYTHON) tests/fixtures/stage8/generate_cases.py --check
	cd backend && $(PYTHON) -m unittest discover -s tests/stage8 -p 'test_*.py'
	cd backend && $(PYTHON) scripts/generate_stage7_copilot_artifacts.py --check
	cd backend && $(PYTHON) -m app.copilot.evaluation.run_stage7 --mode runtime --suite full --output ../artifacts/stage8.75-stage7-runtime-evaluation.json
	cd backend && $(PYTHON) scripts/augment_stage75_runtime_actions.py --artifact ../artifacts/stage8.75-stage7-runtime-evaluation.json
	cd backend && $(PYTHON) -m app.copilot.evaluation.run_stage7 --mode reference --suite full --output ../artifacts/stage8.75-stage7-reference-evaluation.json
	cd backend && $(PYTHON) -m app.copilot.evaluation.review build --results ../artifacts/stage8.75-stage7-reference-evaluation.json --output ../artifacts/stage8.75-stage7-human-review.json
	cd backend && $(PYTHON) scripts/compare_stage75_semantics.py --before ../artifacts/stage75-pre-refactor-runtime-evaluation.json --after ../artifacts/stage8.75-stage7-runtime-evaluation.json --output ../artifacts/stage8.75-stage7-semantic-equivalence.json
	cd backend && $(PYTHON) -m unittest discover -s tests
	cd frontend && npx tsc --noEmit
	cd frontend && npm run lint
	cd frontend && npm run validate:data-ui
	cd frontend && npx tsx tests/copilotContracts.test.ts
	cd frontend && npx tsx tests/copilotTransport.test.ts
	cd frontend && npx tsx tests/copilotReducer.test.ts
	cd frontend && npx tsx tests/copilotDestinations.test.ts
	cd frontend && npx tsx tests/themeSnapshot.test.ts
	cd frontend && npx tsx tests/themeRotation.test.ts
	cd frontend && npx tsx tests/themeRotationView.test.ts
	cd frontend && npx tsx tests/sectorSnapshot.test.ts
	cd frontend && npx tsx tests/rotationCopy.test.ts
	cd frontend && npx tsx tests/themeGovernanceStatus.test.ts
	cd frontend && npx tsx tests/themeHomeSummary.test.ts
	cd frontend && npx tsx tests/watchlistSectorThemes.test.ts
	cd frontend && npx tsx tests/newsIntelligenceNormalizer.test.ts
	cd frontend && npx tsx tests/sessionNarrativePresenter.test.ts
	cd frontend && npx tsx tests/contextIntelligenceConsumers.test.ts
	cd frontend && npx tsx tests/newsRequestDeduplication.test.ts
	cd frontend && npx expo export --platform web
	cd backend && $(PYTHON) scripts/validate_stage8_75_theme_rotation_model.py --model-spec-output $(STAGE875_ROTATION_MODEL_SPEC_OUTPUT) --parameters-output $(STAGE875_ROTATION_PARAMETERS_OUTPUT) --sensitivity-output $(STAGE875_ROTATION_SENSITIVITY_OUTPUT) --synthetic-output $(STAGE875_ROTATION_SYNTHETIC_OUTPUT) --coordinates-output $(STAGE875_ROTATION_COORDINATES_OUTPUT) --performance-output $(STAGE875_ROTATION_PERFORMANCE_OUTPUT)
	cd backend && $(PYTHON) scripts/validate_stage8_75_theme_rotation.py --output $(STAGE875_ROTATION_OUTPUT)
	cd backend && $(PYTHON) scripts/validate_stage8_75_sector_rotation.py --output $(STAGE875_SECTOR_ROTATION_OUTPUT) --spec-output $(STAGE875_SECTOR_ROTATION_MODEL_SPEC_OUTPUT) --parameters-output $(STAGE875_SECTOR_ROTATION_PARAMETERS_OUTPUT) --synthetic-output $(STAGE875_SECTOR_ROTATION_SYNTHETIC_OUTPUT) --coordinates-output $(STAGE875_SECTOR_ROTATION_COORDINATES_OUTPUT) --performance-output $(STAGE875_SECTOR_ROTATION_PERFORMANCE_OUTPUT) --markdown-output $(STAGE875_SECTOR_ROTATION_REPORT_OUTPUT)
	cd frontend && npx tsx scripts/benchmark-theme-rotation.mjs --artifact $(STAGE875_ROTATION_OUTPUT)
	cd frontend && npx tsx scripts/validate-theme-rotation-view.mjs
	cd backend && $(PYTHON) scripts/benchmark_stage8_75_theme_intelligence.py --output $(STAGE875_PERFORMANCE_OUTPUT)
	cd backend && $(PYTHON) scripts/validate_stage8_75_theme_intelligence.py --release-gates-passed --performance-artifact $(STAGE875_PERFORMANCE_OUTPUT) --rotation-artifact $(STAGE875_ROTATION_OUTPUT) --rotation-visual-acceptance $(STAGE875_ROTATION_VISUAL_ACCEPTANCE_OUTPUT) --symbol-audit $(STAGE875_SYMBOL_AUDIT_OUTPUT) --coverage-output $(STAGE875_COVERAGE_OUTPUT) --output $(STAGE875_VALIDATION_OUTPUT) --markdown-output $(STAGE875_REPORT_OUTPUT)
