#!/bin/bash

echo "Starting Inventory Management System..."
echo

# Check if Docker is running
if ! docker version >/dev/null 2>&1; then
    echo "ERROR: Docker is not running or not installed."
    echo "Please start Docker and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp ".env.template" ".env"
    echo
    echo "WARNING: Please edit .env file with your configuration before continuing."
    echo "Opening .env file for editing..."

    # Try to open with common editors
    if command -v nano >/dev/null 2>&1; then
        nano .env
    elif command -v vim >/dev/null 2>&1; then
        vim .env
    elif command -v vi >/dev/null 2>&1; then
        vi .env
    else
        echo "Please manually edit the .env file with your preferred editor."
        echo "After editing, run this script again."
        exit 1
    fi

    echo
    echo "Please save the .env file and restart this script."
    exit 1
fi

echo "Pulling latest images..."
docker-compose pull

echo "Building and starting services..."
docker-compose up -d --build

echo
echo "Waiting for services to start..."
sleep 10

echo
echo "Checking service status..."
docker-compose ps

echo
echo "Services started successfully!"
echo
echo "Access the application at: http://localhost:8501"
echo "Access database admin at: http://localhost:8080 (development only)"
echo
echo "To stop the system, run: ./scripts/stop.sh"
echo "To view logs, run: docker-compose logs -f"
echo