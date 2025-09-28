"""
Notification services for stock alerts and critical events
"""

from typing import Dict, List, Any, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, text
from datetime import datetime, date, timedelta
from enum import Enum

from database.models.hardware import HardwareItem
from database.models.cable import Cable
from database.models.location import Location
from database.models.user import User
from database.models.audit_log import AuditLog
from core.database import get_db


class NotificationPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationType(Enum):
    STOCK_LOW = "stock_low"
    STOCK_OUT = "stock_out"
    STOCK_HIGH = "stock_high"
    WARRANTY_EXPIRING = "warranty_expiring"
    WARRANTY_EXPIRED = "warranty_expired"
    CRITICAL_ACTION = "critical_action"
    SYSTEM_ALERT = "system_alert"
    MAINTENANCE_DUE = "maintenance_due"


class NotificationService:
    """Service class for managing notifications and alerts"""

    def __init__(self, db: Session):
        self.db = db

    def _safe_get_attr(self, obj, attr_name, default=None):
        """Safely get attribute from object or dictionary"""
        try:
            # Handle None objects
            if obj is None:
                return default

            # Try object attribute access first (SQLAlchemy ORM objects)
            if hasattr(obj, attr_name):
                attr_value = getattr(obj, attr_name)
                return attr_value

            # Try dictionary access (when ORM objects are converted to dicts)
            elif isinstance(obj, dict):
                return obj.get(attr_name, default)

            # Try index access for tuples/lists
            elif isinstance(obj, (tuple, list)) and isinstance(attr_name, int):
                if 0 <= attr_name < len(obj):
                    return obj[attr_name]
                return default

            # Try string conversion for special cases
            elif hasattr(obj, '__dict__'):
                return getattr(obj, attr_name, default)

            else:
                return default

        except (AttributeError, KeyError, TypeError, IndexError) as e:
            # Log the error for debugging but don't fail
            print(f"_safe_get_attr error for {attr_name}: {e}")
            return default

    def get_all_notifications(self, user_role: str = "admin") -> List[Dict[str, Any]]:
        """Get all current notifications based on user role"""
        notifications = []

        try:
            # Validate database connection first
            if not self.db:
                raise Exception("Database connection not available")

            # Test database connectivity
            try:
                self.db.execute(text("SELECT 1"))
            except Exception as db_error:
                raise Exception(f"Database connection failed: {db_error}")

            # Stock alerts (accessible to netzwerker and above)
            if user_role in ["admin", "netzwerker"]:
                try:
                    stock_alerts = self._get_stock_alerts()
                    if isinstance(stock_alerts, list):
                        notifications.extend(stock_alerts)
                except Exception as e:
                    print(f"Error getting stock alerts: {e}")
                    # Add a notification about the stock alert error
                    notifications.append({
                        'id': 'stock_alert_error',
                        'type': NotificationType.SYSTEM_ALERT,
                        'priority': NotificationPriority.MEDIUM,
                        'title': 'Bestandswarnungen nicht verfügbar',
                        'message': f'Fehler beim Laden der Bestandswarnungen: {str(e)[:100]}',
                        'details': {'error': str(e)},
                        'timestamp': datetime.now(),
                        'action_url': '/cables',
                        'icon': '⚠️'
                    })

                try:
                    warranty_alerts = self._get_warranty_alerts()
                    if isinstance(warranty_alerts, list):
                        notifications.extend(warranty_alerts)
                except Exception as e:
                    print(f"Error getting warranty alerts: {e}")

                try:
                    critical_alerts = self._get_critical_action_alerts()
                    if isinstance(critical_alerts, list):
                        notifications.extend(critical_alerts)
                except Exception as e:
                    print(f"Error getting critical action alerts: {e}")

            # System alerts (admin only)
            if user_role == "admin":
                try:
                    system_alerts = self._get_system_alerts()
                    if isinstance(system_alerts, list):
                        notifications.extend(system_alerts)
                except Exception as e:
                    print(f"Error getting system alerts: {e}")

            # Sort by priority and timestamp with safe handling
            priority_order = {
                NotificationPriority.CRITICAL: 0,
                NotificationPriority.HIGH: 1,
                NotificationPriority.MEDIUM: 2,
                NotificationPriority.LOW: 3
            }

            def safe_sort_key(x):
                try:
                    priority = x.get('priority', NotificationPriority.LOW)
                    timestamp = x.get('timestamp', datetime.min)

                    if not isinstance(timestamp, datetime):
                        timestamp = datetime.min

                    return (
                        priority_order.get(priority, 3),
                        timestamp
                    )
                except Exception:
                    return (3, datetime.min)

            notifications.sort(key=safe_sort_key, reverse=True)

        except Exception as e:
            print(f"Critical error in get_all_notifications: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")

            # Return a fallback notification about the system issue
            notifications = [{
                'id': 'system_error',
                'type': NotificationType.SYSTEM_ALERT,
                'priority': NotificationPriority.HIGH,
                'title': 'Benachrichtigungssystem nicht verfügbar',
                'message': 'Es gab ein Problem beim Laden der Benachrichtigungen. Bitte versuchen Sie es später erneut.',
                'details': {'error': str(e), 'user_role': user_role},
                'timestamp': datetime.now(),
                'action_url': '/notifications',
                'icon': '⚠️'
            }]

        return notifications

    def _get_stock_alerts(self) -> List[Dict[str, Any]]:
        """Get stock-related alerts"""
        alerts = []

        try:
            # Low stock cables
            low_stock_cables = self.db.query(Cable).filter(
                and_(
                    Cable.ist_aktiv == True,
                    Cable.menge <= Cable.mindestbestand,
                    Cable.menge > 0
                )
            ).all()

            for cable in low_stock_cables:
                # Safe attribute access for both ORM objects and dictionaries
                cable_id = self._safe_get_attr(cable, 'id')
                cable_typ = self._safe_get_attr(cable, 'typ')
                cable_standard = self._safe_get_attr(cable, 'standard')
                cable_menge = self._safe_get_attr(cable, 'menge')
                cable_mindestbestand = self._safe_get_attr(cable, 'mindestbestand')

                # Handle standort relationship safely
                standort_name = "Unbekannt"
                try:
                    standort = self._safe_get_attr(cable, 'standort')
                    if standort:
                        standort_name = self._safe_get_attr(standort, 'name') or "Unbekannt"
                except (AttributeError, KeyError):
                    standort_name = "Unbekannt"

                alerts.append({
                    'id': f"low_stock_cable_{cable_id}",
                    'type': NotificationType.STOCK_LOW,
                    'priority': NotificationPriority.MEDIUM,
                    'title': f"Niedriger Bestand: {cable_typ} {cable_standard}",
                    'message': f"Aktueller Bestand: {cable_menge}, Mindestbestand: {cable_mindestbestand}",
                    'details': {
                        'cable_id': cable_id,
                        'current_stock': cable_menge,
                        'min_stock': cable_mindestbestand,
                        'location': standort_name
                    },
                    'timestamp': datetime.now(),
                    'action_url': f"/cables?id={cable_id}",
                    'icon': "⚠️"
                })
        except Exception as e:
            # If query fails, return empty alerts and log the error
            print(f"Error fetching low stock cables: {e}")
            pass

        try:
            # Out of stock cables
            out_of_stock_cables = self.db.query(Cable).filter(
                and_(
                    Cable.ist_aktiv == True,
                    Cable.menge == 0
                )
            ).all()

            for cable in out_of_stock_cables:
                # Safe attribute access
                cable_id = self._safe_get_attr(cable, 'id')
                cable_typ = self._safe_get_attr(cable, 'typ')
                cable_standard = self._safe_get_attr(cable, 'standard')
                cable_mindestbestand = self._safe_get_attr(cable, 'mindestbestand')

                # Handle standort relationship safely
                standort_name = "Unbekannt"
                try:
                    standort = self._safe_get_attr(cable, 'standort')
                    if standort:
                        standort_name = self._safe_get_attr(standort, 'name') or "Unbekannt"
                except (AttributeError, KeyError):
                    standort_name = "Unbekannt"

                alerts.append({
                    'id': f"out_of_stock_cable_{cable_id}",
                    'type': NotificationType.STOCK_OUT,
                    'priority': NotificationPriority.HIGH,
                    'title': f"Ausverkauft: {cable_typ} {cable_standard}",
                    'message': f"Kein Bestand vorhanden - Mindestbestand: {cable_mindestbestand}",
                    'details': {
                        'cable_id': cable_id,
                        'min_stock': cable_mindestbestand,
                        'location': standort_name
                    },
                    'timestamp': datetime.now(),
                    'action_url': f"/cables?id={cable_id}",
                    'icon': "🔴"
                })
        except Exception as e:
            print(f"Error fetching out of stock cables: {e}")
            pass

        try:
            # High stock cables (overstock warning)
            high_stock_cables = self.db.query(Cable).filter(
                and_(
                    Cable.ist_aktiv == True,
                    Cable.menge >= Cable.hoechstbestand,
                    Cable.hoechstbestand > 0
                )
            ).all()

            for cable in high_stock_cables:
                # Safe attribute access
                cable_id = self._safe_get_attr(cable, 'id')
                cable_typ = self._safe_get_attr(cable, 'typ')
                cable_standard = self._safe_get_attr(cable, 'standard')
                cable_menge = self._safe_get_attr(cable, 'menge')
                cable_hoechstbestand = self._safe_get_attr(cable, 'hoechstbestand')

                # Handle standort relationship safely
                standort_name = "Unbekannt"
                try:
                    standort = self._safe_get_attr(cable, 'standort')
                    if standort:
                        standort_name = self._safe_get_attr(standort, 'name') or "Unbekannt"
                except (AttributeError, KeyError):
                    standort_name = "Unbekannt"

                alerts.append({
                    'id': f"high_stock_cable_{cable_id}",
                    'type': NotificationType.STOCK_HIGH,
                    'priority': NotificationPriority.LOW,
                    'title': f"Überbestand: {cable_typ} {cable_standard}",
                    'message': f"Aktueller Bestand: {cable_menge}, Höchstbestand: {cable_hoechstbestand}",
                    'details': {
                        'cable_id': cable_id,
                        'current_stock': cable_menge,
                        'max_stock': cable_hoechstbestand,
                        'location': standort_name
                    },
                    'timestamp': datetime.now(),
                    'action_url': f"/cables?id={cable_id}",
                    'icon': "🟠"
                })
        except Exception as e:
            print(f"Error fetching high stock cables: {e}")
            pass

        return alerts

    def _get_warranty_alerts(self) -> List[Dict[str, Any]]:
        """Get warranty-related alerts"""
        alerts = []
        today = date.today()
        warning_period = today + timedelta(days=30)  # 30 days warning

        try:
            # Expiring warranties (within 30 days)
            expiring_warranties = self.db.query(HardwareItem).filter(
                and_(
                    HardwareItem.ist_aktiv == True,
                    HardwareItem.garantie_bis.isnot(None),
                    HardwareItem.garantie_bis >= today,
                    HardwareItem.garantie_bis <= warning_period
                )
            ).all()

            for item in expiring_warranties:
                # Safe attribute access
                item_id = self._safe_get_attr(item, 'id')
                item_name = self._safe_get_attr(item, 'name', 'Unbekannt')
                garantie_bis = self._safe_get_attr(item, 'garantie_bis')
                hersteller = self._safe_get_attr(item, 'hersteller', 'Unbekannt')
                seriennummer = self._safe_get_attr(item, 'seriennummer', 'Unbekannt')

                if garantie_bis:
                    # Handle both date objects and string dates
                    if isinstance(garantie_bis, str):
                        try:
                            garantie_bis = datetime.strptime(garantie_bis, '%Y-%m-%d').date()
                        except ValueError:
                            continue
                    elif isinstance(garantie_bis, datetime):
                        garantie_bis = garantie_bis.date()

                    days_left = (garantie_bis - today).days
                    priority = NotificationPriority.HIGH if days_left <= 7 else NotificationPriority.MEDIUM

                    alerts.append({
                        'id': f"warranty_expiring_{item_id}",
                        'type': NotificationType.WARRANTY_EXPIRING,
                        'priority': priority,
                        'title': f"Garantie läuft ab: {item_name}",
                        'message': f"Garantie endet in {days_left} Tag{'en' if days_left != 1 else ''} ({garantie_bis})",
                        'details': {
                            'hardware_id': item_id,
                            'warranty_end': garantie_bis,
                            'days_left': days_left,
                            'manufacturer': hersteller,
                            'serial_number': seriennummer
                        },
                        'timestamp': datetime.now(),
                        'action_url': f"/hardware?id={item_id}",
                        'icon': "⏰"
                    })
        except Exception as e:
            print(f"Error fetching expiring warranties: {e}")
            pass

        try:
            # Expired warranties
            expired_warranties = self.db.query(HardwareItem).filter(
                and_(
                    HardwareItem.ist_aktiv == True,
                    HardwareItem.garantie_bis.isnot(None),
                    HardwareItem.garantie_bis < today
                )
            ).all()

            for item in expired_warranties:
                # Safe attribute access
                item_id = self._safe_get_attr(item, 'id')
                item_name = self._safe_get_attr(item, 'name', 'Unbekannt')
                garantie_bis = self._safe_get_attr(item, 'garantie_bis')
                hersteller = self._safe_get_attr(item, 'hersteller', 'Unbekannt')
                seriennummer = self._safe_get_attr(item, 'seriennummer', 'Unbekannt')

                if garantie_bis:
                    # Handle both date objects and string dates
                    if isinstance(garantie_bis, str):
                        try:
                            garantie_bis = datetime.strptime(garantie_bis, '%Y-%m-%d').date()
                        except ValueError:
                            continue
                    elif isinstance(garantie_bis, datetime):
                        garantie_bis = garantie_bis.date()

                    days_expired = (today - garantie_bis).days

                    alerts.append({
                        'id': f"warranty_expired_{item_id}",
                        'type': NotificationType.WARRANTY_EXPIRED,
                        'priority': NotificationPriority.LOW,
                        'title': f"Garantie abgelaufen: {item_name}",
                        'message': f"Garantie seit {days_expired} Tag{'en' if days_expired != 1 else ''} abgelaufen ({garantie_bis})",
                        'details': {
                            'hardware_id': item_id,
                            'warranty_end': garantie_bis,
                            'days_expired': days_expired,
                            'manufacturer': hersteller,
                            'serial_number': seriennummer
                        },
                        'timestamp': datetime.now(),
                        'action_url': f"/hardware?id={item_id}",
                        'icon': "❌"
                    })
        except Exception as e:
            print(f"Error fetching expired warranties: {e}")
            pass

        return alerts

    def _get_critical_action_alerts(self) -> List[Dict[str, Any]]:
        """Get alerts for critical system actions"""
        alerts = []

        try:
            # Check for critical actions in the last 24 hours
            since_time = datetime.now() - timedelta(hours=24)
            critical_actions = [
                'Hardware gelöscht', 'Kabel gelöscht', 'Standort gelöscht',
                'Hardware deaktiviert', 'Kabel deaktiviert', 'Standort deaktiviert',
                'Benutzer deaktiviert', 'Benutzer gelöscht'
            ]

            recent_critical = self.db.query(AuditLog).filter(
                and_(
                    AuditLog.zeitstempel >= since_time,
                    or_(*[AuditLog.aktion.ilike(f"%{action}%") for action in critical_actions])
                )
            ).all()

            for log in recent_critical:
                # Safe attribute access
                log_id = self._safe_get_attr(log, 'id')
                log_aktion = self._safe_get_attr(log, 'aktion', 'Unbekannte Aktion')
                log_zeitstempel = self._safe_get_attr(log, 'zeitstempel', datetime.now())
                log_ressource_typ = self._safe_get_attr(log, 'ressource_typ', 'Unbekannt')
                log_ressource_id = self._safe_get_attr(log, 'ressource_id')
                log_beschreibung = self._safe_get_attr(log, 'beschreibung', '')

                user_name = "Unbekannt"
                try:
                    benutzer = self._safe_get_attr(log, 'benutzer')
                    if benutzer:
                        vorname = self._safe_get_attr(benutzer, 'vorname', '')
                        nachname = self._safe_get_attr(benutzer, 'nachname', '')
                        user_name = f"{vorname} {nachname}".strip() or "Unbekannt"
                except (AttributeError, KeyError):
                    user_name = "Unbekannt"

                # Handle zeitstempel safely
                time_str = "--:--"
                try:
                    if isinstance(log_zeitstempel, datetime):
                        time_str = log_zeitstempel.strftime('%H:%M')
                    elif isinstance(log_zeitstempel, str):
                        # Try to parse string timestamp
                        parsed_time = datetime.fromisoformat(log_zeitstempel.replace('Z', '+00:00'))
                        time_str = parsed_time.strftime('%H:%M')
                except (ValueError, AttributeError):
                    time_str = "--:--"

                alerts.append({
                    'id': f"critical_action_{log_id}",
                    'type': NotificationType.CRITICAL_ACTION,
                    'priority': NotificationPriority.HIGH,
                    'title': f"Kritische Aktion: {log_aktion}",
                    'message': f"Durchgeführt von {user_name} um {time_str}",
                    'details': {
                        'audit_log_id': log_id,
                        'action': log_aktion,
                        'user': user_name,
                        'resource_type': log_ressource_typ,
                        'resource_id': log_ressource_id,
                        'description': log_beschreibung
                    },
                    'timestamp': log_zeitstempel,
                    'action_url': f"/audit?id={log_id}",
                    'icon': "🚨"
                })
        except Exception as e:
            print(f"Error fetching critical action alerts: {e}")
            pass

        return alerts

    def _get_system_alerts(self) -> List[Dict[str, Any]]:
        """Get system-level alerts (admin only)"""
        alerts = []

        try:
            # Check for unusual activity patterns
            today = date.today()
            last_week = today - timedelta(days=7)

            # High number of deletions/deactivations
            critical_actions_count = self.db.query(AuditLog).filter(
                and_(
                    AuditLog.zeitstempel >= datetime.combine(last_week, datetime.min.time()),
                    or_(
                        AuditLog.aktion.ilike("%gelöscht%"),
                        AuditLog.aktion.ilike("%deaktiviert%")
                    )
                )
            ).count()

            if critical_actions_count > 10:  # Threshold for concern
                alerts.append({
                    'id': "high_critical_actions",
                    'type': NotificationType.SYSTEM_ALERT,
                    'priority': NotificationPriority.HIGH,
                    'title': "Ungewöhnlich viele kritische Aktionen",
                    'message': f"{critical_actions_count} kritische Aktionen in den letzten 7 Tagen erkannt",
                    'details': {
                        'count': critical_actions_count,
                        'period': "7 Tage",
                        'threshold': 10
                    },
                    'timestamp': datetime.now(),
                    'action_url': "/audit",
                    'icon': "⚠️"
                })
        except Exception as e:
            print(f"Error checking critical actions count: {e}")
            pass

        try:
            # Check for locations without inventory
            empty_locations = self.db.query(Location).filter(
                and_(
                    Location.ist_aktiv == True,
                    Location.typ.in_(["room", "storage"])
                )
            ).all()

            empty_count = 0
            for location in empty_locations:
                try:
                    location_id = self._safe_get_attr(location, 'id')
                    if location_id:
                        hardware_count = self.db.query(HardwareItem).filter(
                            and_(
                                HardwareItem.standort_id == location_id,
                                HardwareItem.ist_aktiv == True
                            )
                        ).count()

                        cable_count = self.db.query(Cable).filter(
                            and_(
                                Cable.standort_id == location_id,
                                Cable.ist_aktiv == True
                            )
                        ).count()

                        if hardware_count == 0 and cable_count == 0:
                            empty_count += 1
                except Exception as e:
                    print(f"Error checking location {location}: {e}")
                    continue

            if empty_count > 5:  # Threshold for empty locations
                alerts.append({
                    'id': "many_empty_locations",
                    'type': NotificationType.SYSTEM_ALERT,
                    'priority': NotificationPriority.MEDIUM,
                    'title': "Viele leere Standorte",
                    'message': f"{empty_count} Standorte ohne Inventar gefunden",
                    'details': {
                        'empty_count': empty_count,
                        'threshold': 5
                    },
                    'timestamp': datetime.now(),
                    'action_url': "/locations",
                    'icon': "📍"
                })
        except Exception as e:
            print(f"Error checking empty locations: {e}")
            pass

        return alerts

    def get_notification_summary(self, user_role: str = "admin") -> Dict[str, Any]:
        """Get summary of notifications by type and priority"""
        notifications = self.get_all_notifications(user_role)

        summary = {
            'total_count': len(notifications),
            'by_priority': {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0
            },
            'by_type': {},
            'recent_count': 0  # Last 24 hours
        }

        recent_time = datetime.now() - timedelta(hours=24)

        for notification in notifications:
            # Count by priority
            priority = notification.get('priority', NotificationPriority.LOW)
            if isinstance(priority, NotificationPriority):
                priority = priority.value
            summary['by_priority'][priority] = summary['by_priority'].get(priority, 0) + 1

            # Count by type
            notif_type = notification.get('type', 'unknown')
            if isinstance(notif_type, NotificationType):
                notif_type = notif_type.value
            summary['by_type'][notif_type] = summary['by_type'].get(notif_type, 0) + 1

            # Count recent notifications
            if notification.get('timestamp', datetime.min) >= recent_time:
                summary['recent_count'] += 1

        return summary

    def mark_notification_read(self, notification_id: str, user_id: int) -> bool:
        """Mark a notification as read for a user"""
        # In a full implementation, this would update a user_notifications table
        # For now, we'll return True as a placeholder
        return True

    def get_user_notification_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get notification preferences for a user"""
        # Placeholder implementation
        # Would load from user_notification_preferences table
        return {
            'email_notifications': True,
            'in_app_notifications': True,
            'stock_alerts': True,
            'warranty_alerts': True,
            'critical_alerts': True,
            'system_alerts': False  # Usually admin-only
        }

    def update_user_notification_preferences(self, user_id: int, preferences: Dict[str, Any]) -> bool:
        """Update notification preferences for a user"""
        # Placeholder implementation
        # Would update user_notification_preferences table
        return True

    def get_dashboard_alerts(self, user_role: str = "admin", limit: int = 5) -> List[Dict[str, Any]]:
        """Get top priority alerts for dashboard display"""
        all_notifications = self.get_all_notifications(user_role)

        # Filter for high priority notifications
        high_priority = [
            n for n in all_notifications
            if n.get('priority') in [NotificationPriority.CRITICAL, NotificationPriority.HIGH]
        ]

        return high_priority[:limit]

    def get_notification_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get notification trends over time"""
        # This would analyze historical notification patterns
        # Placeholder implementation
        return {
            'stock_alerts_trend': 'increasing',
            'warranty_alerts_trend': 'stable',
            'critical_actions_trend': 'decreasing',
            'total_alerts_avg': 15.3
        }


def get_notification_service(db: Session = None) -> NotificationService:
    """Dependency injection for notification service"""
    if db is None:
        db = next(get_db())
    return NotificationService(db)