.PHONY: all
all: precommit

.PHONY: typecheck
typecheck:
	mypy ./sillyorm --strict

.PHONY: lint
lint:
	pylint ./sillyorm --disable=missing-module-docstring,missing-class-docstring,missing-function-docstring

.PHONY: precommit
precommit: test typecheck lint

.PHONY: test
test:
	coverage run --source sillyorm/ -m pytest -vv --tb=long tests/
	coverage html --omit="tests/*"
	coverage report -m --omit="tests/*"

.PHONY: postgrescontainer
postgrescontainer:
	docker run --rm -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres

.PHONY: psql
psql:
	PGPASSWORD="postgres" psql -U postgres -h 127.0.0.1 $@

.PHONY: docs
docs:
	mkdir -p docs && cd docs
	sphinx-apidoc --help -F -o . ../sillyorm
	make html

	# conf.py:
	#import os
	#import sys
	#sys.path.insert(0, os.path.abspath('..'))  # so we can import from the directory below

.PHONY: format
format: 
	black sillyorm \
    --line-length 100 \
    --preview \
    --enable-unstable-feature string_processing
