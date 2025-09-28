"""
Authentication views for Streamlit interface
"""

import streamlit as st
from typing import Optional

from core.security import SessionManager
from core.database import get_db
from auth.services import get_auth_service


def show_login_page():
    """
    Display login page
    """
    st.markdown('<div class="main-header"><h1>🔐 Anmeldung</h1></div>', unsafe_allow_html=True)

    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
        <div style="background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            st.markdown("### Willkommen zum Inventory Management System")
            st.markdown("Bitte geben Sie Ihre Anmeldedaten ein:")

            benutzername = st.text_input(
                "Benutzername oder E-Mail",
                placeholder="Ihr Benutzername oder E-Mail-Adresse"
            )

            passwort = st.text_input(
                "Passwort",
                type="password",
                placeholder="Ihr Passwort"
            )

            submitted = st.form_submit_button("Anmelden", type="primary", use_container_width=True)

            if submitted:
                if not benutzername or not passwort:
                    st.error("Bitte füllen Sie alle Felder aus.")
                else:
                    # Attempt authentication
                    with st.spinner("Anmeldung wird überprüft..."):
                        db = next(get_db())
                        auth_service = get_auth_service(db)

                        # Get client information
                        ip_adresse = "127.0.0.1"  # Default for local development
                        user_agent = "Streamlit Client"

                        user_data = auth_service.authenticate_user(
                            benutzername=benutzername,
                            passwort=passwort,
                            ip_adresse=ip_adresse,
                            user_agent=user_agent
                        )

                        if user_data:
                            SessionManager.login_user(user_data)
                            st.success(f"Willkommen, {user_data['vorname']}!")
                            st.rerun()
                        else:
                            st.error("Ungültige Anmeldedaten. Bitte überprüfen Sie Benutzername und Passwort.")

        st.markdown("</div>", unsafe_allow_html=True)

        # System information
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #666; font-size: 0.9em;">
        <p><strong>Inventory Management System v1.0</strong></p>
        <p>Bei Problemen wenden Sie sich an Ihren Administrator.</p>
        </div>
        """, unsafe_allow_html=True)


def show_user_management_page():
    """
    Display user management page (Admin only)
    """
    if not SessionManager.has_permission("admin"):
        st.error("Sie haben keine Berechtigung für diese Seite.")
        return

    st.header("👥 Benutzerverwaltung")

    # Get database connection
    db = next(get_db())
    auth_service = get_auth_service(db)

    # Tabs for different operations
    tab1, tab2, tab3 = st.tabs(["Benutzer Liste", "Neuer Benutzer", "Benutzer bearbeiten"])

    with tab1:
        show_users_list(auth_service)

    with tab2:
        show_create_user_form(auth_service)

    with tab3:
        show_edit_user_form(auth_service)


def show_users_list(auth_service):
    """Show list of all users"""
    st.subheader("Alle Benutzer")

    users = auth_service.get_all_users(include_inactive=True)

    if not users:
        st.info("Keine Benutzer gefunden.")
        return

    # Convert users to DataFrame for display
    import pandas as pd

    user_data = []
    for user in users:
        user_data.append({
            "ID": user.id,
            "Benutzername": user.benutzername,
            "Name": user.vollname,
            "E-Mail": user.email,
            "Rolle": user.rolle.title(),
            "Abteilung": user.abteilung or "-",
            "Aktiv": "✅" if user.ist_aktiv else "❌",
            "Letzter Login": user.letzter_login.strftime("%d.%m.%Y %H:%M") if user.letzter_login else "Nie"
        })

    df = pd.DataFrame(user_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # User actions
    st.subheader("Benutzer Aktionen")
    col1, col2 = st.columns(2)

    with col1:
        user_to_deactivate = st.selectbox(
            "Benutzer deaktivieren",
            options=[u for u in users if u.ist_aktiv],
            format_func=lambda x: f"{x.vollname} ({x.benutzername})",
            key="deactivate_user"
        )

        if st.button("Benutzer deaktivieren", type="secondary"):
            if user_to_deactivate:
                current_user = SessionManager.get_current_user()
                if auth_service.deactivate_user(user_to_deactivate.id, current_user['id']):
                    st.success(f"Benutzer {user_to_deactivate.vollname} wurde deaktiviert.")
                    st.rerun()
                else:
                    st.error("Fehler beim Deaktivieren des Benutzers.")


def show_create_user_form(auth_service):
    """Show form to create new user"""
    st.subheader("Neuen Benutzer erstellen")

    with st.form("create_user_form"):
        col1, col2 = st.columns(2)

        with col1:
            vorname = st.text_input("Vorname*", key="new_vorname")
            nachname = st.text_input("Nachname*", key="new_nachname")
            benutzername = st.text_input("Benutzername*", key="new_benutzername")
            email = st.text_input("E-Mail*", key="new_email")

        with col2:
            passwort = st.text_input("Passwort*", type="password", key="new_passwort")
            passwort_confirm = st.text_input("Passwort bestätigen*", type="password", key="new_passwort_confirm")
            rolle = st.selectbox("Rolle*", ["auszubildende", "netzwerker", "admin"], key="new_rolle")
            abteilung = st.text_input("Abteilung", key="new_abteilung")

        telefon = st.text_input("Telefon", key="new_telefon")
        notizen = st.text_area("Notizen", key="new_notizen")

        submitted = st.form_submit_button("Benutzer erstellen", type="primary")

        if submitted:
            # Validation
            if not all([vorname, nachname, benutzername, email, passwort]):
                st.error("Bitte füllen Sie alle Pflichtfelder (*) aus.")
            elif passwort != passwort_confirm:
                st.error("Passwörter stimmen nicht überein.")
            elif len(passwort) < 6:
                st.error("Passwort muss mindestens 6 Zeichen lang sein.")
            else:
                # Create user
                user_data = {
                    'vorname': vorname,
                    'nachname': nachname,
                    'benutzername': benutzername,
                    'email': email,
                    'passwort': passwort,
                    'rolle': rolle,
                    'abteilung': abteilung,
                    'telefon': telefon,
                    'notizen': notizen
                }

                current_user = SessionManager.get_current_user()
                new_user = auth_service.create_user(user_data, current_user['id'])

                if new_user:
                    st.success(f"Benutzer {new_user.vollname} wurde erfolgreich erstellt.")
                    st.rerun()
                else:
                    st.error("Fehler beim Erstellen des Benutzers. Benutzername oder E-Mail bereits vergeben.")


def show_edit_user_form(auth_service):
    """Show form to edit existing user"""
    st.subheader("Benutzer bearbeiten")

    users = auth_service.get_all_users(include_inactive=False)
    if not users:
        st.info("Keine aktiven Benutzer gefunden.")
        return

    selected_user = st.selectbox(
        "Benutzer auswählen",
        options=users,
        format_func=lambda x: f"{x.vollname} ({x.benutzername})",
        key="edit_user_select"
    )

    if selected_user:
        with st.form("edit_user_form"):
            col1, col2 = st.columns(2)

            with col1:
                vorname = st.text_input("Vorname", value=selected_user.vorname, key="edit_vorname")
                nachname = st.text_input("Nachname", value=selected_user.nachname, key="edit_nachname")
                email = st.text_input("E-Mail", value=selected_user.email, key="edit_email")
                rolle = st.selectbox("Rolle", ["auszubildende", "netzwerker", "admin"],
                                   index=["auszubildende", "netzwerker", "admin"].index(selected_user.rolle),
                                   key="edit_rolle")

            with col2:
                abteilung = st.text_input("Abteilung", value=selected_user.abteilung or "", key="edit_abteilung")
                telefon = st.text_input("Telefon", value=selected_user.telefon or "", key="edit_telefon")
                neues_passwort = st.text_input("Neues Passwort (leer lassen um beizubehalten)",
                                             type="password", key="edit_passwort")

            notizen = st.text_area("Notizen", value=selected_user.notizen or "", key="edit_notizen")

            submitted = st.form_submit_button("Änderungen speichern", type="primary")

            if submitted:
                # Prepare update data
                update_data = {
                    'vorname': vorname,
                    'nachname': nachname,
                    'email': email,
                    'rolle': rolle,
                    'abteilung': abteilung,
                    'telefon': telefon,
                    'notizen': notizen
                }

                if neues_passwort:
                    if len(neues_passwort) < 6:
                        st.error("Passwort muss mindestens 6 Zeichen lang sein.")
                        return
                    update_data['passwort'] = neues_passwort

                current_user = SessionManager.get_current_user()
                updated_user = auth_service.update_user(selected_user.id, update_data, current_user['id'])

                if updated_user:
                    st.success(f"Benutzer {updated_user.vollname} wurde erfolgreich aktualisiert.")
                    st.rerun()
                else:
                    st.error("Fehler beim Aktualisieren des Benutzers.")


def show_profile_page():
    """
    Show user profile page where users can edit their own information
    """
    st.header("👤 Mein Profil")

    current_user = SessionManager.get_current_user()
    if not current_user:
        st.error("Benutzerdaten konnten nicht geladen werden.")
        return

    db = next(get_db())
    auth_service = get_auth_service(db)

    # Profile information
    st.subheader("Profil Informationen")

    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Name:** {current_user['vollname']}")
        st.info(f"**Benutzername:** {current_user['benutzername']}")
        st.info(f"**E-Mail:** {current_user['email']}")

    with col2:
        st.info(f"**Rolle:** {current_user['rolle'].title()}")
        st.info(f"**Abteilung:** {current_user.get('abteilung', 'Nicht angegeben')}")

    # Password change form
    st.subheader("Passwort ändern")

    with st.form("change_password_form"):
        altes_passwort = st.text_input("Aktuelles Passwort", type="password")
        neues_passwort = st.text_input("Neues Passwort", type="password")
        passwort_confirm = st.text_input("Neues Passwort bestätigen", type="password")

        submitted = st.form_submit_button("Passwort ändern", type="primary")

        if submitted:
            if not all([altes_passwort, neues_passwort, passwort_confirm]):
                st.error("Bitte füllen Sie alle Felder aus.")
            elif neues_passwort != passwort_confirm:
                st.error("Neue Passwörter stimmen nicht überein.")
            elif len(neues_passwort) < 6:
                st.error("Neues Passwort muss mindestens 6 Zeichen lang sein.")
            else:
                success = auth_service.change_password(
                    current_user['id'],
                    altes_passwort,
                    neues_passwort
                )

                if success:
                    st.success("Passwort wurde erfolgreich geändert.")
                else:
                    st.error("Fehler beim Ändern des Passworts. Überprüfen Sie Ihr aktuelles Passwort.")