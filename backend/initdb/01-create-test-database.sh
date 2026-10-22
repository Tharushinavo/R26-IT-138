#!/bin/bash
# Creates the isolated TEST database alongside the dev one, on first initialisation of the
# Postgres data volume.
#
# WHY THIS EXISTS. `studentapp_test` used to be created by hand, once, with a comment in
# compose.yaml recording the command. That worked until the data volume was removed (2026-10-10,
# reclaiming disk), at which point the database silently ceased to exist and the whole suite would
# have failed to connect -- with no instruction anywhere that runs itself. A test database that
# only exists because someone remembered to type a command is a step that will eventually be
# missed; this makes a fresh volume reproduce the full expected state on its own.
#
# WHY A SEPARATE DATABASE AND NOT A SEPARATE SERVER. Six migration-reversibility tests downgrade
# the schema and re-upgrade it, dropping and recreating every table. Pointing the suite at the dev
# database destroys real data, which is exactly what the `api-test` service and its own
# `DATABASE_URL` override exist to prevent. Same server, same credentials, different database.
#
# Postgres runs every *.sh and *.sql in /docker-entrypoint-initdb.d ONLY when the data directory is
# empty, so this is a no-op on every later start and cannot clobber an existing database.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE ${POSTGRES_DB}_test OWNER ${POSTGRES_USER};
EOSQL

echo "initdb: created ${POSTGRES_DB}_test owned by ${POSTGRES_USER}"
