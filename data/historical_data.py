import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import sqlite3
import os
import json

class HistoricalDataManager:
    def __init__(self, db_path: str = "data/historical.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for historical data"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables for different timeframes
            timeframes = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']
            
            for tf in timeframes:
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {tf.lower()}_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        open REAL NOT NULL,
                        high REAL NOT NULL,
                        low REAL NOT NULL,
                        close REAL NOT NULL,
                        volume INTEGER DEFAULT 0,
                        UNIQUE(symbol, timestamp)
                    )
                ''')
                
                # Create index for faster queries
                cursor.execute(f'''
                    CREATE INDEX IF NOT EXISTS idx_{tf.lower()}_symbol_time 
                    ON {tf.lower()}_data(symbol, timestamp)
                ''')
            
            conn.commit()
            conn.close()
            
            self.logger.info("Historical data database initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
    
    def store_data(self, symbol: str, timeframe: str, data: pd.DataFrame) -> bool:
        """Store historical data in database"""
        try:
            if data is None or data.empty:
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Prepare data for insertion
            table_name = f"{timeframe.lower()}_data"
            records = []
            
            for timestamp, row in data.iterrows():
                record = (
                    symbol,
                    timestamp.isoformat(),
                    row.get('open', 0),
                    row.get('high', 0),
                    row.get('low', 0),
                    row.get('close', 0),
                    row.get('volume', 0)
                )
                records.append(record)
            
            # Insert data (replace on conflict)
            cursor.executemany(f'''
                INSERT OR REPLACE INTO {table_name} 
                (symbol, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', records)
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Stored {len(records)} records for {symbol} {timeframe}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing data for {symbol} {timeframe}: {e}")
            return False
    
    def get_data(self, symbol: str, timeframe: str, start_date: datetime = None, 
                end_date: datetime = None, limit: int = None) -> Optional[pd.DataFrame]:
        """Get historical data from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Build query
            table_name = f"{timeframe.lower()}_data"
            query = f"SELECT timestamp, open, high, low, close, volume FROM {table_name} WHERE symbol = ?"
            params = [symbol]
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            
            query += " ORDER BY timestamp"
            
            if limit:
                query += f" LIMIT {limit}"
            
            # Execute query
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            if df.empty:
                return None
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting data for {symbol} {timeframe}: {e}")
            return None
    
    def get_latest_data(self, symbol: str, timeframe: str, count: int = 100) -> Optional[pd.DataFrame]:
        """Get latest historical data"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            table_name = f"{timeframe.lower()}_data"
            query = f'''
                SELECT timestamp, open, high, low, close, volume 
                FROM {table_name} 
                WHERE symbol = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            '''
            
            df = pd.read_sql_query(query, conn, params=[symbol, count])
            conn.close()
            
            if df.empty:
                return None
            
            # Convert timestamp and sort by time
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting latest data for {symbol} {timeframe}: {e}")
            return None
    
    def get_data_range(self, symbol: str, timeframe: str) -> Optional[Tuple[datetime, datetime]]:
        """Get date range for available data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            table_name = f"{timeframe.lower()}_data"
            query = f'''
                SELECT MIN(timestamp), MAX(timestamp) 
                FROM {table_name} 
                WHERE symbol = ?
            '''
            
            cursor.execute(query, [symbol])
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] and result[1]:
                return (
                    datetime.fromisoformat(result[0]),
                    datetime.fromisoformat(result[1])
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting data range for {symbol} {timeframe}: {e}")
            return None
    
    def get_available_symbols(self, timeframe: str) -> List[str]:
        """Get list of available symbols for timeframe"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            table_name = f"{timeframe.lower()}_data"
            query = f"SELECT DISTINCT symbol FROM {table_name} ORDER BY symbol"
            
            cursor.execute(query)
            symbols = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return symbols
            
        except Exception as e:
            self.logger.error(f"Error getting available symbols for {timeframe}: {e}")
            return []
    
    def get_data_statistics(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """Get statistics for stored data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            table_name = f"{timeframe.lower()}_data"
            query = f'''
                SELECT 
                    COUNT(*) as record_count,
                    MIN(timestamp) as first_date,
                    MAX(timestamp) as last_date,
                    AVG(close) as avg_price,
                    MIN(low) as min_price,
                    MAX(high) as max_price
                FROM {table_name} 
                WHERE symbol = ?
            '''
            
            cursor.execute(query, [symbol])
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] > 0:
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'record_count': result[0],
                    'first_date': datetime.fromisoformat(result[1]) if result[1] else None,
                    'last_date': datetime.fromisoformat(result[2]) if result[2] else None,
                    'avg_price': result[3],
                    'min_price': result[4],
                    'max_price': result[5]
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting data statistics for {symbol} {timeframe}: {e}")
            return None
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data to save space"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cutoff_str = cutoff_date.isoformat()
            
            timeframes = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']
            total_deleted = 0
            
            for tf in timeframes:
                table_name = f"{tf.lower()}_data"
                query = f"DELETE FROM {table_name} WHERE timestamp < ?"
                
                cursor.execute(query, [cutoff_str])
                deleted = cursor.rowcount
                total_deleted += deleted
                
                self.logger.info(f"Deleted {deleted} old records from {table_name}")
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Cleanup completed: {total_deleted} records deleted")
            return total_deleted
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
            return 0
    
    def export_data(self, symbol: str, timeframe: str, start_date: datetime = None, 
                   end_date: datetime = None, format: str = 'csv') -> Optional[str]:
        """Export data to file"""
        try:
            data = self.get_data(symbol, timeframe, start_date, end_date)
            if data is None or data.empty:
                return None
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{symbol}_{timeframe}_{timestamp}.{format}"
            filepath = os.path.join("data/exports", filename)
            
            # Create exports directory
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Export data
            if format.lower() == 'csv':
                data.to_csv(filepath)
            elif format.lower() == 'json':
                data.to_json(filepath, orient='index', date_format='iso')
            elif format.lower() == 'excel':
                data.to_excel(filepath)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            self.logger.info(f"Data exported to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error exporting data: {e}")
            return None
    
    def import_data(self, filepath: str, symbol: str, timeframe: str) -> bool:
        """Import data from file"""
        try:
            if not os.path.exists(filepath):
                self.logger.error(f"File not found: {filepath}")
                return False
            
            # Read data based on file extension
            if filepath.endswith('.csv'):
                data = pd.read_csv(filepath, index_col=0, parse_dates=True)
            elif filepath.endswith('.json'):
                data = pd.read_json(filepath, orient='index')
                data.index = pd.to_datetime(data.index)
            elif filepath.endswith('.xlsx') or filepath.endswith('.xls'):
                data = pd.read_excel(filepath, index_col=0, parse_dates=True)
            else:
                raise ValueError(f"Unsupported file format: {filepath}")
            
            # Validate data format
            required_columns = ['open', 'high', 'low', 'close']
            if not all(col in data.columns for col in required_columns):
                self.logger.error(f"Invalid data format. Required columns: {required_columns}")
                return False
            
            # Store data
            success = self.store_data(symbol, timeframe, data)
            
            if success:
                self.logger.info(f"Data imported successfully from {filepath}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error importing data: {e}")
            return False
    
    def get_database_info(self) -> Dict:
        """Get database information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            info = {
                'database_path': self.db_path,
                'timeframes': {},
                'total_size_mb': 0
            }
            
            # Get database size
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            size_result = cursor.fetchone()
            if size_result:
                info['total_size_mb'] = size_result[0] / (1024 * 1024)
            
            # Get info for each timeframe
            timeframes = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']
            
            for tf in timeframes:
                table_name = f"{tf.lower()}_data"
                
                # Get record count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                record_count = cursor.fetchone()[0]
                
                # Get unique symbols
                cursor.execute(f"SELECT COUNT(DISTINCT symbol) FROM {table_name}")
                symbol_count = cursor.fetchone()[0]
                
                # Get date range
                cursor.execute(f"SELECT MIN(timestamp), MAX(timestamp) FROM {table_name}")
                date_range = cursor.fetchone()
                
                info['timeframes'][tf] = {
                    'record_count': record_count,
                    'symbol_count': symbol_count,
                    'first_date': datetime.fromisoformat(date_range[0]).isoformat() if date_range[0] else None,
                    'last_date': datetime.fromisoformat(date_range[1]).isoformat() if date_range[1] else None
                }
            
            conn.close()
            return info
            
        except Exception as e:
            self.logger.error(f"Error getting database info: {e}")
            return {}


class DataBackupManager:
    """Manager for backing up and restoring historical data"""
    
    def __init__(self, historical_manager: HistoricalDataManager):
        self.historical_manager = historical_manager
        self.logger = logging.getLogger(__name__)
    
    def create_backup(self, backup_path: str = None) -> Optional[str]:
        """Create backup of historical data"""
        try:
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"data/backups/historical_backup_{timestamp}.db"
            
            # Create backup directory
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # Copy database
            import shutil
            shutil.copy2(self.historical_manager.db_path, backup_path)
            
            self.logger.info(f"Backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
            return None
    
    def restore_backup(self, backup_path: str) -> bool:
        """Restore from backup"""
        try:
            if not os.path.exists(backup_path):
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Create backup of current database
            current_backup = self.create_backup()
            if not current_backup:
                self.logger.error("Failed to create backup of current database")
                return False
            
            # Restore from backup
            import shutil
            shutil.copy2(backup_path, self.historical_manager.db_path)
            
            self.logger.info(f"Database restored from backup: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error restoring backup: {e}")
            return False
    
    def list_backups(self, backup_dir: str = "data/backups") -> List[str]:
        """List available backups"""
        try:
            if not os.path.exists(backup_dir):
                return []
            
            backup_files = []
            for filename in os.listdir(backup_dir):
                if filename.startswith("historical_backup_") and filename.endswith(".db"):
                    filepath = os.path.join(backup_dir, filename)
                    file_stat = os.stat(filepath)
                    backup_files.append({
                        'filename': filename,
                        'filepath': filepath,
                        'size_mb': file_stat.st_size / (1024 * 1024),
                        'created': datetime.fromtimestamp(file_stat.st_ctime)
                    })
            
            # Sort by creation time (newest first)
            backup_files.sort(key=lambda x: x['created'], reverse=True)
            return backup_files
            
        except Exception as e:
            self.logger.error(f"Error listing backups: {e}")
            return []
