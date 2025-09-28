# CLAUDE.md - AI Development Guide
## Inventory Management System

**Last Updated**: 2025-09-28
**Version**: 1.0
**Project Status**: Core Implementation Phase

---

## Quick Start for AI Development

### Current Project State
- **Phase**: Core foundation implemented, authentication working
- **Completed**: Project structure, database models, authentication system, basic dashboard
- **Next Steps**: Complete hardware inventory CRUD operations
- **Priority**: Hardware inventory management, then cable inventory

### Environment Setup
- **Platform**: WSL2 Debian (root password: "electric")
- **Tech Stack**: Python + Streamlit + PostgreSQL + Docker
- **Target Deployment**: Windows Server + Linux Server support

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
│   ├── core/           # Shared utilities and base classes
│   └── main.py         # Streamlit main application
├── database/
│   ├── models/         # SQLAlchemy models
│   ├── migrations/     # Database migration scripts
│   └── seeds/          # Initial/sample data
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
├── docs/
│   ├── API.md
│   ├── USER_GUIDE.md
│   └── DEPLOYMENT.md
├── requirements.txt
├── docker-compose.yml
├── .env.template
├── .gitignore
└── README.md
```

---

## Core Requirements Summary

### Essential Features (MVP)
1. **User Authentication**: Simple login system with role-based access
2. **Hardware Inventory**: Complete CRUD with German field names
3. **Dashboard**: Overview with health checks and alerts
4. **PostgreSQL Integration**: Robust data persistence
5. **Docker Deployment**: Cross-platform containerization

### Key Data Models

#### Hardware Inventory Fields
```python
# German field names as specified in requirements
- standort (Location)
- ort (Specific Location: "Lager 1, Schrank 3")
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

# Utilities
pandas>=2.1.0
plotly>=5.17.0
python-dotenv>=1.0.0
bcrypt>=4.0.0
python-multipart>=0.0.6
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

4. **Authentication System**:
   - Complete login/logout functionality
   - Role-based access control (admin, netzwerker, auszubildende)
   - User management (create, update, deactivate)
   - Password change functionality
   - Audit logging for all auth events

5. **Basic Dashboard**:
   - Main navigation structure
   - Quick stats display (placeholder)
   - Health check alerts system (placeholder)
   - Recent activity feed (placeholder)

6. **Deployment Setup**:
   - Docker configuration with PostgreSQL
   - Cross-platform start/stop scripts
   - Environment configuration template
   - Git automation scripts

### 🚧 Partially Implemented

1. **Database Initialization**: Sample data script created
2. **Module Structure**: All modules have placeholder views

### ❌ Pending Implementation

1. **Hardware Inventory CRUD**: Complete implementation needed
2. **Cable Inventory Management**: Full implementation needed
3. **Real Health Checks**: Connect to actual data
4. **Location Management**: CRUD operations
5. **Analytics Module**: Data visualization and reports
6. **Import/Export**: File processing functionality
7. **History/Audit Views**: Transaction history display

### 🔧 Ready for Testing

The system can be started and tested with:
- User authentication (3 sample users: admin/admin123, netzwerker/network123, azubi/azubi123)
- Basic navigation between modules
- Role-based access control
- Database connectivity

## Implementation Roadmap

### Phase 1: Foundation (✅ COMPLETED)
1. **Project Setup**
   - Initialize directory structure
   - Set up Docker configuration
   - Create batch/shell scripts
   - Configure PostgreSQL container

2. **Core Authentication**
   - User model and database tables
   - Simple login/logout functionality
   - Role-based access control
   - Session management

3. **Basic Hardware Inventory**
   - Hardware model with all required fields
   - CRUD operations (Create, Read, Update, Delete)
   - Basic Streamlit interface
   - Data validation

4. **Simple Dashboard**
   - Inventory overview
   - Basic health checks
   - Navigation structure

