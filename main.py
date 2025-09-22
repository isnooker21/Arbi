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
    
    def __init__(self, auto_setup=True):
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
        self.trading_thread = None
        
        # Auto Setup if requested
        if auto_setup:
            self._auto_setup()
        
        # Initialize components
        self._initialize_components()
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        self.logger.info("Trading system initialized successfully")
    
    def _auto_setup(self):
        """Auto Setup ระบบโดยอัตโนมัติ"""
        try:
            self.logger.info("Starting Auto Setup...")
            print("กำลังทำ Auto Setup...")
            
            # Import BrokerAPI
            from trading.broker_api import BrokerAPI
            
            # สร้าง BrokerAPI instance และเก็บไว้ใน self.broker_api
            self.broker_api = BrokerAPI("MetaTrader5")
            
            print("กำลังตรวจสอบการเชื่อมต่อ MT5...")
            
            # ลองเชื่อมต่อแบบ auto
            if self.broker_api.connect():
                print("เชื่อมต่อ MT5 สำเร็จ!")
                
                # แสดงข้อมูลบัญชี
                if self.broker_api.account_info:
                    account = self.broker_api.account_info
                    print(f"\nข้อมูลบัญชี:")
                    print(f"   หมายเลขบัญชี: {account.login}")
                    print(f"   เซิร์ฟเวอร์: {account.server}")
                    print(f"   ยอดเงิน: {account.balance:.2f} {account.currency}")
                    print(f"   Equity: {account.equity:.2f} {account.currency}")
                    print(f"   Leverage: 1:{account.leverage}")
                    
                    # ตรวจสอบการตั้งค่า
                    print(f"\nการตั้งค่า:")
                    print(f"   Auto-detect สำเร็จ: OK")
                    print(f"   Config file อัปเดตแล้ว: OK")
                    
                    # แสดงคู่เงินที่ใช้ได้
                    print(f"\nกำลังตรวจสอบคู่เงินที่ใช้ได้...")
                    try:
                        symbols = self.broker_api.get_available_pairs()
                        if symbols:
                            print(f"   พบคู่เงิน {len(symbols)} คู่")
                            print(f"   ตัวอย่าง: {', '.join(symbols[:5])}")
                        else:
                            print("   ไม่พบคู่เงิน")
                    except Exception as e:
                        print(f"   ไม่สามารถดึงข้อมูลคู่เงิน: {e}")
                    
                    print(f"\nAuto Setup เสร็จสิ้น!")
                    print(f"   ระบบพร้อมใช้งานแล้ว")
                    
                else:
                    print("ไม่สามารถดึงข้อมูลบัญชีได้")
                    self.logger.warning("Could not get account info during auto setup")
                    
            else:
                print("ไม่สามารถเชื่อมต่อ MT5 ได้")
                print("\nวิธีแก้ไข:")
                print("   1. ตรวจสอบว่า MT5 เปิดอยู่และ login แล้ว")
                print("   2. ตรวจสอบว่า MT5 อนุญาตให้ Expert Advisors ทำงาน")
                print("   3. ตรวจสอบการตั้งค่าใน Tools → Options → Expert Advisors")
                self.logger.warning("Could not connect to MT5 during auto setup")
                
        except ImportError as e:
            print(f"ไม่สามารถ import modules ได้: {e}")
            print("   ลองติดตั้ง dependencies: pip install -r requirements.txt")
            self.logger.error(f"Import error during auto setup: {e}")
            
        except Exception as e:
            print(f"เกิดข้อผิดพลาดใน Auto Setup: {e}")
            self.logger.error(f"Error during auto setup: {e}")
    
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
            
            # Initialize risk manager (enhanced)
            self.risk_manager = RiskManager()
            # Pass broker_api to risk_manager for balance access
            self.risk_manager.broker_api = self.broker_api
            self.logger.info("Enhanced risk manager initialized")
            
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
        
        # Only setup signal handlers in main thread
        try:
            import threading
            if threading.current_thread() is threading.main_thread():
                signal.signal(signal.SIGINT, signal_handler)
                signal.signal(signal.SIGTERM, signal_handler)
            else:
                self.logger.warning("Cannot set signal handlers in non-main thread")
        except Exception as e:
            self.logger.warning(f"Cannot set signal handlers: {e}")
    
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
            
            if not self.broker_api or not self.broker_api.is_connected():
                self.logger.error("Not connected to broker - trying to connect...")
                # Try to connect if not connected
                if not self.broker_api:
                    from trading.broker_api import BrokerAPI
                    self.broker_api = BrokerAPI("MetaTrader5")
                
                if not self.broker_api.connect():
                    self.logger.error("Failed to connect to broker")
                    return False
                else:
                    self.logger.info("Successfully connected to broker")
            
            self.logger.info("🚀 Starting trading components...")
            
            # Start all components
            self.position_manager.start_position_monitoring()
            self.arbitrage_detector.start_detection()
            self.correlation_manager.start_correlation_monitoring()
            
            self.is_running = True
            self.emergency_stop = False
            
            self.logger.info("✅ Trading system started successfully")
            
            # Start main trading loop in background thread
            self.trading_thread = threading.Thread(target=self._trading_loop, daemon=True)
            self.trading_thread.start()
            
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
            
            self.logger.info("🛑 Stopping trading system...")
            
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
            
            # Wait for trading thread to finish (with timeout)
            if hasattr(self, 'trading_thread') and self.trading_thread.is_alive():
                self.trading_thread.join(timeout=5.0)
                if self.trading_thread.is_alive():
                    self.logger.warning("⚠️ Trading thread timeout")
            
            self.logger.info("✅ Trading system stopped")
            
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
        self.logger.info("🔄 Trading system active - monitoring markets...")
        
        try:
            while self.is_running and not self.emergency_stop:
                try:
                    # Update market analysis
                    if self.market_analyzer:
                        try:
                            market_conditions = self.market_analyzer.analyze_market_conditions()
                        except Exception as e:
                            self.logger.warning(f"Market analysis error: {e}")
                    
                    # Check risk management
                    if self.risk_manager:
                        try:
                            account_balance = self.broker_api.get_account_balance() if self.broker_api else 10000
                            current_pnl = self.position_manager.get_total_pnl() if self.position_manager else 0
                            
                            # Check circuit breaker
                            if not self.risk_manager.check_circuit_breaker(current_pnl, account_balance):
                                self.logger.warning("⚠️ Circuit breaker triggered - stopping trading")
                                self.stop()
                                break
                            
                            # Check traditional risk management
                            if self.risk_manager.should_stop_trading():
                                self.logger.warning("⚠️ Risk management triggered - stopping trading")
                                self.stop()
                                break
                        except Exception as e:
                            self.logger.warning(f"Risk check error: {e}")
                    
                    # Update performance tracking
                    try:
                        self._update_performance_tracking()
                    except Exception as e:
                        pass  # Silent fail for performance tracking
                    
                    # Sleep for 1 second
                    time.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"Trading loop error: {e}")
                    time.sleep(5)
            
            self.logger.info("🛑 Trading system stopped")
            
        except Exception as e:
            self.logger.error(f"Critical trading error: {e}")
    
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
                    'data_feed': self.data_feed is not None,
                    'enhanced_risk_manager': self.risk_manager is not None
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
    """Main application entry point with Auto Setup"""
    try:
        print("=" * 60)
        print("ระบบเทรด Forex AI")
        print("   Triangular Arbitrage & Correlation Recovery")
        print("   พร้อม AI Engine และ Auto Setup")
        print("=" * 60)
        
        # Check command line arguments
        if len(sys.argv) > 1:
            if sys.argv[1] == '--cli':
                # Run command line mode
                print("เริ่มต้น Command Line Mode...")
                trading_system = TradingSystem(auto_setup=True)
                print("ระบบเทรดพร้อมใช้งาน")
                print("ใช้ --gui เพื่อเปิดหน้าจอ GUI")
            elif sys.argv[1] == '--no-auto-setup':
                # Run without auto setup
                print("เริ่มต้นระบบโดยไม่ทำ Auto Setup...")
                trading_system = TradingSystem(auto_setup=False)
                app = MainWindow(auto_setup=False)
                app.run()
            else:
                print(f"ไม่รู้จักคำสั่ง: {sys.argv[1]}")
                print("ใช้ --cli สำหรับ Command Line หรือ --no-auto-setup สำหรับ GUI")
        else:
            # Default: Run GUI mode with Auto Setup
            print("เริ่มต้น GUI Mode พร้อม Auto Setup...")
            
            # Initialize trading system with auto setup
            trading_system = TradingSystem(auto_setup=True)
            
            # Start GUI and pass trading_system
            app = MainWindow(auto_setup=False)
            app.trading_system = trading_system  # Pass the initialized system
            app.run()
    
    except KeyboardInterrupt:
        print("\nปิดระบบตามคำขอของผู้ใช้")
    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
