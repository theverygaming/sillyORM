#!/usr/bin/env bash
set -e
mypy ./sillyORM --strict
pylint ./sillyORM
