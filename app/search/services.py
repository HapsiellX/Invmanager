"""
Advanced search and filtering services
"""

from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text, desc, asc
from datetime import datetime, date
from decimal import Decimal

from database.models.hardware import HardwareItem
from database.models.cable import Cable
from database.models.location import Location
from database.models.user import User
from core.database import get_db


class SearchService:
    """Service class for advanced search and filtering operations"""

    def __init__(self, db: Session):
        self.db = db

    def advanced_hardware_search(
        self,
        search_term: Optional[str] = None,
        kategorie: Optional[str] = None,
        hersteller: Optional[str] = None,
        status: Optional[str] = None,
        standort_id: Optional[int] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        purchase_date_start: Optional[date] = None,
        purchase_date_end: Optional[date] = None,
        warranty_status: Optional[str] = None,
        has_mac_address: Optional[bool] = None,
        has_ip_address: Optional[bool] = None,
        sort_by: str = "name",
        sort_order: str = "asc",
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Advanced search for hardware items with multiple filters"""

        query = self.db.query(HardwareItem).filter(HardwareItem.ist_aktiv == True)

        # Text search across multiple fields
        if search_term:
            text_filter = or_(
                HardwareItem.name.ilike(f"%{search_term}%"),
                HardwareItem.modell.ilike(f"%{search_term}%"),
                HardwareItem.seriennummer.ilike(f"%{search_term}%"),
                HardwareItem.artikel_nummer.ilike(f"%{search_term}%"),
                HardwareItem.notizen.ilike(f"%{search_term}%")
            )
            query = query.filter(text_filter)

        # Category filter
        if kategorie:
            query = query.filter(HardwareItem.kategorie == kategorie)

        # Manufacturer filter
        if hersteller:
            query = query.filter(HardwareItem.hersteller == hersteller)

        # Status filter
        if status:
            query = query.filter(HardwareItem.status == status)

        # Location filter
        if standort_id:
            query = query.filter(HardwareItem.standort_id == standort_id)

        # Price range filter
        if price_min is not None:
            query = query.filter(HardwareItem.einkaufspreis >= Decimal(str(price_min)))
        if price_max is not None:
            query = query.filter(HardwareItem.einkaufspreis <= Decimal(str(price_max)))

        # Purchase date range filter
        if purchase_date_start:
            query = query.filter(HardwareItem.einkaufsdatum >= purchase_date_start)
        if purchase_date_end:
            query = query.filter(HardwareItem.einkaufsdatum <= purchase_date_end)

        # Warranty status filter
        if warranty_status:
            today = date.today()
            if warranty_status == "active":
                query = query.filter(HardwareItem.garantie_bis >= today)
            elif warranty_status == "expired":
                query = query.filter(
                    and_(
                        HardwareItem.garantie_bis.isnot(None),
                        HardwareItem.garantie_bis < today
                    )
                )
            elif warranty_status == "expiring_soon":
                # Expiring within 30 days
                from datetime import timedelta
                soon = today + timedelta(days=30)
                query = query.filter(
                    and_(
                        HardwareItem.garantie_bis >= today,
                        HardwareItem.garantie_bis <= soon
                    )
                )

        # MAC address filter
        if has_mac_address is not None:
            if has_mac_address:
                query = query.filter(HardwareItem.mac_adresse.isnot(None))
            else:
                query = query.filter(HardwareItem.mac_adresse.is_(None))

        # IP address filter
        if has_ip_address is not None:
            if has_ip_address:
                query = query.filter(HardwareItem.ip_adresse.isnot(None))
            else:
                query = query.filter(HardwareItem.ip_adresse.is_(None))

        # Get total count before pagination
        total_count = query.count()

        # Apply sorting
        sort_column = getattr(HardwareItem, sort_by, HardwareItem.name)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Apply pagination
        items = query.offset(offset).limit(limit).all()

        return {
            "items": [item.to_dict() for item in items],
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }

    def advanced_cable_search(
        self,
        search_term: Optional[str] = None,
        typ: Optional[str] = None,
        standard: Optional[str] = None,
        length_min: Optional[float] = None,
        length_max: Optional[float] = None,
        standort_id: Optional[int] = None,
        farbe: Optional[str] = None,
        stecker_typ: Optional[str] = None,
        stock_status: Optional[str] = None,
        sort_by: str = "typ",
        sort_order: str = "asc",
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Advanced search for cables with multiple filters"""

        query = self.db.query(Cable).filter(Cable.ist_aktiv == True)

        # Text search
        if search_term:
            text_filter = or_(
                Cable.typ.ilike(f"%{search_term}%"),
                Cable.standard.ilike(f"%{search_term}%"),
                Cable.hersteller.ilike(f"%{search_term}%"),
                Cable.modell.ilike(f"%{search_term}%"),
                Cable.artikel_nummer.ilike(f"%{search_term}%"),
                Cable.notizen.ilike(f"%{search_term}%")
            )
            query = query.filter(text_filter)

        # Type filter
        if typ:
            query = query.filter(Cable.typ == typ)

        # Standard filter
        if standard:
            query = query.filter(Cable.standard == standard)

        # Length range filter
        if length_min is not None:
            query = query.filter(Cable.laenge >= Decimal(str(length_min)))
        if length_max is not None:
            query = query.filter(Cable.laenge <= Decimal(str(length_max)))

        # Location filter
        if standort_id:
            query = query.filter(Cable.standort_id == standort_id)

        # Color filter
        if farbe:
            query = query.filter(Cable.farbe == farbe)

        # Connector type filter (either end)
        if stecker_typ:
            connector_filter = or_(
                Cable.stecker_typ_a == stecker_typ,
                Cable.stecker_typ_b == stecker_typ
            )
            query = query.filter(connector_filter)

        # Stock status filter
        if stock_status:
            if stock_status == "in_stock":
                query = query.filter(Cable.menge > 0)
            elif stock_status == "out_of_stock":
                query = query.filter(Cable.menge == 0)
            elif stock_status == "low_stock":
                query = query.filter(Cable.menge <= Cable.mindestbestand)
            elif stock_status == "high_stock":
                query = query.filter(Cable.menge >= Cable.hoechstbestand)

        # Get total count
        total_count = query.count()

        # Apply sorting
        sort_column = getattr(Cable, sort_by, Cable.typ)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Apply pagination
        items = query.offset(offset).limit(limit).all()

        return {
            "items": [item.to_dict() for item in items],
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }

    def global_search(
        self,
        search_term: str,
        search_types: List[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Global search across all inventory types"""

        if search_types is None:
            search_types = ["hardware", "cables", "locations"]

        results = {}

        # Search hardware
        if "hardware" in search_types:
            hardware_query = self.db.query(HardwareItem).filter(
                and_(
                    HardwareItem.ist_aktiv == True,
                    or_(
                        HardwareItem.name.ilike(f"%{search_term}%"),
                        HardwareItem.modell.ilike(f"%{search_term}%"),
                        HardwareItem.seriennummer.ilike(f"%{search_term}%"),
                        HardwareItem.artikel_nummer.ilike(f"%{search_term}%"),
                        HardwareItem.hersteller.ilike(f"%{search_term}%")
                    )
                )
            ).limit(limit).all()

            results["hardware"] = [
                {
                    "id": item.id,
                    "name": item.name,
                    "type": "Hardware",
                    "details": f"{item.hersteller} {item.modell}",
                    "location": item.standort.name if item.standort else "Unbekannt",
                    "status": item.status
                }
                for item in hardware_query
            ]

        # Search cables
        if "cables" in search_types:
            cable_query = self.db.query(Cable).filter(
                and_(
                    Cable.ist_aktiv == True,
                    or_(
                        Cable.typ.ilike(f"%{search_term}%"),
                        Cable.standard.ilike(f"%{search_term}%"),
                        Cable.hersteller.ilike(f"%{search_term}%"),
                        Cable.modell.ilike(f"%{search_term}%"),
                        Cable.artikel_nummer.ilike(f"%{search_term}%")
                    )
                )
            ).limit(limit).all()

            results["cables"] = [
                {
                    "id": cable.id,
                    "name": f"{cable.typ} {cable.standard}",
                    "type": "Kabel",
                    "details": f"{cable.laenge}m - {cable.farbe}",
                    "location": cable.standort.name if cable.standort else "Unbekannt",
                    "stock": cable.menge
                }
                for cable in cable_query
            ]

        # Search locations
        if "locations" in search_types:
            location_query = self.db.query(Location).filter(
                and_(
                    Location.ist_aktiv == True,
                    or_(
                        Location.name.ilike(f"%{search_term}%"),
                        Location.beschreibung.ilike(f"%{search_term}%"),
                        Location.adresse.ilike(f"%{search_term}%"),
                        Location.stadt.ilike(f"%{search_term}%")
                    )
                )
            ).limit(limit).all()

            results["locations"] = [
                {
                    "id": location.id,
                    "name": location.name,
                    "type": "Standort",
                    "details": location.typ,
                    "path": location.vollstaendiger_pfad,
                    "address": location.adresse or ""
                }
                for location in location_query
            ]

        return results

    def get_filter_options(self) -> Dict[str, Any]:
        """Get available filter options for dropdown menus"""

        # Hardware categories
        hw_categories = self.db.query(HardwareItem.kategorie).filter(
            and_(
                HardwareItem.ist_aktiv == True,
                HardwareItem.kategorie.isnot(None)
            )
        ).distinct().all()

        # Hardware manufacturers
        hw_manufacturers = self.db.query(HardwareItem.hersteller).filter(
            and_(
                HardwareItem.ist_aktiv == True,
                HardwareItem.hersteller.isnot(None)
            )
        ).distinct().all()

        # Hardware statuses
        hw_statuses = self.db.query(HardwareItem.status).filter(
            and_(
                HardwareItem.ist_aktiv == True,
                HardwareItem.status.isnot(None)
            )
        ).distinct().all()

        # Cable types
        cable_types = self.db.query(Cable.typ).filter(
            and_(
                Cable.ist_aktiv == True,
                Cable.typ.isnot(None)
            )
        ).distinct().all()

        # Cable standards
        cable_standards = self.db.query(Cable.standard).filter(
            and_(
                Cable.ist_aktiv == True,
                Cable.standard.isnot(None)
            )
        ).distinct().all()

        # Cable colors
        cable_colors = self.db.query(Cable.farbe).filter(
            and_(
                Cable.ist_aktiv == True,
                Cable.farbe.isnot(None)
            )
        ).distinct().all()

        # Connector types
        connector_types_a = self.db.query(Cable.stecker_typ_a).filter(
            and_(
                Cable.ist_aktiv == True,
                Cable.stecker_typ_a.isnot(None)
            )
        ).distinct().all()

        connector_types_b = self.db.query(Cable.stecker_typ_b).filter(
            and_(
                Cable.ist_aktiv == True,
                Cable.stecker_typ_b.isnot(None)
            )
        ).distinct().all()

        # Combine connector types
        all_connectors = set()
        for row in connector_types_a:
            if row[0]:
                all_connectors.add(row[0])
        for row in connector_types_b:
            if row[0]:
                all_connectors.add(row[0])

        # Active locations
        locations = self.db.query(Location.id, Location.name, Location.vollstaendiger_pfad).filter(
            Location.ist_aktiv == True
        ).order_by(Location.vollstaendiger_pfad).all()

        return {
            "hardware": {
                "categories": sorted([row[0] for row in hw_categories if row[0]]),
                "manufacturers": sorted([row[0] for row in hw_manufacturers if row[0]]),
                "statuses": sorted([row[0] for row in hw_statuses if row[0]])
            },
            "cables": {
                "types": sorted([row[0] for row in cable_types if row[0]]),
                "standards": sorted([row[0] for row in cable_standards if row[0]]),
                "colors": sorted([row[0] for row in cable_colors if row[0]]),
                "connectors": sorted(list(all_connectors))
            },
            "locations": [
                {
                    "id": loc.id,
                    "name": loc.name,
                    "path": loc.vollstaendiger_pfad
                }
                for loc in locations
            ]
        }

    def get_search_suggestions(self, partial_term: str, search_type: str = "all") -> List[str]:
        """Get search suggestions based on partial input"""

        suggestions = set()

        if search_type in ["all", "hardware"]:
            # Hardware suggestions
            hw_suggestions = self.db.query(HardwareItem.name).filter(
                and_(
                    HardwareItem.ist_aktiv == True,
                    HardwareItem.name.ilike(f"%{partial_term}%")
                )
            ).distinct().limit(10).all()

            for row in hw_suggestions:
                if row[0]:
                    suggestions.add(row[0])

            # Add manufacturer suggestions
            mfg_suggestions = self.db.query(HardwareItem.hersteller).filter(
                and_(
                    HardwareItem.ist_aktiv == True,
                    HardwareItem.hersteller.ilike(f"%{partial_term}%")
                )
            ).distinct().limit(5).all()

            for row in mfg_suggestions:
                if row[0]:
                    suggestions.add(row[0])

        if search_type in ["all", "cables"]:
            # Cable suggestions
            cable_suggestions = self.db.query(Cable.typ).filter(
                and_(
                    Cable.ist_aktiv == True,
                    Cable.typ.ilike(f"%{partial_term}%")
                )
            ).distinct().limit(10).all()

            for row in cable_suggestions:
                if row[0]:
                    suggestions.add(row[0])

        if search_type in ["all", "locations"]:
            # Location suggestions
            location_suggestions = self.db.query(Location.name).filter(
                and_(
                    Location.ist_aktiv == True,
                    Location.name.ilike(f"%{partial_term}%")
                )
            ).distinct().limit(10).all()

            for row in location_suggestions:
                if row[0]:
                    suggestions.add(row[0])

        return sorted(list(suggestions))[:15]  # Limit to 15 suggestions

    def save_search_preset(self, user_id: int, name: str, search_params: Dict[str, Any]) -> bool:
        """Save search parameters as a preset for quick access"""
        # This would typically be saved to a user_search_presets table
        # For now, we'll implement this as a placeholder
        # In a full implementation, you would create a new model for search presets
        return True

    def get_saved_search_presets(self, user_id: int) -> List[Dict[str, Any]]:
        """Get saved search presets for a user"""
        # Placeholder implementation
        # Would load from user_search_presets table
        return []

    def get_recent_searches(self, user_id: int, limit: int = 10) -> List[str]:
        """Get recent search terms for a user"""
        # This would be implemented with a search_history table
        # Placeholder implementation
        return []


def get_search_service(db: Session = None) -> SearchService:
    """Dependency injection for search service"""
    if db is None:
        db = next(get_db())
    return SearchService(db)