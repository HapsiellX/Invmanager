"""
Advanced reporting module for comprehensive inventory reports
"""

from .services import ReportService, get_report_service
from .views import show_reports_page

__all__ = [
    "ReportService",
    "get_report_service", 
    "show_reports_page"
]
