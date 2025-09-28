"""
QR Code and Barcode views for inventory management
"""

import streamlit as st
import base64
from io import BytesIO
from typing import Dict, Any, Optional

from core.security import require_auth, require_role
from core.database import get_db
from .services import get_qr_barcode_service, QR_AVAILABLE, BARCODE_AVAILABLE, PIL_AVAILABLE

# Import scanner module if available
try:
    from .scanner import show_camera_scanner, show_image_scanner, PYZBAR_AVAILABLE, WEBRTC_AVAILABLE
    SCANNER_AVAILABLE = True
except ImportError as e:
    print(f"Scanner import error: {e}")
    SCANNER_AVAILABLE = False
    PYZBAR_AVAILABLE = False
    WEBRTC_AVAILABLE = False

    # Create placeholder functions
    def show_camera_scanner(qr_service=None):
        st.error("❌ Kamera-Scanner nicht verfügbar - Abhängigkeiten fehlen")
        st.info("Führen Sie `pip install opencv-python pyzbar streamlit-webrtc av` aus")

    def show_image_scanner(qr_service=None):
        st.error("❌ Bild-Scanner nicht verfügbar - Abhängigkeiten fehlen")
        st.info("Führen Sie `pip install opencv-python pyzbar` aus")


@require_auth
def show_qr_barcode_page():
    """
    QR Code and Barcode generation page
    """
    st.header("📱 QR-Codes & Barcodes")

    # Check for required dependencies
    show_dependency_status()

    # Show warning but don't stop completely if some features are available
    if not (QR_AVAILABLE and BARCODE_AVAILABLE and PIL_AVAILABLE):
        missing_deps = []
        if not QR_AVAILABLE:
            missing_deps.append("qrcode[pil]")
        if not BARCODE_AVAILABLE:
            missing_deps.append("python-barcode[images]")
        if not PIL_AVAILABLE:
            missing_deps.append("Pillow")

        if missing_deps:
            st.warning(f"""
            ⚠️ **Einige Bibliotheken fehlen**: {', '.join(missing_deps)}

            Einige Funktionen sind möglicherweise eingeschränkt. Für volle Funktionalität führen Sie aus:
            ```bash
            pip install {' '.join(missing_deps)}
            ```
            """)

    # Only completely block if nothing is available
    if not (QR_AVAILABLE or BARCODE_AVAILABLE or PIL_AVAILABLE):
        st.error("Keine der erforderlichen Bibliotheken ist installiert. Bitte installieren Sie mindestens eine: qrcode[pil], python-barcode[images], oder Pillow.")
        st.info("Nutzen Sie das Debug Tool um detaillierte Informationen über fehlende Dependencies zu erhalten.")
        return

    # Get database session and service
    db = next(get_db())
    qr_service = get_qr_barcode_service(db)

    # Create tabs for different functions
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏷️ Inventar Labels", "📱 QR Generator", "📊 Barcode Generator", "🔍 Code Scanner"
    ])

    with tab1:
        show_inventory_labels_tab(qr_service)

    with tab2:
        show_qr_generator_tab(qr_service)

    with tab3:
        show_barcode_generator_tab(qr_service)

    with tab4:
        show_code_scanner_tab(qr_service)

    db.close()


def show_dependency_status():
    """Show status of required dependencies"""
    with st.expander("📋 Systemvoraussetzungen"):
        st.write("### Code Generation")
        col1, col2, col3 = st.columns(3)

        with col1:
            status = "✅ Installiert" if QR_AVAILABLE else "❌ Nicht installiert"
            st.write(f"**QR-Code:** {status}")
            if not QR_AVAILABLE:
                st.code("pip install qrcode[pil]")

        with col2:
            status = "✅ Installiert" if BARCODE_AVAILABLE else "❌ Nicht installiert"
            st.write(f"**Barcode:** {status}")
            if not BARCODE_AVAILABLE:
                st.code("pip install python-barcode[images]")

        with col3:
            status = "✅ Installiert" if PIL_AVAILABLE else "❌ Nicht installiert"
            st.write(f"**PIL/Pillow:** {status}")
            if not PIL_AVAILABLE:
                st.code("pip install Pillow")

        st.write("### Camera Scanning")
        col4, col5, col6 = st.columns(3)

        with col4:
            status = "✅ Installiert" if WEBRTC_AVAILABLE else "❌ Nicht installiert"
            st.write(f"**WebRTC:** {status}")
            if not WEBRTC_AVAILABLE:
                st.code("pip install streamlit-webrtc av")

        with col5:
            status = "✅ Installiert" if PYZBAR_AVAILABLE else "❌ Nicht installiert"
            st.write(f"**PyZBar:** {status}")
            if not PYZBAR_AVAILABLE:
                st.code("pip install pyzbar")

        with col6:
            try:
                import cv2
                CV2_AVAILABLE = True
            except ImportError:
                CV2_AVAILABLE = False

            status = "✅ Installiert" if CV2_AVAILABLE else "❌ Nicht installiert"
            st.write(f"**OpenCV:** {status}")
            if not CV2_AVAILABLE:
                st.code("pip install opencv-python")


