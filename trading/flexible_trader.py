"""
ระบบเทรดแบบยืดหยุ่น (Flexible Trading System)

ไฟล์นี้ทำหน้าที่:
- ตรวจจับโอกาสเทรดที่ไม่ใช่ pure arbitrage
- Trend Following: ตามแนวโน้ม
- Momentum Trading: เทรดตามแรงส่ง
- Scalping: เทรดระยะสั้น
- Grid Trading: เทรดแบบกริด
- Breakout Trading: เทรดตาม breakout
- Mean Reversion: เทรดตามการกลับสู่ค่าเฉลี่ย

Author: AI Trading System
Version: 1.0
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
import threading
import json

class FlexibleTrader:
    def __init__(self, broker_api, ai_engine):
        self.broker = broker_api
        self.ai = ai_engine
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        
        # Load flexible trading settings
        self.settings = self._load_flexible_settings()
        
        # Trading state
        self.active_positions = {}
        self.trading_history = []
        
    def _load_flexible_settings(self) -> Dict:
        """Load flexible trading settings from config"""
        try:
            with open('config/settings.json', 'r') as f:
                config = json.load(f)
                return config.get('flexible_trading', {
                    'enable_trend_following': True,
                    'enable_momentum_trading': True,
                    'enable_scalping': True,
                    'enable_grid_trading': True,
                    'min_trend_strength': 0.3,
                    'min_momentum_threshold': 0.001,
                    'scalp_threshold': 0.0005,
                    'grid_spacing': 0.001
                })
        except Exception as e:
            self.logger.error(f"Error loading flexible settings: {e}")
            return {}
    
    def start_flexible_trading(self):
        """Start flexible trading system"""
        self.is_running = True
        self.logger.info("🚀 Starting flexible trading system...")
        
        # Run in separate thread
        trading_thread = threading.Thread(target=self._trading_loop, daemon=True)
        trading_thread.start()
    
    def stop_flexible_trading(self):
        """Stop flexible trading system"""
        self.is_running = False
        self.logger.info("🛑 Stopping flexible trading system...")
    
    def _trading_loop(self):
        """Main flexible trading loop"""
        self.logger.info("🚀 Flexible trading loop started")
        loop_count = 0
        
        while self.is_running:
            try:
                loop_count += 1
                self.logger.info(f"🚀 Flexible trading loop #{loop_count}")
                
                # Get available pairs
                available_pairs = self.broker.get_available_pairs()
                if not available_pairs:
                    self.logger.warning("No pairs available for flexible trading")
                    threading.Event().wait(10)
                    continue
                
                # Filter Major/Minor pairs
                major_minor_pairs = self._filter_major_minor_pairs(available_pairs)
                self.logger.info(f"Checking {len(major_minor_pairs)} pairs for flexible trading opportunities")
                
                opportunities_found = 0
                
                # Check each pair for different trading opportunities
                for pair in major_minor_pairs:
                    if not self.is_running:
                        break
                    
                    # Check different trading strategies
                    if self.settings.get('enable_trend_following', True):
                        if self._check_trend_following(pair):
                            opportunities_found += 1
                    
                    if self.settings.get('enable_momentum_trading', True):
                        if self._check_momentum_trading(pair):
                            opportunities_found += 1
                    
                    if self.settings.get('enable_scalping', True):
                        if self._check_scalping(pair):
                            opportunities_found += 1
                    
                    if self.settings.get('enable_grid_trading', True):
                        if self._check_grid_trading(pair):
                            opportunities_found += 1
                
                self.logger.info(f"🚀 Found {opportunities_found} flexible trading opportunities")
                
                # Sleep for 10 seconds between checks
                threading.Event().wait(10.0)
                
            except Exception as e:
                self.logger.error(f"Flexible trading error: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                threading.Event().wait(5)
        
        self.logger.info("🚀 Flexible trading loop stopped")
    
    def _filter_major_minor_pairs(self, all_pairs: List[str]) -> List[str]:
        """Filter only Major and Minor pairs"""
        major_minor_currencies = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD']
        filtered_pairs = []
        
        for pair in all_pairs:
            if len(pair) == 6:  # Standard pair format
                currency1 = pair[:3]
                currency2 = pair[3:]
                if currency1 in major_minor_currencies and currency2 in major_minor_currencies:
                    filtered_pairs.append(pair)
        
        return filtered_pairs
    
    def _check_trend_following(self, pair: str) -> bool:
        """Check for trend following opportunities"""
        try:
            # Get recent price data
            data = self.broker.get_historical_data(pair, 'M15', 100)
            if data is None or len(data) < 50:
                return False
            
            # Calculate trend strength using moving averages
            prices = [candle['close'] for candle in data]
            
            # Short and long moving averages
            sma_20 = np.mean(prices[-20:])
            sma_50 = np.mean(prices[-50:])
            
            # Trend strength calculation
            trend_strength = abs(sma_20 - sma_50) / sma_50
            
            if trend_strength > self.settings.get('min_trend_strength', 0.3):
                # Check momentum
                price_momentum = (prices[-1] - prices[-10]) / prices[-10]
                
                if abs(price_momentum) > self.settings.get('min_momentum_threshold', 0.001):
                    self.logger.info(f"📈 Trend Following Opportunity: {pair}, "
                                   f"Trend: {trend_strength:.4f}, Momentum: {price_momentum:.4f}")
                    
                    # Create opportunity context
                    opportunity = {
                        'pair': pair,
                        'trading_type': 'trend_following',
                        'trend_strength': trend_strength,
                        'price_momentum': price_momentum,
                        'direction': 'BUY' if price_momentum > 0 else 'SELL',
                        'timestamp': datetime.now()
                    }
                    
                    # AI evaluation
                    ai_decision = self.ai.evaluate_flexible_opportunity(opportunity)
                    
                    if ai_decision.should_act and ai_decision.confidence > 0.2:
                        self.logger.info(f"🎯 EXECUTING Trend Following: {pair}, "
                                       f"Direction: {opportunity['direction']}, "
                                       f"Confidence: {ai_decision.confidence:.2f}")
                        self._execute_flexible_trade(opportunity, ai_decision)
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking trend following for {pair}: {e}")
            return False
    
    def _check_momentum_trading(self, pair: str) -> bool:
        """Check for momentum trading opportunities"""
        try:
            # Get recent price data
            data = self.broker.get_historical_data(pair, 'M5', 50)
            if data is None or len(data) < 20:
                return False
            
            prices = [candle['close'] for candle in data]
            
            # Calculate momentum indicators
            rsi = self._calculate_rsi(prices, 14)
            momentum = (prices[-1] - prices[-5]) / prices[-5]
            
            # Check for strong momentum
            if abs(momentum) > self.settings.get('min_momentum_threshold', 0.001):
                # Check volatility
                volatility = np.std(prices[-10:]) / np.mean(prices[-10:])
                
                if volatility > 0.1:  # Sufficient volatility
                    self.logger.info(f"⚡ Momentum Opportunity: {pair}, "
                                   f"Momentum: {momentum:.4f}, RSI: {rsi:.2f}, Vol: {volatility:.4f}")
                    
                    opportunity = {
                        'pair': pair,
                        'trading_type': 'momentum',
                        'momentum': momentum,
                        'rsi': rsi,
                        'volatility': volatility,
                        'direction': 'BUY' if momentum > 0 else 'SELL',
                        'timestamp': datetime.now()
                    }
                    
                    ai_decision = self.ai.evaluate_flexible_opportunity(opportunity)
                    
                    if ai_decision.should_act and ai_decision.confidence > 0.2:
                        self.logger.info(f"🎯 EXECUTING Momentum Trade: {pair}, "
                                       f"Direction: {opportunity['direction']}, "
                                       f"Confidence: {ai_decision.confidence:.2f}")
                        self._execute_flexible_trade(opportunity, ai_decision)
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking momentum for {pair}: {e}")
            return False
    
    def _check_scalping(self, pair: str) -> bool:
        """Check for scalping opportunities"""
        try:
            # Get very recent data
            data = self.broker.get_historical_data(pair, 'M1', 20)
            if data is None or len(data) < 10:
                return False
            
            prices = [candle['close'] for candle in data]
            
            # Check for small but consistent moves
            price_change = (prices[-1] - prices[-5]) / prices[-5]
            
            if abs(price_change) > self.settings.get('scalp_threshold', 0.0005):
                # Check spread
                current_price = self.broker.get_current_price(pair)
                if current_price:
                    spread = self.broker.get_spread(pair) if hasattr(self.broker, 'get_spread') else 0
                    
                    if spread < 1.5:  # Low spread for scalping
                        self.logger.info(f"⚡ Scalping Opportunity: {pair}, "
                                       f"Change: {price_change:.4f}, Spread: {spread}")
                        
                        opportunity = {
                            'pair': pair,
                            'trading_type': 'scalping',
                            'price_change': price_change,
                            'spread': spread,
                            'direction': 'BUY' if price_change > 0 else 'SELL',
                            'timestamp': datetime.now()
                        }
                        
                        ai_decision = self.ai.evaluate_flexible_opportunity(opportunity)
                        
                        if ai_decision.should_act and ai_decision.confidence > 0.2:
                            self.logger.info(f"🎯 EXECUTING Scalp Trade: {pair}, "
                                           f"Direction: {opportunity['direction']}, "
                                           f"Confidence: {ai_decision.confidence:.2f}")
                            self._execute_flexible_trade(opportunity, ai_decision)
                            return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking scalping for {pair}: {e}")
            return False
    
    def _check_grid_trading(self, pair: str) -> bool:
        """Check for grid trading opportunities"""
        try:
            # Get recent data to check if market is ranging
            data = self.broker.get_historical_data(pair, 'M15', 50)
            if data is None or len(data) < 30:
                return False
            
            prices = [candle['close'] for candle in data]
            
            # Check if market is ranging (low volatility, sideways movement)
            volatility = np.std(prices[-20:]) / np.mean(prices[-20:])
            price_range = (max(prices[-20:]) - min(prices[-20:])) / np.mean(prices[-20:])
            
            if volatility < 0.5 and price_range < 0.01:  # Ranging market
                self.logger.info(f"📊 Grid Trading Opportunity: {pair}, "
                               f"Volatility: {volatility:.4f}, Range: {price_range:.4f}")
                
                opportunity = {
                    'pair': pair,
                    'trading_type': 'grid',
                    'volatility': volatility,
                    'price_range': price_range,
                    'direction': 'BOTH',  # Grid trading both directions
                    'timestamp': datetime.now()
                }
                
                ai_decision = self.ai.evaluate_flexible_opportunity(opportunity)
                
                if ai_decision.should_act and ai_decision.confidence > 0.2:
                    self.logger.info(f"🎯 EXECUTING Grid Trade: {pair}, "
                                   f"Confidence: {ai_decision.confidence:.2f}")
                    self._execute_flexible_trade(opportunity, ai_decision)
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking grid trading for {pair}: {e}")
            return False
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _execute_flexible_trade(self, opportunity: Dict, ai_decision):
        """Execute flexible trading opportunity"""
        try:
            pair = opportunity['pair']
            direction = opportunity['direction']
            lot_size = ai_decision.position_size if hasattr(ai_decision, 'position_size') else 0.1
            
            if direction == 'BOTH':  # Grid trading
                # Place both buy and sell orders
                buy_order = self.broker.place_order(pair, 'BUY', lot_size)
                sell_order = self.broker.place_order(pair, 'SELL', lot_size)
                
                if buy_order and sell_order:
                    self.logger.info(f"✅ Grid orders placed for {pair}")
                    self.active_positions[pair] = {
                        'type': 'grid',
                        'orders': [buy_order, sell_order],
                        'entry_time': datetime.now()
                    }
            else:
                # Single direction trade
                order = self.broker.place_order(pair, direction, lot_size)
                
                if order:
                    self.logger.info(f"✅ {direction} order placed for {pair}")
                    self.active_positions[pair] = {
                        'type': opportunity['trading_type'],
                        'orders': [order],
                        'entry_time': datetime.now(),
                        'direction': direction
                    }
                else:
                    self.logger.error(f"Failed to place {direction} order for {pair}")
            
        except Exception as e:
            self.logger.error(f"Error executing flexible trade: {e}")
    
    def get_trading_summary(self) -> Dict:
        """Get summary of flexible trading performance"""
        return {
            'active_positions': len(self.active_positions),
            'total_trades': len(self.trading_history),
            'is_running': self.is_running
        }
