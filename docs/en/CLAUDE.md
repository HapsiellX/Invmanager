# CLAUDE.md - AI Development Guide
## Inventory Management System

**Last Updated**: 2025-09-28
**Version**: 1.0
**Project Status**: Production Ready with Camera Scanner Enhancement

---

## Quick Start for AI Development

### Current Project State
- **Phase**: Production ready with advanced camera scanning capabilities
- **Completed**: Full inventory system, HTTPS security, camera scanner integration
- **Technology**: Python + Streamlit + PostgreSQL + Docker + nginx + WebRTC
- **Status**: Fully functional production system

### Environment Setup
- **Platform**: WSL2 Debian (root password: "electric")
- **Tech Stack**: Python + Streamlit + PostgreSQL + Docker + nginx + Camera Scanner
- **Target Deployment**: Windows Server + Linux Server support with HTTPS-only

---

## Project Structure Overview

```
inventory-management/
├── app/
│   ├── auth/           # Authentication & user management
│   ├── dashboard/      # Main dashboard with health checks
│   ├── hardware/       # Hardware inventory management
│   ├── cables/         # Cable inventory management
│   ├── analytics/      # Analytics and reporting
│   ├── locations/      # Location hierarchy management
│   ├── history/        # Audit trail and transaction history
│   ├── import_export/  # Data import/export functionality
│   ├── qr_barcode/     # QR/Barcode generation & camera scanning
│   ├── core/           # Shared utilities and base classes
│   └── main.py         # Streamlit main application
├── database/
│   ├── models/         # SQLAlchemy models
│   ├── migrations/     # Database migration scripts
│   └── seeds/          # Initial/sample data
├── docs/
│   ├── en/             # English documentation
│   ├── de/             # German documentation (Deutsch)
│   └── README.md       # Language selection
├── nginx/
│   ├── nginx.conf      # HTTPS reverse proxy configuration
│   └── ssl/            # SSL certificates
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.template
├── scripts/
│   ├── start.bat       # Windows start script
│   ├── stop.bat        # Windows stop script
│   ├── github.bat      # Git automation script
│   ├── start.sh        # Linux start script
│   └── stop.sh         # Linux stop script
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── requirements.txt
├── docker-compose.yml
├── .env.template
├── .gitignore
└── README.md
```

---

## Core Requirements Summary

### Essential Features (✅ COMPLETED)
1. **User Authentication**: Complete login system with role-based access
2. **Hardware Inventory**: Complete CRUD with German field names
3. **Cable Inventory**: Stock management with alerts
4. **Location Management**: Hierarchical structure
5. **Dashboard**: Overview with health checks and alerts
6. **PostgreSQL Integration**: Robust data persistence
7. **Docker Deployment**: Cross-platform containerization
8. **HTTPS Security**: nginx reverse proxy with SSL/TLS
9. **Camera Scanner**: WebRTC-based QR/barcode scanning

### Key Data Models

#### Hardware Inventory Fields
```python
# German field names as specified in requirements
- standort (Location)
- ort (Specific Location: "Warehouse 1, Cabinet 3")
- kategorie (Category: Switch, Router, Firewall, Transceiver)
- bezeichnung (Model: MX204)
- hersteller (Manufacturer: Aruba, HPE, Cisco)
- seriennummer (S/N)
- formfaktor (Form Factor)
- klassifikation (Classification: 20Ports, 40Ports, SFP, OSFP)
- besonderheiten (Special Features)
- angenommen_durch (Received by)
- leistungsschein_nummer (Invoice Number)
- datum_eingang (Date In)
- datum_ausgang (Date Out)
```

#### User Roles
- **Admin**: Full system access
- **Netzwerker**: Hardware/cable management
- **Auszubildende**: Limited read/write access

---

## Development Guidelines

### Code Organization Principles
1. **Modular Architecture**: Each feature in separate module
2. **Maximum File Size**: Keep files under 300 lines for AI readability
3. **Clear Separation**: Models, Views, Controllers in separate files
4. **German Business Terms**: Use German field names as specified
5. **Comprehensive Documentation**: Every function and class documented
6. **Camera Integration**: WebRTC and OpenCV for scanning capabilities

### Naming Conventions
- **Files**: snake_case.py
- **Classes**: PascalCase
- **Functions**: snake_case
- **Variables**: snake_case
- **Constants**: UPPER_SNAKE_CASE
- **Database Tables**: singular nouns (user, hardware_item, cable)

### Required Dependencies
```python
# Core Framework
streamlit>=1.28.0
fastapi>=0.104.0
uvicorn>=0.24.0

# Database
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
alembic>=1.12.0

# Camera Scanner
opencv-python>=4.8.0
pyzbar>=0.1.9
streamlit-webrtc>=0.47.0
av>=10.0.0

# Utilities
pandas>=2.1.0
plotly>=5.17.0
python-dotenv>=1.0.0
bcrypt>=4.0.0
python-multipart>=0.0.6
qrcode[pil]>=7.0.0
python-barcode[images]>=0.15.0
Pillow>=10.0.0
```

---

## Current Implementation Status

### ✅ Completed Components

1. **Project Structure**: Complete directory structure with all modules
2. **Database Models**: All models implemented with German field names
   - User model with role-based permissions
   - Hardware model with all required fields
   - Cable model with quantity tracking
   - Location model with hierarchical structure
   - Transaction model for audit trail
   - AuditLog model for security events

3. **Core Infrastructure**:
   - Configuration management (config.py)
   - Database connection and session management
   - Security utilities with password hashing and JWT
   - Session management for Streamlit
   - HTTPS-only deployment with nginx