def show_inventory_labels_tab(qr_service):
    """Show inventory label generation"""
    st.subheader("🏷️ Inventar Etiketten")

    st.info("Generieren Sie komplette Etiketten für Ihre Inventargegenstände mit QR-Codes und Barcodes.")

    # Item selection
    col1, col2 = st.columns(2)

    with col1:
        item_type = st.selectbox(
            "Inventar Typ:",
            ["hardware", "cable", "location"],
            format_func=lambda x: {"hardware": "Hardware", "cable": "Kabel", "location": "Standort"}[x],
            key="label_item_type"
        )

    with col2:
        # Get items of selected type
        items = get_items_by_type(qr_service.db, item_type)
        if items:
            item_options = {f"{item['name']} (ID: {item['id']})": item['id'] for item in items}
            selected_item = st.selectbox(
                "Item auswählen:",
                list(item_options.keys()),
                key="label_selected_item"
            )
            selected_item_id = item_options[selected_item]
        else:
            st.warning(f"Keine {item_type} Artikel gefunden")
            selected_item_id = None

    if selected_item_id:
        # Label options
        st.subheader("🎨 Etikett Optionen")

        col1, col2, col3 = st.columns(3)

        with col1:
            include_qr = st.checkbox("QR-Code einschließen", value=True, key="label_include_qr")
            include_barcode = st.checkbox("Barcode einschließen", value=True, key="label_include_barcode")

        with col2:
            if item_type == "location":
                label_size = st.selectbox(
                    "Etikett Größe:",
                    ["small", "medium", "large"],
                    format_func=lambda x: {"small": "Klein (300x150)", "medium": "Mittel (400x200)", "large": "Groß (500x250)"}[x],
                    index=1,
                    key="label_size"
                )
            else:
                label_size = "medium"

        with col3:
            qr_data_format = st.selectbox(
                "QR Datenformat:",
                ["url", "json", "simple"],
                format_func=lambda x: {"url": "URL", "json": "JSON Daten", "simple": "Einfacher Text"}[x],
                key="label_qr_format"
            )

        # Generate button
        if st.button("🏷️ Etikett generieren", type="primary", key="generate_label"):
            with st.spinner("Etikett wird generiert..."):
                if item_type == "location":
                    result = qr_service.generate_location_label(
                        selected_item_id,
                        include_qr=include_qr,
                        include_barcode=include_barcode,
                        label_size=label_size
                    )
                else:
                    # For hardware and cables, generate individual codes
                    result = generate_item_label(
                        qr_service, item_type, selected_item_id,
                        include_qr, include_barcode, qr_data_format
                    )

                if result:
                    display_generated_label(result, item_type)
                else:
                    st.error("Fehler beim Generieren des Etiketts")


