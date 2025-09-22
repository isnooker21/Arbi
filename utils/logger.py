"""
ระบบบันทึกข้อมูลและ Logging สำหรับระบบเทรด

ไฟล์นี้ทำหน้าที่:
- บันทึกข้อมูลการเทรดและผลการดำเนินงาน
- จัดการ Log Files แบบหมุนเวียน
- บันทึกข้อมูล AI Decisions และ Arbitrage Opportunities
- สร้างรายงาน Performance และ Statistics
- จัดการการลบ Log เก่าเพื่อประหยัดพื้นที่

ฟีเจอร์หลัก:
- Multi-level Logging: บันทึกข้อมูลหลายระดับ
- Trade Logging: บันทึกข้อมูลการเทรด
- AI Decision Logging: บันทึกการตัดสินใจของ AI
- Performance Logging: บันทึกผลการดำเนินงาน
- Log Rotation: หมุนเวียนไฟล์ Log
"""

import logging
import os
import sys
from datetime import datetime
from typing import Optional
import json

class TradingLogger:
    """Custom logger for the trading system"""
    
    def __init__(self, name: str = "TradingSystem", log_level: str = "INFO"):
        self.name = name
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Setup the logger with appropriate handlers"""
        # Create logs directory
        os.makedirs("logs", exist_ok=True)
        
        # Create logger
        logger = logging.getLogger(self.name)
        logger.setLevel(self.log_level)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # File handler for detailed logs
        file_handler = logging.FileHandler(
            f"logs/{self.name}_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
        
        # Console handler for important messages
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)
        
        # Error file handler
        error_handler = logging.FileHandler(
            f"logs/errors_{datetime.now().strftime('%Y%m%d')}.log"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        logger.addHandler(error_handler)
        
        return logger
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(message, extra=kwargs)
    
    def log_trade(self, trade_data: dict):
        """Log trade information"""
        try:
            trade_log = {
                'timestamp': datetime.now().isoformat(),
                'type': 'trade',
                'data': trade_data
            }
            
            # Log to file
            with open(f"logs/trades_{datetime.now().strftime('%Y%m%d')}.log", "a") as f:
                f.write(json.dumps(trade_log) + "\n")
            
            # Log to console
            self.info(f"Trade: {trade_data.get('symbol', 'Unknown')} "
                     f"{trade_data.get('type', 'Unknown')} "
                     f"{trade_data.get('volume', 0)} @ "
                     f"{trade_data.get('price', 0)}")
            
        except Exception as e:
            self.error(f"Error logging trade: {e}")
    
    def log_arbitrage_opportunity(self, opportunity_data: dict):
        """Log arbitrage opportunity"""
        try:
            arbitrage_log = {
                'timestamp': datetime.now().isoformat(),
                'type': 'arbitrage_opportunity',
                'data': opportunity_data
            }
            
            # Log to file
            with open(f"logs/arbitrage_{datetime.now().strftime('%Y%m%d')}.log", "a") as f:
                f.write(json.dumps(arbitrage_log) + "\n")
            
            # Log to console
            triangle = opportunity_data.get('triangle', [])
            arbitrage_percent = opportunity_data.get('arbitrage_percent', 0)
            self.info(f"Arbitrage Opportunity: {triangle} - {arbitrage_percent:.4f}%")
            
        except Exception as e:
            self.error(f"Error logging arbitrage opportunity: {e}")
    
    def log_ai_decision(self, decision_data: dict):
        """Log AI decision"""
        try:
            decision_log = {
                'timestamp': datetime.now().isoformat(),
                'type': 'ai_decision',
                'data': decision_data
            }
            
            # Log to file
            with open(f"logs/ai_decisions_{datetime.now().strftime('%Y%m%d')}.log", "a") as f:
                f.write(json.dumps(decision_log) + "\n")
            
            # Log to console
            decision_type = decision_data.get('decision_type', 'Unknown')
            should_act = decision_data.get('should_act', False)
            confidence = decision_data.get('confidence', 0)
            self.info(f"AI Decision: {decision_type} - Act: {should_act}, "
                     f"Confidence: {confidence:.2f}")
            
        except Exception as e:
            self.error(f"Error logging AI decision: {e}")
    
    def log_performance(self, performance_data: dict):
        """Log performance metrics"""
        try:
            perf_log = {
                'timestamp': datetime.now().isoformat(),
                'type': 'performance',
                'data': performance_data
            }
            
            # Log to file
            with open(f"logs/performance_{datetime.now().strftime('%Y%m%d')}.log", "a") as f:
                f.write(json.dumps(perf_log) + "\n")
            
        except Exception as e:
            self.error(f"Error logging performance: {e}")
    
    def get_log_files(self) -> list:
        """Get list of log files"""
        try:
            log_files = []
            logs_dir = "logs"
            
            if os.path.exists(logs_dir):
                for filename in os.listdir(logs_dir):
                    if filename.endswith('.log'):
                        filepath = os.path.join(logs_dir, filename)
                        file_stat = os.stat(filepath)
                        log_files.append({
                            'filename': filename,
                            'filepath': filepath,
                            'size_mb': file_stat.st_size / (1024 * 1024),
                            'created': datetime.fromtimestamp(file_stat.st_ctime),
                            'modified': datetime.fromtimestamp(file_stat.st_mtime)
                        })
            
            return sorted(log_files, key=lambda x: x['modified'], reverse=True)
            
        except Exception as e:
            self.error(f"Error getting log files: {e}")
            return []
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Clean up old log files"""
        try:
            import time
            cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
            deleted_count = 0
            
            for log_file in self.get_log_files():
                if log_file['created'].timestamp() < cutoff_time:
                    try:
                        os.remove(log_file['filepath'])
                        deleted_count += 1
                        self.info(f"Deleted old log file: {log_file['filename']}")
                    except Exception as e:
                        self.error(f"Error deleting log file {log_file['filename']}: {e}")
            
            self.info(f"Cleanup completed: {deleted_count} log files deleted")
            return deleted_count
            
        except Exception as e:
            self.error(f"Error cleaning up old logs: {e}")
            return 0


