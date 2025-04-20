#!/usr/bin/with-contenv bashio
set -e
echo "SR-201 Service started"

## start ritar-bms main part
python3 -u /sr-201.py
