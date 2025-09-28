"""
User model for authentication and authorization
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from core.database import Base


class User(Base):
    """
    User model with German field names for business logic
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    benutzername = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    passwort_hash = Column(String(255), nullable=False)

    # User details
    vorname = Column(String(50), nullable=False)
    nachname = Column(String(50), nullable=False)

    # Role: admin, netzwerker, auszubildende
    rolle = Column(String(20), nullable=False, default="auszubildende")

    # Status
    ist_aktiv = Column(Boolean, default=True, nullable=False)
    ist_email_bestaetigt = Column(Boolean, default=False, nullable=False)

    # Timestamps
    erstellt_am = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    aktualisiert_am = Column(DateTime(timezone=True), onupdate=func.now())
    letzter_login = Column(DateTime(timezone=True))

    # Additional info
    telefon = Column(String(20))
    abteilung = Column(String(50))
    notizen = Column(Text)

    def __repr__(self):
        return f"<User(benutzername='{self.benutzername}', rolle='{self.rolle}')>"

    @property
    def vollname(self) -> str:
        """Return full name"""
        return f"{self.vorname} {self.nachname}"

    @property
    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.rolle == "admin"

    @property
    def is_netzwerker(self) -> bool:
        """Check if user is network admin"""
        return self.rolle == "netzwerker"

    @property
    def is_auszubildende(self) -> bool:
        """Check if user is trainee"""
        return self.rolle == "auszubildende"

    def can_edit_hardware(self) -> bool:
        """Check if user can edit hardware inventory"""
        return self.rolle in ["admin", "netzwerker"]

    def can_edit_cables(self) -> bool:
        """Check if user can edit cable inventory"""
        return self.rolle in ["admin", "netzwerker"]

    def can_manage_users(self) -> bool:
        """Check if user can manage other users"""
        return self.rolle == "admin"

    def can_view_analytics(self) -> bool:
        """Check if user can view analytics"""
        return self.rolle in ["admin", "netzwerker"]

    def to_dict(self) -> dict:
        """Convert user to dictionary for session storage"""
        return {
            "id": self.id,
            "benutzername": self.benutzername,
            "email": self.email,
            "vorname": self.vorname,
            "nachname": self.nachname,
            "rolle": self.rolle,
            "ist_aktiv": self.ist_aktiv,
            "vollname": self.vollname,
            "abteilung": self.abteilung
        }