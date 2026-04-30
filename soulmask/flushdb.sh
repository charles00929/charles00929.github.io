#!/bin/bash
docker compose exec python bash -c "python soulmask/scripts/parse_talents.py"
docker compose exec python bash -c "python soulmask/scripts/assign_tags.py"
docker compose exec python bash -c "python soulmask/scripts/build_pools.py"


# docker compose exec python bash -c \
# "python soulmask/scripts/parse_talents.py && \
# python soulmask/scripts/assign_tags.py && \
# python soulmask/scripts/export_json.py" 2>&1