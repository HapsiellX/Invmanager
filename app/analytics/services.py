"""
Analytics services for inventory management
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timedelta
from decimal import Decimal

from database.models.hardware import HardwareItem
from database.models.cable import Cable
from database.models.location import Location
from database.models.transaction import Transaction
from database.models.audit_log import AuditLog
from core.database import get_db


class AnalyticsService:
    """Service class for analytics and reporting operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_inventory_overview(self) -> Dict[str, Any]:
        """Get comprehensive inventory overview"""
        # Hardware statistics
        hardware_stats = self.db.query(
            func.count(HardwareItem.id),
            func.sum(HardwareItem.einkaufspreis),
            func.avg(HardwareItem.einkaufspreis)
        ).filter(HardwareItem.ist_aktiv == True).first()

        # Cable statistics
        cable_stats = self.db.query(
            func.count(Cable.id),
            func.sum(Cable.menge * Cable.einkaufspreis_pro_einheit),
            func.sum(Cable.menge),
            func.avg(Cable.einkaufspreis_pro_einheit)
        ).filter(Cable.ist_aktiv == True).first()

        # Location statistics
        location_count = self.db.query(func.count(Location.id)).filter(
            Location.ist_aktiv == True
        ).scalar()

        # Low stock items
        low_stock_cables = self.db.query(Cable).filter(
            Cable.ist_aktiv == True,
            Cable.menge <= Cable.mindestbestand
        ).count()

        return {
            "hardware": {
                "total_items": hardware_stats[0] or 0,
                "total_value": float(hardware_stats[1] or 0),
                "average_value": float(hardware_stats[2] or 0)
            },
            "cables": {
                "total_types": cable_stats[0] or 0,
                "total_value": float(cable_stats[1] or 0),
                "total_quantity": int(cable_stats[2] or 0),
                "average_price": float(cable_stats[3] or 0),
                "low_stock_count": low_stock_cables
            },
            "locations": {
                "total_locations": location_count or 0
            }
        }

    def get_hardware_by_category(self) -> List[Dict[str, Any]]:
        """Get hardware distribution by category"""
        results = self.db.query(
            HardwareItem.kategorie,
            func.count(HardwareItem.id).label('count'),
            func.sum(HardwareItem.einkaufspreis).label('total_value')
        ).filter(
            HardwareItem.ist_aktiv == True
        ).group_by(HardwareItem.kategorie).all()

        return [
            {
                "category": row.kategorie or "Unbekannt",
                "count": row.count,
                "total_value": float(row.total_value or 0)
            }
            for row in results
        ]

    def get_hardware_by_status(self) -> List[Dict[str, Any]]:
        """Get hardware distribution by status"""
        results = self.db.query(
            HardwareItem.status,
            func.count(HardwareItem.id).label('count')
        ).filter(
            HardwareItem.ist_aktiv == True
        ).group_by(HardwareItem.status).all()

        return [
            {
                "status": row.status or "Unbekannt",
                "count": row.count
            }
            for row in results
        ]

    def get_cable_by_type(self) -> List[Dict[str, Any]]:
        """Get cable distribution by type"""
        results = self.db.query(
            Cable.typ,
            Cable.standard,
            func.count(Cable.id).label('types_count'),
            func.sum(Cable.menge).label('total_quantity'),
            func.sum(Cable.menge * Cable.einkaufspreis_pro_einheit).label('total_value')
        ).filter(
            Cable.ist_aktiv == True
        ).group_by(Cable.typ, Cable.standard).all()

        return [
            {
                "type": row.typ,
                "standard": row.standard,
                "types_count": row.types_count,
                "total_quantity": int(row.total_quantity or 0),
                "total_value": float(row.total_value or 0)
            }
            for row in results
        ]

    def get_location_inventory_distribution(self) -> List[Dict[str, Any]]:
        """Get inventory distribution across locations"""
        results = self.db.query(
            Location.name,
            Location.typ,
            func.count(HardwareItem.id).label('hardware_count'),
            func.count(Cable.id).label('cable_count')
        ).outerjoin(
            HardwareItem, Location.id == HardwareItem.standort_id
        ).outerjoin(
            Cable, Location.id == Cable.standort_id
        ).filter(
            Location.ist_aktiv == True
        ).group_by(Location.id, Location.name, Location.typ).all()

        return [
            {
                "location_name": row.name,
                "location_type": row.typ,
                "hardware_count": row.hardware_count or 0,
                "cable_count": row.cable_count or 0
            }
            for row in results
        ]

    def get_stock_alerts(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get stock alerts for low/high stock items"""
        # Low stock cables
        low_stock = self.db.query(Cable).filter(
            Cable.ist_aktiv == True,
            Cable.menge <= Cable.mindestbestand
        ).all()

        # High stock cables
        high_stock = self.db.query(Cable).filter(
            Cable.ist_aktiv == True,
            Cable.menge >= Cable.hoechstbestand
        ).all()

        # Out of stock cables
        out_of_stock = self.db.query(Cable).filter(
            Cable.ist_aktiv == True,
            Cable.menge == 0
        ).all()

        return {
            "low_stock": [
                {
                    "id": cable.id,
                    "type": cable.typ,
                    "standard": cable.standard,
                    "length": float(cable.laenge),
                    "current_stock": cable.menge,
                    "min_stock": cable.mindestbestand,
                    "location": cable.standort.name if cable.standort else "Unbekannt"
                }
                for cable in low_stock
            ],
            "high_stock": [
                {
                    "id": cable.id,
                    "type": cable.typ,
                    "standard": cable.standard,
                    "length": float(cable.laenge),
                    "current_stock": cable.menge,
                    "max_stock": cable.hoechstbestand,
                    "location": cable.standort.name if cable.standort else "Unbekannt"
                }
                for cable in high_stock
            ],
            "out_of_stock": [
                {
                    "id": cable.id,
                    "type": cable.typ,
                    "standard": cable.standard,
                    "length": float(cable.laenge),
                    "min_stock": cable.mindestbestand,
                    "location": cable.standort.name if cable.standort else "Unbekannt"
                }
                for cable in out_of_stock
            ]
        }

    def get_activity_timeline(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get recent activity timeline"""
        start_date = datetime.now() - timedelta(days=days)

        activities = self.db.query(AuditLog).filter(
            AuditLog.zeitstempel >= start_date
        ).order_by(AuditLog.zeitstempel.desc()).limit(100).all()

        return [
            {
                "timestamp": activity.zeitstempel,
                "action": activity.aktion,
                "resource_type": activity.ressource_typ,
                "resource_id": activity.ressource_id,
                "user_id": activity.benutzer_id,
                "description": activity.beschreibung
            }
            for activity in activities
        ]

    def get_value_trends(self, months: int = 12) -> Dict[str, List[Dict[str, Any]]]:
        """Get value trends over time"""
        # This is a simplified version - in a real scenario, you'd track historical values
        start_date = datetime.now() - timedelta(days=months * 30)

        # Get transactions over time
        transactions = self.db.query(
            func.date(Transaction.zeitstempel).label('date'),
            func.sum(Transaction.menge_aenderung).label('quantity_change'),
            Transaction.typ
        ).filter(
            Transaction.zeitstempel >= start_date
        ).group_by(
            func.date(Transaction.zeitstempel),
            Transaction.typ
        ).order_by(func.date(Transaction.zeitstempel)).all()

        trends = {}
        for transaction in transactions:
            date_str = transaction.date.strftime('%Y-%m-%d')
            if date_str not in trends:
                trends[date_str] = {}
            trends[date_str][transaction.typ] = transaction.quantity_change

        return {
            "daily_transactions": [
                {
                    "date": date,
                    "inbound": data.get("Eingang", 0),
                    "outbound": data.get("Ausgang", 0),
                    "transfer": data.get("Transfer", 0)
                }
                for date, data in trends.items()
            ]
        }

    def get_top_suppliers(self) -> List[Dict[str, Any]]:
        """Get top suppliers by inventory value"""
        # Hardware suppliers
        hardware_suppliers = self.db.query(
            HardwareItem.hersteller,
            func.count(HardwareItem.id).label('item_count'),
            func.sum(HardwareItem.einkaufspreis).label('total_value')
        ).filter(
            HardwareItem.ist_aktiv == True,
            HardwareItem.hersteller.isnot(None)
        ).group_by(HardwareItem.hersteller).all()

        # Cable suppliers
        cable_suppliers = self.db.query(
            Cable.lieferant,
            func.count(Cable.id).label('item_count'),
            func.sum(Cable.menge * Cable.einkaufspreis_pro_einheit).label('total_value')
        ).filter(
            Cable.ist_aktiv == True,
            Cable.lieferant.isnot(None)
        ).group_by(Cable.lieferant).all()

        # Combine and sort
        all_suppliers = {}

        for supplier in hardware_suppliers:
            name = supplier.hersteller
            if name not in all_suppliers:
                all_suppliers[name] = {"hardware_items": 0, "cable_items": 0, "total_value": 0}
            all_suppliers[name]["hardware_items"] = supplier.item_count
            all_suppliers[name]["total_value"] += float(supplier.total_value or 0)

        for supplier in cable_suppliers:
            name = supplier.lieferant
            if name not in all_suppliers:
                all_suppliers[name] = {"hardware_items": 0, "cable_items": 0, "total_value": 0}
            all_suppliers[name]["cable_items"] = supplier.item_count
            all_suppliers[name]["total_value"] += float(supplier.total_value or 0)

        return sorted([
            {
                "name": name,
                "hardware_items": data["hardware_items"],
                "cable_items": data["cable_items"],
                "total_items": data["hardware_items"] + data["cable_items"],
                "total_value": data["total_value"]
            }
            for name, data in all_suppliers.items()
        ], key=lambda x: x["total_value"], reverse=True)

    def get_space_utilization(self) -> List[Dict[str, Any]]:
        """Get space utilization statistics"""
        locations = self.db.query(Location).filter(
            Location.ist_aktiv == True,
            Location.typ.in_(["room", "storage"])
        ).all()

        utilization = []
        for location in locations:
            # Count items in this location
            hardware_count = self.db.query(HardwareItem).filter(
                HardwareItem.standort_id == location.id,
                HardwareItem.ist_aktiv == True
            ).count()

            cable_types = self.db.query(Cable).filter(
                Cable.standort_id == location.id,
                Cable.ist_aktiv == True
            ).count()

            utilization.append({
                "location_name": location.name,
                "location_type": location.typ,
                "hardware_items": hardware_count,
                "cable_types": cable_types,
                "total_items": hardware_count + cable_types,
                "path": location.vollstaendiger_pfad
            })

        return sorted(utilization, key=lambda x: x["total_items"], reverse=True)


def get_analytics_service(db: Session = None) -> AnalyticsService:
    """Dependency injection for analytics service"""
    if db is None:
        db = next(get_db())
    return AnalyticsService(db)