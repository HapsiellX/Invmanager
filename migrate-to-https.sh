#!/bin/bash

# Migration script from HTTP to HTTPS
# This script safely migrates the existing system to HTTPS

set -e

echo "🔄 Migrating Inventory Management System to HTTPS..."
echo "================================================="

# Backup current configuration
echo "💾 Creating backup of current configuration..."
mkdir -p backups/$(date +%Y%m%d_%H%M%S)
cp docker-compose.yml backups/$(date +%Y%m%d_%H%M%S)/ 2>/dev/null || true
cp .env backups/$(date +%Y%m%d_%H%M%S)/ 2>/dev/null || true

# Stop current system
echo "🛑 Stopping current HTTP system..."
docker-compose down

# Generate SSL certificates
echo "🔑 Setting up SSL certificates..."
if [ ! -f "ssl/certificate.crt" ]; then
    docker-compose --profile ssl-setup run --rm ssl-generator
    echo "✅ SSL certificates generated"
else
    echo "✅ SSL certificates already exist"
fi

# Start HTTPS system
echo "🚀 Starting HTTPS-enabled system..."
docker-compose up -d

# Wait for system to start
echo "⏳ Waiting for system to initialize..."
sleep 15

# Verify HTTPS is working
echo "🔍 Verifying HTTPS setup..."
if curl -k -s https://localhost >/dev/null 2>&1; then
    echo "✅ HTTPS migration completed successfully!"
    echo ""
    echo "🌐 Your system is now accessible at:"
    echo "   HTTPS: https://localhost"
    echo "   HTTP requests will be redirected to HTTPS"
    echo ""
    echo "⚠️  Browser Warning:"
    echo "   You may see a security warning due to self-signed certificates."
    echo "   This is normal for development environments."
    echo "   Click 'Advanced' and 'Proceed to localhost' to continue."
else
    echo "❌ HTTPS verification failed"
    echo "🔧 Troubleshooting steps:"
    echo "   1. Check container logs: docker-compose logs"
    echo "   2. Verify SSL certificates: ls -la ssl/"
    echo "   3. Check nginx configuration: docker-compose logs nginx"
    exit 1
fi

echo ""
echo "🛡️  Security improvements enabled:"
echo "   • All traffic is now encrypted with TLS"
echo "   • HTTP requests are automatically redirected to HTTPS"
echo "   • Security headers are applied to all responses"
echo "   • HSTS (HTTP Strict Transport Security) is enabled"
echo ""
echo "📝 Next steps:"
echo "   1. Update any bookmarks to use https://localhost"
echo "   2. For production, replace self-signed certificates with CA-signed ones"
echo "   3. Update any API clients to use HTTPS endpoints"
echo ""