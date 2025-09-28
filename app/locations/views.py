"""
Location management views for hierarchical location structure
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any

from core.security import require_auth, SessionManager
from core.database import get_db
from locations.services import get_location_service
from database.models.location import Location


@require_auth
def show_locations_page():
    """
    Main location management page
    """
    st.header("📍 Standort-Verwaltung")

    # Get location service
    location_service = get_location_service()

    # Create tabs for different operations
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏗️ Hierarchie",
        "➕ Hinzufügen",
        "✏️ Bearbeiten",
        "📊 Statistiken",
        "🔍 Suchen"
    ])

    with tab1:
        show_location_hierarchy(location_service)

    with tab2:
        show_add_location_form(location_service)

    with tab3:
        show_edit_location_form(location_service)

    with tab4:
        show_location_statistics(location_service)

    with tab5:
        show_location_search(location_service)


def show_location_hierarchy(location_service):
    """Display hierarchical location structure"""
    st.subheader("🏗️ Standort-Hierarchie")

    # Get hierarchy
    hierarchy = location_service.get_location_hierarchy()

    if not hierarchy:
        st.info("Keine Standorte gefunden. Erstellen Sie zunächst einen Hauptstandort.")
        return

    # Display as expandable tree
    for root_node in hierarchy:
        display_location_tree(root_node, location_service, level=0)

    # Quick actions
    st.subheader("⚡ Schnellaktionen")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🏢 Neuen Hauptstandort erstellen", type="primary"):
            st.session_state.location_quick_action = "create_site"
            st.rerun()

    with col2:
        # Location type overview
        st.markdown("**Standort-Typen:**")
        type_counts = {}
        all_locations = location_service.get_all_locations()
        for loc in all_locations:
            type_counts[loc.typ] = type_counts.get(loc.typ, 0) + 1

        for typ, count in type_counts.items():
            st.write(f"• {typ.title()}: {count}")


def display_location_tree(node: Dict[str, Any], location_service, level: int = 0):
    """Recursively display location tree"""
    location = node["location"]
    children = node["children"]

    # Create indentation based on level
    indent = "    " * level

    # Icons for different types
    type_icons = {
        "site": "🏢",
        "building": "🏗️",
        "floor": "🏢",
        "room": "🚪",
        "storage": "📦"
    }

    icon = type_icons.get(location.typ, "📍")

    # Create expandable section for locations with children
    if children:
        with st.expander(f"{indent}{icon} {location.name} ({location.typ})", expanded=level < 2):
            show_location_details(location, location_service, compact=True)

            # Display children
            for child_node in children:
                display_location_tree(child_node, location_service, level + 1)
    else:
        # Leaf location
        st.write(f"{indent}{icon} {location.name} ({location.typ})")
        if st.button(f"Details anzeigen", key=f"details_{location.id}"):
            st.session_state.selected_location_id = location.id
            st.rerun()


def show_location_details(location: Location, location_service, compact: bool = False):
    """Show detailed location information"""
    if compact:
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**ID:** {location.id}")
            if location.beschreibung:
                st.write(f"**Beschreibung:** {location.beschreibung}")
        with col2:
            st.write(f"**Pfad:** {location.vollstaendiger_pfad}")
            st.write(f"**Aktiv:** {'✅' if location.ist_aktiv else '❌'}")
    else:
        # Full details
        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**ID:** {location.id}")
            st.write(f"**Name:** {location.name}")
            st.write(f"**Typ:** {location.typ}")
            st.write(f"**Pfad:** {location.vollstaendiger_pfad}")
            if location.beschreibung:
                st.write(f"**Beschreibung:** {location.beschreibung}")

        with col2:
            if location.adresse:
                st.write(f"**Adresse:** {location.adresse}")
            if location.stadt:
                st.write(f"**Stadt:** {location.stadt} {location.postleitzahl or ''}")
            if location.kontakt_person:
                st.write(f"**Kontakt:** {location.kontakt_person}")
            if location.telefon:
                st.write(f"**Telefon:** {location.telefon}")
            if location.email:
                st.write(f"**E-Mail:** {location.email}")

    # Get statistics
    stats = location_service.get_location_statistics(location.id)
    if stats:
        st.markdown("**Inventar:**")
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Hardware", stats.get('hardware_count', 0))
        with col_stat2:
            st.metric("Kabel", stats.get('cable_count', 0))
        with col_stat3:
            st.metric("Wert", f"€{stats.get('total_value', 0):.2f}")


def show_add_location_form(location_service):
    """Show form to add new location"""
    st.subheader("➕ Neuen Standort hinzufügen")

    with st.form("add_location_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Name*", placeholder="z.B. Hauptgebäude, Serverraum 1")
            typ = st.selectbox("Typ*", ["site", "building", "floor", "room", "storage"],
                             format_func=lambda x: {
                                 "site": "🏢 Standort/Campus",
                                 "building": "🏗️ Gebäude",
                                 "floor": "🏢 Etage",
                                 "room": "🚪 Raum",
                                 "storage": "📦 Lager/Schrank"
                             }.get(x, x))

            # Get available parent locations
            available_parents = location_service.get_available_parent_locations()
            parent_options = [None] + available_parents

            parent = st.selectbox(
                "Übergeordneter Standort",
                options=parent_options,
                format_func=lambda x: "Keine (Hauptstandort)" if x is None else f"{x.vollstaendiger_pfad} ({x.typ})"
            )

            beschreibung = st.text_area("Beschreibung", placeholder="Detaillierte Beschreibung des Standorts")

        with col2:
            # Address information (mainly for sites)
            st.markdown("**Adresse (optional):**")
            adresse = st.text_input("Straße und Hausnummer")
            col_addr1, col_addr2 = st.columns(2)
            with col_addr1:
                postleitzahl = st.text_input("PLZ")
            with col_addr2:
                stadt = st.text_input("Stadt")

            land = st.text_input("Land", value="Deutschland")

            # Contact information
            st.markdown("**Kontakt (optional):**")
            kontakt_person = st.text_input("Ansprechpartner")
            telefon = st.text_input("Telefon")
            email = st.text_input("E-Mail")

        notizen = st.text_area("Notizen", placeholder="Zusätzliche Informationen")

        submitted = st.form_submit_button("Standort erstellen", type="primary")

        if submitted:
            # Validation
            if not name or not typ:
                st.error("Bitte füllen Sie alle Pflichtfelder (*) aus.")
            else:
                # Create location
                location_data = {
                    'name': name,
                    'typ': typ,
                    'parent_id': parent.id if parent else None,
                    'beschreibung': beschreibung if beschreibung else None,
                    'adresse': adresse if adresse else None,
                    'stadt': stadt if stadt else None,
                    'postleitzahl': postleitzahl if postleitzahl else None,
                    'land': land if land else None,
                    'kontakt_person': kontakt_person if kontakt_person else None,
                    'telefon': telefon if telefon else None,
                    'email': email if email else None,
                    'notizen': notizen if notizen else None
                }

                current_user = SessionManager.get_current_user()
                try:
                    new_location = location_service.create_location(location_data, current_user['id'])
                    st.success(f"Standort '{new_location.name}' wurde erfolgreich erstellt!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Erstellen des Standorts: {str(e)}")


def show_edit_location_form(location_service):
    """Show form to edit existing location"""
    st.subheader("✏️ Standort bearbeiten")

    locations = location_service.get_all_locations()
    if not locations:
        st.info("Keine Standorte zum Bearbeiten gefunden.")
        return

    selected_location = st.selectbox(
        "Standort auswählen",
        options=locations,
        format_func=lambda x: f"{x.vollstaendiger_pfad} ({x.typ})",
        key="edit_location_select"
    )

    if selected_location:
        # Show current details
        st.markdown("**Aktuelle Details:**")
        show_location_details(selected_location, location_service)

        with st.form("edit_location_form"):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Name", value=selected_location.name)
                typ = st.selectbox("Typ", ["site", "building", "floor", "room", "storage"],
                                 index=["site", "building", "floor", "room", "storage"].index(selected_location.typ),
                                 format_func=lambda x: {
                                     "site": "🏢 Standort/Campus",
                                     "building": "🏗️ Gebäude",
                                     "floor": "🏢 Etage",
                                     "room": "🚪 Raum",
                                     "storage": "📦 Lager/Schrank"
                                 }.get(x, x))

                # Get available parent locations (excluding self and descendants)
                available_parents = location_service.get_available_parent_locations(selected_location.id)
                parent_options = [None] + available_parents

                current_parent_index = 0
                if selected_location.parent_id:
                    try:
                        current_parent = next(p for p in available_parents if p.id == selected_location.parent_id)
                        current_parent_index = available_parents.index(current_parent) + 1
                    except (StopIteration, ValueError):
                        current_parent_index = 0

                parent = st.selectbox(
                    "Übergeordneter Standort",
                    options=parent_options,
                    index=current_parent_index,
                    format_func=lambda x: "Keine (Hauptstandort)" if x is None else f"{x.vollstaendiger_pfad} ({x.typ})"
                )

                beschreibung = st.text_area("Beschreibung", value=selected_location.beschreibung or "")

            with col2:
                # Address information
                st.markdown("**Adresse:**")
                adresse = st.text_input("Straße und Hausnummer", value=selected_location.adresse or "")
                col_addr1, col_addr2 = st.columns(2)
                with col_addr1:
                    postleitzahl = st.text_input("PLZ", value=selected_location.postleitzahl or "")
                with col_addr2:
                    stadt = st.text_input("Stadt", value=selected_location.stadt or "")

                land = st.text_input("Land", value=selected_location.land or "Deutschland")

                # Contact information
                st.markdown("**Kontakt:**")
                kontakt_person = st.text_input("Ansprechpartner", value=selected_location.kontakt_person or "")
                telefon = st.text_input("Telefon", value=selected_location.telefon or "")
                email = st.text_input("E-Mail", value=selected_location.email or "")

            notizen = st.text_area("Notizen", value=selected_location.notizen or "")

            # Action buttons
            col_btn1, col_btn2, col_btn3 = st.columns(3)

            with col_btn1:
                submitted = st.form_submit_button("Änderungen speichern", type="primary")

            with col_btn2:
                move_location = st.form_submit_button("Nur verschieben", type="secondary")

            with col_btn3:
                if not SessionManager.has_permission("admin"):
                    st.write("") # Placeholder
                else:
                    delete_location = st.form_submit_button("Deaktivieren", type="secondary")

            if submitted:
                # Update location
                update_data = {
                    'name': name,
                    'typ': typ,
                    'parent_id': parent.id if parent else None,
                    'beschreibung': beschreibung if beschreibung else None,
                    'adresse': adresse if adresse else None,
                    'stadt': stadt if stadt else None,
                    'postleitzahl': postleitzahl if postleitzahl else None,
                    'land': land if land else None,
                    'kontakt_person': kontakt_person if kontakt_person else None,
                    'telefon': telefon if telefon else None,
                    'email': email if email else None,
                    'notizen': notizen if notizen else None
                }

                current_user = SessionManager.get_current_user()
                try:
                    updated_location = location_service.update_location(selected_location.id, update_data, current_user['id'])
                    if updated_location:
                        st.success(f"Standort '{updated_location.name}' wurde erfolgreich aktualisiert!")
                        st.rerun()
                    else:
                        st.error("Standort nicht gefunden.")
                except Exception as e:
                    st.error(f"Fehler beim Aktualisieren: {str(e)}")

            elif move_location:
                # Only move to new parent
                if parent and parent.id != selected_location.parent_id:
                    current_user = SessionManager.get_current_user()
                    try:
                        success = location_service.move_location(selected_location.id, parent.id, current_user['id'])
                        if success:
                            st.success(f"Standort '{selected_location.name}' wurde erfolgreich verschoben!")
                            st.rerun()
                        else:
                            st.error("Fehler beim Verschieben des Standorts.")
                    except Exception as e:
                        st.error(f"Fehler beim Verschieben: {str(e)}")
                else:
                    st.warning("Keine Änderung des übergeordneten Standorts erkannt.")

            elif 'delete_location' in locals() and delete_location:
                # Deactivate location
                grund = st.text_input("Grund für Deaktivierung")
                current_user = SessionManager.get_current_user()
                try:
                    success = location_service.delete_location(selected_location.id, current_user['id'], grund)
                    if success:
                        st.success(f"Standort '{selected_location.name}' wurde deaktiviert!")
                        st.rerun()
                    else:
                        st.error("Standort konnte nicht deaktiviert werden. Überprüfen Sie, ob noch Inventar oder Unterstandorte vorhanden sind.")
                except Exception as e:
                    st.error(f"Fehler beim Deaktivieren: {str(e)}")


def show_location_statistics(location_service):
    """Show statistics and analytics for locations"""
    st.subheader("📊 Standort-Statistiken")

    locations = location_service.get_all_locations()
    if not locations:
        st.info("Keine Standorte für Statistiken gefunden.")
        return

    # Overview metrics
    total_locations = len(locations)
    type_counts = {}
    for loc in locations:
        type_counts[loc.typ] = type_counts.get(loc.typ, 0) + 1

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Gesamt Standorte", total_locations)
    with col2:
        st.metric("Hauptstandorte", type_counts.get('site', 0))
    with col3:
        st.metric("Gebäude", type_counts.get('building', 0))
    with col4:
        st.metric("Lagerräume", type_counts.get('storage', 0))

    # Detailed statistics per location
    st.subheader("📋 Detaillierte Standort-Statistiken")

    selected_location = st.selectbox(
        "Standort für Details auswählen",
        options=locations,
        format_func=lambda x: f"{x.vollstaendiger_pfad} ({x.typ})",
        key="stats_location_select"
    )

    if selected_location:
        stats = location_service.get_location_statistics(selected_location.id)

        if stats:
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown("**Inventar-Übersicht:**")

                # Inventory metrics
                col_inv1, col_inv2, col_inv3, col_inv4 = st.columns(4)
                with col_inv1:
                    st.metric("Hardware Items", stats['hardware_count'])
                with col_inv2:
                    st.metric("Kabel Arten", stats['cable_count'])
                with col_inv3:
                    st.metric("Unterstandorte", stats['child_locations'])
                with col_inv4:
                    st.metric("Gesamtwert", f"€{stats['total_value']:.2f}")

                # Hardware by category
                if stats['hardware_by_category']:
                    st.markdown("**Hardware nach Kategorie:**")
                    hw_data = []
                    for kategorie, count in stats['hardware_by_category'].items():
                        hw_data.append({"Kategorie": kategorie, "Anzahl": count})
                    df_hw = pd.DataFrame(hw_data)
                    st.dataframe(df_hw, use_container_width=True, hide_index=True)

                # Cables by type
                if stats['cable_by_type']:
                    st.markdown("**Kabel nach Typ:**")
                    cable_data = []
                    for typ, count in stats['cable_by_type'].items():
                        cable_data.append({"Typ": typ, "Anzahl": count})
                    df_cable = pd.DataFrame(cable_data)
                    st.dataframe(df_cable, use_container_width=True, hide_index=True)

            with col2:
                st.markdown("**Standort-Details:**")
                show_location_details(selected_location, location_service, compact=True)


def show_location_search(location_service):
    """Show location search interface"""
    st.subheader("🔍 Standort-Suche")

    # Search input
    search_term = st.text_input("🔍 Suchbegriff", placeholder="Name, Beschreibung, Adresse oder Stadt...")

    if search_term:
        results = location_service.search_locations(search_term)

        if results:
            st.write(f"**{len(results)} Standorte gefunden:**")

            for location in results:
                with st.expander(f"📍 {location.vollstaendiger_pfad} ({location.typ})"):
                    show_location_details(location, location_service)

                    # Quick actions
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"Bearbeiten", key=f"edit_{location.id}"):
                            st.session_state.edit_location_id = location.id
                            st.rerun()
                    with col2:
                        if st.button(f"Statistiken", key=f"stats_{location.id}"):
                            st.session_state.stats_location_id = location.id
                            st.rerun()
        else:
            st.info("Keine Standorte gefunden.")

    # Browse by type
    st.subheader("📂 Nach Typ durchsuchen")

    type_options = ["site", "building", "floor", "room", "storage"]
    selected_type = st.selectbox(
        "Standort-Typ auswählen",
        options=type_options,
        format_func=lambda x: {
            "site": "🏢 Standorte/Campus",
            "building": "🏗️ Gebäude",
            "floor": "🏢 Etagen",
            "room": "🚪 Räume",
            "storage": "📦 Lager/Schränke"
        }.get(x, x)
    )

    if selected_type:
        locations_by_type = location_service.get_locations_by_type(selected_type)

        if locations_by_type:
            st.write(f"**{len(locations_by_type)} {selected_type} gefunden:**")

            # Display as table
            type_data = []
            for location in locations_by_type:
                type_data.append({
                    "Name": location.name,
                    "Vollständiger Pfad": location.vollstaendiger_pfad,
                    "Stadt": location.stadt or "-",
                    "Kontakt": location.kontakt_person or "-",
                    "ID": location.id
                })

            df_type = pd.DataFrame(type_data)
            st.dataframe(df_type, use_container_width=True, hide_index=True)
        else:
            st.info(f"Keine {selected_type} gefunden.")