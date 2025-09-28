# 📦 Inventory Management System

Ein umfassendes, professionelles Inventarverwaltungssystem für Hardware, Kabel und Standorte mit erweiterten Funktionen für Analytics, QR-Code-Generation und Benachrichtigungen.

## 🚀 Version 0.4.0 - HTTPS-Only Security Release

### ✨ Features

#### 🔧 **Core Funktionalität**
- **Hardware Inventar**: Vollständige Verwaltung mit technischen Details, Standorten und Garantie-Tracking
- **Kabel Inventar**: Bestandsmanagement mit Mindest-/Höchstbeständen und automatischen Alerts
- **Standort Management**: Hierarchische Struktur mit Adress- und Kontaktinformationen
- **Benutzer Management**: Rollenbasierte Zugriffskontrolle mit Passwort-Änderung (Admin, Netzwerker, Auszubildende)

#### 📊 **Analytics & Reporting**
- **Dashboard**: Übersicht über Bestände, Werte und kritische Alerts
- **Advanced Analytics**: Trend-Analysen, Wert-Entwicklung und Nutzungsstatistiken
- **Benachrichtigungen**: Intelligente Alerts für niedrige Bestände, ablaufende Garantien und kritische Aktionen
- **Audit Trail**: Vollständige Nachverfolgung aller Änderungen und Benutzeraktivitäten

#### 🎯 **Advanced Features**
- **QR & Barcode Generation**: Automatische Code-Erstellung für alle Inventar-Items
- **Import/Export**: CSV/JSON Im- und Export mit Template-System
- **Backup & Archivierung**: Automatische Datensicherung mit Komprimierung
- **Bulk Operations**: Massenoperationen für effiziente Datenverwaltung
- **Debug Tool**: Umfassende System-Diagnostik und Monitoring

#### 🔍 **Search & Filter**
- **Advanced Search**: Globale Suche mit Filtern, Suggestions und Export
- **Smart Filtering**: Intelligente Filter für Hardware, Kabel und Standorte
- **Real-time Results**: Instant-Suchergebnisse mit Highlight

## 🛠 Technology Stack

- **Backend**: FastAPI + SQLAlchemy + PostgreSQL
- **Frontend**: Streamlit (Multi-Page App)
- **Database**: PostgreSQL 15 mit SQLAlchemy ORM
- **Security**: HTTPS-only mit nginx Reverse Proxy, SSL/TLS 1.2+
- **Containerization**: Docker + Docker Compose
- **Authentication**: Session-based mit bcrypt
- **Analytics**: Pandas + Plotly für Visualisierungen
- **QR/Barcode**: qrcode + python-barcode + Pillow
- **PDF Generation**: ReportLab

## 🚦 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### Installation

```bash
# Repository klonen
git clone https://github.com/HapsiellX/invmanager.git
cd invmanager

# HTTPS-System starten
docker-compose up -d

# Warten bis alle Services bereit sind (ca. 30 Sekunden)
# SICHERER Zugang über HTTPS: https://localhost
# HTTP wird automatisch zu HTTPS umgeleitet
```

### Standard Login
- **Username**: `admin`
- **Password**: `admin123`

## 📁 Project Structure

```
inventory-management/
├── app/                        # Hauptanwendung
│   ├── main.py                # Streamlit Entry Point
│   ├── core/                  # Kern-Module
│   │   ├── config.py         # Konfiguration
│   │   ├── database.py       # Datenbankverbindung
│   │   └── security.py       # Authentifizierung
│   ├── database/             # Datenbank Models
│   │   └── models/           # SQLAlchemy Models
│   ├── auth/                 # Authentifizierung
│   ├── dashboard/            # Dashboard Views
│   ├── hardware/             # Hardware Management
│   ├── cable/                # Kabel Management
│   ├── locations/            # Standort Management
│   ├── analytics/            # Analytics & Reporting
│   ├── notifications/        # Benachrichtigungssystem
│   ├── qr_barcode/          # QR & Barcode Generation
│   ├── search/              # Advanced Search
│   ├── import_export/       # Datenimport/-export
│   ├── backup/              # Backup & Archivierung
│   ├── bulk_operations/     # Massenoperationen
│   ├── audit/               # Audit Trail
│   ├── settings/            # System Settings
│   └── debug/               # Debug Tools
├── database/                 # Database Files
├── backups/                  # Backup Storage
├── nginx/                     # HTTPS Reverse Proxy
│   └── nginx.conf            # SSL/HTTPS Konfiguration
├── ssl/                      # SSL Zertifikate
│   ├── certificate.crt       # SSL Zertifikat
│   ├── private.key          # Privater Schlüssel
│   └── fullchain.pem        # Zertifikatskette
├── docker-compose.yml        # Docker Configuration (HTTPS)
├── Dockerfile               # Container Definition
├── requirements.txt         # Python Dependencies
├── HTTPS_SETUP.md          # HTTPS Dokumentation
└── README.md               # Diese Datei
```

