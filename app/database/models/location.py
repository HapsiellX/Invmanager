"""
Location model for hierarchical location management
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from core.database import Base


class Location(Base):
    """
    Location model with German field names
    Supports hierarchical structure: Site -> Building -> Floor -> Room -> Storage
    """
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)

    # Location details
    name = Column(String(100), nullable=False, index=True)
    beschreibung = Column(Text)

    # Hierarchical structure
    parent_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    parent = relationship("Location", remote_side=[id], backref="kinder")

    # Location type: site, building, floor, room, storage
    typ = Column(String(20), nullable=False)

    # Address information (mainly for sites)
    adresse = Column(String(200))
    stadt = Column(String(50))
    postleitzahl = Column(String(10))
    land = Column(String(50), default="Deutschland")

    # Contact information
    kontakt_person = Column(String(100))
    telefon = Column(String(20))
    email = Column(String(100))

    # Status
    ist_aktiv = Column(Boolean, default=True, nullable=False)

    # Timestamps
    erstellt_am = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    aktualisiert_am = Column(DateTime(timezone=True), onupdate=func.now())

    # Additional metadata
    notizen = Column(Text)

    def __repr__(self):
        return f"<Location(name='{self.name}', typ='{self.typ}')>"

    @property
    def vollstaendiger_pfad(self) -> str:
        """Get full hierarchical path"""
        if self.parent:
            return f"{self.parent.vollstaendiger_pfad} > {self.name}"
        return self.name

    @property
    def ebene(self) -> int:
        """Get level in hierarchy (0 = root)"""
        if self.parent:
            return self.parent.ebene + 1
        return 0

    def get_root_location(self):
        """Get the root location (site)"""
        if self.parent:
            return self.parent.get_root_location()
        return self

    def get_all_children(self) -> list:
        """Get all child locations recursively"""
        children = []
        for child in self.kinder:
            children.append(child)
            children.extend(child.get_all_children())
        return children

    def to_dict(self) -> dict:
        """Convert location to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "beschreibung": self.beschreibung,
            "typ": self.typ,
            "vollstaendiger_pfad": self.vollstaendiger_pfad,
            "parent_id": self.parent_id,
            "ist_aktiv": self.ist_aktiv,
            "adresse": self.adresse,
            "stadt": self.stadt,
            "postleitzahl": self.postleitzahl,
            "kontakt_person": self.kontakt_person,
            "telefon": self.telefon,
            "email": self.email
        }