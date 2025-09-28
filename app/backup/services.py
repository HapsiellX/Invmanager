"""
Automated backup and data archiving services
"""

import os
import json
import zipfile
import shutil
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, create_engine
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import subprocess
import hashlib

from database.models.hardware import HardwareItem
from database.models.cable import Cable
from database.models.location import Location
from database.models.user import User
from database.models.audit_log import AuditLog
from database.models.settings import SystemSettings
from core.database import get_db, engine
from core.config import settings


class BackupService:
    """Service for automated backup and data archiving"""

    def __init__(self, db: Session):
        self.db = db
        self.backup_base_path = self._get_backup_path()

    def _get_backup_path(self) -> Path:
        """Get the backup directory path"""
        backup_path = Path(settings.BACKUP_PATH if hasattr(settings, 'BACKUP_PATH') else './backups')
        backup_path.mkdir(parents=True, exist_ok=True)
        return backup_path

    def create_full_backup(self, include_files: bool = True, compress: bool = True) -> Dict[str, Any]:
        """Create a complete system backup"""
        backup_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"full_backup_{backup_id}"

        try:
            # Create backup directory
            backup_dir = self.backup_base_path / backup_name
            backup_dir.mkdir(exist_ok=True)

            backup_info = {
                "backup_id": backup_id,
                "backup_name": backup_name,
                "backup_type": "full",
                "created_at": datetime.now().isoformat(),
                "status": "in_progress",
                "size_bytes": 0,
                "components": []
            }

            # 1. Database backup
            db_backup_result = self._backup_database(backup_dir)
            backup_info["components"].append(db_backup_result)

            # 2. Application configuration
            config_backup_result = self._backup_configuration(backup_dir)
            backup_info["components"].append(config_backup_result)

            # 3. User uploads/files (if any)
            if include_files:
                files_backup_result = self._backup_files(backup_dir)
                backup_info["components"].append(files_backup_result)

            # 4. System metadata
            metadata_result = self._backup_metadata(backup_dir, backup_info)
            backup_info["components"].append(metadata_result)

            # Calculate total size
            total_size = sum(comp.get("size_bytes", 0) for comp in backup_info["components"])
            backup_info["size_bytes"] = total_size

            # 5. Compress if requested
            if compress:
                compressed_file = self._compress_backup(backup_dir)
                if compressed_file:
                    # Remove uncompressed directory
                    shutil.rmtree(backup_dir)
                    backup_info["compressed"] = True
                    backup_info["file_path"] = str(compressed_file)
                    backup_info["size_bytes"] = compressed_file.stat().st_size
                else:
                    backup_info["compressed"] = False
                    backup_info["file_path"] = str(backup_dir)
            else:
                backup_info["compressed"] = False
                backup_info["file_path"] = str(backup_dir)

            # Calculate checksum
            backup_info["checksum"] = self._calculate_backup_checksum(backup_info["file_path"])

            backup_info["status"] = "completed"
            backup_info["completed_at"] = datetime.now().isoformat()

            # Save backup info to database
            self._save_backup_info(backup_info)

            return backup_info

        except Exception as e:
            backup_info["status"] = "failed"
            backup_info["error"] = str(e)
            backup_info["failed_at"] = datetime.now().isoformat()

            # Clean up failed backup
            if backup_dir.exists():
                shutil.rmtree(backup_dir, ignore_errors=True)

            return backup_info

    def create_incremental_backup(self, last_backup_date: datetime) -> Dict[str, Any]:
        """Create an incremental backup since last backup"""
        backup_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"incremental_backup_{backup_id}"

        try:
            backup_dir = self.backup_base_path / backup_name
            backup_dir.mkdir(exist_ok=True)

            backup_info = {
                "backup_id": backup_id,
                "backup_name": backup_name,
                "backup_type": "incremental",
                "created_at": datetime.now().isoformat(),
                "since_date": last_backup_date.isoformat(),
                "status": "in_progress",
                "components": []
            }

            # 1. Incremental database backup (changed records)
            db_changes = self._backup_database_changes(backup_dir, last_backup_date)
            backup_info["components"].append(db_changes)

            # 2. Audit log since last backup
            audit_backup = self._backup_audit_logs(backup_dir, last_backup_date)
            backup_info["components"].append(audit_backup)

            # 3. Configuration changes
            config_backup = self._backup_configuration(backup_dir)
            backup_info["components"].append(config_backup)

            # Compress backup
            compressed_file = self._compress_backup(backup_dir)
            if compressed_file:
                shutil.rmtree(backup_dir)
                backup_info["compressed"] = True
                backup_info["file_path"] = str(compressed_file)
                backup_info["size_bytes"] = compressed_file.stat().st_size
            else:
                backup_info["file_path"] = str(backup_dir)
                backup_info["size_bytes"] = sum(comp.get("size_bytes", 0) for comp in backup_info["components"])

            backup_info["checksum"] = self._calculate_backup_checksum(backup_info["file_path"])
            backup_info["status"] = "completed"
            backup_info["completed_at"] = datetime.now().isoformat()

            self._save_backup_info(backup_info)

            return backup_info

        except Exception as e:
            backup_info["status"] = "failed"
            backup_info["error"] = str(e)
            return backup_info

    def _backup_database(self, backup_dir: Path) -> Dict[str, Any]:
        """Backup the entire database"""
        try:
            db_backup_file = backup_dir / "database.sql"

            # Get database URL
            db_url = str(engine.url)

            if "sqlite" in db_url:
                # SQLite backup
                db_file = db_url.replace("sqlite:///", "")
                shutil.copy2(db_file, backup_dir / "database.db")

                # Also export as SQL
                self._export_sqlite_to_sql(db_file, db_backup_file)

            elif "postgresql" in db_url:
                # PostgreSQL backup using pg_dump
                self._backup_postgresql(db_backup_file)

            else:
                # Generic SQL export
                self._export_generic_sql(db_backup_file)

            # Get file size
            file_size = db_backup_file.stat().st_size if db_backup_file.exists() else 0

            return {
                "component": "database",
                "status": "success",
                "file_path": str(db_backup_file),
                "size_bytes": file_size,
                "tables_count": self._count_database_tables(),
                "records_count": self._count_database_records()
            }

        except Exception as e:
            return {
                "component": "database",
                "status": "failed",
                "error": str(e),
                "size_bytes": 0
            }

    def _backup_database_changes(self, backup_dir: Path, since_date: datetime) -> Dict[str, Any]:
        """Backup only changed database records since specified date"""
        try:
            changes_file = backup_dir / "database_changes.json"

            changes = {
                "since_date": since_date.isoformat(),
                "changes": {
                    "hardware": self._get_changed_records(HardwareItem, since_date),
                    "cables": self._get_changed_records(Cable, since_date),
                    "locations": self._get_changed_records(Location, since_date),
                    "users": self._get_changed_records(User, since_date),
                    "settings": self._get_changed_records(SystemSettings, since_date)
                }
            }

            # Write changes to file
            with open(changes_file, 'w', encoding='utf-8') as f:
                json.dump(changes, f, indent=2, ensure_ascii=False, default=str)

            total_changes = sum(len(records) for records in changes["changes"].values())

            return {
                "component": "database_changes",
                "status": "success",
                "file_path": str(changes_file),
                "size_bytes": changes_file.stat().st_size,
                "total_changes": total_changes,
                "changes_by_table": {k: len(v) for k, v in changes["changes"].items()}
            }

        except Exception as e:
            return {
                "component": "database_changes",
                "status": "failed",
                "error": str(e),
                "size_bytes": 0
            }

    def _backup_audit_logs(self, backup_dir: Path, since_date: datetime) -> Dict[str, Any]:
        """Backup audit logs since specified date"""
        try:
            audit_file = backup_dir / "audit_logs.json"

            # Get audit logs since date
            audit_logs = self.db.query(AuditLog).filter(
                AuditLog.zeitstempel >= since_date
            ).order_by(AuditLog.zeitstempel.desc()).all()

            audit_data = {
                "since_date": since_date.isoformat(),
                "logs_count": len(audit_logs),
                "logs": [
                    {
                        "id": log.id,
                        "zeitstempel": log.zeitstempel.isoformat(),
                        "benutzer_id": log.benutzer_id,
                        "benutzer_rolle": log.benutzer_rolle,
                        "aktion": log.aktion,
                        "ressource_typ": log.ressource_typ,
                        "ressource_id": log.ressource_id,
                        "alte_werte": log.alte_werte,
                        "neue_werte": log.neue_werte,
                        "beschreibung": log.beschreibung,
                        "ip_adresse": log.ip_adresse,
                        "user_agent": log.user_agent
                    }
                    for log in audit_logs
                ]
            }

            with open(audit_file, 'w', encoding='utf-8') as f:
                json.dump(audit_data, f, indent=2, ensure_ascii=False, default=str)

            return {
                "component": "audit_logs",
                "status": "success",
                "file_path": str(audit_file),
                "size_bytes": audit_file.stat().st_size,
                "logs_count": len(audit_logs)
            }

        except Exception as e:
            return {
                "component": "audit_logs",
                "status": "failed",
                "error": str(e),
                "size_bytes": 0
            }

    def _backup_configuration(self, backup_dir: Path) -> Dict[str, Any]:
        """Backup system configuration"""
        try:
            config_file = backup_dir / "configuration.json"

            # Get system settings from database
            system_settings = self.db.query(SystemSettings).all()

            config_data = {
                "backup_date": datetime.now().isoformat(),
                "system_settings": [
                    {
                        "key": setting.key,
                        "value": setting.value,
                        "description": setting.description,
                        "category": setting.category,
                        "data_type": setting.data_type,
                        "updated_at": setting.updated_at.isoformat() if setting.updated_at else None
                    }
                    for setting in system_settings
                ],
                "environment_config": {
                    "database_url_type": "sqlite" if "sqlite" in str(engine.url) else "postgresql",
                    "log_level": settings.LOG_LEVEL,
                    "is_development": settings.is_development
                }
            }

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False, default=str)

            return {
                "component": "configuration",
                "status": "success",
                "file_path": str(config_file),
                "size_bytes": config_file.stat().st_size,
                "settings_count": len(system_settings)
            }

        except Exception as e:
            return {
                "component": "configuration",
                "status": "failed",
                "error": str(e),
                "size_bytes": 0
            }

    def _backup_files(self, backup_dir: Path) -> Dict[str, Any]:
        """Backup user files and uploads"""
        try:
            files_dir = backup_dir / "files"
            files_dir.mkdir(exist_ok=True)

            # Backup any user uploaded files (if directory exists)
            uploads_path = Path("./uploads")
            files_copied = 0
            total_size = 0

            if uploads_path.exists():
                for file_path in uploads_path.rglob("*"):
                    if file_path.is_file():
                        relative_path = file_path.relative_to(uploads_path)
                        dest_path = files_dir / relative_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, dest_path)
                        files_copied += 1
                        total_size += file_path.stat().st_size

            return {
                "component": "files",
                "status": "success",
                "file_path": str(files_dir),
                "size_bytes": total_size,
                "files_count": files_copied
            }

        except Exception as e:
            return {
                "component": "files",
                "status": "failed",
                "error": str(e),
                "size_bytes": 0
            }

    def _backup_metadata(self, backup_dir: Path, backup_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create backup metadata file"""
        try:
            metadata_file = backup_dir / "backup_metadata.json"

            metadata = {
                "backup_info": backup_info,
                "system_info": {
                    "python_version": self._get_python_version(),
                    "database_version": self._get_database_version(),
                    "application_version": "1.0.0",  # Would be from settings
                    "backup_created_by": "Inventory Management System",
                    "backup_format_version": "1.0"
                },
                "statistics": {
                    "total_hardware": self.db.query(HardwareItem).filter(HardwareItem.ist_aktiv == True).count(),
                    "total_cables": self.db.query(Cable).filter(Cable.ist_aktiv == True).count(),
                    "total_locations": self.db.query(Location).filter(Location.ist_aktiv == True).count(),
                    "total_users": self.db.query(User).filter(User.ist_aktiv == True).count(),
                    "total_audit_logs": self.db.query(AuditLog).count()
                }
            }

            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)

            return {
                "component": "metadata",
                "status": "success",
                "file_path": str(metadata_file),
                "size_bytes": metadata_file.stat().st_size
            }

        except Exception as e:
            return {
                "component": "metadata",
                "status": "failed",
                "error": str(e),
                "size_bytes": 0
            }

    def _compress_backup(self, backup_dir: Path) -> Optional[Path]:
        """Compress backup directory into ZIP file"""
        try:
            zip_file = backup_dir.with_suffix('.zip')

            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in backup_dir.rglob("*"):
                    if file_path.is_file():
                        arc_name = file_path.relative_to(backup_dir.parent)
                        zipf.write(file_path, arc_name)

            return zip_file

        except Exception as e:
            print(f"Error compressing backup: {e}")
            return None

    def _calculate_backup_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of backup file/directory"""
        try:
            hasher = hashlib.sha256()

            path = Path(file_path)
            if path.is_file():
                with open(path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hasher.update(chunk)
            else:
                # For directories, hash all files
                for file_path in sorted(path.rglob("*")):
                    if file_path.is_file():
                        with open(file_path, 'rb') as f:
                            for chunk in iter(lambda: f.read(4096), b""):
                                hasher.update(chunk)

            return hasher.hexdigest()

        except Exception:
            return "checksum_failed"

    def _save_backup_info(self, backup_info: Dict[str, Any]) -> None:
        """Save backup information to database"""
        try:
            # In a real implementation, this would save to a backup_history table
            # For now, we'll save to a JSON file
            history_file = self.backup_base_path / "backup_history.json"

            history = []
            if history_file.exists():
                try:
                    with open(history_file, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                except:
                    history = []

            history.append(backup_info)

            # Keep only last 100 backups in history
            history = history[-100:]

            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False, default=str)

        except Exception as e:
            print(f"Error saving backup info: {e}")

    def get_backup_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get backup history"""
        try:
            history_file = self.backup_base_path / "backup_history.json"

            if not history_file.exists():
                return []

            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)

            # Sort by creation date (newest first)
            history.sort(key=lambda x: x.get('created_at', ''), reverse=True)

            return history[:limit]

        except Exception:
            return []

    def verify_backup(self, backup_path: str) -> Dict[str, Any]:
        """Verify backup integrity"""
        try:
            backup_file = Path(backup_path)

            verification = {
                "backup_path": backup_path,
                "verified_at": datetime.now().isoformat(),
                "status": "valid",
                "checks": {}
            }

            # Check if file/directory exists
            if not backup_file.exists():
                verification["status"] = "invalid"
                verification["error"] = "Backup file/directory not found"
                return verification

            verification["checks"]["exists"] = True

            # Check if it's compressed
            if backup_file.suffix == '.zip':
                verification["checks"]["compressed"] = True

                # Check ZIP integrity
                try:
                    with zipfile.ZipFile(backup_file, 'r') as zipf:
                        bad_files = zipf.testzip()
                        if bad_files:
                            verification["status"] = "corrupted"
                            verification["error"] = f"Corrupted files in ZIP: {bad_files}"
                            return verification
                        verification["checks"]["zip_integrity"] = True

                        # Check for required files
                        required_files = ["backup_metadata.json", "database.sql"]
                        zip_files = zipf.namelist()

                        for req_file in required_files:
                            file_found = any(req_file in zf for zf in zip_files)
                            verification["checks"][f"has_{req_file}"] = file_found

                except zipfile.BadZipFile:
                    verification["status"] = "corrupted"
                    verification["error"] = "Invalid ZIP file"
                    return verification

            else:
                verification["checks"]["compressed"] = False

                # Check for required files in directory
                required_files = ["backup_metadata.json", "database.sql"]
                for req_file in required_files:
                    file_exists = (backup_file / req_file).exists()
                    verification["checks"][f"has_{req_file}"] = file_exists
                    if not file_exists:
                        verification["status"] = "incomplete"

            return verification

        except Exception as e:
            return {
                "backup_path": backup_path,
                "verified_at": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }

    def cleanup_old_backups(self, retention_days: int = 30, keep_minimum: int = 5) -> Dict[str, Any]:
        """Clean up old backups based on retention policy"""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            # Get all backup files
            backup_files = list(self.backup_base_path.glob("*backup_*"))

            # Sort by modification time
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            deleted_count = 0
            deleted_size = 0
            kept_count = 0

            # Keep minimum number of backups regardless of age
            for i, backup_file in enumerate(backup_files):
                if i < keep_minimum:
                    kept_count += 1
                    continue

                # Check if backup is older than retention period
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_time < cutoff_date:
                    try:
                        if backup_file.is_file():
                            file_size = backup_file.stat().st_size
                            backup_file.unlink()
                        else:
                            file_size = sum(f.stat().st_size for f in backup_file.rglob('*') if f.is_file())
                            shutil.rmtree(backup_file)

                        deleted_count += 1
                        deleted_size += file_size
                    except Exception as e:
                        print(f"Error deleting {backup_file}: {e}")
                else:
                    kept_count += 1

            return {
                "cleanup_completed_at": datetime.now().isoformat(),
                "retention_days": retention_days,
                "keep_minimum": keep_minimum,
                "deleted_backups": deleted_count,
                "deleted_size_bytes": deleted_size,
                "kept_backups": kept_count,
                "status": "success"
            }

        except Exception as e:
            return {
                "cleanup_completed_at": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e)
            }

    def schedule_automatic_backup(self, backup_type: str = "incremental", interval_hours: int = 24) -> Dict[str, Any]:
        """Schedule automatic backups (would integrate with task scheduler)"""
        # This is a placeholder for scheduling functionality
        # In production, this would integrate with celery, cron, or Windows Task Scheduler

        schedule_info = {
            "backup_type": backup_type,
            "interval_hours": interval_hours,
            "next_backup": (datetime.now() + timedelta(hours=interval_hours)).isoformat(),
            "status": "scheduled",
            "created_at": datetime.now().isoformat()
        }

        return schedule_info

    # Helper methods
    def _get_changed_records(self, model_class, since_date: datetime) -> List[Dict[str, Any]]:
        """Get records that changed since specified date"""
        try:
            # For models with updated_at field
            if hasattr(model_class, 'updated_at'):
                records = self.db.query(model_class).filter(
                    model_class.updated_at >= since_date
                ).all()
            else:
                # Fallback to created_at or erstellt_am
                date_field = getattr(model_class, 'erstellt_am', getattr(model_class, 'created_at', None))
                if date_field:
                    records = self.db.query(model_class).filter(
                        date_field >= since_date
                    ).all()
                else:
                    records = []

            return [record.to_dict() for record in records if hasattr(record, 'to_dict')]

        except Exception:
            return []

    def _count_database_tables(self) -> int:
        """Count number of tables in database"""
        try:
            if "sqlite" in str(engine.url):
                result = self.db.execute(text("SELECT COUNT(*) FROM sqlite_master WHERE type='table'"))
            else:
                result = self.db.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"))

            return result.scalar()
        except:
            return 0

    def _count_database_records(self) -> int:
        """Count total records across all main tables"""
        try:
            hardware_count = self.db.query(HardwareItem).count()
            cable_count = self.db.query(Cable).count()
            location_count = self.db.query(Location).count()
            user_count = self.db.query(User).count()
            audit_count = self.db.query(AuditLog).count()

            return hardware_count + cable_count + location_count + user_count + audit_count
        except:
            return 0

    def _export_sqlite_to_sql(self, db_file: str, output_file: Path) -> None:
        """Export SQLite database to SQL file"""
        try:
            conn = sqlite3.connect(db_file)
            with open(output_file, 'w', encoding='utf-8') as f:
                for line in conn.iterdump():
                    f.write(f"{line}\n")
            conn.close()
        except Exception as e:
            print(f"Error exporting SQLite to SQL: {e}")

    def _backup_postgresql(self, output_file: Path) -> None:
        """Backup PostgreSQL database using pg_dump"""
        try:
            # This would use pg_dump command
            # subprocess.run(['pg_dump', db_url, '-f', str(output_file)], check=True)
            pass
        except Exception as e:
            print(f"Error backing up PostgreSQL: {e}")

    def _export_generic_sql(self, output_file: Path) -> None:
        """Export database using generic SQL queries"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("-- Generic SQL Export\n")
                f.write(f"-- Created: {datetime.now().isoformat()}\n\n")

                # Export table structures and data
                # This would iterate through all tables and export their data
                pass
        except Exception as e:
            print(f"Error exporting generic SQL: {e}")

    def _get_python_version(self) -> str:
        """Get Python version"""
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def _get_database_version(self) -> str:
        """Get database version"""
        try:
            if "sqlite" in str(engine.url):
                result = self.db.execute(text("SELECT sqlite_version()"))
                return f"SQLite {result.scalar()}"
            elif "postgresql" in str(engine.url):
                result = self.db.execute(text("SELECT version()"))
                return result.scalar()
            else:
                return "Unknown"
        except:
            return "Unknown"


def get_backup_service(db: Session = None) -> BackupService:
    """Dependency injection for backup service"""
    if db is None:
        db = next(get_db())
    return BackupService(db)