## 🔧 Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/inventory_db
POSTGRES_DB=inventory_db
POSTGRES_USER=inventory_user
POSTGRES_PASSWORD=secure_password

# Application
SECRET_KEY=your_secret_key_here
STREAMLIT_SERVER_PORT=8501
```

### Docker Compose
Das System läuft standardmäßig mit:
- **HTTPS**: Port 443 (nginx SSL Proxy)
- **HTTP**: Port 80 (automatischer Redirect zu HTTPS)
- **App**: Port 8501 (intern über nginx)
- **Database**: Port 5432 (PostgreSQL)

## 👥 User Roles

### 🔑 **Admin**
- Vollzugriff auf alle Funktionen
- Benutzer- und Systemverwaltung
- Debug Tools und Analytics
- Backup & Import/Export

### 🌐 **Netzwerker**
- Hardware & Kabel Management
- Standort Verwaltung
- Analytics und Reports
- QR/Barcode Generation

### 🎓 **Auszubildende**
- Readonly Zugriff auf Inventar
- Basic Search Funktionen
- Benachrichtigungen einsehen

## 📊 Key Features Details

### QR & Barcode System
- **Unterstützte Formate**: QR Code, Code128, Code39, EAN13
- **Automatische Generation**: Für alle Inventar-Items
- **Label Creation**: Komplette Etiketten mit Metadaten
- **Bulk Generation**: Massenweise Code-Erstellung

### Notification System
- **Stock Alerts**: Niedrige/Hohe Bestände
- **Warranty Alerts**: Ablaufende Garantien
- **Critical Actions**: Systemänderungen tracking
- **Real-time Updates**: Instant Benachrichtigungen

### Analytics Dashboard
- **Value Trends**: Bestandswert-Entwicklung über Zeit
- **Usage Statistics**: Nutzungsanalysen und Trends
- **Performance Metrics**: System-Performance Monitoring
- **Custom Reports**: Anpassbare Report-Generierung

## 🔄 Version History

### v0.4.0 (Latest) - HTTPS-Only Security Release
- 🔐 **HTTPS-Only Implementation**: Vollständige SSL/TLS Verschlüsselung mit nginx Reverse Proxy
- 🛡️ **Security Headers**: HSTS, CSP, XSS Protection, Frame Options
- 🔧 **User Profile Management**: Passwort-Änderung für alle Benutzerrollen
- 🚀 **HTTP/2 Support**: Moderne Performance-Optimierungen
- 🔄 **Auto-Redirect**: Automatische Umleitung von HTTP zu HTTPS
- 📱 **Self-Signed Certificates**: Automatische SSL-Zertifikat Generierung
- 🔍 **Enhanced Security**: Umfassende Sicherheitsverbesserungen

### v0.3.1 - Production Ready & Bug-Free
- ✅ **FINAL FIX**: Persistent notification AttributeError komplett behoben
- ✅ Enhanced safe attribute accessor mit vollständiger ORM/Dictionary Kompatibilität
- ✅ Comprehensive database error handling mit graceful degradation
- ✅ Advanced debug tools mit detaillierter system diagnostik
- ✅ Alle kritischen bugs systematisch identifiziert und behoben
- ✅ 100% production-ready deployment ohne bekannte Fehler

### v0.3.0 - Production Ready Foundation
- ✅ Vollständige Dependency-Resolution (QR/Barcode, Notifications)
- ✅ Robuste Error-Handling überall implementiert
- ✅ Debug Tool für umfassende System-Diagnostik
- ✅ Analytics AttributeError fixes
- ✅ Safe attribute accessor für ORM/Dictionary Kompatibilität
- ✅ Docker optimization mit allen System-Dependencies

### v0.2.0 - Feature Complete
- Advanced Search & Filtering
- QR/Barcode Generation
- Backup & Archivierung
- Bulk Operations
- Notification System

### v0.1.0 - Core Features
- Basic Inventory Management
- User Authentication
- Dashboard
- CRUD Operations

## 🛡️ Security Features

### 🔐 **HTTPS & SSL/TLS**
- **HTTPS-Only**: Alle Verbindungen vollständig verschlüsselt
- **TLS 1.2/1.3**: Moderne Verschlüsselungsstandards
- **Perfect Forward Secrecy**: Enhanced Key Exchange
- **HTTP to HTTPS Redirect**: Automatische sichere Umleitung

### 🔒 **Security Headers**
- **HSTS**: HTTP Strict Transport Security (1 Jahr)
- **CSP**: Content Security Policy
- **XSS Protection**: Cross-Site Scripting Schutz
- **Frame Options**: Clickjacking-Schutz
- **Content Type Protection**: MIME-Type Sniffing Schutz

### 👤 **Authentication & Authorization**
- **Rollenbasierte Zugriffskontrolle** (Admin, Netzwerker, Auszubildende)
- **Session Management** mit automatischem Timeout
- **Password Hashing** mit bcrypt (12 Rounds)
- **User Profile Management** mit sicherer Passwort-Änderung
- **Audit Logging** für alle kritischen Aktionen
- **Input Validation** und SQL Injection Schutz

## 🔍 Troubleshooting

### Common Issues

#### Dependencies nicht installiert
```bash
# Clean rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### Debug Information
Nutzen Sie das integrierte **Debug Tool** (Admin → 🔧 Debug Tool) für:
- Dependency Status Check
- Database Connection Tests
- System Performance Monitoring
- Error Diagnostics

