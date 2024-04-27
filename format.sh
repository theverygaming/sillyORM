#!/usr/bin/env bash
set -e
black sillyORM \
    --line-length 100 \
    --preview \
    --enable-unstable-feature string_processing
