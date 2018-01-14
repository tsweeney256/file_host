#!/bin/bash

thisdir="$(dirname $(readlink -f $0))"
dbname="${1:-file_host}"
superuser="${2:-postgres}"
port="${3:-5432}"
host="${4:-/var/run/postgresql}"

function run_psql_file {
    psql -U "$superuser" -p "$port" -h "$host" -f "$1" "$dbname"
}

run_psql_file "${thisdir}/users.sql"
run_psql_file "${thisdir}/tables.sql"
run_psql_file "${thisdir}/functions.sql"
