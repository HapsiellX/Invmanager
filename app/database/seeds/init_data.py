"""
Initialize database with sample data for testing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.orm import Session
from core.database import SessionLocal, engine
from core.security import security
from database.models.user import User
from database.models.location import Location
from database.models.cable import Cable
from datetime import datetime
from decimal import Decimal


def create_sample_data():
    """Create sample data for testing"""
    db = SessionLocal()

    try:
        # Create sample locations
        if not db.query(Location).first():
            locations = [
                Location(
                    name="Hauptsitz",
                    beschreibung="Hauptsitz des Unternehmens",
                    typ="site",
                    adresse="Musterstraße 123",
                    stadt="Berlin",
                    postleitzahl="10115",
                    ist_aktiv=True
                ),
                Location(
                    name="Gebäude A",
                    beschreibung="Hauptgebäude",
                    typ="building",
                    ist_aktiv=True
                ),
                Location(
                    name="Erdgeschoss",
                    beschreibung="Erdgeschoss Gebäude A",
                    typ="floor",
                    ist_aktiv=True
                ),
                Location(
                    name="Serverraum 1",
                    beschreibung="Hauptserverraum",
                    typ="room",
                    ist_aktiv=True
                ),
                Location(
                    name="Rack A1",
                    beschreibung="Rack A1 im Serverraum",
                    typ="storage",
                    ist_aktiv=True
                )
            ]

            # Set up hierarchy
            for i, location in enumerate(locations):
                if i > 0:
                    location.parent_id = locations[i-1].id
                db.add(location)

            db.commit()

            # Refresh to get IDs
            for location in locations:
                db.refresh(location)

        # Create sample users
        if not db.query(User).first():
            users = [
                User(
                    benutzername="admin",
                    email="admin@inventory.local",
                    passwort_hash=security.hash_password("admin123"),
                    vorname="System",
                    nachname="Administrator",
                    rolle="admin",
                    abteilung="IT",
                    ist_aktiv=True,
                    ist_email_bestaetigt=True
                ),
                User(
                    benutzername="netzwerker",
                    email="network@inventory.local",
                    passwort_hash=security.hash_password("network123"),
                    vorname="Max",
                    nachname="Mustermann",
                    rolle="netzwerker",
                    abteilung="Netzwerk",
                    ist_aktiv=True,
                    ist_email_bestaetigt=True
                ),
                User(
                    benutzername="azubi",
                    email="azubi@inventory.local",
                    passwort_hash=security.hash_password("azubi123"),
                    vorname="Anna",
                    nachname="Schmidt",
                    rolle="auszubildende",
                    abteilung="IT",
                    ist_aktiv=True,
                    ist_email_bestaetigt=True
                )
            ]

            for user in users:
                db.add(user)

            db.commit()

        # Create sample cables
        if not db.query(Cable).first():
            # Get the admin user for creation
            admin_user = db.query(User).filter(User.benutzername == "admin").first()
            # Get a location for cables
            location = db.query(Location).filter(Location.name == "Serverraum 1").first()

            if admin_user and location:
                cables = [
                    Cable(
                        typ="Copper",
                        standard="Cat6",
                        laenge=Decimal("2.0"),
                        standort_id=location.id,
                        lagerort="Lager 1, Regal A",
                        menge=25,
                        mindestbestand=10,
                        hoechstbestand=100,
                        farbe="Blau",
                        stecker_typ_a="RJ45",
                        stecker_typ_b="RJ45",
                        hersteller="Panduit",
                        modell="TX6-28",
                        einkaufspreis_pro_einheit=Decimal("12.50"),
                        lieferant="Elektro Weber",
                        artikel_nummer="TX6-28-2M-BL",
                        erstellt_von=admin_user.id
                    ),
                    Cable(
                        typ="Copper",
                        standard="Cat6a",
                        laenge=Decimal("5.0"),
                        standort_id=location.id,
                        lagerort="Lager 1, Regal A",
                        menge=3,
                        mindestbestand=5,
                        hoechstbestand=50,
                        farbe="Gelb",
                        stecker_typ_a="RJ45",
                        stecker_typ_b="RJ45",
                        hersteller="Legrand",
                        modell="032762",
                        einkaufspreis_pro_einheit=Decimal("18.90"),
                        lieferant="Elektro Weber",
                        artikel_nummer="LG-032762-5M",
                        erstellt_von=admin_user.id
                    ),
                    Cable(
                        typ="Fiber",
                        standard="Single-mode",
                        laenge=Decimal("10.0"),
                        standort_id=location.id,
                        lagerort="Lager 1, Regal B",
                        menge=15,
                        mindestbestand=5,
                        hoechstbestand=30,
                        farbe="Gelb",
                        stecker_typ_a="LC",
                        stecker_typ_b="LC",
                        hersteller="Corning",
                        modell="SMF-28",
                        einkaufspreis_pro_einheit=Decimal("45.00"),
                        lieferant="Fiber Solutions",
                        artikel_nummer="COR-SMF-10M-LC",
                        erstellt_von=admin_user.id
                    ),
                    Cable(
                        typ="Fiber",
                        standard="Multi-mode",
                        laenge=Decimal("3.0"),
                        standort_id=location.id,
                        lagerort="Lager 1, Regal B",
                        menge=0,
                        mindestbestand=8,
                        hoechstbestand=40,
                        farbe="Orange",
                        stecker_typ_a="SC",
                        stecker_typ_b="SC",
                        hersteller="CommScope",
                        modell="760151902",
                        einkaufspreis_pro_einheit=Decimal("32.50"),
                        lieferant="Fiber Solutions",
                        artikel_nummer="CS-MM-3M-SC",
                        erstellt_von=admin_user.id
                    ),
                    Cable(
                        typ="Power",
                        standard="CEE 7/7",
                        laenge=Decimal("1.5"),
                        standort_id=location.id,
                        lagerort="Lager 1, Regal C",
                        menge=8,
                        mindestbestand=10,
                        hoechstbestand=50,
                        farbe="Schwarz",
                        stecker_typ_a="CEE 7/7",
                        stecker_typ_b="C13",
                        hersteller="Brennenstuhl",
                        modell="1165450",
                        einkaufspreis_pro_einheit=Decimal("8.50"),
                        lieferant="Conrad Electronic",
                        artikel_nummer="BR-1165450",
                        erstellt_von=admin_user.id
                    ),
                    Cable(
                        typ="Copper",
                        standard="Cat6",
                        laenge=Decimal("0.5"),
                        standort_id=location.id,
                        lagerort="Lager 1, Regal A",
                        menge=45,
                        mindestbestand=20,
                        hoechstbestand=80,
                        farbe="Rot",
                        stecker_typ_a="RJ45",
                        stecker_typ_b="RJ45",
                        hersteller="Panduit",
                        modell="TX6-28",
                        einkaufspreis_pro_einheit=Decimal("8.90"),
                        lieferant="Elektro Weber",
                        artikel_nummer="TX6-28-0.5M-RD",
                        erstellt_von=admin_user.id
                    )
                ]

                for cable in cables:
                    db.add(cable)

                db.commit()

        print("Sample data created successfully!")

    except Exception as e:
        print(f"Error creating sample data: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    # Import models to ensure they're registered
    from database.models import user, location, hardware, cable, transaction, audit_log, settings

    # Create all tables
    from core.database import Base
    Base.metadata.create_all(bind=engine)

    # Create sample data
    create_sample_data()