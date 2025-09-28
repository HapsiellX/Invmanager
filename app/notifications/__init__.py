"""
Notifications module for stock alerts and critical events
"""

from .services import NotificationService, get_notification_service, NotificationPriority, NotificationType
from .views import show_notifications_page, show_dashboard_notifications_widget, show_notification_badge

__all__ = [
    "NotificationService",
    "get_notification_service",
    "NotificationPriority",
    "NotificationType",
    "show_notifications_page",
    "show_dashboard_notifications_widget",
    "show_notification_badge"
]