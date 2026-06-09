#! /usr/bin/env bash

set -e
set -x

# Let the DB start
python cli.py server pre-start

# Run migrations
alembic upgrade head

# Create initial data in DB
python cli.py data init-db
