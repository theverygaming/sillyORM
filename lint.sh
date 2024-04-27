#!/usr/bin/env bash
set -e
mypy ./sillyORM --strict
pylint ./sillyORM --disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
