"""
Hardware inventory model with German field names as specified in requirements
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from core.database import Base


class HardwareItem(Base):
    """
    Hardware inventory model with all required German field names
    """
    __tablename__ = "hardware_items"

    id = Column(Integer, primary_key=True, index=True)

    # Required fields as specified in requirements
    standort_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    standort = relationship("Location", foreign_keys=[standort_id])

    ort = Column(String(100), nullable=False)  # "Lager 1, Schrank 3"
    kategorie = Column(String(50), nullable=False, index=True)  # Switch, Router, Firewall, Transceiver
    bezeichnung = Column(String(100), nullable=False)  # MX204
    hersteller = Column(String(50), nullable=False, index=True)  # Aruba, HPE, Cisco
    seriennummer = Column(String(100), unique=True, nullable=False, index=True)

    # Optional technical details
    formfaktor = Column(String(50))  # Rack units, port density
    klassifikation = Column(String(100))  # 20Ports, 40Ports, SFP, OSFP
    besonderheiten = Column(Text)  # Special features

    # Administrative details
    angenommen_durch = Column(String(100), nullable=False)  # Person who received it
    leistungsschein_nummer = Column(String(100))  # Invoice number

    # Dates
    datum_eingang = Column(DateTime(timezone=True), nullable=False)
    datum_ausgang = Column(DateTime(timezone=True), nullable=True)

    # Status tracking
    status = Column(String(20), nullable=False, default="verfuegbar")  # verfuegbar, in_verwendung, wartung, ausrangiert
    ist_aktiv = Column(Boolean, default=True, nullable=False)  # False when removed from active inventory

    # Financial information
    einkaufspreis = Column(Numeric(10, 2))
    lieferant = Column(String(100))
    garantie_bis = Column(DateTime(timezone=True))

    # Technical specifications
    ip_adresse = Column(String(45))  # IPv4 or IPv6
    mac_adresse = Column(String(17))
    firmware_version = Column(String(50))

    # Additional metadata
    notizen = Column(Text)
    bild_url = Column(String(500))  # URL to device image

    # Timestamps
    erstellt_am = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    aktualisiert_am = Column(DateTime(timezone=True), onupdate=func.now())
    erstellt_von = Column(Integer, ForeignKey("users.id"), nullable=False)
    aktualisiert_von = Column(Integer, ForeignKey("users.id"))

    # Relationships
    ersteller = relationship("User", foreign_keys=[erstellt_von])
    aktualisierer = relationship("User", foreign_keys=[aktualisiert_von])

    def __repr__(self):
        return f"<HardwareItem(bezeichnung='{self.bezeichnung}', seriennummer='{self.seriennummer}')>"

    @property
    def ist_verfuegbar(self) -> bool:
        """Check if hardware is available"""
        return self.ist_aktiv and self.status == "verfuegbar"

    @property
    def vollstaendige_bezeichnung(self) -> str:
        """Get full description"""
        return f"{self.hersteller} {self.bezeichnung}"

    @property
    def ist_ueberfaellig(self) -> bool:
        """Check if device is overdue for maintenance"""
        # Could be extended with maintenance schedules
        return False

    @property
    def standort_pfad(self) -> str:
        """Get full location path"""
        if self.standort:
            return f"{self.standort.vollstaendiger_pfad} - {self.ort}"
        return self.ort

    def ausrangieren(self, benutzer_id: int, grund: str = None):
        """Mark hardware as retired"""
        self.status = "ausrangiert"
        self.ist_aktiv = False
        self.datum_ausgang = func.now()
        self.aktualisiert_von = benutzer_id
        if grund:
            self.notizen = f"{self.notizen or ''}\nAusrangiert: {grund}".strip()

    def in_wartung_setzen(self, benutzer_id: int, grund: str = None):
        """Mark hardware as under maintenance"""
        self.status = "wartung"
        self.aktualisiert_von = benutzer_id
        if grund:
            self.notizen = f"{self.notizen or ''}\nWartung: {grund}".strip()

    def verfuegbar_machen(self, benutzer_id: int):
        """Mark hardware as available"""
        self.status = "verfuegbar"
        self.aktualisiert_von = benutzer_id

    def to_dict(self) -> dict:
        """Convert hardware item to dictionary"""
        return {
            "id": self.id,
            "standort_pfad": self.standort_pfad,
            "ort": self.ort,
            "kategorie": self.kategorie,
            "bezeichnung": self.bezeichnung,
            "hersteller": self.hersteller,
            "seriennummer": self.seriennummer,
            "formfaktor": self.formfaktor,
            "klassifikation": self.klassifikation,
            "besonderheiten": self.besonderheiten,
            "angenommen_durch": self.angenommen_durch,
            "leistungsschein_nummer": self.leistungsschein_nummer,
            "datum_eingang": self.datum_eingang.isoformat() if self.datum_eingang else None,
            "datum_ausgang": self.datum_ausgang.isoformat() if self.datum_ausgang else None,
            "status": self.status,
            "ist_aktiv": self.ist_aktiv,
            "vollstaendige_bezeichnung": self.vollstaendige_bezeichnung,
            "ist_verfuegbar": self.ist_verfuegbar
        }