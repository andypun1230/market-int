.PHONY: validate-application-data validate-market-snapshot validate-stock-snapshot validate-phase-4-4a validate-phase-4-4b validate-phase-4-4c validate-phase-4-4c-semantics validate-phase-4-4c-release-gate validate-phase-4-4c-blockers audit-rotation-integrity

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

audit-rotation-integrity:
	cd backend && python3 scripts/audit_rotation_integrity.py --entity all --all-intervals --live --json-output ../docs/rotation-integrity-validation.json --csv-output ../docs/rotation-integrity-validation.csv
