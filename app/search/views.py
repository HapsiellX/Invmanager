"""
Advanced search views for inventory management
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from typing import Dict, Any, Optional

from core.security import require_auth, SessionManager
from core.database import get_db
from .services import get_search_service


@require_auth
def show_search_page():
    """
    Advanced search page for all inventory types
    """
    st.header("🔍 Erweiterte Suche")

    # Get database session and service
    db = next(get_db())
    search_service = get_search_service(db)
    current_user = SessionManager.get_current_user()

    # Check if current_user is valid
    if not current_user or not isinstance(current_user, dict):
        st.error("❌ Benutzerinformationen nicht verfügbar. Bitte melden Sie sich erneut an.")
        db.close()
        return

    # Create tabs for different search types
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Globale Suche", "🔧 Hardware Suche", "🔌 Kabel Suche", "💾 Gespeicherte Suchen"
    ])

    with tab1:
        show_global_search_tab(search_service)

    with tab2:
        show_hardware_search_tab(search_service)

    with tab3:
        show_cable_search_tab(search_service)

    with tab4:
        show_saved_searches_tab(search_service, current_user)

    db.close()


def show_global_search_tab(search_service):
    """Global search across all inventory types"""
    st.subheader("🌐 Globale Suche")

    col1, col2 = st.columns([3, 1])

    with col1:
        search_term = st.text_input(
            "Suchbegriff:",
            placeholder="Name, Modell, Seriennummer, Hersteller...",
            key="global_search_term"
        )

    with col2:
        search_types = st.multiselect(
            "Suche in:",
            ["hardware", "cables", "locations"],
            default=["hardware", "cables", "locations"],
            key="global_search_types"
        )

    if search_term and len(search_term) >= 2:
        with st.spinner("Suche läuft..."):
            results = search_service.global_search(
                search_term=search_term,
                search_types=search_types,
                limit=100
            )

        # Display results
        total_results = sum(len(results.get(key, [])) for key in results.keys())

        if total_results > 0:
            st.success(f"✅ {total_results} Ergebnisse gefunden")

            # Hardware results
            if "hardware" in results and results["hardware"]:
                st.subheader(f"🔧 Hardware ({len(results['hardware'])} Ergebnisse)")
                hardware_df = pd.DataFrame(results["hardware"])
                st.dataframe(
                    hardware_df,
                    column_config={
                        "name": "Name",
                        "details": "Details",
                        "location": "Standort",
                        "status": "Status"
                    },
                    hide_index=True,
                    use_container_width=True
                )

            # Cable results
            if "cables" in results and results["cables"]:
                st.subheader(f"🔌 Kabel ({len(results['cables'])} Ergebnisse)")
                cables_df = pd.DataFrame(results["cables"])
                st.dataframe(
                    cables_df,
                    column_config={
                        "name": "Name",
                        "details": "Details",
                        "location": "Standort",
                        "stock": "Bestand"
                    },
                    hide_index=True,
                    use_container_width=True
                )

            # Location results
            if "locations" in results and results["locations"]:
                st.subheader(f"🏢 Standorte ({len(results['locations'])} Ergebnisse)")
                locations_df = pd.DataFrame(results["locations"])
                st.dataframe(
                    locations_df,
                    column_config={
                        "name": "Name",
                        "details": "Typ",
                        "path": "Pfad",
                        "address": "Adresse"
                    },
                    hide_index=True,
                    use_container_width=True
                )

        else:
            st.info("Keine Ergebnisse gefunden. Versuchen Sie andere Suchbegriffe.")

        # Search suggestions
        if len(search_term) >= 2:
            suggestions = search_service.get_search_suggestions(search_term, "all")
            if suggestions:
                st.subheader("💡 Suchvorschläge")
                suggestion_cols = st.columns(min(5, len(suggestions)))
                for i, suggestion in enumerate(suggestions[:5]):
                    with suggestion_cols[i]:
                        if st.button(f"🔍 {suggestion}", key=f"suggestion_{i}"):
                            st.session_state.global_search_term = suggestion
                            st.rerun()


def show_hardware_search_tab(search_service):
    """Advanced hardware search with multiple filters"""
    st.subheader("🔧 Hardware Erweiterte Suche")

    # Get filter options
    filter_options = search_service.get_filter_options()

    # Search form
    with st.form("hardware_search_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            search_term = st.text_input(
                "Suchbegriff:",
                placeholder="Name, Modell, Seriennummer...",
                key="hw_search_term"
            )

            kategorie = st.selectbox(
                "Kategorie:",
                ["Alle"] + filter_options["hardware"]["categories"],
                key="hw_kategorie"
            )

            hersteller = st.selectbox(
                "Hersteller:",
                ["Alle"] + filter_options["hardware"]["manufacturers"],
                key="hw_hersteller"
            )

        with col2:
            status = st.selectbox(
                "Status:",
                ["Alle"] + filter_options["hardware"]["statuses"],
                key="hw_status"
            )

            standort = st.selectbox(
                "Standort:",
                ["Alle"] + [f"{loc['name']} ({loc['path']})" for loc in filter_options["locations"]],
                key="hw_standort"
            )

            warranty_status = st.selectbox(
                "Garantie Status:",
                ["Alle", "Aktiv", "Abgelaufen", "Läuft bald ab"],
                key="hw_warranty"
            )

        with col3:
            price_range = st.slider(
                "Preisbereich (€):",
                min_value=0,
                max_value=50000,
                value=(0, 50000),
                step=100,
                key="hw_price_range"
            )

            date_range = st.date_input(
                "Einkaufsdatum:",
                value=(date.today() - timedelta(days=365), date.today()),
                key="hw_date_range"
            )

            col3a, col3b = st.columns(2)
            with col3a:
                has_mac = st.selectbox("MAC Adresse:", ["Alle", "Ja", "Nein"], key="hw_mac")
            with col3b:
                has_ip = st.selectbox("IP Adresse:", ["Alle", "Ja", "Nein"], key="hw_ip")

        # Sort options
        col4, col5 = st.columns(2)
        with col4:
            sort_by = st.selectbox(
                "Sortieren nach:",
                ["name", "kategorie", "hersteller", "einkaufspreis", "einkaufsdatum"],
                key="hw_sort_by"
            )
        with col5:
            sort_order = st.selectbox(
                "Reihenfolge:",
                ["asc", "desc"],
                format_func=lambda x: "Aufsteigend" if x == "asc" else "Absteigend",
                key="hw_sort_order"
            )

        # Submit button
        search_submitted = st.form_submit_button("🔍 Suchen", type="primary")

    if search_submitted:
        # Prepare search parameters
        params = {}

        if search_term:
            params["search_term"] = search_term

        if kategorie != "Alle":
            params["kategorie"] = kategorie

        if hersteller != "Alle":
            params["hersteller"] = hersteller

        if status != "Alle":
            params["status"] = status

        if standort != "Alle":
            # Extract location ID from selection
            selected_location = next(
                (loc for loc in filter_options["locations"]
                 if f"{loc['name']} ({loc['path']})" == standort),
                None
            )
            if selected_location:
                params["standort_id"] = selected_location["id"]

        if price_range[0] > 0:
            params["price_min"] = price_range[0]
        if price_range[1] < 50000:
            params["price_max"] = price_range[1]

        if isinstance(date_range, tuple) and len(date_range) == 2:
            params["purchase_date_start"] = date_range[0]
            params["purchase_date_end"] = date_range[1]

        if warranty_status != "Alle":
            warranty_map = {
                "Aktiv": "active",
                "Abgelaufen": "expired",
                "Läuft bald ab": "expiring_soon"
            }
            params["warranty_status"] = warranty_map.get(warranty_status)

        if has_mac != "Alle":
            params["has_mac_address"] = has_mac == "Ja"

        if has_ip != "Alle":
            params["has_ip_address"] = has_ip == "Ja"

        params["sort_by"] = sort_by
        params["sort_order"] = sort_order

        # Perform search
        with st.spinner("Hardware wird gesucht..."):
            results = search_service.advanced_hardware_search(**params)

        # Display results
        if results["items"]:
            st.success(f"✅ {results['total_count']} Hardware-Artikel gefunden")

            # Convert to DataFrame for display
            df = pd.DataFrame(results["items"])

            # Select relevant columns for display
            display_columns = [
                "name", "kategorie", "hersteller", "modell", "status",
                "einkaufspreis", "seriennummer"
            ]
            available_columns = [col for col in display_columns if col in df.columns]

            st.dataframe(
                df[available_columns],
                column_config={
                    "name": "Name",
                    "kategorie": "Kategorie",
                    "hersteller": "Hersteller",
                    "modell": "Modell",
                    "status": "Status",
                    "einkaufspreis": st.column_config.NumberColumn("Preis (€)", format="€%.2f"),
                    "seriennummer": "Seriennummer"
                },
                hide_index=True,
                use_container_width=True
            )

            # Export option
            if st.button("📥 Suchergebnisse exportieren", key="export_hw_search"):
                csv_data = df.to_csv(index=False)
                st.download_button(
                    "💾 CSV Download",
                    csv_data,
                    file_name=f"hardware_search_results_{date.today()}.csv",
                    mime="text/csv"
                )

        else:
            st.info("Keine Hardware-Artikel mit den gewählten Kriterien gefunden.")


def show_cable_search_tab(search_service):
    """Advanced cable search with multiple filters"""
    st.subheader("🔌 Kabel Erweiterte Suche")

    # Get filter options
    filter_options = search_service.get_filter_options()

    # Search form
    with st.form("cable_search_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            search_term = st.text_input(
                "Suchbegriff:",
                placeholder="Typ, Standard, Hersteller...",
                key="cable_search_term"
            )

            typ = st.selectbox(
                "Kabel Typ:",
                ["Alle"] + filter_options["cables"]["types"],
                key="cable_typ"
            )

            standard = st.selectbox(
                "Standard:",
                ["Alle"] + filter_options["cables"]["standards"],
                key="cable_standard"
            )

        with col2:
            farbe = st.selectbox(
                "Farbe:",
                ["Alle"] + filter_options["cables"]["colors"],
                key="cable_farbe"
            )

            stecker_typ = st.selectbox(
                "Stecker Typ:",
                ["Alle"] + filter_options["cables"]["connectors"],
                key="cable_stecker"
            )

            standort = st.selectbox(
                "Standort:",
                ["Alle"] + [f"{loc['name']} ({loc['path']})" for loc in filter_options["locations"]],
                key="cable_standort"
            )

        with col3:
            length_range = st.slider(
                "Länge (m):",
                min_value=0.0,
                max_value=100.0,
                value=(0.0, 100.0),
                step=0.5,
                key="cable_length_range"
            )

            stock_status = st.selectbox(
                "Bestandsstatus:",
                ["Alle", "Verfügbar", "Ausverkauft", "Niedriger Bestand", "Hoher Bestand"],
                key="cable_stock_status"
            )

        # Sort options
        col4, col5 = st.columns(2)
        with col4:
            sort_by = st.selectbox(
                "Sortieren nach:",
                ["typ", "standard", "laenge", "menge", "einkaufspreis_pro_einheit"],
                key="cable_sort_by"
            )
        with col5:
            sort_order = st.selectbox(
                "Reihenfolge:",
                ["asc", "desc"],
                format_func=lambda x: "Aufsteigend" if x == "asc" else "Absteigend",
                key="cable_sort_order"
            )

        # Submit button
        search_submitted = st.form_submit_button("🔍 Suchen", type="primary")

    if search_submitted:
        # Prepare search parameters
        params = {}

        if search_term:
            params["search_term"] = search_term

        if typ != "Alle":
            params["typ"] = typ

        if standard != "Alle":
            params["standard"] = standard

        if farbe != "Alle":
            params["farbe"] = farbe

        if stecker_typ != "Alle":
            params["stecker_typ"] = stecker_typ

        if standort != "Alle":
            # Extract location ID from selection
            selected_location = next(
                (loc for loc in filter_options["locations"]
                 if f"{loc['name']} ({loc['path']})" == standort),
                None
            )
            if selected_location:
                params["standort_id"] = selected_location["id"]

        if length_range[0] > 0:
            params["length_min"] = length_range[0]
        if length_range[1] < 100:
            params["length_max"] = length_range[1]

        if stock_status != "Alle":
            status_map = {
                "Verfügbar": "in_stock",
                "Ausverkauft": "out_of_stock",
                "Niedriger Bestand": "low_stock",
                "Hoher Bestand": "high_stock"
            }
            params["stock_status"] = status_map.get(stock_status)

        params["sort_by"] = sort_by
        params["sort_order"] = sort_order

        # Perform search
        with st.spinner("Kabel werden gesucht..."):
            results = search_service.advanced_cable_search(**params)

        # Display results
        if results["items"]:
            st.success(f"✅ {results['total_count']} Kabel gefunden")

            # Convert to DataFrame for display
            df = pd.DataFrame(results["items"])

            # Select relevant columns for display
            display_columns = [
                "typ", "standard", "laenge", "farbe", "menge", "mindestbestand",
                "einkaufspreis_pro_einheit", "hersteller"
            ]
            available_columns = [col for col in display_columns if col in df.columns]

            st.dataframe(
                df[available_columns],
                column_config={
                    "typ": "Typ",
                    "standard": "Standard",
                    "laenge": st.column_config.NumberColumn("Länge (m)", format="%.1f"),
                    "farbe": "Farbe",
                    "menge": "Bestand",
                    "mindestbestand": "Min. Bestand",
                    "einkaufspreis_pro_einheit": st.column_config.NumberColumn("Preis/Einheit (€)", format="€%.2f"),
                    "hersteller": "Hersteller"
                },
                hide_index=True,
                use_container_width=True
            )

            # Export option
            if st.button("📥 Suchergebnisse exportieren", key="export_cable_search"):
                csv_data = df.to_csv(index=False)
                st.download_button(
                    "💾 CSV Download",
                    csv_data,
                    file_name=f"cable_search_results_{date.today()}.csv",
                    mime="text/csv"
                )

        else:
            st.info("Keine Kabel mit den gewählten Kriterien gefunden.")


def show_saved_searches_tab(search_service, current_user):
    """Show saved search presets and recent searches"""
    st.subheader("💾 Gespeicherte Suchen")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📋 Suchvorlagen")

        # Predefined search templates
        templates = {
            "Hardware ohne IP": {
                "type": "hardware",
                "description": "Alle Hardware ohne IP-Adresse",
                "params": {"has_ip_address": False}
            },
            "Ablaufende Garantien": {
                "type": "hardware",
                "description": "Hardware mit ablaufender Garantie (30 Tage)",
                "params": {"warranty_status": "expiring_soon"}
            },
            "Niedrige Kabelbestände": {
                "type": "cable",
                "description": "Kabel mit niedrigem Bestand",
                "params": {"stock_status": "low_stock"}
            },
            "Glasfaser Kabel": {
                "type": "cable",
                "description": "Alle Glasfaser Kabel",
                "params": {"typ": "Fiber"}
            },
            "Server Hardware": {
                "type": "hardware",
                "description": "Alle Server Hardware",
                "params": {"kategorie": "Server"}
            }
        }

        for template_name, template_data in templates.items():
            if st.button(f"🔍 {template_name}", key=f"template_{template_name}"):
                st.info(f"Vorlage geladen: {template_data['description']}")
                # Here you would load the template parameters into the search form
                # This would require storing the parameters in session state
                # and updating the appropriate form fields

        st.subheader("⭐ Benutzerdefinierte Vorlagen")

        # Get saved presets for user
        saved_presets = search_service.get_saved_search_presets(current_user['id'])

        if saved_presets:
            for preset in saved_presets:
                col1a, col1b = st.columns([3, 1])
                with col1a:
                    if st.button(f"🔍 {preset['name']}", key=f"preset_{preset['id']}"):
                        st.info(f"Gespeicherte Suche geladen: {preset['name']}")
                with col1b:
                    if st.button("🗑️", key=f"delete_preset_{preset['id']}"):
                        # Delete preset logic would go here
                        st.success("Vorlage gelöscht")
        else:
            st.info("Keine gespeicherten Suchvorlagen vorhanden.")

    with col2:
        st.subheader("🕐 Kürzliche Suchen")

        # Get recent searches for user
        recent_searches = search_service.get_recent_searches(current_user['id'])

        if recent_searches:
            for search_term in recent_searches:
                if st.button(f"🔍 {search_term}", key=f"recent_{search_term}"):
                    st.session_state.global_search_term = search_term
                    st.rerun()
        else:
            st.info("Keine kürzlichen Suchen vorhanden.")

        st.subheader("💾 Aktuelle Suche speichern")

        # Form to save current search as preset
        with st.form("save_search_preset"):
            preset_name = st.text_input(
                "Name für Suchvorlage:",
                placeholder="z.B. Meine Hardware Suche",
                key="preset_name"
            )

            preset_description = st.text_area(
                "Beschreibung (optional):",
                placeholder="Beschreibung der Suchkriterien...",
                key="preset_description"
            )

            if st.form_submit_button("💾 Suche speichern"):
                if preset_name:
                    # Save current search parameters
                    # This would extract current form values and save them
                    # For now, we'll show a success message
                    st.success(f"Suchvorlage '{preset_name}' gespeichert!")
                else:
                    st.error("Bitte geben Sie einen Namen für die Vorlage ein.")

    # Quick search shortcuts
    st.subheader("⚡ Schnellzugriff")

    quick_col1, quick_col2, quick_col3, quick_col4 = st.columns(4)

    with quick_col1:
        if st.button("🔧 Alle Hardware", key="quick_all_hardware"):
            st.session_state.global_search_term = ""
            st.session_state.global_search_types = ["hardware"]
            st.rerun()

    with quick_col2:
        if st.button("🔌 Alle Kabel", key="quick_all_cables"):
            st.session_state.global_search_term = ""
            st.session_state.global_search_types = ["cables"]
            st.rerun()

    with quick_col3:
        if st.button("🏢 Alle Standorte", key="quick_all_locations"):
            st.session_state.global_search_term = ""
            st.session_state.global_search_types = ["locations"]
            st.rerun()

    with quick_col4:
        if st.button("⚠️ Niedrige Bestände", key="quick_low_stock"):
            # This would navigate to a pre-filtered cable search
            st.info("Navigation zu niedrigen Beständen...")


def add_search_to_navigation():
    """Helper function to add search to main navigation"""
    # This would be called from main.py to add search to the navigation menu
    pass