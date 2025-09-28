"""
Advanced reporting views for comprehensive inventory reports
"""

import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional

from .services import get_report_service
from core.security import SessionManager
from core.utils import format_currency, format_date


def show_reports_page():
    """Display the main reports page with comprehensive reporting functionality"""
    st.title("📊 Erweiterte Berichte")
    
    report_service = get_report_service()
    
    # Check dependencies
    deps_status = report_service.get_dependencies_status()
    missing_deps = report_service.get_missing_dependencies()
    
    if missing_deps:
        st.warning(f"""
        **Fehlende Abhängigkeiten für Berichte:**
        
        Die folgenden Python-Pakete müssen installiert werden für volle Funktionalität:
        - {', '.join(missing_deps)}
        
        Installieren Sie diese mit:
        ```bash
        pip install {' '.join(missing_deps)}
        ```
        """)
    
    # Dependency status indicators
    with st.expander("🔧 Abhängigkeiten Status"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_icon = "✅" if deps_status["reportlab"] else "❌"
            st.write(f"{status_icon} **PDF Generation (ReportLab)**")
            
        with col2:
            status_icon = "✅" if deps_status["pandas"] else "❌"
            st.write(f"{status_icon} **Excel Generation (Pandas)**")
            
        with col3:
            status_icon = "✅" if deps_status["openpyxl"] else "❌"
            st.write(f"{status_icon} **Excel Styling (OpenPyXL)**")
    
    # Create tabs for different report types
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Zusammenfassung",
        "📋 Detaillierte Berichte",
        "💰 Bewertungsberichte",
        "📍 Standortberichte", 
        "🔍 Audit Berichte",
        "🔧 Wartungsberichte"
    ])
    
    with tab1:
        show_summary_reports(report_service, deps_status)
    
    with tab2:
        show_detailed_reports(report_service, deps_status)
    
    with tab3:
        show_valuation_reports(report_service, deps_status)
    
    with tab4:
        show_location_reports(report_service, deps_status)
    
    with tab5:
        show_audit_reports(report_service, deps_status)
    
    with tab6:
        show_maintenance_reports(report_service, deps_status)


