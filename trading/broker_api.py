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

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import json
import time

class BrokerAPI:
    def __init__(self, broker_type: str = "MetaTrader5", config_file: str = "config/broker_config.json"):
        self.broker_type = broker_type
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_file)
        self._connected = False
        self.account_info = None
        
    def _load_config(self, config_file: str) -> Dict:
        """Load broker configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
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
                self.logger.info("MT5 already connected - using existing connection")
                self.account_info = account_info
                self._connected = True
                
                # Auto-detect and save config
                self.auto_detect_mt5_config()
                
                self.logger.info(f"Auto-connected to MT5 - Account: {account_info.login}, "
                               f"Server: {account_info.server}, Balance: {account_info.balance}")
                return True
            
            # Try to connect using terminal's connection
            self.logger.info("Attempting to connect using MT5 terminal connection...")
            if mt5.login():
                account_info = mt5.account_info()
                if account_info is not None:
                    self.account_info = account_info
                    self._connected = True
                    
                    # Auto-detect and save config
                    self.auto_detect_mt5_config()
                    
                    self.logger.info(f"Auto-connected to MT5 - Account: {account_info.login}, "
                                   f"Server: {account_info.server}, Balance: {account_info.balance}")
                    return True
            
            # Try to connect with config credentials
            mt5_config = self.config.get('MetaTrader5', {})
            if mt5_config.get('login') and mt5_config.get('password') and mt5_config.get('server'):
                self.logger.info("Attempting to connect with config credentials...")
                if self._connect_with_credentials():
                    return True
            
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
            with open('config/broker_config.json', 'w') as f:
                json.dump(self.config, f, indent=2)
            self.logger.info("Config file updated successfully")
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
        return [
            'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD',
            'EURGBP', 'EURJPY', 'GBPJPY', 'AUDJPY', 'CADJPY',
            'EURCHF', 'GBPCHF', 'USDCHF', 'AUDCHF', 'CADCHF',
            'EURAUD', 'GBPAUD', 'USDAUD', 'AUDCAD', 'EURNZD',
            'GBPNZD', 'USDNZD', 'AUDNZD', 'CADNZD', 'CHFJPY',
            'EURCAD', 'GBPCAD', 'USDCAD', 'AUDCAD', 'CADCHF'
        ]
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            if not self._connected:
                return None
            
            if self.broker_type == "MetaTrader5":
                tick = mt5.symbol_info_tick(symbol)
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
    
    def get_spread(self, symbol: str) -> Optional[float]:
        """Get current spread for a symbol"""
        try:
            if not self._connected:
                return None
            
            if self.broker_type == "MetaTrader5":
                tick = mt5.symbol_info_tick(symbol)
                if tick:
                    return tick.ask - tick.bid
            
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
                rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
                
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
                   price: float = None, sl: float = None, tp: float = None, comment: str = None) -> Optional[Dict]:
        """Place an order"""
        try:
            if not self._connected:
                return None
            
            if self.broker_type == "MetaTrader5":
                # Convert order type
                if order_type.upper() == 'BUY':
                    order_type_mt5 = mt5.ORDER_TYPE_BUY
                elif order_type.upper() == 'SELL':
                    order_type_mt5 = mt5.ORDER_TYPE_SELL
                else:
                    self.logger.error(f"Invalid order type: {order_type}")
                    return None
                
                # Get current price if not provided
                if price is None:
                    tick = mt5.symbol_info_tick(symbol)
                    if not tick:
                        return None
                    price = tick.ask if order_type.upper() == 'BUY' else tick.bid
                
                # Validate symbol first
                symbol_info = mt5.symbol_info(symbol)
                if symbol_info is None:
                    self.logger.error(f"❌ Symbol {symbol} not found in MT5")
                    return None
                
                # Check if symbol is selectable (compatible with different MT5 versions)
                try:
                    if hasattr(symbol_info, 'selectable') and not symbol_info.selectable:
                        self.logger.warning(f"⚠️ Symbol {symbol} is not selectable, trying to select...")
                        if not mt5.symbol_select(symbol, True):
                            self.logger.error(f"❌ Failed to select symbol {symbol}")
                            return None
                    else:
                        # Try to select symbol anyway to ensure it's available
                        if not mt5.symbol_select(symbol, True):
                            self.logger.warning(f"⚠️ Could not select symbol {symbol}, but continuing...")
                except AttributeError:
                    # Fallback for older MT5 versions
                    self.logger.debug(f"🔍 Symbol {symbol} validation skipped (older MT5 version)")
                    if not mt5.symbol_select(symbol, True):
                        self.logger.warning(f"⚠️ Could not select symbol {symbol}, but continuing...")
                
                # Final symbol validation
                if not mt5.symbol_select(symbol, True):
                    self.logger.error(f"❌ Symbol {symbol} cannot be selected for trading")
                    return None
                
                # Check if symbol trading is allowed
                if not symbol_info.trade_mode:
                    self.logger.error(f"❌ Trading not allowed for symbol {symbol}")
                    return None
                
                # Check if symbol is visible
                if not symbol_info.visible:
                    self.logger.warning(f"⚠️ Symbol {symbol} is not visible, trying to make visible...")
                    if not mt5.symbol_select(symbol, True):
                        self.logger.error(f"❌ Cannot make symbol {symbol} visible")
                        return None
                
                # Prepare request for REAL TRADING
                # Let broker choose the filling type automatically
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": volume,
                    "type": order_type_mt5,
                    "price": price,
                    "deviation": 20,
                    "magic": 234000,
                    "comment": comment or "Arbitrage Bot",
                    "type_time": mt5.ORDER_TIME_GTC,
                    # Let broker choose type_filling automatically
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
                
                # Check MT5 connection before sending
                if not mt5.terminal_info():
                    self.logger.error(f"❌ MT5 terminal not connected")
                    return None
                
                # Check if trading is allowed
                account_info = mt5.account_info()
                if not account_info:
                    self.logger.error(f"❌ Cannot get account info from MT5")
                    return None
                
                if not account_info.trade_allowed:
                    self.logger.error(f"❌ Trading not allowed on this account")
                    return None
                
                # Send order - let broker choose filling type
                self.logger.info(f"🔍 Sending order to MT5: {request}")
                result = mt5.order_send(request)
                
                # Debug: Check what we got
                if result is None:
                    self.logger.warning(f"⚠️ MT5 returned None for {symbol}")
                    self.logger.info(f"🔍 This means order was not sent to MT5")
                else:
                    self.logger.info(f"✅ MT5 returned result: {result}")
                    self.logger.info(f"🔍 Result retcode: {result.retcode}")
                    self.logger.info(f"🔍 Result comment: {result.comment}")
                
                if result is None:
                    self.logger.warning(f"⚠️ No result from MT5 for {symbol} - checking for success...")
                    # Try to get last error
                    error = mt5.last_error()
                    if error:
                        error_code, error_desc = error
                        if error_code == 1:  # Success code
                            self.logger.info(f"✅ MT5 Success: {error_desc}")
                            # Check if position was actually created
                            positions = mt5.positions_get(symbol=symbol)
                            if positions:
                                # Find the most recent position
                                latest_position = max(positions, key=lambda p: p.time)
                                self.logger.info(f"✅ Order executed successfully: {symbol} {order_type} {volume} @ {price}")
                                return {
                                    'order_id': latest_position.ticket,
                                    'symbol': symbol,
                                    'type': order_type,
                                    'volume': volume,
                                    'price': price,
                                    'sl': sl,
                                    'tp': tp,
                                    'retcode': 10009,  # TRADE_RETCODE_DONE
                                    'comment': 'Order executed successfully'
                                }
                            else:
                                # No position found, but MT5 says success
                                self.logger.warning(f"⚠️ MT5 reports success but no position found for {symbol}")
                                return None
                        else:
                            self.logger.error(f"MT5 Error: {error}")
                    else:
                        # No error but no result - check if position was created
                        self.logger.info(f"🔍 No error reported - checking for position: {symbol}")
                        positions = mt5.positions_get(symbol=symbol)
                        if positions:
                            # Find the most recent position
                            latest_position = max(positions, key=lambda p: p.time)
                            self.logger.info(f"✅ Order executed successfully: {symbol} {order_type} {volume} @ {price}")
                            return {
                                'order_id': latest_position.ticket,
                                'symbol': symbol,
                                'type': order_type,
                                'volume': volume,
                                'price': price,
                                'sl': sl,
                                'tp': tp,
                                'retcode': 10009,  # TRADE_RETCODE_DONE
                                'comment': 'Order executed successfully (no error)'
                            }
                        else:
                            self.logger.warning(f"⚠️ No error but no position found for {symbol}")
                            return None
                    return None
                
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    self.logger.error(f"❌ Order failed: {result.retcode} - {result.comment}")
                    return None
                
                # Success!
                self.logger.info(f"✅ Order executed successfully: {symbol} {order_type} {volume} @ {price}")
                self.logger.info(f"   Order ID: {result.order}, Retcode: {result.retcode}")
                
                return {
                    'order_id': result.order,
                    'symbol': symbol,
                    'type': order_type,
                    'volume': volume,
                    'price': price,
                    'sl': sl,
                    'tp': tp,
                    'retcode': result.retcode,
                    'comment': result.comment
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return None
    
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
                
                # Prepare close request
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": position.symbol,
                    "volume": position.volume,
                    "type": close_type,
                    "position": order_id,
                    "deviation": 20,
                    "magic": 234000,
                    "comment": "Close Position",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                
                # Send close order
                result = mt5.order_send(request)
                
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    self.logger.error(f"Close order failed: {result.retcode} - {result.comment}")
                    return False
                
                return True
            
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
                    position_list.append({
                        'ticket': pos.ticket,
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
                
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    self.logger.error(f"Cancel order failed: {result.retcode} - {result.comment}")
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
    
    def is_connected(self) -> bool:
        """Check if connected to broker"""
        return self._connected