def show_qr_generator_tab(qr_service):
    """Show QR code generator"""
    st.subheader("📱 QR-Code Generator")

    if not QR_AVAILABLE:
        st.error("❌ QR-Code Generation nicht verfügbar - qrcode Bibliothek fehlt")
        st.code("pip install qrcode[pil]")
        return

    # Generation mode
    mode = st.radio(
        "Generierungsmodus:",
        ["Inventar Item", "Benutzerdefinierten Text", "JSON Daten"],
        key="qr_mode"
    )

    if mode == "Inventar Item":
        # Item selection
        col1, col2 = st.columns(2)

        with col1:
            item_type = st.selectbox(
                "Item Typ:",
                ["hardware", "cable", "location"],
                format_func=lambda x: {"hardware": "Hardware", "cable": "Kabel", "location": "Standort"}[x],
                key="qr_item_type"
            )

        with col2:
            items = get_items_by_type(qr_service.db, item_type)
            if items:
                item_options = {f"{item['name']} (ID: {item['id']})": item['id'] for item in items}
                selected_item = st.selectbox(
                    "Item auswählen:",
                    list(item_options.keys()),
                    key="qr_selected_item"
                )
                selected_item_id = item_options[selected_item]
            else:
                st.warning(f"Keine {item_type} Artikel gefunden")
                selected_item_id = None

        # Data inclusion options
        if selected_item_id:
            st.subheader("📋 Einzuschließende Daten")
            include_basic = st.checkbox("Grunddaten", value=True, key="qr_include_basic")
            include_location = st.checkbox("Standort Info", value=True, key="qr_include_location")

            if item_type == "hardware":
                include_technical = st.checkbox("Technische Daten", key="qr_include_technical")
                include_purchase = st.checkbox("Einkaufsdaten", key="qr_include_purchase")
                include_data = ["basic"] if include_basic else []
                if include_location: include_data.append("location")
                if include_technical: include_data.append("technical")
                if include_purchase: include_data.append("purchase")
            elif item_type == "cable":
                include_inventory = st.checkbox("Bestandsdaten", key="qr_include_inventory")
                include_purchase = st.checkbox("Einkaufsdaten", key="qr_include_purchase")
                include_data = ["basic"] if include_basic else []
                if include_location: include_data.append("location")
                if include_inventory: include_data.append("inventory")
                if include_purchase: include_data.append("purchase")
            else:  # location
                include_contact = st.checkbox("Kontaktdaten", key="qr_include_contact")
                include_data = ["basic"] if include_basic else []
                if include_location: include_data.append("path")
                if include_contact: include_data.append("contact")

    elif mode == "Benutzerdefinierten Text":
        custom_text = st.text_area(
            "Text für QR-Code:",
            placeholder="Geben Sie den Text ein, der im QR-Code codiert werden soll...",
            key="qr_custom_text"
        )
        selected_item_id = None
        include_data = []

    else:  # JSON mode
        st.write("**JSON Daten eingeben:**")
        json_data = st.text_area(
            "JSON:",
            value='{\n  "name": "Beispiel Item",\n  "id": 123,\n  "type": "hardware"\n}',
            height=150,
            key="qr_json_data"
        )
        selected_item_id = None
        include_data = []

    # QR Code styling options
    st.subheader("🎨 QR-Code Stil")

    col1, col2, col3 = st.columns(3)

    with col1:
        qr_size = st.slider("Größe:", 5, 20, 10, key="qr_size")
        qr_border = st.slider("Rand:", 1, 10, 4, key="qr_border")

    with col2:
        error_correction = st.selectbox(
            "Fehlerkorrektur:",
            ["L", "M", "Q", "H"],
            index=1,
            format_func=lambda x: {
                "L": "Niedrig (~7%)",
                "M": "Mittel (~15%)",
                "Q": "Hoch (~25%)",
                "H": "Sehr hoch (~30%)"
            }[x],
            key="qr_error_correction"
        )

        qr_style = st.selectbox(
            "Stil:",
            ["square", "rounded", "simple"],
            format_func=lambda x: {"square": "Quadratisch", "rounded": "Abgerundet", "simple": "Einfach"}[x],
            key="qr_style"
        )

    with col3:
        qr_color = st.color_picker("Vordergrund:", "#000000", key="qr_color")
        qr_background = st.color_picker("Hintergrund:", "#FFFFFF", key="qr_background")

    # Generate button
    if st.button("📱 QR-Code generieren", type="primary", key="generate_qr"):
        with st.spinner("QR-Code wird generiert..."):
            if mode == "Inventar Item" and selected_item_id:
                result = qr_service.generate_inventory_qr(
                    item_type, selected_item_id, include_data, "json"
                )
                if result:
                    # Generate styled QR code
                    qr_image = qr_service.generate_qr_code(
                        result["data"],
                        size=qr_size,
                        border=qr_border,
                        error_correction=error_correction,
                        style=qr_style,
                        color=qr_color,
                        background=qr_background
                    )
                    if qr_image:
                        display_qr_code(qr_image, result)
                    else:
                        st.error("Fehler beim Generieren des QR-Codes")
                else:
                    st.error("Fehler beim Laden der Item-Daten")

            elif mode == "Benutzerdefinierten Text" and custom_text:
                qr_image = qr_service.generate_qr_code(
                    custom_text,
                    size=qr_size,
                    border=qr_border,
                    error_correction=error_correction,
                    style=qr_style,
                    color=qr_color,
                    background=qr_background
                )
                if qr_image:
                    display_qr_code(qr_image, {"data": custom_text, "format": "text"})
                else:
                    st.error("Fehler beim Generieren des QR-Codes")

            elif mode == "JSON Daten" and json_data:
                try:
                    import json
                    parsed_json = json.loads(json_data)
                    qr_image = qr_service.generate_qr_code(
                        parsed_json,
                        size=qr_size,
                        border=qr_border,
                        error_correction=error_correction,
                        style=qr_style,
                        color=qr_color,
                        background=qr_background
                    )
                    if qr_image:
                        display_qr_code(qr_image, {"data": parsed_json, "format": "json"})
                    else:
                        st.error("Fehler beim Generieren des QR-Codes")
                except json.JSONDecodeError:
                    st.error("Ungültige JSON-Daten")

            else:
                st.warning("Bitte wählen Sie ein Item aus oder geben Sie Text ein")


