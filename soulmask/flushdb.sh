#!/bin/bash

docker compose exec python bash -c "rm -f soulmask/data/soulmask.db && python soulmask/scripts/setup_db.py && python soulmask/scripts/parse_talents.py && python soulmask/scripts/export_json.py" 2>&1