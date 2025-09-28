"""
Audit log model for tracking system events and user actions
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from core.database import Base


class AuditLog(Base):
    """
    Audit log for system security and compliance
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Event details
    ereignis_typ = Column(String(50), nullable=False, index=True)  # login, logout, create, update, delete, view
    ressource_typ = Column(String(50), nullable=False)  # user, hardware, cable, location, system
    ressource_id = Column(Integer)  # ID of affected resource (nullable for system events)
    aktion = Column(String(100), nullable=False)  # Specific action performed

    # User information
    benutzer_id = Column(Integer, ForeignKey("users.id"))
    benutzer = relationship("User")
    benutzer_rolle = Column(String(20))  # Role at time of action
    session_id = Column(String(100))  # Session identifier

    # Request details
    ip_adresse = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(String(500))  # Browser/client information
    request_method = Column(String(10))  # GET, POST, PUT, DELETE
    request_url = Column(String(500))  # Requested URL

    # Event details
    erfolgreich = Column(Boolean, nullable=False, default=True)
    fehler_nachricht = Column(Text)  # Error message if failed

    # Data changes (for update operations)
    alte_werte = Column(JSON)  # Previous values
    neue_werte = Column(JSON)  # New values

    # Additional context
    beschreibung = Column(Text)  # Human-readable description
    zusaetzliche_daten = Column(JSON)  # Additional contextual data

    # Timestamps
    zeitstempel = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Risk assessment
    risiko_level = Column(String(10), default="low")  # low, medium, high, critical
    verdaechtig = Column(Boolean, default=False)  # Flagged as suspicious

    def __repr__(self):
        return f"<AuditLog(ereignis_typ='{self.ereignis_typ}', aktion='{self.aktion}', erfolgreich={self.erfolgreich})>"

    @classmethod
    def log_login(
        cls,
        benutzer_id: int,
        benutzer_rolle: str,
        ip_adresse: str,
        user_agent: str,
        erfolgreich: bool = True,
        fehler_nachricht: str = None,
        session_id: str = None
    ):
        """Log user login attempt"""
        return cls(
            ereignis_typ="login",
            ressource_typ="user",
            ressource_id=benutzer_id,
            aktion="Benutzer Anmeldung",
            benutzer_id=benutzer_id,
            benutzer_rolle=benutzer_rolle,
            session_id=session_id,
            ip_adresse=ip_adresse,
            user_agent=user_agent,
            erfolgreich=erfolgreich,
            fehler_nachricht=fehler_nachricht,
            beschreibung=f"Anmeldung {'erfolgreich' if erfolgreich else 'fehlgeschlagen'}",
            risiko_level="low" if erfolgreich else "medium"
        )

    @classmethod
    def log_logout(
        cls,
        benutzer_id: int,
        benutzer_rolle: str,
        session_id: str,
        ip_adresse: str = None
    ):
        """Log user logout"""
        return cls(
            ereignis_typ="logout",
            ressource_typ="user",
            ressource_id=benutzer_id,
            aktion="Benutzer Abmeldung",
            benutzer_id=benutzer_id,
            benutzer_rolle=benutzer_rolle,
            session_id=session_id,
            ip_adresse=ip_adresse,
            erfolgreich=True,
            beschreibung="Benutzer erfolgreich abgemeldet",
            risiko_level="low"
        )

    @classmethod
    def log_data_change(
        cls,
        benutzer_id: int,
        benutzer_rolle: str,
        aktion: str,
        ressource_typ: str,
        ressource_id: int,
        alte_werte: dict = None,
        neue_werte: dict = None,
        session_id: str = None,
        ip_adresse: str = None,
        beschreibung: str = None
    ):
        """Log data modification"""
        ereignis_typ = "update" if alte_werte else "create"
        if aktion.lower().startswith("delete") or aktion.lower().startswith("löschen"):
            ereignis_typ = "delete"

        return cls(
            ereignis_typ=ereignis_typ,
            ressource_typ=ressource_typ,
            ressource_id=ressource_id,
            aktion=aktion,
            benutzer_id=benutzer_id,
            benutzer_rolle=benutzer_rolle,
            session_id=session_id,
            ip_adresse=ip_adresse,
            erfolgreich=True,
            alte_werte=alte_werte,
            neue_werte=neue_werte,
            beschreibung=beschreibung or f"{aktion} ausgeführt",
            risiko_level="low" if ereignis_typ in ["create", "update"] else "medium"
        )

    @classmethod
    def log_security_event(
        cls,
        ereignis_typ: str,
        aktion: str,
        benutzer_id: int = None,
        benutzer_rolle: str = None,
        ip_adresse: str = None,
        beschreibung: str = None,
        risiko_level: str = "high",
        zusaetzliche_daten: dict = None
    ):
        """Log security-related events"""
        return cls(
            ereignis_typ=ereignis_typ,
            ressource_typ="system",
            aktion=aktion,
            benutzer_id=benutzer_id,
            benutzer_rolle=benutzer_rolle,
            ip_adresse=ip_adresse,
            erfolgreich=False,
            beschreibung=beschreibung,
            risiko_level=risiko_level,
            verdaechtig=True,
            zusaetzliche_daten=zusaetzliche_daten
        )

    @classmethod
    def log_system_event(
        cls,
        aktion: str,
        beschreibung: str = None,
        erfolgreich: bool = True,
        fehler_nachricht: str = None,
        zusaetzliche_daten: dict = None
    ):
        """Log system events"""
        return cls(
            ereignis_typ="system",
            ressource_typ="system",
            aktion=aktion,
            erfolgreich=erfolgreich,
            fehler_nachricht=fehler_nachricht,
            beschreibung=beschreibung,
            risiko_level="low",
            zusaetzliche_daten=zusaetzliche_daten
        )

    def to_dict(self) -> dict:
        """Convert audit log to dictionary"""
        return {
            "id": self.id,
            "ereignis_typ": self.ereignis_typ,
            "ressource_typ": self.ressource_typ,
            "ressource_id": self.ressource_id,
            "aktion": self.aktion,
            "benutzer_name": self.benutzer.vollname if self.benutzer else "System",
            "benutzer_rolle": self.benutzer_rolle,
            "ip_adresse": self.ip_adresse,
            "erfolgreich": self.erfolgreich,
            "fehler_nachricht": self.fehler_nachricht,
            "beschreibung": self.beschreibung,
            "zeitstempel": self.zeitstempel.isoformat() if self.zeitstempel else None,
            "risiko_level": self.risiko_level,
            "verdaechtig": self.verdaechtig,
            "alte_werte": self.alte_werte,
            "neue_werte": self.neue_werte
        }