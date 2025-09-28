"""
Transaction model for tracking all inventory movements and changes
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Numeric, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from core.database import Base


class Transaction(Base):
    """
    Transaction model for audit trail of all inventory operations
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)

    # Transaction details
    typ = Column(String(50), nullable=False, index=True)  # eingang, ausgang, bewegung, aenderung, wartung
    beschreibung = Column(String(200), nullable=False)

    # Target item reference
    ziel_typ = Column(String(20), nullable=False)  # hardware, cable, user, location
    ziel_id = Column(Integer, nullable=False)  # ID of the target item

    # User who performed the action
    benutzer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    benutzer = relationship("User")

    # Quantity changes (for cables mainly)
    menge_vorher = Column(Integer)
    menge_nachher = Column(Integer)
    menge_aenderung = Column(Integer)

    # Location changes
    standort_vorher_id = Column(Integer, ForeignKey("locations.id"))
    standort_nachher_id = Column(Integer, ForeignKey("locations.id"))
    standort_vorher = relationship("Location", foreign_keys=[standort_vorher_id])
    standort_nachher = relationship("Location", foreign_keys=[standort_nachher_id])

    # Status changes
    status_vorher = Column(String(50))
    status_nachher = Column(String(50))

    # Additional data as JSON
    zusaetzliche_daten = Column(JSON)

    # Financial impact
    kosten = Column(Numeric(10, 2))
    waehrung = Column(String(3), default="EUR")

    # Reference documents
    referenz_dokument = Column(String(200))  # Invoice number, work order, etc.

    # Timestamps
    zeitstempel = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Additional context
    grund = Column(Text)  # Reason for the transaction
    notizen = Column(Text)  # Additional notes

    # System generated or manual
    ist_automatisch = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Transaction(typ='{self.typ}', ziel_typ='{self.ziel_typ}', ziel_id={self.ziel_id})>"

    @classmethod
    def create_hardware_eingang(
        cls,
        hardware_id: int,
        benutzer_id: int,
        standort_id: int,
        beschreibung: str = None,
        grund: str = None,
        kosten: float = None,
        referenz_dokument: str = None
    ):
        """Create transaction for hardware arrival"""
        return cls(
            typ="eingang",
            beschreibung=beschreibung or "Hardware Eingang",
            ziel_typ="hardware",
            ziel_id=hardware_id,
            benutzer_id=benutzer_id,
            standort_nachher_id=standort_id,
            status_nachher="verfuegbar",
            grund=grund,
            kosten=kosten,
            referenz_dokument=referenz_dokument
        )

    @classmethod
    def create_hardware_ausgang(
        cls,
        hardware_id: int,
        benutzer_id: int,
        beschreibung: str = None,
        grund: str = None
    ):
        """Create transaction for hardware departure"""
        return cls(
            typ="ausgang",
            beschreibung=beschreibung or "Hardware Ausgang",
            ziel_typ="hardware",
            ziel_id=hardware_id,
            benutzer_id=benutzer_id,
            status_vorher="verfuegbar",
            status_nachher="ausrangiert",
            grund=grund
        )

    @classmethod
    def create_cable_eingang(
        cls,
        cable_id: int,
        benutzer_id: int,
        standort_id: int,
        menge: int,
        beschreibung: str = None,
        grund: str = None,
        kosten: float = None,
        referenz_dokument: str = None
    ):
        """Create transaction for cable arrival"""
        return cls(
            typ="eingang",
            beschreibung=beschreibung or "Kabel Eingang",
            ziel_typ="cable",
            ziel_id=cable_id,
            benutzer_id=benutzer_id,
            standort_nachher_id=standort_id,
            menge_nachher=menge,
            menge_aenderung=menge,
            grund=grund,
            kosten=kosten,
            referenz_dokument=referenz_dokument
        )

    @classmethod
    def create_cable_bestandsaenderung(
        cls,
        cable_id: int,
        benutzer_id: int,
        alte_menge: int,
        neue_menge: int,
        menge_aenderung: int,
        beschreibung: str = None,
        grund: str = None
    ):
        """Create transaction for cable quantity change"""
        return cls(
            typ="bestandsaenderung",
            beschreibung=beschreibung or f"Kabel Bestandsänderung ({menge_aenderung:+d})",
            ziel_typ="cable",
            ziel_id=cable_id,
            benutzer_id=benutzer_id,
            menge_vorher=alte_menge,
            menge_nachher=neue_menge,
            menge_aenderung=menge_aenderung,
            grund=grund
        )

    @classmethod
    def create_cable_bestandskorrektur(
        cls,
        cable_id: int,
        benutzer_id: int,
        alte_menge: int,
        neue_menge: int,
        beschreibung: str = None,
        grund: str = None
    ):
        """Create transaction for cable stock correction"""
        aenderung = neue_menge - alte_menge
        return cls(
            typ="bestandskorrektur",
            beschreibung=beschreibung or f"Kabel Bestandskorrektur ({aenderung:+d})",
            ziel_typ="cable",
            ziel_id=cable_id,
            benutzer_id=benutzer_id,
            menge_vorher=alte_menge,
            menge_nachher=neue_menge,
            menge_aenderung=aenderung,
            grund=grund
        )

    @classmethod
    def create_standort_aenderung(
        cls,
        item_typ: str,
        item_id: int,
        benutzer_id: int,
        alter_standort_id: int,
        neuer_standort_id: int,
        beschreibung: str = None,
        grund: str = None
    ):
        """Create transaction for location change"""
        return cls(
            typ="bewegung",
            beschreibung=beschreibung or f"{item_typ.title()} Standort Änderung",
            ziel_typ=item_typ,
            ziel_id=item_id,
            benutzer_id=benutzer_id,
            standort_vorher_id=alter_standort_id,
            standort_nachher_id=neuer_standort_id,
            grund=grund
        )

    @classmethod
    def create_status_aenderung(
        cls,
        item_typ: str,
        item_id: int,
        benutzer_id: int,
        alter_status: str,
        neuer_status: str,
        beschreibung: str = None,
        grund: str = None
    ):
        """Create transaction for status change"""
        return cls(
            typ="status_aenderung",
            beschreibung=beschreibung or f"{item_typ.title()} Status Änderung",
            ziel_typ=item_typ,
            ziel_id=item_id,
            benutzer_id=benutzer_id,
            status_vorher=alter_status,
            status_nachher=neuer_status,
            grund=grund
        )

    def to_dict(self) -> dict:
        """Convert transaction to dictionary"""
        return {
            "id": self.id,
            "typ": self.typ,
            "beschreibung": self.beschreibung,
            "ziel_typ": self.ziel_typ,
            "ziel_id": self.ziel_id,
            "benutzer_name": self.benutzer.vollname if self.benutzer else "Unbekannt",
            "menge_vorher": self.menge_vorher,
            "menge_nachher": self.menge_nachher,
            "menge_aenderung": self.menge_aenderung,
            "standort_vorher": self.standort_vorher.name if self.standort_vorher else None,
            "standort_nachher": self.standort_nachher.name if self.standort_nachher else None,
            "status_vorher": self.status_vorher,
            "status_nachher": self.status_nachher,
            "zeitstempel": self.zeitstempel.isoformat() if self.zeitstempel else None,
            "grund": self.grund,
            "notizen": self.notizen,
            "kosten": float(self.kosten) if self.kosten else None,
            "waehrung": self.waehrung,
            "referenz_dokument": self.referenz_dokument,
            "ist_automatisch": self.ist_automatisch
        }