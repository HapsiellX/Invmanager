"""
Location services for hierarchical location management
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from database.models.location import Location
from database.models.hardware import HardwareItem
from database.models.cable import Cable
from database.models.audit_log import AuditLog
from core.database import get_db


class LocationService:
    """Service class for location management operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_all_locations(self, nur_aktive: bool = True) -> List[Location]:
        """Get all locations"""
        query = self.db.query(Location)
        if nur_aktive:
            query = query.filter(Location.ist_aktiv == True)
        return query.order_by(Location.name).all()

    def get_location_by_id(self, location_id: int) -> Optional[Location]:
        """Get location by ID"""
        return self.db.query(Location).filter(Location.id == location_id).first()

    def get_root_locations(self) -> List[Location]:
        """Get all root locations (sites)"""
        return self.db.query(Location).filter(
            and_(Location.parent_id.is_(None), Location.ist_aktiv == True)
        ).order_by(Location.name).all()

    def get_location_hierarchy(self) -> List[Dict[str, Any]]:
        """Get complete location hierarchy as nested structure"""
        root_locations = self.get_root_locations()
        hierarchy = []

        for root in root_locations:
            hierarchy.append(self._build_location_tree(root))

        return hierarchy

    def _build_location_tree(self, location: Location) -> Dict[str, Any]:
        """Build tree structure for a location and its children"""
        tree_node = {
            "location": location,
            "data": location.to_dict(),
            "children": []
        }

        # Get direct children
        children = self.db.query(Location).filter(
            and_(Location.parent_id == location.id, Location.ist_aktiv == True)
        ).order_by(Location.name).all()

        for child in children:
            tree_node["children"].append(self._build_location_tree(child))

        return tree_node

    def get_location_statistics(self, location_id: int) -> Dict[str, Any]:
        """Get statistics for a specific location"""
        location = self.get_location_by_id(location_id)
        if not location:
            return {}

        # Get all child locations for counting
        all_children = location.get_all_children()
        child_ids = [child.id for child in all_children] + [location.id]

        # Count hardware items
        hardware_count = self.db.query(HardwareItem).filter(
            and_(HardwareItem.standort_id.in_(child_ids), HardwareItem.ist_aktiv == True)
        ).count()

        # Count cables
        cable_count = self.db.query(Cable).filter(
            and_(Cable.standort_id.in_(child_ids), Cable.ist_aktiv == True)
        ).count()

        # Get hardware by category
        hardware_by_category = self.db.query(
            HardwareItem.kategorie,
            func.count(HardwareItem.id)
        ).filter(
            and_(HardwareItem.standort_id.in_(child_ids), HardwareItem.ist_aktiv == True)
        ).group_by(HardwareItem.kategorie).all()

        # Get cable types
        cable_by_type = self.db.query(
            Cable.typ,
            func.count(Cable.id)
        ).filter(
            and_(Cable.standort_id.in_(child_ids), Cable.ist_aktiv == True)
        ).group_by(Cable.typ).all()

        # Calculate total stock value
        hardware_value = self.db.query(
            func.sum(HardwareItem.einkaufspreis)
        ).filter(
            and_(
                HardwareItem.standort_id.in_(child_ids),
                HardwareItem.ist_aktiv == True,
                HardwareItem.einkaufspreis.isnot(None)
            )
        ).scalar() or 0

        cable_value = self.db.query(
            func.sum(Cable.menge * Cable.einkaufspreis_pro_einheit)
        ).filter(
            and_(
                Cable.standort_id.in_(child_ids),
                Cable.ist_aktiv == True,
                Cable.einkaufspreis_pro_einheit.isnot(None)
            )
        ).scalar() or 0

        return {
            "location": location.to_dict(),
            "child_locations": len(all_children),
            "hardware_count": hardware_count,
            "cable_count": cable_count,
            "total_value": float(hardware_value + cable_value),
            "hardware_by_category": dict(hardware_by_category),
            "cable_by_type": dict(cable_by_type)
        }

    def create_location(self, location_data: Dict[str, Any], benutzer_id: int) -> Location:
        """Create new location"""
        try:
            # Validate parent exists and is active
            if location_data.get('parent_id'):
                parent = self.get_location_by_id(location_data['parent_id'])
                if not parent or not parent.ist_aktiv:
                    raise ValueError("Übergeordneter Standort nicht gefunden oder inaktiv")

            new_location = Location(
                name=location_data['name'],
                beschreibung=location_data.get('beschreibung'),
                parent_id=location_data.get('parent_id'),
                typ=location_data['typ'],
                adresse=location_data.get('adresse'),
                stadt=location_data.get('stadt'),
                postleitzahl=location_data.get('postleitzahl'),
                land=location_data.get('land', 'Deutschland'),
                kontakt_person=location_data.get('kontakt_person'),
                telefon=location_data.get('telefon'),
                email=location_data.get('email'),
                notizen=location_data.get('notizen')
            )

            self.db.add(new_location)
            self.db.commit()
            self.db.refresh(new_location)

            # Create audit log
            audit_log = AuditLog.log_data_change(
                benutzer_id=benutzer_id,
                benutzer_rolle="admin",
                aktion="Standort erstellt",
                ressource_typ="location",
                ressource_id=new_location.id,
                neue_werte=new_location.to_dict(),
                beschreibung=f"Neuer Standort erstellt: {new_location.name}"
            )
            self.db.add(audit_log)
            self.db.commit()

            return new_location

        except Exception as e:
            self.db.rollback()
            raise e

    def update_location(self, location_id: int, location_data: Dict[str, Any], benutzer_id: int) -> Optional[Location]:
        """Update existing location"""
        try:
            location = self.get_location_by_id(location_id)
            if not location:
                return None

            # Store old values for audit
            old_values = location.to_dict()

            # Validate parent change doesn't create circular reference
            new_parent_id = location_data.get('parent_id')
            if new_parent_id and new_parent_id != location.parent_id:
                if self._would_create_circular_reference(location_id, new_parent_id):
                    raise ValueError("Zirkuläre Referenz würde entstehen")

            # Update fields
            for field, value in location_data.items():
                if hasattr(location, field) and field not in ['id', 'erstellt_am']:
                    setattr(location, field, value)

            self.db.commit()
            self.db.refresh(location)

            # Create audit log
            audit_log = AuditLog.log_data_change(
                benutzer_id=benutzer_id,
                benutzer_rolle="admin",
                aktion="Standort aktualisiert",
                ressource_typ="location",
                ressource_id=location.id,
                alte_werte=old_values,
                neue_werte=location.to_dict(),
                beschreibung=f"Standort aktualisiert: {location.name}"
            )
            self.db.add(audit_log)
            self.db.commit()

            return location

        except Exception as e:
            self.db.rollback()
            raise e

    def delete_location(self, location_id: int, benutzer_id: int, grund: str = None) -> bool:
        """Soft delete location (set inactive)"""
        try:
            location = self.get_location_by_id(location_id)
            if not location:
                return False

            # Check if location has active children
            active_children = self.db.query(Location).filter(
                and_(Location.parent_id == location_id, Location.ist_aktiv == True)
            ).count()

            if active_children > 0:
                raise ValueError("Standort hat aktive Unterstandorte und kann nicht deaktiviert werden")

            # Check if location has active inventory
            hardware_count = self.db.query(HardwareItem).filter(
                and_(HardwareItem.standort_id == location_id, HardwareItem.ist_aktiv == True)
            ).count()

            cable_count = self.db.query(Cable).filter(
                and_(Cable.standort_id == location_id, Cable.ist_aktiv == True)
            ).count()

            if hardware_count > 0 or cable_count > 0:
                raise ValueError("Standort enthält noch aktives Inventar und kann nicht deaktiviert werden")

            old_values = location.to_dict()

            # Soft delete
            location.ist_aktiv = False
            if grund:
                location.notizen = f"{location.notizen or ''}\nDeaktiviert: {grund}".strip()

            self.db.commit()

            # Create audit log
            audit_log = AuditLog.log_data_change(
                benutzer_id=benutzer_id,
                benutzer_rolle="admin",
                aktion="Standort deaktiviert",
                ressource_typ="location",
                ressource_id=location.id,
                alte_werte=old_values,
                neue_werte=location.to_dict(),
                beschreibung=f"Standort deaktiviert: {location.name}"
            )
            self.db.add(audit_log)
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            return False

    def _would_create_circular_reference(self, location_id: int, new_parent_id: int) -> bool:
        """Check if changing parent would create circular reference"""
        if location_id == new_parent_id:
            return True

        # Check if new_parent_id is a descendant of location_id
        potential_parent = self.get_location_by_id(new_parent_id)
        while potential_parent and potential_parent.parent_id:
            if potential_parent.parent_id == location_id:
                return True
            potential_parent = self.get_location_by_id(potential_parent.parent_id)

        return False

    def move_location(self, location_id: int, new_parent_id: Optional[int], benutzer_id: int) -> bool:
        """Move location to new parent"""
        try:
            location = self.get_location_by_id(location_id)
            if not location:
                return False

            old_parent_id = location.parent_id

            # Validate move
            if new_parent_id:
                if self._would_create_circular_reference(location_id, new_parent_id):
                    raise ValueError("Zirkuläre Referenz würde entstehen")

                new_parent = self.get_location_by_id(new_parent_id)
                if not new_parent or not new_parent.ist_aktiv:
                    raise ValueError("Ziel-Standort nicht gefunden oder inaktiv")

            old_values = location.to_dict()
            location.parent_id = new_parent_id
            self.db.commit()

            # Create audit log
            old_parent_name = self.get_location_by_id(old_parent_id).name if old_parent_id else "Keine"
            new_parent_name = self.get_location_by_id(new_parent_id).name if new_parent_id else "Keine"

            audit_log = AuditLog.log_data_change(
                benutzer_id=benutzer_id,
                benutzer_rolle="admin",
                aktion="Standort verschoben",
                ressource_typ="location",
                ressource_id=location.id,
                alte_werte=old_values,
                neue_werte=location.to_dict(),
                beschreibung=f"Standort {location.name} von '{old_parent_name}' nach '{new_parent_name}' verschoben"
            )
            self.db.add(audit_log)
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            return False

    def get_locations_by_type(self, typ: str, nur_aktive: bool = True) -> List[Location]:
        """Get locations by type"""
        query = self.db.query(Location).filter(Location.typ == typ)
        if nur_aktive:
            query = query.filter(Location.ist_aktiv == True)
        return query.order_by(Location.name).all()

    def search_locations(self, search_term: str) -> List[Location]:
        """Search locations by name, description, or address"""
        search_filter = or_(
            Location.name.ilike(f"%{search_term}%"),
            Location.beschreibung.ilike(f"%{search_term}%"),
            Location.adresse.ilike(f"%{search_term}%"),
            Location.stadt.ilike(f"%{search_term}%")
        )

        return self.db.query(Location).filter(
            and_(Location.ist_aktiv == True, search_filter)
        ).order_by(Location.name).all()

    def get_location_path(self, location_id: int) -> List[Location]:
        """Get full path from root to location"""
        location = self.get_location_by_id(location_id)
        if not location:
            return []

        path = [location]
        current = location
        while current.parent_id:
            current = self.get_location_by_id(current.parent_id)
            if current:
                path.insert(0, current)
            else:
                break

        return path

    def get_available_parent_locations(self, location_id: Optional[int] = None) -> List[Location]:
        """Get available parent locations (excluding self and descendants)"""
        excluded_ids = []

        if location_id:
            # Exclude self and all descendants
            location = self.get_location_by_id(location_id)
            if location:
                excluded_ids.append(location_id)
                all_children = location.get_all_children()
                excluded_ids.extend([child.id for child in all_children])

        query = self.db.query(Location).filter(Location.ist_aktiv == True)
        if excluded_ids:
            query = query.filter(~Location.id.in_(excluded_ids))

        return query.order_by(Location.vollstaendiger_pfad).all()


def get_location_service(db: Session = None) -> LocationService:
    """Dependency injection for location service"""
    if db is None:
        db = next(get_db())
    return LocationService(db)