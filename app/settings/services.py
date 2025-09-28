"""
Settings services for system configuration management
"""

from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.models.settings import SystemSettings, SettingsManager
from database.models.audit_log import AuditLog
from core.database import get_db


class SettingsService:
    """Service class for system settings operations"""

    def __init__(self, db: Session):
        self.db = db
        self.manager = SettingsManager(db)

    def get_all_settings(self, nur_sichtbare: bool = True) -> List[SystemSettings]:
        """Get all settings, optionally filtered by visibility"""
        query = self.db.query(SystemSettings)
        if nur_sichtbare:
            query = query.filter(SystemSettings.ist_sichtbar == True)
        return query.order_by(SystemSettings.kategorie, SystemSettings.bezeichnung).all()

    def get_settings_by_category(self, kategorie: str, nur_sichtbare: bool = True) -> List[SystemSettings]:
        """Get settings for a specific category"""
        query = self.db.query(SystemSettings).filter(SystemSettings.kategorie == kategorie)
        if nur_sichtbare:
            query = query.filter(SystemSettings.ist_sichtbar == True)
        return query.order_by(SystemSettings.bezeichnung).all()

    def get_setting(self, key: str) -> Optional[SystemSettings]:
        """Get a specific setting by key"""
        return self.db.query(SystemSettings).filter(SystemSettings.key == key).first()

    def get_setting_value(self, key: str, default=None):
        """Get the parsed value of a setting"""
        return self.manager.get(key, default)

    def update_setting(self, key: str, new_value: Union[int, float, str, bool, dict, list], benutzer_id: int) -> bool:
        """Update a setting value with audit logging"""
        try:
            setting = self.get_setting(key)
            if not setting:
                return False

            # Validate the new value
            if not setting.validate_value(new_value):
                return False

            # Store old value for audit
            old_value = setting.parsed_value

            # Update the setting
            setting.set_value(new_value)
            self.db.commit()

            # Update cache
            self.manager.reload_cache()

            # Create audit log
            audit_log = AuditLog.log_data_change(
                benutzer_id=benutzer_id,
                benutzer_rolle="admin",
                aktion="Einstellung geändert",
                ressource_typ="setting",
                ressource_id=setting.id,
                alte_werte={"wert": str(old_value)},
                neue_werte={"wert": str(new_value)},
                beschreibung=f"Einstellung '{setting.bezeichnung}' geändert von '{old_value}' auf '{new_value}'"
            )
            self.db.add(audit_log)
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            return False

    def bulk_update_settings(self, updates: Dict[str, Any], benutzer_id: int) -> Dict[str, bool]:
        """Update multiple settings at once"""
        results = {}

        for key, value in updates.items():
            results[key] = self.update_setting(key, value, benutzer_id)

        return results

    def reset_setting_to_default(self, key: str, benutzer_id: int) -> bool:
        """Reset a setting to its default value"""
        # This would require storing default values, which we can implement later
        # For now, this is a placeholder
        return False

    def get_categories(self) -> List[str]:
        """Get all setting categories"""
        result = self.db.query(SystemSettings.kategorie).distinct().all()
        return [r[0] for r in result if r[0]]

    def create_setting(self, setting_data: Dict[str, Any], benutzer_id: int) -> Optional[SystemSettings]:
        """Create a new system setting"""
        try:
            new_setting = SystemSettings(**setting_data)
            self.db.add(new_setting)
            self.db.commit()
            self.db.refresh(new_setting)

            # Update cache
            self.manager.reload_cache()

            # Create audit log
            audit_log = AuditLog.log_data_change(
                benutzer_id=benutzer_id,
                benutzer_rolle="admin",
                aktion="Einstellung erstellt",
                ressource_typ="setting",
                ressource_id=new_setting.id,
                neue_werte=new_setting.to_dict(),
                beschreibung=f"Neue Einstellung erstellt: {new_setting.bezeichnung}"
            )
            self.db.add(audit_log)
            self.db.commit()

            return new_setting

        except Exception as e:
            self.db.rollback()
            return None

    def delete_setting(self, key: str, benutzer_id: int) -> bool:
        """Delete a setting (only if not required)"""
        try:
            setting = self.get_setting(key)
            if not setting or setting.ist_erforderlich:
                return False

            # Store for audit
            old_values = setting.to_dict()

            self.db.delete(setting)
            self.db.commit()

            # Update cache
            self.manager.reload_cache()

            # Create audit log
            audit_log = AuditLog.log_data_change(
                benutzer_id=benutzer_id,
                benutzer_rolle="admin",
                aktion="Einstellung gelöscht",
                ressource_typ="setting",
                ressource_id=setting.id,
                alte_werte=old_values,
                beschreibung=f"Einstellung gelöscht: {setting.bezeichnung}"
            )
            self.db.add(audit_log)
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            return False

    def get_inventory_defaults(self) -> Dict[str, Any]:
        """Get inventory-related default values for easy access"""
        return {
            "cable_min_stock": self.get_setting_value("inventory.cable.default_min_stock", 5),
            "cable_max_stock": self.get_setting_value("inventory.cable.default_max_stock", 100),
            "warranty_alert_days": self.get_setting_value("inventory.hardware.warranty_alert_days", 30)
        }

    def get_ui_settings(self) -> Dict[str, Any]:
        """Get UI-related settings for the frontend"""
        return {
            "items_per_page": self.get_setting_value("ui.items_per_page", 50),
            "refresh_interval": self.get_setting_value("ui.refresh_interval", 300)
        }

    def get_notification_settings(self) -> Dict[str, Any]:
        """Get notification settings"""
        return {
            "low_stock_enabled": self.get_setting_value("notifications.low_stock_enabled", True),
            "critical_stock_enabled": self.get_setting_value("notifications.critical_stock_enabled", True)
        }

    def initialize_default_settings(self):
        """Initialize default system settings"""
        SystemSettings.create_default_settings(self.db)
        self.manager.reload_cache()


def get_settings_service(db: Session = None) -> SettingsService:
    """Dependency injection for settings service"""
    if db is None:
        db = next(get_db())
    return SettingsService(db)