"""
Hardware inventory services for business logic
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime

from database.models.hardware import HardwareItem
from database.models.location import Location
from database.models.transaction import Transaction
from database.models.audit_log import AuditLog
from core.database import get_db


class HardwareService:
    """Service class for hardware inventory operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_all_hardware(self,
                        standort_filter: str = None,
                        kategorie_filter: str = None,
                        status_filter: str = None,
                        nur_aktive: bool = True) -> List[HardwareItem]:
        """
        Get all hardware items with optional filters
        """
        query = self.db.query(HardwareItem)

        if nur_aktive:
            query = query.filter(HardwareItem.ist_aktiv == True)

        if standort_filter and standort_filter != "Alle":
            query = query.join(Location).filter(Location.name == standort_filter)

        if kategorie_filter and kategorie_filter != "Alle":
            query = query.filter(HardwareItem.kategorie == kategorie_filter)

        if status_filter and status_filter != "Alle":
            query = query.filter(HardwareItem.status == status_filter)

        return query.order_by(desc(HardwareItem.erstellt_am)).all()

    def get_hardware_by_id(self, hardware_id: int) -> Optional[HardwareItem]:
        """Get hardware item by ID"""
        return self.db.query(HardwareItem).filter(HardwareItem.id == hardware_id).first()

    def create_hardware(self, hardware_data: Dict[str, Any], benutzer_id: int) -> HardwareItem:
        """Create new hardware item"""
        try:
            new_hardware = HardwareItem(
                standort_id=hardware_data['standort_id'],
                ort=hardware_data['ort'],
                kategorie=hardware_data['kategorie'],
                bezeichnung=hardware_data['bezeichnung'],
                hersteller=hardware_data['hersteller'],
                seriennummer=hardware_data['seriennummer'],
                formfaktor=hardware_data.get('formfaktor'),
                klassifikation=hardware_data.get('klassifikation'),
                besonderheiten=hardware_data.get('besonderheiten'),
                angenommen_durch=hardware_data['angenommen_durch'],
                leistungsschein_nummer=hardware_data.get('leistungsschein_nummer'),
                datum_eingang=hardware_data['datum_eingang'],
                status=hardware_data.get('status', 'verfuegbar'),
                einkaufspreis=hardware_data.get('einkaufspreis'),
                lieferant=hardware_data.get('lieferant'),
                garantie_bis=hardware_data.get('garantie_bis'),
                ip_adresse=hardware_data.get('ip_adresse'),
                mac_adresse=hardware_data.get('mac_adresse'),
                firmware_version=hardware_data.get('firmware_version'),
                notizen=hardware_data.get('notizen'),
                erstellt_von=benutzer_id
            )

            self.db.add(new_hardware)
            self.db.commit()
            self.db.refresh(new_hardware)

            # Create transaction record
            transaction = Transaction.create_hardware_eingang(
                hardware_id=new_hardware.id,
                benutzer_id=benutzer_id,
                standort_id=new_hardware.standort_id,
                beschreibung=f"Hardware hinzugefügt: {new_hardware.vollstaendige_bezeichnung}",
                kosten=float(hardware_data.get('einkaufspreis', 0)) if hardware_data.get('einkaufspreis') else None,
                referenz_dokument=hardware_data.get('leistungsschein_nummer')
            )
            self.db.add(transaction)

            # Create audit log
            audit_log = AuditLog.log_data_change(
                benutzer_id=benutzer_id,
                benutzer_rolle="admin",  # Will be updated with actual role
                aktion="Hardware erstellt",
                ressource_typ="hardware",
                ressource_id=new_hardware.id,
                neue_werte=new_hardware.to_dict(),
                beschreibung=f"Neue Hardware erstellt: {new_hardware.vollstaendige_bezeichnung}"
            )
            self.db.add(audit_log)

            self.db.commit()
            return new_hardware

        except Exception as e:
            self.db.rollback()
            raise e

    def update_hardware(self, hardware_id: int, hardware_data: Dict[str, Any], benutzer_id: int) -> Optional[HardwareItem]:
        """Update existing hardware item"""
        try:
            hardware = self.db.query(HardwareItem).filter(HardwareItem.id == hardware_id).first()
            if not hardware:
                return None

            # Store old values for audit
            old_values = hardware.to_dict()

            # Update fields
            for field, value in hardware_data.items():
                if hasattr(hardware, field) and field not in ['id', 'erstellt_am', 'erstellt_von']:
                    setattr(hardware, field, value)

            hardware.aktualisiert_von = benutzer_id
            hardware.aktualisiert_am = datetime.utcnow()

            self.db.commit()
            self.db.refresh(hardware)

            # Create audit log
            audit_log = AuditLog.log_data_change(
                benutzer_id=benutzer_id,
                benutzer_rolle="admin",
                aktion="Hardware aktualisiert",
                ressource_typ="hardware",
                ressource_id=hardware.id,
                alte_werte=old_values,
                neue_werte=hardware.to_dict(),
                beschreibung=f"Hardware aktualisiert: {hardware.vollstaendige_bezeichnung}"
            )
            self.db.add(audit_log)
            self.db.commit()

            return hardware

        except Exception as e:
            self.db.rollback()
            raise e

    def delete_hardware(self, hardware_id: int, benutzer_id: int, grund: str = None) -> bool:
        """Soft delete hardware item (move to inactive)"""
        try:
            hardware = self.db.query(HardwareItem).filter(HardwareItem.id == hardware_id).first()
            if not hardware:
                return False

            old_values = hardware.to_dict()

            # Soft delete
            hardware.ausrangieren(benutzer_id, grund)

            self.db.commit()

            # Create transaction record
            transaction = Transaction.create_hardware_ausgang(
                hardware_id=hardware.id,
                benutzer_id=benutzer_id,
                beschreibung=f"Hardware ausrangiert: {hardware.vollstaendige_bezeichnung}",
                grund=grund
            )
            self.db.add(transaction)

            # Create audit log
            audit_log = AuditLog.log_data_change(
                benutzer_id=benutzer_id,
                benutzer_rolle="admin",
                aktion="Hardware ausrangiert",
                ressource_typ="hardware",
                ressource_id=hardware.id,
                alte_werte=old_values,
                neue_werte=hardware.to_dict(),
                beschreibung=f"Hardware ausrangiert: {hardware.vollstaendige_bezeichnung}"
            )
            self.db.add(audit_log)
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            return False

    def get_locations(self) -> List[Location]:
        """Get all active locations"""
        return self.db.query(Location).filter(Location.ist_aktiv == True).order_by(Location.name).all()

    def get_unique_categories(self) -> List[str]:
        """Get list of unique hardware categories"""
        result = self.db.query(HardwareItem.kategorie).distinct().all()
        return [r[0] for r in result if r[0]]

    def get_unique_manufacturers(self) -> List[str]:
        """Get list of unique manufacturers"""
        result = self.db.query(HardwareItem.hersteller).distinct().all()
        return [r[0] for r in result if r[0]]

    def get_inventory_summary(self) -> Dict[str, Any]:
        """Get inventory summary statistics"""
        total_hardware = self.db.query(HardwareItem).filter(HardwareItem.ist_aktiv == True).count()

        by_category = self.db.query(
            HardwareItem.kategorie,
            func.count(HardwareItem.id)
        ).filter(HardwareItem.ist_aktiv == True).group_by(HardwareItem.kategorie).all()

        by_status = self.db.query(
            HardwareItem.status,
            func.count(HardwareItem.id)
        ).filter(HardwareItem.ist_aktiv == True).group_by(HardwareItem.status).all()

        by_location = self.db.query(
            Location.name,
            func.count(HardwareItem.id)
        ).join(HardwareItem).filter(HardwareItem.ist_aktiv == True).group_by(Location.name).all()

        return {
            "total_hardware": total_hardware,
            "by_category": dict(by_category),
            "by_status": dict(by_status),
            "by_location": dict(by_location)
        }

    def search_hardware(self, search_term: str) -> List[HardwareItem]:
        """Search hardware by various fields"""
        search_filter = or_(
            HardwareItem.bezeichnung.ilike(f"%{search_term}%"),
            HardwareItem.hersteller.ilike(f"%{search_term}%"),
            HardwareItem.seriennummer.ilike(f"%{search_term}%"),
            HardwareItem.ort.ilike(f"%{search_term}%")
        )

        return self.db.query(HardwareItem).filter(
            and_(HardwareItem.ist_aktiv == True, search_filter)
        ).order_by(desc(HardwareItem.erstellt_am)).all()


def get_hardware_service(db: Session = None) -> HardwareService:
    """Dependency injection for hardware service"""
    if db is None:
        db = next(get_db())
    return HardwareService(db)