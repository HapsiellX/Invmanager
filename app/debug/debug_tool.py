"""
Comprehensive debugging tool for inventory management system
"""

import streamlit as st
import sys
import os
import traceback
import importlib
import subprocess
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

# Optional import for psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

def show_debug_page():
    """Main debug page with comprehensive system analysis"""
    st.header("🔧 System Debug Tool")

    st.warning("""
    ⚠️ **Debug-Modus aktiv**
    Dieses Tool zeigt detaillierte Systeminformationen zur Fehlerbehebung.
    """)

    # Create tabs for different debug categories
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🐍 Python Environment",
        "📦 Dependencies",
        "🗄️ Database",
        "🔔 Notifications",
        "📊 QR & Barcodes"
    ])

    with tab1:
        show_python_environment_debug()

    with tab2:
        show_dependencies_debug()

    with tab3:
        show_database_debug()

    with tab4:
        show_notifications_debug()

    with tab5:
        show_qr_barcode_debug()


def show_python_environment_debug():
    """Debug Python environment and system info"""
    st.subheader("🐍 Python Environment")

    try:
        # Python version and path
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
            st.metric("Python Executable", sys.executable)

        with col2:
            st.metric("Platform", sys.platform)
            if PSUTIL_AVAILABLE:
                try:
                    memory_info = psutil.virtual_memory()
                    st.metric("Available Memory", f"{memory_info.available / (1024**3):.1f} GB")
                except:
                    st.metric("Available Memory", "Unknown")
            else:
                st.metric("Available Memory", "psutil not available")

        # Python path
        with st.expander("🛤️ Python Path (sys.path)"):
            for i, path in enumerate(sys.path):
                st.text(f"{i}: {path}")

        # Environment variables
        with st.expander("🌍 Environment Variables"):
            env_vars = dict(os.environ)
            for key, value in sorted(env_vars.items()):
                if any(secret in key.lower() for secret in ['password', 'token', 'secret', 'key']):
                    st.text(f"{key}: *** (hidden)")
                else:
                    st.text(f"{key}: {value}")

        # Current working directory and file structure
        with st.expander("📁 File System"):
            st.text(f"Current Working Directory: {os.getcwd()}")
            st.text(f"Script Directory: {os.path.dirname(os.path.abspath(__file__))}")

            # Show app structure
            app_dir = "/mnt/c/Users/Kardo/inventory-management/app"
            if os.path.exists(app_dir):
                st.text("App Directory Structure:")
                for root, dirs, files in os.walk(app_dir):
                    level = root.replace(app_dir, '').count(os.sep)
                    indent = ' ' * 2 * level
                    st.text(f"{indent}{os.path.basename(root)}/")
                    subindent = ' ' * 2 * (level + 1)
                    for file in files[:10]:  # Limit to first 10 files per directory
                        st.text(f"{subindent}{file}")
                    if len(files) > 10:
                        st.text(f"{subindent}... and {len(files) - 10} more files")

    except Exception as e:
        st.error(f"Error analyzing Python environment: {e}")
        st.code(traceback.format_exc())


