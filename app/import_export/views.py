"""
Import/Export views for inventory data management
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any

from core.security import require_auth, require_role, SessionManager
from core.database import get_db
from .services import get_import_export_service


@require_auth
@require_role("netzwerker")
def show_import_export_page():
    """
    Import/Export page (requires netzwerker role or higher)
    """
    st.header("📥📤 Import/Export")

    # Get database session and service
    db = next(get_db())
    import_export_service = get_import_export_service(db)
    current_user = SessionManager.get_current_user()

    # Check if current_user is valid
    if not current_user or not isinstance(current_user, dict):
        st.error("❌ Benutzerinformationen nicht verfügbar. Bitte melden Sie sich erneut an.")
        db.close()
        return

    # Create tabs for different operations
    tab1, tab2, tab3 = st.tabs(["📤 Export", "📥 Import", "📋 Vorlagen"])

    with tab1:
        show_export_section(import_export_service)

    with tab2:
        show_import_section(import_export_service, current_user)

    with tab3:
        show_templates_section(import_export_service)

    db.close()


def show_export_section(import_export_service):
    """Show export functionality"""
    st.subheader("📤 Daten Export")

    st.info("Exportieren Sie Ihre Inventardaten in verschiedene Formate für Backup oder externe Nutzung.")

    # Export options
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("CSV Export")

        # Hardware export
        if st.button("🔧 Hardware exportieren (CSV)", key="export_hw_csv"):
            with st.spinner("Hardware Daten werden exportiert..."):
                csv_data = import_export_service.export_hardware_to_csv()

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"hardware_export_{timestamp}.csv"

                st.download_button(
                    label="📥 Hardware CSV herunterladen",
                    data=csv_data,
                    file_name=filename,
                    mime="text/csv",
                    key="download_hw_csv"
                )
                st.success("Hardware Export bereit!")

        # Cables export
        if st.button("🔌 Kabel exportieren (CSV)", key="export_cables_csv"):
            with st.spinner("Kabel Daten werden exportiert..."):
                csv_data = import_export_service.export_cables_to_csv()

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"cables_export_{timestamp}.csv"

                st.download_button(
                    label="📥 Kabel CSV herunterladen",
                    data=csv_data,
                    file_name=filename,
                    mime="text/csv",
                    key="download_cables_csv"
                )
                st.success("Kabel Export bereit!")

        # Locations export
        if st.button("🏢 Standorte exportieren (CSV)", key="export_locations_csv"):
            with st.spinner("Standort Daten werden exportiert..."):
                csv_data = import_export_service.export_locations_to_csv()

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"locations_export_{timestamp}.csv"

                st.download_button(
                    label="📥 Standorte CSV herunterladen",
                    data=csv_data,
                    file_name=filename,
                    mime="text/csv",
                    key="download_locations_csv"
                )
                st.success("Standorte Export bereit!")

    with col2:
        st.subheader("JSON Export")

        # Complete inventory export
        if st.button("📦 Komplettes Inventar exportieren (JSON)", key="export_all_json"):
            with st.spinner("Komplette Inventardaten werden exportiert..."):
                json_data = import_export_service.export_inventory_to_json()

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"inventory_complete_export_{timestamp}.json"

                st.download_button(
                    label="📥 Kompletter Export JSON herunterladen",
                    data=json_data,
                    file_name=filename,
                    mime="application/json",
                    key="download_all_json"
                )
                st.success("Kompletter Inventar Export bereit!")

        st.info("""
        **JSON Export Vorteile:**
        - Vollständige Datenstruktur
        - Alle Beziehungen erhalten
        - Ideal für Backups
        - Maschinenlesbar
        """)

    # Export information
    st.subheader("ℹ️ Export Informationen")

    with st.expander("📋 Was wird exportiert?"):
        st.markdown("""
        **Hardware CSV:**
        - Alle aktiven Hardware-Artikel
        - Standort-Zuordnungen
        - Technische Details und Preise
        - Audit-Informationen

        **Kabel CSV:**
        - Alle aktiven Kabel-Typen
        - Bestandsinformationen
        - Spezifikationen und Preise
        - Lagerort-Details

        **Standorte CSV:**
        - Hierarchische Standort-Struktur
        - Adress- und Kontaktinformationen
        - Parent-Child Beziehungen

        **JSON Komplett:**
        - Alle oben genannten Daten
        - Vollständige Datenstruktur
        - Zeitstempel und Metadaten
        """)


def show_import_section(import_export_service, current_user):
    """Show import functionality"""
    st.subheader("📥 Daten Import")

    st.warning("""
    ⚠️ **Wichtiger Hinweis:**
    - Bitte erstellen Sie vor dem Import ein Backup
    - Verwenden Sie die bereitgestellten Vorlagen
    - Überprüfen Sie Ihre Daten vor dem Import
    """)

    # Import type selection
    import_type = st.selectbox(
        "Import Typ auswählen:",
        ["Hardware", "Kabel"],
        key="import_type_select"
    )

    # File upload
    uploaded_file = st.file_uploader(
        f"CSV Datei für {import_type} hochladen:",
        type=['csv'],
        key=f"upload_{import_type.lower()}"
    )

    if uploaded_file is not None:
        # Read file content
        csv_content = uploaded_file.read().decode('utf-8')

        # Validate data
        with st.spinner("Daten werden validiert..."):
            validation_result = import_export_service.validate_import_data(
                csv_content,
                import_type.lower() if import_type == "Hardware" else "cables"
            )

        if validation_result["success"]:
            # Show validation results
            st.success("✅ Datei erfolgreich validiert!")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Gesamte Zeilen", validation_result["total_rows"])
            with col2:
                st.metric("Gültige Zeilen", validation_result["valid_rows"])
            with col3:
                st.metric("Erkannte Spalten", len(validation_result["columns"]))

            # Show columns
            with st.expander("📋 Erkannte Spalten"):
                st.write(validation_result["columns"])

            # Preview data
            if st.checkbox("📊 Datenvorschau anzeigen"):
                import pandas as pd
                import io

                df = pd.read_csv(io.StringIO(csv_content))
                st.dataframe(df.head(10), use_container_width=True)

            # Import confirmation
            st.subheader("🚀 Import durchführen")

            if validation_result["valid_rows"] > 0:
                confirm_import = st.checkbox(
                    f"✅ Ich bestätige den Import von {validation_result['valid_rows']} {import_type} Einträgen",
                    key="confirm_import"
                )

                if confirm_import and st.button(f"📥 {import_type} importieren", key="execute_import"):
                    with st.spinner(f"{import_type} werden importiert..."):
                        if import_type == "Hardware":
                            result = import_export_service.import_hardware_from_csv(
                                csv_content, current_user['id']
                            )
                        else:
                            result = import_export_service.import_cables_from_csv(
                                csv_content, current_user['id']
                            )

                    # Show results
                    if result["success"]:
                        st.success(f"✅ Import erfolgreich! {result['imported_count']} Einträge importiert.")

                        # Show warnings if any
                        if result.get("warnings"):
                            with st.expander("⚠️ Warnungen"):
                                for warning in result["warnings"]:
                                    st.warning(warning)

                        # Show errors if any
                        if result.get("errors"):
                            with st.expander("❌ Fehler"):
                                for error in result["errors"]:
                                    st.error(error)

                    else:
                        st.error(f"❌ Import fehlgeschlagen: {result.get('error')}")
            else:
                st.warning("Keine gültigen Daten zum Importieren gefunden.")

        else:
            st.error(f"❌ Validierung fehlgeschlagen: {validation_result.get('error')}")

    # Import guidelines
    with st.expander("📚 Import Richtlinien"):
        st.markdown("""
        **Hardware Import:**
        - **Erforderliche Felder:** Name, Kategorie
        - Standort muss bereits existieren (falls angegeben)
        - Datumsformat: YYYY-MM-DD
        - Preise als Dezimalzahlen mit Punkt als Trenner

        **Kabel Import:**
        - **Erforderliche Felder:** Typ, Standard, Länge
        - Länge als Dezimalzahl in Metern
        - Menge, Mindest- und Höchstbestand als ganze Zahlen
        - Standort muss bereits existieren (falls angegeben)

        **Allgemeine Hinweise:**
        - UTF-8 Kodierung verwenden
        - Komma als CSV-Trenner
        - Erste Zeile muss Header enthalten
        - Leere Zeilen werden ignoriert
        """)


def show_templates_section(import_export_service):
    """Show import templates"""
    st.subheader("📋 Import Vorlagen")

    st.info("Verwenden Sie diese Vorlagen als Ausgangspunkt für Ihre Import-Dateien.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔧 Hardware Vorlage")

        if st.button("📥 Hardware Vorlage herunterladen", key="download_hw_template"):
            template_data = import_export_service.get_import_template_hardware()

            st.download_button(
                label="📄 Hardware Template CSV",
                data=template_data,
                file_name="hardware_import_template.csv",
                mime="text/csv",
                key="hw_template_download"
            )

        with st.expander("📋 Hardware Template Vorschau"):
            template_data = import_export_service.get_import_template_hardware()
            st.text_area(
                "Template Inhalt:",
                template_data,
                height=200,
                key="hw_template_preview"
            )

    with col2:
        st.subheader("🔌 Kabel Vorlage")

        if st.button("📥 Kabel Vorlage herunterladen", key="download_cable_template"):
            template_data = import_export_service.get_import_template_cables()

            st.download_button(
                label="📄 Kabel Template CSV",
                data=template_data,
                file_name="cables_import_template.csv",
                mime="text/csv",
                key="cable_template_download"
            )

        with st.expander("📋 Kabel Template Vorschau"):
            template_data = import_export_service.get_import_template_cables()
            st.text_area(
                "Template Inhalt:",
                template_data,
                height=200,
                key="cable_template_preview"
            )

    # Template usage instructions
    st.subheader("📖 Verwendung der Vorlagen")

    with st.expander("💡 Anleitung"):
        st.markdown("""
        **So verwenden Sie die Vorlagen:**

        1. **Template herunterladen**
           - Wählen Sie die gewünschte Vorlage (Hardware oder Kabel)
           - Klicken Sie auf "Vorlage herunterladen"

        2. **Datei bearbeiten**
           - Öffnen Sie die CSV-Datei in Excel, LibreOffice oder einem Texteditor
           - Ersetzen Sie die Beispieldaten durch Ihre eigenen Daten
           - Behalten Sie die Header-Zeile bei

        3. **Daten vorbereiten**
           - Stellen Sie sicher, dass alle erforderlichen Felder ausgefüllt sind
           - Verwenden Sie das korrekte Datumsformat (YYYY-MM-DD)
           - Standorte müssen bereits im System existieren

        4. **Import durchführen**
           - Gehen Sie zum Import-Tab
           - Laden Sie Ihre vorbereitete CSV-Datei hoch
           - Überprüfen Sie die Validierung
           - Führen Sie den Import durch

        **Tipps:**
        - Beginnen Sie mit kleinen Testdateien
        - Überprüfen Sie die Datentypen und Formate
        - Erstellen Sie vor dem Import ein Backup
        - Nutzen Sie die Datenvorschau zur Kontrolle
        """)

    # Additional resources
    st.subheader("🔧 Zusätzliche Ressourcen")

    with st.expander("🆘 Häufige Probleme und Lösungen"):
        st.markdown("""
        **Problem: "Standort nicht gefunden"**
        - Lösung: Erstellen Sie zuerst alle Standorte oder lassen Sie das Standort-Feld leer

        **Problem: "Ungültiges Datum"**
        - Lösung: Verwenden Sie das Format YYYY-MM-DD (z.B. 2024-01-15)

        **Problem: "Ungültiger Preis"**
        - Lösung: Verwenden Sie Dezimalzahlen mit Punkt (z.B. 123.45, nicht 123,45)

        **Problem: "Fehlende erforderliche Spalten"**
        - Lösung: Stellen Sie sicher, dass alle Pflichtfelder vorhanden sind

        **Problem: CSV-Formatierung**
        - Lösung: Speichern Sie als CSV mit UTF-8 Kodierung und Komma als Trenner
        """)

def show_batch_operations():
    """Show batch operations for data management"""
    st.subheader("🔄 Batch Operationen")

    st.info("Führen Sie Massenoperationen an Ihren Inventardaten durch.")

    # This would be implemented in a future iteration
    st.warning("Batch-Operationen werden in einer zukünftigen Version verfügbar sein.")