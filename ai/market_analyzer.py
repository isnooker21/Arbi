"""
ระบบวิเคราะห์ตลาดแบบ Simplified สำหรับ Adaptive Arbitrage
=========================================================

ไฟล์นี้ทำหน้าที่:
- เน้นแค่ Market Regime Detection (volatile, trending, ranging, normal)
- วิเคราะห์ volatility และ trend detection
- เพิ่ม correlation stability analysis
- ปรับปรุง real-time performance
- ลบ complex analysis ที่ไม่ใช้

Author: AI Trading System
Version: 2.0 (Simplified)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import json

class MarketAnalyzer:
    """
    ระบบวิเคราะห์ตลาดแบบ Simplified
    
    รับผิดชอบในการวิเคราะห์ Market Regime Detection เท่านั้น
    เน้น performance และ real-time analysis
    """
    
    def __init__(self, broker_api):
        """
        เริ่มต้นระบบวิเคราะห์ตลาดแบบ Simplified
        
        Args:
            broker_api: API สำหรับเชื่อมต่อกับโบรกเกอร์
        """
        self.broker = broker_api
        self.logger = logging.getLogger(__name__)
        
        # Simplified market analysis
        self.market_regime = 'normal'
        self.volatility_level = 'medium'
        self.correlation_stability = 'stable'
        
        # Performance tracking
        self.analysis_cache = {}
        self.last_analysis_time = None
        self.analysis_interval = 300  # 5 minutes
        
        # Market regime thresholds
        self.regime_thresholds = {
            'volatility': {
                'low': 0.0005,
                'high': 0.002
            },
            'trend_strength': {
                'weak': 0.3,
                'strong': 0.7
            },
            'correlation_stability': {
                'unstable': 0.3,
                'stable': 0.7
            }
        }
        
    def analyze_market_conditions(self, symbols: List[str] = None) -> Dict:
        """
        วิเคราะห์ Market Regime Detection แบบ Simplified
        
        วิเคราะห์แค่ Market Regime, Volatility, และ Correlation Stability
        เน้น performance และ real-time analysis
        
        Args:
            symbols: รายการคู่เงินที่ต้องการวิเคราะห์ (ถ้าไม่ระบุจะใช้ 5 คู่แรก)
            
        Returns:
            Dict: ข้อมูล Market Regime ที่วิเคราะห์แล้ว
        """
        try:
            # Check if analysis is needed (cache-based)
            current_time = datetime.now()
            if (self.last_analysis_time and 
                (current_time - self.last_analysis_time).total_seconds() < self.analysis_interval):
                return self.analysis_cache.get('last_analysis', {})
            
            if symbols is None:
                symbols = self.broker.get_available_pairs()[:5]  # Limit to 5 for performance
            
            # Simplified market analysis
            market_analysis = {
                'timestamp': current_time,
                'market_regime': self.market_regime,
                'volatility_level': self.volatility_level,
                'correlation_stability': self.correlation_stability,
                'symbols_analyzed': len(symbols),
                'analysis_type': 'simplified_regime_detection'
            }
            
            # Analyze market regime
            regime_analysis = self._detect_market_regime(symbols)
            market_analysis.update(regime_analysis)
            
            # Analyze volatility
            volatility_analysis = self._analyze_volatility(symbols)
            market_analysis.update(volatility_analysis)
            
            # Analyze correlation stability
            correlation_analysis = self._analyze_correlation_stability(symbols)
            market_analysis.update(correlation_analysis)
            
            # Update cache
            self.analysis_cache['last_analysis'] = market_analysis
            self.last_analysis_time = current_time
            
            # Update class variables
            self.market_regime = market_analysis.get('market_regime', 'normal')
            self.volatility_level = market_analysis.get('volatility_level', 'medium')
            self.correlation_stability = market_analysis.get('correlation_stability', 'stable')
            
            self.logger.debug(f"Market regime analysis completed: {self.market_regime}, "
                            f"volatility: {self.volatility_level}, "
                            f"correlation: {self.correlation_stability}")
            
            return market_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing market conditions: {e}")
            return {}
    
    def _detect_market_regime(self, symbols: List[str]) -> Dict:
        """
        ตรวจจับ Market Regime ปัจจุบัน
        
        Args:
            symbols: รายการคู่เงินที่ใช้ในการวิเคราะห์
            
        Returns:
            Dict: ข้อมูล Market Regime
        """
        try:
            regime_indicators = []
            
            for symbol in symbols:
                try:
                    # Get H1 data for trend analysis
                    data = self.broker.get_historical_data(symbol, 'H1', 24)  # Last 24 hours
                    
                    if data is None or len(data) < 20:
                        continue
                    
                    # Calculate trend strength
                    trend_strength = self._calculate_trend_strength(data)
                    
                    # Calculate volatility
                    returns = data['close'].pct_change().dropna()
                    volatility = returns.std()
                    
                    # Determine regime for this symbol
                    if volatility > self.regime_thresholds['volatility']['high']:
                        regime_indicators.append('volatile')
                    elif trend_strength > self.regime_thresholds['trend_strength']['strong']:
                        regime_indicators.append('trending')
                    elif trend_strength < self.regime_thresholds['trend_strength']['weak']:
                        regime_indicators.append('ranging')
                    else:
                        regime_indicators.append('normal')
                        
                except Exception as e:
                    self.logger.warning(f"Error analyzing regime for {symbol}: {e}")
                    continue
            
            if regime_indicators:
                # Determine overall regime (most common)
                regime_counts = {}
                for regime in regime_indicators:
                    regime_counts[regime] = regime_counts.get(regime, 0) + 1
                
                # Get most common regime
                detected_regime = max(regime_counts, key=regime_counts.get)
                
                return {
                    'market_regime': detected_regime,
                    'regime_confidence': regime_counts[detected_regime] / len(regime_indicators),
                    'regime_distribution': regime_counts
                }
            else:
                return {
                    'market_regime': 'normal',
                    'regime_confidence': 0.0,
                    'regime_distribution': {}
                }
                
        except Exception as e:
            self.logger.error(f"Error detecting market regime: {e}")
            return {'market_regime': 'normal', 'regime_confidence': 0.0}
    
    def _analyze_volatility(self, symbols: List[str]) -> Dict:
        """
        วิเคราะห์ Market Volatility
        
        Args:
            symbols: รายการคู่เงินที่ใช้ในการวิเคราะห์
            
        Returns:
            Dict: ข้อมูล Volatility
        """
        try:
            volatilities = []
            
            for symbol in symbols:
                try:
                    # Get M15 data for volatility calculation
                    data = self.broker.get_historical_data(symbol, 'M15', 96)  # 24 hours of M15 data
                    
                    if data is None or len(data) < 20:
                        continue
                    
                    # Calculate volatility
                    returns = data['close'].pct_change().dropna()
                    volatility = returns.std()
                    volatilities.append(volatility)
                    
                except Exception as e:
                    self.logger.warning(f"Error calculating volatility for {symbol}: {e}")
                    continue
            
            if volatilities:
                avg_volatility = np.mean(volatilities)
                
                # Determine volatility level
                if avg_volatility < self.regime_thresholds['volatility']['low']:
                    volatility_level = 'low'
                elif avg_volatility > self.regime_thresholds['volatility']['high']:
                    volatility_level = 'high'
                else:
                    volatility_level = 'medium'
                
                return {
                    'volatility_level': volatility_level,
                    'avg_volatility': avg_volatility,
                    'volatility_range': (min(volatilities), max(volatilities))
                }
            else:
                return {
                    'volatility_level': 'medium',
                    'avg_volatility': 0.001,
                    'volatility_range': (0.001, 0.001)
                }
                
        except Exception as e:
            self.logger.error(f"Error analyzing volatility: {e}")
            return {'volatility_level': 'medium', 'avg_volatility': 0.001}
    
    def _analyze_correlation_stability(self, symbols: List[str]) -> Dict:
        """
        วิเคราะห์ Correlation Stability
        
        Args:
            symbols: รายการคู่เงินที่ใช้ในการวิเคราะห์
            
        Returns:
            Dict: ข้อมูล Correlation Stability
        """
        try:
            if len(symbols) < 2:
                return {'correlation_stability': 'stable', 'stability_score': 1.0}
            
            # Calculate correlation matrix
            correlation_matrix = []
            
            for i, symbol1 in enumerate(symbols):
                for j, symbol2 in enumerate(symbols):
                    if i >= j:
                        continue
                    
                    try:
                        # Get H1 data for both symbols
                        data1 = self.broker.get_historical_data(symbol1, 'H1', 24)
                        data2 = self.broker.get_historical_data(symbol2, 'H1', 24)
                        
                        if data1 is None or data2 is None:
                            continue
                        
                        # Calculate correlation
                        correlation = self._calculate_pair_correlation(data1, data2)
                        correlation_matrix.append(correlation)
                        
                    except Exception as e:
                        self.logger.warning(f"Error calculating correlation between {symbol1} and {symbol2}: {e}")
                        continue
            
            if correlation_matrix:
                # Calculate stability score (lower standard deviation = more stable)
                stability_score = 1.0 - np.std(correlation_matrix)
                stability_score = max(0, min(1, stability_score))  # Ensure 0-1 range
                
                # Determine stability level
                if stability_score < self.regime_thresholds['correlation_stability']['unstable']:
                    stability_level = 'unstable'
                elif stability_score > self.regime_thresholds['correlation_stability']['stable']:
                    stability_level = 'stable'
                else:
                    stability_level = 'moderate'
                
                return {
                    'correlation_stability': stability_level,
                    'stability_score': stability_score,
                    'avg_correlation': np.mean(correlation_matrix),
                    'correlation_std': np.std(correlation_matrix)
                }
            else:
                return {
                    'correlation_stability': 'stable',
                    'stability_score': 1.0,
                    'avg_correlation': 0.0,
                    'correlation_std': 0.0
                }
                
        except Exception as e:
            self.logger.error(f"Error analyzing correlation stability: {e}")
            return {'correlation_stability': 'stable', 'stability_score': 1.0}
    
    def _calculate_trend_strength(self, data: pd.DataFrame) -> float:
        """Calculate trend strength (0-1)"""
        try:
            if len(data) < 20:
                return 0.0
            
            # Simple trend strength calculation using moving averages
            sma_10 = data['close'].rolling(10).mean()
            sma_20 = data['close'].rolling(20).mean()
            
            if len(sma_10) < 1 or len(sma_20) < 1:
                return 0.0
            
            # Calculate trend strength as percentage difference
            current_sma_10 = sma_10.iloc[-1]
            current_sma_20 = sma_20.iloc[-1]
            
            if current_sma_20 == 0:
                return 0.0
            
            trend_strength = abs(current_sma_10 - current_sma_20) / current_sma_20
            
            return min(trend_strength, 1.0)  # Cap at 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating trend strength: {e}")
            return 0.0
    
    def _calculate_pair_correlation(self, data1: pd.DataFrame, data2: pd.DataFrame) -> float:
        """Calculate correlation between two pairs"""
        try:
            # Align data by timestamp
            merged = pd.merge(data1[['close']], data2[['close']], 
                            left_index=True, right_index=True, 
                            suffixes=('_1', '_2'))
            
            if len(merged) < 10:
                return 0.0
            
            # Calculate returns
            returns1 = merged['close_1'].pct_change().dropna()
            returns2 = merged['close_2'].pct_change().dropna()
            
            # Align returns
            aligned_returns = pd.merge(returns1, returns2, left_index=True, right_index=True)
            
            if len(aligned_returns) < 5:
                return 0.0
            
            # Calculate correlation
            correlation = aligned_returns['close_1'].corr(aligned_returns['close_2'])
            
            return correlation if not np.isnan(correlation) else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating pair correlation: {e}")
            return 0.0
    
    def get_market_regime_summary(self) -> Dict:
        """Get current market regime summary"""
        try:
            return {
                'market_regime': self.market_regime,
                'volatility_level': self.volatility_level,
                'correlation_stability': self.correlation_stability,
                'last_analysis_time': self.last_analysis_time,
                'analysis_interval': self.analysis_interval
            }
            
        except Exception as e:
            self.logger.error(f"Error getting market regime summary: {e}")
            return {}
    
    def update_regime_thresholds(self, new_thresholds: Dict):
        """Update regime detection thresholds"""
        try:
            if 'volatility' in new_thresholds:
                self.regime_thresholds['volatility'].update(new_thresholds['volatility'])
            
            if 'trend_strength' in new_thresholds:
                self.regime_thresholds['trend_strength'].update(new_thresholds['trend_strength'])
            
            if 'correlation_stability' in new_thresholds:
                self.regime_thresholds['correlation_stability'].update(new_thresholds['correlation_stability'])
            
            self.logger.info(f"Regime thresholds updated: {new_thresholds}")
            
        except Exception as e:
            self.logger.error(f"Error updating regime thresholds: {e}")
    
    def force_regime_analysis(self, symbols: List[str] = None) -> Dict:
        """Force immediate regime analysis (bypass cache)"""
        try:
            # Reset cache to force analysis
            self.last_analysis_time = None
            
            # Perform analysis
            return self.analyze_market_conditions(symbols)
            
        except Exception as e:
            self.logger.error(f"Error forcing regime analysis: {e}")
            return {}
    
    def get_market_summary(self) -> Dict:
        """Get current market summary (simplified)"""
        try:
            if not self.analysis_cache.get('last_analysis'):
                return {'status': 'no_data', 'message': 'Market analysis not performed yet'}
            
            last_analysis = self.analysis_cache['last_analysis']
            
            return {
                'status': 'success',
                'timestamp': last_analysis.get('timestamp'),
                'market_regime': last_analysis.get('market_regime', 'unknown'),
                'volatility_level': last_analysis.get('volatility_level', 'unknown'),
                'correlation_stability': last_analysis.get('correlation_stability', 'unknown'),
                'regime_confidence': last_analysis.get('regime_confidence', 0.0),
                'symbols_analyzed': last_analysis.get('symbols_analyzed', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting market summary: {e}")
            return {'status': 'error', 'message': str(e)}
    
