#!/usr/bin/env python3
"""
Simple startup test to verify the system can initialize
Run this before starting the Docker containers
"""

import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

try:
    print("Testing imports...")

    # Test core imports
    from app.core.config import settings
    print("✅ Core config imported")

    from app.core.security import security, SessionManager
    print("✅ Security module imported")

    # Test model imports
    from app.database.models.user import User
    from app.database.models.hardware import HardwareItem
    from app.database.models.cable import Cable
    from app.database.models.location import Location
    print("✅ Database models imported")

    # Test service imports
    from app.auth.services import AuthService
    print("✅ Auth service imported")

    # Test view imports
    from app.auth.views import show_login_page
    from app.dashboard.views import show_dashboard
    print("✅ View modules imported")

    print("\n🎉 All imports successful!")
    print(f"Database URL: {settings.DATABASE_URL}")
    print(f"Environment: {settings.ENVIRONMENT}")

    print("\n📋 Next steps:")
    print("1. Navigate to inventory-management directory")
    print("2. Run: scripts/start.bat (Windows) or ./scripts/start.sh (Linux)")
    print("3. Wait for containers to start")
    print("4. Access http://localhost:8501")
    print("5. Login with: admin/admin123 or netzwerker/network123 or azubi/azubi123")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please check that all dependencies are installed")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)