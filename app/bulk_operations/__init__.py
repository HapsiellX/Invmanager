"""
Bulk operations module for efficient inventory management
"""

from .services import BulkOperationsService, get_bulk_operations_service
from .views import show_bulk_operations_page

__all__ = [
    "BulkOperationsService",
    "get_bulk_operations_service",
    "show_bulk_operations_page"
]