#### Logs einsehen
```bash
# Application logs
docker-compose logs app

# Database logs
docker-compose logs db
```

## 📝 Development

### Local Development Setup
```bash
# Virtual environment erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Dependencies installieren
pip install -r requirements.txt

# Lokale Entwicklung starten
streamlit run app/main.py
```

### Testing
```bash
# Tests ausführen
pytest app/tests/

# Coverage Report
pytest --cov=app app/tests/
```

## 🤝 Contributing

1. Fork das Repository
2. Feature Branch erstellen (`git checkout -b feature/AmazingFeature`)
3. Changes committen (`git commit -m 'Add some AmazingFeature'`)
4. Branch pushen (`git push origin feature/AmazingFeature`)
5. Pull Request öffnen

## 📄 License

Dieses Projekt ist unter der MIT License lizenziert - siehe [LICENSE](LICENSE) Datei für Details.

## 🎯 Roadmap

- [x] **HTTPS-Only Security** ✅ (v0.4.0)
- [x] **User Profile Management** ✅ (v0.4.0)
- [ ] Production SSL Certificates (Let's Encrypt Integration)
- [ ] Mobile-responsive UI
- [ ] REST API für externe Integration
- [ ] Advanced Reporting mit Charts
- [ ] Multi-Tenant Support
- [ ] LDAP/AD Integration
- [ ] Email Notifications
- [ ] Asset Lifecycle Management

### 🔐 Security Roadmap
- [x] HTTPS-Only Implementation
- [x] Security Headers (HSTS, CSP, etc.)
- [ ] WAF (Web Application Firewall)
- [ ] Rate Limiting & DDoS Protection
- [ ] Two-Factor Authentication (2FA)
- [ ] Single Sign-On (SSO)

## 🆘 Support

Bei Fragen oder Problemen:
1. Prüfen Sie die [Issues](https://github.com/HapsiellX/invmanager/issues)
2. Nutzen Sie das integrierte Debug Tool
3. Erstellen Sie ein neues Issue mit detaillierter Beschreibung

---

**Built with ❤️ for efficient inventory management**