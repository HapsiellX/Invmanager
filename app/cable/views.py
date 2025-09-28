"""
Cable inventory views for Streamlit interface
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional

from core.security import require_auth, SessionManager
from core.database import get_db
from cable.services import get_cable_service
from database.models.cable import Cable


@require_auth
def show_cable_inventory():
    """
    Main cable inventory management page
    """
    st.header("🔌 Kabel Inventory")

    # Get database connection and service
    db = next(get_db())
    cable_service = get_cable_service(db)

    # Create tabs for different operations
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📋 Übersicht",
        "➕ Hinzufügen",
        "✏️ Bearbeiten",
        "📊 Zusammenfassung",
        "🔄 Bulk Aktionen",
        "⚙️ Bestandsgrenzen"
    ])

    with tab1:
        show_cable_overview(cable_service)

    with tab2:
        show_add_cable_form(cable_service)

    with tab3:
        show_edit_cable_form(cable_service)

    with tab4:
        show_cable_summary(cable_service)

    with tab5:
        show_bulk_operations(cable_service)

    with tab6:
        show_stock_threshold_management(cable_service)


def show_cable_overview(cable_service):
    """Display cable overview with filtering and search"""
    st.subheader("Kabel Übersicht")

    # Filters
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        standort_options = ["Alle"] + [loc.name for loc in cable_service.get_locations()]
        standort_filter = st.selectbox("Standort", standort_options, key="cable_standort_filter")

    with col2:
        typ_options = ["Alle"] + cable_service.get_unique_types()
        typ_filter = st.selectbox("Typ", typ_options, key="cable_typ_filter")

    with col3:
        standard_options = ["Alle"] + cable_service.get_unique_standards()
        standard_filter = st.selectbox("Standard", standard_options, key="cable_standard_filter")

    with col4:
        health_options = ["Alle", "kritisch", "niedrig", "normal", "hoch"]
        health_filter = st.selectbox("Bestandsstatus", health_options, key="cable_health_filter")

    # Search
    search_term = st.text_input("🔍 Suche", placeholder="Typ, Standard, Hersteller, Modell, Artikel-Nr...")

    # Get cables based on filters
    if search_term:
        cables = cable_service.search_cables(search_term)
    else:
        cables = cable_service.get_all_cables(
            standort_filter=standort_filter,
            typ_filter=typ_filter,
            standard_filter=standard_filter,
            health_filter=health_filter
        )

    if not cables:
        st.info("Keine Kabel gefunden.")
        return

    # Convert to DataFrame for display
    cable_data = []
    for cable in cables:
        status_color = {
            "kritisch": "🔴",
            "niedrig": "🟡",
            "normal": "🟢",
            "hoch": "🟠"
        }.get(cable.health_status, "⚪")

        cable_data.append({
            "ID": cable.id,
            "Bezeichnung": cable.bezeichnung,
            "Typ": cable.typ,
            "Standard": cable.standard,
            "Länge (m)": cable.laenge,
            "Farbe": cable.farbe or "-",
            "Standort": cable.standort.name if cable.standort else "-",
            "Lagerort": cable.lagerort,
            "Menge": cable.menge,
            "Min": cable.mindestbestand,
            "Max": cable.hoechstbestand,
            "Status": f"{status_color} {cable.health_status}",
            "Hersteller": cable.hersteller or "-",
            "Modell": cable.modell or "-",
            "Wert": f"€{cable.gesamtwert:.2f}" if cable.einkaufspreis_pro_einheit else "-"
        })

    df = pd.DataFrame(cable_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Quick stock adjustment
    st.subheader("⚡ Schnelle Bestandsanpassung")

    col1, col2, col3, col4 = st.columns([3, 1, 1, 2])

    with col1:
        selected_cable = st.selectbox(
            "Kabel auswählen",
            options=cables,
            format_func=lambda x: f"{x.bezeichnung} (aktuell: {x.menge})",
            key="quick_cable_select"
        )

    if selected_cable:
        with col2:
            if st.button("➕ +1", key="quick_plus_1"):
                quick_adjust_stock(cable_service, selected_cable.id, 1)
                st.rerun()

        with col3:
            if st.button("➖ -1", key="quick_minus_1") and selected_cable.menge > 0:
                quick_adjust_stock(cable_service, selected_cable.id, -1)
                st.rerun()

        with col4:
            custom_amount = st.number_input("Benutzerdefiniert", min_value=-selected_cable.menge, step=1, key="custom_amount")
            if st.button("Anwenden", key="apply_custom"):
                if custom_amount != 0:
                    quick_adjust_stock(cable_service, selected_cable.id, custom_amount)
                    st.rerun()


def show_add_cable_form(cable_service):
    """Show form to add new cable"""
    st.subheader("Neues Kabel hinzufügen")

    # Get default stock levels from settings
    defaults = cable_service.get_default_stock_levels()

    with st.form("add_cable_form"):
        col1, col2 = st.columns(2)

        with col1:
            typ = st.selectbox("Typ*", ["Fiber", "Copper", "Power", "Coax"], key="add_typ")
            standard = st.text_input("Standard*", placeholder="z.B. Cat6, Cat6a, Single-mode", key="add_standard")
            laenge = st.number_input("Länge (m)*", min_value=0.1, step=0.5, format="%.1f", key="add_laenge")
            farbe = st.text_input("Farbe", placeholder="z.B. Blau, Rot, Gelb", key="add_farbe")

        with col2:
            locations = cable_service.get_locations()
            standort = st.selectbox("Standort*", options=locations, format_func=lambda x: x.name, key="add_standort")
            lagerort = st.text_input("Lagerort*", placeholder="z.B. Lager 1, Regal A", key="add_lagerort")
            hersteller = st.text_input("Hersteller", placeholder="z.B. Panduit, Legrand", key="add_hersteller")
            modell = st.text_input("Modell", placeholder="Modellbezeichnung", key="add_modell")

        # Stock levels
        st.subheader("Bestandsverwaltung")
        col3, col4, col5 = st.columns(3)

        with col3:
            menge = st.number_input("Anfangsbestand*", min_value=0, value=0, step=1, key="add_menge")
        with col4:
            mindestbestand = st.number_input("Mindestbestand*", min_value=0, value=defaults["mindestbestand"], step=1, key="add_mindestbestand", help=f"Standard aus Einstellungen: {defaults['mindestbestand']}")
        with col5:
            hoechstbestand = st.number_input("Höchstbestand*", min_value=1, value=defaults["hoechstbestand"], step=1, key="add_hoechstbestand", help=f"Standard aus Einstellungen: {defaults['hoechstbestand']}")

        # Technical specifications
        st.subheader("Technische Spezifikationen")
        col6, col7 = st.columns(2)

        with col6:
            stecker_typ_a = st.text_input("Stecker Typ A", placeholder="z.B. RJ45, SC, LC", key="add_stecker_a")
            stecker_typ_b = st.text_input("Stecker Typ B", placeholder="z.B. RJ45, SC, LC", key="add_stecker_b")

        with col7:
            einkaufspreis = st.number_input("Einkaufspreis pro Einheit (€)", min_value=0.0, step=0.01, format="%.2f", key="add_preis")
            lieferant = st.text_input("Lieferant", placeholder="Lieferantenname", key="add_lieferant")

        artikel_nummer = st.text_input("Artikel-Nummer", placeholder="Interne oder Lieferanten Artikel-Nr.", key="add_artikel_nr")
        notizen = st.text_area("Notizen", placeholder="Zusätzliche Informationen", key="add_notizen")

        submitted = st.form_submit_button("Kabel hinzufügen", type="primary")

        if submitted:
            # Validation
            if not all([typ, standard, laenge, standort, lagerort]):
                st.error("Bitte füllen Sie alle Pflichtfelder (*) aus.")
            elif mindestbestand >= hoechstbestand:
                st.error("Mindestbestand muss kleiner als Höchstbestand sein.")
            else:
                # Create cable
                cable_data = {
                    'typ': typ,
                    'standard': standard,
                    'laenge': laenge,
                    'standort_id': standort.id,
                    'lagerort': lagerort,
                    'menge': menge,
                    'mindestbestand': mindestbestand,
                    'hoechstbestand': hoechstbestand,
                    'farbe': farbe if farbe else None,
                    'stecker_typ_a': stecker_typ_a if stecker_typ_a else None,
                    'stecker_typ_b': stecker_typ_b if stecker_typ_b else None,
                    'hersteller': hersteller if hersteller else None,
                    'modell': modell if modell else None,
                    'einkaufspreis_pro_einheit': einkaufspreis if einkaufspreis > 0 else None,
                    'lieferant': lieferant if lieferant else None,
                    'artikel_nummer': artikel_nummer if artikel_nummer else None,
                    'notizen': notizen if notizen else None
                }

                current_user = SessionManager.get_current_user()
                try:
                    new_cable = cable_service.create_cable(cable_data, current_user['id'])
                    st.success(f"Kabel {new_cable.bezeichnung} wurde erfolgreich hinzugefügt.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Hinzufügen des Kabels: {str(e)}")


def show_edit_cable_form(cable_service):
    """Show form to edit existing cable"""
    st.subheader("Kabel bearbeiten")

    cables = cable_service.get_all_cables()
    if not cables:
        st.info("Keine Kabel zum Bearbeiten gefunden.")
        return

    selected_cable = st.selectbox(
        "Kabel auswählen",
        options=cables,
        format_func=lambda x: f"{x.bezeichnung} (Bestand: {x.menge})",
        key="edit_cable_select"
    )

    if selected_cable:
        with st.form("edit_cable_form"):
            col1, col2 = st.columns(2)

            with col1:
                typ = st.selectbox("Typ", ["Fiber", "Copper", "Power", "Coax"],
                                 index=["Fiber", "Copper", "Power", "Coax"].index(selected_cable.typ) if selected_cable.typ in ["Fiber", "Copper", "Power", "Coax"] else 0,
                                 key="edit_typ")
                standard = st.text_input("Standard", value=selected_cable.standard, key="edit_standard")
                laenge = st.number_input("Länge (m)", value=float(selected_cable.laenge), min_value=0.1, step=0.5, format="%.1f", key="edit_laenge")
                farbe = st.text_input("Farbe", value=selected_cable.farbe or "", key="edit_farbe")

            with col2:
                locations = cable_service.get_locations()
                current_standort_index = next((i for i, loc in enumerate(locations) if loc.id == selected_cable.standort_id), 0)
                standort = st.selectbox("Standort", options=locations, index=current_standort_index, format_func=lambda x: x.name, key="edit_standort")
                lagerort = st.text_input("Lagerort", value=selected_cable.lagerort, key="edit_lagerort")
                hersteller = st.text_input("Hersteller", value=selected_cable.hersteller or "", key="edit_hersteller")
                modell = st.text_input("Modell", value=selected_cable.modell or "", key="edit_modell")

            # Stock levels with direct adjustment
            st.subheader("Bestandsverwaltung")
            col3, col4, col5, col6 = st.columns(4)

            with col3:
                aktuelle_menge = st.number_input("Aktuelle Menge", value=selected_cable.menge, min_value=0, step=1, key="edit_menge")
            with col4:
                mindestbestand = st.number_input("Mindestbestand", value=selected_cable.mindestbestand, min_value=0, step=1, key="edit_mindestbestand")
            with col5:
                hoechstbestand = st.number_input("Höchstbestand", value=selected_cable.hoechstbestand, min_value=1, step=1, key="edit_hoechstbestand")
            with col6:
                if aktuelle_menge != selected_cable.menge:
                    st.info(f"Bestand ändert sich: {selected_cable.menge} → {aktuelle_menge}")

            # Technical specifications
            st.subheader("Technische Spezifikationen")
            col7, col8 = st.columns(2)

            with col7:
                stecker_typ_a = st.text_input("Stecker Typ A", value=selected_cable.stecker_typ_a or "", key="edit_stecker_a")
                stecker_typ_b = st.text_input("Stecker Typ B", value=selected_cable.stecker_typ_b or "", key="edit_stecker_b")

            with col8:
                einkaufspreis = st.number_input("Einkaufspreis pro Einheit (€)",
                                              value=float(selected_cable.einkaufspreis_pro_einheit) if selected_cable.einkaufspreis_pro_einheit else 0.0,
                                              min_value=0.0, step=0.01, format="%.2f", key="edit_preis")
                lieferant = st.text_input("Lieferant", value=selected_cable.lieferant or "", key="edit_lieferant")

            artikel_nummer = st.text_input("Artikel-Nummer", value=selected_cable.artikel_nummer or "", key="edit_artikel_nr")
            notizen = st.text_area("Notizen", value=selected_cable.notizen or "", key="edit_notizen")

            # Action buttons
            col9, col10, col11 = st.columns(3)

            with col9:
                submitted = st.form_submit_button("Änderungen speichern", type="primary")

            with col10:
                if aktuelle_menge != selected_cable.menge:
                    bestandskorrektur = st.form_submit_button("Nur Bestand korrigieren", type="secondary")
                else:
                    bestandskorrektur = False

            with col11:
                delete_cable = st.form_submit_button("Kabel deaktivieren", type="secondary")

            if submitted or bestandskorrektur:
                # Validation
                if mindestbestand >= hoechstbestand:
                    st.error("Mindestbestand muss kleiner als Höchstbestand sein.")
                else:
                    current_user = SessionManager.get_current_user()

                    try:
                        if bestandskorrektur:
                            # Only adjust stock
                            grund = st.text_input("Grund für Bestandskorrektur", placeholder="z.B. Inventur, Korrektur")
                            if cable_service.set_absolute_stock(selected_cable.id, aktuelle_menge, current_user['id'], grund):
                                st.success(f"Bestand von {selected_cable.bezeichnung} wurde korrigiert.")
                                st.rerun()
                            else:
                                st.error("Fehler bei der Bestandskorrektur.")
                        else:
                            # Update all fields
                            update_data = {
                                'typ': typ,
                                'standard': standard,
                                'laenge': laenge,
                                'standort_id': standort.id,
                                'lagerort': lagerort,
                                'mindestbestand': mindestbestand,
                                'hoechstbestand': hoechstbestand,
                                'farbe': farbe if farbe else None,
                                'stecker_typ_a': stecker_typ_a if stecker_typ_a else None,
                                'stecker_typ_b': stecker_typ_b if stecker_typ_b else None,
                                'hersteller': hersteller if hersteller else None,
                                'modell': modell if modell else None,
                                'einkaufspreis_pro_einheit': einkaufspreis if einkaufspreis > 0 else None,
                                'lieferant': lieferant if lieferant else None,
                                'artikel_nummer': artikel_nummer if artikel_nummer else None,
                                'notizen': notizen if notizen else None
                            }

                            updated_cable = cable_service.update_cable(selected_cable.id, update_data, current_user['id'])

                            # Handle stock change if needed
                            if aktuelle_menge != selected_cable.menge:
                                grund = "Bestandsänderung bei Update"
                                cable_service.set_absolute_stock(selected_cable.id, aktuelle_menge, current_user['id'], grund)

                            if updated_cable:
                                st.success(f"Kabel {updated_cable.bezeichnung} wurde erfolgreich aktualisiert.")
                                st.rerun()
                            else:
                                st.error("Fehler beim Aktualisieren des Kabels.")

                    except Exception as e:
                        st.error(f"Fehler: {str(e)}")

            if delete_cable:
                current_user = SessionManager.get_current_user()
                grund = st.text_input("Grund für Deaktivierung", placeholder="z.B. Beschädigt, Nicht mehr benötigt")

                if cable_service.delete_cable(selected_cable.id, current_user['id'], grund):
                    st.success(f"Kabel {selected_cable.bezeichnung} wurde deaktiviert.")
                    st.rerun()
                else:
                    st.error("Fehler beim Deaktivieren des Kabels.")


def show_cable_summary(cable_service):
    """Display cable inventory summary and statistics"""
    st.subheader("Kabel Inventory Zusammenfassung")

    # Get summary data
    summary = cable_service.get_inventory_summary()

    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
        <h3>Kabel Arten</h3>
        <h2 style="color: #1f77b4;">{summary['total_cables']}</h2>
        <small>Verschiedene Kabel</small>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
        <h3>Gesamtbestand</h3>
        <h2 style="color: #ff7f0e;">{summary['total_stock']}</h2>
        <small>Stück insgesamt</small>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
        <h3>Gesamtwert</h3>
        <h2 style="color: #2ca02c;">€{summary['total_value']:.2f}</h2>
        <small>Aktueller Lagerwert</small>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        critical_count = summary['by_health'].get('kritisch', 0)
        color = "#d62728" if critical_count > 0 else "#2ca02c"
        st.markdown(f"""
        <div class="metric-card">
        <h3>Kritische Bestände</h3>
        <h2 style="color: {color};">{critical_count}</h2>
        <small>Sofort nachbestellen</small>
        </div>
        """, unsafe_allow_html=True)

    # Charts and detailed breakdown
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Verteilung nach Typ")
        if summary['by_type']:
            type_data = []
            for typ, data in summary['by_type'].items():
                type_data.append({
                    "Typ": typ,
                    "Anzahl Artikel": data['count'],
                    "Gesamtbestand": data['stock']
                })

            df_types = pd.DataFrame(type_data)
            st.dataframe(df_types, use_container_width=True, hide_index=True)
        else:
            st.info("Keine Daten verfügbar")

    with col2:
        st.subheader("🚦 Bestandsstatus")
        if summary['by_health']:
            health_data = []
            for status, count in summary['by_health'].items():
                status_emoji = {
                    "kritisch": "🔴",
                    "niedrig": "🟡",
                    "normal": "🟢",
                    "hoch": "🟠"
                }.get(status, "⚪")

                health_data.append({
                    "Status": f"{status_emoji} {status.title()}",
                    "Anzahl": count
                })

            df_health = pd.DataFrame(health_data)
            st.dataframe(df_health, use_container_width=True, hide_index=True)
        else:
            st.info("Keine Daten verfügbar")

    # Low stock alerts
    st.subheader("⚠️ Nachbestellung erforderlich")

    kritische_kabel = cable_service.get_low_stock_cables("kritisch")
    niedrige_kabel = cable_service.get_low_stock_cables("niedrig")

    if kritische_kabel or niedrige_kabel:
        tab1, tab2 = st.tabs(["🔴 Kritisch (leer)", "🟡 Niedrig"])

        with tab1:
            if kritische_kabel:
                critical_data = []
                for cable in kritische_kabel:
                    critical_data.append({
                        "Bezeichnung": cable.bezeichnung,
                        "Standort": cable.standort.name if cable.standort else "-",
                        "Lagerort": cable.lagerort,
                        "Aktuell": cable.menge,
                        "Mindest": cable.mindestbestand
                    })

                df_critical = pd.DataFrame(critical_data)
                st.dataframe(df_critical, use_container_width=True, hide_index=True)
            else:
                st.success("Keine kritischen Bestände!")

        with tab2:
            if niedrige_kabel:
                low_data = []
                for cable in niedrige_kabel:
                    low_data.append({
                        "Bezeichnung": cable.bezeichnung,
                        "Standort": cable.standort.name if cable.standort else "-",
                        "Lagerort": cable.lagerort,
                        "Aktuell": cable.menge,
                        "Mindest": cable.mindestbestand
                    })

                df_low = pd.DataFrame(low_data)
                st.dataframe(df_low, use_container_width=True, hide_index=True)
            else:
                st.success("Alle Bestände ausreichend!")
    else:
        st.success("🎉 Alle Kabelbestände sind ausreichend!")


def show_bulk_operations(cable_service):
    """Show bulk operations for multiple cables"""
    st.subheader("🔄 Bulk Operationen")

    cables = cable_service.get_all_cables()
    if not cables:
        st.info("Keine Kabel für Bulk-Operationen verfügbar.")
        return

    # Cable selection
    st.write("**Kabel auswählen:**")

    # Quick filters for bulk selection
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Alle kritischen auswählen"):
            st.session_state.bulk_cable_ids = [c.id for c in cables if c.health_status == "kritisch"]

    with col2:
        if st.button("Alle niedrigen auswählen"):
            st.session_state.bulk_cable_ids = [c.id for c in cables if c.health_status == "niedrig"]

    with col3:
        if st.button("Auswahl zurücksetzen"):
            st.session_state.bulk_cable_ids = []

    # Initialize session state
    if 'bulk_cable_ids' not in st.session_state:
        st.session_state.bulk_cable_ids = []

    # Manual selection
    selected_cables = st.multiselect(
        "Kabel manuell auswählen",
        options=cables,
        format_func=lambda x: f"{x.bezeichnung} (Bestand: {x.menge})",
        default=[c for c in cables if c.id in st.session_state.bulk_cable_ids],
        key="bulk_manual_select"
    )

    if selected_cables:
        st.write(f"**{len(selected_cables)} Kabel ausgewählt**")

        # Quick increment buttons
        st.subheader("⚡ Schnelle Anpassungen")
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            if st.button("Alle +1"):
                bulk_adjust_with_feedback(cable_service, [c.id for c in selected_cables], 1, "Bulk +1")
                st.rerun()

        with col2:
            if st.button("Alle +5"):
                bulk_adjust_with_feedback(cable_service, [c.id for c in selected_cables], 5, "Bulk +5")
                st.rerun()

        with col3:
            if st.button("Alle +10"):
                bulk_adjust_with_feedback(cable_service, [c.id for c in selected_cables], 10, "Bulk +10")
                st.rerun()

        with col4:
            if st.button("Alle -1"):
                bulk_adjust_with_feedback(cable_service, [c.id for c in selected_cables], -1, "Bulk -1")
                st.rerun()

        with col5:
            if st.button("Alle -5"):
                bulk_adjust_with_feedback(cable_service, [c.id for c in selected_cables], -5, "Bulk -5")
                st.rerun()

        # Custom adjustment
        st.subheader("🛠 Benutzerdefinierte Anpassung")

        with st.form("bulk_adjustment_form"):
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                custom_adjustment = st.number_input("Anpassung", value=0, step=1)

            with col2:
                grund = st.text_input("Grund", placeholder="z.B. Lieferung, Inventur, Verbrauch")

            with col3:
                submitted = st.form_submit_button("Anwenden", type="primary")

            if submitted and custom_adjustment != 0:
                bulk_adjust_with_feedback(cable_service, [c.id for c in selected_cables], custom_adjustment, grund)
                st.rerun()

        # Preview current selection
        st.subheader("📋 Aktuelle Auswahl")
        selection_data = []
        for cable in selected_cables:
            selection_data.append({
                "Bezeichnung": cable.bezeichnung,
                "Aktueller Bestand": cable.menge,
                "Status": cable.health_status,
                "Standort": cable.standort.name if cable.standort else "-"
            })

        df_selection = pd.DataFrame(selection_data)
        st.dataframe(df_selection, use_container_width=True, hide_index=True)


def quick_adjust_stock(cable_service, cable_id: int, adjustment: int):
    """Helper function for quick stock adjustments"""
    current_user = SessionManager.get_current_user()
    grund = f"Schnelle Anpassung ({adjustment:+d})"

    success = cable_service.adjust_stock(cable_id, adjustment, current_user['id'], grund)
    if success:
        st.success(f"Bestand um {adjustment:+d} angepasst")
    else:
        st.error("Anpassung fehlgeschlagen (nicht genügend Bestand?)")


def bulk_adjust_with_feedback(cable_service, cable_ids: List[int], adjustment: int, grund: str):
    """Helper function for bulk adjustments with user feedback"""
    current_user = SessionManager.get_current_user()
    results = cable_service.bulk_stock_adjustment(cable_ids, adjustment, current_user['id'], grund)

    if results['success'] > 0:
        st.success(f"{results['success']} Kabel erfolgreich angepasst")

    if results['failed'] > 0:
        st.warning(f"{results['failed']} Kabel konnten nicht angepasst werden (nicht genügend Bestand?)")


def show_stock_threshold_management(cable_service):
    """Show interface for managing stock thresholds"""
    st.subheader("⚙️ Bestandsgrenzen-Verwaltung")

    # Check permissions
    if not SessionManager.has_permission(["admin", "netzwerker"]):
        st.error("Sie haben keine Berechtigung für diese Funktion.")
        return

    # Get current defaults from settings
    defaults = cable_service.get_default_stock_levels()

    col1, col2 = st.columns([2, 1])

    with col2:
        st.subheader("🎯 Aktuelle Standard-Werte")
        st.info(f"**Mindestbestand:** {defaults['mindestbestand']}")
        st.info(f"**Höchstbestand:** {defaults['hoechstbestand']}")

        if st.button("⚙️ Einstellungen ändern"):
            st.info("Nutzen Sie das Einstellungen-Menü im Hauptmenü, um die Standard-Werte zu ändern.")

    with col1:
        st.subheader("📋 Individuelle Bestandsgrenzen")

        # Get all cables for overview
        cables = cable_service.get_all_cables()

        if not cables:
            st.info("Keine Kabel gefunden.")
            return

        # Convert to DataFrame for editing
        threshold_data = []
        for cable in cables:
            threshold_data.append({
                "ID": cable.id,
                "Bezeichnung": cable.bezeichnung,
                "Typ": cable.typ,
                "Standard": cable.standard,
                "Aktueller Bestand": cable.menge,
                "Mindestbestand": cable.mindestbestand,
                "Höchstbestand": cable.hoechstbestand,
                "Status": cable.health_status
            })

        df = pd.DataFrame(threshold_data)

        # Allow editing of thresholds
        st.markdown("**Aktuelle Bestandsgrenzen:**")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Bulk update interface
        st.subheader("🔄 Bulk-Update Bestandsgrenzen")

        # Filter options
        col_filter1, col_filter2, col_filter3 = st.columns(3)

        with col_filter1:
            typ_filter = st.selectbox("Nach Typ filtern", ["Alle"] + cable_service.get_unique_types(), key="threshold_typ_filter")

        with col_filter2:
            standard_filter = st.selectbox("Nach Standard filtern", ["Alle"] + cable_service.get_unique_standards(), key="threshold_standard_filter")

        with col_filter3:
            health_filter = st.selectbox("Nach Status filtern", ["Alle", "kritisch", "niedrig", "normal", "hoch"], key="threshold_health_filter")

        # Get filtered cables
        filtered_cables = cable_service.get_all_cables(
            typ_filter=typ_filter,
            standard_filter=standard_filter,
            health_filter=health_filter
        )

        st.write(f"**{len(filtered_cables)} Kabel entsprechen den Filtern**")

        # Bulk update form
        with st.form("bulk_threshold_update"):
            st.markdown("**Neue Grenzwerte für gefilterte Kabel:**")

            col_update1, col_update2, col_update3 = st.columns(3)

            with col_update1:
                update_min = st.checkbox("Mindestbestand aktualisieren")
                if update_min:
                    new_min = st.number_input("Neuer Mindestbestand", min_value=0, value=defaults["mindestbestand"], step=1)
                else:
                    new_min = None

            with col_update2:
                update_max = st.checkbox("Höchstbestand aktualisieren")
                if update_max:
                    new_max = st.number_input("Neuer Höchstbestand", min_value=1, value=defaults["hoechstbestand"], step=1)
                else:
                    new_max = None

            with col_update3:
                st.markdown("**Vorschau:**")
                if update_min or update_max:
                    st.write(f"✅ {len(filtered_cables)} Kabel werden aktualisiert")
                    if update_min:
                        st.write(f"• Mindestbestand → {new_min}")
                    if update_max:
                        st.write(f"• Höchstbestand → {new_max}")
                else:
                    st.write("❌ Keine Änderungen ausgewählt")

            submitted = st.form_submit_button("Bestandsgrenzen aktualisieren", type="primary", disabled=not (update_min or update_max))

            if submitted:
                if not (update_min or update_max):
                    st.error("Bitte wählen Sie mindestens eine Grenze zum Aktualisieren aus.")
                elif new_max and new_min and new_min >= new_max:
                    st.error("Mindestbestand muss kleiner als Höchstbestand sein.")
                else:
                    # Prepare updates
                    updates = []
                    for cable in filtered_cables:
                        update_data = {"cable_id": cable.id}
                        if update_min:
                            update_data["mindestbestand"] = new_min
                        if update_max:
                            update_data["hoechstbestand"] = new_max
                        updates.append(update_data)

                    # Perform bulk update
                    current_user = SessionManager.get_current_user()
                    results = cable_service.bulk_update_stock_thresholds(updates, current_user['id'])

                    if results["success"] > 0:
                        st.success(f"✅ {results['success']} Kabel erfolgreich aktualisiert!")

                    if results["failed"] > 0:
                        st.warning(f"⚠️ {results['failed']} Kabel konnten nicht aktualisiert werden.")

                    st.rerun()

        # Individual cable threshold editor
        st.subheader("✏️ Einzelne Kabel bearbeiten")

        selected_cable = st.selectbox(
            "Kabel für individuelle Bearbeitung auswählen",
            options=cables,
            format_func=lambda x: f"{x.bezeichnung} (Min: {x.mindestbestand}, Max: {x.hoechstbestand})",
            key="individual_threshold_cable"
        )

        if selected_cable:
            with st.form("individual_threshold_update"):
                col_ind1, col_ind2 = st.columns(2)

                with col_ind1:
                    ind_min = st.number_input(
                        "Mindestbestand",
                        value=selected_cable.mindestbestand,
                        min_value=0,
                        step=1,
                        key="ind_min"
                    )

                with col_ind2:
                    ind_max = st.number_input(
                        "Höchstbestand",
                        value=selected_cable.hoechstbestand,
                        min_value=1,
                        step=1,
                        key="ind_max"
                    )

                submitted_ind = st.form_submit_button("Grenzwerte für dieses Kabel speichern", type="secondary")

                if submitted_ind:
                    if ind_min >= ind_max:
                        st.error("Mindestbestand muss kleiner als Höchstbestand sein.")
                    else:
                        current_user = SessionManager.get_current_user()
                        updates = [{
                            "cable_id": selected_cable.id,
                            "mindestbestand": ind_min,
                            "hoechstbestand": ind_max
                        }]

                        results = cable_service.bulk_update_stock_thresholds(updates, current_user['id'])

                        if results["success"] > 0:
                            st.success(f"✅ Bestandsgrenzen für {selected_cable.bezeichnung} aktualisiert!")
                            st.rerun()
                        else:
                            st.error("❌ Fehler beim Aktualisieren der Bestandsgrenzen.")