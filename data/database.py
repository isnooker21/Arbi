"""
ระบบจัดการฐานข้อมูลสำหรับระบบเทรด
====================================

ไฟล์นี้ทำหน้าที่:
- สร้างและจัดการฐานข้อมูล SQLite
- เก็บข้อมูลการเทรด คำสั่งซื้อ/ขาย และตำแหน่ง
- เก็บข้อมูล AI และการเรียนรู้
- เก็บข้อมูลประสิทธิภาพและสถิติ
- เก็บข้อมูล Log และการติดตาม

Author: AI Trading System
Version: 1.0
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
import pandas as pd

class DatabaseManager:
    """
    ระบบจัดการฐานข้อมูลหลัก
    
    รับผิดชอบในการสร้าง จัดการ และเข้าถึงฐานข้อมูล
    สำหรับระบบเทรดทั้งหมด
    """
    
    def __init__(self, db_path: str = "data/trading_system.db"):
        """
        เริ่มต้นระบบจัดการฐานข้อมูล
        
        Args:
            db_path: เส้นทางไฟล์ฐานข้อมูล SQLite
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
        
    def _init_database(self):
        """
        เริ่มต้นฐานข้อมูล SQLite พร้อมตารางที่จำเป็น
        
        สร้างตารางทั้งหมดที่จำเป็นสำหรับระบบเทรด:
        - ตารางคำสั่งซื้อ/ขาย
        - ตารางตำแหน่งการเทรด
        - ตารางข้อมูล AI
        - ตารางประสิทธิภาพ
        - ตาราง Log
        """
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            self._create_trading_tables(cursor)
            self._create_ai_tables(cursor)
            self._create_performance_tables(cursor)
            self._create_log_tables(cursor)
            
            conn.commit()
            conn.close()
            
            self.logger.info("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
    
    def _create_trading_tables(self, cursor):
        """
        สร้างตารางที่เกี่ยวข้องกับการเทรด
        
        รวมถึงตารางคำสั่ง ตำแหน่ง และข้อมูลการเทรด
        """
        # Orders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                symbol TEXT NOT NULL,
                order_type TEXT NOT NULL,
                volume REAL NOT NULL,
                price REAL NOT NULL,
                sl REAL,
                tp REAL,
                status TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                closed_at DATETIME,
                profit_loss REAL DEFAULT 0,
                commission REAL DEFAULT 0,
                swap REAL DEFAULT 0,
                comment TEXT
            )
        ''')
        
        # Positions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id TEXT UNIQUE NOT NULL,
                symbol TEXT NOT NULL,
                position_type TEXT NOT NULL,
                volume REAL NOT NULL,
                open_price REAL NOT NULL,
                current_price REAL,
                sl REAL,
                tp REAL,
                status TEXT NOT NULL,
                opened_at DATETIME NOT NULL,
                closed_at DATETIME,
                profit_loss REAL DEFAULT 0,
                commission REAL DEFAULT 0,
                swap REAL DEFAULT 0,
                max_profit REAL DEFAULT 0,
                max_loss REAL DEFAULT 0,
                current_drawdown REAL DEFAULT 0,
                comment TEXT
            )
        ''')
        
        # Arbitrage opportunities table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                triangle TEXT NOT NULL,
                arbitrage_percent REAL NOT NULL,
                pair1_price REAL NOT NULL,
                pair2_price REAL NOT NULL,
                pair3_price REAL NOT NULL,
                spread_acceptable BOOLEAN NOT NULL,
                volatility REAL,
                market_conditions TEXT,
                ai_decision TEXT,
                executed BOOLEAN NOT NULL DEFAULT 0,
                profit_loss REAL,
                created_at DATETIME NOT NULL,
                executed_at DATETIME
            )
        ''')
        
        # Correlation recovery table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS correlation_recovery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                base_pair TEXT NOT NULL,
                recovery_pair TEXT NOT NULL,
                correlation REAL NOT NULL,
                suggested_direction TEXT NOT NULL,
                base_pnl REAL NOT NULL,
                recovery_volume REAL NOT NULL,
                ai_decision TEXT,
                executed BOOLEAN NOT NULL DEFAULT 0,
                profit_loss REAL,
                created_at DATETIME NOT NULL,
                executed_at DATETIME
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_opened ON positions(opened_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_arbitrage_created ON arbitrage_opportunities(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_correlation_created ON correlation_recovery(created_at)')
    
    def _create_ai_tables(self, cursor):
        """
        สร้างตารางที่เกี่ยวข้องกับ AI
        
        รวมถึงตารางการเรียนรู้ การตัดสินใจ และประสิทธิภาพ AI
        """
        # Rule performance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rule_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id TEXT NOT NULL,
                rule_name TEXT,
                category TEXT,
                timestamp DATETIME NOT NULL,
                success BOOLEAN NOT NULL,
                profit_loss REAL NOT NULL,
                confidence REAL,
                market_conditions TEXT,
                context TEXT,
                execution_time_ms INTEGER
            )
        ''')
        
        # AI decisions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_type TEXT NOT NULL,
                should_act BOOLEAN NOT NULL,
                confidence REAL NOT NULL,
                reasoning TEXT,
                fired_rules TEXT,
                actions TEXT,
                context TEXT,
                position_size REAL,
                direction TEXT,
                created_at DATETIME NOT NULL,
                outcome TEXT,
                profit_loss REAL
            )
        ''')
        
        # Market patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern_name TEXT,
                characteristics TEXT NOT NULL,
                success_rate REAL NOT NULL,
                sample_size INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                last_updated DATETIME NOT NULL,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Learning data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_type TEXT NOT NULL,
                features TEXT NOT NULL,
                target TEXT,
                prediction TEXT,
                actual_outcome TEXT,
                confidence REAL,
                created_at DATETIME NOT NULL
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rule_perf_rule_id ON rule_performance(rule_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rule_perf_timestamp ON rule_performance(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ai_decisions_type ON ai_decisions(decision_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ai_decisions_created ON ai_decisions(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_patterns_type ON market_patterns(pattern_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_learning_data_type ON learning_data(data_type)')
    
    def _create_performance_tables(self, cursor):
        """
        สร้างตารางติดตามประสิทธิภาพ
        
        รวมถึงตารางสถิติ กำไร/ขาดทุน และการวิเคราะห์
        """
        # Daily performance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                realized_pnl REAL DEFAULT 0,
                unrealized_pnl REAL DEFAULT 0,
                max_drawdown REAL DEFAULT 0,
                win_rate REAL DEFAULT 0,
                profit_factor REAL DEFAULT 0,
                sharpe_ratio REAL DEFAULT 0,
                created_at DATETIME NOT NULL,
                UNIQUE(date)
            )
        ''')
        
        # Hourly performance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hourly_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                datetime DATETIME NOT NULL,
                total_trades INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                active_positions INTEGER DEFAULT 0,
                arbitrage_opportunities INTEGER DEFAULT 0,
                correlation_recoveries INTEGER DEFAULT 0,
                ai_decisions INTEGER DEFAULT 0,
                created_at DATETIME NOT NULL
            )
        ''')
        
        # System metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metric_unit TEXT,
                timestamp DATETIME NOT NULL,
                context TEXT
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_perf_date ON daily_performance(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_hourly_perf_datetime ON hourly_performance(datetime)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_system_metrics_name ON system_metrics(metric_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp)')
    
    def _create_log_tables(self, cursor):
        """
        สร้างตาราง Log
        
        รวมถึงตาราง Log ระบบ และการติดตามเหตุการณ์
        """
        # System logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                module TEXT,
                function_name TEXT,
                line_number INTEGER,
                timestamp DATETIME NOT NULL,
                context TEXT
            )
        ''')
        
        # Error logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                stack_trace TEXT,
                module TEXT,
                function_name TEXT,
                line_number INTEGER,
                timestamp DATETIME NOT NULL,
                context TEXT,
                resolved BOOLEAN DEFAULT 0
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_error_logs_type ON error_logs(error_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp ON error_logs(timestamp)')
    
    def execute_query(self, query: str, params: tuple = None) -> List[tuple]:
        """Execute a SQL query and return results"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            conn.close()
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error executing query: {e}")
            return []
    
    def execute_insert(self, query: str, params: tuple = None) -> int:
        """Execute an INSERT query and return the last row ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            last_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return last_id
            
        except Exception as e:
            self.logger.error(f"Error executing insert: {e}")
            return 0
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute an UPDATE query and return the number of affected rows"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            affected_rows = cursor.rowcount
            conn.commit()
            conn.close()
            
            return affected_rows
            
        except Exception as e:
            self.logger.error(f"Error executing update: {e}")
            return 0
    
    def get_dataframe(self, query: str, params: tuple = None) -> pd.DataFrame:
        """Execute a query and return results as DataFrame"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            if params:
                df = pd.read_sql_query(query, conn, params=params)
            else:
                df = pd.read_sql_query(query, conn)
            
            conn.close()
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting DataFrame: {e}")
            return pd.DataFrame()
    
    def insert_order(self, order_data: Dict) -> int:
        """Insert a new order record"""
        query = '''
            INSERT INTO orders (
                order_id, symbol, order_type, volume, price, sl, tp, status,
                created_at, updated_at, comment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        params = (
            order_data.get('order_id'),
            order_data.get('symbol'),
            order_data.get('order_type'),
            order_data.get('volume'),
            order_data.get('price'),
            order_data.get('sl'),
            order_data.get('tp'),
            order_data.get('status', 'pending'),
            order_data.get('created_at', datetime.now()),
            order_data.get('updated_at', datetime.now()),
            order_data.get('comment')
        )
        
        return self.execute_insert(query, params)
    
    def insert_position(self, position_data: Dict) -> int:
        """Insert a new position record"""
        query = '''
            INSERT INTO positions (
                position_id, symbol, position_type, volume, open_price, current_price,
                sl, tp, status, opened_at, comment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        params = (
            position_data.get('position_id'),
            position_data.get('symbol'),
            position_data.get('position_type'),
            position_data.get('volume'),
            position_data.get('open_price'),
            position_data.get('current_price'),
            position_data.get('sl'),
            position_data.get('tp'),
            position_data.get('status', 'open'),
            position_data.get('opened_at', datetime.now()),
            position_data.get('comment')
        )
        
        return self.execute_insert(query, params)
    
    def update_position(self, position_id: str, update_data: Dict) -> int:
        """Update a position record"""
        set_clauses = []
        params = []
        
        for key, value in update_data.items():
            if key in ['current_price', 'profit_loss', 'commission', 'swap', 
                      'max_profit', 'max_loss', 'current_drawdown', 'status', 'closed_at']:
                set_clauses.append(f"{key} = ?")
                params.append(value)
        
        if not set_clauses:
            return 0
        
        params.append(position_id)
        query = f"UPDATE positions SET {', '.join(set_clauses)}, updated_at = ? WHERE position_id = ?"
        params.append(datetime.now())
        
        return self.execute_update(query, tuple(params))
    
    def insert_arbitrage_opportunity(self, opportunity_data: Dict) -> int:
        """Insert an arbitrage opportunity record"""
        query = '''
            INSERT INTO arbitrage_opportunities (
                triangle, arbitrage_percent, pair1_price, pair2_price, pair3_price,
                spread_acceptable, volatility, market_conditions, ai_decision,
                executed, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        params = (
            json.dumps(opportunity_data.get('triangle', [])),
            opportunity_data.get('arbitrage_percent'),
            opportunity_data.get('pair1_price'),
            opportunity_data.get('pair2_price'),
            opportunity_data.get('pair3_price'),
            opportunity_data.get('spread_acceptable'),
            opportunity_data.get('volatility'),
            json.dumps(opportunity_data.get('market_conditions', {})),
            json.dumps(opportunity_data.get('ai_decision', {})),
            opportunity_data.get('executed', False),
            opportunity_data.get('created_at', datetime.now())
        )
        
        return self.execute_insert(query, params)
    
    def insert_ai_decision(self, decision_data: Dict) -> int:
        """Insert an AI decision record"""
        query = '''
            INSERT INTO ai_decisions (
                decision_type, should_act, confidence, reasoning, fired_rules,
                actions, context, position_size, direction, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        params = (
            decision_data.get('decision_type'),
            decision_data.get('should_act'),
            decision_data.get('confidence'),
            decision_data.get('reasoning'),
            json.dumps(decision_data.get('fired_rules', [])),
            json.dumps(decision_data.get('actions', [])),
            json.dumps(decision_data.get('context', {})),
            decision_data.get('position_size'),
            json.dumps(decision_data.get('direction', {})),
            decision_data.get('created_at', datetime.now())
        )
        
        return self.execute_insert(query, params)
    
    def get_performance_summary(self, days: int = 30) -> Dict:
        """Get performance summary for the last N days"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Get daily performance data
            query = '''
                SELECT 
                    SUM(total_trades) as total_trades,
                    SUM(winning_trades) as winning_trades,
                    SUM(losing_trades) as losing_trades,
                    SUM(total_pnl) as total_pnl,
                    SUM(realized_pnl) as realized_pnl,
                    AVG(win_rate) as avg_win_rate,
                    AVG(profit_factor) as avg_profit_factor,
                    MAX(max_drawdown) as max_drawdown
                FROM daily_performance 
                WHERE date >= ?
            '''
            
            results = self.execute_query(query, (start_date.date(),))
            
            if results and results[0][0] is not None:
                row = results[0]
                return {
                    'total_trades': row[0] or 0,
                    'winning_trades': row[1] or 0,
                    'losing_trades': row[2] or 0,
                    'total_pnl': row[3] or 0,
                    'realized_pnl': row[4] or 0,
                    'avg_win_rate': row[5] or 0,
                    'avg_profit_factor': row[6] or 0,
                    'max_drawdown': row[7] or 0,
                    'period_days': days
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Error getting performance summary: {e}")
            return {}
    
    def get_active_positions(self) -> List[Dict]:
        """Get all active positions"""
        try:
            query = '''
                SELECT * FROM positions 
                WHERE status = 'open' 
                ORDER BY opened_at DESC
            '''
            
            results = self.execute_query(query)
            positions = []
            
            for row in results:
                position = {
                    'id': row[0],
                    'position_id': row[1],
                    'symbol': row[2],
                    'position_type': row[3],
                    'volume': row[4],
                    'open_price': row[5],
                    'current_price': row[6],
                    'sl': row[7],
                    'tp': row[8],
                    'status': row[9],
                    'opened_at': row[10],
                    'closed_at': row[11],
                    'profit_loss': row[12],
                    'commission': row[13],
                    'swap': row[14],
                    'max_profit': row[15],
                    'max_loss': row[16],
                    'current_drawdown': row[17],
                    'comment': row[18]
                }
                positions.append(position)
            
            return positions
            
        except Exception as e:
            self.logger.error(f"Error getting active positions: {e}")
            return []
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old data to save space"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Clean up old logs
            tables_to_clean = [
                'system_logs',
                'error_logs',
                'hourly_performance'
            ]
            
            total_deleted = 0
            
            for table in tables_to_clean:
                query = f"DELETE FROM {table} WHERE timestamp < ?"
                deleted = self.execute_update(query, (cutoff_date,))
                total_deleted += deleted
                self.logger.info(f"Deleted {deleted} old records from {table}")
            
            self.logger.info(f"Cleanup completed: {total_deleted} records deleted")
            return total_deleted
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
            return 0
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        try:
            stats = {
                'database_path': self.db_path,
                'tables': {},
                'total_size_mb': 0
            }
            
            # Get database size
            query = "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()"
            results = self.execute_query(query)
            if results:
                stats['total_size_mb'] = results[0][0] / (1024 * 1024)
            
            # Get table statistics
            tables = [
                'orders', 'positions', 'arbitrage_opportunities', 'correlation_recovery',
                'rule_performance', 'ai_decisions', 'market_patterns', 'learning_data',
                'daily_performance', 'hourly_performance', 'system_metrics',
                'system_logs', 'error_logs'
            ]
            
            for table in tables:
                query = f"SELECT COUNT(*) FROM {table}"
                results = self.execute_query(query)
                if results:
                    stats['tables'][table] = results[0][0]
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}")
            return {}
