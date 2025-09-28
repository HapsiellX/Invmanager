"""
Audit trail views for viewing and analyzing system activities
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from typing import Optional
import json

from core.security import require_auth, require_role, SessionManager
from core.database import get_db
from .services import get_audit_service


@require_auth
@require_role("netzwerker")
def show_audit_page():
    """
    Audit trail page (requires netzwerker role or higher)
    """
    st.header("🔍 Audit Trail")

    # Get database session and service
    db = next(get_db())
    audit_service = get_audit_service(db)
    current_user = SessionManager.get_current_user()

    # Create tabs for different audit views
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📋 Aktivitäten", "📊 Statistiken", "⚠️ Kritische Ereignisse",
        "👤 Benutzer", "🔐 Anmeldungen", "📤 Export"
    ])

    with tab1:
        show_activities_tab(audit_service)

    with tab2:
        show_statistics_tab(audit_service)

    with tab3:
        show_critical_events_tab(audit_service)

    with tab4:
        show_user_activities_tab(audit_service)

    with tab5:
        show_login_activities_tab(audit_service)

    with tab6:
        show_export_tab(audit_service)

    db.close()


def show_activities_tab(audit_service):
    """Show main activities view with filtering"""
    st.subheader("📋 System Aktivitäten")

    # Filtering options
    with st.expander("🔍 Filter Optionen"):
        col1, col2, col3 = st.columns(3)

        with col1:
            # Date range filter
            start_date = st.date_input(
                "Von Datum:",
                value=date.today() - timedelta(days=7),
                key="activities_start_date"
            )
            end_date = st.date_input(
                "Bis Datum:",
                value=date.today(),
                key="activities_end_date"
            )

        with col2:
            # Resource type filter
            resource_types = ["Alle", "hardware", "cable", "location", "user", "settings"]
            selected_resource = st.selectbox(
                "Ressource Typ:",
                resource_types,
                key="activities_resource_filter"
            )

            # Action filter
            action_filter = st.text_input(
                "Aktion Filter:",
                placeholder="z.B. erstellt, gelöscht, aktualisiert",
                key="activities_action_filter"
            )

        with col3:
            # Search term
            search_term = st.text_input(
                "Suchbegriff:",
                placeholder="Benutzer, Beschreibung, etc.",
                key="activities_search"
            )

            # Results per page
            page_size = st.selectbox(
                "Einträge pro Seite:",
                [25, 50, 100, 200],
                index=1,
                key="activities_page_size"
            )

    # Apply filters
    resource_filter = None if selected_resource == "Alle" else selected_resource
    action_filter_value = action_filter if action_filter.strip() else None
    search_filter = search_term if search_term.strip() else None

    # Pagination
    if "activities_page" not in st.session_state:
        st.session_state.activities_page = 0

    # Get filtered results
    with st.spinner("Aktivitäten werden geladen..."):
        result = audit_service.get_audit_logs(
            limit=page_size,
            offset=st.session_state.activities_page * page_size,
            ressource_typ=resource_filter,
            aktion=action_filter_value,
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.min.time()),
            search_term=search_filter
        )

    # Display results summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Gesamt Einträge", result["total_count"])
    with col2:
        st.metric("Angezeigte Einträge", len(result["logs"]))
    with col3:
        current_page = st.session_state.activities_page + 1
        total_pages = (result["total_count"] + page_size - 1) // page_size
        st.metric("Seite", f"{current_page} von {total_pages}")

    # Activities table
    if result["logs"]:
        # Convert to DataFrame for better display
        df = pd.DataFrame(result["logs"])
        df['zeitstempel'] = pd.to_datetime(df['zeitstempel'])

        # Display table
        st.dataframe(
            df[[
                'zeitstempel', 'benutzer_name', 'aktion', 'ressource_typ',
                'ressource_id', 'beschreibung'
            ]],
            column_config={
                'zeitstempel': st.column_config.DatetimeColumn(
                    'Zeitstempel',
                    format="DD.MM.YYYY HH:mm:ss"
                ),
                'benutzer_name': 'Benutzer',
                'aktion': 'Aktion',
                'ressource_typ': 'Ressource Typ',
                'ressource_id': 'Ressource ID',
                'beschreibung': 'Beschreibung'
            },
            hide_index=True,
            use_container_width=True
        )

        # Detailed view for selected entry
        if st.checkbox("📄 Details für ausgewählten Eintrag anzeigen"):
            selected_id = st.selectbox(
                "Eintrag auswählen:",
                options=range(len(result["logs"])),
                format_func=lambda x: f"{result['logs'][x]['zeitstempel']} - {result['logs'][x]['aktion']}",
                key="selected_activity_detail"
            )

            if selected_id is not None:
                selected_log = result["logs"][selected_id]
                show_activity_details(selected_log)

        # Pagination controls
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("⬅️ Vorherige Seite") and st.session_state.activities_page > 0:
                st.session_state.activities_page -= 1
                st.rerun()

        with col3:
            if st.button("➡️ Nächste Seite") and (st.session_state.activities_page + 1) * page_size < result["total_count"]:
                st.session_state.activities_page += 1
                st.rerun()

        with col2:
            st.write(f"Seite {current_page} von {total_pages}")

    else:
        st.info("Keine Aktivitäten für die gewählten Filter gefunden.")


def show_activity_details(log_entry):
    """Show detailed view of a single activity"""
    st.subheader("📄 Aktivitäts Details")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Grundinformationen:**")
        st.write(f"**ID:** {log_entry['id']}")
        st.write(f"**Zeitstempel:** {log_entry['zeitstempel']}")
        st.write(f"**Benutzer:** {log_entry['benutzer_name']} ({log_entry['benutzername']})")
        st.write(f"**Rolle:** {log_entry['benutzer_rolle']}")
        st.write(f"**Aktion:** {log_entry['aktion']}")

    with col2:
        st.write("**Ressourcen Details:**")
        st.write(f"**Typ:** {log_entry['ressource_typ']}")
        st.write(f"**ID:** {log_entry['ressource_id']}")
        st.write(f"**IP Adresse:** {log_entry['ip_adresse'] or 'Nicht verfügbar'}")
        if log_entry['user_agent']:
            st.write(f"**User Agent:** {log_entry['user_agent'][:100]}...")

    st.write("**Beschreibung:**")
    st.write(log_entry['beschreibung'] or "Keine Beschreibung verfügbar")

    # Show old and new values if available
    if log_entry['alte_werte'] or log_entry['neue_werte']:
        st.write("**Datenänderungen:**")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Alte Werte:**")
            if log_entry['alte_werte']:
                try:
                    old_values = json.loads(log_entry['alte_werte']) if isinstance(log_entry['alte_werte'], str) else log_entry['alte_werte']
                    st.json(old_values)
                except:
                    st.text(str(log_entry['alte_werte']))
            else:
                st.write("Keine alten Werte")

        with col2:
            st.write("**Neue Werte:**")
            if log_entry['neue_werte']:
                try:
                    new_values = json.loads(log_entry['neue_werte']) if isinstance(log_entry['neue_werte'], str) else log_entry['neue_werte']
                    st.json(new_values)
                except:
                    st.text(str(log_entry['neue_werte']))
            else:
                st.write("Keine neuen Werte")


def show_statistics_tab(audit_service):
    """Show audit statistics and analytics"""
    st.subheader("📊 Audit Statistiken")

    # Time period selector
    period_options = {"7 Tage": 7, "30 Tage": 30, "90 Tage": 90, "365 Tage": 365}
    selected_period = st.selectbox(
        "Zeitraum auswählen:",
        list(period_options.keys()),
        index=1,
        key="stats_period"
    )
    days = period_options[selected_period]

    # Get statistics
    with st.spinner("Statistiken werden geladen..."):
        stats = audit_service.get_audit_statistics(days=days)

    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Gesamt Aktivitäten", stats["total_activities"])

    with col2:
        st.metric("Verschiedene Aktionen", len(stats["actions"]))

    with col3:
        st.metric("Aktive Benutzer", len(stats["users"]))

    with col4:
        avg_daily = stats["total_activities"] / days if days > 0 else 0
        st.metric("Ø Täglich", f"{avg_daily:.1f}")

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        # Actions pie chart
        st.subheader("🎯 Aktionen Verteilung")
        if stats["actions"]:
            action_df = pd.DataFrame(stats["actions"])
            fig_pie = px.pie(
                action_df.head(10),  # Top 10 actions
                values='count',
                names='action',
                title=f'Top 10 Aktionen - {selected_period}'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Keine Aktionsdaten verfügbar")

    with col2:
        # Resource types bar chart
        st.subheader("📦 Ressource Typen")
        if stats["resource_types"]:
            resource_df = pd.DataFrame(stats["resource_types"])
            fig_bar = px.bar(
                resource_df,
                x='type',
                y='count',
                title='Aktivitäten nach Ressource Typ',
                labels={'type': 'Ressource Typ', 'count': 'Anzahl'}
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Keine Ressourcentyp-Daten verfügbar")

    # Daily trend
    st.subheader("📈 Tägliche Aktivitäten")
    if stats["daily_trend"]:
        trend_df = pd.DataFrame(stats["daily_trend"])
        trend_df['date'] = pd.to_datetime(trend_df['date'])

        fig_trend = px.line(
            trend_df,
            x='date',
            y='count',
            title=f'Tägliche Aktivitäten - {selected_period}',
            labels={'date': 'Datum', 'count': 'Anzahl Aktivitäten'}
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Keine Trend-Daten verfügbar")

    # Top users table
    st.subheader("👥 Aktivste Benutzer")
    if stats["users"]:
        users_df = pd.DataFrame(stats["users"])
        st.dataframe(
            users_df.head(15),
            column_config={
                'username': 'Benutzername',
                'full_name': 'Vollständiger Name',
                'count': 'Aktivitäten'
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Keine Benutzerdaten verfügbar")


def show_critical_events_tab(audit_service):
    """Show critical system events"""
    st.subheader("⚠️ Kritische Ereignisse")

    st.info("Diese Seite zeigt kritische Systemereignisse wie Löschungen, Deaktivierungen und Systemänderungen.")

    # Time period selector
    days = st.selectbox(
        "Zeitraum:",
        [1, 3, 7, 14, 30],
        index=2,
        format_func=lambda x: f"{x} Tag{'e' if x > 1 else ''}",
        key="critical_period"
    )

    # Get critical activities
    with st.spinner("Kritische Ereignisse werden geladen..."):
        critical_activities = audit_service.get_critical_activities(days=days)

    if critical_activities:
        # Summary metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Kritische Ereignisse", len(critical_activities))

        with col2:
            deletion_count = sum(1 for act in critical_activities if 'gelöscht' in act['aktion'].lower())
            st.metric("Löschungen", deletion_count)

        with col3:
            deactivation_count = sum(1 for act in critical_activities if 'deaktiviert' in act['aktion'].lower())
            st.metric("Deaktivierungen", deactivation_count)

        # Critical events table
        df = pd.DataFrame(critical_activities)
        df['zeitstempel'] = pd.to_datetime(df['zeitstempel'])

        st.dataframe(
            df[[
                'zeitstempel', 'benutzer_name', 'aktion', 'ressource_typ',
                'ressource_id', 'beschreibung'
            ]],
            column_config={
                'zeitstempel': st.column_config.DatetimeColumn(
                    'Zeitstempel',
                    format="DD.MM.YYYY HH:mm:ss"
                ),
                'benutzer_name': 'Benutzer',
                'aktion': 'Kritische Aktion',
                'ressource_typ': 'Ressource Typ',
                'ressource_id': 'Ressource ID',
                'beschreibung': 'Beschreibung'
            },
            hide_index=True,
            use_container_width=True
        )

        # Charts
        if len(critical_activities) > 1:
            col1, col2 = st.columns(2)

            with col1:
                # Actions breakdown
                action_counts = df['aktion'].value_counts()
                fig_actions = px.bar(
                    x=action_counts.values,
                    y=action_counts.index,
                    orientation='h',
                    title='Kritische Aktionen Verteilung',
                    labels={'x': 'Anzahl', 'y': 'Aktion'}
                )
                st.plotly_chart(fig_actions, use_container_width=True)

            with col2:
                # Users involved
                user_counts = df['benutzer_name'].value_counts()
                fig_users = px.pie(
                    values=user_counts.values,
                    names=user_counts.index,
                    title='Benutzer bei kritischen Ereignissen'
                )
                st.plotly_chart(fig_users, use_container_width=True)

    else:
        st.success(f"✅ Keine kritischen Ereignisse in den letzten {days} Tag{'en' if days > 1 else ''} gefunden.")


def show_user_activities_tab(audit_service):
    """Show user-specific activities"""
    st.subheader("👤 Benutzer Aktivitäten")

    # Get all users for selection
    db = next(get_db())
    from database.models.user import User
    users = db.query(User).filter(User.ist_aktiv == True).all()
    db.close()

    if not users:
        st.warning("Keine aktiven Benutzer gefunden.")
        return

    # User selection
    user_options = {f"{user.vorname} {user.nachname} ({user.benutzername})": user.id for user in users}
    selected_user_display = st.selectbox(
        "Benutzer auswählen:",
        list(user_options.keys()),
        key="user_activities_select"
    )
    selected_user_id = user_options[selected_user_display]

    # Time period
    days = st.selectbox(
        "Zeitraum:",
        [7, 14, 30, 60, 90],
        index=2,
        format_func=lambda x: f"{x} Tage",
        key="user_activities_period"
    )

    # Get user activity
    with st.spinner("Benutzer Aktivitäten werden geladen..."):
        user_activity = audit_service.get_user_activity(selected_user_id, days=days)

    if "error" in user_activity:
        st.error(user_activity["error"])
        return

    # Display user info
    user_info = user_activity["user"]
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Benutzer", user_info["full_name"])
    with col2:
        st.metric("Benutzername", user_info["username"])
    with col3:
        st.metric("Rolle", user_info["role"])
    with col4:
        st.metric("Gesamt Aktivitäten", user_activity["total_activities"])

    if user_activity["total_activities"] > 0:
        # Charts
        col1, col2 = st.columns(2)

        with col1:
            # Action breakdown
            st.subheader("🎯 Aktionen Verteilung")
            if user_activity["action_breakdown"]:
                action_df = pd.DataFrame(user_activity["action_breakdown"])
                fig_actions = px.pie(
                    action_df,
                    values='count',
                    names='action',
                    title='Aktionen des Benutzers'
                )
                st.plotly_chart(fig_actions, use_container_width=True)

        with col2:
            # Resource breakdown
            st.subheader("📦 Ressourcen Verteilung")
            if user_activity["resource_breakdown"]:
                resource_df = pd.DataFrame(user_activity["resource_breakdown"])
                fig_resources = px.bar(
                    resource_df,
                    x='type',
                    y='count',
                    title='Bearbeitete Ressourcen',
                    labels={'type': 'Ressource Typ', 'count': 'Anzahl'}
                )
                st.plotly_chart(fig_resources, use_container_width=True)

        # Daily activity trend
        st.subheader("📈 Tägliche Aktivitäten")
        if user_activity["daily_activity"]:
            daily_df = pd.DataFrame(user_activity["daily_activity"])
            daily_df['date'] = pd.to_datetime(daily_df['date'])

            fig_daily = px.line(
                daily_df,
                x='date',
                y='count',
                title='Tägliche Aktivitäten des Benutzers',
                labels={'date': 'Datum', 'count': 'Anzahl Aktivitäten'}
            )
            st.plotly_chart(fig_daily, use_container_width=True)

        # Recent activities table
        st.subheader("🔄 Neueste Aktivitäten")
        if user_activity["recent_activities"]:
            recent_df = pd.DataFrame(user_activity["recent_activities"])
            recent_df['zeitstempel'] = pd.to_datetime(recent_df['zeitstempel'])

            st.dataframe(
                recent_df,
                column_config={
                    'zeitstempel': st.column_config.DatetimeColumn(
                        'Zeitstempel',
                        format="DD.MM.YYYY HH:mm:ss"
                    ),
                    'aktion': 'Aktion',
                    'ressource_typ': 'Ressource Typ',
                    'beschreibung': 'Beschreibung'
                },
                hide_index=True,
                use_container_width=True
            )

    else:
        st.info(f"Keine Aktivitäten für diesen Benutzer in den letzten {days} Tagen gefunden.")


def show_login_activities_tab(audit_service):
    """Show login and authentication activities"""
    st.subheader("🔐 Anmelde Aktivitäten")

    # Time period
    days = st.selectbox(
        "Zeitraum:",
        [7, 14, 30, 60, 90],
        index=2,
        format_func=lambda x: f"{x} Tage",
        key="login_activities_period"
    )

    # Get login activities
    with st.spinner("Anmelde Aktivitäten werden geladen..."):
        login_activities = audit_service.get_login_activities(days=days)

    if login_activities:
        st.metric("Anmelde Ereignisse", len(login_activities))

        # Login activities table
        df = pd.DataFrame(login_activities)
        df['zeitstempel'] = pd.to_datetime(df['zeitstempel'])

        st.dataframe(
            df,
            column_config={
                'zeitstempel': st.column_config.DatetimeColumn(
                    'Zeitstempel',
                    format="DD.MM.YYYY HH:mm:ss"
                ),
                'benutzer_name': 'Benutzer',
                'benutzername': 'Benutzername',
                'aktion': 'Aktion',
                'ip_adresse': 'IP Adresse',
                'user_agent': 'User Agent'
            },
            hide_index=True,
            use_container_width=True
        )

        # Analytics
        if len(login_activities) > 1:
            col1, col2 = st.columns(2)

            with col1:
                # Users by login frequency
                user_counts = df['benutzer_name'].value_counts()
                fig_users = px.bar(
                    x=user_counts.values,
                    y=user_counts.index,
                    orientation='h',
                    title='Anmeldungen pro Benutzer',
                    labels={'x': 'Anzahl Anmeldungen', 'y': 'Benutzer'}
                )
                st.plotly_chart(fig_users, use_container_width=True)

            with col2:
                # Daily login trend
                df['date'] = df['zeitstempel'].dt.date
                daily_logins = df.groupby('date').size().reset_index(name='count')
                daily_logins['date'] = pd.to_datetime(daily_logins['date'])

                fig_daily = px.line(
                    daily_logins,
                    x='date',
                    y='count',
                    title='Tägliche Anmeldungen',
                    labels={'date': 'Datum', 'count': 'Anzahl Anmeldungen'}
                )
                st.plotly_chart(fig_daily, use_container_width=True)

    else:
        st.info(f"Keine Anmelde Aktivitäten in den letzten {days} Tagen gefunden.")


def show_export_tab(audit_service):
    """Show audit export functionality"""
    st.subheader("📤 Audit Export")

    st.info("Exportieren Sie Audit-Daten für externe Analyse oder Archivierung.")

    # Export parameters
    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input(
            "Von Datum:",
            value=date.today() - timedelta(days=30),
            key="export_start_date"
        )
        end_date = st.date_input(
            "Bis Datum:",
            value=date.today(),
            key="export_end_date"
        )

    with col2:
        export_format = st.selectbox(
            "Export Format:",
            ["CSV", "JSON"],
            key="export_format"
        )

    # Export button
    if st.button("📥 Audit Daten exportieren", key="export_audit"):
        if start_date > end_date:
            st.error("Start-Datum muss vor End-Datum liegen.")
        else:
            with st.spinner("Export wird vorbereitet..."):
                try:
                    export_data = audit_service.export_audit_logs(
                        start_date=datetime.combine(start_date, datetime.min.time()),
                        end_date=datetime.combine(end_date, datetime.min.time()),
                        format_type=export_format.lower()
                    )

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"audit_export_{start_date}_{end_date}_{timestamp}.{export_format.lower()}"

                    mime_type = "text/csv" if export_format == "CSV" else "application/json"

                    st.download_button(
                        label=f"📥 {export_format} Export herunterladen",
                        data=export_data,
                        file_name=filename,
                        mime=mime_type,
                        key="download_export"
                    )

                    st.success("Export erfolgreich erstellt!")

                except Exception as e:
                    st.error(f"Fehler beim Export: {str(e)}")

    # Export information
    with st.expander("ℹ️ Export Informationen"):
        st.markdown("""
        **CSV Export:**
        - Tabellenformat für Excel/LibreOffice
        - Einfache Filterung und Sortierung
        - Kompakt und lesbar

        **JSON Export:**
        - Vollständige Datenstruktur
        - Alle Metadaten enthalten
        - Ideal für automatisierte Verarbeitung

        **Verwendungszwecke:**
        - Compliance und Audit-Berichte
        - Forensische Analyse
        - Langzeit-Archivierung
        - Integration in externe Systeme
        """)

    # Quick export presets
    st.subheader("🚀 Schnell-Export")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📊 Letzte 7 Tage (CSV)", key="quick_7_csv"):
            start = date.today() - timedelta(days=7)
            end = date.today()
            export_quick(audit_service, start, end, "csv", "7_tage")

    with col2:
        if st.button("📈 Letzter Monat (CSV)", key="quick_30_csv"):
            start = date.today() - timedelta(days=30)
            end = date.today()
            export_quick(audit_service, start, end, "csv", "30_tage")

    with col3:
        if st.button("📦 Komplett (JSON)", key="quick_all_json"):
            # Export all available data (last 365 days)
            start = date.today() - timedelta(days=365)
            end = date.today()
            export_quick(audit_service, start, end, "json", "komplett")


def export_quick(audit_service, start_date, end_date, format_type, period_name):
    """Quick export function"""
    try:
        with st.spinner(f"Export {period_name} wird vorbereitet..."):
            export_data = audit_service.export_audit_logs(
                start_date=datetime.combine(start_date, datetime.min.time()),
                end_date=datetime.combine(end_date, datetime.min.time()),
                format_type=format_type
            )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"audit_{period_name}_{timestamp}.{format_type}"

            mime_type = "text/csv" if format_type == "csv" else "application/json"

            st.download_button(
                label=f"📥 {period_name.title()} Export herunterladen",
                data=export_data,
                file_name=filename,
                mime=mime_type,
                key=f"download_{period_name}_{timestamp}"
            )

            st.success(f"Export {period_name} erfolgreich erstellt!")

    except Exception as e:
        st.error(f"Fehler beim Schnell-Export: {str(e)}")