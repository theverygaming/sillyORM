#!/usr/bin/env bash
set -e
coverage run --source sillyORM/ -m pytest -vv --tb=long tests/
coverage html --omit="tests/*"
coverage report -m --omit="tests/*"
