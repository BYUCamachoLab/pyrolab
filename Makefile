help:
	@echo 'make install:        Set up the dev environment (uv) and pre-commit hooks'
	@echo 'make precommit:      Run all pre-commit hooks on every file'
	@echo 'make doc:            Build the static documentation site'
	@echo 'make serve:          Serve the documentation site on localhost for browsing'
	@echo 'make test:           Run tests with pytest'
	@echo 'make format:         Sort imports and format code with ruff'
	@echo 'make patch:          Start a release candidate (also minor, major): 0.4.0 -> 0.4.1rc1'
	@echo 'make rc:             Publish the next candidate: 0.4.1rc1 -> 0.4.1rc2'
	@echo 'make release:        Release the current candidate: 0.4.1rc2 -> 0.4.1'

install:
	uv sync --all-extras
	uv run pre-commit install

precommit:
	uv run pre-commit run --all-files

doc:
	uv run --group docs jb build docs

serve:
	cd docs/_build/html && python3 -m http.server

format:
	uv run ruff check --fix
	uv run ruff format

mypy:
	uv run mypy -p pyrolab

test:
	uv run coverage run -m pytest
	uv run coverage report

jupytext:
	uvx jupytext **/*.ipynb --to py

notebooks:
	uvx jupytext docs/notebooks/**/*.py --to ipynb
	uvx jupytext docs/notebooks/*.py --to ipynb

build:
	rm -rf dist
	uv build

###############################################################################
# Releasing: every release starts as a release candidate on PyPI. Each target
# bumps the version, commits, tags vX.Y.Z, and pushes; the tag triggers
# .github/workflows/release.yml. See scripts/release.sh for the rules.

patch minor major rc release:
	@bash scripts/release.sh $@

.PHONY: help install precommit doc serve format mypy test jupytext notebooks build \
	patch minor major rc release
