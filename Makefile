.PHONY: install test run

install:
	pip install -e ".[dev]"

test:
	pytest -v --cov=src/repo_debug_agent

run:
	python -m repo_debug_agent.main