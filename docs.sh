#!/usr/bin/env bash
set -e
mkdir -p docs && cd docs
sphinx-apidoc --help -F -o . ../sillyORM
make html

# conf.py:
#import os
#import sys
#sys.path.insert(0, os.path.abspath('..'))  # so we can import from the directory below
