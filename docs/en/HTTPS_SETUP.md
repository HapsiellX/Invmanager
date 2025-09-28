# 🔒 HTTPS Setup Guide

Complete guide for setting up HTTPS-only access with SSL/TLS encryption for the Inventory Management System.

## 🎯 Overview

This system implements **HTTPS-only** access with:
- **nginx reverse proxy** with SSL termination
- **Self-signed SSL certificates** for development/internal use
- **Security headers** (HSTS, CSP, XSS protection)
- **HTTP to HTTPS redirect** (automatic)
- **WebSocket support** for Streamlit real-time features

## 🚀 Quick Setup

### 1. Start HTTPS System
```bash
# Start all services with HTTPS
docker-compose up -d

# Check status
docker-compose ps
```

### 2. Access Application
- **HTTPS**: https://localhost (recommended)
- **HTTP**: http://localhost (redirects to HTTPS)

### 3. Accept Certificate
- Browser will show certificate warning (expected for self-signed)
- Click "Advanced" → "Proceed to localhost" or similar
- Certificate is valid for development use

## 🛠️ Technical Implementation

### Architecture
```
Browser → nginx (Port 443/80) → Streamlit App (Port 8501)
```

### SSL/TLS Configuration
- **TLS Versions**: 1.2 and 1.3
- **Certificate**: 4096-bit RSA self-signed
- **Cipher Suites**: Modern, secure algorithms
- **HSTS**: 1-year max-age policy

## 📁 File Structure

```
nginx/
├── nginx.conf              # Main nginx configuration
└── ssl/                    # SSL certificates directory
    ├── fullchain.pem       # SSL certificate
    ├── private.key         # Private key
    └── csr.pem            # Certificate signing request

docker-compose.yml          # Updated with nginx service
.env                        # HTTPS configuration
```

## 🔧 Configuration Details

### nginx Configuration Highlights

```nginx
server {
    listen 443 ssl http2;
    server_name localhost;

    # SSL Configuration
    ssl_certificate /ssl/fullchain.pem;
    ssl_certificate_key /ssl/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options SAMEORIGIN always;
    add_header X-Content-Type-Options nosniff always;

    # Streamlit Proxy
    location / {
        proxy_pass http://app:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name localhost;
    return 301 https://$server_name$request_uri;
}
```

### Environment Variables

```bash
# .env configuration
HTTPS_PORT=443
HTTP_PORT=80
SSL_CERT_PATH=./nginx/ssl/fullchain.pem
SSL_KEY_PATH=./nginx/ssl/private.key
```

## 🔑 Certificate Management

### Automatic Certificate Generation
The system automatically generates self-signed certificates on first startup:

```bash
# Certificate generation (automatic)
openssl genrsa -out private.key 4096
openssl req -new -key private.key -out csr.pem
openssl x509 -req -days 365 -in csr.pem -signkey private.key -out fullchain.pem
```

### Certificate Details
- **Validity**: 365 days
- **Key Size**: 4096 bits RSA
- **Subject**: CN=localhost
- **Usage**: Development and internal deployment

### Production Certificates
For production use, replace self-signed certificates with:
- **Let's Encrypt** certificates (free, automated)
- **Commercial SSL** certificates
- **Internal CA** certificates

## 🛡️ Security Features

### Security Headers Implemented

| Header | Purpose | Value |
|--------|---------|-------|
| **HSTS** | Force HTTPS | `max-age=31536000; includeSubDomains` |
| **CSP** | Content Security | Streamlit-compatible policy |
| **X-Frame-Options** | Clickjacking protection | `SAMEORIGIN` |
| **X-Content-Type-Options** | MIME sniffing protection | `nosniff` |
| **X-XSS-Protection** | XSS protection | `1; mode=block` |
| **Referrer-Policy** | Privacy protection | `strict-origin-when-cross-origin` |

### HTTPS-Only Enforcement
- All HTTP traffic redirected to HTTPS
- HSTS header prevents downgrade attacks
- Secure cookie flags enabled
- Mixed content protection

## 📱 Browser Compatibility

### Supported Browsers
- **Chrome/Edge**: ✅ Full support
- **Firefox**: ✅ Full support
- **Safari**: ✅ Full support
- **Mobile browsers**: ✅ Full support

### Camera Access Requirements
- **HTTPS mandatory**: Camera API only works over HTTPS
- **Permissions**: Browser requests camera permission
- **Security**: WebRTC requires secure context

## 🔍 Troubleshooting

### Common Issues

#### 1. Certificate Warning
**Problem**: Browser shows "Not Secure" or certificate warning
**Solution**:
- Expected for self-signed certificates
- Click "Advanced" → "Proceed to localhost"
- For production, use valid SSL certificate

#### 2. nginx Startup Error
**Problem**: nginx container fails to start
**Solution**:
```bash
# Check nginx configuration
docker-compose logs nginx

# Restart with clean state
docker-compose down
docker-compose up -d
```

#### 3. Camera Not Working
**Problem**: Camera scanner not accessible
**Solution**:
- Ensure HTTPS access (https://localhost)
- Check browser permissions
- Verify WebRTC compatibility

#### 4. Mixed Content Errors
**Problem**: Resources not loading over HTTPS
**Solution**:
- All resources loaded via HTTPS
- Check browser console for details
- Verify nginx proxy headers

### Diagnostic Commands

```bash
# Check SSL certificate
openssl x509 -in nginx/ssl/fullchain.pem -text -noout

# Test HTTPS connection
curl -k https://localhost

# Check nginx configuration
docker exec inventory_nginx nginx -t

# View nginx logs
docker-compose logs nginx
```

## 🚀 Production Deployment

### Production Checklist
- [ ] Replace self-signed certificates with valid SSL
- [ ] Update server_name in nginx.conf
- [ ] Configure firewall rules (443, 80)
- [ ] Set up certificate renewal (if using Let's Encrypt)
- [ ] Update DNS records
- [ ] Test all functionality over HTTPS

### Let's Encrypt Integration
For automatic SSL certificates:

```bash
# Example with certbot (not included in current setup)
certbot --nginx -d yourdomain.com
```

### Performance Optimization
- HTTP/2 enabled for better performance
- Gzip compression for reduced bandwidth
- SSL session caching for faster handshakes
- Modern cipher suites for security and speed

## 📋 Security Checklist

### HTTPS Implementation
- [x] SSL/TLS 1.2+ only
- [x] Strong cipher suites
- [x] HSTS header implemented
- [x] HTTP to HTTPS redirect
- [x] Secure cookie configuration

### Application Security
- [x] Content Security Policy
- [x] XSS protection headers
- [x] Clickjacking protection
- [x] MIME type sniffing protection
- [x] Referrer policy configuration

### Infrastructure Security
- [x] nginx reverse proxy
- [x] Container isolation
- [x] Non-root application user
- [x] Minimal attack surface
- [x] Security header validation

## 📈 Monitoring

### Health Checks
- nginx health check: `curl -f http://localhost/_nginx_health`
- Application health: `curl -k https://localhost/_stcore/health`
- SSL certificate expiry monitoring

### Log Monitoring
```bash
# nginx access logs
docker-compose logs nginx | grep access

# SSL handshake logs
docker-compose logs nginx | grep ssl

# Application logs
docker-compose logs app
```

---

**Version**: 1.0.0
**Last Updated**: 2025-09-28
**Status**: Production Ready

This HTTPS setup provides enterprise-grade security for the Inventory Management System while maintaining ease of deployment and management.