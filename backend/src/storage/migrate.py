"""
Database Migration Script - Migrate from legacy schema to enhanced schema.
This script handles the migration while preserving existing data.
"""
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseMigration:
    """Handle database schema migration from v1 to v2"""
    
    def __init__(self, db_path: str = "./gandiva_pro.db", new_db_path: str = "./railway_monitoring.db"):
        self.db_path = Path(db_path)
        self.new_db_path = Path(new_db_path)
        self.backup_path = Path(f"{db_path}.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}")
    
    def migrate(self) -> bool:
        """Execute full migration"""
        try:
            logger.info("Starting database migration...")
            
            # Backup existing database
            self._backup_database()
            
            # Create new schema
            self._create_new_schema()
            
            # Migrate existing data
            self._migrate_data()
            
            logger.info("Migration completed successfully!")
            logger.info(f"New database: {self.new_db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
    
    def _backup_database(self):
        """Create backup of existing database"""
        import shutil
        if self.db_path.exists():
            shutil.copy2(self.db_path, self.backup_path)
            logger.info(f"Backup created: {self.backup_path}")
    
    def _create_new_schema(self):
        """Create enhanced database schema"""
        from storage.database import create_enhanced_engine, init_enhanced_db
        
        engine = create_enhanced_engine(f"sqlite:///{self.new_db_path}")
        init_enhanced_db(engine)
        logger.info("New schema created")
    
    def _migrate_data(self):
        """Migrate data from old database to new"""
        if not self.db_path.exists():
            logger.warning("No existing database to migrate from")
            return
        
        old_conn = sqlite3.connect(self.db_path)
        new_conn = sqlite3.connect(self.new_db_path)
        
        try:
            old_cursor = old_conn.cursor()
            new_cursor = new_conn.cursor()
            
            # Migrate thresholds to threshold_configs
            logger.info("Migrating thresholds...")
            old_cursor.execute("SELECT * FROM thresholds")
            thresholds = old_cursor.fetchall()
            
            for thresh in thresholds:
                new_cursor.execute("""
                    INSERT INTO threshold_configs (
                        parameter, warning_high, critical_high, is_active, created_at, updated_at
                    ) VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
                """, (thresh[1], thresh[2], thresh[3]))
            
            # Migrate alerts
            logger.info("Migrating alerts...")
            old_cursor.execute("SELECT * FROM alerts")
            alerts = old_cursor.fetchall()
            
            for alert in alerts:
                # Map old severity to new
                severity_map = {"warning": "warning", "critical": "critical"}
                severity = severity_map.get(alert[3], "warning")
                
                new_cursor.execute("""
                    INSERT INTO alerts (
                        alert_type, severity, status, title, message, parameter,
                        current_value, threshold, acknowledged, acknowledged_by,
                        acknowledged_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert[1], severity, "acknowledged" if alert[9] else "resolved",
                    alert[4], alert[4], alert[5], alert[6], alert[7],
                    alert[9], alert[10], alert[11], alert[12]
                ))
            
            new_conn.commit()
            logger.info(f"Migrated {len(thresholds)} thresholds and {len(alerts)} alerts")
            
        finally:
            old_conn.close()
            new_conn.close()
    
    def verify_migration(self) -> bool:
        """Verify migration was successful"""
        if not self.new_db_path.exists():
            logger.error("New database not found")
            return False
        
        conn = sqlite3.connect(self.new_db_path)
        try:
            cursor = conn.cursor()
            
            # Check all new tables exist
            required_tables = [
                'devices', 'raw_data', 'processed_data', 'defect_detections',
                'alerts', 'events', 'system_status', 'threshold_configs',
                'data_exports', 'notification_configs'
            ]
            
            for table in required_tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if not cursor.fetchone():
                    logger.error(f"Missing table: {table}")
                    return False
            
            logger.info("Migration verification passed")
            return True
            
        finally:
            conn.close()


if __name__ == "__main__":
    migrator = DatabaseMigration()
    
    if migrator.migrate():
        print("✅ Migration successful!")
        if migrator.verify_migration():
            print("✅ Verification passed!")
        else:
            print("❌ Verification failed!")
    else:
        print("❌ Migration failed!")
