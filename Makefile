.PHONY: all
all: precommit

.PHONY: typecheck
typecheck:
	mypy ./sillyorm --strict

.PHONY: lint
lint:
	pylint ./sillyorm --disable=missing-module-docstring,unknown-option-value

.PHONY: precommit
precommit: test typecheck lint

.PHONY: test
test:
	coverage run --source sillyorm/ -m pytest -vv --tb=long --showlocals tests/
	coverage html --omit="tests/*"
	coverage report -m --omit="tests/*"
	cd docs && make doctest

.PHONY: postgrescontainer
postgrescontainer:
	docker run --rm -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres

.PHONY: psql
psql:
	PGPASSWORD="postgres" psql -U postgres -h 127.0.0.1 $@

.PHONY: format
format: 
	black sillyorm tests \
    --line-length 100 \
    --preview \
    --enable-unstable-feature string_processing
