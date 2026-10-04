help:
	@echo 'make install:        Set up the dev environment (uv) and pre-commit hooks'
	@echo 'make precommit:      Run all pre-commit hooks on every file'
	@echo 'make doc:            Build the static documentation site'
	@echo 'make serve:          Serve the documentation site on localhost for browsing'
	@echo 'make test:           Run tests with pytest'
	@echo 'make format:         Sort imports and format code with ruff'
	@echo 'make release-patch:  Bump, tag, and push a release (also -minor, -major)'

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
# Releasing: bumps the version in pyproject.toml (and uv.lock), commits, tags
# vX.Y.Z, and pushes. The tag triggers .github/workflows/release.yml.

release-patch: BUMP = patch
release-minor: BUMP = minor
release-major: BUMP = major

release-patch release-minor release-major:
	@test -z "$$(git status --porcelain)" || \
		{ echo "Working tree is not clean; commit or stash changes first."; exit 1; }
	@OLD=$$(uv version --short) && \
	NEW=$$(uv version --bump $(BUMP) --dry-run --short) && \
	test -f docs/changelog/$$NEW-changelog.md || \
		{ echo "Missing docs/changelog/$$NEW-changelog.md (the release body)."; exit 1; } && \
	uv version --bump $(BUMP) && \
	git add pyproject.toml uv.lock && \
	git commit -m "Bump version: $$OLD → $$NEW" && \
	git tag v$$NEW && \
	git push && \
	git push origin v$$NEW

.PHONY: help install precommit doc serve format mypy test jupytext notebooks build \
	release-patch release-minor release-major
