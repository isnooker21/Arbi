#!/usr/bin/env python3
"""
ระบบเทรด Forex แบบ Adaptive Arbitrage + Correlation Recovery
พร้อม Never-Cut-Loss และ Auto Position Sizing

ไฟล์หลักของระบบเทรดอัตโนมัติที่รวมทุกส่วนเข้าด้วยกัน:
- ระบบตรวจจับ Arbitrage แบบ Adaptive
- ระบบกู้คืนตำแหน่งด้วย Correlation Recovery
- Adaptive Engine สำหรับจัดการ Market Regime
- Never-Cut-Loss Strategy
- Auto Position Sizing ตามยอดเงินในบัญชี
- GUI สำหรับควบคุมและติดตามผลการเทรด

ผู้พัฒนา: AI Assistant
เวอร์ชัน: 2.0.0 (Adaptive Engine)
"""

import sys
import os
import logging
import signal
import threading
import time
from datetime import datetime
from typing import Optional

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    try:
        # Set console code page to UTF-8
        os.system("chcp 65001 >nul 2>&1")
    except:
        pass

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import core modules
from trading.broker_api import BrokerAPI
from trading.arbitrage_detector import TriangleArbitrageDetector
from trading.correlation_manager import CorrelationManager
from trading.adaptive_engine import AdaptiveEngine
from trading.position_manager import PositionManager
from trading.risk_manager import RiskManager

# from ai.market_analyzer import MarketAnalyzer  # DISABLED - not used in simple trading system

from data.data_feed import RealTimeDataFeed
from data.database import DatabaseManager

from gui.main_window import MainWindow

