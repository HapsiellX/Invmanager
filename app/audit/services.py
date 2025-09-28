"""
Audit trail services for viewing and analyzing system activities
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text
from datetime import datetime, timedelta

from database.models.audit_log import AuditLog
from database.models.user import User
from core.database import get_db


class AuditService:
    """Service class for audit trail operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_audit_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        benutzer_id: Optional[int] = None,
        ressource_typ: Optional[str] = None,
        aktion: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search_term: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get audit logs with filtering and pagination"""

        query = self.db.query(AuditLog).join(User, AuditLog.benutzer_id == User.id)

        # Apply filters
        if benutzer_id:
            query = query.filter(AuditLog.benutzer_id == benutzer_id)

        if ressource_typ:
            query = query.filter(AuditLog.ressource_typ == ressource_typ)

        if aktion:
            query = query.filter(AuditLog.aktion.ilike(f"%{aktion}%"))

        if start_date:
            query = query.filter(AuditLog.zeitstempel >= start_date)

        if end_date:
            # Add one day to include the entire end date
            end_date_inclusive = end_date + timedelta(days=1)
            query = query.filter(AuditLog.zeitstempel < end_date_inclusive)

        if search_term:
            search_filter = or_(
                AuditLog.aktion.ilike(f"%{search_term}%"),
                AuditLog.beschreibung.ilike(f"%{search_term}%"),
                User.benutzername.ilike(f"%{search_term}%"),
                User.vorname.ilike(f"%{search_term}%"),
                User.nachname.ilike(f"%{search_term}%")
            )
            query = query.filter(search_filter)

        # Get total count
        total_count = query.count()

        # Apply pagination and ordering
        logs = query.order_by(desc(AuditLog.zeitstempel)).offset(offset).limit(limit).all()

        return {
            "logs": [
                {
                    "id": log.id,
                    "zeitstempel": log.zeitstempel,
                    "benutzer_id": log.benutzer_id,
                    "benutzer_name": f"{log.benutzer.vorname} {log.benutzer.nachname}" if log.benutzer else "Unbekannt",
                    "benutzername": log.benutzer.benutzername if log.benutzer else "Unbekannt",
                    "benutzer_rolle": log.benutzer_rolle,
                    "aktion": log.aktion,
                    "ressource_typ": log.ressource_typ,
                    "ressource_id": log.ressource_id,
                    "alte_werte": log.alte_werte,
                    "neue_werte": log.neue_werte,
                    "beschreibung": log.beschreibung,
                    "ip_adresse": log.ip_adresse,
                    "user_agent": log.user_agent
                }
                for log in logs
            ],
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }

    def get_audit_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get audit statistics for the specified period"""
        start_date = datetime.now() - timedelta(days=days)

        # Total activities
        total_activities = self.db.query(AuditLog).filter(
            AuditLog.zeitstempel >= start_date
        ).count()

        # Activities by action
        action_stats = self.db.query(
            AuditLog.aktion,
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.zeitstempel >= start_date
        ).group_by(AuditLog.aktion).order_by(desc('count')).all()

        # Activities by resource type
        resource_stats = self.db.query(
            AuditLog.ressource_typ,
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.zeitstempel >= start_date
        ).group_by(AuditLog.ressource_typ).order_by(desc('count')).all()

        # Activities by user
        user_stats = self.db.query(
            User.benutzername,
            User.vorname,
            User.nachname,
            func.count(AuditLog.id).label('count')
        ).join(AuditLog, User.id == AuditLog.benutzer_id).filter(
            AuditLog.zeitstempel >= start_date
        ).group_by(User.id, User.benutzername, User.vorname, User.nachname).order_by(desc('count')).all()

        # Daily activity trend
        daily_stats = self.db.query(
            func.date(AuditLog.zeitstempel).label('date'),
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.zeitstempel >= start_date
        ).group_by(func.date(AuditLog.zeitstempel)).order_by('date').all()

        return {
            "total_activities": total_activities,
            "period_days": days,
            "actions": [{"action": row.aktion, "count": row.count} for row in action_stats],
            "resource_types": [{"type": row.ressource_typ or "Unbekannt", "count": row.count} for row in resource_stats],
            "users": [
                {
                    "username": row.benutzername,
                    "full_name": f"{row.vorname} {row.nachname}",
                    "count": row.count
                }
                for row in user_stats
            ],
            "daily_trend": [
                {
                    "date": row.date.strftime('%Y-%m-%d'),
                    "count": row.count
                }
                for row in daily_stats
            ]
        }

    def get_resource_history(self, ressource_typ: str, ressource_id: int) -> List[Dict[str, Any]]:
        """Get complete history for a specific resource"""
        logs = self.db.query(AuditLog).join(User, AuditLog.benutzer_id == User.id).filter(
            and_(
                AuditLog.ressource_typ == ressource_typ,
                AuditLog.ressource_id == ressource_id
            )
        ).order_by(desc(AuditLog.zeitstempel)).all()

        return [
            {
                "id": log.id,
                "zeitstempel": log.zeitstempel,
                "benutzer_name": f"{log.benutzer.vorname} {log.benutzer.nachname}" if log.benutzer else "Unbekannt",
                "benutzername": log.benutzer.benutzername if log.benutzer else "Unbekannt",
                "benutzer_rolle": log.benutzer_rolle,
                "aktion": log.aktion,
                "alte_werte": log.alte_werte,
                "neue_werte": log.neue_werte,
                "beschreibung": log.beschreibung,
                "ip_adresse": log.ip_adresse
            }
            for log in logs
        ]

    def get_user_activity(self, benutzer_id: int, days: int = 30) -> Dict[str, Any]:
        """Get activity summary for a specific user"""
        start_date = datetime.now() - timedelta(days=days)

        user = self.db.query(User).filter(User.id == benutzer_id).first()
        if not user:
            return {"error": "Benutzer nicht gefunden"}

        # Get user's activities
        activities = self.db.query(AuditLog).filter(
            and_(
                AuditLog.benutzer_id == benutzer_id,
                AuditLog.zeitstempel >= start_date
            )
        ).order_by(desc(AuditLog.zeitstempel)).all()

        # Group by action
        action_counts = {}
        resource_counts = {}
        daily_counts = {}

        for activity in activities:
            # Count by action
            action = activity.aktion
            action_counts[action] = action_counts.get(action, 0) + 1

            # Count by resource type
            resource_type = activity.ressource_typ or "Unbekannt"
            resource_counts[resource_type] = resource_counts.get(resource_type, 0) + 1

            # Count by day
            day = activity.zeitstempel.date().strftime('%Y-%m-%d')
            daily_counts[day] = daily_counts.get(day, 0) + 1

        return {
            "user": {
                "id": user.id,
                "username": user.benutzername,
                "full_name": f"{user.vorname} {user.nachname}",
                "role": user.rolle
            },
            "period_days": days,
            "total_activities": len(activities),
            "action_breakdown": [{"action": k, "count": v} for k, v in action_counts.items()],
            "resource_breakdown": [{"type": k, "count": v} for k, v in resource_counts.items()],
            "daily_activity": [{"date": k, "count": v} for k, v in sorted(daily_counts.items())],
            "recent_activities": [
                {
                    "zeitstempel": activity.zeitstempel,
                    "aktion": activity.aktion,
                    "ressource_typ": activity.ressource_typ,
                    "beschreibung": activity.beschreibung
                }
                for activity in activities[:20]  # Last 20 activities
            ]
        }

    def get_critical_activities(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get critical activities (deletions, deactivations, etc.)"""
        start_date = datetime.now() - timedelta(days=days)

        critical_actions = [
            'Hardware gelöscht', 'Kabel gelöscht', 'Standort gelöscht',
            'Hardware deaktiviert', 'Kabel deaktiviert', 'Standort deaktiviert',
            'Benutzer deaktiviert', 'Benutzer gelöscht',
            'Einstellungen geändert'
        ]

        logs = self.db.query(AuditLog).join(User, AuditLog.benutzer_id == User.id).filter(
            and_(
                AuditLog.zeitstempel >= start_date,
                or_(*[AuditLog.aktion.ilike(f"%{action}%") for action in critical_actions])
            )
        ).order_by(desc(AuditLog.zeitstempel)).all()

        return [
            {
                "id": log.id,
                "zeitstempel": log.zeitstempel,
                "benutzer_name": f"{log.benutzer.vorname} {log.benutzer.nachname}" if log.benutzer else "Unbekannt",
                "benutzername": log.benutzer.benutzername if log.benutzer else "Unbekannt",
                "benutzer_rolle": log.benutzer_rolle,
                "aktion": log.aktion,
                "ressource_typ": log.ressource_typ,
                "ressource_id": log.ressource_id,
                "beschreibung": log.beschreibung,
                "ip_adresse": log.ip_adresse
            }
            for log in logs
        ]

    def get_login_activities(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get login and authentication activities"""
        start_date = datetime.now() - timedelta(days=days)

        auth_actions = ['Anmeldung', 'Abmeldung', 'Login', 'Logout', 'Authentifizierung']

        logs = self.db.query(AuditLog).join(User, AuditLog.benutzer_id == User.id).filter(
            and_(
                AuditLog.zeitstempel >= start_date,
                or_(*[AuditLog.aktion.ilike(f"%{action}%") for action in auth_actions])
            )
        ).order_by(desc(AuditLog.zeitstempel)).all()

        return [
            {
                "zeitstempel": log.zeitstempel,
                "benutzer_name": f"{log.benutzer.vorname} {log.benutzer.nachname}" if log.benutzer else "Unbekannt",
                "benutzername": log.benutzer.benutzername if log.benutzer else "Unbekannt",
                "aktion": log.aktion,
                "ip_adresse": log.ip_adresse,
                "user_agent": log.user_agent
            }
            for log in logs
        ]

    def export_audit_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format_type: str = "csv"
    ) -> str:
        """Export audit logs in specified format"""
        query = self.db.query(AuditLog).join(User, AuditLog.benutzer_id == User.id)

        if start_date:
            query = query.filter(AuditLog.zeitstempel >= start_date)

        if end_date:
            end_date_inclusive = end_date + timedelta(days=1)
            query = query.filter(AuditLog.zeitstempel < end_date_inclusive)

        logs = query.order_by(desc(AuditLog.zeitstempel)).all()

        if format_type == "csv":
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            header = [
                'Zeitstempel', 'Benutzer', 'Benutzername', 'Rolle', 'Aktion',
                'Ressource_Typ', 'Ressource_ID', 'Beschreibung', 'IP_Adresse'
            ]
            writer.writerow(header)

            # Write data
            for log in logs:
                benutzer_name = f"{log.benutzer.vorname} {log.benutzer.nachname}" if log.benutzer else "Unbekannt"
                benutzername = log.benutzer.benutzername if log.benutzer else "Unbekannt"

                row = [
                    log.zeitstempel.strftime('%Y-%m-%d %H:%M:%S'),
                    benutzer_name,
                    benutzername,
                    log.benutzer_rolle,
                    log.aktion,
                    log.ressource_typ,
                    log.ressource_id,
                    log.beschreibung,
                    log.ip_adresse
                ]
                writer.writerow(row)

            return output.getvalue()

        elif format_type == "json":
            import json

            data = {
                "export_timestamp": datetime.now().isoformat(),
                "logs": [
                    {
                        "zeitstempel": log.zeitstempel.isoformat(),
                        "benutzer_name": f"{log.benutzer.vorname} {log.benutzer.nachname}" if log.benutzer else "Unbekannt",
                        "benutzername": log.benutzer.benutzername if log.benutzer else "Unbekannt",
                        "benutzer_rolle": log.benutzer_rolle,
                        "aktion": log.aktion,
                        "ressource_typ": log.ressource_typ,
                        "ressource_id": log.ressource_id,
                        "alte_werte": log.alte_werte,
                        "neue_werte": log.neue_werte,
                        "beschreibung": log.beschreibung,
                        "ip_adresse": log.ip_adresse,
                        "user_agent": log.user_agent
                    }
                    for log in logs
                ]
            }

            return json.dumps(data, indent=2, ensure_ascii=False, default=str)

        else:
            raise ValueError(f"Nicht unterstütztes Export-Format: {format_type}")


def get_audit_service(db: Session = None) -> AuditService:
    """Dependency injection for audit service"""
    if db is None:
        db = next(get_db())
    return AuditService(db)