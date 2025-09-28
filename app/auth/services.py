"""
Authentication services for user management
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.models.user import User
from database.models.audit_log import AuditLog
from core.security import security
from core.database import get_db


class AuthService:
    """Service class for authentication operations"""

    def __init__(self, db: Session):
        self.db = db

    def authenticate_user(self, benutzername: str, passwort: str, ip_adresse: str = None, user_agent: str = None) -> Optional[Dict[str, Any]]:
        """
        Authenticate user with username and password
        Returns user data if successful, None if failed
        """
        try:
            # Find user by username or email
            user = self.db.query(User).filter(
                and_(
                    User.ist_aktiv == True,
                    (User.benutzername == benutzername) | (User.email == benutzername)
                )
            ).first()

            if not user:
                # Log failed login attempt
                audit_log = AuditLog.log_login(
                    benutzer_id=None,
                    benutzer_rolle="unknown",
                    ip_adresse=ip_adresse,
                    user_agent=user_agent,
                    erfolgreich=False,
                    fehler_nachricht="Benutzer nicht gefunden"
                )
                self.db.add(audit_log)
                self.db.commit()
                return None

            # Verify password
            if not security.verify_password(passwort, user.passwort_hash):
                # Log failed login attempt
                audit_log = AuditLog.log_login(
                    benutzer_id=user.id,
                    benutzer_rolle=user.rolle,
                    ip_adresse=ip_adresse,
                    user_agent=user_agent,
                    erfolgreich=False,
                    fehler_nachricht="Falsches Passwort"
                )
                self.db.add(audit_log)
                self.db.commit()
                return None

            # Update last login
            from sqlalchemy.sql import func
            user.letzter_login = func.now()

            # Log successful login
            session_id = security.generate_session_id()
            audit_log = AuditLog.log_login(
                benutzer_id=user.id,
                benutzer_rolle=user.rolle,
                ip_adresse=ip_adresse,
                user_agent=user_agent,
                erfolgreich=True,
                session_id=session_id
            )
            self.db.add(audit_log)
            self.db.commit()

            return user.to_dict()

        except Exception as e:
            self.db.rollback()
            # Log system error
            audit_log = AuditLog.log_system_event(
                aktion="Login Fehler",
                beschreibung=f"Systemfehler bei der Anmeldung: {str(e)}",
                erfolgreich=False,
                fehler_nachricht=str(e)
            )
            self.db.add(audit_log)
            self.db.commit()
            return None

    def create_user(self, user_data: Dict[str, Any], created_by_id: int) -> Optional[User]:
        """
        Create a new user
        """
        try:
            # Check if username or email already exists
            existing_user = self.db.query(User).filter(
                (User.benutzername == user_data['benutzername']) |
                (User.email == user_data['email'])
            ).first()

            if existing_user:
                return None

            # Hash password
            passwort_hash = security.hash_password(user_data['passwort'])

            # Create new user
            new_user = User(
                benutzername=user_data['benutzername'],
                email=user_data['email'],
                passwort_hash=passwort_hash,
                vorname=user_data['vorname'],
                nachname=user_data['nachname'],
                rolle=user_data.get('rolle', 'auszubildende'),
                telefon=user_data.get('telefon'),
                abteilung=user_data.get('abteilung'),
                notizen=user_data.get('notizen')
            )

            self.db.add(new_user)
            self.db.commit()
            self.db.refresh(new_user)

            # Log user creation
            audit_log = AuditLog.log_data_change(
                benutzer_id=created_by_id,
                benutzer_rolle="admin",  # Only admins can create users
                aktion="Benutzer erstellt",
                ressource_typ="user",
                ressource_id=new_user.id,
                neue_werte=new_user.to_dict(),
                beschreibung=f"Neuer Benutzer erstellt: {new_user.benutzername}"
            )
            self.db.add(audit_log)
            self.db.commit()

            return new_user

        except Exception as e:
            self.db.rollback()
            return None

    def update_user(self, user_id: int, user_data: Dict[str, Any], updated_by_id: int) -> Optional[User]:
        """
        Update an existing user
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return None

            # Store old values for audit
            old_values = user.to_dict()

            # Update fields
            for field, value in user_data.items():
                if field == 'passwort' and value:
                    user.passwort_hash = security.hash_password(value)
                elif hasattr(user, field) and field not in ['id', 'passwort_hash', 'erstellt_am']:
                    setattr(user, field, value)

            self.db.commit()
            self.db.refresh(user)

            # Log user update
            audit_log = AuditLog.log_data_change(
                benutzer_id=updated_by_id,
                benutzer_rolle="admin",
                aktion="Benutzer aktualisiert",
                ressource_typ="user",
                ressource_id=user.id,
                alte_werte=old_values,
                neue_werte=user.to_dict(),
                beschreibung=f"Benutzer aktualisiert: {user.benutzername}"
            )
            self.db.add(audit_log)
            self.db.commit()

            return user

        except Exception as e:
            self.db.rollback()
            return None

    def deactivate_user(self, user_id: int, deactivated_by_id: int) -> bool:
        """
        Deactivate a user (soft delete)
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False

            old_values = user.to_dict()
            user.ist_aktiv = False
            self.db.commit()

            # Log user deactivation
            audit_log = AuditLog.log_data_change(
                benutzer_id=deactivated_by_id,
                benutzer_rolle="admin",
                aktion="Benutzer deaktiviert",
                ressource_typ="user",
                ressource_id=user.id,
                alte_werte=old_values,
                neue_werte=user.to_dict(),
                beschreibung=f"Benutzer deaktiviert: {user.benutzername}"
            )
            self.db.add(audit_log)
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            return False

    def get_all_users(self, include_inactive: bool = False) -> list:
        """
        Get all users
        """
        query = self.db.query(User)
        if not include_inactive:
            query = query.filter(User.ist_aktiv == True)

        return query.order_by(User.nachname, User.vorname).all()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """
        Change user password after verifying old password
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False

            # Verify old password
            if not security.verify_password(old_password, user.passwort_hash):
                return False

            # Set new password
            user.passwort_hash = security.hash_password(new_password)
            self.db.commit()

            # Log password change
            audit_log = AuditLog.log_data_change(
                benutzer_id=user_id,
                benutzer_rolle=user.rolle,
                aktion="Passwort geändert",
                ressource_typ="user",
                ressource_id=user.id,
                beschreibung="Benutzer hat Passwort geändert"
            )
            self.db.add(audit_log)
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            return False


def get_auth_service(db: Session = None) -> AuthService:
    """
    Dependency injection for auth service
    """
    if db is None:
        db = next(get_db())
    return AuthService(db)