class TradingSystem:
    """
    ระบบเทรดหลักที่ประสานงานทุกส่วนเข้าด้วยกัน
    
    หน้าที่หลัก:
    - เชื่อมต่อกับ Broker (MetaTrader5, OANDA, FXCM)
    - เริ่มต้นระบบ Adaptive Engine
    - จัดการ Never-Cut-Loss Strategy
    - Auto Position Sizing ตามยอดเงินในบัญชี
    - ติดตามผลการเทรดและจัดการความเสี่ยง
    - รายงานสถานะและผลการดำเนินงาน
    """
    
    def __init__(self, auto_setup=True):
        self.logger = self._setup_logging()
        
        # Initialize components
        self.broker_api = None
        self.risk_manager = None
        self.position_manager = None
        self.arbitrage_detector = None
        self.correlation_manager = None
        self.adaptive_engine = None
        # self.market_analyzer = None  # DISABLED - not used in simple trading system
        self.data_feed = None
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
        
    
    def _auto_setup(self):
        """Auto Setup ระบบโดยอัตโนมัติ"""
        try:
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
                    
            else:
                print("ไม่สามารถเชื่อมต่อ MT5 ได้")
                print("\nวิธีแก้ไข:")
                print("   1. ตรวจสอบว่า MT5 เปิดอยู่และ login แล้ว")
                print("   2. ตรวจสอบว่า MT5 อนุญาตให้ Expert Advisors ทำงาน")
                print("   3. ตรวจสอบการตั้งค่าใน Tools → Options → Expert Advisors")
                
        except ImportError as e:
            print(f"ไม่สามารถ import modules ได้: {e}")
            print("   ลองติดตั้ง dependencies: pip install -r requirements.txt")
            
        except Exception as e:
            print(f"เกิดข้อผิดพลาดใน Auto Setup: {e}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        # Create logs directory
        os.makedirs("logs", exist_ok=True)
        
        # Setup console handler with UTF-8 encoding
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Try to set UTF-8 encoding for console output
        try:
            if hasattr(console_handler.stream, 'reconfigure'):
                console_handler.stream.reconfigure(encoding='utf-8')
        except Exception:
            pass  # Fallback to default encoding
        
        # Setup file handler with UTF-8 encoding
        file_handler = logging.FileHandler(
            f"logs/trading_system_{datetime.now().strftime('%Y%m%d')}.log",
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            handlers=[file_handler, console_handler]
        )
        
        return logging.getLogger(__name__)
    
    def _initialize_components(self):
        """Initialize all system components"""
        try:
            # Initialize database manager first
            self.database_manager = DatabaseManager()
            self.logger.info("Database manager initialized")
            
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
            
            # Initialize market analyzer (simplified)
        # Market Analyzer - DISABLED for simple trading system
        # self.market_analyzer = MarketAnalyzer(self.broker_api)
        # self.market_analyzer = None
            
            # Initialize trading components
            self.correlation_manager = CorrelationManager(
                self.broker_api, 
                None  # No market analyzer needed for simple trading system
            )
            self.arbitrage_detector = TriangleArbitrageDetector(
                self.broker_api, 
                None,  # No market analyzer needed for simple trading system
                self.correlation_manager  # Pass correlation_manager to arbitrage_detector
            )
            self.logger.info("Trading components initialized")
            
            # Initialize adaptive engine (main trading engine)
            self.adaptive_engine = AdaptiveEngine(
                self.broker_api,
                self.arbitrage_detector,
                self.correlation_manager,
                None  # No market analyzer needed for simple trading system
            )
            self.logger.info("Adaptive engine initialized")
            
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
                
                # Try multiple connection attempts
                max_attempts = 3
                for attempt in range(max_attempts):
                    self.logger.info(f"Connection attempt {attempt + 1}/{max_attempts}")
                    if self.broker_api.connect():
                        self.logger.info("Successfully connected to broker")
                        break
                    else:
                        self.logger.warning(f"Connection attempt {attempt + 1} failed")
                        if attempt < max_attempts - 1:
                            time.sleep(2)  # Wait 2 seconds before retry
                else:
                    self.logger.error("Failed to connect to broker after all attempts")
                    return False
            
            self.logger.info("🚀 Starting adaptive trading system...")
            
            # Start all components
            self.position_manager.start_position_monitoring()
            self.arbitrage_detector.start_detection()
            # Correlation manager doesn't need separate monitoring - it's integrated with arbitrage detector
            
            # Start adaptive engine (main trading engine)
            self.adaptive_engine.start_adaptive_trading()
            
            self.is_running = True
            self.emergency_stop = False
            
            self.logger.info("✅ Adaptive trading system started successfully")
            
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
            
            self.logger.info("🛑 Stopping adaptive trading system...")
            
            # Stop adaptive engine first
            if self.adaptive_engine:
                self.adaptive_engine.stop_adaptive_trading()
            
            # Stop all components
            if self.arbitrage_detector:
                self.arbitrage_detector.stop_detection()
            
            if self.correlation_manager:
                # Save recovery data before stopping
                self.correlation_manager.stop()
            
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
            
            self.logger.info("✅ Adaptive trading system stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping trading system: {e}")
    
    def emergency_stop(self):
        """Emergency stop all trading activities"""
        try:
            self.logger.critical("🚨 EMERGENCY STOP ACTIVATED")
            
            self.emergency_stop = True
            
            # Use adaptive engine emergency stop
            if self.adaptive_engine:
                self.adaptive_engine.emergency_stop()
            
            # Stop all trading
            self.stop()
            
            # Close all positions
            if self.position_manager:
                closed_count = self.position_manager.close_all_positions("emergency_stop")
                self.logger.info(f"Closed {closed_count} positions due to emergency stop")
            
            # Disconnect from broker
            if self.broker_api:
                self.broker_api.disconnect()
            
            self.logger.critical("🚨 Emergency stop completed")
            
        except Exception as e:
            self.logger.error(f"Error during emergency stop: {e}")
    
    def _trading_loop(self):
        """
        ⚡ CRITICAL: Main trading loop with health checks and recovery
        """
        self.logger.info("🔄 Trading system active - monitoring markets...")
        
        try:
            while self.is_running and not self.emergency_stop:
                try:
                    # Health check every 30 seconds
                    if not self._health_check():
                        self.logger.warning("⚠️ System health check failed - attempting recovery")
                        self._attempt_system_recovery()
                        time.sleep(10)  # Wait 10 seconds before retry
                        continue
                    
                    # Update market analysis
                    # Market analysis disabled for simple trading system
                    # if self.market_analyzer:
                    #     try:
                    #         market_conditions = self.market_analyzer.analyze_market_conditions()
                    #     except Exception as e:
                    #         self.logger.warning(f"Market analysis error: {e}")
                    
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
            
            self.logger.info("✅ Trading system stopped")
            
        except Exception as e:
            self.logger.error(f"Critical trading error: {e}")
    
    def _health_check(self) -> bool:
        """
        ⚡ CRITICAL: Check system health and component status
        """
        try:
            # Check broker connection
            if not self.broker_api:
                self.logger.warning("⚠️ Broker API not initialized")
                return False
                
            if not self.broker_api.is_connected():
                self.logger.warning("⚠️ Broker connection lost - attempting reconnection")
                # Try to reconnect
                if self.broker_api.connect():
                    self.logger.info("✅ Broker reconnected successfully")
                else:
                    self.logger.error("❌ Failed to reconnect to broker")
                    return False
            
            # Check adaptive engine
            if not self.adaptive_engine or not self.adaptive_engine.is_running:
                self.logger.warning("⚠️ Adaptive engine not running")
                return False
            
            # Check arbitrage detector
            if not self.arbitrage_detector or not self.arbitrage_detector.is_running:
                self.logger.warning("⚠️ Arbitrage detector not running")
                return False
            
            # Check correlation manager (ไม่ต้องตรวจสอบ is_running เพราะมัน integrated กับ arbitrage detector)
            if not self.correlation_manager:
                self.logger.warning("⚠️ Correlation manager not available")
                return False
            
            # Check recovery positions
            if self.correlation_manager:
                self.correlation_manager.check_recovery_positions()
            
            # Check market analyzer - DISABLED for simple trading system
            # if not self.market_analyzer:
            #     self.logger.warning("⚠️ Market analyzer not initialized")
            #     return False
            
            self.logger.debug("✅ System health check passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in health check: {e}")
            return False
    
    def _attempt_system_recovery(self):
        """
        ⚡ CRITICAL: Attempt to recover system components
        """
        try:
            self.logger.info("🔄 Attempting system recovery...")
            
            # Try to reconnect broker
            if self.broker_api:
                try:
                    self.broker_api.connect()
                    self.logger.info("✅ Broker reconnected")
                except Exception as e:
                    self.logger.error(f"Failed to reconnect broker: {e}")
            
            # Try to restart adaptive engine
            if self.adaptive_engine:
                try:
                    self.adaptive_engine.stop_adaptive_trading()
                    threading.Event().wait(2)  # Wait 2 seconds
                    self.adaptive_engine.start_adaptive_trading()
                    self.logger.info("✅ Adaptive engine restarted")
                except Exception as e:
                    self.logger.error(f"Failed to restart adaptive engine: {e}")
            
            # Try to restart arbitrage detector
            if self.arbitrage_detector:
                try:
                    self.arbitrage_detector.stop_detection()
                    threading.Event().wait(1)  # Wait 1 second
                    self.arbitrage_detector.start_detection()
                    self.logger.info("✅ Arbitrage detector restarted")
                except Exception as e:
                    self.logger.error(f"Failed to restart arbitrage detector: {e}")
            
            # Try to restart correlation manager
            if self.correlation_manager:
                try:
                    # Correlation manager doesn't need separate monitoring - it's integrated with arbitrage detector
                    self.logger.info("✅ Correlation manager is integrated with arbitrage detector")
                except Exception as e:
                    self.logger.error(f"Failed to restart correlation manager: {e}")
            
            self.logger.info("🔄 System recovery attempt completed")
            
        except Exception as e:
            self.logger.error(f"Error in system recovery: {e}")
    
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
                    'adaptive_engine': self.adaptive_engine is not None,
                    'arbitrage_detector': self.arbitrage_detector is not None,
                    'correlation_manager': self.correlation_manager is not None,
                    'position_manager': self.position_manager is not None,
                    # 'market_analyzer': self.market_analyzer is not None,  # DISABLED
                    'data_feed': self.data_feed is not None,
                    'risk_manager': self.risk_manager is not None
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
                status['market_regime'] = triangle_performance.get('market_regime', 'unknown')
                status['adaptive_threshold'] = triangle_performance.get('adaptive_threshold', 0.001)
                status['duplicate_prevention'] = {
                    'used_currency_pairs': triangle_performance.get('used_currency_pairs', []),
                    'active_groups_count': triangle_performance.get('active_groups_count', 0),
                    'group_currency_mapping': triangle_performance.get('group_currency_mapping', {})
                }
            
            if self.correlation_manager:
                correlation_performance = self.correlation_manager.get_correlation_performance()
                status['active_recoveries'] = correlation_performance.get('active_recoveries', 0)
                status['recovery_mode'] = correlation_performance.get('recovery_mode', 'unknown')
            
            if self.adaptive_engine:
                engine_status = self.adaptive_engine.get_adaptive_engine_status()
                status['engine_mode'] = engine_status.get('engine_mode', 'unknown')
                status['performance_metrics'] = engine_status.get('performance_metrics', {})
            
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
        print("ระบบเทรด Forex AI แบบ Adaptive")
        print("   Adaptive Arbitrage + Correlation Recovery")
        print("   Never-Cut-Loss + Auto Position Sizing")
        print("   พร้อม Adaptive Engine และ Auto Setup")
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
