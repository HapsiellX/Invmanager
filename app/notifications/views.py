"""
Notification views for displaying alerts and managing notification settings
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any

from core.security import require_auth, require_role, SessionManager
from core.database import get_db
from .services import get_notification_service, NotificationPriority, NotificationType


@require_auth
def show_notifications_page():
    """
    Main notifications page
    """
    st.header("🔔 Benachrichtigungen")

    # Get database session and service
    try:
        db = next(get_db())
        notification_service = get_notification_service(db)
    except Exception as e:
        st.error(f"❌ Datenbankfehler: {e}")
        st.info("Das Benachrichtigungssystem ist momentan nicht verfügbar. Bitte versuchen Sie es später erneut.")
        return

    current_user = SessionManager.get_current_user()
    user_role = SessionManager.get_user_role()

    # Debug: Check current_user structure
    if not current_user:
        st.error("❌ Keine Benutzerinformationen gefunden. Bitte melden Sie sich erneut an.")
        db.close()
        return

    if not isinstance(current_user, dict):
        st.error(f"❌ Ungültige Benutzerinformationen (Typ: {type(current_user)}). Bitte melden Sie sich erneut an.")
        db.close()
        return

    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        "🔔 Aktuelle Benachrichtigungen", "📊 Übersicht", "⚙️ Einstellungen"
    ])

    with tab1:
        show_current_notifications(notification_service, user_role)

    with tab2:
        show_notification_overview(notification_service, user_role)

    with tab3:
        show_notification_settings(notification_service, current_user)

    db.close()


def show_current_notifications(notification_service, user_role: str):
    """Display current notifications"""
    st.subheader("📋 Aktuelle Benachrichtigungen")

    # Get all notifications with error handling
    try:
        notifications = notification_service.get_all_notifications(user_role)
    except Exception as e:
        st.error(f"❌ Fehler beim Laden der Benachrichtigungen: {e}")
        if st.checkbox("🔍 Debug Details anzeigen", key="debug_notifications"):
            st.code(f"""
