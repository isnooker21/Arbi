"""
ระบบตรวจจับ Triangular Arbitrage แบบ Adaptive
==============================================

ไฟล์นี้ทำหน้าที่:
- ตรวจจับโอกาส Arbitrage แบบสามเหลี่ยมระหว่างคู่เงิน 28 คู่หลัก
- ปรับ threshold แบบ Dynamic ตาม market volatility
- ปรับปรุง triangle generation ใช้ 28 pairs จริง
- เพิ่ม execution speed optimization
- เพิ่ม market regime detection
- ระบบ Never-Cut-Loss โดยใช้ Correlation Recovery

ตัวอย่างการทำงาน:
1. ตรวจสอบราคา EUR/USD, GBP/USD, EUR/GBP
2. คำนวณ Adaptive Threshold ตาม volatility
3. ใช้ AI วิเคราะห์โอกาสและความเสี่ยง
4. เปิดตำแหน่งถ้าโอกาสดีและความเสี่ยงต่ำ
5. ใช้ Correlation Recovery แทนการ cut loss
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
import asyncio
import threading
# import talib  # ไม่ใช้ในระบบนี้
import time

class TriangleArbitrageDetector:
    def __init__(self, broker_api, ai_engine, correlation_manager=None):
        self.broker = broker_api
        self.ai = ai_engine
        self.correlation_manager = correlation_manager  # เพิ่ม correlation manager
        self.active_triangles = {}
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        
        # Adaptive parameters - More strict and accurate
        self.current_regime = 'normal'  # volatile, trending, ranging, normal
        self.arbitrage_threshold = 0.008  # Higher threshold (0.8 pips) for better accuracy
        self.execution_timeout = 150  # Target execution speed
        self.position_size = 0.1  # Default position size
        
        # Enhanced validation parameters
        self.min_confidence_score = 0.75  # Minimum confidence score (75%)
        self.max_spread_ratio = 0.3  # Maximum spread ratio (30%)
        self.min_volume_threshold = 0.5  # Minimum volume threshold
        self.price_stability_checks = 3  # Number of price stability checks
        self.confirmation_delay = 2  # Seconds to wait for confirmation
        
        # Group management for single arbitrage entry
        self.active_groups = {}  # เก็บข้อมูลกลุ่มที่เปิดอยู่
        self.group_counter = 0   # ตัวนับกลุ่ม
        self.is_arbitrage_paused = False  # หยุดตรวจสอบ arbitrage ใหม่
        self.used_currency_pairs = set()  # เก็บคู่เงินที่ถูกใช้ในกลุ่มที่ยังเปิดอยู่
        self.group_currency_mapping = {}  # เก็บการแมปกลุ่มกับคู่เงินที่ใช้
        
        # ระบบส่งออเดอร์รอบเดียวทันที
        self.arbitrage_sent = False  # ตรวจสอบว่าส่งออเดอร์ arbitrage แล้วหรือไม่
        self.arbitrage_send_time = None  # เวลาที่ส่งออเดอร์ arbitrage
        
        # Rate limiting for order placement
        self.last_order_time = 0  # เวลาที่ส่งออเดอร์ล่าสุด
        self.min_order_interval = 10  # ระยะห่างขั้นต่ำระหว่างออเดอร์ (วินาที)
        self.daily_order_limit = 50  # จำกัดออเดอร์ต่อวัน
        self.daily_order_count = 0  # จำนวนออเดอร์ที่ส่งวันนี้
        self.last_reset_date = datetime.now().date()  # วันที่รีเซ็ตตัวนับ
        self.regime_parameters = {
            'volatile': {'threshold': 0.012, 'timeout': 200},    # 1.2 pips (เข้มขึ้น)
            'trending': {'threshold': 0.010, 'timeout': 150},   # 1.0 pips (เข้มขึ้น)
            'ranging': {'threshold': 0.008, 'timeout': 100},    # 0.8 pips (เข้มขึ้น)
            'normal': {'threshold': 0.008, 'timeout': 150}      # 0.8 pips (เข้มขึ้น)
        }
        
        # Performance tracking
        self.total_opportunities_detected = 0
        self.performance_metrics = {
            'total_opportunities': 0,
            'successful_trades': 0,
            'avg_execution_time': 0,
            'market_regime_changes': 0
        }
        
        # Initialize pairs and combinations after logger is set
        self.available_pairs = self._get_available_pairs()
        
        # ใช้เฉพาะคู่เงิน Arbitrage 3 คู่ที่กำหนด
        self.arbitrage_pairs = ['EURUSD', 'GBPUSD', 'EURGBP']
        self.triangle_combinations = self._generate_fixed_triangle_combinations()
        
        # Log triangle combinations count
        self.logger.info(f"Available pairs: {len(self.available_pairs)}")
        self.logger.info(f"Generated {len(self.triangle_combinations)} triangle combinations (Major & Minor pairs only)")
        
        # Debug: Show first few pairs
        if self.available_pairs:
            self.logger.info(f"First 5 pairs: {self.available_pairs[:5]}")
        else:
            self.logger.warning("⚠️ No available pairs found!")
        
        # If no triangles generated, create fallback triangles
        if len(self.triangle_combinations) == 0 and len(self.available_pairs) > 0:
            self.logger.warning("No triangles generated, creating fallback triangles...")
            self.triangle_combinations = self._create_fallback_triangles()
            self.logger.info(f"Created {len(self.triangle_combinations)} fallback triangle combinations")
        elif len(self.triangle_combinations) == 0:
            self.logger.error("❌ No triangles generated and no available pairs!")
    
    def _get_available_pairs(self) -> List[str]:
        """Get list of available trading pairs from broker"""
        try:
            # Call broker method directly (it has its own fallback logic)
            all_pairs = self.broker.get_available_pairs()
            self.logger.info(f"Raw pairs from broker: {len(all_pairs) if all_pairs else 0}")
            if all_pairs and len(all_pairs) > 0:
                self.logger.info(f"First 5 raw pairs: {all_pairs[:5]}")
            
            if not all_pairs:
                self.logger.warning("No pairs available from broker")
                # Return hardcoded pairs as fallback
                fallback_pairs = [
                    'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'USDCAD', 'AUDUSD', 'NZDUSD',
                    'EURGBP', 'EURJPY', 'EURCHF', 'EURCAD', 'EURAUD', 'EURNZD',
                    'GBPEUR', 'GBPJPY', 'GBPCHF', 'GBPCAD', 'GBPAUD', 'GBPNZD',
                    'JPYEUR', 'JPYUSD', 'JPYGBP', 'JPYCHF', 'JPYCAD', 'JPYAUD', 'JPYNZD',
                    'CHFEUR', 'CHFUSD', 'CHFGBP', 'CHFJPY', 'CHFCAD', 'CHFAUD', 'CHFNZD',
                    'CADEUR', 'CADUSD', 'CADGBP', 'CADJPY', 'CADCHF', 'CADAUD', 'CADNZD',
                    'AUDEUR', 'AUDUSD', 'AUDGBP', 'AUDJPY', 'AUDCHF', 'AUDCAD', 'AUDNZD',
                    'NZDEUR', 'NZDUSD', 'NZDGBP', 'NZDJPY', 'NZDCHF', 'NZDCAD', 'NZDAUD'
                ]
                self.logger.warning(f"Using fallback pairs: {len(fallback_pairs)} pairs")
                return fallback_pairs
            
            # Filter only Major and Minor pairs
            major_minor_currencies = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD']
            available_pairs = []
            
            for pair in all_pairs:
                # Debug logging for first few pairs
                if len(available_pairs) < 5:
                    self.logger.info(f"Processing pair: {pair} (type: {type(pair)})")
                
                # Handle both string and dict formats
                pair_str = pair if isinstance(pair, str) else str(pair)
                
                # Check if pair contains only major/minor currencies
                if len(pair_str) == 6:  # Standard pair format like EURUSD
                    currency1 = pair_str[:3]
                    currency2 = pair_str[3:]
                    if currency1 in major_minor_currencies and currency2 in major_minor_currencies:
                        available_pairs.append(pair_str)
            
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
        
        self.logger.info(f"Generating triangles from {len(self.available_pairs)} available pairs")
        
        # Only use pairs that are actually available in the account
        available_pairs_set = set(self.available_pairs)
        self.logger.info(f"Available pairs set: {len(available_pairs_set)}")
        
        # Generate triangles from available pairs
        triangles_found = 0
        for i, pair1 in enumerate(self.available_pairs):
            if i < 3:  # Debug first few pairs
                self.logger.info(f"Processing pair1: {pair1}")
            
            currency1_base = pair1[:3]
            currency1_quote = pair1[3:]
            
            for j, pair2 in enumerate(self.available_pairs):
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
                        triangles_found += 1
                        if triangles_found <= 5:  # Log first few triangles
                            self.logger.info(f"Found triangle {triangles_found}: {triangle}")
                
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
        
        self.logger.info(f"Generated {len(combinations)} unique triangle combinations")
        
        return combinations
    
    def _generate_fixed_triangle_combinations(self) -> List[Tuple[str, str, str]]:
        """
        สร้าง triangle combinations จากคู่เงิน Arbitrage ที่กำหนด
        ใช้เฉพาะ EURUSD, GBPUSD, EURGBP
        """
        combinations = []
        
        # ตรวจสอบว่าคู่เงินที่กำหนดมีอยู่ใน available_pairs หรือไม่
        available_pairs_set = set(self.available_pairs)
        valid_arbitrage_pairs = [pair for pair in self.arbitrage_pairs if pair in available_pairs_set]
        
        if len(valid_arbitrage_pairs) < 3:
            self.logger.warning(f"⚠️ คู่เงิน Arbitrage ที่กำหนดไม่ครบ 3 คู่")
            self.logger.warning(f"   คู่เงินที่กำหนด: {self.arbitrage_pairs}")
            self.logger.warning(f"   คู่เงินที่ใช้ได้: {valid_arbitrage_pairs}")
            return []
        
        # สร้าง triangle combination จากคู่เงินที่กำหนด
        # EURUSD, GBPUSD, EURGBP
        triangle = (valid_arbitrage_pairs[0], valid_arbitrage_pairs[1], valid_arbitrage_pairs[2])
        combinations.append(triangle)
        
        self.logger.info(f"✅ สร้าง triangle combination จากคู่เงินที่กำหนด: {triangle}")
        self.logger.info(f"   คู่เงิน Arbitrage: {valid_arbitrage_pairs}")
        
        return combinations
    
    def _create_fallback_triangles(self) -> List[Tuple[str, str, str]]:
        """Create fallback triangle combinations when normal generation fails"""
        fallback_triangles = []
        
        # Common triangle patterns
        common_triangles = [
            ('EURUSD', 'USDJPY', 'EURJPY'),
            ('GBPUSD', 'USDJPY', 'GBPJPY'),
            ('EURUSD', 'USDCHF', 'EURCHF'),
            ('GBPUSD', 'USDCHF', 'GBPCHF'),
            ('EURUSD', 'USDCAD', 'EURCAD'),
            ('GBPUSD', 'USDCAD', 'GBPCAD'),
            ('EURUSD', 'AUDUSD', 'EURAUD'),
            ('GBPUSD', 'AUDUSD', 'GBPAUD'),
            ('EURUSD', 'NZDUSD', 'EURNZD'),
            ('GBPUSD', 'NZDUSD', 'GBPNZD'),
            ('USDJPY', 'JPYCHF', 'USDCHF'),
            ('USDJPY', 'JPYCAD', 'USDCAD'),
            ('USDJPY', 'JPYAUD', 'AUDUSD'),
            ('USDJPY', 'JPYNZD', 'NZDUSD'),
            ('EURGBP', 'GBPJPY', 'EURJPY'),
            ('EURGBP', 'GBPCHF', 'EURCHF'),
            ('EURGBP', 'GBPCAD', 'EURCAD'),
            ('EURGBP', 'GBPAUD', 'EURAUD'),
            ('EURGBP', 'GBPNZD', 'EURNZD'),
            ('AUDCAD', 'CADCHF', 'AUDCHF'),
            ('AUDCAD', 'CADJPY', 'AUDJPY'),
            ('AUDCAD', 'CADNZD', 'AUDNZD'),
            ('AUDCHF', 'CHFJPY', 'AUDJPY'),
            ('AUDCHF', 'CHFCAD', 'AUDCAD'),
            ('AUDCHF', 'CHFNZD', 'AUDNZD')
        ]
        
        # Filter to only include triangles with available pairs
        available_pairs_set = set(self.available_pairs)
        
        for triangle in common_triangles:
            pair1, pair2, pair3 = triangle
            if pair1 in available_pairs_set and pair2 in available_pairs_set and pair3 in available_pairs_set:
                fallback_triangles.append(triangle)
        
        self.logger.info(f"Created {len(fallback_triangles)} fallback triangles from common patterns")
        return fallback_triangles
    
    def update_adaptive_parameters(self, params: Dict):
        """
        ⚡ CRITICAL: Update parameters based on market regime
        Called by AdaptiveEngine every 30 seconds
        """
        try:
            if 'market_regime' in params:
                self.current_regime = params['market_regime']
                regime_params = self.regime_parameters.get(self.current_regime, self.regime_parameters['normal'])
                
                # Update threshold based on regime
                self.arbitrage_threshold = regime_params['threshold']
                self.execution_timeout = regime_params['timeout']
                
                self.logger.info(f"🎯 Arbitrage parameters updated for {self.current_regime} market")
                self.logger.info(f"   Threshold: {self.arbitrage_threshold}")
                self.logger.info(f"   Timeout: {self.execution_timeout}ms")
            
            if 'position_size' in params:
                self.position_size = params['position_size']
                self.logger.info(f"📊 Position size updated: {self.position_size}")
                
        except Exception as e:
            self.logger.error(f"Error updating adaptive parameters: {e}")
    
    def _get_priority_triangles(self) -> List[Tuple]:
        """Get triangles prioritized by market regime - ใช้เฉพาะคู่เงินที่กำหนด"""
        
        # เพิ่ม debug logging
        self.logger.info(f"🔍 Getting priority triangles for regime: {self.current_regime}")
        self.logger.info(f"🔍 Total triangle combinations available: {len(self.triangle_combinations)}")
        
        # ใช้เฉพาะ triangle combinations ที่สร้างจากคู่เงินที่กำหนด
        priority_triangles = self.triangle_combinations
        
        # Filter triangles by available pairs
        available_pairs_set = set(self.available_pairs)
        filtered_triangles = []
        
        for triangle in priority_triangles:
            pair1, pair2, pair3 = triangle
            if (pair1 in available_pairs_set and 
                pair2 in available_pairs_set and 
                pair3 in available_pairs_set):
                filtered_triangles.append(triangle)
            else:
                self.logger.debug(f"🔍 Triangle filtered out (missing pairs): {triangle}")
        
        self.logger.info(f"🔍 Filtered triangles for {self.current_regime}: {len(filtered_triangles)}")
        if len(filtered_triangles) == 0:
            self.logger.warning(f"⚠️ No valid triangles for regime {self.current_regime}")
            self.logger.info(f"Available pairs: {self.available_pairs[:10]}...")  # Show first 10 pairs
        
        return filtered_triangles

    def _calculate_triangle_opportunity(self, triangle: Tuple[str, str, str]) -> Optional[Dict]:
        """
        ⚡ ENHANCED: Calculate arbitrage opportunity with strict validation
        """
        try:
            pair1, pair2, pair3 = triangle
            
            # Step 1: Get current prices (simplified for compatibility)
            price1 = self.broker.get_current_price(pair1)
            price2 = self.broker.get_current_price(pair2)
            price3 = self.broker.get_current_price(pair3)
            
            if not all([price1, price2, price3]):
                return None
            
            # Step 2: Calculate arbitrage potential
            cross_rate = (price1 * price2) / price3
            profit_potential = abs(cross_rate - 1) * 100
            
            # Step 3: Use higher threshold for better accuracy
            effective_threshold = self.arbitrage_threshold  # Use full threshold, not reduced
            
            # Debug logging
            if profit_potential > 0.001:
                self.logger.debug(f"🔍 Triangle {triangle}: profit={profit_potential:.4f}%, threshold={effective_threshold:.4f}%")
            
            if profit_potential > effective_threshold:
                # Step 4: Simple validation checks
                if not self._simple_validation_checks(triangle, cross_rate, profit_potential):
                    return None
                
                # Step 6: Determine trade direction
                if cross_rate > 1:
                    legs = [
                        {'symbol': pair1, 'type': 'BUY', 'volume': self.position_size},
                        {'symbol': pair2, 'type': 'BUY', 'volume': self.position_size},
                        {'symbol': pair3, 'type': 'SELL', 'volume': self.position_size}
                    ]
                else:
                    legs = [
                        {'symbol': pair1, 'type': 'SELL', 'volume': self.position_size},
                        {'symbol': pair2, 'type': 'SELL', 'volume': self.position_size},
                        {'symbol': pair3, 'type': 'BUY', 'volume': self.position_size}
                    ]
                
                return {
                    'id': f"{pair1}_{pair2}_{pair3}_{int(time.time())}",
                    'triangle': triangle,
                    'profit_potential': profit_potential,
                    'cross_rate': cross_rate,
                    'legs': legs,
                    'timestamp': datetime.now(),
                    'market_regime': self.current_regime
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error calculating triangle opportunity for {triangle}: {e}")
            return None
    
    def _get_validated_prices(self, triangle: Tuple[str, str, str]) -> Optional[Dict]:
        """Get prices with multiple validation checks"""
        try:
            pair1, pair2, pair3 = triangle
            prices = {}
            
            # Get prices multiple times for stability check
            for pair in [pair1, pair2, pair3]:
                price_checks = []
                for _ in range(self.price_stability_checks):
                    price = self.broker.get_current_price(pair)
                    if price:
                        price_checks.append(price)
                    time.sleep(0.1)  # Small delay between checks
                
                if not price_checks:
                    self.logger.debug(f"❌ No valid prices for {pair}")
                    return None
                
                # Check price stability
                if len(price_checks) > 1:
                    price_variance = max(price_checks) - min(price_checks)
                    if price_variance > 0.0001:  # Too much variance
                        self.logger.debug(f"❌ Price too volatile for {pair}: {price_variance}")
                        return None
                
                prices[pair] = sum(price_checks) / len(price_checks)
            
            # Calculate spread ratio
            spread_ratio = self._calculate_spread_ratio(triangle, prices)
            if spread_ratio > self.max_spread_ratio:
                self.logger.debug(f"❌ Spread too wide: {spread_ratio:.2f}")
                return None
            
            # Calculate volume score
            volume_score = self._calculate_volume_score(triangle)
            if volume_score < self.min_volume_threshold:
                self.logger.debug(f"❌ Volume too low: {volume_score:.2f}")
                return None
            
            prices['spread_ratio'] = spread_ratio
            prices['volume_score'] = volume_score
            
            return prices
            
        except Exception as e:
            self.logger.error(f"Error getting validated prices: {e}")
            return None
    
    def _validate_arbitrage_opportunity(self, triangle: Tuple[str, str, str], prices: Dict, 
                                      cross_rate: float, profit_potential: float) -> Dict:
        """Enhanced validation for arbitrage opportunities"""
        try:
            validation_result = {
                'is_valid': True,
                'reason': '',
                'checks_passed': 0,
                'total_checks': 5
            }
            
            # Check 1: Profit potential is significant
            if profit_potential < self.arbitrage_threshold:
                validation_result['is_valid'] = False
                validation_result['reason'] = f"Profit too low: {profit_potential:.4f}%"
                return validation_result
            validation_result['checks_passed'] += 1
            
            # Check 2: Cross rate is reasonable
            if cross_rate < 0.5 or cross_rate > 2.0:
                validation_result['is_valid'] = False
                validation_result['reason'] = f"Cross rate unreasonable: {cross_rate:.4f}"
                return validation_result
            validation_result['checks_passed'] += 1
            
            # Check 3: Spread ratio is acceptable
            if prices['spread_ratio'] > self.max_spread_ratio:
                validation_result['is_valid'] = False
                validation_result['reason'] = f"Spread too wide: {prices['spread_ratio']:.2f}"
                return validation_result
            validation_result['checks_passed'] += 1
            
            # Check 4: Volume is sufficient
            if prices['volume_score'] < self.min_volume_threshold:
                validation_result['is_valid'] = False
                validation_result['reason'] = f"Volume too low: {prices['volume_score']:.2f}"
                return validation_result
            validation_result['checks_passed'] += 1
            
            # Check 5: Market conditions are suitable
            if self.current_regime in ['volatile', 'trending'] and profit_potential < self.arbitrage_threshold * 1.5:
                validation_result['is_valid'] = False
                validation_result['reason'] = f"Market too volatile for low profit: {profit_potential:.4f}%"
                return validation_result
            validation_result['checks_passed'] += 1
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error validating arbitrage opportunity: {e}")
            return {'is_valid': False, 'reason': f'Validation error: {e}', 'checks_passed': 0, 'total_checks': 5}
    
    def _calculate_confidence_score(self, profit_potential: float, validation_result: Dict, prices: Dict) -> float:
        """Calculate confidence score for arbitrage opportunity"""
        try:
            confidence = 0.0
            
            # Base confidence from profit potential
            if profit_potential > self.arbitrage_threshold * 2:
                confidence += 0.4
            elif profit_potential > self.arbitrage_threshold * 1.5:
                confidence += 0.3
            else:
                confidence += 0.2
            
            # Validation checks bonus
            checks_ratio = validation_result['checks_passed'] / validation_result['total_checks']
            confidence += checks_ratio * 0.3
            
            # Spread ratio bonus
            if prices['spread_ratio'] < 0.1:
                confidence += 0.2
            elif prices['spread_ratio'] < 0.2:
                confidence += 0.1
            
            # Volume bonus
            if prices['volume_score'] > 0.8:
                confidence += 0.1
            
            return min(confidence, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence score: {e}")
            return 0.0
    
    def _calculate_spread_ratio(self, triangle: Tuple[str, str, str], prices: Dict) -> float:
        """Calculate average spread ratio for triangle"""
        try:
            total_spread = 0
            for pair in triangle:
                # Mock spread calculation - in real system, get bid/ask spread
                spread = 0.0001  # 1 pip spread
                total_spread += spread
            
            return total_spread / len(triangle)
            
        except Exception as e:
            self.logger.error(f"Error calculating spread ratio: {e}")
            return 1.0
    
    def _calculate_volume_score(self, triangle: Tuple[str, str, str]) -> float:
        """Calculate volume score for triangle"""
        try:
            # Mock volume calculation - in real system, get actual volume data
            return 0.8  # High volume score
            
        except Exception as e:
            self.logger.error(f"Error calculating volume score: {e}")
            return 0.5
    
    def _simple_validation_checks(self, triangle: Tuple[str, str, str], cross_rate: float, profit_potential: float) -> bool:
        """การตรวจสอบแบบง่ายเพื่อความเข้ากันได้"""
        try:
            # Check 1: Cross rate is reasonable
            if cross_rate < 0.5 or cross_rate > 2.0:
                self.logger.debug(f"❌ Cross rate unreasonable: {cross_rate:.4f}")
                return False
            
            # Check 2: Profit potential is significant enough
            if profit_potential < self.arbitrage_threshold:
                self.logger.debug(f"❌ Profit too low: {profit_potential:.4f}%")
                return False
            
            # Check 3: Market conditions are suitable
            if self.current_regime in ['volatile', 'trending'] and profit_potential < self.arbitrage_threshold * 1.5:
                self.logger.debug(f"❌ Market too volatile for low profit: {profit_potential:.4f}%")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in simple validation: {e}")
            return False
    
    def _check_rate_limits(self) -> bool:
        """ตรวจสอบ rate limits ก่อนส่งออเดอร์"""
        try:
            current_time = time.time()
            current_date = datetime.now().date()
            
            # รีเซ็ตตัวนับรายวัน
            if current_date != self.last_reset_date:
                self.daily_order_count = 0
                self.last_reset_date = current_date
                self.logger.info(f"📅 Daily order count reset for {current_date}")
            
            # ตรวจสอบจำนวนออเดอร์ต่อวัน
            if self.daily_order_count >= self.daily_order_limit:
                self.logger.warning(f"⚠️ Daily order limit reached: {self.daily_order_count}/{self.daily_order_limit}")
                return False
            
            # ตรวจสอบระยะห่างระหว่างออเดอร์
            if current_time - self.last_order_time < self.min_order_interval:
                remaining_time = self.min_order_interval - (current_time - self.last_order_time)
                self.logger.debug(f"⏳ Order rate limited: {remaining_time:.1f}s remaining")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking rate limits: {e}")
            return False
    
    def _update_order_tracking(self):
        """อัพเดทการติดตามออเดอร์"""
        try:
            self.last_order_time = time.time()
            self.daily_order_count += 1
            self.logger.debug(f"📊 Order tracking updated: {self.daily_order_count}/{self.daily_order_limit} today")
        except Exception as e:
            self.logger.error(f"Error updating order tracking: {e}")
    
    
    
    def _execute_triangle_arbitrage(self, opportunity: Dict) -> bool:
        """Execute triangle arbitrage with Never-Cut-Loss logic"""
        try:
            self.logger.info(f"🚀 Executing triangle arbitrage: {opportunity['id']}")
            
            orders = []
            failed_legs = []
            
            # Execute all 3 legs
            for i, leg in enumerate(opportunity['legs']):
                try:
                    order = self.broker.place_order(
                        symbol=leg['symbol'],
                        order_type=leg['type'],
                        volume=leg['volume'],
                        comment=f"ARBITRAGE_{opportunity['id']}_LEG{i+1}"
                    )
                    
                    if order:
                        orders.append(order)
                        self.logger.debug(f"✅ Leg {i+1} executed: {leg['symbol']}")
                    else:
                        failed_legs.append(leg)
                        self.logger.warning(f"⚠️ Leg {i+1} failed: {leg['symbol']} - Will use correlation recovery")
                        
                except Exception as e:
                    failed_legs.append(leg)
                    self.logger.error(f"❌ Leg {i+1} error: {e}")
            
            # Evaluate success
            if len(orders) > 0:
                opportunity['execution_status'] = 'complete' if len(failed_legs) == 0 else 'partial'
                opportunity['orders'] = orders
                opportunity['failed_legs'] = failed_legs
                opportunity['execution_time'] = datetime.now()
                
                if len(failed_legs) > 0:
                    self.logger.warning(f"⚠️ Partial execution - correlation manager will handle failed legs")
                
                return True
            else:
                self.logger.error(f"❌ Complete execution failure - all legs failed")
                self.logger.warning(f"⚠️ All arbitrage legs failed - correlation manager will handle recovery")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing triangle arbitrage: {e}")
            return False
    
    def calculate_adaptive_threshold(self) -> float:
        """
        คำนวณ threshold แบบ Adaptive ตาม market volatility และ regime
        
        Returns:
            float: Adaptive threshold สำหรับการตรวจจับ arbitrage
        """
        try:
            # Get current market volatility
            current_volatility = self.detect_market_volatility()
            
            # Base threshold from market regime
            base_threshold = self.adaptive_thresholds.get(self.market_regime, 0.001)
            
            # Adjust based on volatility
            if current_volatility > 0.002:  # High volatility
                volatility_multiplier = 1.5
            elif current_volatility < 0.0005:  # Low volatility
                volatility_multiplier = 0.7
            else:  # Normal volatility
                volatility_multiplier = 1.0
            
            # Calculate final threshold
            adaptive_threshold = base_threshold * volatility_multiplier
            
            # Update stored threshold
            self.volatility_threshold = adaptive_threshold
            
            self.logger.debug(f"Adaptive threshold calculated: {adaptive_threshold:.4f} "
                            f"(regime: {self.market_regime}, volatility: {current_volatility:.4f})")
            
            return adaptive_threshold
            
        except Exception as e:
            self.logger.error(f"Error calculating adaptive threshold: {e}")
            return 0.001  # Default fallback
    
    def detect_market_volatility(self) -> float:
        """
        ตรวจจับ market volatility ปัจจุบัน
        
        Returns:
            float: Current market volatility (0-1)
        """
        try:
            if not self.available_pairs:
                return 0.001
            
            # Sample a few major pairs for volatility calculation
            sample_pairs = self.available_pairs[:5] if len(self.available_pairs) >= 5 else self.available_pairs
            volatilities = []
            
            for pair in sample_pairs:
                try:
                    # Get recent price data (last 24 hours)
                    data = self.broker.get_historical_data(pair, 'M15', 96)  # 24 hours of M15 data
                    
                    if data is not None and len(data) >= 20:
                        # Calculate returns
                        returns = data['close'].pct_change().dropna()
                        
                        # Calculate volatility as standard deviation
                        volatility = returns.std()
                        volatilities.append(volatility)
                        
                except Exception as e:
                    self.logger.warning(f"Error calculating volatility for {pair}: {e}")
                    continue
            
            if volatilities:
                avg_volatility = np.mean(volatilities)
                self.logger.debug(f"Market volatility: {avg_volatility:.4f}")
                return avg_volatility
            else:
                return 0.001  # Default volatility
                
        except Exception as e:
            self.logger.error(f"Error detecting market volatility: {e}")
            return 0.001
    
    def detect_market_regime(self) -> str:
        """
        ตรวจจับ market regime ปัจจุบัน
        
        Returns:
            str: Market regime ('volatile', 'trending', 'ranging', 'normal')
        """
        try:
            if not self.available_pairs:
                return 'normal'
            
            # Analyze major pairs for regime detection
            sample_pairs = self.available_pairs[:3] if len(self.available_pairs) >= 3 else self.available_pairs
            regime_indicators = []
            
            for pair in sample_pairs:
                try:
                    # Get H1 data for trend analysis
                    data = self.broker.get_historical_data(pair, 'H1', 24)  # Last 24 hours
                    
                    if data is None or len(data) < 20:
                        continue
                    
                    # Calculate trend strength
                    trend_strength = self._calculate_trend_strength(data)
                    
                    # Calculate volatility
                    returns = data['close'].pct_change().dropna()
                    volatility = returns.std()
                    
                    # Determine regime for this pair
                    if volatility > 0.002:
                        regime_indicators.append('volatile')
                    elif trend_strength > 0.7:
                        regime_indicators.append('trending')
                    elif trend_strength < 0.3:
                        regime_indicators.append('ranging')
                    else:
                        regime_indicators.append('normal')
                        
                except Exception as e:
                    self.logger.warning(f"Error analyzing regime for {pair}: {e}")
                    continue
            
            if regime_indicators:
                # Determine overall regime (most common)
                regime_counts = {}
                for regime in regime_indicators:
                    regime_counts[regime] = regime_counts.get(regime, 0) + 1
                
                # Get most common regime
                new_regime = max(regime_counts, key=regime_counts.get)
                
                # Update if regime changed
                if new_regime != self.market_regime:
                    self.logger.info(f"Market regime changed: {self.market_regime} -> {new_regime}")
                    self.market_regime = new_regime
                    self.performance_metrics['market_regime_changes'] += 1
                
                return new_regime
            else:
                return 'normal'
                
        except Exception as e:
            self.logger.error(f"Error detecting market regime: {e}")
            return 'normal'
    
    def optimize_triangle_selection(self, triangles: List[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
        """
        ปรับปรุงการเลือก triangle ให้เหมาะสมกับสภาวะตลาด
        
        Args:
            triangles: รายการ triangles ที่มีอยู่
            
        Returns:
            List[Tuple[str, str, str]]: รายการ triangles ที่ถูกเลือกแล้ว
        """
        try:
            if not triangles:
                return []
            
            # Filter triangles based on current market conditions
            optimized_triangles = []
            
            for triangle in triangles:
                try:
                    # Check if triangle is suitable for current regime
                    if self._is_triangle_suitable_for_regime(triangle):
                        optimized_triangles.append(triangle)
                        
                except Exception as e:
                    self.logger.warning(f"Error checking triangle suitability: {e}")
                    continue
            
            # Limit number of triangles based on market regime
            max_triangles = {
                'volatile': 3,    # Fewer triangles in volatile markets
                'trending': 5,    # More triangles in trending markets
                'ranging': 7,     # Most triangles in ranging markets
                'normal': 5       # Default number
            }
            
            limit = max_triangles.get(self.market_regime, 5)
            
            if len(optimized_triangles) > limit:
                # Select best triangles based on historical performance
                optimized_triangles = optimized_triangles[:limit]
            
            self.logger.debug(f"Optimized triangle selection: {len(optimized_triangles)}/{len(triangles)} triangles")
            return optimized_triangles
            
        except Exception as e:
            self.logger.error(f"Error optimizing triangle selection: {e}")
            return triangles[:5]  # Return first 5 as fallback
    
    def validate_execution_speed(self, triangle: Tuple[str, str, str]) -> bool:
        """
        ตรวจสอบว่า execution speed อยู่ในเกณฑ์ที่กำหนด
        
        Args:
            triangle: Triangle ที่ต้องการตรวจสอบ
            
        Returns:
            bool: True ถ้า execution speed อยู่ในเกณฑ์
        """
        try:
            start_time = datetime.now()
            
            # Simulate execution by getting current prices
            pair1, pair2, pair3 = triangle
            
            price1 = self.broker.get_current_price(pair1)
            price2 = self.broker.get_current_price(pair2)
            price3 = self.broker.get_current_price(pair3)
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds() * 1000  # Convert to milliseconds
            
            # Update average execution time
            if self.performance_metrics['avg_execution_time'] == 0:
                self.performance_metrics['avg_execution_time'] = execution_time
            else:
                # Exponential moving average
                self.performance_metrics['avg_execution_time'] = (
                    self.performance_metrics['avg_execution_time'] * 0.9 + execution_time * 0.1
                )
            
            # Check if execution time is acceptable
            is_acceptable = execution_time <= self.execution_speed_ms
            
            if not is_acceptable:
                self.logger.warning(f"Execution speed too slow: {execution_time:.1f}ms > {self.execution_speed_ms}ms")
            
            return is_acceptable
            
        except Exception as e:
            self.logger.error(f"Error validating execution speed: {e}")
            return False
    
    def _calculate_trend_strength(self, data: pd.DataFrame) -> float:
        """Calculate trend strength from price data"""
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
    
    def _is_triangle_suitable_for_regime(self, triangle: Tuple[str, str, str]) -> bool:
        """Check if triangle is suitable for current market regime"""
        try:
            pair1, pair2, pair3 = triangle
            
            # In volatile markets, prefer major pairs only
            if self.market_regime == 'volatile':
                major_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'USDCAD', 'AUDUSD']
                return all(pair in major_pairs for pair in triangle)
            
            # In trending markets, prefer pairs with strong trends
            elif self.market_regime == 'trending':
                # Check if pairs have trending characteristics
                return True  # For now, accept all pairs
            
            # In ranging markets, prefer all pairs
            elif self.market_regime == 'ranging':
                return True
            
            # Normal regime - accept all pairs
            else:
                return True
                
        except Exception as e:
            self.logger.error(f"Error checking triangle suitability: {e}")
            return True
    
    def _calculate_technical_indicators(self, prices: List[float]) -> Dict:
        """Calculate multi-timeframe technical indicators"""
        try:
            if len(prices) < 50:
                return {}
            
            prices_array = np.array(prices, dtype=float)
            
            # Simple technical indicators without talib
            indicators = {
                # Moving Averages
                'sma_10': np.mean(prices_array[-10:]) if len(prices_array) >= 10 else np.mean(prices_array),
                'sma_20': np.mean(prices_array[-20:]) if len(prices_array) >= 20 else np.mean(prices_array),
                'sma_50': np.mean(prices_array[-50:]) if len(prices_array) >= 50 else np.mean(prices_array),
                
                # Simple RSI calculation
                'rsi': self._calculate_simple_rsi(prices_array),
                
                # Simple Bollinger Bands
                'bb_upper': np.mean(prices_array[-20:]) + 2 * np.std(prices_array[-20:]) if len(prices_array) >= 20 else np.mean(prices_array),
                'bb_middle': np.mean(prices_array[-20:]) if len(prices_array) >= 20 else np.mean(prices_array),
                'bb_lower': np.mean(prices_array[-20:]) - 2 * np.std(prices_array[-20:]) if len(prices_array) >= 20 else np.mean(prices_array),
                
                # Volume indicators (using price as proxy)
                'volume_sma': np.mean(prices_array[-20:]) if len(prices_array) >= 20 else np.mean(prices_array),
                
                # Price position in Bollinger Bands
                'bb_position': 0.5,  # Default neutral position
                
                # Trend strength
                'trend_strength': abs(np.mean(prices_array[-20:]) - np.mean(prices_array[-50:])) / np.mean(prices_array[-50:]) if len(prices_array) >= 50 and np.mean(prices_array[-50:]) > 0 else 0
            }
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error calculating technical indicators: {e}")
            return {}
    
    def _calculate_simple_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate simple RSI without talib"""
        try:
            if len(prices) < period + 1:
                return 50.0  # Default neutral RSI
            
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
            
        except Exception as e:
            self.logger.error(f"Error calculating RSI: {e}")
            return 50.0
    
    def _analyze_multi_timeframe_signals(self, triangle: Tuple[str, str, str]) -> Dict:
        """Analyze multi-timeframe signals for triangle"""
        try:
            pair1, pair2, pair3 = triangle
            signals = {}
            
            timeframes = ['M1', 'M5', 'M15', 'M30', 'H1']
            
            for pair in triangle:
                pair_signals = {}
                
                for tf in timeframes:
                    try:
                        # Get historical data
                        data = self.broker.get_historical_data(pair, tf, 100)
                        if data is None or len(data) < 50:
                            continue
                        
                        # Convert to prices
                        if hasattr(data, 'close'):
                            prices = data['close'].tolist()
                        else:
                            prices = [candle['close'] for candle in data]
                        
                        # Calculate indicators
                        indicators = self._calculate_technical_indicators(prices)
                        
                        if indicators:
                            pair_signals[tf] = {
                                'rsi': indicators.get('rsi', 50),
                                'macd_signal': indicators.get('macd_histogram', 0),
                                'bb_position': indicators.get('bb_position', 0.5),
                                'trend_strength': indicators.get('trend_strength', 0),
                                'adx': indicators.get('adx', 20),
                                'stoch_k': indicators.get('stoch_k', 50),
                                'stoch_d': indicators.get('stoch_d', 50)
                            }
                    
                    except Exception as e:
                        self.logger.error(f"Error analyzing {pair} {tf}: {e}")
                        continue
                
                signals[pair] = pair_signals
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error analyzing multi-timeframe signals: {e}")
            return {}
    
    def _get_signal_strength(self, signals: Dict) -> float:
        """Calculate overall signal strength from multi-timeframe analysis"""
        try:
            if not signals:
                return 0.0
            
            total_strength = 0
            count = 0
            
            for pair, pair_signals in signals.items():
                for tf, tf_signals in pair_signals.items():
                    # RSI signal (0-1)
                    rsi = tf_signals.get('rsi', 50)
                    if rsi < 30 or rsi > 70:  # Oversold/Overbought
                        total_strength += 0.8
                    elif 40 <= rsi <= 60:  # Neutral
                        total_strength += 0.5
                    else:
                        total_strength += 0.3
                    
                    # MACD signal (0-1)
                    macd = tf_signals.get('macd_signal', 0)
                    if macd > 0:  # Bullish
                        total_strength += 0.7
                    else:  # Bearish
                        total_strength += 0.4
                    
                    # Trend strength (0-1)
                    trend = tf_signals.get('trend_strength', 0)
                    total_strength += min(trend * 2, 1.0)  # Scale to 0-1
                    
                    # ADX signal (0-1)
                    adx = tf_signals.get('adx', 20)
                    if adx > 25:  # Strong trend
                        total_strength += 0.8
                    elif adx > 20:  # Moderate trend
                        total_strength += 0.6
                    else:  # Weak trend
                        total_strength += 0.4
                    
                    count += 1
            
            if count == 0:
                return 0.0
            
            return total_strength / count
            
        except Exception as e:
            self.logger.error(f"Error calculating signal strength: {e}")
            return 0.0
    
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
                
                # ตรวจสอบว่าส่งออเดอร์ arbitrage แล้วหรือไม่
                if self.arbitrage_sent:
                    self.logger.debug(f"⏸️ Detection loop #{loop_count} - ส่งออเดอร์ arbitrage แล้ว - ใช้ Correlation Recovery")
                    threading.Event().wait(30.0)  # รอนานขึ้นเมื่อใช้ Correlation Recovery
                    continue
                
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
        """Main detection method called by AdaptiveEngine - Single Entry Mode"""
        try:
            if not self.is_running:
                return
            
            # ตรวจสอบว่าส่งออเดอร์ arbitrage แล้วหรือไม่
            if self.arbitrage_sent:
                self.logger.debug("⏸️ ส่งออเดอร์ arbitrage แล้ว - ใช้ Correlation Recovery")
                return
            
            # เงื่อนไขเข้มงวด: ถ้ามีกลุ่มเปิดอยู่ ให้หยุดตรวจสอบ
            if len(self.active_groups) > 0:
                self.logger.debug("⏸️ มีกลุ่มเปิดอยู่ - หยุดตรวจสอบ arbitrage")
                return
            
            # ถ้าไม่มีกลุ่มที่เปิดอยู่ ให้ reset ข้อมูล
            if len(self.active_groups) == 0:
                self._reset_group_data()
            
            # ตรวจสอบเพิ่มเติม: ถ้ามีคู่เงินที่ถูกใช้แล้ว ให้หยุดตรวจสอบ
            if len(self.used_currency_pairs) > 0:
                self.logger.debug("⏸️ มีคู่เงินที่ถูกใช้แล้ว - หยุดตรวจสอบ arbitrage")
                self.logger.debug(f"   คู่เงินที่ถูกใช้: {self.used_currency_pairs}")
                # ตั้งค่าว่าส่งออเดอร์ arbitrage แล้ว
                self.arbitrage_sent = True
                self.arbitrage_send_time = datetime.now()
                return
            
            # ตรวจสอบเพิ่มเติม: ตรวจสอบว่ามีตำแหน่งที่เปิดอยู่จากกลุ่ม arbitrage หรือไม่
            try:
                all_positions = self.broker.get_all_positions()
                if all_positions:
                    arbitrage_positions = [pos for pos in all_positions if pos.get('comment', '').startswith('ARB_G')]
                    if arbitrage_positions:
                        self.logger.debug("⏸️ พบตำแหน่ง arbitrage ที่เปิดอยู่ - หยุดตรวจสอบ")
                        self.logger.debug(f"   ตำแหน่งที่พบ: {[pos['symbol'] for pos in arbitrage_positions]}")
                        # ตั้งค่าว่าส่งออเดอร์ arbitrage แล้ว
                        self.arbitrage_sent = True
                        self.arbitrage_send_time = datetime.now()
                        return
            except Exception as e:
                self.logger.warning(f"Error checking existing positions: {e}")
                
            self.logger.debug(f"🔍 Detecting arbitrage opportunities (threshold: {self.arbitrage_threshold})")
            
            # Get triangles for current market regime
            triangles_to_check = self._get_priority_triangles()
            
            if not triangles_to_check:
                self.logger.warning("⚠️ No triangles available for checking - investigating...")
                
                # Debug info
                self.logger.info(f"🔍 Debug Info:")
                self.logger.info(f"   Available pairs: {len(self.available_pairs)}")
                self.logger.info(f"   Triangle combinations: {len(self.triangle_combinations)}")
                self.logger.info(f"   Current regime: {self.current_regime}")
                
                # Try to use fallback triangles
                if len(self.available_pairs) >= 3:
                    # Create simple fallback triangle from first 3 pairs
                    fallback_triangle = tuple(self.available_pairs[:3])
                    triangles_to_check = [fallback_triangle]
                    self.logger.info(f"🔄 Using fallback triangle: {fallback_triangle}")
                else:
                    return
            
            opportunities_found = 0
            
            for triangle in triangles_to_check:
                try:
                    # Calculate arbitrage opportunity
                    opportunity = self._calculate_triangle_opportunity(triangle)
                    
                    if opportunity and opportunity['profit_potential'] > self.arbitrage_threshold:
                        self.total_opportunities_detected += 1
                        opportunities_found += 1
                        
                        self.logger.info(f"🎯 Arbitrage opportunity found: {triangle}")
                        self.logger.info(f"   Profit potential: {opportunity['profit_potential']:.4f}%")
                        
                        # สร้างกลุ่ม arbitrage และส่งออเดอร์ 3 คู่พร้อมกัน
                        success = self._create_arbitrage_group(triangle, opportunity)
                        if success:
                            # ตั้งค่าว่าส่งออเดอร์ arbitrage แล้ว
                            self.arbitrage_sent = True
                            self.arbitrage_send_time = datetime.now()
                            
                            # หยุดการตรวจสอบ arbitrage ใหม่ทันที
                            self.logger.info("⏸️ ส่งกลุ่มสำเร็จ - หยุดตรวจสอบ arbitrage")
                            self.logger.info("🔄 เริ่มใช้ระบบ Correlation Recovery")
                            break  # ออกจากลูปทันที
                        else:
                            self.logger.warning(f"⚠️ Triangle arbitrage failed: {opportunity['id']}")
                            
                except Exception as e:
                    self.logger.error(f"Error checking triangle {triangle}: {e}")
                    continue
            
            # Update performance metrics
            self.performance_metrics['total_opportunities'] += opportunities_found
            
            if opportunities_found > 0:
                self.logger.info(f"📊 Found {opportunities_found} arbitrage opportunities")
            else:
                self.logger.debug(f"📊 No arbitrage opportunities found in this cycle")
                    
        except Exception as e:
            self.logger.error(f"Error in detect_opportunities: {e}")
    
    def _create_arbitrage_group(self, triangle: Tuple[str, str, str], opportunity: Dict) -> bool:
        """สร้างกลุ่ม arbitrage และส่งออเดอร์ 3 คู่พร้อมกัน"""
        try:
            # ตรวจสอบว่าส่งออเดอร์ arbitrage แล้วหรือไม่
            if self.arbitrage_sent:
                self.logger.warning("🚫 ส่งออเดอร์ arbitrage แล้ว - หยุดสร้างกลุ่มใหม่")
                return False
            
            # เงื่อนไขเข้มงวด: ถ้ามีกลุ่มเปิดอยู่ ให้หยุด
            if len(self.active_groups) > 0:
                self.logger.warning("🚫 มีกลุ่มเปิดอยู่แล้ว - หยุดสร้างกลุ่มใหม่")
                self.logger.info(f"   กลุ่มที่เปิดอยู่: {list(self.active_groups.keys())}")
                return False
            
            # ตรวจสอบเพิ่มเติม: ถ้ามีคู่เงินที่ถูกใช้แล้ว ให้หยุด
            if len(self.used_currency_pairs) > 0:
                self.logger.warning("🚫 มีคู่เงินที่ถูกใช้แล้ว - หยุดสร้างกลุ่มใหม่")
                self.logger.info(f"   คู่เงินที่ใช้แล้ว: {self.used_currency_pairs}")
                return False
            
            # ตรวจสอบเพิ่มเติม: ตรวจสอบว่ามีตำแหน่งที่เปิดอยู่จากกลุ่ม arbitrage หรือไม่
            try:
                all_positions = self.broker.get_all_positions()
                if all_positions:
                    arbitrage_positions = [pos for pos in all_positions if pos.get('comment', '').startswith('ARB_G')]
                    if arbitrage_positions:
                        self.logger.warning("🚫 พบตำแหน่ง arbitrage ที่เปิดอยู่แล้ว - หยุดสร้างกลุ่มใหม่")
                        self.logger.info(f"   ตำแหน่งที่พบ: {[pos['symbol'] for pos in arbitrage_positions]}")
                        return False
            except Exception as e:
                self.logger.warning(f"Error checking existing positions: {e}")
            
            # ตรวจสอบว่าคู่เงินใดถูกใช้ไปแล้วในกลุ่มอื่น (double check)
            pair1, pair2, pair3 = triangle
            triangle_pairs = {pair1, pair2, pair3}
            used_pairs = triangle_pairs.intersection(self.used_currency_pairs)
            
            if used_pairs:
                self.logger.warning(f"🚫 คู่เงิน {used_pairs} ถูกใช้ในกลุ่มอื่นแล้ว - หยุดสร้างกลุ่ม")
                self.logger.info(f"   คู่เงินที่ใช้แล้ว: {self.used_currency_pairs}")
                return False
            
            self.group_counter += 1
            group_id = f"arbitrage_group_{self.group_counter}"
            
            pair1, pair2, pair3 = triangle
            
            self.logger.info(f"🎯 Creating arbitrage group {group_id}")
            self.logger.info(f"   Triangle: {pair1}, {pair2}, {pair3}")
            self.logger.info(f"   Opportunity: {opportunity.get('arbitrage_percent', 0):.4f}%")
            self.logger.info(f"   🚀 Sending orders simultaneously...")
            
            # สร้างข้อมูลกลุ่ม
            group_data = {
                'group_id': group_id,
                'triangle': triangle,
                'created_at': datetime.now(),
                'positions': [],
                'status': 'active',
                'total_pnl': 0.0,
                'recovery_chain': []
            }
            
            # ส่งออเดอร์ 3 คู่พร้อมกันด้วย threading
            orders_sent = 0
            order_results = []
            
            # สร้างข้อมูลออเดอร์ทั้ง 3 คู่
            orders_to_send = [
                {
                    'symbol': pair1,
                    'direction': opportunity.get('pair1_direction', 'BUY'),
                    'group_id': group_id,
                    'index': 0
                },
                {
                    'symbol': pair2,
                    'direction': opportunity.get('pair2_direction', 'SELL'),
                    'group_id': group_id,
                    'index': 1
                },
                {
                    'symbol': pair3,
                    'direction': opportunity.get('pair3_direction', 'BUY'),
                    'group_id': group_id,
                    'index': 2
                }
            ]
            
            # ส่งออเดอร์พร้อมกันด้วย threading
            threads = []
            results = [None] * 3  # เก็บผลลัพธ์ของแต่ละออเดอร์
            
            def send_single_order(order_data, result_index):
                """ส่งออเดอร์เดี่ยวใน thread แยก"""
                try:
                    result = self._send_arbitrage_order(
                        order_data['symbol'], 
                        order_data['direction'], 
                        order_data['group_id']
                    )
                    
                    if isinstance(result, dict):
                        results[result_index] = {
                            'success': result['success'],
                            'symbol': result['symbol'],
                            'direction': result['direction'],
                            'order_id': result.get('order_id'),
                            'index': result_index
                        }
                    else:
                        # Fallback for old return format
                        results[result_index] = {
                            'success': result,
                            'symbol': order_data['symbol'],
                            'direction': order_data['direction'],
                            'order_id': None,
                            'index': result_index
                        }
                except Exception as e:
                    self.logger.error(f"Error sending order for {order_data['symbol']}: {e}")
                    results[result_index] = {
                        'success': False,
                        'symbol': order_data['symbol'],
                        'direction': order_data['direction'],
                        'order_id': None,
                        'index': result_index,
                        'error': str(e)
                    }
            
            # เริ่มส่งออเดอร์พร้อมกัน
            start_time = datetime.now()
            for i, order_data in enumerate(orders_to_send):
                thread = threading.Thread(
                    target=send_single_order, 
                    args=(order_data, i),
                    daemon=True
                )
                threads.append(thread)
                thread.start()
            
            # รอให้ออเดอร์ทั้งหมดเสร็จสิ้น (timeout 5 วินาที)
            for thread in threads:
                thread.join(timeout=5.0)
            
            end_time = datetime.now()
            total_execution_time = (end_time - start_time).total_seconds() * 1000  # milliseconds
            self.logger.info(f"   ⏱️ Total execution time: {total_execution_time:.1f}ms")
            
            # ตรวจสอบผลลัพธ์และเพิ่มตำแหน่งที่สำเร็จ
            for result in results:
                if result and result['success']:
                    orders_sent += 1
                    group_data['positions'].append({
                        'symbol': result['symbol'],
                        'direction': result['direction'],
                        'lot_size': self.position_size,
                        'status': 'active',
                        'order_id': result.get('order_id'),  # เก็บ order_id สำหรับปิดออเดอร์
                        'comment': f"ARB_G{group_id.split('_')[-1]}_{result['symbol']}"  # เก็บ comment สำหรับค้นหา
                    })
                elif result:
                    self.logger.warning(f"❌ Order failed: {result['symbol']} {result['direction']}")
                    if 'error' in result:
                        self.logger.error(f"   Error: {result['error']}")
            
            # ตรวจสอบว่าส่งออเดอร์สำเร็จครบ 3 คู่
            if orders_sent == 3:
                self.active_groups[group_id] = group_data
                
                # เพิ่มคู่เงินลงในรายการที่ใช้แล้ว
                self.used_currency_pairs.update(triangle_pairs)
                self.group_currency_mapping[group_id] = triangle_pairs
                
                # อัพเดท order tracking
                self._update_order_tracking()
                
                self.logger.info(f"✅ Arbitrage group {group_id} created successfully")
                self.logger.info(f"   🚀 Orders sent simultaneously: {orders_sent}/3")
                self.logger.info(f"   📊 คู่เงินที่ใช้: {triangle_pairs}")
                self.logger.info(f"   ⏸️ หยุดตรวจสอบ arbitrage จนกว่ากลุ่มจะปิด")
                
                # แสดงรายละเอียดออเดอร์ที่ส่งสำเร็จ
                successful_orders = [r for r in results if r and r['success']]
                for order in successful_orders:
                    self.logger.info(f"   ✅ {order['symbol']} {order['direction']} - สำเร็จ")
                
                return True
            else:
                self.logger.error(f"❌ Failed to create arbitrage group {group_id}")
                self.logger.error(f"   Orders sent: {orders_sent}/3")
                
                # แสดงรายละเอียดออเดอร์ที่ล้มเหลว
                failed_orders = [r for r in results if r and not r['success']]
                for order in failed_orders:
                    self.logger.error(f"   ❌ {order['symbol']} {order['direction']} - ล้มเหลว")
                    if 'error' in order:
                        self.logger.error(f"      Error: {order['error']}")
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating arbitrage group: {e}")
            return False
    
    def _send_arbitrage_order(self, symbol: str, direction: str, group_id: str) -> bool:
        """ส่งออเดอร์ arbitrage"""
        try:
            # ตรวจสอบว่าส่งออเดอร์ arbitrage แล้วหรือไม่
            if self.arbitrage_sent:
                self.logger.warning(f"🚫 ส่งออเดอร์ arbitrage แล้ว - หยุดส่งออเดอร์ {symbol}")
                return {
                    'success': False,
                    'order_id': None,
                    'symbol': symbol,
                    'direction': direction,
                    'error': 'Arbitrage already sent'
                }
            
            # ตรวจสอบเพิ่มเติม: ตรวจสอบว่าคู่เงินนี้ถูกใช้แล้วหรือไม่
            if symbol in self.used_currency_pairs:
                self.logger.warning(f"🚫 คู่เงิน {symbol} ถูกใช้แล้ว - หยุดส่งออเดอร์")
                return {
                    'success': False,
                    'order_id': None,
                    'symbol': symbol,
                    'direction': direction,
                    'error': 'Currency pair already in use'
                }
            
            # สร้าง comment ที่แสดงกลุ่มและลำดับ
            group_number = group_id.split('_')[-1]  # เอาเฉพาะหมายเลขกลุ่ม
            comment = f"ARB_G{group_number}_{symbol}"
            
            # เริ่มส่งออเดอร์พร้อมกัน
            start_time = datetime.now()
            
            result = self.broker.place_order(
                symbol=symbol,
                order_type=direction,
                volume=self.position_size,
                comment=comment
            )
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds() * 1000  # milliseconds
            
            if result and result.get('retcode') == 10009:
                self.logger.debug(f"✅ Order sent: {symbol} {direction} {self.position_size} lot (took {execution_time:.1f}ms)")
                return {
                    'success': True,
                    'order_id': result.get('order_id'),
                    'symbol': symbol,
                    'direction': direction
                }
            else:
                self.logger.error(f"❌ Order failed: {symbol} {direction} (took {execution_time:.1f}ms)")
                return {
                    'success': False,
                    'order_id': None,
                    'symbol': symbol,
                    'direction': direction
                }
                
        except Exception as e:
            self.logger.error(f"Error sending arbitrage order: {e}")
            return False
    
    def check_group_status(self):
        """ตรวจสอบสถานะของกลุ่มที่เปิดอยู่"""
        try:
            if not self.active_groups:
                # ถ้าไม่มีกลุ่มที่เปิดอยู่ ให้ reset ข้อมูล
                self._reset_group_data()
                return
            
            groups_to_close = []
            
            for group_id, group_data in self.active_groups.items():
                # ตรวจสอบว่ากลุ่มหมดเวลา 24 ชั่วโมง
                if (datetime.now() - group_data['created_at']).total_seconds() > 86400:  # 24 hours
                    self.logger.warning(f"⏰ Group {group_id} expired after 24 hours")
                    groups_to_close.append(group_id)
                    continue
                
                # ตรวจสอบ PnL จริงของแต่ละตำแหน่ง
                total_group_pnl = 0.0
                all_positions_profitable = True
                
                for position in group_data['positions']:
                    # หา order_id จาก broker API
                    order_id = position.get('order_id')
                    if order_id:
                        # ตรวจสอบ PnL จาก broker API
                        all_positions = self.broker.get_all_positions()
                        position_pnl = 0.0
                        
                        for pos in all_positions:
                            if pos['ticket'] == order_id:
                                position_pnl = pos['profit']
                                break
                        
                        total_group_pnl += position_pnl
                        
                        # ตรวจสอบว่าตำแหน่งนี้กำไรหรือไม่
                        if position_pnl < 0:
                            all_positions_profitable = False
                        
                        self.logger.debug(f"   Position {position['symbol']}: PnL = {position_pnl:.2f} USD")
                    else:
                        self.logger.warning(f"   No order_id found for position {position['symbol']}")
                        all_positions_profitable = False
                
                # แสดงผล PnL รวมของกลุ่ม
                pnl_status = "💰" if total_group_pnl > 0 else "💸" if total_group_pnl < 0 else "⚖️"
                self.logger.info(f"📊 Group {group_id} PnL: {pnl_status} {total_group_pnl:.2f} USD")
                
                # คำนวณ % ของทุนจาก broker API
                account_balance = self.broker.get_account_balance()
                if account_balance is None:
                    account_balance = 1000.0  # fallback ถ้าไม่สามารถดึงได้
                    self.logger.warning("⚠️ Cannot get account balance, using fallback: 1000 USD")
                
                profit_percentage = (total_group_pnl / account_balance) * 100
                
                # ปิดกลุ่มเฉพาะเมื่อผลรวมเป็นบวก (ไม่ปิดขาดทุน)
                if total_group_pnl > 0:
                    self.logger.info(f"✅ Group {group_id} profitable - Total PnL: {total_group_pnl:.2f} USD ({profit_percentage:.2f}%)")
                    self.logger.info(f"✅ Closing group {group_id} - All positions will be closed together")
                    groups_to_close.append(group_id)
                elif total_group_pnl < 0 and self.correlation_manager:  # ถ้าขาดทุนและมี correlation manager
                    # เริ่ม correlation recovery (ไม่ปิดขาดทุน)
                    self.logger.info(f"🔄 Group {group_id} losing - Total PnL: {total_group_pnl:.2f} USD ({profit_percentage:.2f}%)")
                    self.logger.info(f"🔄 Starting correlation recovery - Never cut loss")
                    self._start_correlation_recovery(group_id, group_data, total_group_pnl)
            
            # ปิดกลุ่มที่ครบเงื่อนไข
            for group_id in groups_to_close:
                self._close_group(group_id)
                
        except Exception as e:
            self.logger.error(f"Error checking group status: {e}")
    
    def _start_correlation_recovery(self, group_id: str, group_data: Dict, total_pnl: float):
        """เริ่ม correlation recovery สำหรับกลุ่มที่ขาดทุน"""
        try:
            if not self.correlation_manager:
                self.logger.warning("Correlation manager not available")
                return
            
            # หาตำแหน่งที่ขาดทุน
            losing_pairs = []
            for position in group_data['positions']:
                order_id = position.get('order_id')
                if order_id:
                    # ตรวจสอบ PnL จาก broker API
                    all_positions = self.broker.get_all_positions()
                    position_pnl = 0.0
                    
                    for pos in all_positions:
                        if pos['ticket'] == order_id:
                            position_pnl = pos['profit']
                            break
                    
                    if position_pnl < 0:
                        losing_pairs.append({
                            'symbol': position['symbol'],
                            'direction': position['direction'],
                            'loss_percent': (position_pnl / 100) * 100,  # แปลงเป็นเปอร์เซ็นต์
                            'order_id': order_id,
                            'volume': position.get('lot_size', 0.1)
                        })
            
            if losing_pairs:
                self.logger.info(f"🔄 Starting correlation recovery for {len(losing_pairs)} losing pairs")
                self.correlation_manager.start_chain_recovery(group_id, losing_pairs)
            else:
                self.logger.info("No losing pairs found for correlation recovery")
                
        except Exception as e:
            self.logger.error(f"Error starting correlation recovery: {e}")
    
    def _close_group(self, group_id: str):
        """ปิดกลุ่ม arbitrage พร้อมกันทั้งกลุ่ม"""
        try:
            if group_id not in self.active_groups:
                return
            
            group_data = self.active_groups[group_id]
            
            self.logger.info(f"🔄 Closing arbitrage group {group_id}")
            self.logger.info(f"   🚀 Closing orders simultaneously...")
            
            # ปิดออเดอร์พร้อมกันทั้งกลุ่มด้วย threading
            positions_to_close = group_data['positions']
            orders_closed = 0
            close_results = []
            
            # สร้างข้อมูลการปิดออเดอร์
            close_orders = []
            for i, position in enumerate(positions_to_close):
                close_orders.append({
                    'symbol': position['symbol'],
                    'direction': position['direction'],
                    'group_id': group_id,
                    'order_id': position.get('order_id'),
                    'comment': position.get('comment'),
                    'index': i
                })
            
            # ปิดออเดอร์พร้อมกันด้วย threading
            threads = []
            results = [None] * len(close_orders)  # เก็บผลลัพธ์ของแต่ละออเดอร์
            
            def close_single_order(order_data, result_index):
                """ปิดออเดอร์เดี่ยวใน thread แยก"""
                try:
                    # ใช้ order_id ที่เก็บไว้ใน position data
                    order_id = order_data.get('order_id')
                    
                    if order_id:
                        result = self.broker.close_order(order_id)
                        
                        if isinstance(result, dict):
                            results[result_index] = {
                                'success': result['success'],
                                'symbol': order_data['symbol'],
                                'direction': order_data['direction'],
                                'order_id': order_id,
                                'pnl': result.get('pnl', 0),
                                'deal_id': result.get('deal_id'),
                                'index': result_index
                            }
                        else:
                            # Fallback for old return format
                            results[result_index] = {
                                'success': result,
                                'symbol': order_data['symbol'],
                                'direction': order_data['direction'],
                                'order_id': order_id,
                                'pnl': 0,
                                'deal_id': None,
                                'index': result_index
                            }
                    else:
                        # Fallback: หา order_id จาก broker API
                        all_positions = self.broker.get_all_positions()
                        found_order_id = None
                        
                        # หา order ที่ตรงกับ symbol และ comment
                        group_number = group_id.split('_')[-1]
                        expected_comment = f"ARB_G{group_number}_{order_data['symbol']}"
                        
                        for pos in all_positions:
                            if (pos['symbol'] == order_data['symbol'] and 
                                pos['comment'] == expected_comment):
                                found_order_id = pos['ticket']
                                break
                        
                        if found_order_id:
                            result = self.broker.close_order(found_order_id)
                            
                            if isinstance(result, dict):
                                results[result_index] = {
                                    'success': result['success'],
                                    'symbol': order_data['symbol'],
                                    'direction': order_data['direction'],
                                    'order_id': found_order_id,
                                    'pnl': result.get('pnl', 0),
                                    'deal_id': result.get('deal_id'),
                                    'index': result_index
                                }
                            else:
                                results[result_index] = {
                                    'success': result,
                                    'symbol': order_data['symbol'],
                                    'direction': order_data['direction'],
                                    'order_id': found_order_id,
                                    'pnl': 0,
                                    'deal_id': None,
                                    'index': result_index
                                }
                        else:
                            self.logger.warning(f"Order not found for {order_data['symbol']}")
                            results[result_index] = {
                                'success': False,
                                'symbol': order_data['symbol'],
                                'direction': order_data['direction'],
                                'order_id': None,
                                'pnl': 0,
                                'deal_id': None,
                                'index': result_index,
                                'error': 'Order not found'
                            }
                        
                except Exception as e:
                    self.logger.error(f"Error closing order for {order_data['symbol']}: {e}")
                    results[result_index] = {
                        'success': False,
                        'symbol': order_data['symbol'],
                        'direction': order_data['direction'],
                        'order_id': None,
                        'pnl': 0,
                        'deal_id': None,
                        'index': result_index,
                        'error': str(e)
                    }
            
            # เริ่มปิดออเดอร์พร้อมกัน
            start_time = datetime.now()
            for i, order_data in enumerate(close_orders):
                thread = threading.Thread(
                    target=close_single_order, 
                    args=(order_data, i),
                    daemon=True
                )
                threads.append(thread)
                thread.start()
            
            # รอให้ออเดอร์ทั้งหมดเสร็จสิ้น (timeout 5 วินาที)
            for thread in threads:
                thread.join(timeout=5.0)
            
            end_time = datetime.now()
            total_execution_time = (end_time - start_time).total_seconds() * 1000  # milliseconds
            self.logger.info(f"   ⏱️ Total closing time: {total_execution_time:.1f}ms")
            
            # ตรวจสอบผลลัพธ์และนับออเดอร์ที่ปิดสำเร็จ
            total_pnl = 0.0
            for result in results:
                if result and result['success']:
                    orders_closed += 1
                    pnl = result.get('pnl', 0)
                    total_pnl += pnl
                    pnl_status = "💰" if pnl > 0 else "💸" if pnl < 0 else "⚖️"
                    self.logger.info(f"   ✅ Closed: {result['symbol']} {result['direction']} (Order: {result['order_id']}) {pnl_status} PnL: {pnl:.2f} USD")
                elif result:
                    self.logger.warning(f"   ❌ Failed to close: {result['symbol']} {result['direction']}")
                    if 'error' in result:
                        self.logger.error(f"      Error: {result['error']}")
            
            # ลบคู่เงินออกจากรายการที่ใช้แล้ว
            if group_id in self.group_currency_mapping:
                group_pairs = self.group_currency_mapping[group_id]
                self.used_currency_pairs -= group_pairs
                del self.group_currency_mapping[group_id]
                self.logger.info(f"   📊 คู่เงินที่ปลดล็อค: {group_pairs}")
            
            # ปิด recovery positions ที่เกี่ยวข้องกับกลุ่มนี้
            if self.correlation_manager:
                self._close_recovery_positions_for_group(group_id)
            
            # ลบกลุ่มออกจาก active_groups
            del self.active_groups[group_id]
            
            # Reset arbitrage_sent เพื่อให้สามารถส่งออเดอร์ใหม่ได้
            self.arbitrage_sent = False
            self.arbitrage_send_time = None
            
            # Reset ข้อมูลกลุ่มให้ถูกต้อง
            self._reset_group_data()
            
            # แสดงผล PnL รวมของกลุ่ม
            pnl_status = "💰" if total_pnl > 0 else "💸" if total_pnl < 0 else "⚖️"
            self.logger.info(f"✅ Group {group_id} closed successfully")
            self.logger.info(f"   🚀 Orders closed simultaneously: {orders_closed}/{len(positions_to_close)}")
            self.logger.info(f"   {pnl_status} Total PnL: {total_pnl:.2f} USD")
            self.logger.info(f"   📊 คู่เงินที่ใช้ได้แล้ว: {self.used_currency_pairs}")
            self.logger.info("🔄 เริ่มตรวจสอบ arbitrage ใหม่")
            
        except Exception as e:
            self.logger.error(f"Error closing group {group_id}: {e}")
    
    def _close_recovery_positions_for_group(self, group_id: str):
        """ปิด recovery positions ที่เกี่ยวข้องกับกลุ่ม arbitrage"""
        try:
            if not self.correlation_manager:
                return
            
            # หา recovery positions ที่เกี่ยวข้องกับกลุ่มนี้
            group_data = self.active_groups.get(group_id, {})
            group_pairs = set(group_data.get('triangle', []))
            
            recovery_positions_to_close = []
            
            # ตรวจสอบ recovery positions ทั้งหมด
            for recovery_id, recovery_data in self.correlation_manager.recovery_positions.items():
                original_symbol = recovery_data.get('original_position', {}).get('symbol', '')
                
                # ถ้า recovery position นี้เกี่ยวข้องกับกลุ่ม arbitrage นี้
                if original_symbol in group_pairs:
                    recovery_positions_to_close.append(recovery_id)
            
            # ปิด recovery positions ที่เกี่ยวข้อง
            for recovery_id in recovery_positions_to_close:
                self.logger.info(f"🔄 Closing recovery position {recovery_id} for group {group_id}")
                self.correlation_manager._close_recovery_position(recovery_id)
            
            if recovery_positions_to_close:
                self.logger.info(f"✅ Closed {len(recovery_positions_to_close)} recovery positions for group {group_id}")
            
        except Exception as e:
            self.logger.error(f"Error closing recovery positions for group {group_id}: {e}")
    
    def _reset_group_data(self):
        """Reset ข้อมูลกลุ่มให้ถูกต้อง"""
        try:
            # ตรวจสอบว่ามีกลุ่มที่เปิดอยู่จริงหรือไม่
            if len(self.active_groups) == 0:
                # ถ้าไม่มีกลุ่มที่เปิดอยู่ ให้ reset ข้อมูลทั้งหมด
                self.used_currency_pairs.clear()
                self.group_currency_mapping.clear()
                self.logger.info("🔄 Reset ข้อมูลกลุ่ม - คู่เงินทั้งหมดปลดล็อคแล้ว")
            else:
                # ถ้ายังมีกลุ่มที่เปิดอยู่ ให้ตรวจสอบข้อมูลให้ถูกต้อง
                current_used_pairs = set()
                for group_id, group_data in self.active_groups.items():
                    triangle = group_data.get('triangle', [])
                    if triangle:
                        group_pairs = set(triangle)
                        current_used_pairs.update(group_pairs)
                        self.group_currency_mapping[group_id] = group_pairs
                
                # อัพเดท used_currency_pairs ให้ตรงกับข้อมูลจริง
                self.used_currency_pairs = current_used_pairs
                self.logger.info(f"🔄 อัพเดทข้อมูลกลุ่ม - คู่เงินที่ใช้: {self.used_currency_pairs}")
                
        except Exception as e:
            self.logger.error(f"Error resetting group data: {e}")
    
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
    
    def execute_triangle_entry_never_cut_loss(self, triangle: Tuple[str, str, str], ai_decision):
        """
        Execute triangle positions with Never-Cut-Loss approach
        ใช้ Correlation Recovery แทนการ cut loss
        """
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
            
            # Store active triangle with Never-Cut-Loss metadata
            self.active_triangles[triangle] = {
                'orders': orders,
                'entry_time': datetime.now(),
                'ai_decision': ai_decision,
                'status': 'active',
                'never_cut_loss': True,
                'recovery_strategy': 'correlation_hedge',
                'market_regime': self.market_regime,
                'adaptive_threshold': self.volatility_threshold,
                'execution_speed_ms': self.performance_metrics['avg_execution_time']
            }
            
            self.logger.info(f"✅ NEVER-CUT-LOSS triangle executed: {triangle} with {len(orders)} orders "
                           f"(regime: {self.market_regime})")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing Never-Cut-Loss triangle entry for {triangle}: {e}")
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
            'closed_triangles': closed_triangles,
            'market_regime': self.market_regime,
            'adaptive_threshold': self.volatility_threshold,
            'avg_execution_time_ms': self.performance_metrics['avg_execution_time'],
            'total_opportunities': self.performance_metrics['total_opportunities'],
            'successful_trades': self.performance_metrics['successful_trades'],
            'market_regime_changes': self.performance_metrics['market_regime_changes'],
            'used_currency_pairs': list(self.used_currency_pairs),
            'active_groups_count': len(self.active_groups),
            'group_currency_mapping': self.group_currency_mapping
        }
    
    def get_adaptive_parameters(self) -> Dict:
        """Get current adaptive parameters"""
        return {
            'market_regime': self.market_regime,
            'volatility_threshold': self.volatility_threshold,
            'adaptive_thresholds': self.adaptive_thresholds,
            'execution_speed_ms': self.execution_speed_ms,
            'performance_metrics': self.performance_metrics
        }
    
    def update_adaptive_parameters(self, new_params: Dict):
        """Update adaptive parameters dynamically"""
        try:
            if 'market_regime' in new_params:
                self.market_regime = new_params['market_regime']
            
            if 'volatility_threshold' in new_params:
                self.volatility_threshold = new_params['volatility_threshold']
            
            if 'execution_speed_ms' in new_params:
                self.execution_speed_ms = new_params['execution_speed_ms']
            
            if 'adaptive_thresholds' in new_params:
                self.adaptive_thresholds.update(new_params['adaptive_thresholds'])
            
            self.logger.info(f"Adaptive parameters updated: {new_params}")
            
        except Exception as e:
            self.logger.error(f"Error updating adaptive parameters: {e}")
    
    def get_never_cut_loss_positions(self) -> Dict:
        """Get all Never-Cut-Loss positions"""
        never_cut_loss_positions = {}
        
        for triangle, data in self.active_triangles.items():
            if data.get('never_cut_loss', False):
                never_cut_loss_positions[triangle] = data
        
        return never_cut_loss_positions
    
    def calculate_portfolio_health(self) -> Dict:
        """Calculate portfolio health for Never-Cut-Loss system"""
        try:
            total_positions = len(self.active_triangles)
            never_cut_loss_positions = len(self.get_never_cut_loss_positions())
            
            # Calculate average holding time
            current_time = datetime.now()
            holding_times = []
            
            for triangle, data in self.active_triangles.items():
                if data['status'] == 'active':
                    holding_time = (current_time - data['entry_time']).total_seconds() / 3600  # hours
                    holding_times.append(holding_time)
            
            avg_holding_time = np.mean(holding_times) if holding_times else 0
            
            # Calculate success rate
            success_rate = 0
            if self.performance_metrics['total_opportunities'] > 0:
                success_rate = self.performance_metrics['successful_trades'] / self.performance_metrics['total_opportunities']
            
            return {
                'total_positions': total_positions,
                'never_cut_loss_positions': never_cut_loss_positions,
                'avg_holding_time_hours': avg_holding_time,
                'success_rate': success_rate,
                'market_regime': self.market_regime,
                'adaptive_threshold': self.volatility_threshold,
                'execution_speed_ms': self.performance_metrics['avg_execution_time'],
                'duplicate_prevention': {
                    'used_currency_pairs': list(self.used_currency_pairs),
                    'active_groups_count': len(self.active_groups),
                    'group_currency_mapping': self.group_currency_mapping
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio health: {e}")
            return {}
    
    def get_duplicate_prevention_status(self) -> Dict:
        """Get status of duplicate prevention system"""
        try:
            return {
                'is_prevention_active': True,
                'used_currency_pairs': list(self.used_currency_pairs),
                'active_groups_count': len(self.active_groups),
                'group_currency_mapping': self.group_currency_mapping,
                'prevention_rules': {
                    'rule_1': 'ไม่ให้กลุ่มใหม่ใช้คู่เงินที่กลุ่มเก่าใช้อยู่',
                    'rule_2': 'ตรวจสอบก่อนสร้างกลุ่มใหม่ทุกครั้ง',
                    'rule_3': 'ปลดล็อคคู่เงินเมื่อกลุ่มปิด'
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting duplicate prevention status: {e}")
            return {}
    
    def check_currency_pair_availability(self, symbol: str) -> bool:
        """ตรวจสอบว่าคู่เงินสามารถใช้ได้หรือไม่"""
        try:
            return symbol not in self.used_currency_pairs
        except Exception as e:
            self.logger.error(f"Error checking currency pair availability: {e}")
            return False
