"""
ระบบเชื่อมต่อกับ Broker สำหรับการเทรด

ไฟล์นี้ทำหน้าที่:
- เชื่อมต่อกับ Broker ต่างๆ (MetaTrader5, OANDA, FXCM)
- รับข้อมูลราคาและข้อมูลบัญชี
- ส่งคำสั่งซื้อ/ขาย
- จัดการตำแหน่งและคำสั่ง
- ตรวจสอบสถานะการเชื่อมต่อ

ฟีเจอร์หลัก:
- Multi-Broker Support: รองรับ Broker หลายราย
- Real-time Data: รับข้อมูลราคาแบบเรียลไทม์
- Order Management: จัดการคำสั่งซื้อ/ขาย
- Position Tracking: ติดตามตำแหน่งที่เปิดอยู่
- Error Handling: จัดการข้อผิดพลาด
"""

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("⚠️ MetaTrader5 not available - using fallback mode")

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import json
import os
import time
import sys

# Import SymbolMapper
try:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if PROJECT_ROOT not in sys.path:
        sys.path.append(PROJECT_ROOT)
    from utils.symbol_mapper import SymbolMapper
except ImportError:
    SymbolMapper = None
    print("⚠️ SymbolMapper not available - using direct symbol names")

class BrokerAPI:
    def __init__(self, broker_type: str = "MetaTrader5", config_file: str = "config/broker_config.json"):
        self.broker_type = broker_type
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_file)
        self._connected = False
        self.account_info = None
        
        # 🆕 Initialize SymbolMapper
        self.symbol_mapper = SymbolMapper() if SymbolMapper else None
        if self.symbol_mapper:
            self.logger.info("✅ SymbolMapper initialized in BrokerAPI")
        
    def _load_config(self, config_file: str) -> Dict:
        """Load broker configuration from JSON file"""
        try:
            # ใช้ไฟล์ config โดยตรง
            cfg_path = config_file
            with open(cfg_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading broker config: {e}")
            return {}
    
    def connect(self, login: int = None, password: str = None, server: str = None) -> bool:
        """Connect to broker with auto-detection"""
        try:
            if self.broker_type == "MetaTrader5":
                # Try auto-connect first
                if self._auto_connect_mt5():
                    return True
                # Fallback to manual connection
                return self._connect_mt5(login, password, server)
            elif self.broker_type == "OANDA":
                return self._connect_oanda(login, password, server)
            elif self.broker_type == "FXCM":
                return self._connect_fxcm(login, password, server)
            else:
                self.logger.error(f"Unsupported broker type: {self.broker_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error connecting to broker: {e}")
            return False
    
    def _auto_connect_mt5(self) -> bool:
        """Auto-connect to MT5 using existing terminal connection"""
        try:
            # Initialize MT5
            if not mt5.initialize():
                self.logger.error("MT5 initialization failed")
                return False
            
            # Check if already connected
            account_info = mt5.account_info()
            if account_info is not None:
                self.logger.info("✅ MT5 already connected - using existing connection")
                self.account_info = account_info
                self._connected = True
                
                # Auto-detect and save config
                self.auto_detect_mt5_config()
                
                self.logger.info(f"📊 MT5 Connected - Account: {account_info.login}, "
                               f"Server: {account_info.server}, Balance: {account_info.balance}")
                return True
            
            # Try to connect using terminal's connection
            self.logger.info("🔌 Attempting to connect using MT5 terminal connection...")
            if mt5.login():
                account_info = mt5.account_info()
                if account_info is not None:
                    self.account_info = account_info
                    self._connected = True
                    
                    # Auto-detect and save config
                    self.auto_detect_mt5_config()
                    
                    self.logger.info(f"✅ MT5 Connected - Account: {account_info.login}, "
                                   f"Server: {account_info.server}, Balance: {account_info.balance}")
                    return True
            
            # Try to connect with config credentials (if password is provided)
            mt5_config = self.config.get('MetaTrader5', {})
            if mt5_config.get('login') and mt5_config.get('server'):
                password = mt5_config.get('password', '')
                if password and password.strip():
                    self.logger.info("Attempting to connect with config credentials...")
                    if self._connect_with_credentials():
                        return True
                else:
                    self.logger.warning("No valid credentials provided for MT5 connection")
            
            self.logger.warning("Could not auto-connect to MT5 - will try manual connection")
            return False
            
        except Exception as e:
            self.logger.error(f"Error in auto-connect MT5: {e}")
            return False
    
    def _connect_with_credentials(self) -> bool:
        """Connect to MT5 using credentials from config"""
        try:
            mt5_config = self.config.get('MetaTrader5', {})
            login = mt5_config.get('login')
            password = mt5_config.get('password')
            server = mt5_config.get('server')
            timeout = mt5_config.get('timeout', 30000)
            
            if not all([login, password, server]):
                self.logger.error("Missing MT5 credentials in config")
                return False
            
            # Attempt to login
            if mt5.login(login, password=password, server=server, timeout=timeout):
                account_info = mt5.account_info()
                if account_info:
                    self.account_info = account_info
                    self._connected = True
                    self.logger.info(f"Successfully connected to MT5 - Account: {account_info.login}, "
                                   f"Server: {account_info.server}, Balance: {account_info.balance}")
                    return True
                else:
                    self.logger.error("Login successful but no account info received")
                    return False
            else:
                error_code = mt5.last_error()
                self.logger.error(f"MT5 login failed with error code: {error_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error connecting with credentials: {e}")
            return False
    
    def auto_detect_mt5_config(self) -> bool:
        """Auto-detect MT5 configuration and update config file"""
        try:
            if not mt5.initialize():
                self.logger.error("MT5 initialization failed")
                return False
            
            account_info = mt5.account_info()
            if account_info is None:
                self.logger.warning("No MT5 account info available for auto-detection")
                return False
            
            # Update config with detected information
            config = self.config.get('MetaTrader5', {})
            config['login'] = account_info.login
            config['server'] = account_info.server
            config['timeout'] = 30000
            config['portable'] = False
            
            # Update the config
            self.config['MetaTrader5'] = config
            
            # Save to file
            self._save_config()
            
            self.logger.info(f"Auto-detected MT5 config - Account: {account_info.login}, "
                           f"Server: {account_info.server}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error auto-detecting MT5 config: {e}")
            return False
    
    def _save_config(self):
        """Save current config to file"""
        try:
            # บันทึกไฟล์ config โดยตรง
            save_path = 'config/broker_config.json'
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.logger.info(f"Config file updated successfully: {save_path}")
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
    
    def _connect_mt5(self, login: int = None, password: str = None, server: str = None) -> bool:
        """Connect to MetaTrader5 with auto-detection"""
        try:
            # Initialize MT5
            if not mt5.initialize():
                self.logger.error("MT5 initialization failed")
                return False
            
            # Try to get account info first (if already logged in)
            account_info = mt5.account_info()
            if account_info is not None:
                self.logger.info("MT5 already connected - using existing connection")
                self.account_info = account_info
                self._connected = True
                self.logger.info(f"Using existing MT5 connection - Account: {account_info.login}, "
                               f"Balance: {account_info.balance}")
                return True
            
            # If not connected, try to login with provided credentials
            config = self.config.get('MetaTrader5', {})
            login = login or config.get('login', 0)
            password = password or config.get('password', '')
            server = server or config.get('server', '')
            
            # If no credentials provided, try to get from MT5 terminal
            if login == 0 or not password or not server:
                self.logger.info("No credentials provided - attempting to use MT5 terminal connection")
                # Try to connect without explicit login (use terminal's connection)
                if mt5.login():
                    account_info = mt5.account_info()
                    if account_info is not None:
                        self.account_info = account_info
                        self._connected = True
                        self.logger.info(f"Connected using MT5 terminal - Account: {account_info.login}, "
                                       f"Balance: {account_info.balance}")
                        return True
            
            # If explicit login is needed
            if login and password and server:
                if not mt5.login(login, password=password, server=server):
                    self.logger.error(f"MT5 login failed: {mt5.last_error()}")
                    return False
                
                # Get account info
                self.account_info = mt5.account_info()
                if self.account_info is None:
                    self.logger.error("Failed to get account info")
                    return False
                
                self._connected = True
                self.logger.info(f"Connected to MT5 - Account: {self.account_info.login}, "
                               f"Balance: {self.account_info.balance}")
                return True
            else:
                self.logger.error("No valid credentials provided for MT5 connection")
                return False
            
        except Exception as e:
            self.logger.error(f"Error connecting to MT5: {e}")
            return False
    
    def _connect_oanda(self, account_id: str = None, access_token: str = None, environment: str = None) -> bool:
        """Connect to OANDA (placeholder implementation)"""
        try:
            # This would be implemented with oandapyV20
            self.logger.info("OANDA connection not implemented yet")
            return False
            
        except Exception as e:
            self.logger.error(f"Error connecting to OANDA: {e}")
            return False
    
    def _connect_fxcm(self, username: str = None, password: str = None, environment: str = None) -> bool:
        """Connect to FXCM (placeholder implementation)"""
        try:
            # This would be implemented with FXCM API
            self.logger.info("FXCM connection not implemented yet")
            return False
            
        except Exception as e:
            self.logger.error(f"Error connecting to FXCM: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from broker"""
        try:
            if self.broker_type == "MetaTrader5":
                mt5.shutdown()
            
            self._connected = False
            self.account_info = None
            self.logger.info("Disconnected from broker")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting: {e}")
    
    def get_account_info(self) -> Optional[Dict]:
        """Get account information"""
        try:
            if not self._connected:
                return None
            
            if self.broker_type == "MetaTrader5":
                account = mt5.account_info()
                if account:
                    return {
                        'login': account.login,
                        'balance': account.balance,
                        'equity': account.equity,
                        'margin': account.margin,
                        'free_margin': account.margin_free,
                        'margin_level': account.margin_level,
                        'currency': account.currency,
                        'leverage': account.leverage,
                        'server': account.server
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting account info: {e}")
            return None
    
    def get_available_pairs(self) -> List[str]:
        """Get list of available trading pairs"""
        try:
            if not self._connected:
                self.logger.warning("⚠️ Not connected to broker - using fallback pairs")
                return self._get_fallback_pairs()
            
            if self.broker_type == "MetaTrader5":
                symbols = mt5.symbols_get()
                if symbols:
                    pairs = [symbol.name for symbol in symbols]
                    self.logger.info(f"✅ Retrieved {len(pairs)} pairs from MT5")
                    return pairs
                else:
                    self.logger.warning("⚠️ No symbols from MT5 - using fallback pairs")
                    return self._get_fallback_pairs()
            
            return self._get_fallback_pairs()
            
        except Exception as e:
            self.logger.error(f"Error getting available pairs: {e}")
            self.logger.warning("⚠️ Using fallback pairs due to error")
            return self._get_fallback_pairs()
    
    def _get_fallback_pairs(self) -> List[str]:
        """Get fallback pairs when broker data is unavailable"""
        fallback_pairs = [
            'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD',
            'EURGBP', 'EURJPY', 'GBPJPY', 'AUDJPY', 'CADJPY',
            'EURCHF', 'GBPCHF', 'USDCHF', 'AUDCHF', 'CADCHF',
            'EURAUD', 'GBPAUD', 'USDAUD', 'AUDCAD', 'EURNZD',
            'GBPNZD', 'USDNZD', 'AUDNZD', 'CADNZD', 'CHFJPY',
            'EURCAD', 'GBPCAD', 'USDCAD', 'AUDCAD', 'CADCHF'
        ]
        return fallback_pairs
    
    def _get_real_symbol(self, symbol: str) -> str:
        """🆕 แปลง base symbol เป็น real symbol ของ broker"""
        if self.symbol_mapper:
            return self.symbol_mapper.get_real_symbol(symbol)
        return symbol
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            # 🔧 พยายามเชื่อมต่อก่อนถ้ายังไม่ได้เชื่อมต่อ
            if not self._connected:
                self.logger.info(f"🔌 Attempting to connect to broker for {symbol}...")
                connect_result = self.connect()
                if not connect_result:
                    self.logger.warning(f"⚠️ Failed to connect to broker - cannot get price for {symbol}")
                    return None
                else:
                    self.logger.info(f"✅ Connected to broker successfully")
            
            if self.broker_type == "MetaTrader5":
                # 🆕 ใช้ real symbol จาก mapper
                real_symbol = self._get_real_symbol(symbol)
                tick = mt5.symbol_info_tick(real_symbol)
                if tick:
                    return tick.bid  # Return bid price
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    def get_account_balance(self) -> Optional[float]:
        """Get account balance"""
        try:
            if not self._connected:
                return None
            
            if self.broker_type == "MetaTrader5":
                account_info = mt5.account_info()
                if account_info:
                    return account_info.balance
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting account balance: {e}")
            return None
    
    def get_account_equity(self) -> Optional[float]:
        """Get account equity (balance + floating PnL)"""
        try:
            if not self._connected:
                return None
            
            if self.broker_type == "MetaTrader5":
                account_info = mt5.account_info()
                if account_info:
                    return account_info.equity
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting account equity: {e}")
            return None
    
    def get_free_margin(self) -> Optional[float]:
        """Get free margin (available for trading)"""
        try:
            if not self._connected:
                return None
            
            if self.broker_type == "MetaTrader5":
                account_info = mt5.account_info()
                if account_info:
                    return account_info.margin_free
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting free margin: {e}")
            return None
    
    def get_spread(self, symbol: str) -> Optional[float]:
        """Get current spread for a symbol in pips"""
        try:
            # 🔧 พยายามเชื่อมต่อก่อนถ้ายังไม่ได้เชื่อมต่อ
            if not self._connected:
                self.logger.info(f"🔌 Attempting to connect to broker for {symbol}...")
                connect_result = self.connect()
                if not connect_result:
                    self.logger.warning(f"⚠️ Failed to connect to broker - cannot get spread for {symbol}")
                    return None
                else:
                    self.logger.info(f"✅ Connected to broker successfully")
            
            if self.broker_type == "MetaTrader5":
                # 🆕 ใช้ real symbol จาก mapper
                real_symbol = self._get_real_symbol(symbol)
                
                # ดึงข้อมูล symbol info เพื่อรู้ digits
                symbol_info = mt5.symbol_info(real_symbol)
                if not symbol_info:
                    # 🔇 ไม่แสดง warning สำหรับ symbol ที่ไม่มีใน MT5 (เป็นเรื่องปกติ)
                    self.logger.debug(f"Symbol info not found for {symbol} (real: {real_symbol}) - using estimated")
                    return None
                
                # ดึงราคา tick
                tick = mt5.symbol_info_tick(real_symbol)
                if not tick or tick.bid is None or tick.ask is None:
                    self.logger.warning(f"Tick data unavailable for {symbol}: bid={tick.bid if tick else None}, ask={tick.ask if tick else None}")
                    return None
                
                # คำนวณ spread ใน pips
                spread_price = tick.ask - tick.bid
                
                # แปลงเป็น pips ตาม digits
                digits = symbol_info.digits
                if digits == 5 or digits == 3:  # 5-digit broker
                    spread_pips = spread_price * 10000
                elif digits == 4 or digits == 2:  # 4-digit broker
                    spread_pips = spread_price * 10000
                else:
                    # Default fallback
                    spread_pips = spread_price * 10000
                
                self.logger.debug(f"Spread for {symbol}: {spread_pips:.2f} pips (price diff: {spread_price:.5f})")
                return round(spread_pips, 2)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting spread for {symbol}: {e}")
            return None
    
    def get_historical_data(self, symbol: str, timeframe: str, count: int) -> Optional[pd.DataFrame]:
        """Get historical data for a symbol"""
        try:
            if not self._connected:
                return None
            
            if self.broker_type == "MetaTrader5":
                # 🆕 ใช้ real symbol จาก mapper
                real_symbol = self._get_real_symbol(symbol)
                
                # Convert timeframe string to MT5 constant
                tf_map = {
                    'M1': mt5.TIMEFRAME_M1,
                    'M5': mt5.TIMEFRAME_M5,
                    'M15': mt5.TIMEFRAME_M15,
                    'M30': mt5.TIMEFRAME_M30,
                    'H1': mt5.TIMEFRAME_H1,
                    'H4': mt5.TIMEFRAME_H4,
                    'D1': mt5.TIMEFRAME_D1
                }
                
                tf = tf_map.get(timeframe, mt5.TIMEFRAME_M1)
                
                # Get rates
                rates = mt5.copy_rates_from_pos(real_symbol, tf, 0, count)
                
                if rates is None or len(rates) == 0:
                    return None
                
                # Convert to DataFrame
                df = pd.DataFrame(rates)
                df['time'] = pd.to_datetime(df['time'], unit='s')
                df.set_index('time', inplace=True)
                
                return df
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting historical data for {symbol}: {e}")
            return None
    
    def place_order(self, symbol: str, order_type: str, volume: float, 
                   price: float = None, sl: float = None, tp: float = None, comment: str = None, magic: int = None) -> Optional[Dict]:
        """Place an order"""
        try:
            if not self._connected:
                return {
                    'success': False,
                    'error': 'Not connected to broker',
                    'symbol': symbol,
                    'type': order_type
                }
            
            if self.broker_type == "MetaTrader5":
                # Convert order type
                if order_type.upper() == 'BUY':
                    order_type_mt5 = mt5.ORDER_TYPE_BUY
                elif order_type.upper() == 'SELL':
                    order_type_mt5 = mt5.ORDER_TYPE_SELL
                else:
                    self.logger.error(f"Invalid order type: {order_type}")
                    return {
                        'success': False,
                        'error': f'Invalid order type: {order_type}',
                        'symbol': symbol,
                        'type': order_type
                    }
                
                # Get current price if not provided
                if price is None:
                    # ใช้ฟังก์ชันที่มีอยู่แล้ว
                    price = self.get_current_price(symbol)
                    if price is None:
                        return {
                            'success': False,
                            'error': f'Cannot get price for {symbol}',
                            'symbol': symbol,
                            'type': order_type
                        }
                
                # Simple symbol validation - just try to select (like before)
                if not mt5.symbol_select(symbol, True):
                    self.logger.warning(f"⚠️ Could not select symbol {symbol}, but continuing...")
                
                # Prepare request for REAL TRADING (แบบง่ายเหมือน Huakuy_)
                # ใช้ comment ตามกลุ่มและลำดับ
                simple_comment = comment if comment else "Trade"
                
                # ใช้ magic number ที่ระบุ หรือใช้ default
                magic_number = magic if magic is not None else 234000
                
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": volume,
                    "type": order_type_mt5,
                    "price": price,
                    "magic": magic_number,  # Use unique magic number for each group
                    "comment": simple_comment,
                }
                
                # Add stop loss and take profit
                if sl is not None:
                    request["sl"] = sl
                if tp is not None:
                    request["tp"] = tp
                
                # Send order
                self.logger.info(f"📤 Sending REAL order: {symbol} {order_type} {volume} @ {price}")
                self.logger.debug(f"📋 Order request: {request}")
                self.logger.info(f"🔄 Letting broker choose filling type automatically")
                
                # Enhanced validation
                if not self._connected:
                    self.logger.error(f"❌ Not connected to MT5 - cannot send real orders")
                    self.logger.error(f"❌ Please check MT5 connection and credentials")
                    return {
                        'success': False,
                        'error': 'Not connected to MT5',
                        'symbol': symbol,
                        'type': order_type
                    }
                
                # Check symbol info (symbol should already be real symbol from arbitrage_detector)
                symbol_info = mt5.symbol_info(symbol)
                if symbol_info is None:
                    self.logger.error(f"❌ Symbol {symbol} not found in MT5")
                    # ลองใช้ mapper อีกครั้ง
                    real_symbol = self._get_real_symbol(symbol)
                    if real_symbol != symbol:
                        symbol_info = mt5.symbol_info(real_symbol)
                        if symbol_info:
                            symbol = real_symbol  # อัปเดต symbol
                            self.logger.info(f"✅ Found symbol using mapper: {real_symbol}")
                    
                    if symbol_info is None:
                        return {
                            'success': False,
                            'error': f'Symbol {symbol} not found',
                            'symbol': symbol,
                            'type': order_type
                        }
                
                # Check if symbol is tradeable
                if not symbol_info.trade_mode:
                    self.logger.error(f"❌ Symbol {symbol} is not tradeable")
                    return {
                        'success': False,
                        'error': f'Symbol {symbol} not tradeable',
                        'symbol': symbol,
                        'type': order_type
                    }
                
                
                # Send order
                self.logger.info(f"🚀 ส่ง Order: {symbol} {order_type_mt5} Volume: {volume}")
                result = mt5.order_send(request)
                
                # Check result
                if result is None:
                    last_error = mt5.last_error()
                    error_code = last_error[0] if last_error else 0
                    error_msg = last_error[1] if last_error else 'Unknown error'
                    
                    # Provide specific error messages and solutions
                    specific_error = self._get_specific_error_message(error_code, error_msg, symbol, volume)
                    
                    self.logger.error(f"❌ Order failed: {error_msg}")
                    self.logger.error(f"   Symbol: {symbol}, Type: {order_type}, Volume: {volume}")
                    self.logger.error(f"   Error Code: {error_code}")
                    self.logger.error(f"   Specific Issue: {specific_error['issue']}")
                    self.logger.error(f"   Solution: {specific_error['solution']}")
                    
                    return {
                        'success': False,
                        'error': error_msg,
                        'error_code': error_code,
                        'specific_issue': specific_error['issue'],
                        'solution': specific_error['solution'],
                        'symbol': symbol,
                        'type': order_type
                    }
                
                # ตรวจสอบผลลัพธ์แบบง่าย ๆ
                try:
                    if result.retcode == 10009:  # สำเร็จ
                        self.logger.info(f"✅ Order successful: {symbol} {order_type}")
                        return {'success': True, 'symbol': symbol, 'type': order_type, 'volume': volume}
                    else:
                        return {'success': False, 'error': f'Order failed: {result.retcode}'}
                except:
                    # ถ้า result ไม่มี retcode attribute
                    return {'success': False, 'error': 'Order result invalid'}
            
            # This should never be reached, but just in case
            return {
                'success': False,
                'error': 'Unexpected end of function',
                'symbol': symbol,
                'type': order_type
            }
            
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return {
                'success': False,
                'error': str(e),
                'symbol': symbol,
                'type': order_type
            }
    
    def close_order(self, order_id: int) -> bool:
        """Close an order by ID"""
        try:
            if not self._connected:
                return False
            
            if self.broker_type == "MetaTrader5":
                # Get position info
                position = mt5.positions_get(ticket=order_id)
                if not position:
                    self.logger.warning(f"Position {order_id} not found")
                    return False
                
                position = position[0]
                
                # Determine close order type
                close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
                
                # Prepare close request (แบบง่ายเหมือน Huakuy_)
                # ใช้ comment ง่ายๆ เพื่อหลีกเลี่ยงปัญหา encoding
                close_comment = "Close"
                
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": position.symbol,
                    "volume": position.volume,
                    "type": close_type,
                    "position": order_id,
                    "magic": 234000,
                    "comment": close_comment,
                }
                
                # Send close order
                self.logger.info(f"🚀 ปิด Position: {order_id}")
                result = mt5.order_send(request)
                
                if result is None:
                    last_error = mt5.last_error()
                    self.logger.error(f"❌ ปิด Position ไม่สำเร็จ: {last_error}")
                    return False
                
                # Log detailed result
                self.logger.info(f"📋 Close Result: RetCode={getattr(result, 'retcode', 'N/A')}")
                
                if getattr(result, 'retcode', 0) == 10009:  # TRADE_RETCODE_DONE
                    # คำนวณ PnL จากข้อมูล position
                    pnl = position.profit
                    self.logger.info(f"✅ ปิดสำเร็จ! Deal: {getattr(result, 'deal', 'N/A')}, Order: {getattr(result, 'order', 'N/A')}")
                    self.logger.info(f"   💰 PnL: {pnl:.2f} USD")
                    return {
                        'success': True,
                        'order_id': getattr(result, 'order', None),
                        'deal_id': getattr(result, 'deal', None),
                        'pnl': pnl,
                        'symbol': position.symbol,
                        'volume': position.volume
                    }
                else:
                    error_desc = self._get_error_message(getattr(result, 'retcode', 0))
                    self.logger.error(f"❌ ไม่สำเร็จ: RetCode {getattr(result, 'retcode', 0)} - {error_desc}")
                    return {
                        'success': False,
                        'error': error_desc
                    }
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error closing order {order_id}: {e}")
            return False
    
    def close_position(self, position_id: int) -> bool:
        """Close a position by ID (alias for close_order)"""
        return self.close_order(position_id)
    
    def get_all_positions(self) -> List[Dict]:
        """Get all open positions"""
        try:
            if not self._connected:
                return []
            
            if self.broker_type == "MetaTrader5":
                positions = mt5.positions_get()
                if not positions:
                    return []
                
                position_list = []
                for pos in positions:
                    # MT5 positions have ticket - use it directly
                    position_id = pos.ticket
                    
                    position_list.append({
                        'ticket': position_id,
                        'symbol': pos.symbol,
                        'type': 'BUY' if pos.type == mt5.POSITION_TYPE_BUY else 'SELL',
                        'volume': pos.volume,
                        'price': pos.price_open,
                        'current_price': pos.price_current,
                        'sl': pos.sl,
                        'tp': pos.tp,
                        'profit': pos.profit,
                        'swap': pos.swap,
                        'time': pos.time,
                        'magic': pos.magic,
                        'comment': pos.comment
                    })
                
                return position_list
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return []
    
    def get_stuck_positions(self, min_age_hours: int = 1) -> List[Dict]:
        """Get positions that have been open for too long and are losing"""
        try:
            positions = self.get_all_positions()
            stuck_positions = []
            cutoff_time = datetime.now() - timedelta(hours=min_age_hours)
            
            for position in positions:
                # Convert time to datetime
                pos_time = datetime.fromtimestamp(position['time'])
                
                if (pos_time < cutoff_time and position['profit'] < 0):
                    stuck_positions.append(position)
            
            return stuck_positions
            
        except Exception as e:
            self.logger.error(f"Error getting stuck positions: {e}")
            return []
    
    def cancel_order(self, order_id: int) -> bool:
        """Cancel a pending order"""
        try:
            if not self._connected:
                return False
            
            if self.broker_type == "MetaTrader5":
                # Get order info
                orders = mt5.orders_get(ticket=order_id)
                if not orders:
                    self.logger.warning(f"Order {order_id} not found")
                    return False
                
                # Prepare cancel request
                request = {
                    "action": mt5.TRADE_ACTION_REMOVE,
                    "order": order_id,
                    "magic": 234000,
                }
                
                # Send cancel request
                result = mt5.order_send(request)
                
                if getattr(result, 'retcode', 0) != mt5.TRADE_RETCODE_DONE:
                    self.logger.error(f"Cancel order failed: {getattr(result, 'retcode', 0)} - {getattr(result, 'comment', 'No comment')}")
                    return False
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def get_tick_data(self) -> Dict:
        """Get latest tick data for all symbols"""
        try:
            if not self._connected:
                return {}
            
            if self.broker_type == "MetaTrader5":
                symbols = self.get_available_pairs()
                tick_data = {}
                
                for symbol in symbols[:10]:  # Limit to first 10 symbols for performance
                    tick = mt5.symbol_info_tick(symbol)
                    if tick:
                        tick_data[symbol] = {
                            'bid': tick.bid,
                            'ask': tick.ask,
                            'last': tick.last,
                            'volume': tick.volume,
                            'time': tick.time
                        }
                
                return tick_data
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Error getting tick data: {e}")
            return {}
    
    def _get_filling_type(self, symbol_info) -> int:
        """Determine appropriate filling type for symbol"""
        try:
            # Check if filling_mode attribute exists
            if not hasattr(symbol_info, 'filling_mode'):
                self.logger.warning("Symbol info has no filling_mode attribute, using RETURN")
                return mt5.ORDER_FILLING_RETURN
            
            # Check symbol filling modes
            filling_mode = symbol_info.filling_mode
            
            # Check if MT5 constants exist
            if hasattr(mt5, 'SYMBOL_FILLING_FOK') and hasattr(mt5, 'ORDER_FILLING_FOK'):
                # Prefer FOK (Fill or Kill) for better execution
                if filling_mode & mt5.SYMBOL_FILLING_FOK:
                    return mt5.ORDER_FILLING_FOK
                # Fallback to IOC (Immediate or Cancel)
                elif filling_mode & mt5.SYMBOL_FILLING_IOC:
                    return mt5.ORDER_FILLING_IOC
                # Last resort - Return (Fill at any price)
                elif filling_mode & mt5.SYMBOL_FILLING_RETURN:
                    return mt5.ORDER_FILLING_RETURN
                else:
                    # Default to FOK
                    return mt5.ORDER_FILLING_FOK
            else:
                # Fallback to RETURN if constants don't exist
                self.logger.warning("MT5 filling constants not available, using RETURN")
                return mt5.ORDER_FILLING_RETURN
                
        except Exception as e:
            self.logger.warning(f"Error determining filling type: {e}, using RETURN")
            return mt5.ORDER_FILLING_RETURN
    
    def _get_error_message(self, retcode: int) -> str:
        """Get human-readable error message for MT5 retcode"""
        error_messages = {
            mt5.TRADE_RETCODE_REQUOTE: "ราคาเปลี่ยนแปลง - ต้องใช้ราคาใหม่",
            mt5.TRADE_RETCODE_REJECT: "คำสั่งถูกปฏิเสธ",
            mt5.TRADE_RETCODE_ERROR: "ข้อผิดพลาดทั่วไป",
            mt5.TRADE_RETCODE_TIMEOUT: "หมดเวลา - คำสั่งไม่สำเร็จ",
            mt5.TRADE_RETCODE_INVALID_VOLUME: "ปริมาณการเทรดไม่ถูกต้อง",
            mt5.TRADE_RETCODE_INVALID_PRICE: "ราคาไม่ถูกต้อง",
            mt5.TRADE_RETCODE_INVALID_STOPS: "Stop Loss/Take Profit ไม่ถูกต้อง",
            mt5.TRADE_RETCODE_TRADE_DISABLED: "การเทรดถูกปิดใช้งาน",
            mt5.TRADE_RETCODE_MARKET_CLOSED: "ตลาดปิด",
            mt5.TRADE_RETCODE_NO_MONEY: "เงินไม่เพียงพอ",
            mt5.TRADE_RETCODE_PRICE_CHANGED: "ราคาเปลี่ยนแปลง",
            mt5.TRADE_RETCODE_TOO_MANY_REQUESTS: "คำขอมากเกินไป",
            mt5.TRADE_RETCODE_NO_CHANGES: "ไม่มีการเปลี่ยนแปลง",
            mt5.TRADE_RETCODE_SERVER_DISABLES_AT: "เซิร์ฟเวอร์ปิดใช้งาน AT",
            mt5.TRADE_RETCODE_CLIENT_DISABLES_AT: "ไคลเอนต์ปิดใช้งาน AT",
            mt5.TRADE_RETCODE_LOCKED: "บัญชีถูกล็อค",
            mt5.TRADE_RETCODE_FROZEN: "คำสั่งถูกแช่แข็ง",
            mt5.TRADE_RETCODE_INVALID_FILL: "การเติมคำสั่งไม่ถูกต้อง",
            mt5.TRADE_RETCODE_CONNECTION: "ปัญหาการเชื่อมต่อ",
            mt5.TRADE_RETCODE_ONLY_REAL: "เฉพาะบัญชีจริงเท่านั้น",
            mt5.TRADE_RETCODE_LIMIT_ORDERS: "เกินขีดจำกัดคำสั่ง",
            mt5.TRADE_RETCODE_LIMIT_VOLUME: "เกินขีดจำกัดปริมาณ",
            mt5.TRADE_RETCODE_INVALID_ORDER: "คำสั่งไม่ถูกต้อง",
            mt5.TRADE_RETCODE_POSITION_CLOSED: "ตำแหน่งปิดแล้ว",
            mt5.TRADE_RETCODE_INVALID_CLOSE_VOLUME: "ปริมาณปิดไม่ถูกต้อง",
            mt5.TRADE_RETCODE_CLOSE_ORDER_EXIST: "มีคำสั่งปิดอยู่แล้ว",
            mt5.TRADE_RETCODE_LIMIT_POSITIONS: "เกินขีดจำกัดตำแหน่ง",
            mt5.TRADE_RETCODE_REJECT_CANCEL: "การยกเลิกถูกปฏิเสธ",
            mt5.TRADE_RETCODE_LONG_ONLY: "เฉพาะ Long เท่านั้น",
            mt5.TRADE_RETCODE_SHORT_ONLY: "เฉพาะ Short เท่านั้น",
            mt5.TRADE_RETCODE_CLOSE_ONLY: "เฉพาะการปิดเท่านั้น",
            mt5.TRADE_RETCODE_FIFO_CLOSE: "FIFO close required",
            mt5.TRADE_RETCODE_CLOSE_ORDER_EXIST: "มีคำสั่งปิดอยู่แล้ว",
            mt5.TRADE_RETCODE_LIMIT_POSITIONS: "เกินขีดจำกัดตำแหน่ง",
            10030: "Unsupported filling mode - ใช้ filling type ที่ไม่รองรับ",
        }
        
        return error_messages.get(retcode, f"Unknown error (code: {retcode})")
    
    def is_connected(self) -> bool:
        """Check if connected to broker"""
        try:
            if not self._connected:
                return False
            
            # Verify connection is still active
            if self.broker_type == "MetaTrader5":
                account_info = mt5.account_info()
                if account_info is None:
                    self._connected = False
                    self.logger.warning("⚠️ MT5 connection lost")
                    return False
            
            return self._connected
            
        except Exception as e:
            self.logger.error(f"Error checking connection: {e}")
            self._connected = False
            return False
    
    def check_mt5_status(self) -> dict:
        """Check MT5 connection status and provide diagnostics"""
        status = {
            'connected': False,
            'mt5_available': False,
            'terminal_running': False,
            'account_connected': False,
            'config_valid': False,
            'issues': [],
            'recommendations': []
        }
        
        try:
            # Check if MT5 module is available
            try:
                import MetaTrader5 as mt5
                status['mt5_available'] = True
            except ImportError:
                status['issues'].append("MetaTrader5 module not installed")
                status['recommendations'].append("Install MetaTrader5: pip install MetaTrader5")
                return status
            
            # Check if MT5 is initialized
            if mt5.initialize():
                status['terminal_running'] = True
                
                # Check account connection
                account_info = mt5.account_info()
                if account_info:
                    status['account_connected'] = True
                    status['connected'] = True
                else:
                    status['issues'].append("MT5 terminal running but no account connected")
                    status['recommendations'].append("Login to your account in MT5 terminal")
            else:
                status['issues'].append("MT5 terminal not running or not accessible")
                status['recommendations'].append("Start MetaTrader5 terminal")
            
            # Check config
            mt5_config = self.config.get('MetaTrader5', {})
            if mt5_config.get('login') and mt5_config.get('server'):
                password = mt5_config.get('password', '')
                if password and password.strip():
                    status['config_valid'] = True
                else:
                    status['issues'].append("Password not set in broker_config.json")
                    status['recommendations'].append("Set password in config/broker_config.json")
            else:
                status['issues'].append("Incomplete MT5 configuration")
                status['recommendations'].append("Set login, password, and server in broker_config.json")
            
            # Add general recommendations
            if not status['connected']:
                status['recommendations'].extend([
                    "Ensure MT5 terminal is running",
                    "Login to your trading account in MT5",
                    "Enable 'Allow automated trading' in MT5 options",
                    "Check if Expert Advisors are allowed"
                ])
            
        except Exception as e:
            status['issues'].append(f"Error checking MT5 status: {e}")
        
        return status
    
    def _get_specific_error_message(self, error_code: int, error_msg: str, symbol: str, volume: float) -> dict:
        """Get specific error message and solution based on error code"""
        
        error_solutions = {
            10004: {  # TRADE_RETCODE_INVALID_VOLUME
                'issue': f'Volume {volume} is invalid for {symbol}',
                'solution': 'Check minimum/maximum volume limits for this symbol'
            },
            10006: {  # TRADE_RETCODE_MARKET_CLOSED
                'issue': f'Market is closed for {symbol}',
                'solution': 'Wait for market to open or trade during market hours'
            },
            10014: {  # TRADE_RETCODE_NO_MONEY
                'issue': 'Insufficient funds in account',
                'solution': 'Deposit more funds or reduce position size'
            },
            10064: {  # TRADE_RETCODE_TRADE_DISABLED
                'issue': 'Automated trading is disabled',
                'solution': 'Enable "Allow automated trading" in MT5 Options > Expert Advisors'
            },
            10027: {  # TRADE_RETCODE_INVALID_PRICE
                'issue': f'Invalid price for {symbol}',
                'solution': 'Check current market price and spread'
            },
            10028: {  # TRADE_RETCODE_INVALID_STOPS
                'issue': 'Invalid stop loss or take profit levels',
                'solution': 'Check minimum distance requirements for stops'
            },
            10029: {  # TRADE_RETCODE_TRADE_MODIFY_DENIED
                'issue': 'Trade modification denied',
                'solution': 'Check if order can be modified or close and reopen'
            },
            10030: {  # TRADE_RETCODE_LONG_ONLY
                'issue': f'Only long positions allowed for {symbol}',
                'solution': 'Use BUY orders only for this symbol'
            },
            10031: {  # TRADE_RETCODE_SHORT_ONLY
                'issue': f'Only short positions allowed for {symbol}',
                'solution': 'Use SELL orders only for this symbol'
            },
            10032: {  # TRADE_RETCODE_CLOSE_ONLY
                'issue': f'Only closing positions allowed for {symbol}',
                'solution': 'Close existing positions first'
            },
            10033: {  # TRADE_RETCODE_FIFO_CLOSE
                'issue': 'FIFO rule violation',
                'solution': 'Close positions in correct order (FIFO)'
            },
            10034: {  # TRADE_RETCODE_CLOSE_BY
                'issue': 'Position closed by opposite order',
                'solution': 'Check if position was closed by hedging'
            },
            10035: {  # TRADE_RETCODE_INVALID_EXPIRATION
                'issue': 'Invalid expiration time',
                'solution': 'Check expiration time format and validity'
            },
            10036: {  # TRADE_RETCODE_INVALID_ORDER
                'issue': 'Invalid order parameters',
                'solution': 'Check all order parameters (symbol, volume, price, etc.)'
            },
            10037: {  # TRADE_RETCODE_INVALID_POSITION
                'issue': 'Invalid position',
                'solution': 'Check if position exists and is valid'
            },
            10038: {  # TRADE_RETCODE_INVALID_REQUEST
                'issue': 'Invalid request format',
                'solution': 'Check request structure and parameters'
            },
            10039: {  # TRADE_RETCODE_INVALID_STOPS_LEVEL
                'issue': 'Invalid stops level',
                'solution': 'Check minimum distance from current price'
            },
            10040: {  # TRADE_RETCODE_INVALID_TRADE_VOLUME
                'issue': f'Invalid trade volume {volume}',
                'solution': 'Check volume step and limits for this symbol'
            },
            10041: {  # TRADE_RETCODE_INVALID_TRADE_PRICE
                'issue': 'Invalid trade price',
                'solution': 'Check price format and current market price'
            },
            10042: {  # TRADE_RETCODE_INVALID_TRADE_STOPS
                'issue': 'Invalid trade stops',
                'solution': 'Check stop loss and take profit levels'
            },
            10043: {  # TRADE_RETCODE_TRADE_DISABLED
                'issue': 'Trading disabled for this symbol',
                'solution': 'Check if symbol is tradeable and market is open'
            },
            10044: {  # TRADE_RETCODE_MARKET_CLOSED
                'issue': 'Market is closed',
                'solution': 'Wait for market to open'
            },
            10045: {  # TRADE_RETCODE_NO_MONEY
                'issue': 'No money',
                'solution': 'Deposit funds or reduce position size'
            },
            10046: {  # TRADE_RETCODE_PRICE_CHANGED
                'issue': 'Price changed during order execution',
                'solution': 'Retry order with current market price'
            },
            10047: {  # TRADE_RETCODE_OFF_QUOTES
                'issue': 'Off quotes',
                'solution': 'Check if symbol is available for trading'
            },
            10048: {  # TRADE_RETCODE_BROKER_BUSY
                'issue': 'Broker is busy',
                'solution': 'Retry order after a short delay'
            },
            10049: {  # TRADE_RETCODE_REQUOTE
                'issue': 'Requote',
                'solution': 'Accept new price or cancel order'
            },
            10050: {  # TRADE_RETCODE_ORDER_LOCKED
                'issue': 'Order is locked',
                'solution': 'Wait for order to be processed'
            },
            10051: {  # TRADE_RETCODE_LONG_POSITIONS_ONLY_ALLOWED
                'issue': 'Only long positions allowed',
                'solution': 'Use BUY orders only'
            },
            10052: {  # TRADE_RETCODE_TOO_MANY_REQUESTS
                'issue': 'Too many requests',
                'solution': 'Reduce order frequency'
            },
            10053: {  # TRADE_RETCODE_MISMATCH
                'issue': 'Order mismatch',
                'solution': 'Check order parameters'
            },
            10054: {  # TRADE_RETCODE_NO_MARGIN
                'issue': 'No margin',
                'solution': 'Deposit funds or reduce position size'
            },
            10055: {  # TRADE_RETCODE_NOT_ENOUGH_MONEY
                'issue': 'Not enough money',
                'solution': 'Deposit more funds'
            },
            10056: {  # TRADE_RETCODE_PRICE_OFF
                'issue': 'Price is off',
                'solution': 'Check current market price'
            },
            10057: {  # TRADE_RETCODE_INVALID_VOLUME
                'issue': f'Invalid volume {volume}',
                'solution': 'Check volume step and limits'
            },
            10058: {  # TRADE_RETCODE_INVALID_AMOUNT
                'issue': 'Invalid amount',
                'solution': 'Check amount calculation'
            },
            10059: {  # TRADE_RETCODE_INVALID_PRICE
                'issue': 'Invalid price',
                'solution': 'Check price format and current market price'
            },
            10060: {  # TRADE_RETCODE_INVALID_STOPS
                'issue': 'Invalid stops',
                'solution': 'Check stop loss and take profit levels'
            },
            10061: {  # TRADE_RETCODE_TRADE_DISABLED
                'issue': 'Trade disabled',
                'solution': 'Enable automated trading in MT5'
            },
            10062: {  # TRADE_RETCODE_MARKET_CLOSED
                'issue': 'Market closed',
                'solution': 'Wait for market to open'
            },
            10063: {  # TRADE_RETCODE_NO_MONEY
                'issue': 'No money',
                'solution': 'Deposit funds'
            },
            10064: {  # TRADE_RETCODE_TRADE_DISABLED
                'issue': 'Trade disabled',
                'solution': 'Enable automated trading in MT5 Options > Expert Advisors'
            }
        }
        
        # Get specific error info
        if error_code in error_solutions:
            return error_solutions[error_code]
        else:
            return {
                'issue': f'Unknown error code {error_code}: {error_msg}',
                'solution': 'Check MT5 terminal settings and market conditions'
            }
