"""
QR Code and Barcode module for inventory management
"""

from .services import QRBarcodeService, get_qr_barcode_service
from .views import show_qr_barcode_page

__all__ = [
    "QRBarcodeService",
    "get_qr_barcode_service",
    "show_qr_barcode_page"
]