# `make check` is the definition of done (see CONTRIBUTING.md).

.PHONY: install check lint format test validate-specs gallery

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

# Rebuild the published demo artifacts on the GitHub Page from `bokken demo`.
# Built with the [ui] extra so the specimen includes the walkthrough and the
# per-feature browser tests of the bundled mock app.
gallery:
	@H=$$(mktemp -d); BOKKEN_HOME=$$H uv run --extra ui bokken demo gallery >/dev/null; \
	mkdir -p docs/gallery; \
	cp $$H/sessions/gallery/report/report.html docs/gallery/demo-report.html; \
	cp $$H/sessions/gallery/report/report.pptx docs/gallery/demo-deck.pptx; \
	echo "gallery refreshed: docs/gallery/demo-report.html + demo-deck.pptx"
