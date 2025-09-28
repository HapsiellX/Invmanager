# 🔄 Update Instructions

Instructions for updating the Inventory Management System to newer versions.

## 🚀 Quick Update

### Standard Update Process
```bash
# 1. Stop the system
docker-compose down

# 2. Backup current data (recommended)
mkdir -p backups/$(date +%Y%m%d_%H%M%S)
docker-compose exec db pg_dump -U inventory_user inventory_db > backups/$(date +%Y%m%d_%H%M%S)/database_backup.sql

# 3. Pull latest changes
git pull origin main

# 4. Rebuild containers
docker-compose build --no-cache

# 5. Start updated system
docker-compose up -d
```

## 📋 Version-Specific Updates

### From 0.4.0 to 0.4.1 (Camera Scanner)
```bash
# New dependencies for camera scanning
# Containers will automatically rebuild with new requirements

# Verify camera scanner works after update
# Navigate to QR & Barcodes → Code Scanner → Camera Scanner
```

### From 0.3.x to 0.4.0 (HTTPS Implementation)
```bash
# HTTPS was added - new nginx service
# SSL certificates will be auto-generated

# Update .env if needed
cp .env.template .env
# Edit .env with your settings

# Restart with new configuration
docker-compose down
docker-compose up -d
```

## 🗃️ Database Migrations

### Automatic Migrations
```bash
# Most updates include automatic database migrations
docker-compose exec app python -m alembic upgrade head
```

### Manual Migration Check
```bash
# Check current database version
docker-compose exec app python -m alembic current

# View pending migrations
docker-compose exec app python -m alembic heads

# Apply specific migration
docker-compose exec app python -m alembic upgrade <revision_id>
```

## 💾 Backup Procedures

### Before Any Update
```bash
# Create backup directory
mkdir -p backups/$(date +%Y%m%d_%H%M%S)

# Backup database
docker-compose exec db pg_dump -U inventory_user inventory_db > backups/$(date +%Y%m%d_%H%M%S)/database_backup.sql

# Backup configuration
cp .env backups/$(date +%Y%m%d_%H%M%S)/
cp docker-compose.yml backups/$(date +%Y%m%d_%H%M%S)/

# Backup SSL certificates (if custom)
cp -r nginx/ssl backups/$(date +%Y%m%d_%H%M%S)/
```

### Restore from Backup
```bash
# Stop system
docker-compose down -v

# Restore database
docker-compose up -d db
sleep 10
docker-compose exec db psql -U inventory_user -d inventory_db < backups/YYYYMMDD_HHMMSS/database_backup.sql

# Restore configuration
cp backups/YYYYMMDD_HHMMSS/.env .
cp backups/YYYYMMDD_HHMMSS/docker-compose.yml .

# Start system
docker-compose up -d
```

## 🔧 Configuration Updates

### Environment Variables
```bash
# Check for new environment variables
diff .env .env.template

# Add any missing variables to .env
# Common new variables by version:
# 0.4.0: HTTPS_PORT, SSL_CERT_PATH, SSL_KEY_PATH
# 0.4.1: (no new env vars)
```

### Docker Compose Changes
```bash
# Check for service changes
diff docker-compose.yml docker-compose.yml.backup

# Common changes:
# 0.4.0: Added nginx service
# 0.4.1: Updated app service with camera dependencies
```

## 🚨 Rollback Procedures

### Quick Rollback
```bash
# If update fails, rollback to previous version
git log --oneline -5
git checkout <previous_commit_hash>

# Restore from backup
docker-compose down -v
# Follow backup restoration steps above
```

### Version-Specific Rollbacks

#### From 0.4.1 to 0.4.0
```bash
git checkout <0.4.0_commit_hash>
docker-compose down
docker-compose build --no-cache
docker-compose up -d
# Camera scanner features will be unavailable
```

#### From 0.4.0 to 0.3.x
```bash
git checkout <0.3.x_commit_hash>
# Remove nginx service from docker-compose.yml
# Update .env to remove HTTPS variables
docker-compose down
docker-compose build --no-cache
docker-compose up -d
# System will run on HTTP only
```

## 📊 Update Verification

### Post-Update Checks
```bash
# 1. Check all services are running
docker-compose ps

# 2. Verify application access
curl -k https://localhost
# or
curl http://localhost

# 3. Test login functionality
# Login with admin/admin123

# 4. Test key features
# - Hardware inventory
# - QR/Barcode generation
# - Camera scanner (0.4.1+)

# 5. Check logs for errors
docker-compose logs --tail=50
```

### Version Verification
```bash
# Check application version
# Look for version info in:
# - Dashboard footer
# - About section
# - README.md
# - docs/CHANGELOG.md
```

## 🔍 Troubleshooting Updates

### Common Update Issues

#### Docker Build Failures
```bash
# Clear Docker cache
docker system prune -a

# Rebuild from scratch
docker-compose build --no-cache --pull
```

#### Permission Issues
```bash
# Fix file permissions (Linux/WSL)
sudo chown -R $USER:$USER .
chmod +x scripts/*.sh

# Windows: Run as administrator
```

#### Database Migration Errors
```bash
# Check migration status
docker-compose exec app python -m alembic current

# Force migration
docker-compose exec app python -m alembic stamp head
docker-compose exec app python -m alembic upgrade head
```

#### SSL Certificate Issues (0.4.0+)
```bash
# Regenerate SSL certificates
rm -rf nginx/ssl/*
docker-compose down
docker-compose up -d
```

## 📋 Update Checklist

### Pre-Update
- [ ] Create backup of database
- [ ] Backup configuration files
- [ ] Note current version
- [ ] Check disk space
- [ ] Schedule maintenance window

### During Update
- [ ] Stop services gracefully
- [ ] Pull latest code
- [ ] Review configuration changes
- [ ] Rebuild containers
- [ ] Start services
- [ ] Verify functionality

### Post-Update
- [ ] Test all major features
- [ ] Check system logs
- [ ] Verify database integrity
- [ ] Test user access
- [ ] Document any issues
- [ ] Notify users of completion

## 🎯 Best Practices

### Regular Updates
- Update monthly or as needed
- Always backup before updating
- Test updates in development first
- Have rollback plan ready

### Monitoring
- Monitor logs after updates
- Check system resources
- Verify all features work
- Get user feedback

### Documentation
- Keep changelog updated
- Document custom changes
- Note configuration modifications
- Track rollback procedures

---

**Version**: 1.0.0
**Last Updated**: 2025-09-28
**Next Review**: Monthly

Always test updates in a development environment before applying to production systems.