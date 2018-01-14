#!/bin/bash

data="$(dirname $(readlink -f $0))/data"
pg_ctl start -D "$data" -l postgres.log -o "-p 5001" \
       -o "-k $data"
