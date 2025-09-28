"""
Dashboard views for main system overview
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any

from core.security import require_auth
from core.database import get_db


@require_auth
def show_dashboard():
    """
    Main dashboard with overview and health checks
    """
    st.header("📊 Dashboard")

    # Notifications widget at the top
    show_notifications_widget()

    # Quick stats
    show_quick_stats()

    # Health checks
    show_health_checks()

    # Recent activity
    show_recent_activity()


def show_notifications_widget():
    """Display notifications widget on dashboard"""
    try:
        from notifications.views import show_dashboard_notifications_widget
        show_dashboard_notifications_widget()
    except:
        # If notifications module fails, continue without it
        pass


def show_quick_stats():
    """Display quick statistics"""
    from hardware.services import get_hardware_service
    from cable.services import get_cable_service
    from database.models.location import Location

    # Use separate database sessions for each service
    hardware_service = get_hardware_service()
    cable_service = get_cable_service()

    # Use a fresh session for location count
    db = next(get_db())
    location_count = db.query(Location).filter(Location.ist_aktiv == True).count()
    db.close()

    # Get real data
    hardware_summary = hardware_service.get_inventory_summary()
    total_hardware = hardware_summary['total_hardware']

    # Get cable summary
    cable_summary = cable_service.get_inventory_summary()
    total_cable_types = cable_summary['total_cables']
    total_cable_stock = cable_summary['total_stock']


    # Get low stock cables (health status niedrig or kritisch)
    low_stock_cables = cable_summary['by_health'].get('kritisch', 0) + cable_summary['by_health'].get('niedrig', 0)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
        <h3>Hardware Items</h3>
        <h2 style="color: #1f77b4;">{total_hardware}</h2>
        <small>Total inventory</small>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
        <h3>Kabel Arten</h3>
        <h2 style="color: #ff7f0e;">{total_cable_types}</h2>
        <small>Verschiedene Kabel</small>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
        <h3>Locations</h3>
        <h2 style="color: #2ca02c;">{location_count}</h2>
        <small>Active locations</small>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        color = "#d62728" if low_stock_cables > 0 else "#2ca02c"
        st.markdown(f"""
        <div class="metric-card">
        <h3>Low Stock Items</h3>
        <h2 style="color: {color};">{low_stock_cables}</h2>
        <small>Need attention</small>
        </div>
        """, unsafe_allow_html=True)


def show_health_checks():
    """Display health check alerts"""
    from hardware.services import get_hardware_service
    from cable.services import get_cable_service

    st.subheader("🚨 Health Checks")

    # Use separate database sessions
    hardware_service = get_hardware_service()
    cable_service = get_cable_service()

    # Check hardware by category
    hardware_summary = hardware_service.get_inventory_summary()
    hardware_alerts = []

    for kategorie, count in hardware_summary['by_category'].items():
        if count == 0:
            hardware_alerts.append(("kritisch", f"{kategorie} inventory ist leer"))
        elif count <= 2:
            hardware_alerts.append(("niedrig", f"{kategorie} hat nur {count} Geräte"))

    # Check cable inventory
    cable_alerts = []
    critical_cables = cable_service.get_low_stock_cables("kritisch")
    low_cables = cable_service.get_low_stock_cables("niedrig")

    for cable in critical_cables:
        cable_alerts.append(("kritisch", f"Kabel {cable.bezeichnung} ist leer"))

    for cable in low_cables:
        cable_alerts.append(("niedrig", f"Kabel {cable.bezeichnung} hat niedrigen Bestand ({cable.menge} Stück)"))

    # Display alerts
    all_alerts = [("Hardware", hardware_alerts), ("Kabel", cable_alerts)]

    if not any(alerts for _, alerts in all_alerts):
        st.markdown("""
        <div class="alert-success">
        <strong>✅ Alles OK:</strong> Alle Bestände sind ausreichend
        </div>
        """, unsafe_allow_html=True)
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Hardware Alerts:**")
            if hardware_alerts:
                for level, message in hardware_alerts:
                    alert_class = "alert-critical" if level == "kritisch" else "alert-warning"
                    st.markdown(f"""
                    <div class="{alert_class}">
                    <strong>{level.title()}:</strong> {message}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="alert-success">
                <strong>OK:</strong> Hardware Bestände ausreichend
                </div>
                """, unsafe_allow_html=True)

        with col2:
            st.write("**Kabel Alerts:**")
            if cable_alerts:
                for level, message in cable_alerts:
                    alert_class = "alert-critical" if level == "kritisch" else "alert-warning"
                    st.markdown(f"""
                    <div class="{alert_class}">
                    <strong>{level.title()}:</strong> {message}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="alert-success">
                <strong>OK:</strong> Kabel Bestände ausreichend
                </div>
                """, unsafe_allow_html=True)


def show_recent_activity():
    """Display recent system activity"""
    st.subheader("📋 Letzte Aktivitäten")

    # Sample activity data
    activity_data = [
        {"Zeit": "10:30", "Benutzer": "Max Mustermann", "Aktion": "Hardware hinzugefügt", "Item": "Cisco Switch"},
        {"Zeit": "09:15", "Benutzer": "Anna Schmidt", "Aktion": "Kabel bestand aktualisiert", "Item": "Cat6 Cable"},
        {"Zeit": "08:45", "Benutzer": "Tom Weber", "Aktion": "Login", "Item": "-"},
    ]

    df = pd.DataFrame(activity_data)
    st.dataframe(df, use_container_width=True, hide_index=True)