"""
System settings model for dynamic configuration
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Numeric, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from typing import Dict, Any, Union

from core.database import Base


class SystemSettings(Base):
    """
    System-wide settings that can be configured by administrators
    """
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)

    # Setting identification
    key = Column(String(100), nullable=False, unique=True, index=True)
    kategorie = Column(String(50), nullable=False, index=True)  # inventory, security, ui, notifications

    # Setting value and metadata
    wert = Column(Text, nullable=False)  # Stored as string, parsed based on datentyp
    datentyp = Column(String(20), nullable=False)  # int, float, string, boolean, json

    # Description and help text
    bezeichnung = Column(String(200), nullable=False)  # Human readable name
    beschreibung = Column(Text)  # Detailed description
    hilfe_text = Column(Text)  # Help text for admins

    # Validation constraints
    min_wert = Column(Text)  # Minimum value (for numbers)
    max_wert = Column(Text)  # Maximum value (for numbers)
    erlaubte_werte = Column(JSON)  # List of allowed values for enums

    # System behavior
    ist_erforderlich = Column(Boolean, default=True, nullable=False)
    ist_sichtbar = Column(Boolean, default=True, nullable=False)  # Show in admin interface
    neustart_erforderlich = Column(Boolean, default=False, nullable=False)

    # Timestamps
    erstellt_am = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    aktualisiert_am = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<SystemSettings(key='{self.key}', wert='{self.wert}')>"

    @property
    def parsed_value(self) -> Union[int, float, str, bool, dict, list]:
        """Get the parsed value based on data type"""
        if self.datentyp == "int":
            return int(self.wert)
        elif self.datentyp == "float":
            return float(self.wert)
        elif self.datentyp == "boolean":
            return self.wert.lower() in ("true", "1", "yes", "on")
        elif self.datentyp == "json":
            import json
            return json.loads(self.wert)
        else:  # string
            return self.wert

    def set_value(self, value: Union[int, float, str, bool, dict, list]) -> None:
        """Set value with automatic type conversion"""
        if self.datentyp == "json":
            import json
            self.wert = json.dumps(value)
        else:
            self.wert = str(value)

    def validate_value(self, value: Union[int, float, str, bool, dict, list]) -> bool:
        """Validate if a value is acceptable for this setting"""
        try:
            # Type validation
            if self.datentyp == "int":
                val = int(value)
                if self.min_wert and val < int(self.min_wert):
                    return False
                if self.max_wert and val > int(self.max_wert):
                    return False
            elif self.datentyp == "float":
                val = float(value)
                if self.min_wert and val < float(self.min_wert):
                    return False
                if self.max_wert and val > float(self.max_wert):
                    return False
            elif self.datentyp == "boolean":
                if not isinstance(value, bool) and str(value).lower() not in ("true", "false", "1", "0", "yes", "no", "on", "off"):
                    return False
            elif self.datentyp == "string":
                if self.erlaubte_werte and value not in self.erlaubte_werte:
                    return False
            elif self.datentyp == "json":
                import json
                json.dumps(value)  # Test if serializable

            return True
        except (ValueError, TypeError):
            return False

    def to_dict(self) -> dict:
        """Convert setting to dictionary"""
        return {
            "id": self.id,
            "key": self.key,
            "kategorie": self.kategorie,
            "wert": self.wert,
            "parsed_value": self.parsed_value,
            "datentyp": self.datentyp,
            "bezeichnung": self.bezeichnung,
            "beschreibung": self.beschreibung,
            "hilfe_text": self.hilfe_text,
            "min_wert": self.min_wert,
            "max_wert": self.max_wert,
            "erlaubte_werte": self.erlaubte_werte,
            "ist_erforderlich": self.ist_erforderlich,
            "ist_sichtbar": self.ist_sichtbar,
            "neustart_erforderlich": self.neustart_erforderlich,
            "erstellt_am": self.erstellt_am.isoformat() if self.erstellt_am else None,
            "aktualisiert_am": self.aktualisiert_am.isoformat() if self.aktualisiert_am else None
        }

    @classmethod
    def create_default_settings(cls, db_session):
        """Create default system settings"""
        default_settings = [
            # Inventory settings
            {
                "key": "inventory.cable.default_min_stock",
                "kategorie": "inventory",
                "wert": "5",
                "datentyp": "int",
                "bezeichnung": "Standard Mindestbestand für Kabel",
                "beschreibung": "Der Standard-Mindestbestand, der für neue Kabel verwendet wird",
                "hilfe_text": "Wenn der Bestand unter diesen Wert fällt, wird eine Warnung angezeigt",
                "min_wert": "0",
                "max_wert": "1000",
                "ist_erforderlich": True,
                "ist_sichtbar": True
            },
            {
                "key": "inventory.cable.default_max_stock",
                "kategorie": "inventory",
                "wert": "100",
                "datentyp": "int",
                "bezeichnung": "Standard Höchstbestand für Kabel",
                "beschreibung": "Der Standard-Höchstbestand, der für neue Kabel verwendet wird",
                "hilfe_text": "Warnt vor Überbestand wenn dieser Wert überschritten wird",
                "min_wert": "1",
                "max_wert": "10000",
                "ist_erforderlich": True,
                "ist_sichtbar": True
            },
            {
                "key": "inventory.hardware.warranty_alert_days",
                "kategorie": "inventory",
                "wert": "30",
                "datentyp": "int",
                "bezeichnung": "Garantie-Warnung (Tage vorher)",
                "beschreibung": "Anzahl Tage vor Garantieablauf für Warnungen",
                "hilfe_text": "System warnt X Tage vor Ablauf der Hardware-Garantie",
                "min_wert": "1",
                "max_wert": "365",
                "ist_erforderlich": True,
                "ist_sichtbar": True
            },
            # UI settings
            {
                "key": "ui.items_per_page",
                "kategorie": "ui",
                "wert": "50",
                "datentyp": "int",
                "bezeichnung": "Einträge pro Seite",
                "beschreibung": "Anzahl der Einträge, die pro Seite in Tabellen angezeigt werden",
                "hilfe_text": "Höhere Werte können die Ladezeit beeinträchtigen",
                "min_wert": "10",
                "max_wert": "200",
                "ist_erforderlich": True,
                "ist_sichtbar": True
            },
            {
                "key": "ui.refresh_interval",
                "kategorie": "ui",
                "wert": "300",
                "datentyp": "int",
                "bezeichnung": "Auto-Aktualisierung (Sekunden)",
                "beschreibung": "Intervall für automatische Aktualisierung der Dashboard-Daten",
                "hilfe_text": "0 = keine automatische Aktualisierung",
                "min_wert": "0",
                "max_wert": "3600",
                "ist_erforderlich": True,
                "ist_sichtbar": True
            },
            # Security settings
            {
                "key": "security.session_timeout",
                "kategorie": "security",
                "wert": "3600",
                "datentyp": "int",
                "bezeichnung": "Session Timeout (Sekunden)",
                "beschreibung": "Automatisches Logout nach Inaktivität",
                "hilfe_text": "Benutzer müssen sich nach dieser Zeit erneut anmelden",
                "min_wert": "300",
                "max_wert": "86400",
                "ist_erforderlich": True,
                "ist_sichtbar": True,
                "neustart_erforderlich": True
            },
            {
                "key": "security.password_min_length",
                "kategorie": "security",
                "wert": "6",
                "datentyp": "int",
                "bezeichnung": "Mindest-Passwort-Länge",
                "beschreibung": "Minimale Anzahl Zeichen für Benutzerpasswörter",
                "hilfe_text": "Stärkere Passwörter erhöhen die Sicherheit",
                "min_wert": "4",
                "max_wert": "50",
                "ist_erforderlich": True,
                "ist_sichtbar": True
            },
            # Notification settings
            {
                "key": "notifications.low_stock_enabled",
                "kategorie": "notifications",
                "wert": "true",
                "datentyp": "boolean",
                "bezeichnung": "Niedrigbestand-Benachrichtigungen",
                "beschreibung": "Aktiviert Warnungen bei niedrigen Beständen",
                "hilfe_text": "Zeigt Warnungen auf dem Dashboard an",
                "ist_erforderlich": True,
                "ist_sichtbar": True
            },
            {
                "key": "notifications.critical_stock_enabled",
                "kategorie": "notifications",
                "wert": "true",
                "datentyp": "boolean",
                "bezeichnung": "Kritische Bestand-Benachrichtigungen",
                "beschreibung": "Aktiviert Warnungen bei kritischen Beständen (leer)",
                "hilfe_text": "Zeigt kritische Warnungen auf dem Dashboard an",
                "ist_erforderlich": True,
                "ist_sichtbar": True
            }
        ]

        # Check if settings already exist
        existing_keys = {s.key for s in db_session.query(cls).all()}

        for setting_data in default_settings:
            if setting_data["key"] not in existing_keys:
                setting = cls(**setting_data)
                db_session.add(setting)

        db_session.commit()


class SettingsManager:
    """Helper class for managing system settings"""

    def __init__(self, db_session):
        self.db = db_session
        self._cache = {}
        self._load_cache()

    def _load_cache(self):
        """Load all settings into cache"""
        settings = self.db.query(SystemSettings).all()
        self._cache = {setting.key: setting.parsed_value for setting in settings}

    def get(self, key: str, default=None):
        """Get setting value with caching"""
        if key not in self._cache:
            setting = self.db.query(SystemSettings).filter(SystemSettings.key == key).first()
            if setting:
                self._cache[key] = setting.parsed_value
                return setting.parsed_value
            return default
        return self._cache[key]

    def set(self, key: str, value, benutzer_id: int = None):
        """Set setting value and update cache"""
        setting = self.db.query(SystemSettings).filter(SystemSettings.key == key).first()
        if setting:
            if setting.validate_value(value):
                setting.set_value(value)
                self.db.commit()
                self._cache[key] = setting.parsed_value
                return True
        return False

    def get_by_category(self, kategorie: str):
        """Get all settings for a category"""
        return self.db.query(SystemSettings).filter(
            SystemSettings.kategorie == kategorie,
            SystemSettings.ist_sichtbar == True
        ).all()

    def reload_cache(self):
        """Reload cache from database"""
        self._load_cache()