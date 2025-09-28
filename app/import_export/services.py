"""
Import/Export services for inventory data
"""

import csv
import io
import json
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal

from database.models.hardware import HardwareItem
from database.models.cable import Cable
from database.models.location import Location
from database.models.audit_log import AuditLog
from core.database import get_db


class ImportExportService:
    """Service class for import/export operations"""

    def __init__(self, db: Session):
        self.db = db

    def export_hardware_to_csv(self) -> str:
        """Export all hardware items to CSV format"""
        hardware_items = self.db.query(HardwareItem).filter(
            HardwareItem.ist_aktiv == True
        ).all()

        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        header = [
            'ID', 'Name', 'Kategorie', 'Hersteller', 'Modell', 'Seriennummer',
            'Status', 'Standort', 'Lagerort', 'Einkaufspreis', 'Einkaufsdatum',
            'Lieferant', 'Artikel_Nummer', 'Garantie_Bis', 'MAC_Adresse',
            'IP_Adresse', 'Notizen', 'Erstellt_Am', 'Erstellt_Von'
        ]
        writer.writerow(header)

        # Write data
        for item in hardware_items:
            standort_name = item.standort.name if item.standort else ""
            row = [
                item.id,
                item.name,
                item.kategorie,
                item.hersteller,
                item.modell,
                item.seriennummer,
                item.status,
                standort_name,
                item.lagerort,
                float(item.einkaufspreis) if item.einkaufspreis else "",
                item.einkaufsdatum.strftime('%Y-%m-%d') if item.einkaufsdatum else "",
                item.lieferant,
                item.artikel_nummer,
                item.garantie_bis.strftime('%Y-%m-%d') if item.garantie_bis else "",
                item.mac_adresse,
                item.ip_adresse,
                item.notizen,
                item.erstellt_am.strftime('%Y-%m-%d %H:%M:%S'),
                item.erstellt_von
            ]
            writer.writerow(row)

        return output.getvalue()

    def export_cables_to_csv(self) -> str:
        """Export all cables to CSV format"""
        cables = self.db.query(Cable).filter(Cable.ist_aktiv == True).all()

        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        header = [
            'ID', 'Typ', 'Standard', 'Länge', 'Standort', 'Lagerort', 'Menge',
            'Mindestbestand', 'Höchstbestand', 'Farbe', 'Stecker_Typ_A',
            'Stecker_Typ_B', 'Hersteller', 'Modell', 'Einkaufspreis_Pro_Einheit',
            'Lieferant', 'Artikel_Nummer', 'Notizen', 'Erstellt_Am', 'Erstellt_Von'
        ]
        writer.writerow(header)

        # Write data
        for cable in cables:
            standort_name = cable.standort.name if cable.standort else ""
            row = [
                cable.id,
                cable.typ,
                cable.standard,
                float(cable.laenge),
                standort_name,
                cable.lagerort,
                cable.menge,
                cable.mindestbestand,
                cable.hoechstbestand,
                cable.farbe,
                cable.stecker_typ_a,
                cable.stecker_typ_b,
                cable.hersteller,
                cable.modell,
                float(cable.einkaufspreis_pro_einheit) if cable.einkaufspreis_pro_einheit else "",
                cable.lieferant,
                cable.artikel_nummer,
                cable.notizen,
                cable.erstellt_am.strftime('%Y-%m-%d %H:%M:%S'),
                cable.erstellt_von
            ]
            writer.writerow(row)

        return output.getvalue()

    def export_locations_to_csv(self) -> str:
        """Export all locations to CSV format"""
        locations = self.db.query(Location).filter(Location.ist_aktiv == True).all()

        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        header = [
            'ID', 'Name', 'Beschreibung', 'Typ', 'Parent_ID', 'Parent_Name',
            'Adresse', 'Stadt', 'Postleitzahl', 'Land', 'Kontakt_Person',
            'Telefon', 'Email', 'Vollständiger_Pfad', 'Notizen', 'Erstellt_Am'
        ]
        writer.writerow(header)

        # Write data
        for location in locations:
            parent_name = ""
            if location.parent_id:
                parent = self.db.query(Location).filter(Location.id == location.parent_id).first()
                if parent:
                    parent_name = parent.name

            row = [
                location.id,
                location.name,
                location.beschreibung,
                location.typ,
                location.parent_id,
                parent_name,
                location.adresse,
                location.stadt,
                location.postleitzahl,
                location.land,
                location.kontakt_person,
                location.telefon,
                location.email,
                location.vollstaendiger_pfad,
                location.notizen,
                location.erstellt_am.strftime('%Y-%m-%d %H:%M:%S')
            ]
            writer.writerow(row)

        return output.getvalue()

    def export_inventory_to_json(self) -> str:
        """Export complete inventory to JSON format"""
        # Get all data
        hardware_items = self.db.query(HardwareItem).filter(
            HardwareItem.ist_aktiv == True
        ).all()
        cables = self.db.query(Cable).filter(Cable.ist_aktiv == True).all()
        locations = self.db.query(Location).filter(Location.ist_aktiv == True).all()

        # Convert to dictionaries
        data = {
            "export_timestamp": datetime.now().isoformat(),
            "hardware_items": [item.to_dict() for item in hardware_items],
            "cables": [cable.to_dict() for cable in cables],
            "locations": [location.to_dict() for location in locations]
        }

        return json.dumps(data, indent=2, ensure_ascii=False, default=str)

    def import_hardware_from_csv(self, csv_content: str, benutzer_id: int) -> Dict[str, Any]:
        """Import hardware items from CSV format"""
        try:
            df = pd.read_csv(io.StringIO(csv_content))
            imported_count = 0
            errors = []
            warnings = []

            # Validate required columns
            required_columns = ['Name', 'Kategorie']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return {
                    "success": False,
                    "error": f"Fehlende erforderliche Spalten: {', '.join(missing_columns)}"
                }

            # Create location name to ID mapping
            location_mapping = {}
            locations = self.db.query(Location).filter(Location.ist_aktiv == True).all()
            for loc in locations:
                location_mapping[loc.name] = loc.id

            for index, row in df.iterrows():
                try:
                    # Skip empty rows
                    if pd.isna(row.get('Name')) or row.get('Name', '').strip() == '':
                        continue

                    # Find location
                    standort_id = None
                    if not pd.isna(row.get('Standort')):
                        standort_name = str(row['Standort']).strip()
                        if standort_name in location_mapping:
                            standort_id = location_mapping[standort_name]
                        else:
                            warnings.append(f"Zeile {index + 2}: Standort '{standort_name}' nicht gefunden")

                    # Parse dates
                    einkaufsdatum = None
                    if not pd.isna(row.get('Einkaufsdatum')):
                        try:
                            einkaufsdatum = pd.to_datetime(row['Einkaufsdatum']).date()
                        except:
                            warnings.append(f"Zeile {index + 2}: Ungültiges Einkaufsdatum")

                    garantie_bis = None
                    if not pd.isna(row.get('Garantie_Bis')):
                        try:
                            garantie_bis = pd.to_datetime(row['Garantie_Bis']).date()
                        except:
                            warnings.append(f"Zeile {index + 2}: Ungültiges Garantiedatum")

                    # Parse price
                    einkaufspreis = None
                    if not pd.isna(row.get('Einkaufspreis')):
                        try:
                            einkaufspreis = Decimal(str(row['Einkaufspreis']))
                        except:
                            warnings.append(f"Zeile {index + 2}: Ungültiger Einkaufspreis")

                    # Create hardware item
                    hardware_item = HardwareItem(
                        name=str(row['Name']).strip(),
                        kategorie=str(row.get('Kategorie', '')).strip(),
                        hersteller=str(row.get('Hersteller', '')).strip() if not pd.isna(row.get('Hersteller')) else None,
                        modell=str(row.get('Modell', '')).strip() if not pd.isna(row.get('Modell')) else None,
                        seriennummer=str(row.get('Seriennummer', '')).strip() if not pd.isna(row.get('Seriennummer')) else None,
                        status=str(row.get('Status', 'Verfügbar')).strip(),
                        standort_id=standort_id,
                        lagerort=str(row.get('Lagerort', '')).strip() if not pd.isna(row.get('Lagerort')) else None,
                        einkaufspreis=einkaufspreis,
                        einkaufsdatum=einkaufsdatum,
                        lieferant=str(row.get('Lieferant', '')).strip() if not pd.isna(row.get('Lieferant')) else None,
                        artikel_nummer=str(row.get('Artikel_Nummer', '')).strip() if not pd.isna(row.get('Artikel_Nummer')) else None,
                        garantie_bis=garantie_bis,
                        mac_adresse=str(row.get('MAC_Adresse', '')).strip() if not pd.isna(row.get('MAC_Adresse')) else None,
                        ip_adresse=str(row.get('IP_Adresse', '')).strip() if not pd.isna(row.get('IP_Adresse')) else None,
                        notizen=str(row.get('Notizen', '')).strip() if not pd.isna(row.get('Notizen')) else None,
                        erstellt_von=benutzer_id
                    )

                    self.db.add(hardware_item)
                    imported_count += 1

                except Exception as e:
                    errors.append(f"Zeile {index + 2}: {str(e)}")

            if imported_count > 0:
                self.db.commit()

                # Create audit log
                audit_log = AuditLog.log_data_change(
                    benutzer_id=benutzer_id,
                    benutzer_rolle="admin",
                    aktion="Hardware Import",
                    ressource_typ="hardware",
                    ressource_id=None,
                    neue_werte={"imported_count": imported_count},
                    beschreibung=f"Hardware Import: {imported_count} Artikel importiert"
                )
                self.db.add(audit_log)
                self.db.commit()

            return {
                "success": True,
                "imported_count": imported_count,
                "errors": errors,
                "warnings": warnings
            }

        except Exception as e:
            self.db.rollback()
            return {
                "success": False,
                "error": f"Fehler beim Import: {str(e)}"
            }

    def import_cables_from_csv(self, csv_content: str, benutzer_id: int) -> Dict[str, Any]:
        """Import cables from CSV format"""
        try:
            df = pd.read_csv(io.StringIO(csv_content))
            imported_count = 0
            errors = []
            warnings = []

            # Validate required columns
            required_columns = ['Typ', 'Standard', 'Länge']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return {
                    "success": False,
                    "error": f"Fehlende erforderliche Spalten: {', '.join(missing_columns)}"
                }

            # Create location name to ID mapping
            location_mapping = {}
            locations = self.db.query(Location).filter(Location.ist_aktiv == True).all()
            for loc in locations:
                location_mapping[loc.name] = loc.id

            for index, row in df.iterrows():
                try:
                    # Skip empty rows
                    if pd.isna(row.get('Typ')) or row.get('Typ', '').strip() == '':
                        continue

                    # Find location
                    standort_id = None
                    if not pd.isna(row.get('Standort')):
                        standort_name = str(row['Standort']).strip()
                        if standort_name in location_mapping:
                            standort_id = location_mapping[standort_name]
                        else:
                            warnings.append(f"Zeile {index + 2}: Standort '{standort_name}' nicht gefunden")

                    # Parse numeric values
                    try:
                        laenge = Decimal(str(row['Länge']))
                    except:
                        errors.append(f"Zeile {index + 2}: Ungültige Länge")
                        continue

                    menge = int(row.get('Menge', 0)) if not pd.isna(row.get('Menge')) else 0
                    mindestbestand = int(row.get('Mindestbestand', 0)) if not pd.isna(row.get('Mindestbestand')) else 0
                    hoechstbestand = int(row.get('Höchstbestand', 0)) if not pd.isna(row.get('Höchstbestand')) else 0

                    einkaufspreis_pro_einheit = None
                    if not pd.isna(row.get('Einkaufspreis_Pro_Einheit')):
                        try:
                            einkaufspreis_pro_einheit = Decimal(str(row['Einkaufspreis_Pro_Einheit']))
                        except:
                            warnings.append(f"Zeile {index + 2}: Ungültiger Einkaufspreis")

                    # Create cable
                    cable = Cable(
                        typ=str(row['Typ']).strip(),
                        standard=str(row['Standard']).strip(),
                        laenge=laenge,
                        standort_id=standort_id,
                        lagerort=str(row.get('Lagerort', '')).strip() if not pd.isna(row.get('Lagerort')) else None,
                        menge=menge,
                        mindestbestand=mindestbestand,
                        hoechstbestand=hoechstbestand,
                        farbe=str(row.get('Farbe', '')).strip() if not pd.isna(row.get('Farbe')) else None,
                        stecker_typ_a=str(row.get('Stecker_Typ_A', '')).strip() if not pd.isna(row.get('Stecker_Typ_A')) else None,
                        stecker_typ_b=str(row.get('Stecker_Typ_B', '')).strip() if not pd.isna(row.get('Stecker_Typ_B')) else None,
                        hersteller=str(row.get('Hersteller', '')).strip() if not pd.isna(row.get('Hersteller')) else None,
                        modell=str(row.get('Modell', '')).strip() if not pd.isna(row.get('Modell')) else None,
                        einkaufspreis_pro_einheit=einkaufspreis_pro_einheit,
                        lieferant=str(row.get('Lieferant', '')).strip() if not pd.isna(row.get('Lieferant')) else None,
                        artikel_nummer=str(row.get('Artikel_Nummer', '')).strip() if not pd.isna(row.get('Artikel_Nummer')) else None,
                        notizen=str(row.get('Notizen', '')).strip() if not pd.isna(row.get('Notizen')) else None,
                        erstellt_von=benutzer_id
                    )

                    self.db.add(cable)
                    imported_count += 1

                except Exception as e:
                    errors.append(f"Zeile {index + 2}: {str(e)}")

            if imported_count > 0:
                self.db.commit()

                # Create audit log
                audit_log = AuditLog.log_data_change(
                    benutzer_id=benutzer_id,
                    benutzer_rolle="admin",
                    aktion="Kabel Import",
                    ressource_typ="cable",
                    ressource_id=None,
                    neue_werte={"imported_count": imported_count},
                    beschreibung=f"Kabel Import: {imported_count} Kabel importiert"
                )
                self.db.add(audit_log)
                self.db.commit()

            return {
                "success": True,
                "imported_count": imported_count,
                "errors": errors,
                "warnings": warnings
            }

        except Exception as e:
            self.db.rollback()
            return {
                "success": False,
                "error": f"Fehler beim Import: {str(e)}"
            }

    def get_import_template_hardware(self) -> str:
        """Get CSV template for hardware import"""
        header = [
            'Name', 'Kategorie', 'Hersteller', 'Modell', 'Seriennummer',
            'Status', 'Standort', 'Lagerort', 'Einkaufspreis', 'Einkaufsdatum',
            'Lieferant', 'Artikel_Nummer', 'Garantie_Bis', 'MAC_Adresse',
            'IP_Adresse', 'Notizen'
        ]

        # Sample data
        sample_data = [
            ['Server HP ProLiant', 'Server', 'HP', 'ProLiant DL380', 'SN123456789',
             'Verfügbar', 'Serverraum 1', 'Rack A1', '2500.00', '2024-01-15',
             'HP Deutschland', 'HP-DL380-001', '2027-01-15', '00:11:22:33:44:55',
             '192.168.1.100', 'Produktionsserver'],
            ['Switch Cisco Catalyst', 'Netzwerk', 'Cisco', 'Catalyst 2960', 'SW987654321',
             'In Betrieb', 'Serverraum 1', 'Rack B1', '800.00', '2024-02-01',
             'Cisco Systems', 'CS-2960-001', '2027-02-01', '00:AA:BB:CC:DD:EE',
             '192.168.1.10', '24-Port Switch']
        ]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header)
        for row in sample_data:
            writer.writerow(row)

        return output.getvalue()

    def get_import_template_cables(self) -> str:
        """Get CSV template for cables import"""
        header = [
            'Typ', 'Standard', 'Länge', 'Standort', 'Lagerort', 'Menge',
            'Mindestbestand', 'Höchstbestand', 'Farbe', 'Stecker_Typ_A',
            'Stecker_Typ_B', 'Hersteller', 'Modell', 'Einkaufspreis_Pro_Einheit',
            'Lieferant', 'Artikel_Nummer', 'Notizen'
        ]

        # Sample data
        sample_data = [
            ['Copper', 'Cat6', '2.0', 'Serverraum 1', 'Lager 1, Regal A', '25',
             '10', '100', 'Blau', 'RJ45', 'RJ45', 'Panduit', 'TX6-28',
             '12.50', 'Elektro Weber', 'TX6-28-2M-BL', 'Standard Patchkabel'],
            ['Fiber', 'Single-mode', '10.0', 'Serverraum 1', 'Lager 1, Regal B', '15',
             '5', '30', 'Gelb', 'LC', 'LC', 'Corning', 'SMF-28',
             '45.00', 'Fiber Solutions', 'COR-SMF-10M-LC', 'Glasfaserkabel für WAN']
        ]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header)
        for row in sample_data:
            writer.writerow(row)

        return output.getvalue()

    def validate_import_data(self, csv_content: str, data_type: str) -> Dict[str, Any]:
        """Validate import data before actual import"""
        try:
            df = pd.read_csv(io.StringIO(csv_content))

            if data_type == "hardware":
                required_columns = ['Name', 'Kategorie']
            elif data_type == "cables":
                required_columns = ['Typ', 'Standard', 'Länge']
            else:
                return {"success": False, "error": "Unbekannter Datentyp"}

            # Check required columns
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return {
                    "success": False,
                    "error": f"Fehlende erforderliche Spalten: {', '.join(missing_columns)}"
                }

            # Count valid rows
            valid_rows = 0
            for _, row in df.iterrows():
                if data_type == "hardware":
                    if not pd.isna(row.get('Name')) and row.get('Name', '').strip() != '':
                        valid_rows += 1
                elif data_type == "cables":
                    if not pd.isna(row.get('Typ')) and row.get('Typ', '').strip() != '':
                        valid_rows += 1

            return {
                "success": True,
                "total_rows": len(df),
                "valid_rows": valid_rows,
                "columns": list(df.columns)
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Fehler bei der Validierung: {str(e)}"
            }


def get_import_export_service(db: Session = None) -> ImportExportService:
    """Dependency injection for import/export service"""
    if db is None:
        db = next(get_db())
    return ImportExportService(db)