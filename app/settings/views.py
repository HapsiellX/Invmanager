"""
Settings views for admin configuration interface
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any

from core.security import require_auth, SessionManager
from core.database import get_db
from settings.services import get_settings_service
from auth.services import get_auth_service


@require_auth
def show_settings_page():
    """
    Settings page with user profile and admin settings
    """
    st.header("⚙️ Einstellungen")

    # Check if user has admin permissions for system settings
    is_admin = SessionManager.has_permission("admin")

    if is_admin:
        # Get settings service for admin
        settings_service = get_settings_service()
        categories = settings_service.get_categories()
        tab_names = ["👤 Benutzerprofil"] + [cat.title() for cat in categories] + ["➕ Neue Einstellung"]
    else:
        # Non-admin users only see user profile
        tab_names = ["👤 Benutzerprofil"]

    category_tabs = st.tabs(tab_names)

    # User profile tab (available to all users)
    with category_tabs[0]:
        show_user_profile_tab()

    # Admin-only tabs
    if is_admin:
        settings_service = get_settings_service()

        # Show settings for each category
        for i, category in enumerate(categories):
            with category_tabs[i + 1]:
                show_category_settings(settings_service, category)

        # New setting tab
        with category_tabs[-1]:
            show_create_setting_form(settings_service)


def show_category_settings(settings_service, category: str):
    """Show settings for a specific category"""
    st.subheader(f"📂 {category.title()} Einstellungen")

    settings = settings_service.get_settings_by_category(category)

    if not settings:
        st.info(f"Keine Einstellungen in der Kategorie '{category}' gefunden.")
        return

    # Create form for updating settings
    with st.form(f"settings_form_{category}"):
        updated_values = {}

        for setting in settings:
            st.markdown(f"**{setting.bezeichnung}**")
            if setting.beschreibung:
                st.markdown(f"*{setting.beschreibung}*")

            # Create appropriate input widget based on data type
            if setting.datentyp == "boolean":
                updated_values[setting.key] = st.checkbox(
                    "Aktiviert",
                    value=setting.parsed_value,
                    key=f"setting_{setting.key}",
                    help=setting.hilfe_text
                )

            elif setting.datentyp == "int":
                min_val = int(setting.min_wert) if setting.min_wert else None
                max_val = int(setting.max_wert) if setting.max_wert else None
                updated_values[setting.key] = st.number_input(
                    "Wert",
                    value=setting.parsed_value,
                    min_value=min_val,
                    max_value=max_val,
                    step=1,
                    key=f"setting_{setting.key}",
                    help=setting.hilfe_text
                )

            elif setting.datentyp == "float":
                min_val = float(setting.min_wert) if setting.min_wert else None
                max_val = float(setting.max_wert) if setting.max_wert else None
                updated_values[setting.key] = st.number_input(
                    "Wert",
                    value=setting.parsed_value,
                    min_value=min_val,
                    max_value=max_val,
                    step=0.1,
                    format="%.2f",
                    key=f"setting_{setting.key}",
                    help=setting.hilfe_text
                )

            elif setting.datentyp == "string":
                if setting.erlaubte_werte:
                    # Dropdown for enum values
                    try:
                        index = setting.erlaubte_werte.index(setting.parsed_value)
                    except (ValueError, AttributeError):
                        index = 0
                    updated_values[setting.key] = st.selectbox(
                        "Wert",
                        options=setting.erlaubte_werte,
                        index=index,
                        key=f"setting_{setting.key}",
                        help=setting.hilfe_text
                    )
                else:
                    # Text input
                    updated_values[setting.key] = st.text_input(
                        "Wert",
                        value=setting.parsed_value,
                        key=f"setting_{setting.key}",
                        help=setting.hilfe_text
                    )

            elif setting.datentyp == "json":
                # Text area for JSON
                import json
                json_str = json.dumps(setting.parsed_value, indent=2) if setting.parsed_value else "{}"
                updated_values[setting.key] = st.text_area(
                    "JSON Wert",
                    value=json_str,
                    height=100,
                    key=f"setting_{setting.key}",
                    help=setting.hilfe_text
                )

            # Show warning if restart required
            if setting.neustart_erforderlich:
                st.warning("⚠️ Neustart erforderlich nach Änderung")

            st.divider()

        # Submit button
        submitted = st.form_submit_button("Einstellungen speichern", type="primary")

        if submitted:
            current_user = SessionManager.get_current_user()
            results = settings_service.bulk_update_settings(updated_values, current_user['id'])

            # Show results
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)

            if success_count == total_count:
                st.success(f"Alle {success_count} Einstellungen wurden erfolgreich gespeichert!")
            elif success_count > 0:
                st.warning(f"{success_count} von {total_count} Einstellungen wurden gespeichert.")
            else:
                st.error("Keine Einstellungen konnten gespeichert werden.")

            # Show restart warning if any setting requires restart
            restart_required = any(
                setting.neustart_erforderlich
                for setting in settings
                if setting.key in updated_values and results.get(setting.key, False)
            )

            if restart_required:
                st.warning("🔄 **Neustart erforderlich!** Einige Änderungen werden erst nach einem Systemneustart wirksam.")

            st.rerun()


def show_create_setting_form(settings_service):
    """Show form to create new setting"""
    st.subheader("➕ Neue Einstellung erstellen")

    with st.form("create_setting_form"):
        col1, col2 = st.columns(2)

        with col1:
            key = st.text_input("Schlüssel*", placeholder="z.B. inventory.cable.new_setting")
            kategorie = st.selectbox("Kategorie*", ["inventory", "ui", "security", "notifications"])
            bezeichnung = st.text_input("Bezeichnung*", placeholder="Benutzerfreundlicher Name")
            datentyp = st.selectbox("Datentyp*", ["string", "int", "float", "boolean", "json"])

        with col2:
            beschreibung = st.text_area("Beschreibung", placeholder="Detaillierte Beschreibung der Einstellung")
            hilfe_text = st.text_area("Hilfetext", placeholder="Hilfe für Administratoren")
            ist_erforderlich = st.checkbox("Erforderlich", value=True)
            neustart_erforderlich = st.checkbox("Neustart erforderlich", value=False)

        # Value and constraints
        st.subheader("Wert und Validierung")
        col3, col4 = st.columns(2)

        with col3:
            if datentyp == "boolean":
                wert = st.checkbox("Standard-Wert", value=False)
            elif datentyp in ["int", "float"]:
                wert = st.number_input(
                    "Standard-Wert",
                    value=0.0 if datentyp == "float" else 0,
                    step=0.1 if datentyp == "float" else 1
                )
                min_wert = st.text_input("Minimaler Wert (optional)")
                max_wert = st.text_input("Maximaler Wert (optional)")
            elif datentyp == "json":
                wert_str = st.text_area("Standard JSON-Wert", value="{}")
                try:
                    import json
                    wert = json.loads(wert_str)
                except:
                    wert = {}
            else:  # string
                wert = st.text_input("Standard-Wert")

        with col4:
            if datentyp == "string":
                erlaubte_werte_str = st.text_area(
                    "Erlaubte Werte (JSON Array, optional)",
                    placeholder='["wert1", "wert2", "wert3"]'
                )
                try:
                    import json
                    erlaubte_werte = json.loads(erlaubte_werte_str) if erlaubte_werte_str.strip() else None
                except:
                    erlaubte_werte = None
            else:
                erlaubte_werte = None

        submitted = st.form_submit_button("Einstellung erstellen", type="primary")

        if submitted:
            # Validation
            if not all([key, kategorie, bezeichnung, datentyp]):
                st.error("Bitte füllen Sie alle Pflichtfelder (*) aus.")
            elif settings_service.get_setting(key):
                st.error(f"Eine Einstellung mit dem Schlüssel '{key}' existiert bereits.")
            else:
                # Create setting data
                setting_data = {
                    'key': key,
                    'kategorie': kategorie,
                    'bezeichnung': bezeichnung,
                    'beschreibung': beschreibung,
                    'hilfe_text': hilfe_text,
                    'datentyp': datentyp,
                    'ist_erforderlich': ist_erforderlich,
                    'ist_sichtbar': True,
                    'neustart_erforderlich': neustart_erforderlich
                }

                # Add type-specific data
                if datentyp in ["int", "float"]:
                    setting_data['min_wert'] = min_wert if min_wert else None
                    setting_data['max_wert'] = max_wert if max_wert else None

                if erlaubte_werte:
                    setting_data['erlaubte_werte'] = erlaubte_werte

                # Set the value
                if datentyp == "json":
                    import json
                    setting_data['wert'] = json.dumps(wert)
                else:
                    setting_data['wert'] = str(wert)

                current_user = SessionManager.get_current_user()
                new_setting = settings_service.create_setting(setting_data, current_user['id'])

                if new_setting:
                    st.success(f"Einstellung '{bezeichnung}' wurde erfolgreich erstellt!")
                    st.rerun()
                else:
                    st.error("Fehler beim Erstellen der Einstellung.")


def show_user_profile_tab():
    """Show user profile settings including password change"""
    st.subheader("👤 Benutzerprofil")

    current_user = SessionManager.get_current_user()

    # Display current user info
    st.markdown("### 📋 Aktuelle Benutzerinformationen")
    col1, col2 = st.columns(2)

    with col1:
        st.info(f"**Benutzername:** {current_user['benutzername']}")
        st.info(f"**E-Mail:** {current_user['email']}")
        st.info(f"**Rolle:** {current_user['rolle'].title()}")

    with col2:
        st.info(f"**Vorname:** {current_user['vorname']}")
        st.info(f"**Nachname:** {current_user['nachname']}")
        if current_user.get('abteilung'):
            st.info(f"**Abteilung:** {current_user['abteilung']}")

    st.divider()

    # Password change form
    st.markdown("### 🔐 Passwort ändern")

    with st.form("password_change_form"):
        st.markdown("**Passwort aktualisieren**")

        old_password = st.text_input(
            "Aktuelles Passwort*",
            type="password",
            help="Geben Sie Ihr aktuelles Passwort ein"
        )

        new_password = st.text_input(
            "Neues Passwort*",
            type="password",
            help="Mindestens 8 Zeichen empfohlen"
        )

        confirm_password = st.text_input(
            "Neues Passwort bestätigen*",
            type="password",
            help="Wiederholen Sie das neue Passwort"
        )

        submit_password = st.form_submit_button("Passwort ändern", type="primary")

        if submit_password:
            # Validation
            if not all([old_password, new_password, confirm_password]):
                st.error("Bitte füllen Sie alle Felder aus.")
            elif new_password != confirm_password:
                st.error("Die neuen Passwörter stimmen nicht überein.")
            elif len(new_password) < 6:
                st.error("Das neue Passwort muss mindestens 6 Zeichen lang sein.")
            elif old_password == new_password:
                st.error("Das neue Passwort muss sich vom aktuellen Passwort unterscheiden.")
            else:
                # Change password
                auth_service = get_auth_service()
                success = auth_service.change_password(
                    current_user['id'],
                    old_password,
                    new_password
                )

                if success:
                    st.success("✅ Passwort wurde erfolgreich geändert!")
                    st.info("⚠️ Bitte melden Sie sich mit dem neuen Passwort erneut an.")

                    # Optional: Auto-logout after password change
                    if st.button("Jetzt abmelden"):
                        SessionManager.logout_user()
                        st.rerun()
                else:
                    st.error("❌ Passwort konnte nicht geändert werden. Überprüfen Sie Ihr aktuelles Passwort.")

    st.divider()

    # User activity info
    st.markdown("### 📊 Kontoinformationen")
    col3, col4 = st.columns(2)

    with col3:
        if current_user.get('erstellt_am'):
            st.info(f"**Registriert:** {current_user['erstellt_am']}")
        if current_user.get('letzter_login'):
            st.info(f"**Letzter Login:** {current_user['letzter_login']}")

    with col4:
        if current_user.get('telefon'):
            st.info(f"**Telefon:** {current_user['telefon']}")
        st.info(f"**Status:** {'✅ Aktiv' if current_user.get('ist_aktiv', True) else '❌ Inaktiv'}")

    # Security note
    st.markdown("### 🛡️ Sicherheitshinweise")
    st.markdown("""
    **Tipps für ein sicheres Passwort:**
    - Verwenden Sie mindestens 8 Zeichen
    - Kombinieren Sie Groß- und Kleinbuchstaben, Zahlen und Sonderzeichen
    - Verwenden Sie keine persönlichen Informationen
    - Ändern Sie Ihr Passwort regelmäßig
    - Teilen Sie Ihr Passwort niemals mit anderen
    """)

    if current_user['rolle'] == 'admin':
        st.markdown("---")
        st.markdown("### ⚙️ Administrator-Hinweise")
        st.info("Als Administrator haben Sie Zugriff auf alle Systemeinstellungen in den anderen Tabs.")
        st.warning("⚠️ Bei Änderungen an kritischen Einstellungen kann ein Systemneustart erforderlich sein.")


def show_settings_overview():
    """Show settings overview for quick access"""
    st.subheader("📊 Einstellungen Übersicht")

    settings_service = get_settings_service()

    # Quick stats
    all_settings = settings_service.get_all_settings(nur_sichtbare=False)
    categories = settings_service.get_categories()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Gesamte Einstellungen", len(all_settings))

    with col2:
        st.metric("Kategorien", len(categories))

    with col3:
        required_settings = sum(1 for s in all_settings if s.ist_erforderlich)
        st.metric("Erforderliche Einstellungen", required_settings)

    # Settings by category
    st.subheader("Einstellungen nach Kategorie")

    for category in categories:
        with st.expander(f"📂 {category.title()}"):
            category_settings = settings_service.get_settings_by_category(category)

            if category_settings:
                settings_data = []
                for setting in category_settings:
                    settings_data.append({
                        "Bezeichnung": setting.bezeichnung,
                        "Schlüssel": setting.key,
                        "Aktueller Wert": str(setting.parsed_value),
                        "Typ": setting.datentyp,
                        "Erforderlich": "✅" if setting.ist_erforderlich else "❌"
                    })

                df = pd.DataFrame(settings_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info(f"Keine Einstellungen in {category}")


def show_quick_inventory_settings():
    """Show quick access to common inventory settings"""
    st.subheader("⚡ Schnell-Einstellungen Inventory")

    settings_service = get_settings_service()

    with st.form("quick_inventory_settings"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Kabel Standard-Werte**")
            cable_min = st.number_input(
                "Standard Mindestbestand",
                value=settings_service.get_setting_value("inventory.cable.default_min_stock", 5),
                min_value=0,
                max_value=1000,
                step=1
            )
            cable_max = st.number_input(
                "Standard Höchstbestand",
                value=settings_service.get_setting_value("inventory.cable.default_max_stock", 100),
                min_value=1,
                max_value=10000,
                step=1
            )

        with col2:
            st.markdown("**Hardware Einstellungen**")
            warranty_days = st.number_input(
                "Garantie-Warnung (Tage vorher)",
                value=settings_service.get_setting_value("inventory.hardware.warranty_alert_days", 30),
                min_value=1,
                max_value=365,
                step=1
            )

        submitted = st.form_submit_button("Schnell-Einstellungen speichern", type="primary")

        if submitted:
            current_user = SessionManager.get_current_user()

            updates = {
                "inventory.cable.default_min_stock": cable_min,
                "inventory.cable.default_max_stock": cable_max,
                "inventory.hardware.warranty_alert_days": warranty_days
            }

            results = settings_service.bulk_update_settings(updates, current_user['id'])

            success_count = sum(1 for success in results.values() if success)
            if success_count == len(updates):
                st.success("Alle Inventory-Einstellungen wurden gespeichert!")
            else:
                st.error("Einige Einstellungen konnten nicht gespeichert werden.")

            st.rerun()