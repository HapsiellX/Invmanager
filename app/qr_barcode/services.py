"""
QR Code and Barcode generation services for inventory items
"""

import io
import base64
from typing import Dict, Any, Optional, Union, List
from sqlalchemy.orm import Session
import json
from datetime import datetime

# QR Code generation
try:
    import qrcode
    QR_AVAILABLE = True

    # Try to import advanced styling features, but don't fail if they're not available
    try:
        from qrcode.image.styledpil import StyledPilImage
        from qrcode.image.styles.moduledrawers import RoundedModuleDrawer, SquareModuleDrawer
        from qrcode.image.styles.colorfills import SolidFillColorMask
        QR_ADVANCED_STYLING = True
    except ImportError:
        QR_ADVANCED_STYLING = False

except ImportError:
    QR_AVAILABLE = False
    QR_ADVANCED_STYLING = False

# Barcode generation
try:
    from barcode import Code128, Code39, EAN13, UPCA
    from barcode.writer import ImageWriter
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False

# PIL for image manipulation
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from database.models.hardware import HardwareItem
from database.models.cable import Cable
from database.models.location import Location
from core.database import get_db


class QRBarcodeService:
    """Service for generating QR codes and barcodes for inventory items"""

    def __init__(self, db: Session):
        self.db = db

    def generate_qr_code(
        self,
        data: Union[str, Dict[str, Any]],
        size: int = 10,
        border: int = 4,
        error_correction: str = "M",
        style: str = "square",
        color: str = "#000000",
        background: str = "#FFFFFF"
    ) -> Optional[str]:
        """Generate QR code and return as base64 string"""

        if not QR_AVAILABLE:
            return None

        # Convert data to string if it's a dict
        if isinstance(data, dict):
            data_string = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        else:
            data_string = str(data)

        # Error correction level
        error_levels = {
            "L": qrcode.constants.ERROR_CORRECT_L,
            "M": qrcode.constants.ERROR_CORRECT_M,
            "Q": qrcode.constants.ERROR_CORRECT_Q,
            "H": qrcode.constants.ERROR_CORRECT_H
        }

        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=error_levels.get(error_correction, qrcode.constants.ERROR_CORRECT_M),
                box_size=size,
                border=border
            )

            qr.add_data(data_string)
            qr.make(fit=True)

            # Choose drawing style
            if style == "rounded":
                module_drawer = RoundedModuleDrawer()
            else:
                module_drawer = SquareModuleDrawer()

            # Create QR code image with style
            if style != "simple":
                img = qr.make_image(
                    image_factory=StyledPilImage,
                    module_drawer=module_drawer,
                    fill_color=color,
                    back_color=background
                )
            else:
                img = qr.make_image(fill_color=color, back_color=background)

            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()

            return img_str

        except Exception as e:
            print(f"Error generating QR code: {e}")
            return None

    def generate_barcode(
        self,
        data: str,
        barcode_type: str = "code128",
        width: float = 0.2,
        height: float = 15.0,
        text_distance: float = 5.0,
        font_size: int = 10
    ) -> Optional[str]:
        """Generate barcode and return as base64 string"""

        if not BARCODE_AVAILABLE or not PIL_AVAILABLE:
            return None

        try:
            # Choose barcode type
            barcode_classes = {
                "code128": Code128,
                "code39": Code39,
                "ean13": EAN13,
                "upca": UPCA
            }

            barcode_class = barcode_classes.get(barcode_type.lower(), Code128)

            # Create barcode with image writer
            writer = ImageWriter()
            writer.module_width = width
            writer.module_height = height
            writer.text_distance = text_distance
            writer.font_size = font_size

            # Generate barcode
            code = barcode_class(data, writer=writer)

            # Save to buffer
            buffer = io.BytesIO()
            code.write(buffer)

            # Convert to base64
            img_str = base64.b64encode(buffer.getvalue()).decode()

            return img_str

        except Exception as e:
            print(f"Error generating barcode: {e}")
            return None

    def generate_inventory_qr(
        self,
        item_type: str,
        item_id: int,
        include_data: List[str] = None,
        format_type: str = "url"
    ) -> Optional[Dict[str, Any]]:
        """Generate QR code for inventory item with specific data"""

        if include_data is None:
            include_data = ["basic", "location"]

        # Get item data
        item_data = self._get_item_data(item_type, item_id, include_data)
        if not item_data:
            return None

        if format_type == "url":
            # Generate URL that links to item detail page
            base_url = "https://inventory.local"  # Would be configurable
            qr_data = f"{base_url}/{item_type}/{item_id}"
        elif format_type == "json":
            # Generate JSON with item data
            qr_data = item_data
        else:
            # Simple string format
            qr_data = f"{item_type.upper()}-{item_id}: {item_data.get('name', 'Unknown')}"

        # Generate QR code
        qr_image = self.generate_qr_code(qr_data)

        if qr_image:
            return {
                "qr_code": qr_image,
                "data": qr_data,
                "item_data": item_data,
                "format": format_type,
                "generated_at": datetime.now().isoformat()
            }

        return None

    def generate_inventory_barcode(
        self,
        item_type: str,
        item_id: int,
        barcode_format: str = "auto"
    ) -> Optional[Dict[str, Any]]:
        """Generate barcode for inventory item"""

        # Get item data
        item_data = self._get_item_data(item_type, item_id, ["basic"])
        if not item_data:
            return None

        # Generate barcode data
        if barcode_format == "auto":
            # Use item ID padded to appropriate length
            if item_type == "hardware":
                barcode_data = f"HW{item_id:06d}"
            elif item_type == "cable":
                barcode_data = f"CB{item_id:06d}"
            elif item_type == "location":
                barcode_data = f"LOC{item_id:05d}"
            else:
                barcode_data = f"{item_id:08d}"
        else:
            # Use serial number or article number if available
            serial = item_data.get('seriennummer') or item_data.get('artikel_nummer')
            if serial and len(serial) >= 8:
                barcode_data = serial
            else:
                barcode_data = f"{item_id:08d}"

        # Generate barcode
        barcode_type = "code128"  # Most versatile
        barcode_image = self.generate_barcode(barcode_data, barcode_type)

        if barcode_image:
            return {
                "barcode": barcode_image,
                "barcode_data": barcode_data,
                "barcode_type": barcode_type,
                "item_data": item_data,
                "generated_at": datetime.now().isoformat()
            }

        return None

    def generate_location_label(
        self,
        location_id: int,
        include_qr: bool = True,
        include_barcode: bool = True,
        label_size: str = "medium"
    ) -> Optional[Dict[str, Any]]:
        """Generate complete label for location with QR code and/or barcode"""

        if not PIL_AVAILABLE:
            return None

        location = self.db.query(Location).filter(Location.id == location_id).first()
        if not location:
            return None

        # Label dimensions
        label_sizes = {
            "small": (300, 150),
            "medium": (400, 200),
            "large": (500, 250)
        }

        width, height = label_sizes.get(label_size, label_sizes["medium"])

        try:
            # Create label image
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)

            # Try to use a nice font, fall back to default
            try:
                title_font = ImageFont.truetype("arial.ttf", 16)
                text_font = ImageFont.truetype("arial.ttf", 12)
                small_font = ImageFont.truetype("arial.ttf", 10)
            except:
                title_font = ImageFont.load_default()
                text_font = ImageFont.load_default()
                small_font = ImageFont.load_default()

            # Draw location information
            y_offset = 10

            # Title
            draw.text((10, y_offset), location.name, fill='black', font=title_font)
            y_offset += 25

            # Type and path
            draw.text((10, y_offset), f"Typ: {location.typ}", fill='black', font=text_font)
            y_offset += 15

            if location.vollstaendiger_pfad:
                path_text = location.vollstaendiger_pfad
                if len(path_text) > 40:
                    path_text = path_text[:37] + "..."
                draw.text((10, y_offset), f"Pfad: {path_text}", fill='black', font=small_font)
                y_offset += 15

            # Address if available
            if location.adresse:
                address_text = location.adresse
                if len(address_text) > 40:
                    address_text = address_text[:37] + "..."
                draw.text((10, y_offset), address_text, fill='black', font=small_font)

            # Add QR code
            if include_qr:
                qr_data = self.generate_location_qr(location_id)
                if qr_data and qr_data.get("qr_code"):
                    qr_img_data = base64.b64decode(qr_data["qr_code"])
                    qr_img = Image.open(io.BytesIO(qr_img_data))
                    qr_img = qr_img.resize((80, 80))
                    img.paste(qr_img, (width - 90, 10))

            # Add barcode
            if include_barcode:
                barcode_data = self.generate_inventory_barcode("location", location_id)
                if barcode_data and barcode_data.get("barcode"):
                    barcode_img_data = base64.b64decode(barcode_data["barcode"])
                    barcode_img = Image.open(io.BytesIO(barcode_img_data))
                    barcode_img = barcode_img.resize((120, 30))
                    img.paste(barcode_img, (width - 130, height - 40))

            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            label_img_str = base64.b64encode(buffer.getvalue()).decode()

            return {
                "label_image": label_img_str,
                "location_data": location.to_dict(),
                "size": label_size,
                "dimensions": f"{width}x{height}",
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            print(f"Error generating location label: {e}")
            return None

    def generate_location_qr(self, location_id: int) -> Optional[Dict[str, Any]]:
        """Generate QR code specifically for location"""
        return self.generate_inventory_qr("location", location_id, ["basic", "path", "contact"])

    def _get_item_data(self, item_type: str, item_id: int, include_data: List[str]) -> Optional[Dict[str, Any]]:
        """Get item data based on type and included fields"""

        try:
            if item_type == "hardware":
                item = self.db.query(HardwareItem).filter(HardwareItem.id == item_id).first()
                if not item:
                    return None

                data = {
                    "id": item.id,
                    "type": "hardware",
                    "name": item.name
                }

                if "basic" in include_data:
                    data.update({
                        "kategorie": item.kategorie,
                        "hersteller": item.hersteller,
                        "modell": item.modell,
                        "seriennummer": item.seriennummer,
                        "status": item.status
                    })

                if "location" in include_data and item.standort:
                    data.update({
                        "standort_id": item.standort_id,
                        "standort_name": item.standort.name,
                        "lagerort": item.lagerort
                    })

                if "technical" in include_data:
                    data.update({
                        "mac_adresse": item.mac_adresse,
                        "ip_adresse": item.ip_adresse
                    })

                if "purchase" in include_data:
                    data.update({
                        "einkaufspreis": float(item.einkaufspreis) if item.einkaufspreis else None,
                        "einkaufsdatum": item.einkaufsdatum.isoformat() if item.einkaufsdatum else None,
                        "lieferant": item.lieferant
                    })

                return data

            elif item_type == "cable":
                item = self.db.query(Cable).filter(Cable.id == item_id).first()
                if not item:
                    return None

                data = {
                    "id": item.id,
                    "type": "cable",
                    "name": f"{item.typ} {item.standard}"
                }

                if "basic" in include_data:
                    data.update({
                        "typ": item.typ,
                        "standard": item.standard,
                        "laenge": float(item.laenge),
                        "farbe": item.farbe,
                        "stecker_typ_a": item.stecker_typ_a,
                        "stecker_typ_b": item.stecker_typ_b
                    })

                if "location" in include_data and item.standort:
                    data.update({
                        "standort_id": item.standort_id,
                        "standort_name": item.standort.name,
                        "lagerort": item.lagerort
                    })

                if "inventory" in include_data:
                    data.update({
                        "menge": item.menge,
                        "mindestbestand": item.mindestbestand,
                        "hoechstbestand": item.hoechstbestand
                    })

                if "purchase" in include_data:
                    data.update({
                        "einkaufspreis_pro_einheit": float(item.einkaufspreis_pro_einheit) if item.einkaufspreis_pro_einheit else None,
                        "lieferant": item.lieferant,
                        "artikel_nummer": item.artikel_nummer
                    })

                return data

            elif item_type == "location":
                item = self.db.query(Location).filter(Location.id == item_id).first()
                if not item:
                    return None

                data = {
                    "id": item.id,
                    "type": "location",
                    "name": item.name
                }

                if "basic" in include_data:
                    data.update({
                        "typ": item.typ,
                        "beschreibung": item.beschreibung
                    })

                if "path" in include_data:
                    data.update({
                        "vollstaendiger_pfad": item.vollstaendiger_pfad,
                        "parent_id": item.parent_id
                    })

                if "contact" in include_data:
                    data.update({
                        "adresse": item.adresse,
                        "stadt": item.stadt,
                        "postleitzahl": item.postleitzahl,
                        "kontakt_person": item.kontakt_person,
                        "telefon": item.telefon,
                        "email": item.email
                    })

                return data

            return None

        except Exception as e:
            print(f"Error getting item data: {e}")
            return None

    def get_scan_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get history of scanned codes (would be stored in database)"""
        # Placeholder - would implement scan tracking in production
        return []

    def validate_qr_data(self, qr_data: str) -> Dict[str, Any]:
        """Validate and parse QR code data"""
        result = {
            "valid": False,
            "type": "unknown",
            "data": None,
            "item_id": None
        }

        try:
            # Try to parse as JSON
            parsed_data = json.loads(qr_data)
            if isinstance(parsed_data, dict) and "type" in parsed_data and "id" in parsed_data:
                result.update({
                    "valid": True,
                    "type": parsed_data["type"],
                    "data": parsed_data,
                    "item_id": parsed_data["id"]
                })
                return result
        except json.JSONDecodeError:
            pass

        # Try to parse as URL
        if qr_data.startswith("http"):
            # Extract item type and ID from URL
            # Example: https://inventory.local/hardware/123
            try:
                parts = qr_data.split("/")
                if len(parts) >= 2:
                    item_type = parts[-2]
                    item_id = int(parts[-1])
                    if item_type in ["hardware", "cable", "location"]:
                        result.update({
                            "valid": True,
                            "type": item_type,
                            "item_id": item_id,
                            "data": {"url": qr_data}
                        })
                        return result
            except (ValueError, IndexError):
                pass

        # Try to parse as simple format
        # Example: HARDWARE-123: Server HP ProLiant
        if ":" in qr_data and "-" in qr_data:
            try:
                parts = qr_data.split(":")
                id_part = parts[0].strip()
                if "-" in id_part:
                    type_part, id_str = id_part.split("-", 1)
                    item_type = type_part.lower()
                    item_id = int(id_str)
                    if item_type in ["hardware", "cable", "location"]:
                        result.update({
                            "valid": True,
                            "type": item_type,
                            "item_id": item_id,
                            "data": {"raw": qr_data}
                        })
                        return result
            except (ValueError, IndexError):
                pass

        return result


def get_qr_barcode_service(db: Session = None) -> QRBarcodeService:
    """Dependency injection for QR/Barcode service"""
    if db is None:
        db = next(get_db())
    return QRBarcodeService(db)