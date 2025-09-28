"""
Hardware inventory views
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from typing import Optional

from core.security import require_auth, SessionManager
from core.database import get_db
from .services import get_hardware_service


@require_auth
def show_hardware_page():
    """
    Hardware inventory management page
    """
    st.header("🖥️ Hardware Inventar")

    # Get database connection and service
    db = next(get_db())
    hardware_service = get_hardware_service(db)

    # Tabs for different operations
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Übersicht", "➕ Neu hinzufügen", "📝 Bearbeiten", "📊 Zusammenfassung"])

    with tab1:
        show_hardware_overview(hardware_service)

    with tab2:
        if SessionManager.has_permission("netzwerker"):
            show_add_hardware(hardware_service)
        else:
            st.error("Sie haben keine Berechtigung zum Hinzufügen von Hardware.")

    with tab3:
        if SessionManager.has_permission("netzwerker"):
            show_edit_hardware(hardware_service)
        else:
            st.error("Sie haben keine Berechtigung zum Bearbeiten von Hardware.")

    with tab4:
        show_hardware_summary(hardware_service)


def show_hardware_overview(hardware_service):
    """Show hardware overview with filters"""
    st.subheader("📋 Hardware Übersicht")

    # Filters
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        locations = ["Alle"] + [loc.name for loc in hardware_service.get_locations()]
        standort_filter = st.selectbox("Standort", locations, key="hw_standort_filter")

    with col2:
        categories = ["Alle"] + hardware_service.get_unique_categories()
        kategorie_filter = st.selectbox("Kategorie", categories, key="hw_kategorie_filter")

    with col3:
        status_options = ["Alle", "verfuegbar", "in_verwendung", "wartung", "ausrangiert"]
        status_filter = st.selectbox("Status", status_options, key="hw_status_filter")

    with col4:
        nur_aktive = st.checkbox("Nur aktive Hardware", value=True, key="hw_nur_aktive")

    # Search
    search_term = st.text_input("🔍 Suchen (Bezeichnung, Hersteller, S/N, Ort)", key="hw_search")

    # Get hardware data
    if search_term:
        hardware_items = hardware_service.search_hardware(search_term)
    else:
        hardware_items = hardware_service.get_all_hardware(
            standort_filter=standort_filter,
            kategorie_filter=kategorie_filter,
            status_filter=status_filter,
            nur_aktive=nur_aktive
        )

    if not hardware_items:
        st.info("Keine Hardware gefunden.")
        return

    # Convert to DataFrame for display
    data = []
    for item in hardware_items:
        data.append({
            "ID": item.id,
            "Bezeichnung": item.vollstaendige_bezeichnung,
            "Kategorie": item.kategorie,
            "Seriennummer": item.seriennummer,
            "Standort": item.standort_pfad,
            "Status": item.status.replace("_", " ").title(),
            "Eingang": item.datum_eingang.strftime("%d.%m.%Y") if item.datum_eingang else "-",
            "Aktiv": "✅" if item.ist_aktiv else "❌"
        })

    df = pd.DataFrame(data)

    # Display data with pagination
    st.write(f"**{len(hardware_items)} Hardware-Elemente gefunden**")

    # Interactive dataframe
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )

    # Show details for selected row
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_hardware = hardware_items[selected_idx]
        show_hardware_details(selected_hardware, hardware_service)


def show_hardware_details(hardware: object, hardware_service):
    """Show detailed view of selected hardware"""
    st.subheader("📋 Hardware Details")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Grundinformationen:**")
        st.write(f"**ID:** {hardware.id}")
        st.write(f"**Bezeichnung:** {hardware.vollstaendige_bezeichnung}")
        st.write(f"**Kategorie:** {hardware.kategorie}")
        st.write(f"**Seriennummer:** {hardware.seriennummer}")
        st.write(f"**Status:** {hardware.status.replace('_', ' ').title()}")

        st.write("**Standort:**")
        st.write(f"**Standort:** {hardware.standort_pfad}")

    with col2:
        st.write("**Zusätzliche Informationen:**")
        if hardware.formfaktor:
            st.write(f"**Formfaktor:** {hardware.formfaktor}")
        if hardware.klassifikation:
            st.write(f"**Klassifikation:** {hardware.klassifikation}")
        if hardware.ip_adresse:
            st.write(f"**IP-Adresse:** {hardware.ip_adresse}")
        if hardware.mac_adresse:
            st.write(f"**MAC-Adresse:** {hardware.mac_adresse}")

        st.write("**Verwaltung:**")
        st.write(f"**Angenommen durch:** {hardware.angenommen_durch}")
        st.write(f"**Datum Eingang:** {hardware.datum_eingang.strftime('%d.%m.%Y %H:%M') if hardware.datum_eingang else '-'}")

    if hardware.besonderheiten:
        st.write("**Besonderheiten:**")
        st.write(hardware.besonderheiten)

    # Action buttons for authorized users
    if SessionManager.has_permission("netzwerker"):
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📝 Bearbeiten", key=f"edit_{hardware.id}"):
                st.session_state.edit_hardware_id = hardware.id
                st.rerun()

        with col2:
            if hardware.ist_aktiv and st.button("🗑️ Ausrangieren", key=f"delete_{hardware.id}"):
                st.session_state.delete_hardware_id = hardware.id
                st.rerun()

        with col3:
            if hardware.status != "wartung" and st.button("🔧 In Wartung", key=f"maintenance_{hardware.id}"):
                current_user = SessionManager.get_current_user()
                hardware.in_wartung_setzen(current_user['id'], "Manuelle Wartung gesetzt")
                st.success("Hardware in Wartung gesetzt.")
                st.rerun()


def show_add_hardware(hardware_service):
    """Show form to add new hardware"""
    st.subheader("➕ Neue Hardware hinzufügen")

    with st.form("add_hardware_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Grundinformationen**")
            bezeichnung = st.text_input("Bezeichnung*", placeholder="z.B. MX204")
            hersteller = st.text_input("Hersteller*", placeholder="z.B. Aruba")
            kategorie = st.selectbox("Kategorie*", ["Switch", "Router", "Firewall", "Transceiver", "Server", "Access Point", "Sonstiges"])
            seriennummer = st.text_input("Seriennummer*", placeholder="Eindeutige Seriennummer")

        with col2:
            st.write("**Standort & Details**")
            locations = hardware_service.get_locations()
            location_options = {f"{loc.name} ({loc.typ})": loc.id for loc in locations}
            standort = st.selectbox("Standort*", list(location_options.keys()))
            ort = st.text_input("Spezifischer Ort*", placeholder="z.B. Lager 1, Schrank 3")
            formfaktor = st.text_input("Formfaktor", placeholder="z.B. 1U, 2U")
            klassifikation = st.text_input("Klassifikation", placeholder="z.B. 24-Port, SFP+")

        col3, col4 = st.columns(2)

        with col3:
            st.write("**Administrative Daten**")
            angenommen_durch = st.text_input("Angenommen durch*", placeholder="Name der Person")
            leistungsschein_nummer = st.text_input("Leistungsschein Nr.", placeholder="Rechnungsnummer")
            datum_eingang = st.date_input("Datum Eingang*", value=date.today())

        with col4:
            st.write("**Technische Daten**")
            ip_adresse = st.text_input("IP-Adresse", placeholder="192.168.1.1")
            mac_adresse = st.text_input("MAC-Adresse", placeholder="00:11:22:33:44:55")
            firmware_version = st.text_input("Firmware Version", placeholder="v1.2.3")

        besonderheiten = st.text_area("Besonderheiten", placeholder="Zusätzliche Informationen...")

        submitted = st.form_submit_button("Hardware hinzufügen", type="primary")

        if submitted:
            # Validation
            if not all([bezeichnung, hersteller, kategorie, seriennummer, standort, ort, angenommen_durch]):
                st.error("Bitte füllen Sie alle Pflichtfelder (*) aus.")
            else:
                try:
                    current_user = SessionManager.get_current_user()
                    hardware_data = {
                        'standort_id': location_options[standort],
                        'ort': ort,
                        'kategorie': kategorie,
                        'bezeichnung': bezeichnung,
                        'hersteller': hersteller,
                        'seriennummer': seriennummer,
                        'formfaktor': formfaktor or None,
                        'klassifikation': klassifikation or None,
                        'besonderheiten': besonderheiten or None,
                        'angenommen_durch': angenommen_durch,
                        'leistungsschein_nummer': leistungsschein_nummer or None,
                        'datum_eingang': datetime.combine(datum_eingang, datetime.min.time()),
                        'ip_adresse': ip_adresse or None,
                        'mac_adresse': mac_adresse or None,
                        'firmware_version': firmware_version or None
                    }

                    new_hardware = hardware_service.create_hardware(hardware_data, current_user['id'])
                    st.success(f"Hardware '{new_hardware.vollstaendige_bezeichnung}' wurde erfolgreich hinzugefügt!")
                    st.rerun()

                except Exception as e:
                    if "duplicate key" in str(e).lower():
                        st.error("Seriennummer bereits vorhanden. Bitte verwenden Sie eine eindeutige Seriennummer.")
                    else:
                        st.error(f"Fehler beim Hinzufügen der Hardware: {str(e)}")


def show_edit_hardware(hardware_service):
    """Show form to edit existing hardware"""
    st.subheader("📝 Hardware bearbeiten")

    # Hardware selection
    hardware_items = hardware_service.get_all_hardware()
    if not hardware_items:
        st.info("Keine Hardware zum Bearbeiten verfügbar.")
        return

    # Check if editing specific hardware
    edit_hardware_id = st.session_state.get('edit_hardware_id')
    if edit_hardware_id:
        selected_hardware = hardware_service.get_hardware_by_id(edit_hardware_id)
        if selected_hardware:
            show_edit_form(selected_hardware, hardware_service)
        st.session_state.pop('edit_hardware_id', None)
    else:
        # Hardware selection dropdown
        hardware_options = {f"{hw.vollstaendige_bezeichnung} (S/N: {hw.seriennummer})": hw for hw in hardware_items}
        selected_hw_key = st.selectbox("Hardware auswählen", list(hardware_options.keys()))

        if selected_hw_key:
            selected_hardware = hardware_options[selected_hw_key]
            show_edit_form(selected_hardware, hardware_service)


def show_edit_form(hardware, hardware_service):
    """Show edit form for specific hardware"""
    with st.form(f"edit_hardware_form_{hardware.id}"):
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Grundinformationen**")
            bezeichnung = st.text_input("Bezeichnung*", value=hardware.bezeichnung)
            hersteller = st.text_input("Hersteller*", value=hardware.hersteller)
            kategorie = st.selectbox("Kategorie*",
                                   ["Switch", "Router", "Firewall", "Transceiver", "Server", "Access Point", "Sonstiges"],
                                   index=["Switch", "Router", "Firewall", "Transceiver", "Server", "Access Point", "Sonstiges"].index(hardware.kategorie) if hardware.kategorie in ["Switch", "Router", "Firewall", "Transceiver", "Server", "Access Point", "Sonstiges"] else 0)
            seriennummer = st.text_input("Seriennummer*", value=hardware.seriennummer)

        with col2:
            st.write("**Standort & Details**")
            locations = hardware_service.get_locations()
            location_options = {f"{loc.name} ({loc.typ})": loc.id for loc in locations}
            current_location_key = next((k for k, v in location_options.items() if v == hardware.standort_id), list(location_options.keys())[0])
            standort = st.selectbox("Standort*", list(location_options.keys()),
                                  index=list(location_options.keys()).index(current_location_key))
            ort = st.text_input("Spezifischer Ort*", value=hardware.ort)
            formfaktor = st.text_input("Formfaktor", value=hardware.formfaktor or "")
            klassifikation = st.text_input("Klassifikation", value=hardware.klassifikation or "")

        # Status
        status_options = ["verfuegbar", "in_verwendung", "wartung", "ausrangiert"]
        current_status_idx = status_options.index(hardware.status) if hardware.status in status_options else 0
        status = st.selectbox("Status", status_options, index=current_status_idx)

        # Technical data
        col3, col4 = st.columns(2)
        with col3:
            ip_adresse = st.text_input("IP-Adresse", value=hardware.ip_adresse or "")
            mac_adresse = st.text_input("MAC-Adresse", value=hardware.mac_adresse or "")

        with col4:
            firmware_version = st.text_input("Firmware Version", value=hardware.firmware_version or "")
            angenommen_durch = st.text_input("Angenommen durch*", value=hardware.angenommen_durch)

        besonderheiten = st.text_area("Besonderheiten", value=hardware.besonderheiten or "")

        col_submit, col_delete = st.columns([3, 1])

        with col_submit:
            submitted = st.form_submit_button("Änderungen speichern", type="primary")

        with col_delete:
            if hardware.ist_aktiv:
                delete_clicked = st.form_submit_button("🗑️ Ausrangieren", type="secondary")
            else:
                delete_clicked = False

        if submitted:
            if not all([bezeichnung, hersteller, kategorie, seriennummer, standort, ort, angenommen_durch]):
                st.error("Bitte füllen Sie alle Pflichtfelder (*) aus.")
            else:
                try:
                    current_user = SessionManager.get_current_user()
                    update_data = {
                        'standort_id': location_options[standort],
                        'ort': ort,
                        'kategorie': kategorie,
                        'bezeichnung': bezeichnung,
                        'hersteller': hersteller,
                        'seriennummer': seriennummer,
                        'formfaktor': formfaktor or None,
                        'klassifikation': klassifikation or None,
                        'besonderheiten': besonderheiten or None,
                        'angenommen_durch': angenommen_durch,
                        'status': status,
                        'ip_adresse': ip_adresse or None,
                        'mac_adresse': mac_adresse or None,
                        'firmware_version': firmware_version or None
                    }

                    updated_hardware = hardware_service.update_hardware(hardware.id, update_data, current_user['id'])
                    if updated_hardware:
                        st.success(f"Hardware '{updated_hardware.vollstaendige_bezeichnung}' wurde erfolgreich aktualisiert!")
                        st.rerun()
                    else:
                        st.error("Fehler beim Aktualisieren der Hardware.")

                except Exception as e:
                    st.error(f"Fehler beim Aktualisieren der Hardware: {str(e)}")

        if delete_clicked:
            st.session_state.confirm_delete_hardware_id = hardware.id
            st.rerun()

    # Handle delete confirmation
    if st.session_state.get('confirm_delete_hardware_id') == hardware.id:
        st.warning(f"Möchten Sie die Hardware '{hardware.vollstaendige_bezeichnung}' wirklich ausrangieren?")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Ja, ausrangieren"):
                current_user = SessionManager.get_current_user()
                if hardware_service.delete_hardware(hardware.id, current_user['id'], "Ausrangiert über Web-Interface"):
                    st.success("Hardware wurde erfolgreich ausrangiert.")
                    st.session_state.pop('confirm_delete_hardware_id', None)
                    st.rerun()
                else:
                    st.error("Fehler beim Ausrangieren der Hardware.")

        with col2:
            if st.button("❌ Abbrechen"):
                st.session_state.pop('confirm_delete_hardware_id', None)
                st.rerun()


def show_hardware_summary(hardware_service):
    """Show hardware inventory summary and statistics"""
    st.subheader("📊 Hardware Zusammenfassung")

    # Get summary data
    summary = hardware_service.get_inventory_summary()

    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Gesamt Hardware", summary['total_hardware'])

    with col2:
        verfuegbar = summary['by_status'].get('verfuegbar', 0)
        st.metric("Verfügbar", verfuegbar)

    with col3:
        in_verwendung = summary['by_status'].get('in_verwendung', 0)
        st.metric("In Verwendung", in_verwendung)

    with col4:
        wartung = summary['by_status'].get('wartung', 0)
        st.metric("In Wartung", wartung)

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Hardware nach Kategorie")
        if summary['by_category']:
            category_df = pd.DataFrame(list(summary['by_category'].items()), columns=['Kategorie', 'Anzahl'])
            st.bar_chart(category_df.set_index('Kategorie'))
        else:
            st.info("Keine Daten verfügbar")

    with col2:
        st.subheader("Hardware nach Standort")
        if summary['by_location']:
            location_df = pd.DataFrame(list(summary['by_location'].items()), columns=['Standort', 'Anzahl'])
            st.bar_chart(location_df.set_index('Standort'))
        else:
            st.info("Keine Daten verfügbar")

    # Status breakdown
    st.subheader("Status Übersicht")
    if summary['by_status']:
        status_df = pd.DataFrame(list(summary['by_status'].items()), columns=['Status', 'Anzahl'])
        status_df['Status'] = status_df['Status'].str.replace('_', ' ').str.title()
        st.dataframe(status_df, hide_index=True, use_container_width=True)