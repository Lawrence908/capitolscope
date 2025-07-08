#!/bin/bash

# Test script for CapitolScope Docker setup

echo "Building Docker image..."
docker build -t capitolscope-ingestion .

echo "Running container..."
docker run -d --name capitolscope-test \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/var/log \
  capitolscope-ingestion

echo "Container started. Check logs with:"
echo "docker logs capitolscope-test"

echo "To stop the container:"
echo "docker stop capitolscope-test && docker rm capitolscope-test" 