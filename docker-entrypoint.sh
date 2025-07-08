#!/bin/bash

# Start cron service
service cron start

# Start a simple HTTP server for health checks
python -m http.server 8000 &

# Keep container running
exec "$@" 