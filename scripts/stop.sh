#!/bin/bash

echo "Stopping Inventory Management System..."
echo

# Check if Docker is running
if ! docker version >/dev/null 2>&1; then
    echo "ERROR: Docker is not running or not installed."
    exit 1
fi

echo "Stopping all services..."
docker-compose down

echo
echo "Checking if services are stopped..."
docker-compose ps

echo
echo "System stopped successfully!"
echo
echo "To start the system again, run: ./scripts/start.sh"
echo "To completely remove all data (including database), run: docker-compose down -v"
echo