# Developer workflow shortcuts. Run `make help` for the list.

.DEFAULT_GOAL := help
PYTHON ?= python3

.PHONY: help install install-dev format lint type test check run models package clean

help: ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install the package with the full (ai) extra.
	$(PYTHON) -m pip install -e ".[ai]"

install-dev: ## Install dev + ai extras.
	$(PYTHON) -m pip install -e ".[ai,dev]"

format: ## Auto-format with Black.
	$(PYTHON) -m black gesturecam tests

lint: ## Lint with Ruff.
	$(PYTHON) -m ruff check gesturecam tests

type: ## Type-check the pure-logic core with mypy.
	$(PYTHON) -m mypy gesturecam/config gesturecam/gestures gesturecam/quality \
		gesturecam/face gesturecam/storage gesturecam/models \
		gesturecam/errors.py gesturecam/paths.py

test: ## Run the unit-test suite.
	$(PYTHON) -m pytest

check: lint type test ## Run lint, type-check and tests.

run: ## Launch the application.
	$(PYTHON) main.py

models: ## Pre-download the MediaPipe model assets.
	$(PYTHON) scripts/download_models.py

package: ## Build a standalone executable with PyInstaller.
	$(PYTHON) -m PyInstaller GestureCamPro.spec --noconfirm

clean: ## Remove caches and build artifacts.
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
