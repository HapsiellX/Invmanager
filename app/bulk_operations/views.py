"""
Bulk operations views for efficient inventory management
"""

import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional

from .services import get_bulk_operations_service
from core.security import SessionManager


def show_bulk_operations_page():
    """Display the main bulk operations page"""
    st.title("⚡ Bulk-Operationen")
    
    bulk_service = get_bulk_operations_service()
    
    # Check dependencies
    deps_status = bulk_service.get_dependencies_status()
    missing_deps = bulk_service.get_missing_dependencies()
    
    if missing_deps:
        st.warning(f"""
        **Fehlende Abhängigkeiten für Bulk-Operationen:**
        
        Die folgenden Python-Pakete müssen installiert werden:
        - {', '.join(missing_deps)}
        
        Installieren Sie diese mit:
        ```bash
        pip install {' '.join(missing_deps)}
        ```
        """)
        return
    
    st.write("Effiziente Verwaltung großer Mengen von Inventar-Items durch Bulk-Operationen.")
    
    # Create tabs for different bulk operations
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📥 Bulk Import",
        "✏️ Bulk Update", 
        "🗑️ Bulk Delete",
        "📋 Vorlagen",
        "📊 Status & Historie"
    ])
    
    with tab1:
        show_bulk_import_tab(bulk_service)
    
    with tab2:
        show_bulk_update_tab(bulk_service)
    
    with tab3:
        show_bulk_delete_tab(bulk_service)
    
    with tab4:
        show_templates_tab(bulk_service)
    
    with tab5:
        show_status_tab(bulk_service)


def show_bulk_import_tab(bulk_service):
    """Show bulk import functionality"""
    st.header("📥 Bulk Import")
    st.write("Importieren Sie große Mengen neuer Items aus CSV/Excel-Dateien.")
    
    # Item type selection
    item_type = st.selectbox(
        "Item-Typ auswählen:",
        ["Hardware", "Kabel"],
        key="import_item_type"
    )
    
    item_type_key = "hardware" if item_type == "Hardware" else "cables"
    
    # File upload
    uploaded_file = st.file_uploader(
        "CSV/Excel-Datei hochladen:",
        type=['csv', 'xlsx', 'xls'],
        key="bulk_import_file",
        help="Laden Sie eine CSV oder Excel-Datei mit den zu importierenden Items hoch."
    )
    
    if uploaded_file is not None:
        st.success(f"Datei '{uploaded_file.name}' hochgeladen.")
        
        # Parse uploaded file
        with st.spinner("Analysiere Datei..."):
            try:
                data, parse_errors = bulk_service.parse_uploaded_file(uploaded_file)
                
                if parse_errors:
                    st.error("Fehler beim Parsen der Datei:")
                    for error in parse_errors:
                        st.write(f"• {error}")
                    return
                
                if not data:
                    st.warning("Keine Daten in der Datei gefunden.")
                    return
                
                st.success(f"{len(data)} Datensätze gefunden.")
                
                # Show preview
                with st.expander("🔍 Datenvorschau", expanded=True):
                    import pandas as pd
                    df_preview = pd.DataFrame(data[:10])  # Show first 10 rows
                    st.dataframe(df_preview, use_container_width=True)
                    
                    if len(data) > 10:
                        st.info(f"Zeige erste 10 von {len(data)} Datensätzen.")
                
                # Validate data
                st.subheader("📋 Datenvalidierung")
                
                with st.spinner("Validiere Daten..."):
                    valid_items, validation_errors = bulk_service.validate_bulk_data(
                        data, "create", item_type_key
                    )
                
                # Show validation results
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("✅ Gültige Items", len(valid_items))
                
                with col2:
                    st.metric("❌ Fehlerhafte Items", len(validation_errors))
                
                if validation_errors:
                    with st.expander("⚠️ Validierungsfehler anzeigen"):
                        for error in validation_errors:
                            st.write(f"• {error}")
                
                # Import button
                if valid_items:
                    st.divider()
                    
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        confirm_import = st.checkbox(
                            f"Ich bestätige den Import von {len(valid_items)} gültigen Items",
                            key="confirm_bulk_import"
                        )
                    
                    with col2:
                        import_button = st.button(
                            "🚀 Import starten",
                            disabled=not confirm_import,
                            use_container_width=True,
                            key="start_import_button"
                        )
                    
                    if import_button and confirm_import:
                        perform_bulk_import(bulk_service, valid_items, item_type_key)
                
                else:
                    st.error("Keine gültigen Items zum Importieren gefunden.")
                    
            except Exception as e:
                st.error(f"Fehler beim Verarbeiten der Datei: {e}")


