PYTHON ?= python3

.PHONY: validate-application-data validate-market-snapshot validate-stock-snapshot validate-phase-4-4a validate-phase-4-4b validate-phase-4-4c validate-phase-4-4c-semantics validate-phase-4-4c-release-gate validate-phase-4-4c-blockers validate-phase-4-4d validate-phase-4-4d-governance validate-phase-4-4d-pilot validate-phase-4-4d-pilot-integration validate-stage7 audit-rotation-integrity

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
	cd backend && $(PYTHON) -m app.copilot.evaluation.run_stage7 --mode runtime --suite full --output ../artifacts/stage7-agent-validation.json
	cd backend && $(PYTHON) -m app.copilot.evaluation.run_stage7 --mode reference --suite full --output ../artifacts/stage7-reference-evaluation.json
	cd backend && $(PYTHON) -m app.copilot.evaluation.review build --results ../artifacts/stage7-reference-evaluation.json --output ../artifacts/stage7-human-review.json
	cd frontend && npx tsc --noEmit
	cd frontend && npm run lint
	cd frontend && npm run validate:data-ui
	cd frontend && npx tsx tests/copilotContracts.test.ts
	cd frontend && npx tsx tests/copilotTransport.test.ts
	cd frontend && npx tsx tests/copilotReducer.test.ts
	cd frontend && npx tsx tests/copilotDestinations.test.ts
