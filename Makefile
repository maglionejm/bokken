# `make check` is the definition of done (see CONTRIBUTING.md).

.PHONY: install check lint format test validate-specs

install:
	uv sync

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

format:
	uv run ruff check --fix src tests
	uv run ruff format src tests

test:
	uv run pytest

validate-specs:
	openspec validate --strict --all

check: lint test validate-specs
