"""
Database utilities for raw SQL operations
"""

import sqlite3
import os
from typing import Any, Dict, List
from contextlib import contextmanager


@contextmanager
def get_db_connection():
    """
    Get a simple database connection for raw SQL operations
    This is a fallback utility for modules that need direct SQL access
    """
    # In a production environment, this would connect to the same database
    # For now, we'll create a simple SQLite connection
    
    # Get database path from environment or use default
    db_path = os.getenv('SQLITE_DB_PATH', 'database/inventory.db')
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    
    try:
        yield conn
    finally:
        conn.close()


def execute_query(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query and return results as list of dictionaries
    """
    with get_db_connection() as conn:
        cursor = conn.execute(query, params)
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]


def execute_update(query: str, params: tuple = ()) -> int:
    """
    Execute an INSERT/UPDATE/DELETE query and return number of affected rows
    """
    with get_db_connection() as conn:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.rowcount


def create_tables_if_not_exist():
    """
    Create basic tables if they don't exist (for testing purposes)
    """
    with get_db_connection() as conn:
        # Create hardware table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS hardware_inventar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seriennummer TEXT UNIQUE NOT NULL,
                hersteller TEXT,
                modell TEXT,
                kategorie TEXT,
                preis REAL,
                anschaffungsdatum TEXT,
                garantie_ende TEXT,
                status TEXT DEFAULT 'aktiv',
                standort_id INTEGER,
                notizen TEXT,
                erstellt_am TEXT,
                aktualisiert_am TEXT
            )
        """)
        
        # Create cable table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kabel_inventar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seriennummer TEXT UNIQUE NOT NULL,
                typ TEXT,
                kategorie TEXT,
                laenge REAL,
                farbe TEXT,
                anschaffungsdatum TEXT,
                status TEXT DEFAULT 'aktiv',
                standort_id INTEGER,
                notizen TEXT,
                erstellt_am TEXT,
                aktualisiert_am TEXT
            )
        """)
        
        # Create locations table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS standorte (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                beschreibung TEXT,
                adresse TEXT,
                erstellt_am TEXT,
                aktualisiert_am TEXT
            )
        """)
        
        conn.commit()
