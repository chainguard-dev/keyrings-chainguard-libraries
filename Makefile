.PHONY: help install install-dev test test-coverage lint format clean build upload

help:
	@echo "Available targets:"
	@echo "  install        Install the package"
	@echo "  install-dev    Install the package in development mode with dev dependencies"
	@echo "  test           Run tests"
	@echo "  test-coverage  Run tests with coverage"
	@echo "  lint           Run linting checks"
	@echo "  format         Format code with black"
	@echo "  clean          Clean build artifacts"
	@echo "  build          Build the package"
	@echo "  upload         Upload package to PyPI"

install:
	pip install .

install-dev:
	pip install -e ".[dev]"

test:
	pytest

test-coverage:
	pytest --cov=keyrings.chainctl_auth --cov-report=html --cov-report=term

lint:
	flake8 keyrings/
	mypy keyrings/
	black keyrings/ --diff

format:
	black keyrings/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

upload: build
	python -m twine upload dist/*
