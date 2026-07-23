.PHONY: help install install-dev lint format type-check test clean run

help:
	@echo "Template CLI - Development Commands"
	@echo "===================================="
	@echo ""
	@echo "install         Install production dependencies"
	@echo "install-dev     Install development dependencies"
	@echo "lint            Run linting checks (ruff)"
	@echo "format          Format code with black"
	@echo "type-check      Run type checking (mypy)"
	@echo "test            Run tests with pytest"
	@echo "test-cov        Run tests with coverage report"
	@echo "clean           Remove build artifacts and caches"
	@echo "run             Run the CLI application"
	@echo ""

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

lint:
	ruff check template_cli test main.py

format:
	black template_cli test main.py

type-check:
	mypy template_cli

test:
	pytest -v

test-cov:
	pytest --cov=template_cli --cov-report=html --cov-report=term-missing

clean:
	rm -rf build/ dist/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name htmlcov -exec rm -rf {} +
	rm -f .coverage

run:
	python main.py --help
