.PHONY: help install install-py install-js lint test clean

help:
	@echo "Targets: install install-py install-js lint test clean"

install: install-py install-js

install-py:
	# TODO: wire to uv or pip install -e packages/*

install-js:
	npm install

lint:
	# TODO: ruff, mypy, eslint as wired

test:
	# TODO: pytest, contract tests

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null; true
	rm -rf node_modules .venv
