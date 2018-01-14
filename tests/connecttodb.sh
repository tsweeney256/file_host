#!/bin/bash
thisdir="$(dirname $(realpath $0))"
psql -p 5001 -h "$thisdir/data" file_host_unit_test