def show_summary_reports(report_service, deps_status: Dict[str, bool]):
    """Show summary reports tab"""
    st.header("📈 Zusammenfassungsberichte")
    st.write("Erhalten Sie einen schnellen Überblick über Ihr gesamtes Inventar.")
    
    # Summary statistics preview
    with st.spinner("Lade Zusammenfassungsdaten..."):
        summary_data = report_service.get_summary_data()
    
    if summary_data:
        # Key metrics display
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Gesamte Items",
                summary_data.get('total_items', 0)
            )
        
        with col2:
            st.metric(
                "Hardware Wert",
                format_currency(summary_data.get('total_hardware_value', 0))
            )
        
        with col3:
            st.metric(
                "Kategorien",
                len(summary_data.get('hardware_summary', []))
            )
        
        with col4:
            st.metric(
                "Standorte",
                len(summary_data.get('location_summary', []))
            )
        
        st.divider()
        
        # Hardware summary table
        if summary_data.get('hardware_summary'):
            st.subheader("Hardware nach Kategorien")
            hardware_summary = summary_data['hardware_summary']
            
            # Create display dataframe
            import pandas as pd
            df = pd.DataFrame(hardware_summary)
            df['gesamtwert'] = df['gesamtwert'].apply(lambda x: format_currency(x) if x else "€0.00")
            df['durchschnittspreis'] = df['durchschnittspreis'].apply(lambda x: format_currency(x) if x else "€0.00")
            df.columns = ['Kategorie', 'Anzahl', 'Gesamtwert', 'Durchschnittspreis']
            
            st.dataframe(df, use_container_width=True)
        
        # Status distribution
        if summary_data.get('status_distribution'):
            st.subheader("Status Verteilung")
            status_data = summary_data['status_distribution']
            
            # Create pie chart if possible
            try:
                import plotly.express as px
                df_status = pd.DataFrame(status_data)
                fig = px.pie(df_status, values='anzahl', names='status', 
                           title="Inventar Status Verteilung")
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                # Fallback to table
                df_status = pd.DataFrame(status_data)
                df_status.columns = ['Status', 'Anzahl']
                st.dataframe(df_status, use_container_width=True)
        
        st.divider()
        
        # Generate reports section
        st.subheader("📄 Berichte Generieren")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📑 PDF Zusammenfassung", 
                        disabled=not deps_status["reportlab"],
                        use_container_width=True):
                try:
                    with st.spinner("Generiere PDF Bericht..."):
                        pdf_buffer = report_service.generate_summary_report_pdf(summary_data)
                        
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"inventar_zusammenfassung_{timestamp}.pdf"
                    
                    st.download_button(
                        label="📥 PDF Herunterladen",
                        data=pdf_buffer.getvalue(),
                        file_name=filename,
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    st.success("PDF Bericht erfolgreich generiert!")
                    
                except Exception as e:
                    st.error(f"Fehler beim Generieren des PDF Berichts: {e}")
        
        with col2:
            if st.button("📊 Excel Zusammenfassung",
                        disabled=not (deps_status["pandas"] and deps_status["openpyxl"]),
                        use_container_width=True):
                try:
                    with st.spinner("Generiere Excel Bericht..."):
                        # For summary Excel, use detailed data structure
                        detailed_data = report_service.get_detailed_inventory_data()
                        excel_buffer = report_service.generate_detailed_report_excel(detailed_data)
                        
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"inventar_zusammenfassung_{timestamp}.xlsx"
                    
                    st.download_button(
                        label="📥 Excel Herunterladen",
                        data=excel_buffer.getvalue(),
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    
                    st.success("Excel Bericht erfolgreich generiert!")
                    
                except Exception as e:
                    st.error(f"Fehler beim Generieren des Excel Berichts: {e}")
    
    else:
        st.warning("Keine Daten für Zusammenfassung verfügbar.")


def show_detailed_reports(report_service, deps_status: Dict[str, bool]):
    """Show detailed reports tab"""
    st.header("📋 Detaillierte Inventar Berichte")
    st.write("Vollständige Auflistung aller Inventar-Items mit allen Details.")
    
    # Report type selection
    report_type = st.selectbox(
        "Berichtstyp auswählen:",
        ["Alle Items", "Nur Hardware", "Nur Kabel"],
        index=0
    )
    
    type_mapping = {
        "Alle Items": "all",
        "Nur Hardware": "hardware", 
        "Nur Kabel": "cables"
    }
    
    selected_type = type_mapping[report_type]
    
    # Generate detailed reports
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Excel Detailliert",
                    disabled=not (deps_status["pandas"] and deps_status["openpyxl"]),
                    use_container_width=True):
            try:
                with st.spinner("Generiere detaillierten Excel Bericht..."):
                    detailed_data = report_service.get_detailed_inventory_data(selected_type)
                    excel_buffer = report_service.generate_detailed_report_excel(detailed_data)
                    
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"inventar_detailliert_{selected_type}_{timestamp}.xlsx"
                
                st.download_button(
                    label="📥 Excel Herunterladen",
                    data=excel_buffer.getvalue(),
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                
                st.success("Detaillierter Excel Bericht erfolgreich generiert!")
                
            except Exception as e:
                st.error(f"Fehler beim Generieren des detaillierten Excel Berichts: {e}")
    
    with col2:
        if st.button("📑 PDF Detailliert",
                    disabled=not deps_status["reportlab"],
                    use_container_width=True):
            st.info("PDF Detailberichte werden bald verfügbar sein. Verwenden Sie Excel für detaillierte Berichte.")
    
    # Preview some data
    with st.expander("🔍 Datenvorschau", expanded=True):
        with st.spinner("Lade Vorschau..."):
            preview_data = report_service.get_detailed_inventory_data(selected_type)
            
        if preview_data:
            if selected_type in ["all", "hardware"] and preview_data.get('hardware'):
                st.subheader("Hardware Items (Erste 10)")
                import pandas as pd
                df_hw = pd.DataFrame(preview_data['hardware'][:10])
                
                # Select relevant columns for display
                display_cols = ['seriennummer', 'hersteller', 'modell', 'kategorie', 'preis', 'status', 'standort_name']
                available_cols = [col for col in display_cols if col in df_hw.columns]
                
                if available_cols:
                    df_display = df_hw[available_cols]
                    st.dataframe(df_display, use_container_width=True)
            
            if selected_type in ["all", "cables"] and preview_data.get('cables'):
                st.subheader("Kabel Items (Erste 10)")
                import pandas as pd
                df_cables = pd.DataFrame(preview_data['cables'][:10])
                
                # Select relevant columns for display
                display_cols = ['seriennummer', 'typ', 'kategorie', 'laenge', 'farbe', 'status', 'standort_name']
                available_cols = [col for col in display_cols if col in df_cables.columns]
                
                if available_cols:
                    df_display = df_cables[available_cols]
                    st.dataframe(df_display, use_container_width=True)


def show_valuation_reports(report_service, deps_status: Dict[str, bool]):
    """Show valuation reports tab"""
    st.header("💰 Bewertungsberichte")
    st.write("Finanzielle Analysen und Asset-Bewertungen Ihres Inventars.")
    
    # Get valuation data
    with st.spinner("Lade Bewertungsdaten..."):
        valuation_data = report_service.get_valuation_data()
    
    if valuation_data:
        # Category valuations overview
        if valuation_data.get('category_valuations'):
            st.subheader("💼 Bewertung nach Kategorien")
            
            import pandas as pd
            df_cat = pd.DataFrame(valuation_data['category_valuations'])
            
            # Format currency columns
            for col in ['gesamtwert', 'durchschnittspreis', 'minpreis', 'maxpreis']:
                if col in df_cat.columns:
                    df_cat[col] = df_cat[col].apply(lambda x: format_currency(x) if x else "€0.00")
            
            df_cat.columns = ['Kategorie', 'Anzahl', 'Gesamtwert', 'Durchschnitt', 'Min', 'Max']
            st.dataframe(df_cat, use_container_width=True)
            
            # Chart if possible
            try:
                import plotly.express as px
                df_chart = pd.DataFrame(valuation_data['category_valuations'])
                fig = px.bar(df_chart, x='kategorie', y='gesamtwert',
                           title="Gesamtwert nach Kategorien")
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                pass
        
        # Age-based valuations
        if valuation_data.get('age_valuations'):
            st.subheader("📅 Bewertung nach Alter (Abschreibung)")
            
            df_age = pd.DataFrame(valuation_data['age_valuations'])
            
            # Format currency columns
            for col in ['gesamtwert', 'durchschnittspreis']:
                if col in df_age.columns:
                    df_age[col] = df_age[col].apply(lambda x: format_currency(x) if x else "€0.00")
            
            df_age.columns = ['Altersgruppe', 'Anzahl', 'Gesamtwert', 'Durchschnitt']
            st.dataframe(df_age, use_container_width=True)
        
        st.divider()
        
        # Generate valuation reports
        st.subheader("📄 Bewertungsberichte Generieren")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📑 PDF Bewertungsbericht",
                        disabled=not deps_status["reportlab"],
                        use_container_width=True):
                try:
                    with st.spinner("Generiere PDF Bewertungsbericht..."):
                        pdf_buffer = report_service.generate_valuation_report_pdf(valuation_data)
                        
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"bewertungsbericht_{timestamp}.pdf"
                    
                    st.download_button(
                        label="📥 PDF Herunterladen",
                        data=pdf_buffer.getvalue(),
                        file_name=filename,
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    st.success("PDF Bewertungsbericht erfolgreich generiert!")
                    
                except Exception as e:
                    st.error(f"Fehler beim Generieren des PDF Bewertungsberichts: {e}")
        
        with col2:
            if st.button("📊 Excel Bewertungsbericht",
                        disabled=not (deps_status["pandas"] and deps_status["openpyxl"]),
                        use_container_width=True):
                st.info("Excel Bewertungsberichte werden bald verfügbar sein.")
    
    else:
        st.warning("Keine Bewertungsdaten verfügbar.")


def show_location_reports(report_service, deps_status: Dict[str, bool]):
    """Show location-based reports tab"""
    st.header("📍 Standortberichte")
    st.write("Analysen basierend auf Standorten und geografischer Verteilung.")
    
    # Get summary data for location info
    with st.spinner("Lade Standortdaten..."):
        summary_data = report_service.get_summary_data()
    
    if summary_data and summary_data.get('location_summary'):
        st.subheader("📊 Standort Übersicht")
        
        import pandas as pd
        df_locations = pd.DataFrame(summary_data['location_summary'])
        df_locations.columns = ['Standort', 'Gesamt Items', 'Hardware', 'Kabel']
        
        st.dataframe(df_locations, use_container_width=True)
        
        # Chart if possible
        try:
            import plotly.express as px
            fig = px.bar(df_locations, x='Standort', y='Gesamt Items',
                       title="Items pro Standort")
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            pass
        
        st.info("Erweiterte Standortberichte werden in einer zukünftigen Version verfügbar sein.")
    
    else:
        st.warning("Keine Standortdaten verfügbar.")


def show_audit_reports(report_service, deps_status: Dict[str, bool]):
    """Show audit reports tab"""
    st.header("🔍 Audit Berichte")
    st.write("Audit Trail und Änderungshistorie Berichte.")
    
    # Date range for audit reports
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("Von Datum", value=datetime.now().date())
    
    with col2:
        end_date = st.date_input("Bis Datum", value=datetime.now().date())
    
    if st.button("🔍 Audit Bericht Generieren", use_container_width=True):
        st.info("Audit Berichte werden in einer zukünftigen Version verfügbar sein.")
        
        # Placeholder for audit report generation
        with st.expander("🔍 Audit Trail Vorschau"):
            st.write("Hier würden die Audit Trail Einträge für den ausgewählten Zeitraum angezeigt.")


def show_maintenance_reports(report_service, deps_status: Dict[str, bool]):
    """Show maintenance and warranty reports tab"""
    st.header("🔧 Wartungsberichte")
    st.write("Garantie-Status, Wartungsbedarf und Lebenszyklus-Analysen.")
    
    # Get maintenance data
    with st.spinner("Lade Wartungsdaten..."):
        maintenance_data = report_service.get_maintenance_data()
    
    if maintenance_data:
        # Warranty status overview
        if maintenance_data.get('warranty_status'):
            st.subheader("🛡️ Garantie Status Übersicht")
            
            import pandas as pd
            df_warranty = pd.DataFrame(maintenance_data['warranty_status'])
            
            # Format currency
            df_warranty['gesamtwert'] = df_warranty['gesamtwert'].apply(
                lambda x: format_currency(x) if x else "€0.00"
            )
            
            df_warranty.columns = ['Garantie Status', 'Anzahl', 'Gesamtwert']
            st.dataframe(df_warranty, use_container_width=True)
            
            # Pie chart if possible
            try:
                import plotly.express as px
                fig = px.pie(df_warranty, values='Anzahl', names='Garantie Status',
                           title="Garantie Status Verteilung")
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                pass
        
        # Upcoming warranty expirations
        if maintenance_data.get('warranty_expiring'):
            st.subheader("⚠️ Bald Ablaufende Garantien")
            
            df_expiring = pd.DataFrame(maintenance_data['warranty_expiring'])
            
            if not df_expiring.empty:
                # Format data for display
                df_display = df_expiring.copy()
                if 'preis' in df_display.columns:
                    df_display['preis'] = df_display['preis'].apply(
                        lambda x: format_currency(x) if x else "€0.00"
                    )
                if 'garantie_ende' in df_display.columns:
                    df_display['garantie_ende'] = pd.to_datetime(df_display['garantie_ende']).dt.strftime('%d.%m.%Y')
                if 'tage_bis_ablauf' in df_display.columns:
                    df_display['tage_bis_ablauf'] = df_display['tage_bis_ablauf'].round().astype(int)
                
                df_display.columns = ['Seriennummer', 'Hersteller', 'Modell', 'Garantie Ende', 'Preis', 'Tage bis Ablauf']
                st.dataframe(df_display, use_container_width=True)
            else:
                st.success("Keine Garantien laufen in den nächsten 180 Tagen ab.")
        
        # Age distribution
        if maintenance_data.get('age_distribution'):
            st.subheader("📅 Altersverteilung")
            
            df_age = pd.DataFrame(maintenance_data['age_distribution'])
            df_age.columns = ['Altersgruppe', 'Anzahl']
            
            st.dataframe(df_age, use_container_width=True)
            
            # Chart if possible
            try:
                import plotly.express as px
                fig = px.bar(df_age, x='Altersgruppe', y='Anzahl',
                           title="Hardware Altersverteilung")
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                pass
        
        st.info("Erweiterte Wartungsberichte werden in einer zukünftigen Version verfügbar sein.")
    
    else:
        st.warning("Keine Wartungsdaten verfügbar.")
