.PHONY: test lint format-check typecheck security audit quality coverage compile-examples generated-quality online-mock online-mock-quality v20-e2e v20-e2e-live clean

test:
	pytest -q

lint:
	ruff check src tests

format-check:
	ruff format --check src tests

typecheck:
	mypy src/ssm

security:
	bandit -q -r src/ssm

audit:
	pip-audit

coverage:
	pytest --cov=ssm --cov-report=term-missing

quality: lint format-check typecheck test security

compile-examples:
	python -m ssm.cli.main compile examples/inventory_api/project.sml.md --out build/inventory_api
	python -m ssm.cli.main compile examples/todo_api/project.sml.md --out build/todo_api

generated-quality: compile-examples
	cd build/inventory_api && python -m pip install -e '.[dev]' && ruff check . && ruff format --check . && mypy app && pytest && bandit -q -r app
	cd build/inventory_api/admin && npm install --no-audit --no-fund && npm run typecheck && npm run build
	cd build/todo_api && python -m pip install -e '.[dev]' && ruff check . && ruff format --check . && mypy app && pytest && bandit -q -r app
	cd build/todo_api/admin && npm install --no-audit --no-fund && npm run typecheck && npm run build

online-mock:
	RUN_ONLINE_AI=1 SSM_AGENT_MODE=online SSM_LLM_PROVIDER=mock SSM_LLM_MODEL=mock python -m ssm.cli.main draft --agent-mode online --prompt "Build a FastAPI inventory API with PostgreSQL, JWT auth, product CRUD, SKU uniqueness, pagination, OpenAPI contract tests, and Docker support." --out build/online_inventory/project.sml.md
	python -m ssm.cli.main validate build/online_inventory/project.sml.md
	python -m ssm.cli.main compile build/online_inventory/project.sml.md --out build/online_inventory_api

online-mock-quality: online-mock
	cd build/online_inventory_api && python -m pip install -e '.[dev]' && ruff check . && ruff format --check . && mypy app && pytest && bandit -q -r app
	cd build/online_inventory_api/admin && npm install --no-audit --no-fund && npm run typecheck && npm run build

v20-e2e:
	RUN_DEEPSEEK_LIVE=0 ./scripts/test_v20_e2e.sh

v20-e2e-live:
	RUN_DEEPSEEK_LIVE=1 ./scripts/test_v20_e2e.sh

clean:
	rm -rf build .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage
