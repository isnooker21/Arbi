"""
ระบบตรวจจับ Triangular Arbitrage

ไฟล์นี้ทำหน้าที่:
- ตรวจจับโอกาส Arbitrage แบบสามเหลี่ยมระหว่างคู่เงิน
- วิเคราะห์ข้อมูลหลาย Timeframe (M1, M5, M15, M30, H1)
- ใช้ AI Engine ในการประเมินและตัดสินใจ
- จัดการการเปิด/ปิดตำแหน่ง Arbitrage
- ติดตามผลการดำเนินงาน

ตัวอย่างการทำงาน:
1. ตรวจสอบราคา EUR/USD, GBP/USD, EUR/GBP
2. คำนวณ Arbitrage Percentage
3. ใช้ AI วิเคราะห์โอกาสและความเสี่ยง
4. เปิดตำแหน่งถ้าโอกาสดีและความเสี่ยงต่ำ
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
import asyncio
import threading

class TriangleArbitrageDetector:
    def __init__(self, broker_api, ai_engine):
        self.broker = broker_api
        self.ai = ai_engine
        self.active_triangles = {}
        self.triangle_combinations = self._generate_triangle_combinations()
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        
    def _generate_triangle_combinations(self) -> List[Tuple[str, str, str]]:
        """
        สร้างรายการคู่เงินทั้งหมดที่เป็นไปได้สำหรับ Triangular Arbitrage
        
        ตัวอย่าง:
        - EUR/USD, USD/JPY, EUR/JPY
        - GBP/USD, USD/CHF, GBP/CHF
        - AUD/USD, USD/CAD, AUD/CAD
        
        หลักการ: A/B × B/C = A/C (ราคาทางทฤษฎี)
        """
        # Major currency pairs for triangular arbitrage
        majors = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD']
        combinations = []
        
        for base in majors:
            for quote1 in majors:
                for quote2 in majors:
                    if base != quote1 and quote1 != quote2 and base != quote2:
                        # Create triangle: base/quote1, quote1/quote2, base/quote2
                        pair1 = f"{base}{quote1}"
                        pair2 = f"{quote1}{quote2}"
                        pair3 = f"{base}{quote2}"
                        combinations.append((pair1, pair2, pair3))
        
        return combinations
    
    def start_detection(self):
        """Start the arbitrage detection loop"""
        self.is_running = True
        self.logger.info("Starting arbitrage detection...")
        
        # Run detection in separate thread
        detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
        detection_thread.start()
    
    def stop_detection(self):
        """Stop the arbitrage detection loop"""
        self.is_running = False
        self.logger.info("Stopping arbitrage detection...")
    
    def _detection_loop(self):
        """Main detection loop"""
        self.logger.info("🔍 Arbitrage detection started")
        
        while self.is_running:
            try:
                self.detect_opportunities()
                # Sleep for 100ms between detection cycles
                threading.Event().wait(0.1)
            except Exception as e:
                self.logger.error(f"Detection error: {e}")
                threading.Event().wait(1)
        
        self.logger.info("🔍 Arbitrage detection stopped")
    
    def detect_opportunities(self):
        """Main detection method with multi-timeframe analysis"""
        try:
            for triangle in self.triangle_combinations:
                if not self.is_running:
                    break
                    
                # Multi-timeframe analysis
                h1_analysis = self.analyze_timeframe(triangle, 'H1')
                m30_analysis = self.analyze_timeframe(triangle, 'M30')
                m15_analysis = self.analyze_timeframe(triangle, 'M15')
                m5_analysis = self.analyze_timeframe(triangle, 'M5')
                m1_analysis = self.analyze_timeframe(triangle, 'M1')
                
                # Calculate arbitrage percentage
                arbitrage_percent = self.calculate_arbitrage(triangle)
                
                if arbitrage_percent is None:
                    continue
                
                # Create opportunity context
                opportunity = {
                    'triangle': triangle,
                    'h1': h1_analysis,
                    'm30': m30_analysis,
                    'm15': m15_analysis,
                    'm5': m5_analysis,
                    'm1': m1_analysis,
                    'arbitrage_percent': arbitrage_percent,
                    'timestamp': datetime.now(),
                    'spread_acceptable': self._check_spread_acceptable(triangle),
                    'volatility': self._calculate_volatility(triangle)
                }
                
                # AI evaluation
                ai_decision = self.ai.evaluate_arbitrage_opportunity(opportunity)
                
                if ai_decision.should_act and ai_decision.confidence > 0.7:
                    self.logger.info(f"Arbitrage opportunity detected: {triangle}, "
                                   f"Percent: {arbitrage_percent:.4f}%, "
                                   f"Confidence: {ai_decision.confidence:.2f}")
                    self.execute_triangle_entry(triangle, ai_decision)
                    
        except Exception as e:
            self.logger.error(f"Error in detect_opportunities: {e}")
    
    def analyze_timeframe(self, triangle: Tuple[str, str, str], timeframe: str) -> Dict:
        """Analyze triangle for specific timeframe"""
        try:
            pair1, pair2, pair3 = triangle
            
            # Get historical data for each pair
            data1 = self.broker.get_historical_data(pair1, timeframe, 100)
            data2 = self.broker.get_historical_data(pair2, timeframe, 100)
            data3 = self.broker.get_historical_data(pair3, timeframe, 100)
            
            if data1 is None or data2 is None or data3 is None:
                return {'status': 'no_data'}
            
            # Calculate trend
            trend1 = self._calculate_trend(data1)
            trend2 = self._calculate_trend(data2)
            trend3 = self._calculate_trend(data3)
            
            # Calculate structure
            structure1 = self._analyze_structure(data1)
            structure2 = self._analyze_structure(data2)
            structure3 = self._analyze_structure(data3)
            
            # Calculate volatility
            volatility1 = self._calculate_volatility(data1)
            volatility2 = self._calculate_volatility(data2)
            volatility3 = self._calculate_volatility(data3)
            
            return {
                'status': 'success',
                'trend': {
                    pair1: trend1,
                    pair2: trend2,
                    pair3: trend3
                },
                'structure': {
                    pair1: structure1,
                    pair2: structure2,
                    pair3: structure3
                },
                'volatility': {
                    pair1: volatility1,
                    pair2: volatility2,
                    pair3: volatility3
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing timeframe {timeframe} for {triangle}: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def calculate_arbitrage(self, triangle: Tuple[str, str, str]) -> Optional[float]:
        """
        คำนวณเปอร์เซ็นต์ Arbitrage แบบสามเหลี่ยมรวมต้นทุนการเทรดจริง
        
        ใช้สูตรใหม่ที่รวม Spread, Commission, และ Slippage
        """
        try:
            pair1, pair2, pair3 = triangle
            
            # Get current prices
            price1 = self.broker.get_current_price(pair1)
            price2 = self.broker.get_current_price(pair2)
            price3 = self.broker.get_current_price(pair3)
            
            if price1 is None or price2 is None or price3 is None:
                return None
            
            # Get spreads
            spread1 = self.broker.get_spread(pair1) if hasattr(self.broker, 'get_spread') else 0
            spread2 = self.broker.get_spread(pair2) if hasattr(self.broker, 'get_spread') else 0
            spread3 = self.broker.get_spread(pair3) if hasattr(self.broker, 'get_spread') else 0
            
            # Import TradingCalculations
            from utils.calculations import TradingCalculations
            
            # Calculate arbitrage with real trading costs
            arbitrage_percent = TradingCalculations.calculate_arbitrage_percentage(
                pair1_price=price1,
                pair2_price=price2,
                pair3_price=price3,
                spread1=spread1,
                spread2=spread2,
                spread3=spread3,
                commission_rate=0.0001,  # 0.01%
                slippage_percent=0.05,   # 0.05%
                minimum_threshold=0.1    # 0.1%
            )
            
            return arbitrage_percent if arbitrage_percent > 0 else None
            
        except Exception as e:
            self.logger.error(f"Error calculating arbitrage for {triangle}: {e}")
            return None
    
    def execute_triangle_entry(self, triangle: Tuple[str, str, str], ai_decision):
        """Execute triangle positions based on AI decision"""
        try:
            pair1, pair2, pair3 = triangle
            lot_size = ai_decision.position_size
            direction = ai_decision.direction
            
            orders = []
            
            # Place orders for each pair in the triangle
            for i, pair in enumerate(triangle):
                order_type = 'BUY' if direction.get(pair, 1) > 0 else 'SELL'
                order = self.broker.place_order(pair, order_type, lot_size)
                
                if order:
                    orders.append(order)
                else:
                    # If any order fails, cancel all previous orders
                    self.logger.error(f"Failed to place order for {pair}, cancelling triangle")
                    for prev_order in orders:
                        self.broker.cancel_order(prev_order['order_id'])
                    return False
            
            # Store active triangle
            self.active_triangles[triangle] = {
                'orders': orders,
                'entry_time': datetime.now(),
                'ai_decision': ai_decision,
                'status': 'active'
            }
            
            self.logger.info(f"Successfully executed triangle {triangle} with {len(orders)} orders")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing triangle entry for {triangle}: {e}")
            return False
    
    def close_triangle(self, triangle: Tuple[str, str, str], reason: str = "manual"):
        """Close all positions in a triangle"""
        try:
            if triangle not in self.active_triangles:
                return False
            
            triangle_data = self.active_triangles[triangle]
            orders = triangle_data['orders']
            
            # Close all orders
            for order in orders:
                self.broker.close_order(order['order_id'])
            
            # Update triangle status
            triangle_data['status'] = 'closed'
            triangle_data['close_time'] = datetime.now()
            triangle_data['close_reason'] = reason
            
            self.logger.info(f"Closed triangle {triangle} - Reason: {reason}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error closing triangle {triangle}: {e}")
            return False
    
    def _calculate_trend(self, data: pd.DataFrame) -> str:
        """Calculate trend from price data"""
        if len(data) < 20:
            return 'unknown'
        
        # Simple moving average trend
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
    
    def _analyze_structure(self, data: pd.DataFrame) -> str:
        """Analyze market structure"""
        if len(data) < 10:
            return 'unknown'
        
        # Look for support/resistance levels
        highs = data['high'].rolling(5).max()
        lows = data['low'].rolling(5).min()
        
        current_price = data['close'].iloc[-1]
        recent_high = highs.iloc[-1]
        recent_low = lows.iloc[-1]
        
        if current_price > recent_high * 0.99:
            return 'resistance'
        elif current_price < recent_low * 1.01:
            return 'support'
        else:
            return 'normal'
    
    def _calculate_volatility(self, data: pd.DataFrame) -> float:
        """Calculate volatility (standard deviation of returns)"""
        if len(data) < 10:
            return 0.0
        
        returns = data['close'].pct_change().dropna()
        return returns.std() * 100  # Return as percentage
    
    def _check_spread_acceptable(self, triangle: Tuple[str, str, str]) -> bool:
        """Check if spreads are acceptable for arbitrage"""
        try:
            pair1, pair2, pair3 = triangle
            
            spread1 = self.broker.get_spread(pair1)
            spread2 = self.broker.get_spread(pair2)
            spread3 = self.broker.get_spread(pair3)
            
            # Check if all spreads are below threshold
            max_spread = 0.5  # 0.5 pips
            return (spread1 < max_spread and 
                   spread2 < max_spread and 
                   spread3 < max_spread)
                   
        except Exception as e:
            self.logger.error(f"Error checking spread for {triangle}: {e}")
            return False
    
    def get_active_triangles(self) -> Dict:
        """Get all active triangles"""
        return self.active_triangles
    
    def get_triangle_performance(self) -> Dict:
        """Get performance statistics for triangles"""
        total_triangles = len(self.active_triangles)
        active_triangles = sum(1 for t in self.active_triangles.values() if t['status'] == 'active')
        closed_triangles = sum(1 for t in self.active_triangles.values() if t['status'] == 'closed')
        
        return {
            'total_triangles': total_triangles,
            'active_triangles': active_triangles,
            'closed_triangles': closed_triangles
        }
