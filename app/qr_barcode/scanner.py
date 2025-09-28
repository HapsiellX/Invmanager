"""
Camera-based QR Code and Barcode Scanner Module
Implements real-time scanning using device camera via streamlit-webrtc
"""

import streamlit as st
import numpy as np
import cv2
from typing import Optional, Dict, Any, Tuple
import logging

# Import database models for lookups
from database.models.hardware import HardwareItem
from database.models.cable import Cable
from database.models.location import Location

# Configure logging
logger = logging.getLogger(__name__)

# Check for scanner dependencies
try:
    from pyzbar import pyzbar
    from pyzbar.pyzbar import ZBarSymbol
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False
    logger.warning("pyzbar not available - QR/Barcode scanning will be limited")

try:
    from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode
    import av
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False
    logger.warning("streamlit-webrtc not available - Camera scanning will be limited")


class QRBarcodeScanner:
    """
    Handles QR code and barcode scanning from camera or images
    """

    def __init__(self):
        """Initialize the scanner"""
        self.last_scanned_code = None
        self.scan_results = []

    def decode_image(self, image: np.ndarray) -> list:
        """
        Decode QR codes and barcodes from an image

        Args:
            image: numpy array of the image (BGR format from OpenCV)

        Returns:
            List of decoded objects with data and metadata
        """
        if not PYZBAR_AVAILABLE:
            return []

        try:
            # Convert BGR to RGB for pyzbar
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Decode QR codes and barcodes
            decoded_objects = pyzbar.decode(rgb_image)

            results = []
            for obj in decoded_objects:
                result = {
                    'type': obj.type,
                    'data': obj.data.decode('utf-8', errors='ignore'),
                    'rect': obj.rect,
                    'polygon': obj.polygon,
                    'quality': obj.quality if hasattr(obj, 'quality') else None,
                    'orientation': obj.orientation if hasattr(obj, 'orientation') else None
                }
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error decoding image: {e}")
            return []

    def draw_detection(self, image: np.ndarray, decoded_objects: list) -> np.ndarray:
        """
        Draw bounding boxes and labels on detected codes

        Args:
            image: Input image
            decoded_objects: List of decoded objects from decode_image

        Returns:
            Image with drawn detections
        """
        for obj in decoded_objects:
            # Draw bounding box
            rect = obj.get('rect')
            if rect:
                x, y, w, h = rect.x, rect.y, rect.width, rect.height
                cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # Draw label
                label = f"{obj['type']}: {obj['data'][:30]}..."
                cv2.putText(image, label, (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Draw polygon if available
            polygon = obj.get('polygon')
            if polygon and len(polygon) > 0:
                pts = np.array([[p.x, p.y] for p in polygon], np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(image, [pts], True, (0, 0, 255), 2)

        return image

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, Optional[Dict]]:
        """
        Process a single frame for QR/barcode detection

        Args:
            frame: Video frame as numpy array

        Returns:
            Tuple of (processed_frame, detected_code_data)
        """
        # Decode codes in the frame
        decoded_objects = self.decode_image(frame)

        # Draw detections on frame
        processed_frame = self.draw_detection(frame.copy(), decoded_objects)

        # Return first detected code if any
        detected_code = None
        if decoded_objects:
            detected_code = decoded_objects[0]

        return processed_frame, detected_code

    def scan_from_file(self, uploaded_file) -> Optional[Dict]:
        """
        Scan QR codes/barcodes from uploaded image file

        Args:
            uploaded_file: Streamlit uploaded file object

        Returns:
            Dictionary with scan results or None
        """
        try:
            # Convert uploaded file to OpenCV image
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

            if image is None:
                return None

            # Decode the image
            results = self.decode_image(image)

            if results:
                return results[0]  # Return first detected code
            return None

        except Exception as e:
            logger.error(f"Error scanning from file: {e}")
            return None


class VideoTransformer(VideoTransformerBase):
    """
    Video transformer for real-time QR/barcode scanning
    Used with streamlit-webrtc
    """

    def __init__(self):
        self.scanner = QRBarcodeScanner()
        self.detected_codes = []
        self.frame_count = 0
        self.scan_every_n_frames = 5  # Process every 5th frame for performance

    def transform(self, frame: av.VideoFrame) -> av.VideoFrame:
        """
        Transform video frame with QR/barcode detection

        Args:
            frame: Input video frame from streamlit-webrtc

        Returns:
            Processed video frame with annotations
        """
        # Convert frame to numpy array
        img = frame.to_ndarray(format="bgr24")

        # Process every nth frame for performance
        self.frame_count += 1
        if self.frame_count % self.scan_every_n_frames == 0:
            # Process frame for QR/barcode detection
            processed_img, detected_code = self.scanner.process_frame(img)

            # Store detected code
            if detected_code and detected_code not in self.detected_codes:
                self.detected_codes.append(detected_code)

            img = processed_img

        # Return processed frame
        return av.VideoFrame.from_ndarray(img, format="bgr24")


def show_camera_scanner(qr_service=None):
    """
    Display camera scanner interface in Streamlit

    Args:
        qr_service: QR/Barcode service instance for database lookups
    """
    st.subheader("📷 Kamera Scanner")

    # Check dependencies
    if not WEBRTC_AVAILABLE:
        st.error("❌ streamlit-webrtc ist nicht installiert!")
        st.code("pip install streamlit-webrtc av")
        return

    if not PYZBAR_AVAILABLE:
        st.error("❌ pyzbar ist nicht installiert!")
        st.code("pip install pyzbar")
        st.info("Hinweis: Auf Windows benötigen Sie möglicherweise auch Visual C++ Redistributable")
        return

    # Instructions
    with st.expander("📋 Anleitung"):
        st.markdown("""
        **So verwenden Sie den Kamera-Scanner:**
        1. Klicken Sie auf **'Start'** um die Kamera zu aktivieren
        2. Halten Sie den QR-Code oder Barcode vor die Kamera
        3. Der Code wird automatisch erkannt und angezeigt
        4. Klicken Sie auf **'Stop'** wenn Sie fertig sind

        **Unterstützte Formate:**
        - QR Codes
        - Barcodes (Code128, Code39, EAN13, etc.)
        - Data Matrix
        - PDF417

        **Tipps für bessere Erkennung:**
        - Sorgen Sie für gute Beleuchtung
        - Halten Sie den Code ruhig
        - Achten Sie auf scharfe Fokussierung
        - Vermeiden Sie Reflexionen
        """)

    # Camera scanner
    col1, col2 = st.columns([2, 1])

    with col1:
        st.write("### 🎥 Live-Kamera")

        # WebRTC configuration
        rtc_configuration = {
            "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
        }

        # Create webrtc streamer
        ctx = webrtc_streamer(
            key="qr-barcode-scanner",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=rtc_configuration,
            video_transformer_factory=VideoTransformer,
            media_stream_constraints={
                "video": {
                    "width": {"ideal": 640},
                    "height": {"ideal": 480},
                    "facingMode": "environment"  # Use back camera on mobile
                },
                "audio": False
            },
            async_processing=True,
        )

    with col2:
        st.write("### 📊 Scan-Ergebnisse")

        if ctx.video_transformer:
            # Get detected codes from video transformer
            detected_codes = ctx.video_transformer.detected_codes

            if detected_codes:
                st.success(f"✅ {len(detected_codes)} Code(s) erkannt!")

                for i, code in enumerate(detected_codes, 1):
                    with st.expander(f"Code {i}: {code['type']}", expanded=True):
                        st.write(f"**Typ:** {code['type']}")
                        st.code(code['data'])

                        # If service is provided, look up in database
                        if qr_service:
                            validation = qr_service.validate_qr_data(code['data'])
                            if validation['valid']:
                                st.info(f"📦 Item gefunden: {validation['type']} (ID: {validation['item_id']})")

                                if st.button(f"Details anzeigen", key=f"details_{i}"):
                                    # Lookup item in database
                                    if validation['type'] == 'hardware':
                                        item = qr_service.db.query(HardwareItem).filter(
                                            HardwareItem.id == validation['item_id']
                                        ).first()
                                    elif validation['type'] == 'cable':
                                        item = qr_service.db.query(Cable).filter(
                                            Cable.id == validation['item_id']
                                        ).first()

                                    if item:
                                        st.write("**Item Details:**")
                                        st.json(item.to_dict())
                            else:
                                st.warning("⚠️ Code nicht in Datenbank gefunden")

                # Clear button
                if st.button("🗑️ Ergebnisse löschen"):
                    ctx.video_transformer.detected_codes = []
                    st.rerun()
            else:
                st.info("Warten auf Code-Erkennung...")


def show_image_scanner(qr_service=None):
    """
    Display image upload scanner interface

    Args:
        qr_service: QR/Barcode service instance for database lookups
    """
    st.subheader("🖼️ Bild Scanner")

    if not PYZBAR_AVAILABLE:
        st.error("❌ pyzbar ist nicht installiert!")
        st.code("pip install pyzbar")
        return

    uploaded_file = st.file_uploader(
        "Bild mit QR-Code oder Barcode hochladen:",
        type=['png', 'jpg', 'jpeg', 'bmp'],
        key="image_scanner_upload"
    )

    if uploaded_file is not None:
        col1, col2 = st.columns(2)

        with col1:
            st.image(uploaded_file, caption="Hochgeladenes Bild", use_container_width=True)

        with col2:
            scanner = QRBarcodeScanner()
            result = scanner.scan_from_file(uploaded_file)

            if result:
                st.success("✅ Code erkannt!")
                st.write(f"**Typ:** {result['type']}")
                st.code(result['data'])

                # Database lookup if service provided
                if qr_service:
                    validation = qr_service.validate_qr_data(result['data'])
                    if validation['valid']:
                        st.info(f"📦 Item gefunden: {validation['type']} (ID: {validation['item_id']})")
                    else:
                        st.warning("⚠️ Code nicht in Datenbank gefunden")
            else:
                st.error("❌ Kein Code im Bild gefunden")
                st.info("Tipps: Stellen Sie sicher, dass der Code klar sichtbar und nicht verschwommen ist")


# Export scanner functions
__all__ = [
    'QRBarcodeScanner',
    'VideoTransformer',
    'show_camera_scanner',
    'show_image_scanner',
    'PYZBAR_AVAILABLE',
    'WEBRTC_AVAILABLE'
]