#!/usr/bin/env python3
"""
ระบบเทรด Forex แบบ Triangular Arbitrage ร่วมกับ Correlation Recovery
พร้อม AI Engine และ GUI สำหรับควบคุมระบบ

ไฟล์หลักของระบบเทรดอัตโนมัติที่รวมทุกส่วนเข้าด้วยกัน:
- ระบบตรวจจับ Arbitrage แบบสามเหลี่ยม
- ระบบกู้คืนตำแหน่งด้วย Correlation
- AI Engine ที่ใช้ Rule-based และ Machine Learning
- GUI สำหรับควบคุมและติดตามผลการเทรด
- ระบบจัดการข้อมูลและฐานข้อมูล

ผู้พัฒนา: AI Assistant
เวอร์ชัน: 1.0.0
"""

import sys
import os
import logging
import signal
import threading
import time
from datetime import datetime
from typing import Optional

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import core modules
from trading.broker_api import BrokerAPI
from trading.arbitrage_detector import TriangleArbitrageDetector
from trading.correlation_manager import CorrelationManager
from trading.position_manager import PositionManager
from trading.risk_manager import RiskManager

from ai.rule_engine import RuleEngine
from ai.learning_module import LearningModule
from ai.market_analyzer import MarketAnalyzer
from ai.decision_engine import DecisionEngine

from data.data_feed import RealTimeDataFeed
from data.historical_data import HistoricalDataManager
from data.database import DatabaseManager

from gui.main_window import MainWindow

