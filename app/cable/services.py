"""
Cable inventory services for business logic
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, case, text
from datetime import datetime

from database.models.cable import Cable
from database.models.location import Location
from database.models.transaction import Transaction
from database.models.audit_log import AuditLog
from core.database import get_db


class CableService:
    """Service class for cable inventory operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_all_cables(self,
                      standort_filter: str = None,
                      typ_filter: str = None,
                      standard_filter: str = None,
                      health_filter: str = None,
                      nur_aktive: bool = True) -> List[Cable]:
        """
        Get all cables with optional filters
        """
        query = self.db.query(Cable)

        if nur_aktive:
            query = query.filter(Cable.ist_aktiv == True)

        if standort_filter and standort_filter != "Alle":
            query = query.join(Location).filter(Location.name == standort_filter)

        if typ_filter and typ_filter != "Alle":
            query = query.filter(Cable.typ == typ_filter)

        if standard_filter and standard_filter != "Alle":
            query = query.filter(Cable.standard == standard_filter)

        if health_filter and health_filter != "Alle":
            if health_filter == "kritisch":
                query = query.filter(Cable.menge <= 0)
            elif health_filter == "niedrig":
                query = query.filter(and_(Cable.menge > 0, Cable.menge <= Cable.mindestbestand))
            elif health_filter == "normal":
                query = query.filter(and_(Cable.menge > Cable.mindestbestand, Cable.menge < Cable.hoechstbestand))
            elif health_filter == "hoch":
                query = query.filter(Cable.menge >= Cable.hoechstbestand)

        return query.order_by(desc(Cable.erstellt_am)).all()

    def get_cable_by_id(self, cable_id: int) -> Optional[Cable]:
        """Get cable by ID"""
        return self.db.query(Cable).filter(Cable.id == cable_id).first()

    def create_cable(self, cable_data: Dict[str, Any], benutzer_id: int, use_defaults: bool = True) -> Cable:
        """Create new cable entry"""
        try:
            # Get default values from settings if requested
            if use_defaults:
                from settings.services import get_settings_service
                settings_service = get_settings_service()
                default_min = settings_service.get_setting_value("inventory.cable.default_min_stock", 5)
                default_max = settings_service.get_setting_value("inventory.cable.default_max_stock", 100)
            else:
                default_min = 5
                default_max = 100

            new_cable = Cable(
                typ=cable_data['typ'],
                standard=cable_data['standard'],
                laenge=cable_data['laenge'],
                standort_id=cable_data['standort_id'],
                lagerort=cable_data['lagerort'],
                menge=cable_data.get('menge', 0),
                mindestbestand=cable_data.get('mindestbestand', default_min),
                hoechstbestand=cable_data.get('hoechstbestand', default_max),
                farbe=cable_data.get('farbe'),
                stecker_typ_a=cable_data.get('stecker_typ_a'),
                stecker_typ_b=cable_data.get('stecker_typ_b'),
                hersteller=cable_data.get('hersteller'),
                modell=cable_data.get('modell'),
                einkaufspreis_pro_einheit=cable_data.get('einkaufspreis_pro_einheit'),
                lieferant=cable_data.get('lieferant'),
                artikel_nummer=cable_data.get('artikel_nummer'),
                notizen=cable_data.get('notizen'),
                erstellt_von=benutzer_id
            )

            self.db.add(new_cable)
            self.db.commit()
            self.db.refresh(new_cable)

            # Create transaction record
            transaction = Transaction.create_cable_eingang(
                cable_id=new_cable.id,
                benutzer_id=benutzer_id,
                standort_id=new_cable.standort_id,
                menge=new_cable.menge,
                beschreibung=f"Kabel hinzugefügt: {new_cable.bezeichnung}",
                kosten=float(new_cable.einkaufspreis_pro_einheit * new_cable.menge) if new_cable.einkaufspreis_pro_einheit else None
            )
            self.db.add(transaction)

            # Create audit log
            audit_log = AuditLog.log_data_change(
                benutzer_id=benutzer_id,
                benutzer_rolle="admin",
                aktion="Kabel erstellt",
                ressource_typ="cable",
                ressource_id=new_cable.id,
                neue_werte=new_cable.to_dict(),
                beschreibung=f"Neues Kabel erstellt: {new_cable.bezeichnung}"
            )
            self.db.add(audit_log)

            self.db.commit()
            return new_cable

        except Exception as e:
            self.db.rollback()
            raise e

    def update_cable(self, cable_id: int, cable_data: Dict[str, Any], benutzer_id: int) -> Optional[Cable]:
        """Update existing cable"""
        try:
            cable = self.db.query(Cable).filter(Cable.id == cable_id).first()
            if not cable:
                return None

            # Store old values for audit
            old_values = cable.to_dict()

            # Update fields
            for field, value in cable_data.items():
                if hasattr(cable, field) and field not in ['id', 'erstellt_am', 'erstellt_von']:
                    setattr(cable, field, value)

            cable.aktualisiert_von = benutzer_id
            cable.aktualisiert_am = datetime.utcnow()

            self.db.commit()
            self.db.refresh(cable)

            # Create audit log
            audit_log = AuditLog.log_data_change(
                benutzer_id=benutzer_id,
                benutzer_rolle="admin",
                aktion="Kabel aktualisiert",
                ressource_typ="cable",
                ressource_id=cable.id,
                alte_werte=old_values,
                neue_werte=cable.to_dict(),
                beschreibung=f"Kabel aktualisiert: {cable.bezeichnung}"
            )
            self.db.add(audit_log)
            self.db.commit()

            return cable

        except Exception as e:
            self.db.rollback()
            raise e

    def adjust_stock(self, cable_id: int, menge_aenderung: int, benutzer_id: int, grund: str = None) -> bool:
        """Adjust cable stock (positive or negative)"""
        try:
            cable = self.db.query(Cable).filter(Cable.id == cable_id).first()
            if not cable:
                return False

            old_values = cable.to_dict()
            alte_menge = cable.menge

            if menge_aenderung > 0:
                cable.hinzufuegen(menge_aenderung, benutzer_id, grund)
                aktion = f"Bestand erhöht (+{menge_aenderung})"
            else:
                if not cable.entfernen(abs(menge_aenderung), benutzer_id, grund):
                    return False
                aktion = f"Bestand reduziert ({menge_aenderung})"

            self.db.commit()

            # Create transaction record
            transaction = Transaction.create_cable_bestandsaenderung(
                cable_id=cable.id,
                benutzer_id=benutzer_id,
                alte_menge=alte_menge,
                neue_menge=cable.menge,
                menge_aenderung=menge_aenderung,
                beschreibung=f"{aktion}: {cable.bezeichnung}",
                grund=grund
            )
            self.db.add(transaction)

            # Create audit log
            audit_log = AuditLog.log_data_change(
                benutzer_id=benutzer_id,
                benutzer_rolle="admin",
                aktion=aktion,
                ressource_typ="cable",
                ressource_id=cable.id,
                alte_werte=old_values,
                neue_werte=cable.to_dict(),
                beschreibung=f"{aktion}: {cable.bezeichnung}"
            )
            self.db.add(audit_log)
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            return False

    def set_absolute_stock(self, cable_id: int, neue_menge: int, benutzer_id: int, grund: str = None) -> bool:
        """Set absolute stock quantity"""
        try:
            cable = self.db.query(Cable).filter(Cable.id == cable_id).first()
            if not cable:
                return False

            old_values = cable.to_dict()
            alte_menge = cable.menge

            cable.set_menge(neue_menge, benutzer_id, grund)
            self.db.commit()

            # Create transaction record
            transaction = Transaction.create_cable_bestandskorrektur(
                cable_id=cable.id,
                benutzer_id=benutzer_id,
                alte_menge=alte_menge,
                neue_menge=neue_menge,
                beschreibung=f"Bestandskorrektur: {cable.bezeichnung}",
                grund=grund
            )
            self.db.add(transaction)

            # Create audit log
            audit_log = AuditLog.log_data_change(
                benutzer_id=benutzer_id,
                benutzer_rolle="admin",
                aktion="Bestandskorrektur",
                ressource_typ="cable",
                ressource_id=cable.id,
                alte_werte=old_values,
                neue_werte=cable.to_dict(),
                beschreibung=f"Bestand geändert von {alte_menge} auf {neue_menge}: {cable.bezeichnung}"
            )
            self.db.add(audit_log)
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            return False

    def delete_cable(self, cable_id: int, benutzer_id: int, grund: str = None) -> bool:
        """Soft delete cable (set inactive)"""
        try:
            cable = self.db.query(Cable).filter(Cable.id == cable_id).first()
            if not cable:
                return False

            old_values = cable.to_dict()

            # Soft delete
            cable.ist_aktiv = False
            cable.aktualisiert_von = benutzer_id
            cable.aktualisiert_am = datetime.utcnow()

            if grund:
                cable.notizen = f"{cable.notizen or ''}\nDeaktiviert: {grund}".strip()

            self.db.commit()

            # Create audit log
            audit_log = AuditLog.log_data_change(
                benutzer_id=benutzer_id,
                benutzer_rolle="admin",
                aktion="Kabel deaktiviert",
                ressource_typ="cable",
                ressource_id=cable.id,
                alte_werte=old_values,
                neue_werte=cable.to_dict(),
                beschreibung=f"Kabel deaktiviert: {cable.bezeichnung}"
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

    def get_unique_types(self) -> List[str]:
        """Get list of unique cable types"""
        result = self.db.query(Cable.typ).distinct().all()
        return [r[0] for r in result if r[0]]

    def get_unique_standards(self) -> List[str]:
        """Get list of unique cable standards"""
        result = self.db.query(Cable.standard).distinct().all()
        return [r[0] for r in result if r[0]]

    def get_unique_manufacturers(self) -> List[str]:
        """Get list of unique manufacturers"""
        result = self.db.query(Cable.hersteller).distinct().all()
        return [r[0] for r in result if r[0]]

    def get_inventory_summary(self) -> Dict[str, Any]:
        """Get cable inventory summary statistics"""
        total_cables = self.db.query(Cable).filter(Cable.ist_aktiv == True).count()

        # Total stock quantity across all cables
        total_stock = self.db.query(func.sum(Cable.menge)).filter(Cable.ist_aktiv == True).scalar() or 0

        by_type = self.db.query(
            Cable.typ,
            func.count(Cable.id),
            func.sum(Cable.menge)
        ).filter(Cable.ist_aktiv == True).group_by(Cable.typ).all()

        # Simplified health status calculation
        total_active = self.db.query(Cable).filter(Cable.ist_aktiv == True).count()
        critical_count = self.db.query(Cable).filter(
            and_(Cable.ist_aktiv == True, Cable.menge <= 0)
        ).count()
        low_count = self.db.query(Cable).filter(
            and_(Cable.ist_aktiv == True, Cable.menge > 0, Cable.menge <= Cable.mindestbestand)
        ).count()
        high_count = self.db.query(Cable).filter(
            and_(Cable.ist_aktiv == True, Cable.menge >= Cable.hoechstbestand)
        ).count()
        normal_count = total_active - critical_count - low_count - high_count

        by_health = {
            "kritisch": critical_count,
            "niedrig": low_count,
            "normal": normal_count,
            "hoch": high_count
        }

        by_location = self.db.query(
            Location.name,
            func.count(Cable.id),
            func.sum(Cable.menge)
        ).join(Cable).filter(Cable.ist_aktiv == True).group_by(Location.name).all()

        # Calculate total value
        total_value = self.db.query(
            func.sum(Cable.menge * Cable.einkaufspreis_pro_einheit)
        ).filter(
            and_(Cable.ist_aktiv == True, Cable.einkaufspreis_pro_einheit.isnot(None))
        ).scalar() or 0

        return {
            "total_cables": total_cables,
            "total_stock": total_stock,
            "total_value": float(total_value),
            "by_type": {typ: {"count": count, "stock": stock} for typ, count, stock in by_type},
            "by_health": by_health,
            "by_location": {loc: {"count": count, "stock": stock} for loc, count, stock in by_location}
        }

    def search_cables(self, search_term: str) -> List[Cable]:
        """Search cables by various fields"""
        search_filter = or_(
            Cable.typ.ilike(f"%{search_term}%"),
            Cable.standard.ilike(f"%{search_term}%"),
            Cable.hersteller.ilike(f"%{search_term}%"),
            Cable.modell.ilike(f"%{search_term}%"),
            Cable.artikel_nummer.ilike(f"%{search_term}%"),
            Cable.lagerort.ilike(f"%{search_term}%")
        )

        return self.db.query(Cable).filter(
            and_(Cable.ist_aktiv == True, search_filter)
        ).order_by(desc(Cable.erstellt_am)).all()

    def get_low_stock_cables(self, threshold_type: str = "niedrig") -> List[Cable]:
        """Get cables with low stock levels"""
        if threshold_type == "kritisch":
            return self.db.query(Cable).filter(
                and_(Cable.ist_aktiv == True, Cable.menge <= 0)
            ).all()
        else:  # niedrig
            return self.db.query(Cable).filter(
                and_(Cable.ist_aktiv == True, Cable.menge <= Cable.mindestbestand, Cable.menge > 0)
            ).all()

    def bulk_stock_adjustment(self, cable_ids: List[int], menge_aenderung: int, benutzer_id: int, grund: str = None) -> Dict[str, int]:
        """Perform bulk stock adjustments"""
        results = {"success": 0, "failed": 0}

        for cable_id in cable_ids:
            if self.adjust_stock(cable_id, menge_aenderung, benutzer_id, grund):
                results["success"] += 1
            else:
                results["failed"] += 1

        return results

    def get_default_stock_levels(self) -> Dict[str, int]:
        """Get default min/max stock levels from settings"""
        try:
            from settings.services import get_settings_service
            settings_service = get_settings_service()
            return {
                "mindestbestand": settings_service.get_setting_value("inventory.cable.default_min_stock", 5),
                "hoechstbestand": settings_service.get_setting_value("inventory.cable.default_max_stock", 100)
            }
        except:
            # Fallback if settings not available
            return {"mindestbestand": 5, "hoechstbestand": 100}

    def bulk_update_stock_thresholds(self, updates: List[Dict[str, Any]], benutzer_id: int) -> Dict[str, int]:
        """Bulk update min/max stock thresholds for multiple cables"""
        results = {"success": 0, "failed": 0}

        try:
            for update in updates:
                cable_id = update.get('cable_id')
                new_min = update.get('mindestbestand')
                new_max = update.get('hoechstbestand')

                if not cable_id:
                    results["failed"] += 1
                    continue

                cable = self.get_cable_by_id(cable_id)
                if not cable:
                    results["failed"] += 1
                    continue

                # Update thresholds
                old_values = cable.to_dict()

                if new_min is not None:
                    cable.mindestbestand = new_min
                if new_max is not None:
                    cable.hoechstbestand = new_max

                cable.aktualisiert_von = benutzer_id

                # Create audit log
                from database.models.audit_log import AuditLog
                audit_log = AuditLog.log_data_change(
                    benutzer_id=benutzer_id,
                    benutzer_rolle="admin",
                    aktion="Bestandsgrenzen aktualisiert",
                    ressource_typ="cable",
                    ressource_id=cable.id,
                    alte_werte=old_values,
                    neue_werte=cable.to_dict(),
                    beschreibung=f"Bestandsgrenzen für {cable.bezeichnung} aktualisiert"
                )
                self.db.add(audit_log)
                results["success"] += 1

            self.db.commit()
            return results

        except Exception as e:
            self.db.rollback()
            results["failed"] = len(updates)
            return results


def get_cable_service(db: Session = None) -> CableService:
    """Dependency injection for cable service"""
    if db is None:
        db = next(get_db())
    return CableService(db)