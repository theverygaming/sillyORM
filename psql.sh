#!/usr/bin/env bash
PGPASSWORD="postgres" psql -U postgres -h 127.0.0.1 $@
