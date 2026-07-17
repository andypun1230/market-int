.PHONY: validate-application-data validate-market-snapshot validate-stock-snapshot

validate-application-data:
	cd backend && python3 -m compileall app main.py
	cd backend && python3 -m unittest discover -s tests
	cd backend && python3 scripts/validate_phase_4_1.py --mode test
	cd backend && python3 scripts/validate_phase_4_2.py --mode test
	cd backend && python3 scripts/validate_phase_4_3.py --mode test
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
