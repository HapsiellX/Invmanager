"""
Search module for advanced search and filtering capabilities
"""

from .services import SearchService, get_search_service
from .views import show_search_page

__all__ = [
    "SearchService",
    "get_search_service",
    "show_search_page"
]