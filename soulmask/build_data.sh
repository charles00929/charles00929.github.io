#!/bin/bash
docker compose exec python bash -c "python soulmask/scripts/parse_talents.py"
docker compose exec python bash -c "python soulmask/scripts/assign_tags.py"
docker compose exec python bash -c "python soulmask/scripts/build_pools.py"
