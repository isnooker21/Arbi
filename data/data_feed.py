"""
ระบบจัดการข้อมูลราคาแบบ Real-time

ไฟล์นี้ทำหน้าที่:
- รับข้อมูลราคาจาก Broker แบบ Real-time
- แปลงข้อมูล Tick เป็น OHLC (Open, High, Low, Close)
- เก็บข้อมูลใน Cache เพื่อการเข้าถึงที่รวดเร็ว
- ส่งข้อมูลให้กับระบบอื่นๆ ผ่าน Callback
- คำนวณสถิติราคา เช่น Volatility, Moving Average

ฟีเจอร์หลัก:
- Real-time Price Updates: อัปเดตราคาแบบเรียลไทม์
- Data Caching: เก็บข้อมูลในหน่วยความจำ
- OHLC Conversion: แปลงข้อมูล Tick เป็น OHLC
- Statistics Calculation: คำนวณสถิติราคา
- Subscriber System: ระบบแจ้งเตือนข้อมูลใหม่
"""

import asyncio
import json
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import pandas as pd
import numpy as np

# Try to import websockets, fallback to alternative if not available
try:
    import websockets  # type: ignore
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("Warning: websockets library not available. WebSocket features will be disabled.")

class RealTimeDataFeed:
    def __init__(self, broker_api):
        self.broker = broker_api
        self.subscribers = []
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        self.data_cache = {}
        self.update_thread = None
        
    def subscribe(self, callback: Callable, pairs: List[str] = None, data_type: str = "tick"):
        """Subscribe to real-time data updates"""
        try:
            subscriber = {
                'callback': callback,
                'pairs': pairs or 'all',
                'data_type': data_type,
                'last_update': datetime.now()
            }
            self.subscribers.append(subscriber)
            self.logger.info(f"Subscribed to {data_type} data for {pairs or 'all pairs'}")
            
        except Exception as e:
            self.logger.error(f"Error subscribing to data feed: {e}")
    
    def unsubscribe(self, callback: Callable):
        """Unsubscribe from data updates"""
        try:
            self.subscribers = [s for s in self.subscribers if s['callback'] != callback]
            self.logger.info("Unsubscribed from data feed")
            
        except Exception as e:
            self.logger.error(f"Error unsubscribing from data feed: {e}")
    
    def start(self):
        """Start real-time data feed"""
        try:
            if self.is_running:
                self.logger.warning("Data feed already running")
                return
            
            self.is_running = True
            self.logger.info("Starting real-time data feed...")
            
            # Start update thread
            self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self.update_thread.start()
            
        except Exception as e:
            self.logger.error(f"Error starting data feed: {e}")
    
    def stop(self):
        """Stop real-time data feed"""
        try:
            self.is_running = False
            if self.update_thread:
                self.update_thread.join(timeout=5)
            
            self.logger.info("Real-time data feed stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping data feed: {e}")
    
    def _update_loop(self):
        """Main update loop for data feed"""
        while self.is_running:
            try:
                # Get latest tick data
                tick_data = self._get_tick_data()
                
                if tick_data:
                    # Update cache
                    self._update_cache(tick_data)
                    
                    # Notify subscribers
                    self._notify_subscribers(tick_data)
                
                # Sleep for update interval
                threading.Event().wait(0.1)  # 100ms updates
                
            except Exception as e:
                self.logger.error(f"Error in data update loop: {e}")
                threading.Event().wait(1)
    
    def _get_tick_data(self) -> Optional[Dict]:
        """Get latest tick data from broker"""
        try:
            if not self.broker or not self.broker.is_connected():
                return None
            
            # Get available pairs
            pairs = self.broker.get_available_pairs()
            if not pairs:
                return None
            
            # Limit to first 20 pairs for performance
            pairs = pairs[:20]
            
            tick_data = {}
            for symbol in pairs:
                try:
                    # Get current price
                    price = self.broker.get_current_price(symbol)
                    if price is not None:
                        # Get spread
                        spread = self.broker.get_spread(symbol)
                        
                        tick_data[symbol] = {
                            'bid': price,
                            'ask': price + (spread or 0.0001),
                            'spread': spread or 0.0001,
                            'timestamp': datetime.now(),
                            'volume': 0  # Volume not available in tick data
                        }
                        
                except Exception as e:
                    self.logger.debug(f"Error getting tick data for {symbol}: {e}")
                    continue
            
            return tick_data
            
        except Exception as e:
            self.logger.error(f"Error getting tick data: {e}")
            return None
    
    def _update_cache(self, tick_data: Dict):
        """Update data cache with latest tick data"""
        try:
            for symbol, data in tick_data.items():
                if symbol not in self.data_cache:
                    self.data_cache[symbol] = {
                        'ticks': [],
                        'last_update': datetime.now(),
                        'price_history': []
                    }
                
                # Add tick to cache
                self.data_cache[symbol]['ticks'].append(data)
                self.data_cache[symbol]['last_update'] = datetime.now()
                
                # Add to price history
                self.data_cache[symbol]['price_history'].append({
                    'price': data['bid'],
                    'timestamp': data['timestamp']
                })
                
                # Keep only last 1000 ticks
                if len(self.data_cache[symbol]['ticks']) > 1000:
                    self.data_cache[symbol]['ticks'] = self.data_cache[symbol]['ticks'][-1000:]
                
                # Keep only last 10000 price points
                if len(self.data_cache[symbol]['price_history']) > 10000:
                    self.data_cache[symbol]['price_history'] = self.data_cache[symbol]['price_history'][-10000:]
                    
        except Exception as e:
            self.logger.error(f"Error updating cache: {e}")
    
    def _notify_subscribers(self, tick_data: Dict):
        """Notify all subscribers of new data"""
        try:
            for subscriber in self.subscribers:
                try:
                    # Check if subscriber wants this data
                    if subscriber['pairs'] != 'all':
                        filtered_data = {k: v for k, v in tick_data.items() if k in subscriber['pairs']}
                        if not filtered_data:
                            continue
                    else:
                        filtered_data = tick_data
                    
                    # Call subscriber callback
                    if subscriber['data_type'] == 'tick':
                        subscriber['callback'](filtered_data)
                    elif subscriber['data_type'] == 'ohlc':
                        # Convert tick data to OHLC
                        ohlc_data = self._convert_to_ohlc(filtered_data)
                        if ohlc_data:
                            subscriber['callback'](ohlc_data)
                    
                    # Update last update time
                    subscriber['last_update'] = datetime.now()
                    
                except Exception as e:
                    self.logger.error(f"Error notifying subscriber: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error notifying subscribers: {e}")
    
    def _convert_to_ohlc(self, tick_data: Dict) -> Optional[Dict]:
        """Convert tick data to OHLC format"""
        try:
            ohlc_data = {}
            
            for symbol, data in tick_data.items():
                if symbol in self.data_cache and self.data_cache[symbol]['ticks']:
                    ticks = self.data_cache[symbol]['ticks']
                    
                    # Get recent ticks (last minute)
                    recent_ticks = [t for t in ticks if (datetime.now() - t['timestamp']).total_seconds() < 60]
                    
                    if recent_ticks:
                        prices = [t['bid'] for t in recent_ticks]
                        
                        ohlc_data[symbol] = {
                            'open': prices[0],
                            'high': max(prices),
                            'low': min(prices),
                            'close': prices[-1],
                            'volume': len(recent_ticks),
                            'timestamp': datetime.now()
                        }
            
            return ohlc_data
            
        except Exception as e:
            self.logger.error(f"Error converting to OHLC: {e}")
            return None
    
    def get_historical_data(self, symbol: str, timeframe: str, count: int) -> Optional[pd.DataFrame]:
        """Get historical data for a symbol"""
        try:
            if not self.broker or not self.broker.is_connected():
                return None
            
            # Try to get from broker first
            data = self.broker.get_historical_data(symbol, timeframe, count)
            if data is not None:
                return data
            
            # If not available from broker, try to construct from cache
            if symbol in self.data_cache:
                return self._construct_historical_from_cache(symbol, timeframe, count)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting historical data for {symbol}: {e}")
            return None
    
    def _construct_historical_from_cache(self, symbol: str, timeframe: str, count: int) -> Optional[pd.DataFrame]:
        """Construct historical data from cache"""
        try:
            if symbol not in self.data_cache:
                return None
            
            price_history = self.data_cache[symbol]['price_history']
            if len(price_history) < count:
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(price_history[-count:])
            df.set_index('timestamp', inplace=True)
            
            # Resample based on timeframe
            if timeframe == 'M1':
                df = df.resample('1T').agg({
                    'price': ['first', 'max', 'min', 'last']
                }).dropna()
            elif timeframe == 'M5':
                df = df.resample('5T').agg({
                    'price': ['first', 'max', 'min', 'last']
                }).dropna()
            elif timeframe == 'M15':
                df = df.resample('15T').agg({
                    'price': ['first', 'max', 'min', 'last']
                }).dropna()
            elif timeframe == 'H1':
                df = df.resample('1H').agg({
                    'price': ['first', 'max', 'min', 'last']
                }).dropna()
            
            # Flatten column names
            df.columns = ['open', 'high', 'low', 'close']
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error constructing historical data from cache: {e}")
            return None
    
    def get_current_prices(self) -> Dict:
        """Get current prices for all symbols"""
        try:
            current_prices = {}
            
            for symbol, data in self.data_cache.items():
                if data['ticks']:
                    latest_tick = data['ticks'][-1]
                    current_prices[symbol] = {
                        'bid': latest_tick['bid'],
                        'ask': latest_tick['ask'],
                        'spread': latest_tick['spread'],
                        'timestamp': latest_tick['timestamp']
                    }
            
            return current_prices
            
        except Exception as e:
            self.logger.error(f"Error getting current prices: {e}")
            return {}
    
    def get_price_statistics(self, symbol: str, period_minutes: int = 60) -> Optional[Dict]:
        """Get price statistics for a symbol"""
        try:
            if symbol not in self.data_cache:
                return None
            
            # Get recent ticks
            cutoff_time = datetime.now() - timedelta(minutes=period_minutes)
            recent_ticks = [
                t for t in self.data_cache[symbol]['ticks']
                if t['timestamp'] > cutoff_time
            ]
            
            if not recent_ticks:
                return None
            
            prices = [t['bid'] for t in recent_ticks]
            
            return {
                'symbol': symbol,
                'period_minutes': period_minutes,
                'tick_count': len(recent_ticks),
                'current_price': prices[-1],
                'min_price': min(prices),
                'max_price': max(prices),
                'avg_price': np.mean(prices),
                'price_std': np.std(prices),
                'price_range': max(prices) - min(prices),
                'volatility': np.std(prices) / np.mean(prices) * 100 if np.mean(prices) > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting price statistics for {symbol}: {e}")
            return None
    
    def get_subscriber_count(self) -> int:
        """Get number of active subscribers"""
        return len(self.subscribers)
    
    def get_cache_status(self) -> Dict:
        """Get cache status information"""
        try:
            status = {
                'total_symbols': len(self.data_cache),
                'subscribers': len(self.subscribers),
                'is_running': self.is_running,
                'symbols': {}
            }
            
            for symbol, data in self.data_cache.items():
                status['symbols'][symbol] = {
                    'tick_count': len(data['ticks']),
                    'last_update': data['last_update'].isoformat(),
                    'price_history_count': len(data['price_history'])
                }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting cache status: {e}")
            return {}


class WebSocketDataFeed:
    """WebSocket-based data feed for real-time data"""
    
    def __init__(self, broker_api, websocket_url: str = None):
        self.broker = broker_api
        self.websocket_url = websocket_url
        self.subscribers = []
        self.is_running = False
        self.websocket = None
        self.logger = logging.getLogger(__name__)
        
    async def connect(self):
        """Connect to WebSocket feed"""
        try:
            if not WEBSOCKETS_AVAILABLE:
                self.logger.error("WebSockets library not available")
                return False
                
            if not self.websocket_url:
                self.logger.error("WebSocket URL not provided")
                return False
            
            self.websocket = await websockets.connect(self.websocket_url)
            self.logger.info(f"Connected to WebSocket: {self.websocket_url}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error connecting to WebSocket: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket feed"""
        try:
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
                self.logger.info("Disconnected from WebSocket")
                
        except Exception as e:
            self.logger.error(f"Error disconnecting from WebSocket: {e}")
    
    async def start(self):
        """Start WebSocket data feed"""
        try:
            if not await self.connect():
                return False
            
            self.is_running = True
            
            # Start message handling loop
            while self.is_running:
                try:
                    message = await self.websocket.recv()
                    data = json.loads(message)
                    
                    # Notify subscribers
                    await self._notify_subscribers(data)
                    
                except Exception as ws_exception:
                    if WEBSOCKETS_AVAILABLE and "ConnectionClosed" in str(type(ws_exception)):
                        self.logger.warning("WebSocket connection closed")
                        break
                    else:
                        self.logger.error(f"WebSocket error: {ws_exception}")
                        break
                except Exception as e:
                    self.logger.error(f"Error processing WebSocket message: {e}")
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting WebSocket feed: {e}")
            return False
    
    async def stop(self):
        """Stop WebSocket data feed"""
        self.is_running = False
        await self.disconnect()
    
    async def _notify_subscribers(self, data: Dict):
        """Notify subscribers of new data"""
        try:
            for subscriber in self.subscribers:
                try:
                    await subscriber['callback'](data)
                except Exception as e:
                    self.logger.error(f"Error notifying subscriber: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error notifying subscribers: {e}")
    
    def subscribe(self, callback: Callable, pairs: List[str] = None):
        """Subscribe to WebSocket data"""
        subscriber = {
            'callback': callback,
            'pairs': pairs or 'all'
        }
        self.subscribers.append(subscriber)
        self.logger.info(f"Subscribed to WebSocket data for {pairs or 'all pairs'}")
    
    def unsubscribe(self, callback: Callable):
        """Unsubscribe from WebSocket data"""
        self.subscribers = [s for s in self.subscribers if s['callback'] != callback]
        self.logger.info("Unsubscribed from WebSocket data")
