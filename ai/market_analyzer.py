"""
ระบบวิเคราะห์ตลาดสำหรับการเทรด Arbitrage
=========================================

ไฟล์นี้ทำหน้าที่:
- วิเคราะห์สภาพตลาดปัจจุบันและแนวโน้ม
- คำนวณความผันผวนและความสัมพันธ์ระหว่างคู่เงิน
- ระบุช่วงเวลาการเทรด (Session) และสภาพตลาด
- วิเคราะห์เทรนด์และสัญญาณทางเทคนิค
- เก็บข้อมูลสถิติตลาดเพื่อการตัดสินใจ

Author: AI Trading System
Version: 1.0
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import json

class MarketAnalyzer:
    """
    ระบบวิเคราะห์ตลาดหลัก
    
    รับผิดชอบในการวิเคราะห์สภาพตลาด ความผันผวน
    และความสัมพันธ์ระหว่างคู่เงินต่างๆ
    """
    
    def __init__(self, broker_api):
        """
        เริ่มต้นระบบวิเคราะห์ตลาด
        
        Args:
            broker_api: API สำหรับเชื่อมต่อกับโบรกเกอร์
        """
        self.broker = broker_api
        self.logger = logging.getLogger(__name__)
        self.market_conditions = {}
        self.volatility_cache = {}
        self.correlation_cache = {}
        
    def analyze_market_conditions(self, symbols: List[str] = None) -> Dict:
        """
        วิเคราะห์สภาพตลาดปัจจุบัน
        
        วิเคราะห์ข้อมูลตลาดสำหรับคู่เงินที่กำหนด
        รวมถึงเทรนด์ ความผันผวน และช่วงเวลาการเทรด
        
        Args:
            symbols: รายการคู่เงินที่ต้องการวิเคราะห์ (ถ้าไม่ระบุจะใช้ 10 คู่แรก)
            
        Returns:
            Dict: ข้อมูลสภาพตลาดที่วิเคราะห์แล้ว
        """
        try:
            if symbols is None:
                symbols = self.broker.get_available_pairs()[:10]  # Limit to first 10 for performance
            
            market_conditions = {
                'timestamp': datetime.now(),
                'overall_trend': 'neutral',
                'volatility_level': 'medium',
                'session_type': self._get_current_session(),
                'market_sentiment': 'neutral',
                'symbols_analyzed': len(symbols),
                'conditions': {}
            }
            
            # Analyze each symbol
            symbol_conditions = {}
            for symbol in symbols:
                symbol_condition = self._analyze_symbol_condition(symbol)
                if symbol_condition:
                    symbol_conditions[symbol] = symbol_condition
            
            market_conditions['conditions'] = symbol_conditions
            
            # Calculate overall market metrics
            if symbol_conditions:
                market_conditions.update(self._calculate_overall_metrics(symbol_conditions))
            
            # Cache the results
            self.market_conditions = market_conditions
            
            return market_conditions
            
        except Exception as e:
            self.logger.error(f"Error analyzing market conditions: {e}")
            return {}
    
    def _analyze_symbol_condition(self, symbol: str) -> Optional[Dict]:
        """Analyze condition for a specific symbol"""
        try:
            # Get historical data
            data_h1 = self.broker.get_historical_data(symbol, 'H1', 24)
            data_m15 = self.broker.get_historical_data(symbol, 'M15', 96)  # 24 hours of M15 data
            
            if data_h1 is None or data_m15 is None:
                return None
            
            # Calculate various indicators
            condition = {
                'symbol': symbol,
                'trend': self._calculate_trend(data_h1),
                'volatility': self._calculate_volatility(data_m15),
                'momentum': self._calculate_momentum(data_m15),
                'support_resistance': self._find_support_resistance(data_h1),
                'volume_profile': self._analyze_volume_profile(data_m15),
                'spread': self.broker.get_spread(symbol),
                'current_price': self.broker.get_current_price(symbol)
            }
            
            # Calculate additional metrics
            condition['trend_strength'] = self._calculate_trend_strength(data_h1)
            condition['volatility_percentile'] = self._get_volatility_percentile(symbol, condition['volatility'])
            condition['rsi'] = self._calculate_rsi(data_m15)
            condition['bollinger_position'] = self._calculate_bollinger_position(data_m15)
            
            return condition
            
        except Exception as e:
            self.logger.error(f"Error analyzing symbol {symbol}: {e}")
            return None
    
    def _calculate_trend(self, data: pd.DataFrame) -> str:
        """Calculate trend direction"""
        try:
            if len(data) < 20:
                return 'unknown'
            
            # Simple moving averages
            sma_20 = data['close'].rolling(20).mean()
            sma_50 = data['close'].rolling(50).mean()
            
            if len(sma_20) < 1 or len(sma_50) < 1:
                return 'unknown'
            
            current_price = data['close'].iloc[-1]
            sma_20_current = sma_20.iloc[-1]
            sma_50_current = sma_50.iloc[-1]
            
            if current_price > sma_20_current > sma_50_current:
                return 'bullish'
            elif current_price < sma_20_current < sma_50_current:
                return 'bearish'
            else:
                return 'sideways'
                
        except Exception as e:
            self.logger.error(f"Error calculating trend: {e}")
            return 'unknown'
    
    def _calculate_volatility(self, data: pd.DataFrame) -> float:
        """Calculate volatility (standard deviation of returns)"""
        try:
            if len(data) < 10:
                return 0.0
            
            returns = data['close'].pct_change().dropna()
            return returns.std() * 100  # Return as percentage
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility: {e}")
            return 0.0
    
    def _calculate_momentum(self, data: pd.DataFrame) -> float:
        """Calculate momentum indicator"""
        try:
            if len(data) < 14:
                return 0.0
            
            # Rate of Change (ROC)
            current_price = data['close'].iloc[-1]
            price_14_periods_ago = data['close'].iloc[-14]
            
            if price_14_periods_ago == 0:
                return 0.0
            
            momentum = ((current_price - price_14_periods_ago) / price_14_periods_ago) * 100
            return momentum
            
        except Exception as e:
            self.logger.error(f"Error calculating momentum: {e}")
            return 0.0
    
    def _find_support_resistance(self, data: pd.DataFrame) -> Dict:
        """Find support and resistance levels"""
        try:
            if len(data) < 20:
                return {'support': None, 'resistance': None, 'strength': 'weak'}
            
            # Use recent 20 periods for support/resistance
            recent_data = data.tail(20)
            
            # Find local highs and lows
            highs = recent_data['high'].rolling(5, center=True).max()
            lows = recent_data['low'].rolling(5, center=True).min()
            
            # Find resistance (local highs)
            resistance_levels = []
            for i in range(2, len(highs) - 2):
                if (highs.iloc[i] > highs.iloc[i-1] and 
                    highs.iloc[i] > highs.iloc[i+1] and
                    highs.iloc[i] > highs.iloc[i-2] and
                    highs.iloc[i] > highs.iloc[i+2]):
                    resistance_levels.append(highs.iloc[i])
            
            # Find support (local lows)
            support_levels = []
            for i in range(2, len(lows) - 2):
                if (lows.iloc[i] < lows.iloc[i-1] and 
                    lows.iloc[i] < lows.iloc[i+1] and
                    lows.iloc[i] < lows.iloc[i-2] and
                    lows.iloc[i] < lows.iloc[i+2]):
                    support_levels.append(lows.iloc[i])
            
            # Get strongest levels
            resistance = max(resistance_levels) if resistance_levels else None
            support = min(support_levels) if support_levels else None
            
            # Determine strength
            current_price = data['close'].iloc[-1]
            strength = 'weak'
            
            if resistance and support:
                price_range = resistance - support
                if price_range > 0:
                    distance_to_resistance = abs(current_price - resistance) / price_range
                    distance_to_support = abs(current_price - support) / price_range
                    
                    if distance_to_resistance < 0.1 or distance_to_support < 0.1:
                        strength = 'strong'
                    elif distance_to_resistance < 0.2 or distance_to_support < 0.2:
                        strength = 'medium'
            
            return {
                'support': support,
                'resistance': resistance,
                'strength': strength
            }
            
        except Exception as e:
            self.logger.error(f"Error finding support/resistance: {e}")
            return {'support': None, 'resistance': None, 'strength': 'weak'}
    
    def _analyze_volume_profile(self, data: pd.DataFrame) -> Dict:
        """Analyze volume profile (simplified)"""
        try:
            if 'volume' not in data.columns or len(data) < 10:
                return {'trend': 'unknown', 'strength': 'normal'}
            
            # Calculate volume trend
            recent_volume = data['volume'].tail(5).mean()
            earlier_volume = data['volume'].head(5).mean()
            
            if recent_volume > earlier_volume * 1.2:
                trend = 'increasing'
            elif recent_volume < earlier_volume * 0.8:
                trend = 'decreasing'
            else:
                trend = 'stable'
            
            # Determine strength
            avg_volume = data['volume'].mean()
            if recent_volume > avg_volume * 1.5:
                strength = 'high'
            elif recent_volume < avg_volume * 0.5:
                strength = 'low'
            else:
                strength = 'normal'
            
            return {
                'trend': trend,
                'strength': strength,
                'current_volume': recent_volume,
                'average_volume': avg_volume
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing volume profile: {e}")
            return {'trend': 'unknown', 'strength': 'normal'}
    
    def _calculate_trend_strength(self, data: pd.DataFrame) -> float:
        """Calculate trend strength (0-1)"""
        try:
            if len(data) < 20:
                return 0.0
            
            # Use ADX-like calculation
            high = data['high']
            low = data['low']
            close = data['close']
            
            # Calculate True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # Calculate Directional Movement
            dm_plus = high.diff()
            dm_minus = -low.diff()
            
            dm_plus[dm_plus < 0] = 0
            dm_minus[dm_minus < 0] = 0
            
            # Calculate smoothed values
            atr = tr.rolling(14).mean()
            dm_plus_smooth = dm_plus.rolling(14).mean()
            dm_minus_smooth = dm_minus.rolling(14).mean()
            
            # Calculate DI+ and DI-
            di_plus = 100 * (dm_plus_smooth / atr)
            di_minus = 100 * (dm_minus_smooth / atr)
            
            # Calculate DX
            dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
            
            # Calculate ADX (trend strength)
            adx = dx.rolling(14).mean()
            
            # Return latest ADX value normalized to 0-1
            latest_adx = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0
            return min(latest_adx / 100, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating trend strength: {e}")
            return 0.0
    
    def _get_volatility_percentile(self, symbol: str, current_volatility: float) -> float:
        """Get volatility percentile for symbol"""
        try:
            # Check cache first
            if symbol in self.volatility_cache:
                cache_time, percentiles = self.volatility_cache[symbol]
                if datetime.now() - cache_time < timedelta(hours=1):
                    return self._find_percentile(current_volatility, percentiles)
            
            # Calculate historical volatility percentiles
            data = self.broker.get_historical_data(symbol, 'H1', 24 * 7)  # 1 week of data
            if data is None or len(data) < 100:
                return 0.5  # Default to 50th percentile
            
            # Calculate rolling volatility
            returns = data['close'].pct_change().dropna()
            rolling_vol = returns.rolling(24).std() * 100  # 24-hour rolling volatility
            
            # Remove NaN values
            rolling_vol = rolling_vol.dropna()
            
            if len(rolling_vol) < 10:
                return 0.5
            
            # Calculate percentiles
            percentiles = np.percentile(rolling_vol, [10, 25, 50, 75, 90])
            
            # Cache the result
            self.volatility_cache[symbol] = (datetime.now(), percentiles)
            
            return self._find_percentile(current_volatility, percentiles)
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility percentile: {e}")
            return 0.5
    
    def _find_percentile(self, value: float, percentiles: np.ndarray) -> float:
        """Find percentile rank of value"""
        try:
            if value <= percentiles[0]:  # 10th percentile
                return 0.1
            elif value <= percentiles[1]:  # 25th percentile
                return 0.25
            elif value <= percentiles[2]:  # 50th percentile
                return 0.5
            elif value <= percentiles[3]:  # 75th percentile
                return 0.75
            elif value <= percentiles[4]:  # 90th percentile
                return 0.9
            else:
                return 0.95
                
        except Exception as e:
            self.logger.error(f"Error finding percentile: {e}")
            return 0.5
    
    def _calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate RSI indicator"""
        try:
            if len(data) < period + 1:
                return 50.0  # Neutral RSI
            
            close = data['close']
            delta = close.diff()
            
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(period).mean()
            avg_loss = loss.rolling(period).mean()
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
            
        except Exception as e:
            self.logger.error(f"Error calculating RSI: {e}")
            return 50.0
    
    def _calculate_bollinger_position(self, data: pd.DataFrame, period: int = 20) -> float:
        """Calculate position within Bollinger Bands"""
        try:
            if len(data) < period:
                return 0.5  # Middle position
            
            close = data['close']
            sma = close.rolling(period).mean()
            std = close.rolling(period).std()
            
            upper_band = sma + (2 * std)
            lower_band = sma - (2 * std)
            
            current_price = close.iloc[-1]
            upper = upper_band.iloc[-1]
            lower = lower_band.iloc[-1]
            
            if upper == lower:
                return 0.5
            
            # Return position as 0-1 (0 = lower band, 1 = upper band)
            position = (current_price - lower) / (upper - lower)
            return max(0, min(1, position))
            
        except Exception as e:
            self.logger.error(f"Error calculating Bollinger position: {e}")
            return 0.5
    
    def _get_current_session(self) -> str:
        """Determine current trading session"""
        try:
            now = datetime.now()
            hour = now.hour
            
            if 0 <= hour < 8:
                return 'asian'
            elif 8 <= hour < 16:
                return 'london'
            elif 13 <= hour < 21:
                return 'new_york'
            else:
                return 'overlap'
                
        except Exception as e:
            self.logger.error(f"Error getting current session: {e}")
            return 'unknown'
    
    def _calculate_overall_metrics(self, symbol_conditions: Dict) -> Dict:
        """Calculate overall market metrics"""
        try:
            trends = [cond['trend'] for cond in symbol_conditions.values() if 'trend' in cond]
            volatilities = [cond['volatility'] for cond in symbol_conditions.values() if 'volatility' in cond]
            
            # Overall trend
            bullish_count = trends.count('bullish')
            bearish_count = trends.count('bearish')
            total_trends = len(trends)
            
            if bullish_count > bearish_count * 1.5:
                overall_trend = 'bullish'
            elif bearish_count > bullish_count * 1.5:
                overall_trend = 'bearish'
            else:
                overall_trend = 'sideways'
            
            # Volatility level
            if volatilities:
                avg_volatility = np.mean(volatilities)
                if avg_volatility < 0.5:
                    volatility_level = 'low'
                elif avg_volatility > 1.5:
                    volatility_level = 'high'
                else:
                    volatility_level = 'medium'
            else:
                volatility_level = 'medium'
            
            # Market sentiment (simplified)
            if overall_trend == 'bullish' and volatility_level == 'medium':
                sentiment = 'positive'
            elif overall_trend == 'bearish' and volatility_level == 'high':
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
            
            return {
                'overall_trend': overall_trend,
                'volatility_level': volatility_level,
                'market_sentiment': sentiment,
                'bullish_symbols': bullish_count,
                'bearish_symbols': bearish_count,
                'average_volatility': np.mean(volatilities) if volatilities else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating overall metrics: {e}")
            return {}
    
    def get_market_summary(self) -> Dict:
        """Get current market summary"""
        try:
            if not self.market_conditions:
                return {'status': 'no_data', 'message': 'Market analysis not performed yet'}
            
            return {
                'status': 'success',
                'timestamp': self.market_conditions['timestamp'],
                'overall_trend': self.market_conditions.get('overall_trend', 'unknown'),
                'volatility_level': self.market_conditions.get('volatility_level', 'unknown'),
                'session_type': self.market_conditions.get('session_type', 'unknown'),
                'market_sentiment': self.market_conditions.get('market_sentiment', 'unknown'),
                'symbols_analyzed': self.market_conditions.get('symbols_analyzed', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting market summary: {e}")
            return {'status': 'error', 'message': str(e)}
