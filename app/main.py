"""
Main Streamlit application entry point
Inventory Management System
"""

import streamlit as st
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config import settings
from core.database import init_db, test_db_connection
from core.security import SessionManager
from auth.views import show_login_page
from dashboard.views import show_dashboard
from hardware.views import show_hardware_page
from cable.views import show_cable_inventory
from analytics.views import show_analytics_page
from locations.views import show_locations_page
from settings.views import show_settings_page
from import_export.views import show_import_export_page
from audit.views import show_audit_page
from search.views import show_search_page
from notifications.views import show_notifications_page, show_notification_badge
from qr_barcode.views import show_qr_barcode_page
from backup.views import show_backup_page
from reports.views import show_reports_page
from bulk_operations.views import show_bulk_operations_page
from debug.debug_tool import show_debug_page


def configure_page():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="Inventory Management System",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1f77b4;
    }
    .alert-critical {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 10px;
        color: #721c24;
    }
    .alert-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 10px;
        color: #856404;
    }
    .alert-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 10px;
        color: #155724;
    }
    </style>
    """, unsafe_allow_html=True)


def show_sidebar():
    """Display navigation sidebar"""
    with st.sidebar:
        st.image("https://via.placeholder.com/150x50/1f77b4/ffffff?text=IMS", width=150)
        st.title("Navigation")

        # User info
        if SessionManager.is_authenticated():
            user = SessionManager.get_current_user()
            st.write(f"**Willkommen, {user['vorname']}!**")
            st.write(f"Rolle: {user['rolle'].title()}")
            st.divider()

            # Navigation menu
            pages = {
                "Dashboard": "dashboard",
                "🔍 Suche": "search",
                "Hardware Inventar": "hardware",
                "Kabel Inventar": "cables",
                "Standorte": "locations",
                "Analytics": "analytics",
                "📊 Berichte": "reports",
                "⚡ Bulk-Operationen": "bulk_operations",
                "📱 QR & Barcodes": "qr_barcode",
                "Import/Export": "import_export",
                "💾 Backup": "backup",
                "Audit Trail": "audit",
                "🔔 Benachrichtigungen": "notifications",
                "🔧 Debug Tool": "debug",
                "Einstellungen": "settings"
            }

            # Filter pages based on user role
            user_role = SessionManager.get_user_role()
            if user_role == "auszubildende":
                # Trainees have limited access
                pages = {k: v for k, v in pages.items() if v in ["dashboard", "search", "hardware", "cables", "qr_barcode", "notifications"]}
            elif user_role == "netzwerker":
                # Network admins have no settings/backup/bulk_operations access but can use other advanced features including reports
                pages = {k: v for k, v in pages.items() if v not in ["settings", "backup", "bulk_operations", "debug"]}
            # Debug tool only for admins
            elif user_role != "admin":
                pages = {k: v for k, v in pages.items() if v != "debug"}

            for page_name, page_key in pages.items():
                # Add notification badge for notifications page
                button_label = page_name
                if page_key == "notifications":
                    try:
                        urgent_count = show_notification_badge()
                        if urgent_count > 0:
                            button_label = f"{page_name} ({urgent_count})"
                    except:
                        pass  # If badge fails, just show normal label

                if st.button(button_label, key=f"nav_{page_key}", use_container_width=True):
                    st.session_state.current_page = page_key

            st.divider()

            # Logout button
            if st.button("Abmelden", type="secondary", use_container_width=True):
                SessionManager.logout_user()
                st.rerun()

        else:
            st.info("Bitte melden Sie sich an, um das System zu nutzen.")


def main():
    """Main application function"""
    configure_page()

    # Initialize session state
    SessionManager.init_session_state()

    # Initialize current page if not set
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'dashboard'

    # Test database connection on startup
    if 'db_initialized' not in st.session_state:
        try:
            if test_db_connection():
                init_db()
                st.session_state.db_initialized = True
            else:
                st.error("Datenbankverbindung fehlgeschlagen. Bitte überprüfen Sie die Konfiguration.")
                st.stop()
        except Exception as e:
            st.error(f"Fehler beim Initialisieren der Datenbank: {e}")
            st.stop()

    # Show login page if not authenticated
    if not SessionManager.is_authenticated():
        show_login_page()
        return

    # Verify session is still valid
    if not SessionManager.verify_session():
        st.error("Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.")
        SessionManager.logout_user()
        st.rerun()

    # Show sidebar navigation
    show_sidebar()

    # Main content area
    st.markdown('<div class="main-header"><h1>🏢 Inventory Management System</h1></div>',
                unsafe_allow_html=True)

    # Route to appropriate page
    current_page = st.session_state.get('current_page', 'dashboard')

    try:
        if current_page == 'dashboard':
            show_dashboard()
        elif current_page == 'search':
            show_search_page()
        elif current_page == 'hardware':
            show_hardware_page()
        elif current_page == 'cables':
            show_cable_inventory()
        elif current_page == 'locations':
            show_locations_page()
        elif current_page == 'analytics':
            show_analytics_page()
        elif current_page == 'reports':
            show_reports_page()
        elif current_page == 'bulk_operations':
            show_bulk_operations_page()
        elif current_page == 'qr_barcode':
            show_qr_barcode_page()
        elif current_page == 'import_export':
            show_import_export_page()
        elif current_page == 'backup':
            show_backup_page()
        elif current_page == 'audit':
            show_audit_page()
        elif current_page == 'notifications':
            show_notifications_page()
        elif current_page == 'debug':
            show_debug_page()
        elif current_page == 'settings':
            show_settings_page()
        else:
            st.error(f"Unbekannte Seite: {current_page}")

    except Exception as e:
        st.error(f"Fehler beim Laden der Seite: {e}")
        if settings.is_development:
            st.exception(e)


if __name__ == "__main__":
    main()