def show_barcode_generator_tab(qr_service):
    """Show barcode generator"""
    st.subheader("📊 Barcode Generator")

    if not BARCODE_AVAILABLE:
        st.error("Barcode-Generierung nicht verfügbar. Installieren Sie python-barcode[images]")
        return

    # Generation mode
    mode = st.radio(
        "Generierungsmodus:",
        ["Inventar Item", "Benutzerdefinierte Daten"],
        key="barcode_mode"
    )

    if mode == "Inventar Item":
        # Item selection
        col1, col2 = st.columns(2)

        with col1:
            item_type = st.selectbox(
                "Item Typ:",
                ["hardware", "cable", "location"],
                format_func=lambda x: {"hardware": "Hardware", "cable": "Kabel", "location": "Standort"}[x],
                key="barcode_item_type"
            )

        with col2:
            items = get_items_by_type(qr_service.db, item_type)
            if items:
                item_options = {f"{item['name']} (ID: {item['id']})": item['id'] for item in items}
                selected_item = st.selectbox(
                    "Item auswählen:",
                    list(item_options.keys()),
                    key="barcode_selected_item"
                )
                selected_item_id = item_options[selected_item]
            else:
                st.warning(f"Keine {item_type} Artikel gefunden")
                selected_item_id = None

        barcode_format = st.selectbox(
            "Barcode Format:",
            ["auto", "serial_number"],
            format_func=lambda x: {"auto": "Automatisch (ID-basiert)", "serial_number": "Seriennummer"}[x],
            key="barcode_format"
        )

    else:  # Custom data
        custom_data = st.text_input(
            "Barcode Daten:",
            placeholder="Geben Sie die Daten für den Barcode ein...",
            key="barcode_custom_data"
        )
        selected_item_id = None
        barcode_format = "auto"

    # Barcode styling options
    st.subheader("🎨 Barcode Stil")

    col1, col2 = st.columns(2)

    with col1:
        barcode_type = st.selectbox(
            "Barcode Typ:",
            ["code128", "code39", "ean13"],
            format_func=lambda x: {
                "code128": "Code 128 (Empfohlen)",
                "code39": "Code 39",
                "ean13": "EAN-13"
            }[x],
            key="barcode_type"
        )

        width = st.slider("Modulbreite:", 0.1, 1.0, 0.2, step=0.1, key="barcode_width")

    with col2:
        height = st.slider("Höhe:", 5.0, 30.0, 15.0, step=1.0, key="barcode_height")
        font_size = st.slider("Schriftgröße:", 8, 16, 10, key="barcode_font_size")

    # Generate button
    if st.button("📊 Barcode generieren", type="primary", key="generate_barcode"):
        with st.spinner("Barcode wird generiert..."):
            if mode == "Inventar Item" and selected_item_id:
                result = qr_service.generate_inventory_barcode(
                    item_type, selected_item_id, barcode_format
                )
                if result:
                    # Generate styled barcode
                    barcode_image = qr_service.generate_barcode(
                        result["barcode_data"],
                        barcode_type=barcode_type,
                        width=width,
                        height=height,
                        font_size=font_size
                    )
                    if barcode_image:
                        display_barcode(barcode_image, result)
                    else:
                        st.error("Fehler beim Generieren des Barcodes")
                else:
                    st.error("Fehler beim Laden der Item-Daten")

            elif mode == "Benutzerdefinierte Daten" and custom_data:
                barcode_image = qr_service.generate_barcode(
                    custom_data,
                    barcode_type=barcode_type,
                    width=width,
                    height=height,
                    font_size=font_size
                )
                if barcode_image:
                    display_barcode(barcode_image, {
                        "barcode_data": custom_data,
                        "barcode_type": barcode_type
                    })
                else:
                    st.error("Fehler beim Generieren des Barcodes")

            else:
                st.warning("Bitte wählen Sie ein Item aus oder geben Sie Daten ein")


