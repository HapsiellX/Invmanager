"""
Bulk operations services for efficient inventory management
"""

import io
import csv
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
import streamlit as st

# Excel/CSV handling
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from core.db_utils import get_db_connection
from audit.services import get_audit_service
from core.security import SessionManager


class BulkOperationsService:
    """Service for handling bulk operations on inventory items"""

    def __init__(self):
        self.audit_service = get_audit_service()

    def get_dependencies_status(self) -> Dict[str, bool]:
        """Check if required dependencies are available"""
        return {
            "pandas": PANDAS_AVAILABLE
        }

    def get_missing_dependencies(self) -> List[str]:
        """Get list of missing dependencies"""
        status = self.get_dependencies_status()
        missing = []
        if not status["pandas"]:
            missing.append("pandas")
        return missing

    def validate_bulk_data(self, data: List[Dict], operation_type: str, item_type: str) -> Tuple[List[Dict], List[str]]:
        """Validate bulk data before processing"""
        valid_items = []
        errors = []
        
        required_fields = self._get_required_fields(operation_type, item_type)
        
        for idx, item in enumerate(data):
            item_errors = []
            
            # Check required fields
            for field in required_fields:
                if field not in item or not item[field]:
                    item_errors.append(f"Zeile {idx+1}: Fehlendes Feld '{field}'")
            
            # Validate data types and formats
            validation_errors = self._validate_item_data(item, item_type, idx+1)
            item_errors.extend(validation_errors)
            
            if not item_errors:
                valid_items.append(item)
            else:
                errors.extend(item_errors)
        
        return valid_items, errors

    def _get_required_fields(self, operation_type: str, item_type: str) -> List[str]:
        """Get required fields for specific operation and item type"""
        if operation_type == "create":
            if item_type == "hardware":
                return ["seriennummer", "hersteller", "modell", "kategorie"]
            elif item_type == "cables":
                return ["seriennummer", "typ", "kategorie", "laenge"]
        elif operation_type == "update":
            return ["seriennummer"]  # Serial number is required to identify items
        elif operation_type == "delete":
            return ["seriennummer"]
        
        return []

    def _validate_item_data(self, item: Dict, item_type: str, row_num: int) -> List[str]:
        """Validate individual item data"""
        errors = []
        
        # Validate serial number format
        if "seriennummer" in item and item["seriennummer"]:
            serial = str(item["seriennummer"]).strip()
            if len(serial) < 3:
                errors.append(f"Zeile {row_num}: Seriennummer zu kurz (mindestens 3 Zeichen)")
        
        # Validate price if present
        if "preis" in item and item["preis"]:
            try:
                price = float(item["preis"])
                if price < 0:
                    errors.append(f"Zeile {row_num}: Preis kann nicht negativ sein")
            except (ValueError, TypeError):
                errors.append(f"Zeile {row_num}: Ungültiger Preis '{item['preis']}'")
        
        # Validate length for cables
        if item_type == "cables" and "laenge" in item and item["laenge"]:
            try:
                length = float(item["laenge"])
                if length <= 0:
                    errors.append(f"Zeile {row_num}: Kabel Länge muss positiv sein")
            except (ValueError, TypeError):
                errors.append(f"Zeile {row_num}: Ungültige Länge '{item['laenge']}'")
        
        # Validate status
        if "status" in item and item["status"]:
            valid_statuses = ["aktiv", "inaktiv", "defekt", "wartung", "ausgemustert"]
            if item["status"].lower() not in valid_statuses:
                errors.append(f"Zeile {row_num}: Ungültiger Status '{item['status']}' (erlaubt: {', '.join(valid_statuses)})")
        
        # Validate dates
        date_fields = ["anschaffungsdatum", "garantie_ende"]
        for field in date_fields:
            if field in item and item[field]:
                if not self._validate_date_format(item[field]):
                    errors.append(f"Zeile {row_num}: Ungültiges Datumsformat für '{field}' (erwartet: YYYY-MM-DD)")
        
        return errors

    def _validate_date_format(self, date_str: str) -> bool:
        """Validate date format (YYYY-MM-DD)"""
        try:
            datetime.strptime(str(date_str), "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def bulk_create_hardware(self, items: List[Dict]) -> Dict[str, Any]:
        """Bulk create hardware items"""
        try:
            results = {
                "success_count": 0,
                "error_count": 0,
                "errors": [],
                "created_items": []
            }
            
            with get_db_connection() as conn:
                for item in items:
                    try:
                        # Check if serial number already exists
                        existing = conn.execute(
                            "SELECT id FROM hardware_inventar WHERE seriennummer = ?",
                            (item["seriennummer"],)
                        ).fetchone()
                        
                        if existing:
                            results["errors"].append(f"Hardware mit Seriennummer '{item['seriennummer']}' existiert bereits")
                            results["error_count"] += 1
                            continue
                        
                        # Prepare data with defaults
                        data = {
                            "seriennummer": item["seriennummer"],
                            "hersteller": item.get("hersteller", ""),
                            "modell": item.get("modell", ""),
                            "kategorie": item.get("kategorie", ""),
                            "preis": item.get("preis"),
                            "anschaffungsdatum": item.get("anschaffungsdatum"),
                            "garantie_ende": item.get("garantie_ende"),
                            "status": item.get("status", "aktiv"),
                            "standort_id": self._get_location_id(item.get("standort")),
                            "notizen": item.get("notizen", ""),
                            "erstellt_am": datetime.now().isoformat(),
                            "aktualisiert_am": datetime.now().isoformat()
                        }
                        
                        # Insert item
                        cursor = conn.execute("""
                            INSERT INTO hardware_inventar (
                                seriennummer, hersteller, modell, kategorie, preis,
                                anschaffungsdatum, garantie_ende, status, standort_id,
                                notizen, erstellt_am, aktualisiert_am
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            data["seriennummer"], data["hersteller"], data["modell"],
                            data["kategorie"], data["preis"], data["anschaffungsdatum"],
                            data["garantie_ende"], data["status"], data["standort_id"],
                            data["notizen"], data["erstellt_am"], data["aktualisiert_am"]
                        ))
                        
                        item_id = cursor.lastrowid
                        
                        # Log audit trail
                        self.audit_service.log_action(
                            action="bulk_create_hardware",
                            table_name="hardware_inventar",
                            record_id=item_id,
                            details=f"Bulk-Erstellung: {data['seriennummer']}"
                        )
                        
                        results["created_items"].append({
                            "id": item_id,
                            "seriennummer": data["seriennummer"]
                        })
                        results["success_count"] += 1
                        
                    except Exception as e:
                        results["errors"].append(f"Fehler bei Hardware '{item.get('seriennummer', 'Unbekannt')}': {str(e)}")
                        results["error_count"] += 1
                
                conn.commit()
            
            return results
            
        except Exception as e:
            st.error(f"Fehler beim Bulk-Erstellen von Hardware: {e}")
            return {
                "success_count": 0,
                "error_count": len(items),
                "errors": [f"Allgemeiner Fehler: {str(e)}"],
                "created_items": []
            }

    def bulk_create_cables(self, items: List[Dict]) -> Dict[str, Any]:
        """Bulk create cable items"""
        try:
            results = {
                "success_count": 0,
                "error_count": 0,
                "errors": [],
                "created_items": []
            }
            
            with get_db_connection() as conn:
                for item in items:
                    try:
                        # Check if serial number already exists
                        existing = conn.execute(
                            "SELECT id FROM kabel_inventar WHERE seriennummer = ?",
                            (item["seriennummer"],)
                        ).fetchone()
                        
                        if existing:
                            results["errors"].append(f"Kabel mit Seriennummer '{item['seriennummer']}' existiert bereits")
                            results["error_count"] += 1
                            continue
                        
                        # Prepare data with defaults
                        data = {
                            "seriennummer": item["seriennummer"],
                            "typ": item.get("typ", ""),
                            "kategorie": item.get("kategorie", ""),
                            "laenge": item.get("laenge"),
                            "farbe": item.get("farbe", ""),
                            "anschaffungsdatum": item.get("anschaffungsdatum"),
                            "status": item.get("status", "aktiv"),
                            "standort_id": self._get_location_id(item.get("standort")),
                            "notizen": item.get("notizen", ""),
                            "erstellt_am": datetime.now().isoformat(),
                            "aktualisiert_am": datetime.now().isoformat()
                        }
                        
                        # Insert item
                        cursor = conn.execute("""
                            INSERT INTO kabel_inventar (
                                seriennummer, typ, kategorie, laenge, farbe,
                                anschaffungsdatum, status, standort_id,
                                notizen, erstellt_am, aktualisiert_am
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            data["seriennummer"], data["typ"], data["kategorie"],
                            data["laenge"], data["farbe"], data["anschaffungsdatum"],
                            data["status"], data["standort_id"], data["notizen"],
                            data["erstellt_am"], data["aktualisiert_am"]
                        ))
                        
                        item_id = cursor.lastrowid
                        
                        # Log audit trail
                        self.audit_service.log_action(
                            action="bulk_create_cable",
                            table_name="kabel_inventar",
                            record_id=item_id,
                            details=f"Bulk-Erstellung: {data['seriennummer']}"
                        )
                        
                        results["created_items"].append({
                            "id": item_id,
                            "seriennummer": data["seriennummer"]
                        })
                        results["success_count"] += 1
                        
                    except Exception as e:
                        results["errors"].append(f"Fehler bei Kabel '{item.get('seriennummer', 'Unbekannt')}': {str(e)}")
                        results["error_count"] += 1
                
                conn.commit()
            
            return results
            
        except Exception as e:
            st.error(f"Fehler beim Bulk-Erstellen von Kabeln: {e}")
            return {
                "success_count": 0,
                "error_count": len(items),
                "errors": [f"Allgemeiner Fehler: {str(e)}"],
                "created_items": []
            }

    def bulk_update_items(self, items: List[Dict], item_type: str) -> Dict[str, Any]:
        """Bulk update items (hardware or cables)"""
        try:
            results = {
                "success_count": 0,
                "error_count": 0,
                "errors": [],
                "updated_items": []
            }
            
            table_name = "hardware_inventar" if item_type == "hardware" else "kabel_inventar"
            
            with get_db_connection() as conn:
                for item in items:
                    try:
                        # Find existing item by serial number
                        existing = conn.execute(
                            f"SELECT id FROM {table_name} WHERE seriennummer = ?",
                            (item["seriennummer"],)
                        ).fetchone()
                        
                        if not existing:
                            results["errors"].append(f"Item mit Seriennummer '{item['seriennummer']}' nicht gefunden")
                            results["error_count"] += 1
                            continue
                        
                        item_id = existing[0]
                        
                        # Build update query dynamically based on provided fields
                        update_fields = []
                        update_values = []
                        
                        updatable_fields = self._get_updatable_fields(item_type)
                        
                        for field in updatable_fields:
                            if field in item and item[field] is not None:
                                update_fields.append(f"{field} = ?")
                                update_values.append(item[field])
                        
                        if not update_fields:
                            results["errors"].append(f"Keine aktualisierbaren Felder für '{item['seriennummer']}'")
                            results["error_count"] += 1
                            continue
                        
                        # Always update timestamp
                        update_fields.append("aktualisiert_am = ?")
                        update_values.append(datetime.now().isoformat())
                        update_values.append(item_id)
                        
                        # Execute update
                        conn.execute(
                            f"UPDATE {table_name} SET {', '.join(update_fields)} WHERE id = ?",
                            update_values
                        )
                        
                        # Log audit trail
                        self.audit_service.log_action(
                            action=f"bulk_update_{item_type}",
                            table_name=table_name,
                            record_id=item_id,
                            details=f"Bulk-Update: {item['seriennummer']}"
                        )
                        
                        results["updated_items"].append({
                            "id": item_id,
                            "seriennummer": item["seriennummer"]
                        })
                        results["success_count"] += 1
                        
                    except Exception as e:
                        results["errors"].append(f"Fehler bei '{item.get('seriennummer', 'Unbekannt')}': {str(e)}")
                        results["error_count"] += 1
                
                conn.commit()
            
            return results
            
        except Exception as e:
            st.error(f"Fehler beim Bulk-Update: {e}")
            return {
                "success_count": 0,
                "error_count": len(items),
                "errors": [f"Allgemeiner Fehler: {str(e)}"],
                "updated_items": []
            }

    def bulk_delete_items(self, serial_numbers: List[str], item_type: str) -> Dict[str, Any]:
        """Bulk delete items by serial numbers"""
        try:
            results = {
                "success_count": 0,
                "error_count": 0,
                "errors": [],
                "deleted_items": []
            }
            
            table_name = "hardware_inventar" if item_type == "hardware" else "kabel_inventar"
            
            with get_db_connection() as conn:
                for serial in serial_numbers:
                    try:
                        # Find existing item
                        existing = conn.execute(
                            f"SELECT id FROM {table_name} WHERE seriennummer = ?",
                            (serial,)
                        ).fetchone()
                        
                        if not existing:
                            results["errors"].append(f"Item mit Seriennummer '{serial}' nicht gefunden")
                            results["error_count"] += 1
                            continue
                        
                        item_id = existing[0]
                        
                        # Delete item
                        conn.execute(f"DELETE FROM {table_name} WHERE id = ?", (item_id,))
                        
                        # Log audit trail
                        self.audit_service.log_action(
                            action=f"bulk_delete_{item_type}",
                            table_name=table_name,
                            record_id=item_id,
                            details=f"Bulk-Löschung: {serial}"
                        )
                        
                        results["deleted_items"].append({
                            "id": item_id,
                            "seriennummer": serial
                        })
                        results["success_count"] += 1
                        
                    except Exception as e:
                        results["errors"].append(f"Fehler beim Löschen von '{serial}': {str(e)}")
                        results["error_count"] += 1
                
                conn.commit()
            
            return results
            
        except Exception as e:
            st.error(f"Fehler beim Bulk-Löschen: {e}")
            return {
                "success_count": 0,
                "error_count": len(serial_numbers),
                "errors": [f"Allgemeiner Fehler: {str(e)}"],
                "deleted_items": []
            }

    def _get_updatable_fields(self, item_type: str) -> List[str]:
        """Get list of fields that can be updated for each item type"""
        if item_type == "hardware":
            return [
                "hersteller", "modell", "kategorie", "preis",
                "anschaffungsdatum", "garantie_ende", "status",
                "standort_id", "notizen"
            ]
        elif item_type == "cables":
            return [
                "typ", "kategorie", "laenge", "farbe",
                "anschaffungsdatum", "status", "standort_id", "notizen"
            ]
        return []

    def _get_location_id(self, location_name: Optional[str]) -> Optional[int]:
        """Get location ID by name, or None if not found/provided"""
        if not location_name:
            return None
        
        try:
            with get_db_connection() as conn:
                result = conn.execute(
                    "SELECT id FROM standorte WHERE name = ?",
                    (location_name,)
                ).fetchone()
                return result[0] if result else None
        except Exception:
            return None

    def export_template(self, item_type: str, operation_type: str) -> io.BytesIO:
        """Generate CSV template for bulk operations"""
        if not PANDAS_AVAILABLE:
            raise ImportError("Pandas ist nicht installiert")
        
        # Define template columns based on operation and item type
        if operation_type == "create":
            if item_type == "hardware":
                columns = [
                    "seriennummer", "hersteller", "modell", "kategorie",
                    "preis", "anschaffungsdatum", "garantie_ende", "status",
                    "standort", "notizen"
                ]
                sample_data = {
                    "seriennummer": "HW001",
                    "hersteller": "Dell",
                    "modell": "OptiPlex 7090",
                    "kategorie": "Desktop PC",
                    "preis": "899.99",
                    "anschaffungsdatum": "2024-01-15",
                    "garantie_ende": "2027-01-15",
                    "status": "aktiv",
                    "standort": "Büro A",
                    "notizen": "Beispiel Hardware"
                }
            else:  # cables
                columns = [
                    "seriennummer", "typ", "kategorie", "laenge",
                    "farbe", "anschaffungsdatum", "status",
                    "standort", "notizen"
                ]
                sample_data = {
                    "seriennummer": "CAB001",
                    "typ": "Ethernet",
                    "kategorie": "Cat6",
                    "laenge": "10.0",
                    "farbe": "blau",
                    "anschaffungsdatum": "2024-01-15",
                    "status": "aktiv",
                    "standort": "Serverraum",
                    "notizen": "Beispiel Kabel"
                }
        elif operation_type == "update":
            if item_type == "hardware":
                columns = [
                    "seriennummer", "hersteller", "modell", "kategorie",
                    "preis", "anschaffungsdatum", "garantie_ende", "status",
                    "standort", "notizen"
                ]
                sample_data = {
                    "seriennummer": "HW001",
                    "status": "wartung",
                    "notizen": "In Wartung seit 01.12.2024"
                }
            else:  # cables
                columns = [
                    "seriennummer", "typ", "kategorie", "laenge",
                    "farbe", "anschaffungsdatum", "status",
                    "standort", "notizen"
                ]
                sample_data = {
                    "seriennummer": "CAB001",
                    "status": "defekt",
                    "notizen": "Kabel beschädigt"
                }
        else:  # delete
            columns = ["seriennummer"]
            sample_data = {"seriennummer": "HW001"}
        
        # Create DataFrame with sample data
        import pandas as pd
        df = pd.DataFrame([sample_data])
        
        # Create CSV buffer
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False, encoding='utf-8-sig')
        buffer.seek(0)
        
        return buffer

    def parse_uploaded_file(self, uploaded_file) -> Tuple[List[Dict], List[str]]:
        """Parse uploaded CSV/Excel file and return data with any parsing errors"""
        if not PANDAS_AVAILABLE:
            raise ImportError("Pandas ist nicht installiert")
        
        errors = []
        data = []
        
        try:
            import pandas as pd
            
            # Determine file type and read
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            elif uploaded_file.name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(uploaded_file)
            else:
                errors.append("Unsupported file type. Please use CSV or Excel files.")
                return data, errors
            
            # Check if dataframe is empty
            if df.empty:
                errors.append("Uploaded file is empty.")
                return data, errors
            
            # Convert to list of dictionaries
            data = df.fillna('').to_dict('records')
            
            # Clean data - remove empty rows
            data = [row for row in data if any(str(v).strip() for v in row.values())]
            
            if not data:
                errors.append("No valid data rows found in file.")
            
        except Exception as e:
            errors.append(f"Error parsing file: {str(e)}")
        
        return data, errors


# Global service instance
_bulk_operations_service = None


def get_bulk_operations_service() -> BulkOperationsService:
    """Get global bulk operations service instance"""
    global _bulk_operations_service
    if _bulk_operations_service is None:
        _bulk_operations_service = BulkOperationsService()
    return _bulk_operations_service
