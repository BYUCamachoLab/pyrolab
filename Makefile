help:
	@echo 'make install:        Set up the dev environment (uv) and pre-commit hooks'
	@echo 'make precommit:      Run all pre-commit hooks on every file'
	@echo 'make doc:            Build the static documentation site'
	@echo 'make serve:          Serve the documentation site on localhost for browsing'
	@echo 'make test:           Run tests with pytest'
	@echo 'make format:         Sort imports and format code with ruff'
	@echo 'make release-patch:  Bump, tag, and push a release (also -minor, -major)'
	@echo 'make rc:              Bump, tag, and push a release candidate (BUMP=patch|minor|major)'

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
#
# make rc goes to the next release candidate: 0.4.0 -> 0.5.0rc1 (a minor
# release unless BUMP=patch or BUMP=major), then 0.5.0rc1 -> 0.5.0rc2.
# make release-* on a release candidate finalizes it: 0.5.0rc2 -> 0.5.0 (a
# plain --bump minor would skip ahead to 0.6.0).
# Both need docs/changelog/<X.Y.Z>-changelog.md; candidates share the final
# release's changelog.

release-patch: BUMP = patch
release-minor: BUMP = minor
release-major: BUMP = major
rc: BUMP ?= minor

# The release a version leads up to: 0.5.0rc1 -> 0.5.0, 0.5.0 -> 0.5.0.
BASE_VERSION = sed -E 's/(a|b|rc)[0-9]+$$//'

release-patch release-minor release-major rc:
	@test -z "$$(git status --porcelain)" || \
		{ echo "Working tree is not clean; commit or stash changes first."; exit 1; }
	@OLD=$$(uv version --short) && \
	if [ "$$(echo $$OLD | $(BASE_VERSION))" != "$$OLD" ]; then \
		if [ "$@" = rc ]; then ARGS="--bump rc"; else ARGS="--bump stable"; fi; \
	elif [ "$@" = rc ]; then ARGS="--bump $(BUMP) --bump rc"; \
	else ARGS="--bump $(BUMP)"; fi && \
	NEW=$$(uv version $$ARGS --dry-run --short) && \
	NOTES=docs/changelog/$$(echo $$NEW | $(BASE_VERSION))-changelog.md && \
	{ test -f $$NOTES || { echo "Missing $$NOTES (the release body)."; exit 1; }; } && \
	echo "Releasing $$NEW (was $$OLD)" && \
	uv version $$ARGS && \
	git add pyproject.toml uv.lock && \
	git commit -m "Bump version: $$OLD → $$NEW" && \
	git tag v$$NEW && \
	git push && \
	git push origin v$$NEW

.PHONY: help install precommit doc serve format mypy test jupytext notebooks build \
	release-patch release-minor release-major rc