class DatabaseLogger:
    """Logger that writes to database"""
    
    def __init__(self, database_manager):
        self.db = database_manager
        self.logger = logging.getLogger(f"{__name__}.DatabaseLogger")
    
    def log_system_event(self, level: str, message: str, module: str = None, 
                        function_name: str = None, line_number: int = None, 
                        context: dict = None):
        """Log system event to database"""
        try:
            query = '''
                INSERT INTO system_logs 
                (level, message, module, function_name, line_number, timestamp, context)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            '''
            
            params = (
                level,
                message,
                module,
                function_name,
                line_number,
                datetime.now(),
                json.dumps(context) if context else None
            )
            
            self.db.execute_insert(query, params)
            
        except Exception as e:
            self.logger.error(f"Error logging to database: {e}")
    
    def log_error(self, error_type: str, error_message: str, stack_trace: str = None,
                  module: str = None, function_name: str = None, line_number: int = None,
                  context: dict = None):
        """Log error to database"""
        try:
            query = '''
                INSERT INTO error_logs 
                (error_type, error_message, stack_trace, module, function_name, 
                 line_number, timestamp, context)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            params = (
                error_type,
                error_message,
                stack_trace,
                module,
                function_name,
                line_number,
                datetime.now(),
                json.dumps(context) if context else None
            )
            
            self.db.execute_insert(query, params)
            
        except Exception as e:
            self.logger.error(f"Error logging error to database: {e}")


def setup_logging(level: str = "INFO", log_to_database: bool = False, 
                 database_manager = None) -> TradingLogger:
    """Setup logging for the trading system"""
    logger = TradingLogger("TradingSystem", level)
    
    if log_to_database and database_manager:
        db_logger = DatabaseLogger(database_manager)
        
        # Add database handler to root logger
        class DatabaseHandler(logging.Handler):
            def emit(self, record):
                try:
                    db_logger.log_system_event(
                        level=record.levelname,
                        message=record.getMessage(),
                        module=record.module,
                        function_name=record.funcName,
                        line_number=record.lineno,
                        context={'thread': record.thread, 'process': record.process}
                    )
                except Exception:
                    pass
        
        root_logger = logging.getLogger()
        root_logger.addHandler(DatabaseHandler())
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)
