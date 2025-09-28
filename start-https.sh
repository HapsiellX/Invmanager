#!/bin/bash

# HTTPS Setup and Start Script for Inventory Management System
# This script ensures SSL certificates are generated and starts the system with HTTPS support

set -e

echo "🔐 Starting Inventory Management System with HTTPS support..."
echo "================================================="

# Check if Docker and Docker Compose are available
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed or not in PATH"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed or not in PATH"
    exit 1
fi

# Create SSL directory if it doesn't exist
mkdir -p ssl nginx

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Generate SSL certificates if they don't exist
if [ ! -f "ssl/certificate.crt" ]; then
    echo "🔑 Generating SSL certificates..."
    docker-compose --profile ssl-setup run --rm ssl-generator

    if [ ! -f "ssl/certificate.crt" ]; then
        echo "❌ Error: Failed to generate SSL certificates"
        exit 1
    fi

    echo "✅ SSL certificates generated successfully"
else
    echo "✅ SSL certificates already exist"
fi

# Verify SSL certificates
echo "🔍 Verifying SSL certificates..."
if ! openssl x509 -in ssl/certificate.crt -text -noout >/dev/null 2>&1; then
    echo "⚠️  Warning: SSL certificate appears to be invalid, regenerating..."
    rm -f ssl/*.crt ssl/*.key ssl/*.pem ssl/*.csr
    docker-compose --profile ssl-setup run --rm ssl-generator
fi

# Start the services
echo "🚀 Starting HTTPS-enabled services..."
docker-compose up -d db app nginx

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🏥 Checking service health..."

# Check if containers are running
if ! docker ps | grep -q "inventory_db.*Up"; then
    echo "❌ Database container is not running"
    docker-compose logs db
    exit 1
fi

if ! docker ps | grep -q "inventory_app.*Up"; then
    echo "❌ Application container is not running"
    docker-compose logs app
    exit 1
fi

if ! docker ps | grep -q "inventory_nginx.*Up"; then
    echo "❌ Nginx container is not running"
    docker-compose logs nginx
    exit 1
fi

# Test HTTPS connectivity
echo "🌐 Testing HTTPS connectivity..."
sleep 5

if curl -k -s https://localhost >/dev/null 2>&1; then
    echo "✅ HTTPS is working correctly"
else
    echo "⚠️  HTTPS test failed, but services are running"
    echo "   Check the logs for more information:"
    echo "   docker-compose logs nginx"
fi

# Test HTTP redirect
if curl -s -I http://localhost | grep -q "301\|302"; then
    echo "✅ HTTP to HTTPS redirect is working"
else
    echo "⚠️  HTTP to HTTPS redirect may not be working correctly"
fi

echo ""
echo "🎉 Inventory Management System is now running with HTTPS!"
echo "================================================="
echo "🌐 Access URLs:"
echo "   HTTPS (secure):  https://localhost"
echo "   HTTP (redirects): http://localhost"
echo ""
echo "📋 Default login credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "🔧 Management commands:"
echo "   View logs:     docker-compose logs -f"
echo "   Stop system:   docker-compose down"
echo "   Restart:       docker-compose restart"
echo ""
echo "⚠️  Certificate Notice:"
echo "   The system uses self-signed certificates for development."
echo "   Your browser will show a security warning - this is normal."
echo "   Click 'Advanced' and 'Proceed to localhost' to continue."
echo ""
echo "🛡️  Security Features Enabled:"
echo "   • HTTPS-only access"
echo "   • HTTP to HTTPS redirect"
echo "   • HSTS (HTTP Strict Transport Security)"
echo "   • Security headers (XSS, CSRF, etc.)"
echo "   • Content Security Policy"
echo ""