def perform_bulk_import(bulk_service, valid_items: List[Dict], item_type: str):
    """Perform the actual bulk import"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("Starte Bulk-Import...")
        
        if item_type == "hardware":
            results = bulk_service.bulk_create_hardware(valid_items)
        else:
            results = bulk_service.bulk_create_cables(valid_items)
        
        progress_bar.progress(100)
        
        # Show results
        st.success("Bulk-Import abgeschlossen!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("✅ Erfolgreich importiert", results["success_count"])
        
        with col2:
            st.metric("❌ Fehler", results["error_count"])
        
        if results["errors"]:
            with st.expander("❌ Import-Fehler anzeigen"):
                for error in results["errors"]:
                    st.write(f"• {error}")
        
        if results["created_items"]:
            with st.expander("✅ Erstellte Items anzeigen"):
                import pandas as pd
                df_created = pd.DataFrame(results["created_items"])
                st.dataframe(df_created, use_container_width=True)
        
    except Exception as e:
        st.error(f"Fehler beim Import: {e}")
    finally:
        progress_bar.empty()
        status_text.empty()


def show_bulk_update_tab(bulk_service):
    """Show bulk update functionality"""
    st.header("✏️ Bulk Update")
    st.write("Aktualisieren Sie mehrere Items gleichzeitig über CSV/Excel-Dateien.")
    
    # Item type selection
    item_type = st.selectbox(
        "Item-Typ auswählen:",
        ["Hardware", "Kabel"],
        key="update_item_type"
    )
    
    item_type_key = "hardware" if item_type == "Hardware" else "cables"
    
    # File upload
    uploaded_file = st.file_uploader(
        "Update-Datei hochladen:",
        type=['csv', 'xlsx', 'xls'],
        key="bulk_update_file",
        help="Datei muss 'seriennummer' enthalten zur Identifikation der Items."
    )
    
    if uploaded_file is not None:
        try:
            data, parse_errors = bulk_service.parse_uploaded_file(uploaded_file)
            
            if parse_errors:
                st.error("Fehler beim Parsen der Datei:")
                for error in parse_errors:
                    st.write(f"• {error}")
                return
            
            if not data:
                st.warning("Keine Daten in der Datei gefunden.")
                return
            
            # Validate update data
            valid_items, validation_errors = bulk_service.validate_bulk_data(
                data, "update", item_type_key
            )
            
            # Show preview and validation
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("✅ Gültige Updates", len(valid_items))
            
            with col2:
                st.metric("❌ Fehlerhafte Updates", len(validation_errors))
            
            if validation_errors:
                with st.expander("⚠️ Validierungsfehler"):
                    for error in validation_errors:
                        st.write(f"• {error}")
            
            if valid_items:
                with st.expander("🔍 Update-Vorschau", expanded=True):
                    import pandas as pd
                    df_preview = pd.DataFrame(valid_items[:10])
                    st.dataframe(df_preview, use_container_width=True)
                
                # Update button
                if st.button("🔄 Updates durchführen", key="perform_updates"):
                    with st.spinner("Führe Updates durch..."):
                        results = bulk_service.bulk_update_items(valid_items, item_type_key)
                    
                    # Show results
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("✅ Erfolgreich aktualisiert", results["success_count"])
                    
                    with col2:
                        st.metric("❌ Fehler", results["error_count"])
                    
                    if results["errors"]:
                        with st.expander("❌ Update-Fehler"):
                            for error in results["errors"]:
                                st.write(f"• {error}")
            
        except Exception as e:
            st.error(f"Fehler beim Verarbeiten der Update-Datei: {e}")


def show_bulk_delete_tab(bulk_service):
    """Show bulk delete functionality"""
    st.header("🗑️ Bulk Delete")
    st.write("Löschen Sie mehrere Items gleichzeitig. **Achtung: Diese Operation ist nicht rückgängig zu machen!**")
    
    # Warning
    st.error("⚠️ **WARNUNG**: Bulk-Delete löscht Items permanent aus der Datenbank!")
    
    # Item type selection
    item_type = st.selectbox(
        "Item-Typ auswählen:",
        ["Hardware", "Kabel"],
        key="delete_item_type"
    )
    
    item_type_key = "hardware" if item_type == "Hardware" else "cables"
    
    # Method selection
    delete_method = st.radio(
        "Lösch-Methode auswählen:",
        ["Datei hochladen", "Seriennummern eingeben"],
        key="delete_method"
    )
    
    serial_numbers = []
    
    if delete_method == "Datei hochladen":
        uploaded_file = st.file_uploader(
            "Datei mit Seriennummern hochladen:",
            type=['csv', 'xlsx', 'xls'],
            key="bulk_delete_file",
            help="Datei muss eine 'seriennummer' Spalte enthalten."
        )
        
        if uploaded_file is not None:
            try:
                data, parse_errors = bulk_service.parse_uploaded_file(uploaded_file)
                
                if parse_errors:
                    st.error("Fehler beim Parsen der Datei:")
                    for error in parse_errors:
                        st.write(f"• {error}")
                else:
                    serial_numbers = [row.get("seriennummer", "").strip() 
                                    for row in data if row.get("seriennummer", "").strip()]
                    
                    if serial_numbers:
                        st.success(f"{len(serial_numbers)} Seriennummern gefunden.")
                        
                        with st.expander("📋 Zu löschende Seriennummern"):
                            for i, serial in enumerate(serial_numbers[:20], 1):
                                st.write(f"{i}. {serial}")
                            if len(serial_numbers) > 20:
                                st.write(f"... und {len(serial_numbers) - 20} weitere")
                    else:
                        st.warning("Keine gültigen Seriennummern in der Datei gefunden.")
                        
            except Exception as e:
                st.error(f"Fehler beim Verarbeiten der Datei: {e}")
    
    else:  # Manual input
        serial_input = st.text_area(
            "Seriennummern eingeben (eine pro Zeile):",
            height=150,
            help="Geben Sie eine Seriennummer pro Zeile ein.",
            key="manual_serials"
        )
        
        if serial_input.strip():
            serial_numbers = [line.strip() for line in serial_input.strip().split('\n') 
                            if line.strip()]
            st.info(f"{len(serial_numbers)} Seriennummern eingegeben.")
    
    # Delete operation
    if serial_numbers:
        st.divider()
        
        # Final confirmation
        st.subheader("🚨 Löschbestätigung")
        
        confirm_delete = st.checkbox(
            f"Ich bestätige das PERMANENTE Löschen von {len(serial_numbers)} Items",
            key="confirm_bulk_delete"
        )
        
        double_confirm = st.checkbox(
            "Ich verstehe, dass diese Operation nicht rückgängig gemacht werden kann",
            key="double_confirm_delete"
        )
        
        if confirm_delete and double_confirm:
            if st.button("🗑️ PERMANENT LÖSCHEN", 
                        type="primary", 
                        use_container_width=True,
                        key="execute_delete"):
                
                with st.spinner("Lösche Items..."):
                    results = bulk_service.bulk_delete_items(serial_numbers, item_type_key)
                
                # Show results
                if results["success_count"] > 0:
                    st.success(f"✅ {results['success_count']} Items erfolgreich gelöscht.")
                
                if results["error_count"] > 0:
                    st.error(f"❌ {results['error_count']} Items konnten nicht gelöscht werden.")
                
                if results["errors"]:
                    with st.expander("❌ Lösch-Fehler"):
                        for error in results["errors"]:
                            st.write(f"• {error}")


def show_templates_tab(bulk_service):
    """Show template download functionality"""
    st.header("📋 Vorlagen")
    st.write("Laden Sie CSV-Vorlagen für verschiedene Bulk-Operationen herunter.")
    
    # Template type selection
    col1, col2 = st.columns(2)
    
    with col1:
        operation_type = st.selectbox(
            "Operation auswählen:",
            ["Erstellen (Create)", "Aktualisieren (Update)", "Löschen (Delete)"],
            key="template_operation"
        )
        
        operation_key = {
            "Erstellen (Create)": "create",
            "Aktualisieren (Update)": "update", 
            "Löschen (Delete)": "delete"
        }[operation_type]
    
    with col2:
        item_type = st.selectbox(
            "Item-Typ auswählen:",
            ["Hardware", "Kabel"],
            key="template_item_type"
        )
        
        item_type_key = "hardware" if item_type == "Hardware" else "cables"
    
    # Template description
    st.subheader("📝 Vorlage Beschreibung")
    
    descriptions = {
        ("create", "hardware"): """
        **Hardware Erstellen Vorlage**
        - Enthält alle Felder für neue Hardware-Items
        - Erforderliche Felder: seriennummer, hersteller, modell, kategorie
        - Optionale Felder: preis, anschaffungsdatum, garantie_ende, status, standort, notizen
        """,
        ("create", "cables"): """
        **Kabel Erstellen Vorlage**
        - Enthält alle Felder für neue Kabel-Items
        - Erforderliche Felder: seriennummer, typ, kategorie, laenge
        - Optionale Felder: farbe, anschaffungsdatum, status, standort, notizen
        """,
        ("update", "hardware"): """
        **Hardware Update Vorlage**
        - Erforderlich: seriennummer (zur Identifikation)
        - Alle anderen Felder sind optional - nur ausgefüllte Felder werden aktualisiert
        - Leere Felder werden ignoriert
        """,
        ("update", "cables"): """
        **Kabel Update Vorlage**
        - Erforderlich: seriennummer (zur Identifikation)
        - Alle anderen Felder sind optional - nur ausgefüllte Felder werden aktualisiert
        - Leere Felder werden ignoriert
        """,
        ("delete", "hardware"): """
        **Hardware Löschen Vorlage**
        - Enthält nur das seriennummer Feld
        - Jede Zeile repräsentiert ein zu löschendes Item
        """,
        ("delete", "cables"): """
        **Kabel Löschen Vorlage**
        - Enthält nur das seriennummer Feld
        - Jede Zeile repräsentiert ein zu löschendes Item
        """
    }
    
    description_key = (operation_key, item_type_key)
    st.markdown(descriptions.get(description_key, "Beschreibung nicht verfügbar."))
    
    # Download button
    if st.button("📥 Vorlage herunterladen", 
                use_container_width=True,
                key="download_template"):
        try:
            template_buffer = bulk_service.export_template(item_type_key, operation_key)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bulk_{operation_key}_{item_type_key}_template_{timestamp}.csv"
            
            st.download_button(
                label="💾 CSV Template herunterladen",
                data=template_buffer.getvalue(),
                file_name=filename,
                mime="text/csv",
                use_container_width=True
            )
            
            st.success("Template erfolgreich generiert!")
            
        except Exception as e:
            st.error(f"Fehler beim Generieren der Vorlage: {e}")


def show_status_tab(bulk_service):
    """Show status and history of bulk operations"""
    st.header("📊 Status & Historie")
    st.write("Übersicht über vergangene Bulk-Operationen und System-Status.")
    
    # System status
    st.subheader("🔧 System Status")
    
    deps_status = bulk_service.get_dependencies_status()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Abhängigkeiten:**")
        for dep, status in deps_status.items():
            icon = "✅" if status else "❌"
            st.write(f"{icon} {dep.title()}")
    
    with col2:
        st.write("**Benutzer-Berechtigung:**")
        user_role = SessionManager.get_user_role()
        if user_role in ["admin", "netzwerker"]:
            st.write("✅ Bulk-Operationen erlaubt")
        else:
            st.write("❌ Keine Berechtigung für Bulk-Operationen")
    
    # Recent operations (placeholder - would need audit log integration)
    st.subheader("📈 Letzte Operationen")
    st.info("Historie der Bulk-Operationen wird über das Audit-System verwaltet. Besuchen Sie die Audit Trail Seite für detaillierte Logs.")
    
    # Statistics
    st.subheader("📊 Inventar Statistiken")
    
    try:
        from core.db_utils import get_db_connection
        
        with get_db_connection() as conn:
            # Get total counts
            hardware_count = conn.execute("SELECT COUNT(*) FROM hardware_inventar").fetchone()[0]
            cable_count = conn.execute("SELECT COUNT(*) FROM kabel_inventar").fetchone()[0]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Hardware Items", hardware_count)
            
            with col2:
                st.metric("Kabel Items", cable_count)
            
            with col3:
                st.metric("Gesamt Items", hardware_count + cable_count)
    
    except Exception as e:
        st.error(f"Fehler beim Laden der Statistiken: {e}")
