#!/bin/bash

data="$(dirname $(readlink -f $0))/data"
pg_ctl stop -D $data -o "-p 5001" -o "-k $data"
