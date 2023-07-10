help:
	@echo 'make venv:			Create venv for development'
	@echo 'make install:        Install package for development'
	@echo 'make precommit: 		Configure pre-commit on your system'
	@echo 'make doc:			Build the static documentation site'
	@echo 'make serve: 			Serve the documentation site on localhost for browsing'
	@echo 'make test:           Run tests with pytest'

venv:
	python3 -m venv env

install:
	pip install --upgrade pip setuptools wheel
	pip install -r requirements.txt
	pip install -e .[dev]
	pre-commit install

precommit:
	pre-commit install
	pre-commit run --all-files

doc:
	cd docs && make html

serve:
	cd docs/_build/html && python3 -m http.server

format:
	black pyrolab

mypy:
	mypy -p pyrolab

# lint:
# 	flake8 .

test:
	coverage run -m pytest
	coverage report

jupytext:
	jupytext **/*.ipynb --to py

notebooks:
	jupytext docs/notebooks/**/*.py --to ipynb
	jupytext docs/notebooks/*.py --to ipynb

build:
	rm -rf dist
	python -m build

###############################################################################
# Devloper shouldn't use these targets, use release-[patch|minor|major] instead

patch:
	bumpversion patch

minor:
	bumpversion minor

major:
	bumpversion major

release:
	VERSION=$(shell python3 -c "import pyrolab; print(pyrolab.__version__)") && \
	echo Releasing version $$VERSION && \
	TAG_NAME=v$$VERSION && \
	git push && \
	git push origin $$TAG_NAME

###############################################################################

release-patch: patch release

release-minor: minor release

release-major: major release