def show_dependencies_debug():
    """Debug dependency installation and imports"""
    st.subheader("📦 Dependencies Analysis")

    # Required dependencies for different features
    qr_barcode_deps = [
        'qrcode', 'PIL', 'barcode', 'reportlab'
    ]

    notification_deps = [
        'sqlalchemy', 'streamlit', 'pandas'
    ]

    core_deps = [
        'streamlit', 'fastapi', 'sqlalchemy', 'pandas', 'plotly'
    ]

    all_deps = list(set(qr_barcode_deps + notification_deps + core_deps))

    st.subheader("📋 Dependency Status")

    # Check each dependency
    dep_status = {}
    for dep in all_deps:
        status = check_dependency(dep)
        dep_status[dep] = status

        # Color coding
        if status['installed']:
            if status['importable']:
                st.success(f"✅ {dep}: {status['version']} - OK")
            else:
                st.warning(f"⚠️ {dep}: {status['version']} - Installiert aber nicht importierbar")
                if status['error']:
                    st.code(status['error'])
        else:
            st.error(f"❌ {dep}: Nicht installiert")

    # Feature-specific analysis
    st.subheader("🎯 Feature-Specific Analysis")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("QR & Barcodes")
        qr_working = all(dep_status.get(dep, {}).get('importable', False) for dep in qr_barcode_deps)
        if qr_working:
            st.success("✅ Alle Dependencies verfügbar")
        else:
            st.error("❌ Dependencies fehlen")
            for dep in qr_barcode_deps:
                if not dep_status.get(dep, {}).get('importable', False):
                    st.text(f"- {dep}")

    with col2:
        st.subheader("Notifications")
        notif_working = all(dep_status.get(dep, {}).get('importable', False) for dep in notification_deps)
        if notif_working:
            st.success("✅ Alle Dependencies verfügbar")
        else:
            st.error("❌ Dependencies fehlen")
            for dep in notification_deps:
                if not dep_status.get(dep, {}).get('importable', False):
                    st.text(f"- {dep}")

    with col3:
        st.subheader("Core System")
        core_working = all(dep_status.get(dep, {}).get('importable', False) for dep in core_deps)
        if core_working:
            st.success("✅ Alle Dependencies verfügbar")
        else:
            st.error("❌ Dependencies fehlen")
            for dep in core_deps:
                if not dep_status.get(dep, {}).get('importable', False):
                    st.text(f"- {dep}")

    # Pip list output
    with st.expander("📜 Installed Packages (pip list)"):
        try:
            result = subprocess.run(['pip', 'list'], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                st.text(result.stdout)
            else:
                st.error(f"Error running pip list: {result.stderr}")
        except Exception as e:
            st.error(f"Could not run pip list: {e}")

    # Requirements.txt analysis
    with st.expander("📄 Requirements.txt Analysis"):
        req_file = "/mnt/c/Users/Kardo/inventory-management/requirements.txt"
        if os.path.exists(req_file):
            try:
                with open(req_file, 'r') as f:
                    requirements = f.read()
                st.text("Current requirements.txt:")
                st.code(requirements)

                # Check if QR/Barcode deps are in requirements
                missing_in_req = []
                for dep in qr_barcode_deps:
                    if dep.lower() not in requirements.lower():
                        missing_in_req.append(dep)

                if missing_in_req:
                    st.warning(f"Missing in requirements.txt: {', '.join(missing_in_req)}")
                else:
                    st.success("All QR/Barcode dependencies found in requirements.txt")

            except Exception as e:
                st.error(f"Error reading requirements.txt: {e}")
        else:
            st.error("requirements.txt not found")


def check_dependency(package_name: str) -> Dict[str, Any]:
    """Check if a package is installed and importable"""
    result = {
        'installed': False,
        'importable': False,
        'version': None,
        'error': None
    }

    try:
        # Try to import and get version
        if package_name == 'PIL':
            # Special case for Pillow
            import PIL
            result['installed'] = True
            result['importable'] = True
            result['version'] = PIL.__version__
        elif package_name == 'barcode':
            import barcode
            result['installed'] = True
            result['importable'] = True
            result['version'] = getattr(barcode, '__version__', 'unknown')
        else:
            module = importlib.import_module(package_name)
            result['installed'] = True
            result['importable'] = True
            result['version'] = getattr(module, '__version__', 'unknown')

    except ImportError as e:
        result['error'] = str(e)
        # Check if installed but not importable
        try:
            import pkg_resources
            pkg_resources.get_distribution(package_name)
            result['installed'] = True
            result['version'] = pkg_resources.get_distribution(package_name).version
        except:
            pass
    except Exception as e:
        result['error'] = str(e)

    return result


def show_database_debug():
    """Debug database connections and structure"""
    st.subheader("🗄️ Database Debug")

    # Check database file existence and permissions
    db_paths = [
        "/mnt/c/Users/Kardo/inventory-management/database/inventory.db",
        "/mnt/c/Users/Kardo/inventory-management/app/database/inventory.db",
        "./database/inventory.db",
        "./inventory.db"
    ]

    st.subheader("📁 Database File Analysis")

    for db_path in db_paths:
        if os.path.exists(db_path):
            st.success(f"✅ Found: {db_path}")
            try:
                stat = os.stat(db_path)
                st.text(f"  Size: {stat.st_size} bytes")
                st.text(f"  Modified: {datetime.fromtimestamp(stat.st_mtime)}")
                st.text(f"  Readable: {os.access(db_path, os.R_OK)}")
                st.text(f"  Writable: {os.access(db_path, os.W_OK)}")
            except Exception as e:
                st.error(f"  Error accessing file: {e}")
        else:
            st.info(f"❌ Not found: {db_path}")

    # Test database connections
    st.subheader("🔗 Database Connection Test")

    # Test SQLite direct connection
    with st.expander("SQLite Direct Connection"):
        try:
            for db_path in db_paths:
                if os.path.exists(db_path):
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()

                    # Get table list
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()

                    st.success(f"✅ Connected to {db_path}")
                    st.text(f"Tables found: {len(tables)}")
                    for table in tables:
                        st.text(f"  - {table[0]}")

                    # Test specific tables
                    test_tables = ['cables', 'hardware_items', 'users', 'audit_logs']
                    for table in test_tables:
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM {table}")
                            count = cursor.fetchone()[0]
                            st.text(f"  {table}: {count} records")
                        except sqlite3.OperationalError as e:
                            st.warning(f"  {table}: {e}")

                    conn.close()
                    break
        except Exception as e:
            st.error(f"SQLite connection failed: {e}")
            st.code(traceback.format_exc())

    # Test SQLAlchemy connection
    with st.expander("SQLAlchemy Connection"):
        try:
            # Try to import and use the database module
            from core.database import get_db
            db = next(get_db())
            st.success("✅ SQLAlchemy connection successful")

            # Test model imports
            model_tests = [
                ('Cable', 'database.models.cable'),
                ('HardwareItem', 'database.models.hardware'),
                ('User', 'database.models.user'),
                ('AuditLog', 'database.models.audit_log')
            ]

            for model_name, module_name in model_tests:
                try:
                    module = importlib.import_module(module_name)
                    model_class = getattr(module, model_name)
                    count = db.query(model_class).count()
                    st.text(f"  {model_name}: {count} records")
                except Exception as e:
                    st.warning(f"  {model_name}: {e}")

            db.close()

        except Exception as e:
            st.error(f"SQLAlchemy connection failed: {e}")
            st.code(traceback.format_exc())


def show_notifications_debug():
    """Debug notification system specifically"""
    st.subheader("🔔 Notifications Debug")

    # Test notification service import
    with st.expander("📥 Service Import Test"):
        try:
            from notifications.services import NotificationService, get_notification_service
            st.success("✅ NotificationService import successful")

            # Test database connection for notifications
            from core.database import get_db
            db = next(get_db())
            notification_service = get_notification_service(db)
            st.success("✅ NotificationService instantiation successful")

            # Test database connection
            try:
                db.execute("SELECT 1")
                st.success("✅ Database connection test passed")
            except Exception as e:
                st.error(f"❌ Database connection failed: {e}")

            # Test individual methods with detailed error handling
            methods_to_test = [
                '_get_stock_alerts',
                '_get_warranty_alerts',
                '_get_critical_action_alerts',
                '_get_system_alerts'
            ]

            for method_name in methods_to_test:
                with st.expander(f"🔍 Testing {method_name}"):
                    try:
                        method = getattr(notification_service, method_name)
                        alerts = method()
                        st.success(f"✅ {method_name}: {len(alerts)} alerts")

                        # Show detailed alert information
                        if alerts:
                            for i, alert in enumerate(alerts):
                                st.text(f"Alert {i+1}: {alert.get('title', 'No title')}")
                                if st.checkbox(f"Show details for alert {i+1}", key=f"show_alert_{method_name}_{i}"):
                                    st.json(alert)
                    except Exception as e:
                        st.error(f"❌ {method_name}: {e}")
                        st.code(traceback.format_exc())

            # Test main method with comprehensive error checking
            with st.expander("🔍 Testing get_all_notifications"):
                try:
                    all_notifications = notification_service.get_all_notifications("admin")
                    st.success(f"✅ get_all_notifications: {len(all_notifications)} notifications")

                    # Data type verification
                    if all_notifications:
                        st.text(f"Return type: {type(all_notifications)}")
                        st.text(f"First item type: {type(all_notifications[0])}")

                        # Show sample notification structure
                        st.subheader("Sample Notification Structure:")
                        st.json(all_notifications[0])

                        # Test accessing attributes that commonly cause errors
                        first_notification = all_notifications[0]
                        critical_attributes = ['id', 'title', 'message', 'timestamp', 'priority']

                        st.subheader("Attribute Access Test:")
                        for attr in critical_attributes:
                            try:
                                value = first_notification.get(attr, "NOT_FOUND")
                                st.text(f"✅ {attr}: {value} (type: {type(value)})")
                            except Exception as e:
                                st.error(f"❌ {attr}: {e}")

                except Exception as e:
                    st.error(f"❌ get_all_notifications failed: {e}")
                    st.code(traceback.format_exc())

            # Test safe_get_attr method
            with st.expander("🔍 Testing _safe_get_attr method"):
                test_objects = [
                    {'id': 1, 'name': 'test'},  # Dictionary
                    type('TestObj', (), {'id': 2, 'name': 'test_obj'}),  # Object
                    None,  # None
                    [1, 2, 3],  # List
                    (1, 2, 3),  # Tuple
                ]

                for i, test_obj in enumerate(test_objects):
                    st.text(f"Test object {i+1}: {type(test_obj)}")
                    try:
                        result = notification_service._safe_get_attr(test_obj, 'id', 'DEFAULT')
                        st.text(f"  _safe_get_attr(obj, 'id'): {result}")
                    except Exception as e:
                        st.error(f"  _safe_get_attr failed: {e}")

            db.close()

        except Exception as e:
            st.error(f"❌ Notification service import/setup failed: {e}")
            st.code(traceback.format_exc())

    # Test session manager and user information
    with st.expander("👤 User Session Test"):
        try:
            from core.security import SessionManager
            current_user = SessionManager.get_current_user()
            user_role = SessionManager.get_user_role()

            st.text(f"Current user type: {type(current_user)}")
            st.text(f"User role: {user_role}")

            if current_user:
                if isinstance(current_user, dict):
                    st.success("✅ Current user is dictionary")
                    if 'id' in current_user:
                        st.success(f"✅ User has 'id': {current_user['id']}")
                    else:
                        st.error("❌ User dictionary missing 'id' key")
                        st.text(f"Available keys: {list(current_user.keys())}")
                else:
                    st.warning(f"⚠️ Current user is {type(current_user)}, not dictionary")
                    if hasattr(current_user, 'id'):
                        st.text(f"User has id attribute: {current_user.id}")
            else:
                st.error("❌ No current user found")

        except Exception as e:
            st.error(f"❌ Session manager test failed: {e}")
            st.code(traceback.format_exc())
            st.code(traceback.format_exc())

    # Test data type analysis
    with st.expander("🔍 Data Type Analysis"):
        try:
            from core.database import get_db
            from database.models.cable import Cable

            db = next(get_db())

            # Get a sample cable and analyze its type
            cable = db.query(Cable).first()
            if cable:
                st.text(f"Cable object type: {type(cable)}")
                st.text(f"Cable id type: {type(cable.id)}")
                st.text(f"Cable id value: {cable.id}")

                # Test attribute access methods
                st.text("Attribute access test:")
                try:
                    st.text(f"  cable.id: {cable.id}")
                except Exception as e:
                    st.error(f"  cable.id failed: {e}")

                try:
                    st.text(f"  cable['id']: {cable['id']}")
                except Exception as e:
                    st.error(f"  cable['id'] failed: {e}")

                # Test our safe accessor
                try:
                    from notifications.services import NotificationService
                    ns = NotificationService(db)
                    safe_id = ns._safe_get_attr(cable, 'id')
                    st.text(f"  _safe_get_attr(cable, 'id'): {safe_id}")
                except Exception as e:
                    st.error(f"  _safe_get_attr failed: {e}")

                # Test to_dict method
                try:
                    cable_dict = cable.to_dict()
                    st.text(f"cable.to_dict() type: {type(cable_dict)}")
                    st.text(f"cable.to_dict()['id']: {cable_dict['id']}")
                except Exception as e:
                    st.error(f"cable.to_dict() failed: {e}")
            else:
                st.warning("No cables found in database")

            db.close()

        except Exception as e:
            st.error(f"Data type analysis failed: {e}")
            st.code(traceback.format_exc())

    # Advanced notification debugging
    with st.expander("🔍 Advanced Notification Debugging"):
        try:
            from notifications.debug_helper import show_notification_debug_panel, test_notification_methods
            from core.database import get_db

            db = next(get_db())
            show_notification_debug_panel(db)
            test_notification_methods(db)
            db.close()

        except Exception as e:
            st.error(f"Advanced debugging failed: {e}")
            st.code(traceback.format_exc())


def show_qr_barcode_debug():
    """Debug QR code and barcode functionality"""
    st.subheader("📊 QR & Barcode Debug")

    # Test individual package imports
    packages_to_test = {
        'qrcode': 'QR Code generation',
        'PIL': 'Image processing (Pillow)',
        'barcode': 'Barcode generation',
        'reportlab': 'PDF generation'
    }

    st.subheader("📦 Package Import Tests")

    import_results = {}
    for package, description in packages_to_test.items():
        try:
            if package == 'PIL':
                import PIL
                from PIL import Image
                st.success(f"✅ {package} ({description}): v{PIL.__version__}")
                import_results[package] = True
            elif package == 'qrcode':
                import qrcode
                st.success(f"✅ {package} ({description}): v{qrcode.__version__}")
                import_results[package] = True
            elif package == 'barcode':
                import barcode
                st.success(f"✅ {package} ({description}): v{getattr(barcode, '__version__', 'unknown')}")
                import_results[package] = True
            elif package == 'reportlab':
                import reportlab
                st.success(f"✅ {package} ({description}): v{reportlab.Version}")
                import_results[package] = True
        except ImportError as e:
            st.error(f"❌ {package} ({description}): Import failed - {e}")
            import_results[package] = False
        except Exception as e:
            st.warning(f"⚠️ {package} ({description}): {e}")
            import_results[package] = False

    # Functional tests
    st.subheader("🧪 Functional Tests")

    if import_results.get('qrcode', False) and import_results.get('PIL', False):
        with st.expander("QR Code Generation Test"):
            try:
                import qrcode
                from PIL import Image
                import io

                # Generate test QR code
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data("Test QR Code - Debug Tool")
                qr.make(fit=True)

                img = qr.make_image(fill_color="black", back_color="white")

                # Convert to bytes for display
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')
                img_bytes = img_buffer.getvalue()

                st.success("✅ QR Code generation successful")
                st.image(img_bytes, caption="Test QR Code", width=200)

            except Exception as e:
                st.error(f"❌ QR Code generation failed: {e}")
                st.code(traceback.format_exc())
    else:
        st.warning("⚠️ QR Code test skipped - dependencies not available")

    if import_results.get('barcode', False) and import_results.get('PIL', False):
        with st.expander("Barcode Generation Test"):
            try:
                from barcode import Code128
                from barcode.writer import ImageWriter
                import io

                # Generate test barcode
                code = Code128("123456789012", writer=ImageWriter())

                # Save to buffer
                img_buffer = io.BytesIO()
                code.write(img_buffer)
                img_bytes = img_buffer.getvalue()

                st.success("✅ Barcode generation successful")
                st.image(img_bytes, caption="Test Code128 Barcode", width=300)

            except Exception as e:
                st.error(f"❌ Barcode generation failed: {e}")
                st.code(traceback.format_exc())
    else:
        st.warning("⚠️ Barcode test skipped - dependencies not available")

    # Test the actual QR/Barcode service
    with st.expander("🎯 QR/Barcode Service Test"):
        try:
            # Try to import the actual service
            from qr_barcodes.services import get_qr_barcode_service
            from core.database import get_db

            db = next(get_db())
            qr_service = get_qr_barcode_service(db)

            st.success("✅ QR/Barcode service import successful")

            # Test dependency check
            deps = qr_service.check_dependencies()
            st.json(deps)

            # Test QR generation if dependencies are available
            if deps.get('qrcode_available', False):
                try:
                    qr_data = qr_service.generate_qr_code("TEST-DATA-123", "equipment")
                    st.success("✅ Service QR generation successful")
                    if qr_data.get('image_data'):
                        st.image(qr_data['image_data'], caption="Service Generated QR", width=200)
                except Exception as e:
                    st.error(f"❌ Service QR generation failed: {e}")
                    st.code(traceback.format_exc())

            db.close()

        except Exception as e:
            st.error(f"❌ QR/Barcode service test failed: {e}")
            st.code(traceback.format_exc())

    # Environment-specific tests
    with st.expander("🌍 Environment Tests"):
        st.text("Testing Docker/container environment specifics...")

        # Check if we're in Docker
        if os.path.exists('/.dockerenv'):
            st.info("🐳 Running in Docker container")
        else:
            st.info("💻 Running on host system")

        # Check system libraries
        system_libs = [
            'libjpeg-dev', 'zlib1g-dev', 'libfreetype6-dev',
            'liblcms2-dev', 'libopenjp2-7-dev', 'libtiff5-dev'
        ]

        st.text("System library check (approximate):")
        for lib in system_libs:
            # This is a very basic check - in reality, checking system libraries is complex
            lib_paths = [
                f'/usr/lib/x86_64-linux-gnu/{lib}',
                f'/usr/include/{lib}',
                f'/lib/x86_64-linux-gnu/{lib}'
            ]
            found = any(os.path.exists(path) for path in lib_paths)
            if found:
                st.text(f"  ✅ {lib}: Available")
            else:
                st.text(f"  ❓ {lib}: Not found (may still be available)")


if __name__ == "__main__":
    show_debug_page()