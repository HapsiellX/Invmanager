# HTTPS-Only Setup für Inventory Management System

## 🛡️ Übersicht

Das Inventory Management System wurde erfolgreich auf HTTPS-only umgestellt. Alle HTTP-Anfragen werden automatisch auf HTTPS umgeleitet.

## 🔐 Sicherheitsfeatures

### SSL/TLS Verschlüsselung
- **TLS 1.2 und TLS 1.3** Unterstützung
- **4096-Bit RSA** Schlüssel
- **Self-signed Certificate** für Entwicklung/Intranet
- **Perfect Forward Secrecy** aktiviert

### Sicherheits-Header
- **HSTS** (HTTP Strict Transport Security) - 1 Jahr
- **X-Frame-Options: SAMEORIGIN** - Schutz vor Clickjacking
- **X-Content-Type-Options: nosniff** - MIME-Type Schutz
- **X-XSS-Protection** - Cross-Site Scripting Schutz
- **Content Security Policy** - Umfassende CSP für Streamlit
- **Referrer Policy** - Datenschutz-optimiert

### Nginx Proxy Features
- **HTTP/2** Support
- **Gzip Kompression** für bessere Performance
- **WebSocket** Support für Streamlit
- **Health Check** Endpoint
- **Static File Caching**

## 🌐 Zugriff

### URLs
- **HTTPS (sicher):** `https://localhost`
- **HTTP (umgeleitet):** `http://localhost` → `https://localhost`

### Browser-Warnung
Da self-signed Zertifikate verwendet werden, zeigt der Browser eine Sicherheitswarnung an:
1. Klicken Sie auf **"Erweitert"** oder **"Advanced"**
2. Wählen Sie **"Weiter zu localhost"** oder **"Proceed to localhost"**
3. Das System ist dann über HTTPS erreichbar

## 🚀 Deployment-Befehle

### Normale Nutzung
```bash
# System starten
docker-compose up -d

# System stoppen
docker-compose down

# Logs anzeigen
docker-compose logs -f
```

### HTTPS Migration (einmalig)
```bash
# Migration von HTTP zu HTTPS
./migrate-to-https.sh

# Oder manuell:
docker-compose down
docker-compose up -d
```

### SSL-Zertifikate neu generieren
```bash
# Zertifikate löschen
rm -rf ssl/*

# Neue Zertifikate generieren
openssl genrsa -out ssl/private.key 4096
openssl req -new -key ssl/private.key -out ssl/cert.csr -subj '/C=DE/ST=Germany/L=Berlin/O=Inventory Management System/OU=IT Department/CN=localhost/emailAddress=admin@company.com'
openssl x509 -req -days 365 -in ssl/cert.csr -signkey ssl/private.key -out ssl/certificate.crt
cp ssl/certificate.crt ssl/fullchain.pem

# Container neu starten
docker-compose restart nginx
```

## 📁 Dateistruktur

```
├── nginx/
│   └── nginx.conf          # Nginx HTTPS Konfiguration
├── ssl/
│   ├── private.key         # Privater Schlüssel (4096-bit)
│   ├── certificate.crt     # SSL Zertifikat
│   ├── fullchain.pem      # Vollständige Zertifikatskette
│   └── cert.csr           # Certificate Signing Request
├── docker-compose.yml      # HTTPS-erweiterte Compose Datei
├── .env                    # HTTPS Umgebungsvariablen
├── start-https.sh         # HTTPS Startup Script
└── migrate-to-https.sh    # Migration Script
```

## ⚙️ Konfiguration

### Umgebungsvariablen (.env)
```bash
# HTTPS Configuration
ENABLE_HTTPS=true
HTTP_PORT=80
HTTPS_PORT=443
SSL_CERT_PATH=./ssl/certificate.crt
SSL_KEY_PATH=./ssl/private.key
FORCE_HTTPS=true
```

### Container Ports
- **HTTP:** Port 80 (Redirect zu HTTPS)
- **HTTPS:** Port 443 (Hauptzugang)
- **Database:** Port 5432 (intern)
- **Streamlit:** Port 8501 (intern, nur über nginx)

## 🔧 Troubleshooting

### Container starten nicht
```bash
# Konfiguration prüfen
docker-compose config

# Logs anzeigen
docker-compose logs nginx
docker-compose logs app
```

### SSL-Probleme
```bash
# Zertifikat prüfen
openssl x509 -in ssl/certificate.crt -text -noout

# Nginx Konfiguration testen
docker exec inventory_nginx nginx -t
```

### Connection Reset
```bash
# Firewall/Port Freigabe prüfen
netstat -tulpn | grep :443
netstat -tulpn | grep :80
```

### Performance Issues
```bash
# Container Ressourcen prüfen
docker stats

# Nginx Access Logs
docker logs inventory_nginx --tail 50
```

## 🎯 Produktionshinweise

### Für Produktionsumgebung
1. **CA-signierte Zertifikate** verwenden (Let's Encrypt, etc.)
2. **Domain-Namen** statt localhost konfigurieren
3. **Firewall-Regeln** für Ports 80/443
4. **Backup-Strategie** für SSL-Zertifikate
5. **Monitoring** für SSL-Ablaufdatum

### Zertifikat-Erneuerung
```bash
# Automatische Erneuerung mit Let's Encrypt (Beispiel)
# 0 2 * * * /usr/bin/certbot renew --quiet && docker-compose restart nginx
```

## 📊 Performance-Optimierungen

### Bereits aktiviert
- **HTTP/2** für bessere Multiplexing
- **Gzip Kompression** für Text-Inhalte
- **Static File Caching** mit 1-Jahr Expiry
- **Keep-Alive Connections**
- **Worker Process Tuning**

### Weitere Optimierungen
- **Rate Limiting** für DDoS-Schutz
- **IP Whitelisting** für Admin-Bereiche
- **WAF (Web Application Firewall)**
- **CDN Integration** für statische Inhalte

## 🛟 Support

### Häufige Probleme
1. **Browser-Warnung:** Normal bei self-signed Zertifikaten
2. **HTTPS nicht erreichbar:** Ports 443 prüfen
3. **Redirect-Loop:** nginx Konfiguration prüfen
4. **Langsame Verbindung:** HTTP/2 Browser-Support prüfen

### Hilfreiche Befehle
```bash
# HTTPS Test
curl -k -v https://localhost

# HTTP Redirect Test
curl -I http://localhost

# SSL Handshake Test
openssl s_client -connect localhost:443

# Container Health Check
docker exec inventory_nginx wget --spider --quiet http://localhost/health
```

---

✅ **Das System läuft jetzt vollständig HTTPS-only mit allen modernen Sicherheitsstandards!**