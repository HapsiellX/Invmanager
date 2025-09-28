"""
Core utility functions for the inventory management system
"""

from datetime import datetime
from typing import Optional, Union


def format_currency(amount: Optional[Union[int, float]]) -> str:
    """Format a numeric amount as currency in EUR format"""
    if amount is None:
        return "€0.00"
    
    try:
        return f"€{float(amount):,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    except (ValueError, TypeError):
        return "€0.00"


def format_date(date_value: Optional[Union[str, datetime]]) -> str:
    """Format a date value to German date format (DD.MM.YYYY)"""
    if date_value is None:
        return ""
    
    try:
        if isinstance(date_value, str):
            # Try to parse common date formats
            try:
                date_obj = datetime.strptime(date_value, "%Y-%m-%d")
            except ValueError:
                try:
                    date_obj = datetime.strptime(date_value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return date_value  # Return as-is if parsing fails
        elif isinstance(date_value, datetime):
            date_obj = date_value
        else:
            return str(date_value)
        
        return date_obj.strftime("%d.%m.%Y")
    except Exception:
        return str(date_value)


def format_datetime(datetime_value: Optional[Union[str, datetime]]) -> str:
    """Format a datetime value to German datetime format (DD.MM.YYYY HH:MM)"""
    if datetime_value is None:
        return ""
    
    try:
        if isinstance(datetime_value, str):
            # Try to parse common datetime formats
            try:
                dt_obj = datetime.strptime(datetime_value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    dt_obj = datetime.strptime(datetime_value, "%Y-%m-%d")
                except ValueError:
                    return datetime_value  # Return as-is if parsing fails
        elif isinstance(datetime_value, datetime):
            dt_obj = datetime_value
        else:
            return str(datetime_value)
        
        return dt_obj.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(datetime_value)


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing/replacing invalid characters"""
    import re
    
    # Replace spaces and special characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'\s+', '_', filename)
    
    # Remove any leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    return filename


def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text to specified length with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def get_file_size_string(size_bytes: int) -> str:
    """Convert bytes to human readable file size"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"