def show_code_scanner_tab(qr_service):
    """Show enhanced code scanner functionality with camera support"""
    st.subheader("🔍 Code Scanner")

    st.info("Scannen Sie QR-Codes oder Barcodes mit Ihrer Kamera oder laden Sie ein Bild hoch.")

    # Scanner mode selection - always show all options
    scanner_mode = st.radio(
        "Scanner Modus:",
        ["📷 Kamera Scanner", "🖼️ Bild Upload", "✏️ Manuelle Eingabe"],
        key="scanner_mode"
    )

    if scanner_mode == "📷 Kamera Scanner":
        # Always call show_camera_scanner (will show error if not available)
        show_camera_scanner(qr_service)

    elif scanner_mode == "🖼️ Bild Upload":
        # Always call show_image_scanner (will show error if not available)
        show_image_scanner(qr_service)

    else:  # Manual input (always available)
        scanned_data = st.text_area(
            "Gescannte Daten eingeben:",
            placeholder="Fügen Sie hier die gescannten Daten ein...",
            key="scanner_manual_input"
        )

        if scanned_data and st.button("🔍 Daten verarbeiten", key="process_manual"):
            with st.spinner("Daten werden verarbeitet..."):
                validation_result = qr_service.validate_qr_data(scanned_data)

                if validation_result["valid"]:
                    st.success("✅ Gültige Daten erkannt!")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("**Erkannte Informationen:**")
                        st.write(f"**Typ:** {validation_result['type'].title()}")
                        st.write(f"**Item ID:** {validation_result['item_id']}")

                    with col2:
                        st.write("**Rohdaten:**")
                        st.json(validation_result["data"])

                    # Try to fetch item details
                    if validation_result["item_id"]:
                        item_data = qr_service._get_item_data(
                            validation_result["type"],
                            validation_result["item_id"],
                            ["basic", "location"]
                        )

                        if item_data:
                            st.subheader("📋 Item Details")
                            display_item_info(item_data)

                            # Quick actions
                            st.subheader("⚡ Schnellaktionen")
                            col1, col2, col3 = st.columns(3)

                            with col1:
                                if st.button("📝 Bearbeiten", key="quick_edit"):
                                    item_type = validation_result["type"]
                                    item_id = validation_result["item_id"]
                                    st.session_state.current_page = f"{item_type}s"
                                    st.session_state[f"edit_{item_type}_id"] = item_id
                                    st.rerun()

                            with col2:
                                if st.button("📊 Details", key="quick_details"):
                                    # Navigate to item details page
                                    pass

                            with col3:
                                if st.button("🏷️ Neues Label", key="quick_label"):
                                    # Generate new label for this item
                                    pass

                        else:
                            st.error("Item nicht in der Datenbank gefunden")

                else:
                    st.error("❌ Ungültige oder unerkannte Daten")
                    st.write("**Rohdaten:**")
                    st.code(scanned_data)

    # Scan history
    st.subheader("📜 Scan Verlauf")
    scan_history = qr_service.get_scan_history(limit=10)

    if scan_history:
        for entry in scan_history:
            st.write(f"**{entry['timestamp']}** - {entry['type']} ID: {entry['item_id']}")
    else:
        st.info("Kein Scan-Verlauf verfügbar")


def get_items_by_type(db, item_type: str):
    """Get items by type for selection"""
    if item_type == "hardware":
        from database.models.hardware import HardwareItem
        items = db.query(HardwareItem).filter(HardwareItem.ist_aktiv == True).limit(100).all()
        return [{"id": item.id, "name": item.name} for item in items]

    elif item_type == "cable":
        from database.models.cable import Cable
        items = db.query(Cable).filter(Cable.ist_aktiv == True).limit(100).all()
        return [{"id": item.id, "name": f"{item.typ} {item.standard} ({item.laenge}m)"} for item in items]

    elif item_type == "location":
        from database.models.location import Location
        items = db.query(Location).filter(Location.ist_aktiv == True).limit(100).all()
        return [{"id": item.id, "name": item.name} for item in items]

    return []