class TradingSystem:
    """
    ระบบเทรดหลักที่ประสานงานทุกส่วนเข้าด้วยกัน
    
    หน้าที่หลัก:
    - เชื่อมต่อกับ Broker (MetaTrader5, OANDA, FXCM)
    - เริ่มต้นระบบตรวจจับ Arbitrage และ Correlation
    - จัดการ AI Engine และการตัดสินใจ
    - ติดตามผลการเทรดและจัดการความเสี่ยง
    - รายงานสถานะและผลการดำเนินงาน
    """
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.logger.info("Initializing Forex Arbitrage AI Trading System...")
        
        # Initialize components
        self.broker_api = None
        self.risk_manager = None
        self.position_manager = None
        self.arbitrage_detector = None
        self.correlation_manager = None
        self.rule_engine = None
        self.learning_module = None
        self.market_analyzer = None
        self.decision_engine = None
        self.data_feed = None
        self.historical_manager = None
        self.database_manager = None
        
        # System state
        self.is_running = False
        self.is_initialized = False
        self.emergency_stop = False
        
        # Initialize components
        self._initialize_components()
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        self.logger.info("Trading system initialized successfully")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        # Create logs directory
        os.makedirs("logs", exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f"logs/trading_system_{datetime.now().strftime('%Y%m%d')}.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        return logging.getLogger(__name__)
    
    def _initialize_components(self):
        """Initialize all system components"""
        try:
            # Initialize database manager first
            self.database_manager = DatabaseManager()
            self.logger.info("Database manager initialized")
            
            # Initialize historical data manager
            self.historical_manager = HistoricalDataManager()
            self.logger.info("Historical data manager initialized")
            
            # Initialize broker API
            self.broker_api = BrokerAPI()
            self.logger.info("Broker API initialized")
            
            # Initialize risk manager
            self.risk_manager = RiskManager()
            self.logger.info("Risk manager initialized")
            
            # Initialize position manager
            self.position_manager = PositionManager(self.broker_api, self.risk_manager)
            self.logger.info("Position manager initialized")
            
            # Initialize AI components
            self.rule_engine = RuleEngine()
            self.learning_module = LearningModule()
            self.market_analyzer = MarketAnalyzer(self.broker_api)
            self.decision_engine = DecisionEngine(
                self.rule_engine, 
                self.learning_module, 
                self.market_analyzer
            )
            self.logger.info("AI components initialized")
            
            # Initialize trading components
            self.arbitrage_detector = TriangleArbitrageDetector(
                self.broker_api, 
                self.decision_engine
            )
            self.correlation_manager = CorrelationManager(
                self.broker_api, 
                self.decision_engine
            )
            self.logger.info("Trading components initialized")
            
            # Initialize data feed
            self.data_feed = RealTimeDataFeed(self.broker_api)
            self.logger.info("Data feed initialized")
            
            self.is_initialized = True
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
            raise
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def connect_broker(self, broker_type: str = "MetaTrader5", 
                      login: int = None, password: str = None, server: str = None) -> bool:
        """Connect to broker"""
        try:
            if not self.broker_api:
                self.logger.error("Broker API not initialized")
                return False
            
            success = self.broker_api.connect(login, password, server)
            
            if success:
                self.logger.info("Successfully connected to broker")
                
                # Start data feed
                self.data_feed.start()
                
                # Subscribe to data updates
                self.data_feed.subscribe(self._on_data_update, data_type="tick")
                
            else:
                self.logger.error("Failed to connect to broker")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error connecting to broker: {e}")
            return False
    
    def start(self):
        """Start the trading system"""
        try:
            if not self.is_initialized:
                self.logger.error("System not initialized")
                return False
            
            if self.is_running:
                self.logger.warning("Trading system already running")
                return True
            
            if not self.broker_api.is_connected():
                self.logger.error("Not connected to broker")
                return False
            
            self.logger.info("Starting trading system...")
            
            # Start all components
            self.position_manager.start_position_monitoring()
            self.arbitrage_detector.start_detection()
            self.correlation_manager.start_correlation_monitoring()
            
            self.is_running = True
            self.emergency_stop = False
            
            self.logger.info("Trading system started successfully")
            
            # Start main trading loop
            self._trading_loop()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting trading system: {e}")
            return False
    
    def stop(self):
        """Stop the trading system"""
        try:
            if not self.is_running:
                self.logger.warning("Trading system not running")
                return
            
            self.logger.info("Stopping trading system...")
            
            # Stop all components
            if self.arbitrage_detector:
                self.arbitrage_detector.stop_detection()
            
            if self.correlation_manager:
                self.correlation_manager.stop_correlation_monitoring()
            
            if self.position_manager:
                self.position_manager.stop_position_monitoring()
            
            if self.data_feed:
                self.data_feed.stop()
            
            self.is_running = False
            
            self.logger.info("Trading system stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping trading system: {e}")
    
    def emergency_stop(self):
        """Emergency stop all trading activities"""
        try:
            self.logger.critical("EMERGENCY STOP ACTIVATED")
            
            self.emergency_stop = True
            
            # Stop all trading
            self.stop()
            
            # Close all positions
            if self.position_manager:
                closed_count = self.position_manager.close_all_positions("emergency_stop")
                self.logger.info(f"Closed {closed_count} positions due to emergency stop")
            
            # Disconnect from broker
            if self.broker_api:
                self.broker_api.disconnect()
            
            self.logger.critical("Emergency stop completed")
            
        except Exception as e:
            self.logger.error(f"Error during emergency stop: {e}")
    
    def _trading_loop(self):
        """Main trading loop"""
        try:
            while self.is_running and not self.emergency_stop:
                try:
                    # Update market analysis
                    if self.market_analyzer:
                        market_conditions = self.market_analyzer.analyze_market_conditions()
                    
                    # Check risk management
                    if self.risk_manager and self.risk_manager.should_stop_trading():
                        self.logger.warning("Risk management triggered - stopping trading")
                        self.stop()
                        break
                    
                    # Update performance tracking
                    self._update_performance_tracking()
                    
                    # Sleep for 1 second
                    time.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"Error in trading loop: {e}")
                    time.sleep(5)
            
        except Exception as e:
            self.logger.error(f"Error in main trading loop: {e}")
    
    def _on_data_update(self, data: dict):
        """Handle real-time data updates"""
        try:
            # Update market analyzer with new data
            if self.market_analyzer:
                # This could trigger market analysis updates
                pass
            
            # Log significant price movements
            for symbol, tick_data in data.items():
                if 'bid' in tick_data:
                    # Could add price movement detection here
                    pass
            
        except Exception as e:
            self.logger.error(f"Error handling data update: {e}")
    
    def _update_performance_tracking(self):
        """Update performance tracking metrics"""
        try:
            if not self.database_manager:
                return
            
            # Get current performance data
            if self.position_manager:
                position_summary = self.position_manager.get_position_summary()
                
                # Update database with current metrics
                # This would typically update hourly performance records
                pass
            
        except Exception as e:
            self.logger.error(f"Error updating performance tracking: {e}")
    
    def get_system_status(self) -> dict:
        """Get current system status"""
        try:
            status = {
                'is_running': self.is_running,
                'is_initialized': self.is_initialized,
                'emergency_stop': self.emergency_stop,
                'broker_connected': self.broker_api.is_connected() if self.broker_api else False,
                'components': {
                    'arbitrage_detector': self.arbitrage_detector is not None,
                    'correlation_manager': self.correlation_manager is not None,
                    'position_manager': self.position_manager is not None,
                    'ai_engine': self.decision_engine is not None,
                    'data_feed': self.data_feed is not None
                }
            }
            
            # Add component-specific status
            if self.position_manager:
                position_summary = self.position_manager.get_position_summary()
                status['active_positions'] = position_summary.get('active_positions', 0)
                status['total_pnl'] = position_summary.get('total_pnl', 0)
            
            if self.arbitrage_detector:
                triangle_performance = self.arbitrage_detector.get_triangle_performance()
                status['active_triangles'] = triangle_performance.get('active_triangles', 0)
            
            if self.correlation_manager:
                correlation_performance = self.correlation_manager.get_correlation_performance()
                status['active_recoveries'] = correlation_performance.get('active_recoveries', 0)
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {}
    
    def get_performance_summary(self) -> dict:
        """Get performance summary"""
        try:
            if not self.database_manager:
                return {}
            
            return self.database_manager.get_performance_summary(days=30)
            
        except Exception as e:
            self.logger.error(f"Error getting performance summary: {e}")
            return {}


def main():
    """Main application entry point"""
    try:
        print("=" * 60)
        print("Forex Arbitrage AI Trading System")
        print("Version 1.0.0")
        print("=" * 60)
        
        # Check if running in GUI mode or command line mode
        if len(sys.argv) > 1 and sys.argv[1] == '--gui':
            # Run GUI mode
            print("Starting GUI mode...")
            app = MainWindow()
            app.run()
        else:
            # Run command line mode
            print("Starting command line mode...")
            print("Use --gui flag to start GUI mode")
            
            # Initialize trading system
            trading_system = TradingSystem()
            
            # Connect to broker (you would need to provide credentials)
            print("Please configure broker credentials in config/broker_config.json")
            print("Then run with --gui flag to use the GUI interface")
            
            # Example of how to connect (uncomment and modify as needed)
            # success = trading_system.connect_broker(
            #     broker_type="MetaTrader5",
            #     login=123456,
            #     password="your_password",
            #     server="YourBroker-Server"
            # )
            # 
            # if success:
            #     trading_system.start()
            # else:
            #     print("Failed to connect to broker")
    
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
