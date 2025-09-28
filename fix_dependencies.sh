#!/bin/bash

# Fix Dependencies Script for Inventory Management System
# This script ensures all dependencies are correctly installed

echo "🔧 Starting dependency fix for Inventory Management System..."

# Stop existing containers
echo "📦 Stopping existing containers..."
docker-compose down

# Remove old containers and images to force rebuild
echo "🧹 Cleaning up old containers and images..."
docker system prune -f
docker-compose rm -f

# Build with no cache to ensure fresh installation
echo "🏗️ Building containers with fresh dependencies..."
docker-compose build --no-cache

# Start the updated containers
echo "🚀 Starting updated containers..."
docker-compose up -d

# Wait for containers to be ready
echo "⏳ Waiting for containers to be ready..."
sleep 30

# Check if containers are running
echo "✅ Checking container status..."
docker-compose ps

# Check if dependencies are installed in the container
echo "🔍 Checking dependencies in container..."
docker-compose exec app pip list | grep -E "(qrcode|barcode|PIL|Pillow|psutil|reportlab)"

echo "✅ Dependency fix complete!"
echo ""
echo "📋 Next steps:"
echo "1. Open the application in your browser"
echo "2. Login as admin"
echo "3. Go to '🔧 Debug Tool' to verify all dependencies"
echo "4. Test QR & Barcodes functionality"
echo "5. Test Notifications functionality"
echo ""
echo "🌐 Application should be available at: http://localhost:8501"