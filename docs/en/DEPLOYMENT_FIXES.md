# 🛠️ Deployment Fixes and Solutions

Common deployment issues and their solutions for the Inventory Management System.

## 🚨 Common Issues

### 1. Docker Container Issues

#### Problem: Container fails to start
```bash
# Symptoms
docker-compose up -d
# Error: Container exits immediately

# Solution
docker-compose logs app
docker-compose down
docker-compose build --no-cache app
docker-compose up -d
```

#### Problem: Database connection failed
```bash
# Symptoms
Database connection error in logs

# Solution
# Check if PostgreSQL is running
docker-compose ps
# Reset database if needed
docker-compose down -v
docker-compose up -d
```

### 2. HTTPS/SSL Issues

#### Problem: SSL certificate errors
```bash
# Symptoms
nginx: [emerg] cannot load certificate

# Solution
# Regenerate certificates
cd nginx/ssl
rm -f *.pem *.key *.csr
# Restart to trigger auto-generation
docker-compose down
docker-compose up -d
```

#### Problem: Mixed content warnings
```bash
# Symptoms
Browser shows mixed content warnings

# Solution
# Ensure all resources use HTTPS
# Check nginx configuration
docker exec inventory_nginx nginx -t
```

### 3. Camera Scanner Issues

#### Problem: Camera not working
```bash
# Symptoms
Camera scanner shows error or permission denied

# Solution
1. Ensure HTTPS access (https://localhost)
2. Grant camera permissions in browser
3. Check browser compatibility
4. Verify system dependencies:
   docker exec inventory_app python3 -c "import cv2, pyzbar, streamlit_webrtc; print('OK')"
```

#### Problem: Scanner dependencies missing
```bash
# Symptoms
ImportError: No module named 'cv2' or similar

# Solution
# Rebuild container with dependencies
docker-compose build --no-cache app
docker-compose up -d
```

## 🔧 Environment Issues

### Port Conflicts
```bash
# Problem: Port already in use
# Error: bind: address already in use

# Solution
# Check what's using the port
netstat -tulpn | grep :443
# Or change ports in docker-compose.yml
```

### Permission Issues
```bash
# Problem: Permission denied errors

# Solution (Linux/WSL)
sudo chown -R $USER:$USER .
chmod +x scripts/*.sh

# Solution (Windows)
# Run as administrator or check Docker Desktop permissions
```

## 🔄 Reset Procedures

### Complete System Reset
```bash
# Stop everything
docker-compose down -v

# Remove all containers and volumes
docker system prune -a --volumes

# Rebuild and restart
docker-compose build --no-cache
docker-compose up -d
```

### Database Reset Only
```bash
# Stop and remove only database volume
docker-compose down
docker volume rm inventorymanager_postgres_data
docker-compose up -d
```

### SSL Certificate Reset
```bash
# Remove old certificates
rm -rf nginx/ssl/*

# Restart to regenerate
docker-compose down
docker-compose up -d
```

## 📋 Health Checks

### System Health Check
```bash
# Check all services
docker-compose ps

# Check logs
docker-compose logs --tail=50

# Test connectivity
curl -k https://localhost
```

### Application Health
```bash
# Test Streamlit health endpoint
curl -k https://localhost/_stcore/health

# Test database connection
docker exec inventory_app python3 -c "
from core.database import get_db
db = next(get_db())
result = db.execute('SELECT 1')
print('Database OK')
"
```

## 🚀 Performance Optimization

### Memory Issues
```bash
# If containers are using too much memory
# Limit memory in docker-compose.yml
services:
  app:
    mem_limit: 1g
  db:
    mem_limit: 512m
```

### Slow Performance
```bash
# Clear Docker cache
docker system prune

# Optimize PostgreSQL
# Increase shared_buffers in postgres configuration
```

## 🐛 Debugging

### Enable Debug Mode
```bash
# Add to .env file
DEBUG=true
STREAMLIT_DEBUG=true

# Restart
docker-compose down
docker-compose up -d
```

### Verbose Logging
```bash
# View detailed logs
docker-compose logs -f app

# nginx logs
docker-compose logs -f nginx

# Database logs
docker-compose logs -f db
```

## 📱 Browser-Specific Issues

### Chrome/Edge
- Camera permissions: Settings → Privacy → Camera
- HTTPS warnings: Click "Advanced" → "Proceed"

### Firefox
- Camera permissions: Address bar camera icon
- HTTPS warnings: "Add Exception"

### Safari
- Limited WebRTC support
- May need to enable camera permissions manually

## 🔒 Security Issues

### Certificate Not Trusted
```bash
# For development, this is expected with self-signed certificates
# For production, use valid SSL certificates

# Temporary: Add certificate to browser trust store
# Permanent: Get valid SSL certificate (Let's Encrypt, etc.)
```

### CORS Issues
```bash
# If accessing from different domain/port
# Update nginx configuration to allow origins
```

## 📊 Monitoring and Logs

### Log Locations
```bash
# Application logs
docker-compose logs app

# nginx logs
docker-compose logs nginx

# Database logs
docker-compose logs db

# System logs (host)
journalctl -u docker
```

### Performance Monitoring
```bash
# Container resource usage
docker stats

# Disk usage
docker system df

# Network connectivity
docker network ls
docker network inspect inventorymanager_inventory_network
```

## 🚨 Emergency Procedures

### Service Down Emergency
```bash
# Quick restart
docker-compose restart

# If that fails
docker-compose down
docker-compose up -d

# Last resort - complete rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Data Recovery
```bash
# If database is corrupted
# Restore from backup (if available)
# Or reset database and re-import data

# Check backup files
ls -la backups/
```

## 🔧 Maintenance Tasks

### Regular Maintenance
```bash
# Weekly: Clean up Docker
docker system prune

# Monthly: Update system
docker-compose pull
docker-compose build --no-cache
docker-compose up -d

# Check for updates
git pull origin main
```

### Security Updates
```bash
# Update base images
docker-compose build --no-cache --pull
docker-compose up -d

# Review security logs
docker-compose logs | grep -i error
```

---

**Version**: 1.0.0
**Last Updated**: 2025-09-28
**Support**: For additional help, check the logs and documentation.