4. **Authentication System**:
   - Complete login/logout functionality
   - Role-based access control (admin, netzwerker, auszubildende)
   - User management (create, update, deactivate)
   - Password change functionality
   - Audit logging for all auth events

5. **Complete Inventory System**:
   - Hardware inventory with full CRUD operations
   - Cable inventory with stock management
   - Location hierarchy management
   - QR/Barcode generation for all items
   - Advanced search and filtering

6. **Camera Scanner System**:
   - Live camera scanning with WebRTC
   - Image upload scanning with OpenCV
   - Multi-format support (QR, various barcodes)
   - Database integration for scanned items
   - Mobile-optimized camera access

7. **Analytics & Reporting**:
   - Dashboard with real-time metrics
   - Advanced analytics with trend analysis
   - Notification system for alerts
   - Import/Export functionality
   - Audit trail and history

8. **Security & Deployment**:
   - HTTPS-only with SSL/TLS encryption
   - nginx reverse proxy
   - Docker containerization
   - Cross-platform deployment scripts
   - Environment configuration

### 🎯 System Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│    nginx        │    │  Streamlit   │    │  PostgreSQL     │
│  (HTTPS Proxy)  │◄──►│   Frontend   │◄──►│   Database      │
│  Port 443/80    │    │  Port 8501   │    │  Port 5432      │
└─────────────────┘    └──────────────┘    └─────────────────┘
         │                       │
         │              ┌────────▼────────┐
         │              │   Camera API    │
         │              │  (WebRTC/OpenCV)│
         │              └─────────────────┘
         │
┌────────▼─────┐
│ SSL/TLS      │
│ Certificates │
└──────────────┘
```

---

## Camera Scanner Implementation

### Technical Components
1. **WebRTC Integration**: Browser camera access via streamlit-webrtc
2. **OpenCV Processing**: Image processing and frame analysis
3. **pyzbar Detection**: QR/barcode recognition library
4. **Database Lookup**: Automatic inventory item lookup
5. **Mobile Support**: Optimized for mobile device cameras

### Scanner Workflow
```python
def camera_scan_workflow():
    1. User selects "Camera Scanner" mode
    2. WebRTC establishes camera connection
    3. Video frames processed in real-time
    4. OpenCV + pyzbar detect codes
    5. Database lookup for inventory items
    6. Results displayed with actions
```

---

## Production Deployment

### Docker Services
```yaml
services:
  nginx:      # HTTPS reverse proxy
  app:        # Streamlit application
  db:         # PostgreSQL database
```

### Security Features
- HTTPS-only access
- SSL/TLS encryption
- Security headers (HSTS, CSP, XSS protection)
- Role-based access control
- Session security

### Camera Requirements
- HTTPS connection (required for camera access)
- Browser permissions for camera
- WebRTC-compatible browser
- System libraries: libzbar0, libgl1-mesa-dev, OpenCV dependencies

---

## Quick Commands for Development

### Docker Operations
```bash
# Start production environment
docker-compose up -d

# View logs
docker-compose logs -f

# Stop environment
docker-compose down

# Rebuild with new dependencies
docker-compose build --no-cache app
```

### Database Operations
```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Reset database
docker-compose down -v && docker-compose up -d
```

### Development Server
```bash
# Start Streamlit app (development)
streamlit run app/main.py

# Production deployment uses nginx + Docker
```

---

## Camera Scanner Testing

### Test Camera Functionality
```bash
# Test scanner dependencies in container
docker exec inventory_app python3 -c "
import cv2, pyzbar, streamlit_webrtc, av
print('All scanner dependencies available')
"
```

### Test Workflow
1. Navigate to: **📱 QR & Barcodes** → **🔍 Code Scanner**
2. Select: **📷 Camera Scanner**
3. Grant camera permissions
4. Test with QR codes/barcodes
5. Verify database lookup functionality

---

## Architecture Decisions

### Why This Tech Stack?
1. **Streamlit**: Rapid development, perfect for internal tools
2. **PostgreSQL**: Robust, scalable database
3. **Docker**: Consistent deployment across platforms
4. **nginx**: Production-grade reverse proxy
5. **WebRTC**: Standards-based camera access
6. **OpenCV**: Industry-standard computer vision

### Security Considerations
- HTTPS-only deployment
- No sensitive data in logs
- Role-based access control
- Session security
- Camera permissions management

---

## Development Best Practices

### File Organization Template
```python
# Each module should contain:
├── __init__.py          # Module initialization
├── models.py           # Database models
├── views.py            # Streamlit UI components
├── services.py         # Business logic
├── utils.py            # Helper functions
└── tests/              # Module-specific tests
    ├── test_models.py
    ├── test_services.py
    └── test_views.py
```

### Error Handling Strategy
- **Validation Errors**: Clear user-friendly messages in German
- **Database Errors**: Logged but user sees generic error message
- **Authentication Errors**: Specific feedback for login issues
- **Camera Errors**: Helpful troubleshooting messages
- **Import Errors**: Detailed feedback on data validation failures

---

## Current System Status

### Production Ready Features
- ✅ Complete inventory management
- ✅ User authentication & authorization
- ✅ HTTPS security implementation
- ✅ Camera scanner functionality
- ✅ Analytics and reporting
- ✅ Import/Export capabilities
- ✅ Docker deployment
- ✅ Cross-platform support

### System Health
- **Database**: PostgreSQL with full schema
- **Security**: HTTPS-only with SSL/TLS
- **Performance**: Optimized for production use
- **Monitoring**: Health checks and diagnostics
- **Documentation**: Comprehensive bilingual docs

---

**Remember**: This system is production-ready and fully functional. All major features are implemented and tested. The camera scanner enhancement makes it a complete, modern inventory management solution.

---

*This file is updated with every significant change to ensure AI can resume development from the exact point where previous work ended.*