def generate_item_label(qr_service, item_type: str, item_id: int, include_qr: bool, include_barcode: bool, qr_format: str):
    """Generate a complete label for hardware/cable items"""
    # This would create a composite image with QR code, barcode, and item info
    # For now, we'll generate the codes separately
    result = {"codes": []}

    if include_qr:
        qr_data = qr_service.generate_inventory_qr(item_type, item_id, format_type=qr_format)
        if qr_data:
            result["codes"].append({"type": "qr", "data": qr_data})

    if include_barcode:
        barcode_data = qr_service.generate_inventory_barcode(item_type, item_id)
        if barcode_data:
            result["codes"].append({"type": "barcode", "data": barcode_data})

    return result if result["codes"] else None


def display_generated_label(result: Dict[str, Any], item_type: str):
    """Display generated label"""
    st.success("✅ Etikett erfolgreich generiert!")

    if "label_image" in result:
        # Complete label image
        img_data = base64.b64decode(result["label_image"])
        st.image(img_data, caption="Generiertes Etikett")

        # Download button
        st.download_button(
            "💾 Etikett herunterladen",
            data=img_data,
            file_name=f"{item_type}_label_{result['location_data']['id']}.png",
            mime="image/png"
        )

    elif "codes" in result:
        # Individual codes
        for code_info in result["codes"]:
            code_data = code_info["data"]
            if code_info["type"] == "qr":
                display_qr_code(code_data["qr_code"], code_data)
            elif code_info["type"] == "barcode":
                display_barcode(code_data["barcode"], code_data)


def display_qr_code(qr_image: str, result: Dict[str, Any]):
    """Display generated QR code"""
    st.success("✅ QR-Code erfolgreich generiert!")

    col1, col2 = st.columns([1, 1])

    with col1:
        # Display QR code
        img_data = base64.b64decode(qr_image)
        st.image(img_data, caption="Generierter QR-Code")

        # Download button
        st.download_button(
            "💾 QR-Code herunterladen",
            data=img_data,
            file_name=f"qr_code_{result.get('generated_at', 'unknown')}.png",
            mime="image/png"
        )

    with col2:
        # Display data
        st.write("**Kodierte Daten:**")
        if isinstance(result.get("data"), dict):
            st.json(result["data"])
        else:
            st.code(str(result.get("data", "")))

        # Additional info
        if "item_data" in result:
            st.write("**Item Information:**")
            st.json(result["item_data"])


def display_barcode(barcode_image: str, result: Dict[str, Any]):
    """Display generated barcode"""
    st.success("✅ Barcode erfolgreich generiert!")

    col1, col2 = st.columns([1, 1])

    with col1:
        # Display barcode
        img_data = base64.b64decode(barcode_image)
        st.image(img_data, caption="Generierter Barcode")

        # Download button
        st.download_button(
            "💾 Barcode herunterladen",
            data=img_data,
            file_name=f"barcode_{result.get('barcode_data', 'unknown')}.png",
            mime="image/png"
        )

    with col2:
        # Display data
        st.write("**Barcode Daten:**")
        st.code(result.get("barcode_data", ""))

        st.write("**Barcode Typ:**")
        st.write(result.get("barcode_type", "code128").upper())

        # Additional info
        if "item_data" in result:
            st.write("**Item Information:**")
            st.json(result["item_data"])


def display_item_info(item_data: Dict[str, Any]):
    """Display item information"""
    col1, col2 = st.columns(2)

    with col1:
        st.write(f"**Name:** {item_data.get('name', 'Unbekannt')}")
        st.write(f"**ID:** {item_data.get('id', 'Unbekannt')}")
        st.write(f"**Typ:** {item_data.get('type', 'Unbekannt').title()}")

        if "kategorie" in item_data:
            st.write(f"**Kategorie:** {item_data['kategorie']}")
        if "typ" in item_data and item_data["type"] == "cable":
            st.write(f"**Kabel Typ:** {item_data['typ']}")

    with col2:
        if "standort_name" in item_data:
            st.write(f"**Standort:** {item_data['standort_name']}")
        if "lagerort" in item_data:
            st.write(f"**Lagerort:** {item_data['lagerort']}")
        if "seriennummer" in item_data and item_data["seriennummer"]:
            st.write(f"**Seriennummer:** {item_data['seriennummer']}")
        if "menge" in item_data:
            st.write(f"**Bestand:** {item_data['menge']}")