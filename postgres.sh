#!/usr/bin/env bash
docker run --rm -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres
