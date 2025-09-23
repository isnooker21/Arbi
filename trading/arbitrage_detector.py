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
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        
        # Initialize pairs and combinations after logger is set
        self.available_pairs = self._get_available_pairs()
        self.triangle_combinations = self._generate_triangle_combinations()
        
        # Log triangle combinations count
        self.logger.info(f"Available pairs: {len(self.available_pairs)}")
        self.logger.info(f"Generated {len(self.triangle_combinations)} triangle combinations (Major & Minor pairs only)")
    
    def _get_available_pairs(self) -> List[str]:
        """Get list of available trading pairs from broker"""
        try:
            all_pairs = self.broker.get_available_pairs()
            if not all_pairs:
                self.logger.warning("No pairs available from broker")
                return []
            
            # Filter only Major and Minor pairs
            major_minor_currencies = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD']
            available_pairs = []
            
            for pair in all_pairs:
                # Check if pair contains only major/minor currencies
                if len(pair) == 6:  # Standard pair format like EURUSD
                    currency1 = pair[:3]
                    currency2 = pair[3:]
                    if currency1 in major_minor_currencies and currency2 in major_minor_currencies:
                        available_pairs.append(pair)
            
            self.logger.info(f"Filtered {len(available_pairs)} Major/Minor pairs from broker")
            if len(available_pairs) <= 20:  # Show all if small number
                self.logger.info(f"Available pairs: {', '.join(available_pairs)}")
            else:  # Show first 20 if many
                self.logger.info(f"Available pairs (first 20): {', '.join(available_pairs[:20])}")
            return available_pairs
            
        except Exception as e:
            self.logger.error(f"Error getting available pairs: {e}")
            return []
        
    def _generate_triangle_combinations(self) -> List[Tuple[str, str, str]]:
        """
        สร้างรายการคู่เงินสามเหลี่ยมจากคู่เงินที่มีจริงในบัญชีเท่านั้น
        
        หลักการ: A/B × B/C = A/C (ราคาทางทฤษฎี)
        """
        combinations = []
        
        # Only use pairs that are actually available in the account
        available_pairs_set = set(self.available_pairs)
        
        # Generate triangles from available pairs
        for pair1 in self.available_pairs:
            currency1_base = pair1[:3]
            currency1_quote = pair1[3:]
            
            for pair2 in self.available_pairs:
                if pair2 == pair1:
                    continue
                    
                currency2_base = pair2[:3]
                currency2_quote = pair2[3:]
                
                # Check if pair1 and pair2 can form a triangle
                if currency1_quote == currency2_base:
                    # pair1 = A/B, pair2 = B/C, so we need A/C
                    currency3_base = currency1_base
                    currency3_quote = currency2_quote
                    pair3 = f"{currency3_base}{currency3_quote}"
                    
                    if pair3 in available_pairs_set:
                        triangle = (pair1, pair2, pair3)
                        combinations.append(triangle)
                
                elif currency1_base == currency2_quote:
                    # pair1 = A/B, pair2 = C/A, so we need C/B
                    currency3_base = currency2_base
                    currency3_quote = currency1_quote
                    pair3 = f"{currency3_base}{currency3_quote}"
                    
                    if pair3 in available_pairs_set:
                        triangle = (pair1, pair2, pair3)
                        combinations.append(triangle)
        
        # Remove duplicates and sort
        combinations = list(set(combinations))
        combinations.sort()
        
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
        loop_count = 0
        
        while self.is_running:
            try:
                loop_count += 1
                self.logger.info(f"🔍 Detection loop #{loop_count} - Checking {len(self.triangle_combinations)} triangles")
                
                self.detect_opportunities()
                
                # Sleep for 5 seconds between detection cycles (slower for better logging)
                threading.Event().wait(5.0)
            except Exception as e:
                self.logger.error(f"Detection error: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                threading.Event().wait(1)
        
        self.logger.info("🔍 Arbitrage detection stopped")
    
    def detect_opportunities(self):
        """Main detection method with multi-timeframe analysis"""
        try:
            triangles_checked = 0
            opportunities_found = 0
            valid_arbitrages = 0
            
            self.logger.info(f"🔍 Starting to check {len(self.triangle_combinations)} triangles...")
            
            for triangle in self.triangle_combinations:
                if not self.is_running:
                    break
                
                triangles_checked += 1
                
                # Calculate arbitrage percentage first (faster check)
                arbitrage_percent = self.calculate_arbitrage(triangle, triangles_checked)
                
                if arbitrage_percent is None:
                    continue
                
                valid_arbitrages += 1
                
                # Log every triangle for debugging
                self.logger.info(f"Triangle {triangles_checked}: {triangle} = {arbitrage_percent:.4f}%")
                
                # Only count as opportunity if > 0.001% (much lower threshold)
                if arbitrage_percent > 0.001:
                    opportunities_found += 1
                
                # Log every 10 triangles checked
                if triangles_checked % 10 == 0:
                    self.logger.info(f"Progress: {triangles_checked}/{len(self.triangle_combinations)} triangles, "
                                   f"{valid_arbitrages} valid arbitrages, {opportunities_found} opportunities")
                
                # Only do full analysis for opportunities > 0.001%
                if arbitrage_percent < 0.001:
                    continue
                
                # Multi-timeframe analysis (only for promising opportunities)
                h1_analysis = self.analyze_timeframe(triangle, 'H1')
                m30_analysis = self.analyze_timeframe(triangle, 'M30')
                m15_analysis = self.analyze_timeframe(triangle, 'M15')
                m5_analysis = self.analyze_timeframe(triangle, 'M5')
                m1_analysis = self.analyze_timeframe(triangle, 'M1')
                
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
                
                if ai_decision.should_act and ai_decision.confidence > 0.3:
                    self.logger.info(f"🎯 ARBITRAGE OPPORTUNITY: {triangle}, "
                                   f"Percent: {arbitrage_percent:.4f}%, "
                                   f"Confidence: {ai_decision.confidence:.2f}")
                    self.execute_triangle_entry(triangle, ai_decision)
                elif arbitrage_percent and arbitrage_percent > 0.005:
                    # Log opportunities that are close but don't meet criteria
                    self.logger.info(f"🔍 Near opportunity: {triangle}, "
                                   f"Percent: {arbitrage_percent:.4f}%, "
                                   f"Confidence: {ai_decision.confidence:.2f}")
            
            # Summary logging
            self.logger.info(f"🔍 Detection summary: {triangles_checked} triangles checked, "
                           f"{valid_arbitrages} valid arbitrages, {opportunities_found} opportunities found")
                    
        except Exception as e:
            self.logger.error(f"Error in detect_opportunities: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
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
    
    def calculate_arbitrage(self, triangle: Tuple[str, str, str], triangles_checked: int = 0) -> Optional[float]:
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
                # Log missing prices for first few triangles to debug
                if triangles_checked < 5:
                    self.logger.warning(f"Missing prices for {triangle}: {pair1}={price1}, {pair2}={price2}, {pair3}={price3}")
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