### Phase 2: Extended Features
1. **Cable Inventory Management**
2. **Location Hierarchy**
3. **Import/Export Functionality**
4. **Enhanced Analytics**

### Phase 3: Advanced Features
1. **Audit Trail & History**
2. **Advanced Health Checks**
3. **Performance Optimization**
4. **Enhanced UI/UX**

---

## Technical Specifications

### Database Schema Priorities
1. **users** - Authentication and roles
2. **hardware_items** - Core inventory data
3. **locations** - Hierarchical location structure
4. **cables** - Cable inventory with quantities
5. **transactions** - Audit trail for all changes

### Health Check Logic
- **Critical**: Stock count = 0
- **Low**: Stock count < defined threshold
- **Normal**: Stock count >= threshold
- Alert examples: "Niedrig: 2 kabel haben niedrigen bestand", "Kritisch: Router inventory ist leer"

### Deployment Requirements
- **Cross-platform**: Windows Server + Linux Server
- **Simple Operation**: start.bat/stop.bat for easy management
- **Git Integration**: github.bat for version control
- **Container Security**: Minimal attack surface
- **Environment Configuration**: .env files for secrets

---

## Current Development Context

### Immediate Next Steps
1. Set up project directory structure
2. Create Docker configuration files
3. Initialize PostgreSQL with basic schema
4. Implement user authentication system
5. Build hardware inventory CRUD operations

### Key Considerations
- **German Field Names**: All business logic uses German terminology
- **Modular Design**: Each component must be independently developable
- **AI-Friendly**: Code structure optimized for AI comprehension and modification
- **Documentation First**: Comprehensive docs enable seamless AI handoff

### Testing Strategy
- **Unit Tests**: For business logic and data models
- **Integration Tests**: For API endpoints and database operations
- **UI Tests**: For Streamlit interface functionality
- **Deployment Tests**: Verify cross-platform Docker deployment

---

## Questions for Clarification

### Pending Technical Decisions
1. **Frontend Framework**: Pure Streamlit or hybrid with FastAPI?
2. **Real-time Updates**: WebSocket implementation needed?
3. **File Storage**: Local filesystem or cloud storage for imports?
4. **Session Management**: Database-backed or in-memory sessions?

### Business Logic Clarifications
1. **Health Check Thresholds**: Should these be configurable per item category?
2. **Location Hierarchy**: How many levels deep should the location structure go?
3. **User Management**: Should admins be able to create/delete users in the app?
4. **Data Retention**: How long should transaction history be retained?

---

## Common Commands for Development

### Docker Operations
```bash
# Start development environment
docker-compose up -d

# View logs
docker-compose logs -f

# Stop environment
docker-compose down

# Rebuild containers
docker-compose up -d --build
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
# Start Streamlit app
streamlit run app/main.py

# Start FastAPI (if using hybrid approach)
uvicorn app.api.main:app --reload
```

---

## File Organization Best Practices

### Module Structure Template
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

### Import Standards
```python
# Standard library imports first
import os
import datetime
from typing import List, Optional

# Third-party imports
import streamlit as st
import pandas as pd
from sqlalchemy import Column, Integer, String

# Local application imports
from app.core.database import Base
from app.core.config import settings
```

---

## Error Handling Strategy

### Standardized Error Responses
- **Validation Errors**: Clear user-friendly messages in German
- **Database Errors**: Logged but user sees generic error message
- **Authentication Errors**: Specific feedback for login issues
- **Import Errors**: Detailed feedback on data validation failures

### Logging Requirements
- **Application Logs**: All user actions and system events
- **Error Logs**: Complete stack traces for debugging
- **Audit Logs**: Security-relevant events
- **Performance Logs**: Response times and resource usage

---

**Remember**: This project is designed for continuous AI development. Every decision should prioritize code clarity, modularity, and comprehensive documentation to enable seamless AI handoffs and modifications.

---

*Keep this file updated with every significant change to ensure AI can resume development from the exact point where previous work ended.*