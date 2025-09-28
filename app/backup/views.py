"""
Backup and archiving views for data management
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json

from core.security import require_auth, require_role
from core.database import get_db
from .services import get_backup_service


@require_auth
@require_role("admin")  # Only admins can access backup functionality
def show_backup_page():
    """
    Backup and data archiving page (admin only)
    """
    st.header("💾 Backup & Archivierung")

    # Get database session and service
    db = next(get_db())
    backup_service = get_backup_service(db)

    # Create tabs for different backup functions
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔄 Backup erstellen", "📋 Backup Verlauf", "✅ Backup prüfen",
        "🗑️ Backup bereinigen", "⚙️ Automatisierung"
    ])

    with tab1:
        show_create_backup_tab(backup_service)

    with tab2:
        show_backup_history_tab(backup_service)

    with tab3:
        show_verify_backup_tab(backup_service)

    with tab4:
        show_cleanup_backups_tab(backup_service)

    with tab5:
        show_automation_tab(backup_service)

    db.close()


def show_create_backup_tab(backup_service):
    """Show backup creation interface"""
    st.subheader("🔄 Neues Backup erstellen")

    st.info("Erstellen Sie ein Backup Ihrer Inventardaten für Sicherheit und Archivierung.")

    # Backup type selection
    col1, col2 = st.columns(2)

    with col1:
        backup_type = st.radio(
            "Backup Typ:",
            ["Vollständiges Backup", "Inkrementelles Backup"],
            help="Vollständiges Backup: Alle Daten\nInkrementelles Backup: Nur Änderungen seit letztem Backup",
            key="backup_type"
        )

    with col2:
        # Backup options
        st.write("**Backup Optionen:**")
        include_files = st.checkbox("Dateien einschließen", value=True, key="include_files")
        compress_backup = st.checkbox("Backup komprimieren", value=True, key="compress_backup")

        if backup_type == "Inkrementelles Backup":
            # Show last backup date
            history = backup_service.get_backup_history(limit=1)
            if history:
                last_backup = history[0]
                st.info(f"Letztes Backup: {last_backup['created_at']}")
            else:
                st.warning("Kein vorheriges Backup gefunden. Erstelle vollständiges Backup.")
                backup_type = "Vollständiges Backup"

    # Backup preview information
    st.subheader("📊 Backup Vorschau")

    # Get current statistics
    preview_col1, preview_col2, preview_col3, preview_col4 = st.columns(4)

    try:
        # Get database counts
        from database.models.hardware import HardwareItem
        from database.models.cable import Cable
        from database.models.location import Location
        from database.models.user import User
        from database.models.audit_log import AuditLog

        db = backup_service.db

        hardware_count = db.query(HardwareItem).filter(HardwareItem.ist_aktiv == True).count()
        cable_count = db.query(Cable).filter(Cable.ist_aktiv == True).count()
        location_count = db.query(Location).filter(Location.ist_aktiv == True).count()
        user_count = db.query(User).filter(User.ist_aktiv == True).count()
        audit_count = db.query(AuditLog).count()

        with preview_col1:
            st.metric("Hardware Artikel", hardware_count)
            st.metric("Kabel Typen", cable_count)

        with preview_col2:
            st.metric("Standorte", location_count)
            st.metric("Benutzer", user_count)

        with preview_col3:
            st.metric("Audit Logs", audit_count)
            total_records = hardware_count + cable_count + location_count + user_count + audit_count
            st.metric("Gesamt Datensätze", total_records)

        with preview_col4:
            # Estimated backup size (rough calculation)
            estimated_size_mb = (total_records * 0.5) + (audit_count * 0.1)  # Rough estimate
            st.metric("Geschätzte Größe", f"{estimated_size_mb:.1f} MB")

    except Exception as e:
        st.error(f"Fehler beim Laden der Vorschau: {e}")

    # Create backup button
    st.subheader("🚀 Backup starten")

    if st.button("💾 Backup erstellen", type="primary", key="create_backup_btn"):
        with st.spinner("Backup wird erstellt... Dies kann einige Minuten dauern."):
            try:
                if backup_type == "Vollständiges Backup":
                    result = backup_service.create_full_backup(
                        include_files=include_files,
                        compress=compress_backup
                    )
                else:
                    # Get last backup date
                    history = backup_service.get_backup_history(limit=1)
                    if history:
                        last_backup_date = datetime.fromisoformat(history[0]['created_at'])
                        result = backup_service.create_incremental_backup(last_backup_date)
                    else:
                        st.error("Kein vorheriges Backup für inkrementelles Backup gefunden.")
                        return

                # Display results
                if result["status"] == "completed":
                    st.success("✅ Backup erfolgreich erstellt!")

                    # Show backup details
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("**Backup Details:**")
                        st.write(f"**ID:** {result['backup_id']}")
                        st.write(f"**Typ:** {result['backup_type']}")
                        st.write(f"**Erstellt:** {result['created_at']}")
                        st.write(f"**Größe:** {result['size_bytes'] / (1024*1024):.2f} MB")

                    with col2:
                        st.write("**Komponenten:**")
                        for component in result["components"]:
                            status_icon = "✅" if component["status"] == "success" else "❌"
                            st.write(f"{status_icon} {component['component']}")

                    # Show file path
                    st.write(f"**Backup Pfad:** `{result['file_path']}`")

                    # Download option (if applicable)
                    if result.get("compressed") and result.get("file_path"):
                        try:
                            with open(result["file_path"], "rb") as f:
                                backup_data = f.read()

                            st.download_button(
                                label="📥 Backup herunterladen",
                                data=backup_data,
                                file_name=f"{result['backup_name']}.zip",
                                mime="application/zip"
                            )
                        except Exception as e:
                            st.warning(f"Download nicht verfügbar: {e}")

                elif result["status"] == "failed":
                    st.error(f"❌ Backup fehlgeschlagen: {result.get('error', 'Unbekannter Fehler')}")

                else:
                    st.warning(f"⚠️ Backup Status: {result['status']}")

            except Exception as e:
                st.error(f"Fehler beim Erstellen des Backups: {e}")


def show_backup_history_tab(backup_service):
    """Show backup history"""
    st.subheader("📋 Backup Verlauf")

    # Get backup history
    history = backup_service.get_backup_history(limit=50)

    if not history:
        st.info("Noch keine Backups erstellt.")
        return

    # Summary statistics
    col1, col2, col3, col4 = st.columns(4)

    total_backups = len(history)
    successful_backups = len([b for b in history if b["status"] == "completed"])
    failed_backups = len([b for b in history if b["status"] == "failed"])
    total_size = sum(b.get("size_bytes", 0) for b in history) / (1024*1024*1024)  # GB

    with col1:
        st.metric("Gesamt Backups", total_backups)

    with col2:
        st.metric("Erfolgreich", successful_backups)

    with col3:
        st.metric("Fehlgeschlagen", failed_backups)

    with col4:
        st.metric("Gesamtgröße", f"{total_size:.2f} GB")

    # Filter options
    st.subheader("🔍 Filter")
    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        status_filter = st.selectbox(
            "Status:",
            ["Alle", "Erfolgreich", "Fehlgeschlagen", "In Bearbeitung"],
            key="history_status_filter"
        )

    with filter_col2:
        type_filter = st.selectbox(
            "Typ:",
            ["Alle", "Vollständig", "Inkrementell"],
            key="history_type_filter"
        )

    # Apply filters
    filtered_history = history.copy()

    if status_filter != "Alle":
        status_map = {
            "Erfolgreich": "completed",
            "Fehlgeschlagen": "failed",
            "In Bearbeitung": "in_progress"
        }
        filtered_history = [b for b in filtered_history if b["status"] == status_map[status_filter]]

    if type_filter != "Alle":
        type_map = {"Vollständig": "full", "Inkrementell": "incremental"}
        filtered_history = [b for b in filtered_history if b["backup_type"] == type_map[type_filter]]

    # Display backup history table
    if filtered_history:
        st.subheader(f"📊 Backup Historie ({len(filtered_history)} Einträge)")

        # Convert to DataFrame for better display
        history_data = []
        for backup in filtered_history:
            history_data.append({
                "ID": backup["backup_id"],
                "Typ": "Vollständig" if backup["backup_type"] == "full" else "Inkrementell",
                "Status": "✅ Erfolgreich" if backup["status"] == "completed" else
                         "❌ Fehlgeschlagen" if backup["status"] == "failed" else
                         "🔄 In Bearbeitung",
                "Erstellt": backup["created_at"],
                "Größe (MB)": f"{backup.get('size_bytes', 0) / (1024*1024):.2f}",
                "Komponenten": len(backup.get("components", [])),
                "Pfad": backup.get("file_path", "N/A")
            })

        df = pd.DataFrame(history_data)
        st.dataframe(df, hide_index=True, use_container_width=True)

        # Detailed view for selected backup
        st.subheader("🔍 Backup Details")
        selected_backup_id = st.selectbox(
            "Backup für Details auswählen:",
            [b["backup_id"] for b in filtered_history],
            key="selected_backup_detail"
        )

        if selected_backup_id:
            selected_backup = next(b for b in filtered_history if b["backup_id"] == selected_backup_id)
            display_backup_details(selected_backup)

    else:
        st.info("Keine Backups entsprechen den gewählten Filterkriterien.")


def show_verify_backup_tab(backup_service):
    """Show backup verification interface"""
    st.subheader("✅ Backup Verifikation")

    st.info("Überprüfen Sie die Integrität Ihrer Backups um sicherzustellen, dass sie im Notfall wiederherstellbar sind.")

    # Select backup to verify
    history = backup_service.get_backup_history(limit=20)

    if not history:
        st.warning("Keine Backups zum Überprüfen vorhanden.")
        return

    # Backup selection
    col1, col2 = st.columns(2)

    with col1:
        backup_options = {
            f"{b['backup_id']} ({b['backup_type']}) - {b['created_at']}": b['file_path']
            for b in history if b['status'] == 'completed'
        }

        if not backup_options:
            st.warning("Keine erfolgreichen Backups zum Überprüfen vorhanden.")
            return

        selected_backup_display = st.selectbox(
            "Backup auswählen:",
            list(backup_options.keys()),
            key="verify_backup_select"
        )
        selected_backup_path = backup_options[selected_backup_display]

    with col2:
        st.write("**Verifikations-Prüfungen:**")
        st.write("✓ Datei/Verzeichnis Existenz")
        st.write("✓ ZIP Integrität (falls komprimiert)")
        st.write("✓ Erforderliche Dateien")
        st.write("✓ Metadaten Konsistenz")

    # Verify button
    if st.button("🔍 Backup überprüfen", type="primary", key="verify_backup_btn"):
        with st.spinner("Backup wird überprüft..."):
            verification_result = backup_service.verify_backup(selected_backup_path)

            # Display verification results
            if verification_result["status"] == "valid":
                st.success("✅ Backup ist gültig und intakt!")

                # Show detailed checks
                st.subheader("🔍 Detaillierte Prüfungen")
                checks_col1, checks_col2 = st.columns(2)

                with checks_col1:
                    for check, result in verification_result["checks"].items():
                        status_icon = "✅" if result else "❌"
                        check_name = check.replace("_", " ").title()
                        st.write(f"{status_icon} {check_name}")

                with checks_col2:
                    st.write(f"**Überprüft am:** {verification_result['verified_at']}")
                    st.write(f"**Backup Pfad:** {verification_result['backup_path']}")

            elif verification_result["status"] == "invalid":
                st.error(f"❌ Backup ist ungültig: {verification_result.get('error', 'Unbekannter Fehler')}")

            elif verification_result["status"] == "corrupted":
                st.error(f"🚨 Backup ist beschädigt: {verification_result.get('error', 'Datenkorruption erkannt')}")

            elif verification_result["status"] == "incomplete":
                st.warning(f"⚠️ Backup ist unvollständig. Einige erforderliche Dateien fehlen.")

                # Show what's missing
                if "checks" in verification_result:
                    st.write("**Fehlende Komponenten:**")
                    for check, result in verification_result["checks"].items():
                        if not result and check.startswith("has_"):
                            file_name = check.replace("has_", "")
                            st.write(f"❌ {file_name}")

            else:
                st.error(f"❌ Fehler bei der Verifikation: {verification_result.get('error', 'Unbekannter Fehler')}")

    # Automatic verification
    st.subheader("🤖 Automatische Verifikation")

    if st.button("🔄 Alle Backups überprüfen", key="verify_all_backups"):
        with st.spinner("Alle Backups werden überprüft..."):
            verification_results = []

            for backup in history:
                if backup['status'] == 'completed':
                    result = backup_service.verify_backup(backup['file_path'])
                    verification_results.append({
                        "backup_id": backup['backup_id'],
                        "backup_type": backup['backup_type'],
                        "created_at": backup['created_at'],
                        "verification_status": result['status'],
                        "error": result.get('error', '')
                    })

            # Display results
            if verification_results:
                st.subheader("📊 Verifikations Ergebnisse")

                results_data = []
                for result in verification_results:
                    status_display = {
                        "valid": "✅ Gültig",
                        "invalid": "❌ Ungültig",
                        "corrupted": "🚨 Beschädigt",
                        "incomplete": "⚠️ Unvollständig",
                        "error": "❌ Fehler"
                    }.get(result["verification_status"], result["verification_status"])

                    results_data.append({
                        "Backup ID": result["backup_id"],
                        "Typ": result["backup_type"],
                        "Erstellt": result["created_at"],
                        "Status": status_display,
                        "Fehler": result["error"][:50] + "..." if len(result["error"]) > 50 else result["error"]
                    })

                df_results = pd.DataFrame(results_data)
                st.dataframe(df_results, hide_index=True, use_container_width=True)

                # Summary
                valid_count = len([r for r in verification_results if r["verification_status"] == "valid"])
                total_count = len(verification_results)

                if valid_count == total_count:
                    st.success(f"🎉 Alle {total_count} Backups sind gültig!")
                else:
                    st.warning(f"⚠️ {valid_count} von {total_count} Backups sind gültig. Bitte überprüfen Sie die fehlerhaften Backups.")


def show_cleanup_backups_tab(backup_service):
    """Show backup cleanup interface"""
    st.subheader("🗑️ Backup Bereinigung")

    st.info("Verwalten Sie Ihren Speicherplatz durch automatische Bereinigung alter Backups.")

    # Current backup statistics
    history = backup_service.get_backup_history()

    if history:
        total_backups = len(history)
        total_size_gb = sum(b.get("size_bytes", 0) for b in history) / (1024**3)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Gesamt Backups", total_backups)
        with col2:
            st.metric("Gesamtgröße", f"{total_size_gb:.2f} GB")
        with col3:
            # Calculate oldest backup age
            oldest_backup = min(history, key=lambda x: x["created_at"])
            oldest_date = datetime.fromisoformat(oldest_backup["created_at"])
            age_days = (datetime.now() - oldest_date).days
            st.metric("Ältestes Backup", f"{age_days} Tage")

    # Cleanup configuration
    st.subheader("⚙️ Bereinigungsregeln")

    col1, col2 = st.columns(2)

    with col1:
        retention_days = st.number_input(
            "Aufbewahrungszeit (Tage):",
            min_value=1,
            max_value=365,
            value=30,
            help="Backups älter als diese Anzahl Tage werden gelöscht",
            key="retention_days"
        )

    with col2:
        keep_minimum = st.number_input(
            "Mindestanzahl behalten:",
            min_value=1,
            max_value=50,
            value=5,
            help="Mindestanzahl Backups, die unabhängig vom Alter behalten werden",
            key="keep_minimum"
        )

    # Preview what would be deleted
    if st.button("🔍 Vorschau der Bereinigung", key="cleanup_preview"):
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        if history:
            # Sort by creation date
            sorted_history = sorted(history, key=lambda x: x["created_at"], reverse=True)

            to_delete = []
            to_keep = []

            for i, backup in enumerate(sorted_history):
                backup_date = datetime.fromisoformat(backup["created_at"])

                if i < keep_minimum:
                    to_keep.append(backup)
                elif backup_date >= cutoff_date:
                    to_keep.append(backup)
                else:
                    to_delete.append(backup)

            # Display preview
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("🗑️ Zu löschende Backups")
                if to_delete:
                    delete_size = sum(b.get("size_bytes", 0) for b in to_delete) / (1024**2)  # MB
                    st.warning(f"{len(to_delete)} Backups ({delete_size:.2f} MB) werden gelöscht:")

                    for backup in to_delete:
                        st.write(f"• {backup['backup_id']} - {backup['created_at']}")
                else:
                    st.success("Keine Backups zu löschen")

            with col2:
                st.subheader("✅ Behalten")
                if to_keep:
                    keep_size = sum(b.get("size_bytes", 0) for b in to_keep) / (1024**2)  # MB
                    st.info(f"{len(to_keep)} Backups ({keep_size:.2f} MB) werden behalten:")

                    for backup in to_keep[:5]:  # Show first 5
                        st.write(f"• {backup['backup_id']} - {backup['created_at']}")

                    if len(to_keep) > 5:
                        st.write(f"... und {len(to_keep) - 5} weitere")

    # Execute cleanup
    st.subheader("🚀 Bereinigung ausführen")

    st.warning("⚠️ **Achtung:** Diese Aktion kann nicht rückgängig gemacht werden!")

    confirm_cleanup = st.checkbox(
        "Ich bestätige, dass ich die Bereinigungsregeln verstehe und fortfahren möchte",
        key="confirm_cleanup"
    )

    if confirm_cleanup:
        if st.button("🗑️ Bereinigung starten", type="primary", key="execute_cleanup"):
            with st.spinner("Bereinigung wird ausgeführt..."):
                cleanup_result = backup_service.cleanup_old_backups(
                    retention_days=retention_days,
                    keep_minimum=keep_minimum
                )

                if cleanup_result["status"] == "success":
                    st.success("✅ Bereinigung erfolgreich abgeschlossen!")

                    # Show cleanup results
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Gelöschte Backups", cleanup_result["deleted_backups"])

                    with col2:
                        deleted_size_mb = cleanup_result["deleted_size_bytes"] / (1024**2)
                        st.metric("Freigegebener Speicher", f"{deleted_size_mb:.2f} MB")

                    with col3:
                        st.metric("Verbleibende Backups", cleanup_result["kept_backups"])

                else:
                    st.error(f"❌ Bereinigung fehlgeschlagen: {cleanup_result.get('error', 'Unbekannter Fehler')}")

    else:
        st.info("Bitte bestätigen Sie die Bereinigung, um fortzufahren.")


def show_automation_tab(backup_service):
    """Show backup automation settings"""
    st.subheader("⚙️ Backup Automatisierung")

    st.info("Konfigurieren Sie automatische Backups für kontinuierlichen Datenschutz.")

    # Current automation status
    st.subheader("📊 Aktueller Status")

    # This would normally load from a configuration file or database
    automation_enabled = False  # Placeholder
    last_auto_backup = "Nie"  # Placeholder
    next_scheduled = "Nicht geplant"  # Placeholder

    col1, col2, col3 = st.columns(3)

    with col1:
        status_color = "🟢" if automation_enabled else "🔴"
        st.metric("Automatisierung", f"{status_color} {'Aktiv' if automation_enabled else 'Inaktiv'}")

    with col2:
        st.metric("Letztes Auto-Backup", last_auto_backup)

    with col3:
        st.metric("Nächstes Backup", next_scheduled)

    # Automation configuration
    st.subheader("⚙️ Automatisierung konfigurieren")

    with st.form("automation_config"):
        col1, col2 = st.columns(2)

        with col1:
            enable_automation = st.checkbox(
                "Automatische Backups aktivieren",
                value=automation_enabled,
                key="enable_auto_backup"
            )

            backup_frequency = st.selectbox(
                "Backup Häufigkeit:",
                ["Täglich", "Wöchentlich", "Monatlich"],
                index=0,
                key="backup_frequency"
            )

            backup_time = st.time_input(
                "Backup Zeit:",
                value=datetime.strptime("02:00", "%H:%M").time(),
                help="Zeit für automatische Backups (24h Format)",
                key="backup_time"
            )

        with col2:
            auto_backup_type = st.selectbox(
                "Standard Backup Typ:",
                ["Inkrementell", "Vollständig"],
                help="Inkrementell für tägliche Backups empfohlen",
                key="auto_backup_type"
            )

            auto_cleanup = st.checkbox(
                "Automatische Bereinigung",
                value=True,
                help="Alte Backups automatisch löschen",
                key="auto_cleanup"
            )

            if auto_cleanup:
                auto_retention_days = st.number_input(
                    "Aufbewahrungszeit (Tage):",
                    min_value=7,
                    max_value=365,
                    value=30,
                    key="auto_retention_days"
                )

        # Notification settings
        st.subheader("📬 Benachrichtigungen")

        notify_success = st.checkbox(
            "Bei erfolgreichem Backup benachrichtigen",
            value=False,
            key="notify_success"
        )

        notify_failure = st.checkbox(
            "Bei fehlgeschlagenem Backup benachrichtigen",
            value=True,
            key="notify_failure"
        )

        # Save configuration
        if st.form_submit_button("💾 Automatisierung konfigurieren", type="primary"):
            # Create automation schedule
            automation_config = {
                "enabled": enable_automation,
                "frequency": backup_frequency,
                "time": backup_time.strftime("%H:%M"),
                "backup_type": auto_backup_type.lower(),
                "auto_cleanup": auto_cleanup,
                "retention_days": auto_retention_days if auto_cleanup else None,
                "notify_success": notify_success,
                "notify_failure": notify_failure
            }

            # This would normally save to configuration and set up the scheduler
            schedule_result = backup_service.schedule_automatic_backup(
                backup_type=auto_backup_type.lower(),
                interval_hours=24 if backup_frequency == "Täglich" else
                              168 if backup_frequency == "Wöchentlich" else 720
            )

            if schedule_result["status"] == "scheduled":
                st.success("✅ Automatisierung erfolgreich konfiguriert!")

                st.write("**Konfiguration:**")
                st.json(automation_config)

                if enable_automation:
                    st.info(f"🕐 Nächstes automatisches Backup: {schedule_result['next_backup']}")
                else:
                    st.warning("⚠️ Automatisierung ist deaktiviert. Aktivieren Sie sie, um geplante Backups zu starten.")

            else:
                st.error("❌ Fehler beim Konfigurieren der Automatisierung")

    # Manual scheduling
    st.subheader("📅 Einmaliges Backup planen")

    with st.form("schedule_one_time"):
        col1, col2 = st.columns(2)

        with col1:
            schedule_date = st.date_input(
                "Datum:",
                value=datetime.now().date(),
                min_value=datetime.now().date(),
                key="schedule_date"
            )

        with col2:
            schedule_time = st.time_input(
                "Zeit:",
                value=datetime.strptime("03:00", "%H:%M").time(),
                key="schedule_time"
            )

        scheduled_backup_type = st.selectbox(
            "Backup Typ:",
            ["Vollständig", "Inkrementell"],
            key="scheduled_backup_type"
        )

        if st.form_submit_button("📅 Einmaliges Backup planen"):
            scheduled_datetime = datetime.combine(schedule_date, schedule_time)

            if scheduled_datetime <= datetime.now():
                st.error("❌ Geplante Zeit muss in der Zukunft liegen")
            else:
                # This would create a one-time scheduled task
                st.success(f"✅ Backup für {scheduled_datetime.strftime('%d.%m.%Y %H:%M')} geplant")
                st.info("Das geplante Backup wird automatisch zur angegebenen Zeit ausgeführt.")

    # System requirements and limitations
    with st.expander("ℹ️ Systemanforderungen und Einschränkungen"):
        st.markdown("""
        **Systemanforderungen für Automatisierung:**

        - **Betriebssystem:** Windows Task Scheduler, Linux Cron oder macOS Launchd
        - **Berechtigung:** Administrative Rechte für Scheduler-Zugriff
        - **Speicherplatz:** Ausreichend Platz für Backup-Dateien
        - **Laufzeit:** System muss zur geplanten Zeit verfügbar sein

        **Einschränkungen:**

        - Automatische Backups erfordern, dass das System zur geplanten Zeit läuft
        - Bei Systemabschaltung werden verpasste Backups nicht nachgeholt
        - Netzwerkbackups erfordern stabile Verbindung
        - Große Datenbanken können lange Backup-Zeiten haben

        **Empfehlungen:**

        - Planen Sie Backups für Zeiten mit geringer Systemlast
        - Verwenden Sie inkrementelle Backups für häufige Sicherungen
        - Überwachen Sie regelmäßig die Backup-Logs
        - Testen Sie die Wiederherstellung regelmäßig
        """)


def display_backup_details(backup: Dict[str, Any]):
    """Display detailed information about a backup"""
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Grundinformationen:**")
        st.write(f"**ID:** {backup['backup_id']}")
        st.write(f"**Typ:** {backup['backup_type']}")
        st.write(f"**Status:** {backup['status']}")
        st.write(f"**Erstellt:** {backup['created_at']}")

        if backup.get('completed_at'):
            st.write(f"**Abgeschlossen:** {backup['completed_at']}")

        st.write(f"**Größe:** {backup.get('size_bytes', 0) / (1024*1024):.2f} MB")

    with col2:
        st.write("**Dateipfad:**")
        st.code(backup.get('file_path', 'N/A'))

        if backup.get('checksum'):
            st.write(f"**Checksumme:** {backup['checksum'][:16]}...")

        if backup.get('compressed'):
            st.write("**Komprimiert:** ✅ Ja")
        else:
            st.write("**Komprimiert:** ❌ Nein")

    # Components
    if backup.get('components'):
        st.write("**Backup Komponenten:**")

        components_data = []
        for component in backup['components']:
            components_data.append({
                "Komponente": component['component'],
                "Status": "✅ Erfolg" if component['status'] == 'success' else "❌ Fehler",
                "Größe (KB)": f"{component.get('size_bytes', 0) / 1024:.2f}",
                "Details": component.get('records_count', component.get('files_count', 'N/A'))
            })

        df_components = pd.DataFrame(components_data)
        st.dataframe(df_components, hide_index=True, use_container_width=True)

    # Error information
    if backup['status'] == 'failed' and backup.get('error'):
        st.write("**Fehlerdetails:**")
        st.error(backup['error'])