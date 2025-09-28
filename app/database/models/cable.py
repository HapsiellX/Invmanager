"""
Cable inventory model for managing cables with quantities
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from core.database import Base


class Cable(Base):
    """
    Cable inventory model with German field names
    """
    __tablename__ = "cables"

    id = Column(Integer, primary_key=True, index=True)

    # Cable specifications
    typ = Column(String(50), nullable=False, index=True)  # Fiber, Copper, Power
    standard = Column(String(50), nullable=False, index=True)  # Cat6, Cat6a, Single-mode, Multi-mode
    laenge = Column(Numeric(5, 2), nullable=False)  # Length in meters

    # Location
    standort_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    standort = relationship("Location")
    lagerort = Column(String(100), nullable=False)  # "Lager 1, Regal A"

    # Inventory
    menge = Column(Integer, nullable=False, default=0)  # Current quantity
    mindestbestand = Column(Integer, nullable=False, default=5)  # Minimum stock level
    hoechstbestand = Column(Integer, nullable=False, default=100)  # Maximum stock level

    # Additional specifications
    farbe = Column(String(30))
    stecker_typ_a = Column(String(50))  # Connector type A
    stecker_typ_b = Column(String(50))  # Connector type B
    hersteller = Column(String(50))
    modell = Column(String(100))

    # Business information
    einkaufspreis_pro_einheit = Column(Numeric(8, 2))
    lieferant = Column(String(100))
    artikel_nummer = Column(String(100))

    # Status
    ist_aktiv = Column(Boolean, default=True, nullable=False)

    # Timestamps
    erstellt_am = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    aktualisiert_am = Column(DateTime(timezone=True), onupdate=func.now())
    erstellt_von = Column(Integer, ForeignKey("users.id"), nullable=False)
    aktualisiert_von = Column(Integer, ForeignKey("users.id"))

    # Relationships
    ersteller = relationship("User", foreign_keys=[erstellt_von])
    aktualisierer = relationship("User", foreign_keys=[aktualisiert_von])

    # Additional metadata
    notizen = Column(Text)

    def __repr__(self):
        return f"<Cable(typ='{self.typ}', standard='{self.standard}', laenge={self.laenge}m, menge={self.menge})>"

    @property
    def bezeichnung(self) -> str:
        """Get cable designation"""
        return f"{self.typ} {self.standard} {self.laenge}m"

    @property
    def health_status(self) -> str:
        """Get health status based on stock levels"""
        if self.menge <= 0:
            return "kritisch"
        elif self.menge <= self.mindestbestand:
            return "niedrig"
        elif self.menge >= self.hoechstbestand:
            return "hoch"
        else:
            return "normal"

    @property
    def bestand_prozent(self) -> float:
        """Get stock level as percentage of maximum"""
        if self.hoechstbestand <= 0:
            return 0.0
        return min(100.0, (self.menge / self.hoechstbestand) * 100)

    @property
    def gesamtwert(self) -> float:
        """Calculate total value of current stock"""
        if self.einkaufspreis_pro_einheit:
            return float(self.menge * self.einkaufspreis_pro_einheit)
        return 0.0

    def hinzufuegen(self, menge: int, benutzer_id: int, grund: str = None):
        """Add quantity to stock"""
        if menge > 0:
            self.menge += menge
            self.aktualisiert_von = benutzer_id
            if grund:
                self.notizen = f"{self.notizen or ''}\n+{menge}: {grund}".strip()

    def entfernen(self, menge: int, benutzer_id: int, grund: str = None) -> bool:
        """Remove quantity from stock. Returns True if successful."""
        if menge > 0 and self.menge >= menge:
            self.menge -= menge
            self.aktualisiert_von = benutzer_id
            if grund:
                self.notizen = f"{self.notizen or ''}\n-{menge}: {grund}".strip()
            return True
        return False

    def set_menge(self, neue_menge: int, benutzer_id: int, grund: str = None):
        """Set absolute quantity"""
        if neue_menge >= 0:
            alte_menge = self.menge
            self.menge = neue_menge
            self.aktualisiert_von = benutzer_id
            if grund:
                self.notizen = f"{self.notizen or ''}\nMenge geändert von {alte_menge} auf {neue_menge}: {grund}".strip()

    def to_dict(self) -> dict:
        """Convert cable to dictionary"""
        return {
            "id": self.id,
            "bezeichnung": self.bezeichnung,
            "typ": self.typ,
            "standard": self.standard,
            "laenge": float(self.laenge),
            "standort_pfad": self.standort.vollstaendiger_pfad if self.standort else "",
            "lagerort": self.lagerort,
            "menge": self.menge,
            "mindestbestand": self.mindestbestand,
            "hoechstbestand": self.hoechstbestand,
            "health_status": self.health_status,
            "bestand_prozent": self.bestand_prozent,
            "farbe": self.farbe,
            "stecker_typ_a": self.stecker_typ_a,
            "stecker_typ_b": self.stecker_typ_b,
            "hersteller": self.hersteller,
            "modell": self.modell,
            "einkaufspreis_pro_einheit": float(self.einkaufspreis_pro_einheit) if self.einkaufspreis_pro_einheit else None,
            "gesamtwert": self.gesamtwert,
            "lieferant": self.lieferant,
            "artikel_nummer": self.artikel_nummer,
            "ist_aktiv": self.ist_aktiv
        }