Fehlertyp: {type(e).__name__}
Fehlermeldung: {str(e)}
User Role: {user_role}
            """)
            import traceback
            st.code(traceback.format_exc())
        return

    if not notifications:
        st.success("🎉 Keine aktuellen Benachrichtigungen!")
        return

    # Filter options
    col1, col2, col3 = st.columns(3)

    with col1:
        priority_filter = st.selectbox(
            "Nach Priorität filtern:",
            ["Alle", "Kritisch", "Hoch", "Mittel", "Niedrig"],
            key="notification_priority_filter"
        )

    with col2:
        type_filter = st.selectbox(
            "Nach Typ filtern:",
            ["Alle", "Bestandswarnungen", "Garantie", "Kritische Aktionen", "System"],
            key="notification_type_filter"
        )

    with col3:
        show_read = st.checkbox("Gelesene anzeigen", value=True, key="show_read_notifications")

    # Apply filters
    filtered_notifications = notifications.copy()

    if priority_filter != "Alle":
        priority_map = {
            "Kritisch": NotificationPriority.CRITICAL,
            "Hoch": NotificationPriority.HIGH,
            "Mittel": NotificationPriority.MEDIUM,
            "Niedrig": NotificationPriority.LOW
        }
        filtered_notifications = [
            n for n in filtered_notifications
            if n.get('priority') == priority_map.get(priority_filter)
        ]

    if type_filter != "Alle":
        type_map = {
            "Bestandswarnungen": [NotificationType.STOCK_LOW, NotificationType.STOCK_OUT, NotificationType.STOCK_HIGH],
            "Garantie": [NotificationType.WARRANTY_EXPIRING, NotificationType.WARRANTY_EXPIRED],
            "Kritische Aktionen": [NotificationType.CRITICAL_ACTION],
            "System": [NotificationType.SYSTEM_ALERT]
        }
        filter_types = type_map.get(type_filter, [])
        filtered_notifications = [
            n for n in filtered_notifications
            if n.get('type') in filter_types
        ]

    # Display notifications
    st.write(f"**{len(filtered_notifications)} von {len(notifications)} Benachrichtigungen**")

    for notification in filtered_notifications:
        display_notification_card(notification)


def display_notification_card(notification: Dict[str, Any]):
    """Display a single notification as a card"""
    priority = notification.get('priority', NotificationPriority.LOW)

    # Determine color based on priority
    if priority == NotificationPriority.CRITICAL:
        border_color = "#dc3545"  # Red
        bg_color = "#f8d7da"
    elif priority == NotificationPriority.HIGH:
        border_color = "#fd7e14"  # Orange
        bg_color = "#fff3cd"
    elif priority == NotificationPriority.MEDIUM:
        border_color = "#ffc107"  # Yellow
        bg_color = "#fff9c4"
    else:
        border_color = "#6c757d"  # Gray
        bg_color = "#f8f9fa"

    with st.container():
        # Custom CSS for notification card
        st.markdown(f"""
        <div style="
            border-left: 4px solid {border_color};
            background-color: {bg_color};
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
        """, unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns([1, 6, 2, 1])

        with col1:
            st.write(f"## {notification.get('icon', '🔔')}")

        with col2:
            st.write(f"**{notification.get('title', 'Benachrichtigung')}**")
            st.write(notification.get('message', ''))

            # Show details if available
            details = notification.get('details', {})
            if details:
                with st.expander("📋 Details"):
                    for key, value in details.items():
                        if key != 'password':  # Don't show sensitive data
                            st.write(f"**{key.replace('_', ' ').title()}:** {value}")

        with col3:
            timestamp = notification.get('timestamp', datetime.now())
            if isinstance(timestamp, datetime):
                st.write(f"**{timestamp.strftime('%d.%m.%Y')}**")
                st.write(f"{timestamp.strftime('%H:%M')}")
            else:
                st.write("Keine Zeitangabe")

            priority_text = priority.value.title() if isinstance(priority, NotificationPriority) else str(priority)
            st.write(f"**Priorität:** {priority_text}")

        with col4:
            # Action buttons
            if st.button("✅", key=f"mark_read_{notification.get('id')}", help="Als gelesen markieren"):
                st.success("Als gelesen markiert!")

            if notification.get('action_url'):
                if st.button("🔗", key=f"goto_{notification.get('id')}", help="Zur Quelle"):
                    st.info("Navigation zur Quelle...")

        st.markdown("</div>", unsafe_allow_html=True)


def show_notification_overview(notification_service, user_role: str):
    """Show notification statistics and overview"""
    st.subheader("📊 Benachrichtigungs-Übersicht")

    # Get notification summary
    summary = notification_service.get_notification_summary(user_role)

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Gesamt Benachrichtigungen", summary['total_count'])

    with col2:
        critical_count = summary['by_priority'].get('critical', 0)
        high_count = summary['by_priority'].get('high', 0)
        urgent_count = critical_count + high_count
        st.metric("Dringend", urgent_count, delta=f"+{summary['recent_count']}")

    with col3:
        st.metric("Letzte 24h", summary['recent_count'])

    with col4:
        # Calculate average per day (last 7 days)
        avg_per_day = summary['total_count'] / 7 if summary['total_count'] > 0 else 0
        st.metric("Ø pro Tag", f"{avg_per_day:.1f}")

    # Priority breakdown
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🎯 Nach Priorität")
        priority_data = []
        priority_colors = {
            'critical': '#dc3545',
            'high': '#fd7e14',
            'medium': '#ffc107',
            'low': '#6c757d'
        }

        for priority, count in summary['by_priority'].items():
            if count > 0:
                priority_data.append({
                    'Priorität': priority.title(),
                    'Anzahl': count,
                    'Farbe': priority_colors.get(priority, '#6c757d')
                })

        if priority_data:
            df_priority = pd.DataFrame(priority_data)
            st.dataframe(
                df_priority[['Priorität', 'Anzahl']],
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("Keine Benachrichtigungen nach Priorität")

    with col2:
        st.subheader("📋 Nach Typ")
        type_labels = {
            'stock_low': 'Niedriger Bestand',
            'stock_out': 'Ausverkauft',
            'stock_high': 'Überbestand',
            'warranty_expiring': 'Garantie läuft ab',
            'warranty_expired': 'Garantie abgelaufen',
            'critical_action': 'Kritische Aktion',
            'system_alert': 'System Warnung'
        }

        type_data = []
        for notif_type, count in summary['by_type'].items():
            if count > 0:
                type_data.append({
                    'Typ': type_labels.get(notif_type, notif_type.replace('_', ' ').title()),
                    'Anzahl': count
                })

        if type_data:
            df_type = pd.DataFrame(type_data)
            st.dataframe(
                df_type,
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("Keine Benachrichtigungen nach Typ")

    # Trends (if available)
    st.subheader("📈 Trends")
    trends = notification_service.get_notification_trends(30)

    trend_col1, trend_col2, trend_col3 = st.columns(3)

    with trend_col1:
        stock_trend = trends.get('stock_alerts_trend', 'stable')
        trend_icon = "📈" if stock_trend == "increasing" else "📉" if stock_trend == "decreasing" else "➡️"
        st.metric("Bestandswarnungen", stock_trend.title(), delta=trend_icon)

    with trend_col2:
        warranty_trend = trends.get('warranty_alerts_trend', 'stable')
        trend_icon = "📈" if warranty_trend == "increasing" else "📉" if warranty_trend == "decreasing" else "➡️"
        st.metric("Garantie Warnungen", warranty_trend.title(), delta=trend_icon)

    with trend_col3:
        critical_trend = trends.get('critical_actions_trend', 'stable')
        trend_icon = "📈" if critical_trend == "increasing" else "📉" if critical_trend == "decreasing" else "➡️"
        st.metric("Kritische Aktionen", critical_trend.title(), delta=trend_icon)

    # Recent activity timeline
    st.subheader("⏰ Kürzliche Aktivitäten")

    # Get notifications from last 7 days
    try:
        all_notifications = notification_service.get_all_notifications(user_role)
        if not isinstance(all_notifications, (list, tuple)):
            st.warning("Benachrichtigungsdaten haben ein unerwartetes Format")
            all_notifications = []
    except Exception as e:
        st.error(f"Fehler beim Laden der Benachrichtigungen: {e}")
        all_notifications = []

    recent_cutoff = datetime.now() - timedelta(days=7)

    recent_notifications = []
    for n in all_notifications:
        try:
            # Ensure notification is a dictionary
            if not isinstance(n, dict):
                continue

            # Get timestamp safely
            timestamp = n.get('timestamp', datetime.min)

            # Ensure timestamp is a datetime object
            if isinstance(timestamp, str):
                # Try to parse string timestamp
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif not isinstance(timestamp, datetime):
                # Skip if not a proper timestamp
                continue

            if timestamp >= recent_cutoff:
                recent_notifications.append(n)
        except (ValueError, AttributeError, TypeError):
            # Skip malformed notifications
            continue

    if recent_notifications:
        # Group by date
        daily_counts = {}
        for notification in recent_notifications:
            try:
                # Ensure notification is a dictionary
                if not isinstance(notification, dict):
                    continue

                # Get timestamp safely
                timestamp = notification.get('timestamp', datetime.now())

                # Ensure timestamp is a datetime object
                if isinstance(timestamp, str):
                    # Try to parse string timestamp
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                elif not isinstance(timestamp, datetime):
                    # If it's not a datetime, use current time
                    timestamp = datetime.now()

                date_key = timestamp.date()
                daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
            except (ValueError, AttributeError, TypeError):
                # Skip malformed notifications
                continue

        # Create timeline data
        timeline_data = []
        for i in range(7):
            date_check = (datetime.now() - timedelta(days=i)).date()
            count = daily_counts.get(date_check, 0)
            timeline_data.append({
                'Datum': date_check.strftime('%d.%m'),
                'Benachrichtigungen': count
            })

        timeline_df = pd.DataFrame(timeline_data)
        st.line_chart(timeline_df.set_index('Datum'))

    else:
        st.info("Keine kürzlichen Benachrichtigungen in den letzten 7 Tagen")


def show_notification_settings(notification_service, current_user):
    """Show notification settings"""
    st.subheader("⚙️ Benachrichtigungs-Einstellungen")

    # Check if current_user is valid
    if not current_user or not isinstance(current_user, dict) or 'id' not in current_user:
        st.error("Benutzerinformationen nicht verfügbar. Bitte melden Sie sich erneut an.")
        return

    # Get current preferences
    preferences = notification_service.get_user_notification_preferences(current_user['id'])

    st.write("**Konfigurieren Sie, welche Benachrichtigungen Sie erhalten möchten:**")

    with st.form("notification_preferences"):
        col1, col2 = st.columns(2)

        with col1:
            st.write("**📱 Benachrichtigungstypen**")

            stock_alerts = st.checkbox(
                "Bestandswarnungen",
                value=preferences.get('stock_alerts', True),
                help="Benachrichtigungen bei niedrigem oder hohem Bestand"
            )

            warranty_alerts = st.checkbox(
                "Garantie-Warnungen",
                value=preferences.get('warranty_alerts', True),
                help="Benachrichtigungen bei ablaufenden Garantien"
            )

            critical_alerts = st.checkbox(
                "Kritische Ereignisse",
                value=preferences.get('critical_alerts', True),
                help="Benachrichtigungen bei kritischen Systemaktionen"
            )

            if SessionManager.get_user_role() == "admin":
                system_alerts = st.checkbox(
                    "System-Warnungen",
                    value=preferences.get('system_alerts', False),
                    help="Systemweite Warnungen und Anomalien"
                )
            else:
                system_alerts = False

        with col2:
            st.write("**📬 Benachrichtigungskanäle**")

            in_app_notifications = st.checkbox(
                "In-App Benachrichtigungen",
                value=preferences.get('in_app_notifications', True),
                help="Benachrichtigungen in der Anwendung anzeigen"
            )

            email_notifications = st.checkbox(
                "E-Mail Benachrichtigungen",
                value=preferences.get('email_notifications', False),
                help="Benachrichtigungen per E-Mail senden"
            )

            # Additional settings
            st.write("**⚙️ Erweiterte Einstellungen**")

            notification_frequency = st.selectbox(
                "Benachrichtigungsfrequenz:",
                ["Sofort", "Täglich", "Wöchentlich"],
                index=0
            )

            quiet_hours = st.checkbox(
                "Ruhezeiten aktivieren",
                value=False,
                help="Keine Benachrichtigungen zwischen 22:00 und 8:00 Uhr"
            )

        # Save button
        if st.form_submit_button("💾 Einstellungen speichern", type="primary"):
            new_preferences = {
                'stock_alerts': stock_alerts,
                'warranty_alerts': warranty_alerts,
                'critical_alerts': critical_alerts,
                'system_alerts': system_alerts,
                'in_app_notifications': in_app_notifications,
                'email_notifications': email_notifications,
                'notification_frequency': notification_frequency,
                'quiet_hours': quiet_hours
            }

            if notification_service.update_user_notification_preferences(current_user['id'], new_preferences):
                st.success("✅ Einstellungen erfolgreich gespeichert!")
            else:
                st.error("❌ Fehler beim Speichern der Einstellungen")

    # Notification preview
    st.subheader("👀 Vorschau")

    if st.button("🔔 Test-Benachrichtigung senden"):
        st.info("""
        **Test-Benachrichtigung**
        Dies ist eine Beispiel-Benachrichtigung zur Überprüfung Ihrer Einstellungen.

        **Typ:** System-Test
        **Priorität:** Niedrig
        **Zeitstempel:** {timestamp}
        """.format(timestamp=datetime.now().strftime('%d.%m.%Y %H:%M:%S')))

    # Help section
    with st.expander("❓ Hilfe zu Benachrichtigungen"):
        st.markdown("""
        **Benachrichtigungstypen:**

        - **Bestandswarnungen:** Informieren Sie über niedrige, hohe oder fehlende Bestände
        - **Garantie-Warnungen:** Erinnern Sie an ablaufende oder abgelaufene Garantien
        - **Kritische Ereignisse:** Benachrichtigen Sie über wichtige Systemaktionen wie Löschungen
        - **System-Warnungen:** Melden ungewöhnliche Aktivitäten oder Systemprobleme

        **Prioritäten:**

        - **Kritisch:** Sofortige Aufmerksamkeit erforderlich
        - **Hoch:** Wichtig, sollte bald bearbeitet werden
        - **Mittel:** Standard-Priorität
        - **Niedrig:** Informativ, keine sofortige Aktion nötig

        **Tipps:**

        - Aktivieren Sie E-Mail-Benachrichtigungen für kritische Ereignisse
        - Nutzen Sie Ruhezeiten, um Störungen zu vermeiden
        - Überprüfen Sie regelmäßig Ihre Benachrichtigungen
        """)


def show_notification_badge():
    """Show notification badge for navigation"""
    # This function can be called from the main navigation to show unread count
    db = next(get_db())
    notification_service = get_notification_service(db)
    user_role = SessionManager.get_user_role()

    notifications = notification_service.get_all_notifications(user_role)
    urgent_notifications = [
        n for n in notifications
        if n.get('priority') in [NotificationPriority.CRITICAL, NotificationPriority.HIGH]
    ]

    db.close()

    return len(urgent_notifications)


def show_dashboard_notifications_widget():
    """Show notifications widget for dashboard"""
    st.subheader("🔔 Aktuelle Warnungen")

    db = next(get_db())
    notification_service = get_notification_service(db)
    user_role = SessionManager.get_user_role()

    # Get top 3 priority notifications for dashboard
    dashboard_alerts = notification_service.get_dashboard_alerts(user_role, limit=3)

    if dashboard_alerts:
        for alert in dashboard_alerts:
            priority = alert.get('priority', NotificationPriority.LOW)

            if priority == NotificationPriority.CRITICAL:
                st.error(f"🚨 **{alert.get('title')}** - {alert.get('message')}")
            elif priority == NotificationPriority.HIGH:
                st.warning(f"⚠️ **{alert.get('title')}** - {alert.get('message')}")
            else:
                st.info(f"ℹ️ **{alert.get('title')}** - {alert.get('message')}")

        if st.button("🔔 Alle Benachrichtigungen anzeigen"):
            st.session_state.current_page = 'notifications'
            st.rerun()

    else:
        st.success("✅ Keine dringenden Benachrichtigungen")

    db.close()