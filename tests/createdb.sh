#!/bin/bash

data="$(dirname $(readlink -f $0))/data"

if [ -d "$data" ]; then
    pg_ctl stop -D $data -o "-p 5001" -o "-k $data"
    rm -r "$data"
fi

initdb -U $USER "$data"
pg_ctl start -D "$data" -l postgres.log -o "-p 5001" \
       -o "-k $data"
createdb -p 5001 -h "$data" file_host_unit_test
../database/install_db.sh file_host_unit_test $USER 5001 "$data"
psql -p 5001 -h "$data" -U $USER -c "create role file_host_unit_test "\
"with login password 'file_host_unit_test' in group file_host_group;" \
     -d file_host_unit_test
