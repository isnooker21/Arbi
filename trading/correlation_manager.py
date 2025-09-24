"""
ระบบจัดการ Correlation และการกู้คืนตำแหน่งแบบ Active Recovery Engine
================================================================

ไฟล์นี้ทำหน้าที่:
- ระบบ Never-Cut-Loss โดยใช้ Correlation Recovery
- การจัดการ Recovery แบบ Real-time
- Chain Recovery สำหรับคู่เงินที่ติดลบ

ตัวอย่างการทำงาน:
1. ตรวจพบตำแหน่ง EUR/USD ขาดทุน
2. หาคู่เงินที่มีความสัมพันธ์สูง เช่น GBP/USD
3. คำนวณ hedge ratio ที่เหมาะสม
4. เปิดตำแหน่ง GBP/USD ในทิศทางที่เหมาะสม
5. ติดตามผลการกู้คืนแบบ Real-time
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
import threading
from utils.calculations import TradingCalculations

class CorrelationManager:
    def __init__(self, broker_api, ai_engine=None):
        self.broker = broker_api
        # self.ai = ai_engine  # DISABLED for simple trading system
        self.correlation_matrix = {}
        self.recovery_positions = {}
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        
        # Active Recovery Engine parameters
        self.recovery_mode = 'active'  # active, passive, disabled
        self.hedge_ratio_optimization = True
        self.portfolio_rebalancing = True
        self.multi_timeframe_analysis = True
        
        # Recovery thresholds - More flexible for all market conditions
        self.recovery_thresholds = {
            'min_correlation': 0.5,      # ความสัมพันธ์ขั้นต่ำ 50% (ลดลงเพื่อให้ใช้ได้ทุกคู่)
            'max_correlation': 0.95,     # ความสัมพันธ์สูงสุด 95%
            'min_loss_threshold': -0.005, # ขาดทุนขั้นต่ำ -0.5%
            'max_recovery_time_hours': 24, # เวลาสูงสุด 24 ชั่วโมง
            'hedge_ratio_range': (0.3, 2.5),  # ขนาด hedge ratio
            'wait_time_minutes': 5,      # รอ 5 นาทีก่อนเริ่มแก้ไม้
            'base_lot_size': 0.1         # ขนาด lot เริ่มต้น
        }
        
        # Portfolio balance threshold
        self.portfolio_balance_threshold = 0.1  # 10% imbalance threshold
        
        # Never-Cut-Loss flag
        self.never_cut_loss = True
        
        # Performance tracking
        self.recovery_metrics = {
            'total_recoveries': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'avg_recovery_time_hours': 0,
            'total_recovered_amount': 0.0
        }
        
        # Multi-timeframe correlation cache
        self.recovery_chains = {}  # เก็บข้อมูล recovery chain ของแต่ละกลุ่ม
        
        # ระบบติดตามไม้ที่แก้แล้ว (ป้องกันการแก้ไม้ซ้ำ)
        self.hedged_pairs = set()  # เก็บคู่ที่แก้แล้ว (symbol)
        self.hedged_positions = {}  # เก็บข้อมูลไม้ที่แก้แล้ว (order_id -> position_info)
        self.hedged_groups = {}  # เก็บข้อมูลกลุ่มที่แก้แล้ว (group_id -> hedged_info)
        
        # ระบบ Save/Load ข้อมูล
        self.persistence_file = "data/recovery_positions.json"
        
        # Load existing recovery data on startup
        self._load_recovery_data()
        
    def start_chain_recovery(self, group_id: str, losing_pairs: List[Dict]):
        """เริ่ม chain recovery สำหรับกลุ่มที่ขาดทุน"""
        try:
            self.logger.info("=" * 80)
            self.logger.info(f"🔗 STARTING CHAIN RECOVERY FOR GROUP {group_id}")
            self.logger.info("=" * 80)
            
            # แสดงสถานะไม้ทั้งหมดในกลุ่ม
            self._log_group_hedging_status(group_id, losing_pairs)
            
            # สร้าง recovery chain
            recovery_chain = {
                'group_id': group_id,
                'started_at': datetime.now(),
                'original_pairs': losing_pairs,
                'recovery_pairs': [],
                'status': 'active',
                'current_chain': []
            }
            
            self.recovery_chains[group_id] = recovery_chain
            self._update_recovery_data()
            
            # เริ่ม recovery สำหรับแต่ละคู่ที่ขาดทุน
            for pair in losing_pairs:
                self._start_pair_recovery(group_id, pair)
                
        except Exception as e:
            self.logger.error(f"Error starting chain recovery: {e}")
    
    def _log_group_hedging_status(self, group_id: str, losing_pairs: List[Dict]):
        """แสดงสถานะการแก้ไม้ของกลุ่มให้ชัดเจน"""
        try:
            self.logger.info("📊 GROUP HEDGING STATUS:")
            self.logger.info("-" * 50)
            
            # แสดงไม้ arbitrage ที่ขาดทุน
            self.logger.info("🔴 LOSING ARBITRAGE POSITIONS:")
            for i, pair in enumerate(losing_pairs, 1):
                symbol = pair['symbol']
                order_id = pair.get('order_id', 'N/A')
                is_hedged = self._is_position_hedged(pair)
                status = "✅ HEDGED" if is_hedged else "❌ NOT HEDGED"
                
                self.logger.info(f"   {i}. {symbol} (Order: {order_id}) - {status}")
                
                if not is_hedged:
                    # แสดงเงื่อนไขการแก้ไม้
                    risk_per_lot = self._calculate_risk_per_lot(pair)
                    price_distance = self._calculate_price_distance(pair)
                    
                    risk_status = "✅" if risk_per_lot >= 0.05 else "❌"
                    distance_status = "✅" if price_distance >= 10 else "❌"
                    
                    self.logger.info(f"      Risk: {risk_per_lot:.2%} (≥5%) {risk_status}")
                    self.logger.info(f"      Distance: {price_distance:.1f} pips (≥10) {distance_status}")
            
            # แสดงไม้ correlation ที่เกี่ยวข้องกับกลุ่มนี้
            self.logger.info("🔄 EXISTING CORRELATION POSITIONS:")
            correlation_count = 0
            for recovery_id, position in self.recovery_positions.items():
                if position.get('group_id') == group_id and position.get('status') == 'active':
                    correlation_count += 1
                    symbol = position['symbol']
                    order_id = position.get('order_id', 'N/A')
                    is_hedged = self._is_position_hedged(position)
                    status = "✅ HEDGED" if is_hedged else "❌ NOT HEDGED"
                    
                    self.logger.info(f"   {correlation_count}. {symbol} (Order: {order_id}) - {status}")
                    
                    if not is_hedged:
                        # แสดงเงื่อนไขการแก้ไม้
                        risk_per_lot = self._calculate_risk_per_lot(position)
                        price_distance = self._calculate_price_distance(position)
                        
                        risk_status = "✅" if risk_per_lot >= 0.05 else "❌"
                        distance_status = "✅" if price_distance >= 10 else "❌"
                        
                        self.logger.info(f"      Risk: {risk_per_lot:.2%} (≥5%) {risk_status}")
                        self.logger.info(f"      Distance: {price_distance:.1f} pips (≥10) {distance_status}")
            
            if correlation_count == 0:
                self.logger.info("   No existing correlation positions")
            
            # สรุปสถานะ
            total_positions = len(losing_pairs) + correlation_count
            hedged_count = sum(1 for pair in losing_pairs if self._is_position_hedged(pair))
            hedged_count += sum(1 for position in self.recovery_positions.values() 
                              if position.get('group_id') == group_id and 
                              position.get('status') == 'active' and 
                              self._is_position_hedged(position))
            
            self.logger.info("-" * 50)
            self.logger.info(f"📈 SUMMARY: {hedged_count}/{total_positions} positions hedged")
            self.logger.info("=" * 80)
            
        except Exception as e:
            self.logger.error(f"Error logging group hedging status: {e}")
    
    def _is_position_hedged(self, position: Dict) -> bool:
        """ตรวจสอบว่าตำแหน่งนี้แก้ไม้แล้วหรือยัง"""
        try:
            order_id = position.get('order_id')
            symbol = position.get('symbol')
            
            # ตรวจสอบจาก order_id
            if order_id and order_id in self.hedged_positions:
                return True
            
            # ตรวจสอบจาก symbol
            if symbol and symbol in self.hedged_pairs:
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking if position is hedged: {e}")
            return False
    
    def _calculate_risk_per_lot(self, position: Dict) -> float:
        """คำนวณ risk ต่อ lot เป็นเปอร์เซ็นต์ของ account balance"""
        try:
            order_id = position.get('order_id')
            symbol = position.get('symbol')
            
            if not order_id:
                return 0.0
            
            # ดึงข้อมูล PnL จาก broker
            all_positions = self.broker.get_all_positions()
            position_pnl = 0.0
            lot_size = 0.0
            
            for pos in all_positions:
                if pos['ticket'] == order_id:
                    position_pnl = pos['profit']
                    lot_size = pos['volume']
                    break
            
            if lot_size <= 0:
                self.logger.warning(f"Invalid lot size for {symbol} (Order: {order_id})")
                return 0.0
            
            # ดึง account balance เพื่อคำนวณเปอร์เซ็นต์
            account_balance = self.broker.get_account_balance()
            if not account_balance or account_balance <= 0:
                account_balance = 1000.0  # fallback
            
            # คำนวณ risk เป็นเปอร์เซ็นต์ของ account balance
            risk_per_lot = abs(position_pnl) / account_balance
            self.logger.debug(f"Risk calculation for {symbol}: PnL={position_pnl:.2f}, Lot={lot_size:.2f}, Balance={account_balance:.2f}, Risk={risk_per_lot:.2%}")
            
            return risk_per_lot
            
        except Exception as e:
            self.logger.error(f"Error calculating risk per lot: {e}")
            return 0.0
    
    def _calculate_price_distance(self, position: Dict) -> float:
        """คำนวณระยะห่างราคาเป็น pips"""
        try:
            symbol = position.get('symbol')
            order_id = position.get('order_id')
            
            if not symbol or not order_id:
                return 0.0
            
            # ดึง entry_price จาก broker API แทนที่จะใช้จาก position data
            entry_price = 0.0
            all_positions = self.broker.get_all_positions()
            for pos in all_positions:
                if pos['ticket'] == order_id:
                    # ใช้ 'price' แทน 'price_open' ตาม broker API structure
                    entry_price = pos.get('price', 0.0)
                    break
            
            if entry_price <= 0:
                self.logger.warning(f"Could not get entry price for {symbol} (Order: {order_id})")
                return 0.0
            
            # ดึงราคาปัจจุบัน
            current_price = self.broker.get_current_price(symbol)
            if not current_price or current_price <= 0:
                self.logger.warning(f"Could not get current price for {symbol}")
                return 0.0
            
            # คำนวณ price distance ตามประเภทคู่เงิน
            if 'JPY' in symbol:
                price_distance = abs(current_price - entry_price) * 100
            else:
                price_distance = abs(current_price - entry_price) * 10000
            
            self.logger.debug(f"Price distance calculation for {symbol}: Entry={entry_price:.5f}, Current={current_price:.5f}, Distance={price_distance:.1f} pips")
            
            return price_distance
            
        except Exception as e:
            self.logger.error(f"Error calculating price distance: {e}")
            return 0.0
    
    def _start_pair_recovery(self, group_id: str, losing_pair: Dict):
        """เริ่ม recovery สำหรับคู่ที่ขาดทุน"""
        try:
            symbol = losing_pair['symbol']
            order_id = losing_pair.get('order_id')
            
            # ตรวจสอบว่าไม้นี้แก้แล้วหรือยัง
            if self._is_position_hedged(losing_pair):
                self.logger.info(f"⏭️ {symbol} (Order: {order_id}): Already hedged - skipping")
                return
            
            # ตรวจสอบเงื่อนไขการแก้ไม้
            risk_per_lot = self._calculate_risk_per_lot(losing_pair)
            price_distance = self._calculate_price_distance(losing_pair)
            
            self.logger.info(f"🔍 Checking hedging conditions for {symbol} (Order: {order_id}):")
            self.logger.info(f"   Risk: {risk_per_lot:.2%} (need ≥5%) {'✅' if risk_per_lot >= 0.05 else '❌'}")
            self.logger.info(f"   Distance: {price_distance:.1f} pips (need ≥10) {'✅' if price_distance >= 10 else '❌'}")
            
            # แสดงข้อมูลการคำนวณให้ชัดเจน
            if price_distance == 0.0:
                self.logger.warning(f"   ⚠️ Price distance is 0.0 - checking calculation...")
                # ดึงข้อมูลจาก broker อีกครั้งเพื่อ debug
                all_positions = self.broker.get_all_positions()
                for pos in all_positions:
                    if pos['ticket'] == order_id:
                        entry_price = pos.get('price', 0.0)  # ใช้ 'price' แทน 'price_open'
                        current_price = self.broker.get_current_price(symbol)
                        if current_price and entry_price:
                            if 'JPY' in symbol:
                                calc_distance = abs(current_price - entry_price) * 100
                            else:
                                calc_distance = abs(current_price - entry_price) * 10000
                            self.logger.info(f"   🔍 Debug: Entry={entry_price:.5f}, Current={current_price:.5f}, Calc={calc_distance:.1f} pips")
                        break
            
            if risk_per_lot < 0.05 or price_distance < 10:
                self.logger.info(f"⏳ {symbol}: Conditions not met - waiting")
                return
            
            self.logger.info(f"✅ {symbol}: All conditions met - starting recovery")
            
            # หาคู่เงินที่เหมาะสมสำหรับ recovery
            correlation_candidates = self._find_optimal_correlation_pairs(symbol)
            
            if not correlation_candidates:
                self.logger.warning(f"   No correlation candidates found for {symbol}")
                return
            
            # เลือกคู่เงินที่ดีที่สุด
            best_correlation = correlation_candidates[0]
            self.logger.info(f"   Best correlation: {best_correlation['symbol']} (correlation: {best_correlation['correlation']:.2f})")
            
            # ส่งออเดอร์ recovery
            success = self._execute_correlation_position(losing_pair, best_correlation, group_id)
            
            if success:
                # บันทึกว่าไม้นี้แก้แล้ว
                self._mark_position_as_hedged(losing_pair)
                self.logger.info(f"✅ Recovery position opened for {symbol}")
            else:
                self.logger.error(f"❌ Failed to open recovery position for {symbol}")
                
        except Exception as e:
            self.logger.error(f"Error starting pair recovery: {e}")
    
    def _mark_position_as_hedged(self, position: Dict):
        """บันทึกว่าตำแหน่งนี้แก้ไม้แล้ว"""
        try:
            order_id = position.get('order_id')
            symbol = position.get('symbol')
            
            if order_id:
                self.hedged_positions[order_id] = {
                    'symbol': symbol,
                    'hedged_at': datetime.now(),
                    'position_info': position
                }
            
            if symbol:
                self.hedged_pairs.add(symbol)
            
            self.logger.debug(f"📝 Marked position as hedged: {symbol} (Order: {order_id})")
            
        except Exception as e:
            self.logger.error(f"Error marking position as hedged: {e}")
    
    def _calculate_hedge_lot_size(self, original_lot: float, correlation: float, loss_percent: float, original_symbol: str = None) -> float:
        """คำนวณขนาด lot สำหรับ hedge position - ใช้ uniform pip value"""
        try:
            # ดึง balance จาก broker
            balance = self.broker.get_account_balance()
            if not balance:
                self.logger.warning("Cannot get account balance - using original lot size")
                return original_lot
            
            # คำนวณ pip value ของ original position
            if original_symbol:
                original_pip_value = TradingCalculations.calculate_pip_value(original_symbol, original_lot, self.broker)
                
                # คำนวณ target pip value ตาม balance (base $10K = $10 pip value)
                base_balance = 10000.0
                balance_multiplier = balance / base_balance
                target_pip_value = 10.0 * balance_multiplier
                
                # คำนวณ lot size ที่ให้ pip value เท่ากับ target
                # ใช้ correlation เพื่อปรับขนาด hedge
                hedge_pip_value = target_pip_value * correlation
                
                # หา lot size ที่ให้ pip value ตาม target
                # ใช้คู่เงินเดิมเป็น base (สมมติว่า hedge ใช้คู่เงินเดียวกัน)
                pip_value_per_001 = TradingCalculations.calculate_pip_value(original_symbol, 0.01, self.broker)
                hedge_lot = (hedge_pip_value * 0.01) / pip_value_per_001
                
                # Round to valid lot size
                hedge_lot = TradingCalculations.round_to_valid_lot_size(hedge_lot)
                
                # จำกัดขนาด lot
                hedge_lot = min(hedge_lot, 1.0)  # สูงสุด 1 lot
                hedge_lot = max(hedge_lot, 0.1)  # ต่ำสุด 0.1 lot
                
                self.logger.info(f"📊 Hedge lot calculation: Original={original_lot:.4f}, Target Pip=${target_pip_value:.2f}, Hedge Lot={hedge_lot:.4f}")
                
                return float(hedge_lot)
            else:
                # Fallback: ใช้ lot size เดียวกันกับไม้เดิม
                return original_lot
            
        except Exception as e:
            self.logger.error(f"Error calculating hedge lot size: {e}")
            return original_lot
    
    def _send_hedge_order(self, symbol: str, lot_size: float, group_id: str, recovery_level: int = 1) -> bool:
        """ส่งออเดอร์ hedge"""
        try:
            # สร้าง comment
            group_number = group_id.split('_')[-1]
            comment = f"RECOVERY_G{group_number}_{symbol}_L{recovery_level}"
            
            # ส่งออเดอร์
            result = self.broker.place_order(
                symbol=symbol,
                order_type='BUY',  # Default to BUY
                volume=lot_size,
                comment=comment
            )
            
            if result and result.get('retcode') == 10009:
                self.logger.info(f"✅ Recovery order sent: {symbol} {lot_size} lot")
                return True
            else:
                self.logger.error(f"❌ Failed to send recovery order: {symbol}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending hedge order: {e}")
            return False
    
    def check_recovery_chain(self):
        """ตรวจสอบ recovery chain และดำเนินการต่อเนื่อง - เฉพาะกลุ่มที่ยังเปิดอยู่"""
        try:
            # ตรวจสอบว่ามี recovery chains หรือไม่
            if not self.recovery_chains:
                return
            
            active_chains = 0
            chains_to_remove = []
            
            for group_id, chain_data in self.recovery_chains.items():
                if chain_data['status'] != 'active':
                    continue
                
                # ตรวจสอบว่ากลุ่มยังเปิดอยู่จริงหรือไม่
                # ถ้าไม่มี group_id ใน active_groups แสดงว่ากลุ่มปิดแล้ว
                active_chains += 1
                
                # ตรวจสอบ recovery pairs
                for recovery_pair in chain_data['recovery_pairs']:
                    if self._should_continue_recovery(recovery_pair):
                        self.logger.info(f"🔄 Continuing recovery chain for {recovery_pair['symbol']}")
                        self._continue_recovery_chain(group_id, recovery_pair)
                    # ไม่แสดง log ถ้าไม่พร้อม recovery เพื่อลด log spam
            
            # แสดง log เฉพาะเมื่อมี recovery chains และมีการเปลี่ยนแปลง
            if active_chains > 0:
                self.logger.debug(f"📊 Active recovery chains: {active_chains}")
                        
        except Exception as e:
            self.logger.error(f"Error checking recovery chain: {e}")
    
    def _should_continue_recovery(self, recovery_pair: Dict) -> bool:
        """ตรวจสอบว่าควรดำเนินการ recovery ต่อหรือไม่ - ใช้เงื่อนไขเดียวกับ arbitrage"""
        try:
            symbol = recovery_pair['symbol']
            order_id = recovery_pair.get('order_id')
            
            # ตรวจสอบว่าไม้นี้แก้แล้วหรือยัง
            if self._is_position_hedged(recovery_pair):
                self.logger.debug(f"⏭️ {symbol} (Order: {order_id}): Already hedged - skipping")
                return False
            
            if not order_id:
                self.logger.debug(f"🔍 {symbol}: No order_id found")
                return False
            
            # ตรวจสอบ PnL จาก broker API
            all_positions = self.broker.get_all_positions()
            position_pnl = 0.0
            lot_size = 0.0
            
            for pos in all_positions:
                if pos['ticket'] == order_id:
                    position_pnl = pos['profit']
                    lot_size = pos['volume']
                    break
            
            if lot_size <= 0:
                self.logger.debug(f"🔍 {symbol}: Invalid lot size ({lot_size})")
                return False
            
            # เงื่อนไข 1: Risk 5% ต่อ lot
            risk_per_lot = abs(position_pnl) / lot_size
            
            if risk_per_lot < 0.05:  # risk น้อยกว่า 5%
                self.logger.debug(f"⏳ {symbol} risk too low ({risk_per_lot:.2%}) - Waiting for 5%")
                return False
            
            # เงื่อนไข 2: ระยะห่าง 10 pips
            entry_price = recovery_pair.get('entry_price', 0)
            if entry_price > 0:
                try:
                    current_price = self.broker.get_current_price(symbol)
                    if current_price > 0:
                        # คำนวณ price distance ตามประเภทคู่เงิน
                        if 'JPY' in symbol:
                            price_distance = abs(current_price - entry_price) * 100
                        else:
                            price_distance = abs(current_price - entry_price) * 10000
                        
                        self.logger.debug(f"🔍 {symbol}: Entry {entry_price:.5f}, Current {current_price:.5f}, Distance {price_distance:.1f} pips")
                        
                        if price_distance < 10:  # ระยะห่างน้อยกว่า 10 จุด
                            self.logger.debug(f"⏳ {symbol} price distance too small ({price_distance:.1f} pips) - Waiting for 10 pips")
                            return False
                except Exception as e:
                    self.logger.warning(f"Could not get price for {symbol}: {e}")
                    return False
            else:
                self.logger.warning(f"🔍 {symbol}: No entry price found")
                return False
            
            # ผ่านเงื่อนไขทั้งหมด - แก้ไม้ทันที
            self.logger.info(f"✅ {symbol} meets recovery conditions - Risk: {risk_per_lot:.2%}, Distance: {price_distance:.1f} pips")
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking recovery continuation: {e}")
            return False
    
    def _continue_recovery_chain(self, group_id: str, recovery_pair: Dict):
        """ดำเนินการ recovery chain ต่อเนื่อง"""
        try:
            symbol = recovery_pair['symbol']
            order_id = recovery_pair.get('order_id')
            
            self.logger.info("=" * 60)
            self.logger.info(f"🔄 CONTINUING RECOVERY CHAIN FOR {symbol} (Order: {order_id})")
            self.logger.info("=" * 60)
            
            # ตรวจสอบเงื่อนไขการแก้ไม้
            risk_per_lot = self._calculate_risk_per_lot(recovery_pair)
            price_distance = self._calculate_price_distance(recovery_pair)
            
            self.logger.info(f"🔍 Checking hedging conditions for {symbol} (Order: {order_id}):")
            self.logger.info(f"   Risk: {risk_per_lot:.2%} (need ≥5%) {'✅' if risk_per_lot >= 0.05 else '❌'}")
            self.logger.info(f"   Distance: {price_distance:.1f} pips (need ≥10) {'✅' if price_distance >= 10 else '❌'}")
            
            if risk_per_lot < 0.05 or price_distance < 10:
                self.logger.info(f"⏳ {symbol}: Conditions not met - waiting")
                return
            
            self.logger.info(f"✅ {symbol}: All conditions met - continuing recovery")
            
            # หาคู่เงินใหม่สำหรับ recovery
            self.logger.info(f"🔍 Searching for correlation candidates for {symbol}")
            correlation_candidates = self._find_optimal_correlation_pairs(symbol)
            
            if not correlation_candidates:
                self.logger.warning(f"❌ No correlation candidates found for {symbol}")
                return
            
            # เลือกคู่เงินที่ดีที่สุด
            best_correlation = correlation_candidates[0]
            self.logger.info(f"🎯 Best correlation: {best_correlation['symbol']} (correlation: {best_correlation['correlation']:.2f})")
            
            # ส่งออเดอร์ recovery ใหม่
            self.logger.info(f"📤 Sending new recovery order for {symbol} -> {best_correlation['symbol']}")
            success = self._execute_correlation_position(recovery_pair, best_correlation, group_id)
            
            if success:
                # บันทึกว่าไม้นี้แก้แล้ว
                self._mark_position_as_hedged(recovery_pair)
                self.logger.info(f"✅ Chain recovery continued for {symbol} -> {best_correlation['symbol']}")
            else:
                self.logger.error(f"❌ Failed to continue chain recovery for {symbol} -> {best_correlation['symbol']}")
                
        except Exception as e:
            self.logger.error(f"Error continuing recovery chain: {e}")
    
    def update_recovery_parameters(self, params: Dict):
        """อัพเดทพารามิเตอร์ recovery"""
        try:
            for key, value in params.items():
                if key in self.recovery_thresholds:
                    self.recovery_thresholds[key] = value
                    self.logger.info(f"Updated {key} to {value}")
                    
        except Exception as e:
            self.logger.error(f"Error updating recovery parameters: {e}")
    
    def check_recovery_opportunities(self):
        """ตรวจสอบโอกาสการ recovery"""
        try:
            # ตรวจสอบ recovery positions ที่มีอยู่
            for recovery_id, position in self.recovery_positions.items():
                if position['status'] == 'active':
                    # ตรวจสอบว่าต้องการ recovery เพิ่มหรือไม่
                    if self._should_continue_recovery(position):
                        self._continue_recovery_chain(position['group_id'], position)
                        
        except Exception as e:
            self.logger.error(f"Error checking recovery opportunities: {e}")
    
    def _initiate_correlation_recovery(self, losing_position: Dict):
        """เริ่ม correlation recovery"""
        try:
            symbol = losing_position['symbol']
            self.logger.info(f"🔄 Starting correlation recovery for {symbol}")
            
            # หาคู่เงินที่เหมาะสมสำหรับ recovery
            correlation_candidates = self._find_optimal_correlation_pairs(symbol)
            
            if not correlation_candidates:
                self.logger.warning(f"   No correlation candidates found for {symbol}")
                return
            
            # เลือกคู่เงินที่ดีที่สุด
            best_correlation = correlation_candidates[0]
            self.logger.info(f"   Best correlation: {best_correlation['symbol']} (correlation: {best_correlation['correlation']:.2f})")
            
            # ส่งออเดอร์ recovery
            success = self._execute_correlation_position(losing_position, best_correlation, losing_position.get('group_id', 'unknown'))
            
            if success:
                self.logger.info(f"✅ Correlation recovery position opened: {best_correlation['symbol']}")
            else:
                self.logger.error(f"❌ Failed to open correlation recovery position: {best_correlation['symbol']}")
                
        except Exception as e:
            self.logger.error(f"Error initiating correlation recovery: {e}")
    
    def _find_optimal_correlation_pairs(self, base_symbol: str) -> List[Dict]:
        """
        ⚡ CRITICAL: Find optimal correlation pairs for recovery
        หาคู่เงินที่มี correlation กับคู่ที่กำหนด (EURUSD, GBPUSD, EURGBP)
        """
        try:
            correlation_candidates = []
            
            # คู่เงินที่กำหนดสำหรับ arbitrage
            arbitrage_pairs = ['EURUSD', 'GBPUSD', 'EURGBP']
            
            # ตรวจสอบว่า base_symbol เป็นคู่ที่กำหนดหรือไม่
            if base_symbol not in arbitrage_pairs:
                self.logger.warning(f"⚠️ {base_symbol} is not in arbitrage pairs, using all available pairs")
                return self._find_correlation_pairs_for_any_symbol(base_symbol)
            
            # Get all available pairs from broker
            all_pairs = self.broker.get_available_pairs()
            
            if not all_pairs:
                self.logger.warning("No available pairs from broker, using fallback pairs")
                # ใช้ fallback pairs สำหรับ correlation recovery
                all_pairs = [
                    'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'USDNZD',
                    'EURJPY', 'GBPJPY', 'AUDJPY', 'CADJPY', 'CHFJPY', 'NZDJPY',
                    'EURCHF', 'GBPCHF', 'AUDCHF', 'CADCHF', 'NZDCHF',
                    'EURAUD', 'GBPAUD', 'USDAUD', 'AUDCAD', 'AUDNZD',
                    'EURNZD', 'GBPNZD', 'USDNZD', 'AUDNZD', 'CADNZD',
                    'EURCAD', 'GBPCAD', 'USDCAD', 'AUDCAD', 'CADCHF'
                ]
            
            # หาคู่เงินที่มี correlation กับ base_symbol
            self.logger.info(f"🔍 Searching correlation pairs for {base_symbol} from {len(all_pairs)} available pairs")
            checked_pairs = 0
            valid_correlations = 0
            
            for symbol in all_pairs:
                if symbol == base_symbol:
                    continue
                
                # ตรวจสอบว่าเป็นคู่ arbitrage หรือไม่ (ไม่ให้ซ้ำ)
                if symbol in arbitrage_pairs:
                    continue
                
                checked_pairs += 1
                
                # คำนวณ correlation ตามประเภทคู่เงิน
                correlation = self._calculate_correlation_for_arbitrage_pair(base_symbol, symbol)
                
                # ตรวจสอบว่า correlation อยู่ในเกณฑ์ที่ยอมรับได้
                if correlation >= self.recovery_thresholds['min_correlation']:
                    valid_correlations += 1
                    # กำหนดทิศทางตาม correlation
                    direction = self._determine_recovery_direction(base_symbol, symbol, correlation)
                    
                    correlation_candidates.append({
                        'symbol': symbol,
                        'correlation': correlation,
                        'recovery_strength': correlation,
                        'direction': direction
                    })
                    
                    self.logger.debug(f"✅ Found correlation: {symbol} = {correlation:.2f} ({direction})")
                else:
                    self.logger.debug(f"❌ Low correlation: {symbol} = {correlation:.2f} (min: {self.recovery_thresholds['min_correlation']:.2f})")
            
            self.logger.info(f"📊 Correlation search results: {valid_correlations}/{checked_pairs} pairs passed correlation threshold")
            
            # Sort by recovery strength (highest first)
            correlation_candidates.sort(key=lambda x: x['recovery_strength'], reverse=True)
            
            if not correlation_candidates:
                self.logger.error(f"❌ No correlation candidates created for {base_symbol}")
            else:
                self.logger.info(f"🎯 Final correlation candidates for {base_symbol}: {len(correlation_candidates)} pairs")
                for i, candidate in enumerate(correlation_candidates[:3]):  # แสดง 3 อันดับแรก
                    self.logger.info(f"   {i+1}. {candidate['symbol']}: {candidate['correlation']:.2f} ({candidate['direction']})")
            
            return correlation_candidates
            
        except Exception as e:
            self.logger.error(f"Error finding optimal correlation pairs for {base_symbol}: {e}")
            return []
    
    def _calculate_correlation_for_arbitrage_pair(self, base_symbol: str, target_symbol: str) -> float:
        """คำนวณ correlation ระหว่างคู่เงิน arbitrage กับคู่เงินอื่น"""
        try:
            # ใช้ correlation values ที่แม่นยำตามประเภทคู่เงิน
            if base_symbol == 'EURUSD':
                # Major pairs with high correlation
                if target_symbol in ['GBPUSD', 'AUDUSD', 'NZDUSD']:
                    return 0.85  # High correlation
                # EUR crosses
                elif target_symbol in ['EURJPY', 'EURCHF', 'EURCAD', 'EURAUD', 'EURNZD']:
                    return 0.75  # Medium-high correlation
                # USD crosses
                elif target_symbol in ['USDJPY', 'USDCAD', 'USDCHF', 'USDNZD']:
                    return 0.70  # Medium correlation
                # Other major pairs
                elif target_symbol in ['GBPJPY', 'GBPCHF', 'GBPCAD', 'GBPAUD', 'GBPNZD']:
                    return 0.65  # Medium correlation
                # Minor pairs
                elif target_symbol in ['AUDJPY', 'AUDCHF', 'AUDCAD', 'AUDNZD']:
                    return 0.60  # Lower correlation
                # CAD, CHF, NZD crosses
                elif target_symbol in ['CADJPY', 'CHFJPY', 'NZDJPY', 'CADCHF', 'NZDCHF']:
                    return 0.55  # Lower correlation
                else:
                    return 0.50  # Default correlation
                    
            elif base_symbol == 'GBPUSD':
                # Major pairs with high correlation
                if target_symbol in ['EURUSD', 'AUDUSD', 'NZDUSD']:
                    return 0.85  # High correlation
                # GBP crosses
                elif target_symbol in ['GBPJPY', 'GBPCHF', 'GBPCAD', 'GBPAUD', 'GBPNZD']:
                    return 0.80  # High correlation
                # USD crosses
                elif target_symbol in ['USDJPY', 'USDCAD', 'USDCHF', 'USDNZD']:
                    return 0.70  # Medium correlation
                # EUR crosses
                elif target_symbol in ['EURJPY', 'EURCHF', 'EURCAD', 'EURAUD', 'EURNZD']:
                    return 0.65  # Medium correlation
                # Other major pairs
                elif target_symbol in ['AUDJPY', 'AUDCHF', 'AUDCAD', 'AUDNZD']:
                    return 0.60  # Lower correlation
                # Minor pairs
                elif target_symbol in ['CADJPY', 'CHFJPY', 'NZDJPY', 'CADCHF', 'NZDCHF']:
                    return 0.55  # Lower correlation
                else:
                    return 0.50  # Default correlation
                    
            elif base_symbol == 'EURGBP':
                # EUR crosses
                if target_symbol in ['EURJPY', 'EURCHF', 'EURCAD', 'EURAUD', 'EURNZD']:
                    return 0.80  # High correlation
                # GBP crosses
                elif target_symbol in ['GBPJPY', 'GBPCHF', 'GBPCAD', 'GBPAUD', 'GBPNZD']:
                    return 0.80  # High correlation
                # Major pairs
                elif target_symbol in ['EURUSD', 'GBPUSD']:
                    return 0.75  # Medium-high correlation
                # USD crosses
                elif target_symbol in ['USDJPY', 'USDCAD', 'USDCHF', 'USDNZD']:
                    return 0.65  # Medium correlation
                # Other major pairs
                elif target_symbol in ['AUDJPY', 'AUDCHF', 'AUDCAD', 'AUDNZD']:
                    return 0.60  # Lower correlation
                # Minor pairs
                elif target_symbol in ['CADJPY', 'CHFJPY', 'NZDJPY', 'CADCHF', 'NZDCHF']:
                    return 0.55  # Lower correlation
                else:
                    return 0.50  # Default correlation
            
            return 0.50  # Default correlation
            
        except Exception as e:
            self.logger.error(f"Error calculating correlation: {e}")
            return 0.50
    
    def _calculate_correlation_for_any_pair(self, base_symbol: str, target_symbol: str) -> float:
        """คำนวณ correlation ระหว่างคู่เงินใดๆ (ไม่ใช่คู่ arbitrage)"""
        try:
            # ใช้ correlation values ที่แม่นยำตามประเภทคู่เงิน
            if base_symbol == 'USDJPY':
                if target_symbol in ['EURJPY', 'GBPJPY', 'AUDJPY', 'CADJPY', 'CHFJPY', 'NZDJPY']:
                    return 0.80  # High correlation
                elif target_symbol in ['EURUSD', 'GBPUSD', 'AUDUSD', 'USDCAD', 'USDCHF', 'USDNZD']:
                    return 0.70  # Medium correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'AUDUSD':
                if target_symbol in ['NZDUSD', 'EURUSD', 'GBPUSD']:
                    return 0.85  # High correlation
                elif target_symbol in ['AUDJPY', 'AUDCHF', 'AUDCAD', 'AUDNZD']:
                    return 0.80  # High correlation
                elif target_symbol in ['EURAUD', 'GBPAUD', 'USDAUD']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'USDCAD':
                if target_symbol in ['CADJPY', 'CADCHF', 'EURCAD', 'GBPCAD']:
                    return 0.80  # High correlation
                elif target_symbol in ['EURUSD', 'GBPUSD', 'AUDUSD', 'USDJPY', 'USDCHF', 'USDNZD']:
                    return 0.70  # Medium correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'USDCHF':
                if target_symbol in ['CHFJPY', 'EURCHF', 'GBPCHF', 'AUDCHF', 'CADCHF', 'NZDCHF']:
                    return 0.80  # High correlation
                elif target_symbol in ['EURUSD', 'GBPUSD', 'AUDUSD', 'USDJPY', 'USDCAD', 'USDNZD']:
                    return 0.70  # Medium correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'USDNZD':
                if target_symbol in ['NZDJPY', 'NZDCHF', 'EURNZD', 'GBPNZD', 'AUDNZD', 'CADNZD']:
                    return 0.80  # High correlation
                elif target_symbol in ['EURUSD', 'GBPUSD', 'AUDUSD', 'USDJPY', 'USDCAD', 'USDCHF']:
                    return 0.70  # Medium correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'EURJPY':
                if target_symbol in ['EURUSD', 'EURCHF', 'EURCAD', 'EURAUD', 'EURNZD']:
                    return 0.80  # High correlation
                elif target_symbol in ['GBPJPY', 'AUDJPY', 'CADJPY', 'CHFJPY', 'NZDJPY']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'GBPJPY':
                if target_symbol in ['GBPUSD', 'GBPCHF', 'GBPCAD', 'GBPAUD', 'GBPNZD']:
                    return 0.80  # High correlation
                elif target_symbol in ['EURJPY', 'AUDJPY', 'CADJPY', 'CHFJPY', 'NZDJPY']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'AUDJPY':
                if target_symbol in ['AUDUSD', 'AUDCHF', 'AUDCAD', 'AUDNZD']:
                    return 0.80  # High correlation
                elif target_symbol in ['EURJPY', 'GBPJPY', 'CADJPY', 'CHFJPY', 'NZDJPY']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'CADJPY':
                if target_symbol in ['USDCAD', 'CADCHF', 'EURCAD', 'GBPCAD']:
                    return 0.80  # High correlation
                elif target_symbol in ['EURJPY', 'GBPJPY', 'AUDJPY', 'CHFJPY', 'NZDJPY']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'CHFJPY':
                if target_symbol in ['USDCHF', 'EURCHF', 'GBPCHF', 'AUDCHF', 'CADCHF', 'NZDCHF']:
                    return 0.80  # High correlation
                elif target_symbol in ['EURJPY', 'GBPJPY', 'AUDJPY', 'CADJPY', 'NZDJPY']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'NZDJPY':
                if target_symbol in ['USDNZD', 'EURNZD', 'GBPNZD', 'AUDNZD', 'CADNZD', 'NZDCHF']:
                    return 0.80  # High correlation
                elif target_symbol in ['EURJPY', 'GBPJPY', 'AUDJPY', 'CADJPY', 'CHFJPY']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'EURCHF':
                if target_symbol in ['EURUSD', 'EURJPY', 'EURCAD', 'EURAUD', 'EURNZD']:
                    return 0.80  # High correlation
                elif target_symbol in ['GBPCHF', 'AUDCHF', 'CADCHF', 'NZDCHF']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'GBPCHF':
                if target_symbol in ['GBPUSD', 'GBPJPY', 'GBPCAD', 'GBPAUD', 'GBPNZD']:
                    return 0.80  # High correlation
                elif target_symbol in ['EURCHF', 'AUDCHF', 'CADCHF', 'NZDCHF']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'AUDCHF':
                if target_symbol in ['AUDUSD', 'AUDJPY', 'AUDCAD', 'AUDNZD']:
                    return 0.80  # High correlation
                elif target_symbol in ['EURCHF', 'GBPCHF', 'CADCHF', 'NZDCHF']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'CADCHF':
                if target_symbol in ['USDCAD', 'CADJPY', 'EURCAD', 'GBPCAD']:
                    return 0.80  # High correlation
                elif target_symbol in ['EURCHF', 'GBPCHF', 'AUDCHF', 'NZDCHF']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'NZDCHF':
                if target_symbol in ['USDNZD', 'NZDJPY', 'EURNZD', 'GBPNZD', 'AUDNZD', 'CADNZD']:
                    return 0.80  # High correlation
                elif target_symbol in ['EURCHF', 'GBPCHF', 'AUDCHF', 'CADCHF']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'EURAUD':
                if target_symbol in ['EURUSD', 'EURJPY', 'EURCHF', 'EURCAD', 'EURNZD']:
                    return 0.80  # High correlation
                elif target_symbol in ['GBPAUD', 'USDAUD', 'AUDJPY', 'AUDCHF', 'AUDCAD', 'AUDNZD']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'GBPAUD':
                if target_symbol in ['GBPUSD', 'GBPJPY', 'GBPCHF', 'GBPCAD', 'GBPNZD']:
                    return 0.80  # High correlation
                elif target_symbol in ['EURAUD', 'USDAUD', 'AUDJPY', 'AUDCHF', 'AUDCAD', 'AUDNZD']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'USDAUD':
                if target_symbol in ['AUDJPY', 'AUDCHF', 'AUDCAD', 'AUDNZD']:
                    return 0.80  # High correlation
                elif target_symbol in ['EURAUD', 'GBPAUD', 'EURUSD', 'GBPUSD']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'AUDCAD':
                if target_symbol in ['AUDUSD', 'AUDJPY', 'AUDCHF', 'AUDNZD']:
                    return 0.80  # High correlation
                elif target_symbol in ['USDCAD', 'CADJPY', 'CADCHF', 'EURCAD', 'GBPCAD']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'EURNZD':
                if target_symbol in ['EURUSD', 'EURJPY', 'EURCHF', 'EURCAD', 'EURAUD']:
                    return 0.80  # High correlation
                elif target_symbol in ['GBPNZD', 'USDNZD', 'AUDNZD', 'CADNZD', 'NZDJPY', 'NZDCHF']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'GBPNZD':
                if target_symbol in ['GBPUSD', 'GBPJPY', 'GBPCHF', 'GBPCAD', 'GBPAUD']:
                    return 0.80  # High correlation
                elif target_symbol in ['EURNZD', 'USDNZD', 'AUDNZD', 'CADNZD', 'NZDJPY', 'NZDCHF']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'USDNZD':
                if target_symbol in ['NZDJPY', 'NZDCHF', 'EURNZD', 'GBPNZD', 'AUDNZD', 'CADNZD']:
                    return 0.80  # High correlation
                elif target_symbol in ['EURUSD', 'GBPUSD', 'AUDUSD', 'USDJPY', 'USDCAD', 'USDCHF']:
                    return 0.70  # Medium correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'AUDNZD':
                if target_symbol in ['AUDUSD', 'AUDJPY', 'AUDCHF', 'AUDCAD']:
                    return 0.80  # High correlation
                elif target_symbol in ['USDNZD', 'NZDJPY', 'NZDCHF', 'EURNZD', 'GBPNZD', 'CADNZD']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'CADNZD':
                if target_symbol in ['USDCAD', 'CADJPY', 'CADCHF', 'EURCAD', 'GBPCAD']:
                    return 0.80  # High correlation
                elif target_symbol in ['USDNZD', 'NZDJPY', 'NZDCHF', 'EURNZD', 'GBPNZD', 'AUDNZD']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'EURCAD':
                if target_symbol in ['EURUSD', 'EURJPY', 'EURCHF', 'EURAUD', 'EURNZD']:
                    return 0.80  # High correlation
                elif target_symbol in ['USDCAD', 'CADJPY', 'CADCHF', 'GBPCAD']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            elif base_symbol == 'GBPCAD':
                if target_symbol in ['GBPUSD', 'GBPJPY', 'GBPCHF', 'GBPAUD', 'GBPNZD']:
                    return 0.80  # High correlation
                elif target_symbol in ['USDCAD', 'CADJPY', 'CADCHF', 'EURCAD']:
                    return 0.75  # Medium-high correlation
                else:
                    return 0.60  # Lower correlation
                    
            else:
                return 0.60  # Default correlation for unknown pairs
            
        except Exception as e:
            self.logger.error(f"Error calculating correlation for any pair: {e}")
            return 0.60
    
    def _determine_recovery_direction(self, base_symbol: str, target_symbol: str, correlation: float) -> str:
        """กำหนดทิศทางการ recovery ตาม correlation"""
        try:
            # ใช้ทิศทางที่แตกต่างกันตาม correlation
            if correlation >= 0.75:  # High correlation
                # ใช้ทิศทางเดียวกัน
                return 'BUY'  # BUY สำหรับ high correlation
            elif correlation >= 0.60:  # Medium correlation
                # ใช้ทิศทางตรงข้าม
                return 'SELL'  # SELL สำหรับ medium correlation
            else:  # Lower correlation
                # ใช้ทิศทางเดียวกัน
                return 'BUY'  # BUY สำหรับ lower correlation
                
        except Exception as e:
            self.logger.error(f"Error determining recovery direction: {e}")
            return 'BUY'  # Default to BUY
    
    def _find_correlation_pairs_for_any_symbol(self, base_symbol: str) -> List[Dict]:
        """หาคู่เงินที่มี correlation กับคู่เงินใดๆ (ไม่ใช่คู่ arbitrage)"""
        try:
            correlation_candidates = []
            
            # Get all available pairs from broker
            all_pairs = self.broker.get_available_pairs()
            if not all_pairs:
                all_pairs = [
                    'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD',
                    'EURGBP', 'EURJPY', 'GBPJPY', 'AUDJPY', 'CADJPY',
                    'EURCHF', 'GBPCHF', 'USDCHF', 'AUDCHF', 'CADCHF',
                    'EURAUD', 'GBPAUD', 'USDAUD', 'AUDCAD', 'EURNZD',
                    'GBPNZD', 'USDNZD', 'AUDNZD', 'CADNZD', 'CHFJPY',
                    'EURCAD', 'GBPCAD'
                ]
            
            # คู่เงินที่กำหนดสำหรับ arbitrage
            arbitrage_pairs = ['EURUSD', 'GBPUSD', 'EURGBP']
            
            for symbol in all_pairs:
                if symbol == base_symbol:
                    continue
                
                # ตรวจสอบว่าเป็นคู่ arbitrage หรือไม่ (ไม่ให้ซ้ำ)
                if symbol in arbitrage_pairs:
                    continue
                
                # คำนวณ correlation ตามประเภทคู่เงิน
                correlation = self._calculate_correlation_for_any_pair(base_symbol, symbol)
                
                if correlation >= self.recovery_thresholds['min_correlation']:
                    # กำหนดทิศทางตาม correlation
                    direction = self._determine_recovery_direction(base_symbol, symbol, correlation)
                    
                    correlation_candidates.append({
                        'symbol': symbol,
                        'correlation': correlation,
                        'recovery_strength': correlation,
                        'direction': direction
                    })
            
            return correlation_candidates
            
        except Exception as e:
            self.logger.error(f"Error finding correlation pairs for any symbol: {e}")
            return []
    
    def _execute_correlation_position(self, original_position: Dict, correlation_candidate: Dict, group_id: str) -> bool:
        """
        ⚡ CRITICAL: Execute correlation position for recovery
        """
        try:
            symbol = correlation_candidate['symbol']
            correlation = correlation_candidate['correlation']
            direction = correlation_candidate['direction']
            
            # Calculate correlation volume
            correlation_volume = self._calculate_hedge_volume(original_position, correlation_candidate)
            
            # คำนวณ lot size ตาม balance-based sizing
            original_lot = original_position.get('lot_size', original_position.get('volume', 0.1))
            original_symbol = original_position.get('symbol', '')
            
            correlation_lot_size = self._calculate_hedge_lot_size(
                original_lot=original_lot,
                correlation=correlation,
                loss_percent=0.0,  # ไม่ใช้ loss_percent ในระบบใหม่
                original_symbol=original_symbol
            )
            
            # Send correlation order
            success = self._send_correlation_order(symbol, correlation_lot_size, group_id)
            
            if success:
                # ดึงราคาปัจจุบันเป็น entry price
                entry_price = self.broker.get_current_price(symbol)
                if not entry_price:
                    entry_price = 0.0
                
                # Store correlation position
                correlation_position = {
                    'symbol': symbol,
                    'direction': direction,
                    'lot_size': correlation_lot_size,
                    'entry_price': entry_price,
                    'correlation': correlation,
                    'correlation_ratio': 1.0,  # ใช้ lot size เดียวกัน
                    'original_pair': original_position['symbol'],
                    'group_id': group_id,
                    'opened_at': datetime.now(),
                    'status': 'active'
                }
                
                recovery_id = f"recovery_{group_id}_{symbol}_{int(datetime.now().timestamp())}"
                self.recovery_positions[recovery_id] = correlation_position
                self._update_recovery_data()
                
                # บันทึกข้อมูลการแก้ไม้
                self._log_hedging_action(original_position, correlation_position, correlation_candidate)
                
                self.logger.info(f"✅ Correlation recovery position opened: {symbol}")
                return True
            else:
                self.logger.error(f"❌ Failed to open correlation recovery position: {symbol}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing correlation position: {e}")
            return False
    
    def _log_hedging_action(self, original_position: Dict, correlation_position: Dict, correlation_candidate: Dict):
        """แสดง log การแก้ไม้ให้ชัดเจน"""
        try:
            original_symbol = original_position['symbol']
            hedge_symbol = correlation_position['symbol']
            correlation = correlation_candidate['correlation']
            
            self.logger.info("=" * 60)
            self.logger.info(f"🎯 HEDGING ACTION COMPLETED")
            self.logger.info("=" * 60)
            self.logger.info(f"📉 Original Position: {original_symbol}")
            self.logger.info(f"   Order ID: {original_position.get('order_id', 'N/A')}")
            self.logger.info(f"   Lot Size: {original_position.get('lot_size', 0.1)}")
            self.logger.info(f"   Entry Price: {original_position.get('entry_price', 0.0):.5f}")
            
            self.logger.info(f"🛡️ Hedge Position: {hedge_symbol}")
            self.logger.info(f"   Lot Size: {correlation_position['lot_size']}")
            self.logger.info(f"   Entry Price: {correlation_position['entry_price']:.5f}")
            self.logger.info(f"   Direction: {correlation_position['direction']}")
            
            self.logger.info(f"📊 Correlation Details:")
            self.logger.info(f"   Correlation: {correlation:.2f}")
            self.logger.info(f"   Recovery Strength: {correlation_candidate.get('recovery_strength', correlation):.2f}")
            
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"Error logging hedging action: {e}")
    
    def _calculate_hedge_volume(self, original_position: Dict, correlation_candidate: Dict) -> float:
        """คำนวณขนาด volume สำหรับ correlation position - ใช้ balance-based sizing"""
        try:
            # ดึงข้อมูลจาก original position
            original_lot = original_position.get('lot_size', original_position.get('volume', 0.1))
            original_symbol = original_position.get('symbol', '')
            
            # ใช้ balance-based lot sizing
            volume = self._calculate_hedge_lot_size(
                original_lot=original_lot,
                correlation=correlation_candidate.get('correlation', 0.5),
                loss_percent=0.0,
                original_symbol=original_symbol
            )
            
            return float(volume)
            
        except Exception as e:
            self.logger.error(f"Error calculating hedge volume: {e}")
            return 0.1
    
    def _send_correlation_order(self, symbol: str, lot_size: float, group_id: str) -> bool:
        """ส่งออเดอร์ correlation recovery"""
        try:
            # สร้าง comment
            group_number = group_id.split('_')[-1]
            comment = f"RECOVERY_G{group_number}_{symbol}"
            
            # ส่งออเดอร์
            result = self.broker.place_order(
                symbol=symbol,
                order_type='BUY',  # Default to BUY
                volume=lot_size,
                comment=comment
            )
            
            if result and result.get('retcode') == 10009:
                self.logger.info(f"✅ Correlation recovery order sent: {symbol} {lot_size} lot")
                return True
            else:
                self.logger.error(f"❌ Failed to send correlation recovery order: {symbol}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending correlation recovery order: {e}")
            return False
    
    def check_recovery_positions(self):
        """ตรวจสอบ recovery positions - เฉพาะกลุ่มที่ยังเปิดอยู่"""
        try:
            # ตรวจสอบว่ามี recovery positions หรือไม่
            if not self.recovery_positions:
                return
            
            # ทำความสะอาด positions เก่าที่ปิดไปแล้ว
            self.cleanup_closed_recovery_positions()
            
            active_recovery_count = 0
            positions_to_remove = []
            
            for recovery_id, position in self.recovery_positions.items():
                if position['status'] == 'active':
                    # ตรวจสอบว่ากลุ่มยังเปิดอยู่หรือไม่
                    group_id = position.get('group_id', '')
                    if not group_id:
                        positions_to_remove.append(recovery_id)
                        continue
                    
                    # ตรวจสอบว่ากลุ่มยังเปิดอยู่จริงหรือไม่ (ต้องตรวจสอบกับ arbitrage_detector)
                    # ถ้าไม่มี group_id ใน active_groups แสดงว่ากลุ่มปิดแล้ว
                    active_recovery_count += 1
                    
                    # ตรวจสอบว่าต้องการ recovery เพิ่มหรือไม่
                    if self._should_continue_recovery(position):
                        self.logger.info(f"🔄 Starting chain recovery for {position['symbol']}")
                        self._continue_recovery_chain(position['group_id'], position)
                    # ไม่แสดง log ถ้าไม่พร้อม recovery เพื่อลด log spam
            
            # ลบ positions ที่ไม่มี group_id
            for recovery_id in positions_to_remove:
                del self.recovery_positions[recovery_id]
                self.logger.info(f"🗑️ Removed orphaned recovery position: {recovery_id}")
            
            # แสดง log เฉพาะเมื่อมี recovery positions และมีการเปลี่ยนแปลง
            if active_recovery_count > 0:
                self.logger.debug(f"📊 Active recovery positions: {active_recovery_count}")
                        
        except Exception as e:
            self.logger.error(f"Error checking recovery positions: {e}")
    
    def _close_recovery_position(self, recovery_id: str):
        """ปิด recovery position"""
        try:
            if recovery_id not in self.recovery_positions:
                self.logger.debug(f"Recovery position {recovery_id} not found in tracking data")
                return
            
            position = self.recovery_positions[recovery_id]
            symbol = position['symbol']
            order_id = position.get('order_id')
            
            # ตรวจสอบว่าตำแหน่งยังเปิดอยู่จริงหรือไม่
            position_exists = False
            if order_id:
                all_positions = self.broker.get_all_positions()
                for pos in all_positions:
                    if pos['ticket'] == order_id:
                        position_exists = True
                        break
            
            if not position_exists:
                # ตำแหน่งถูกปิดไปแล้ว ให้อัพเดทสถานะ
                position['status'] = 'closed'
                position['closed_at'] = datetime.now()
                position['close_reason'] = 'already_closed'
                self._update_recovery_data()
                self.logger.info(f"✅ Recovery position {symbol} was already closed - updated status")
                return
            
            # ปิดออเดอร์
            success = self.broker.close_position(symbol)
            
            if success:
                position['status'] = 'closed'
                position['closed_at'] = datetime.now()
                position['close_reason'] = 'manual_close'
                self._update_recovery_data()
                self.logger.info(f"✅ Recovery position closed: {symbol}")
            else:
                self.logger.error(f"❌ Failed to close recovery position: {symbol}")
                    
        except Exception as e:
            self.logger.error(f"Error closing recovery position: {e}")
    
    def get_correlation_matrix(self) -> Dict:
        """Get correlation matrix"""
        return self.correlation_matrix
    
    def get_recovery_positions(self) -> Dict:
        """Get recovery positions"""
        return self.recovery_positions
    
    def close_recovery_position(self, recovery_id: str, reason: str = "manual"):
        """Close recovery position manually"""
        try:
            if recovery_id in self.recovery_positions:
                position = self.recovery_positions[recovery_id]
                
                # ปิดออเดอร์
                success = self.broker.close_position(position['symbol'])
                
                if success:
                    position['status'] = 'closed'
                    position['closed_at'] = datetime.now()
                    position['close_reason'] = reason
                    self._update_recovery_data()
                    self.logger.info(f"✅ Recovery position closed: {position['symbol']} (reason: {reason})")
                else:
                    self.logger.error(f"❌ Failed to close recovery position: {position['symbol']}")
                    
        except Exception as e:
            self.logger.error(f"Error closing recovery position: {e}")
    
    def get_correlation_performance(self) -> Dict:
        """Get correlation performance metrics"""
        return self.recovery_metrics
    
    def get_active_recovery_engine_status(self) -> Dict:
        """Get active recovery engine status"""
        return {
            'recovery_mode': self.recovery_mode,
            'hedge_ratio_optimization': self.hedge_ratio_optimization,
            'portfolio_rebalancing': self.portfolio_rebalancing,
            'multi_timeframe_analysis': self.multi_timeframe_analysis,
            'never_cut_loss': self.never_cut_loss,
            'active_recovery_chains': len(self.recovery_chains),
            'active_recovery_positions': len([p for p in self.recovery_positions.values() if p['status'] == 'active'])
        }
    
    def _save_recovery_data(self):
        """บันทึกข้อมูล recovery positions และ chains ลงไฟล์"""
        try:
            import json
            import os
            
            # สร้างโฟลเดอร์ data ถ้าไม่มี
            os.makedirs(os.path.dirname(self.persistence_file), exist_ok=True)
            
            # เตรียมข้อมูลสำหรับบันทึก
            save_data = {
                'recovery_positions': self.recovery_positions,
                'recovery_chains': self.recovery_chains,
                'recovery_metrics': self.recovery_metrics,
                'hedged_pairs': list(self.hedged_pairs),
                'hedged_positions': self.hedged_positions,
                'hedged_groups': self.hedged_groups,
                'saved_at': datetime.now().isoformat()
            }
            
            # บันทึกลงไฟล์
            with open(self.persistence_file, 'w') as f:
                json.dump(save_data, f, indent=2, default=str)
            
            self.logger.debug(f"💾 Saved {len(self.recovery_positions)} recovery positions to {self.persistence_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving recovery data: {e}")
    
    def _load_recovery_data(self):
        """โหลดข้อมูล recovery positions และ chains จากไฟล์"""
        try:
            import json
            import os
            from datetime import datetime
            
            if not os.path.exists(self.persistence_file):
                self.logger.debug("No recovery persistence file found, starting fresh")
                return
            
            with open(self.persistence_file, 'r') as f:
                save_data = json.load(f)
            
            # โหลดข้อมูลกลับมา
            self.recovery_positions = save_data.get('recovery_positions', {})
            self.recovery_chains = save_data.get('recovery_chains', {})
            self.recovery_metrics = save_data.get('recovery_metrics', {
                'total_recoveries': 0,
                'successful_recoveries': 0,
                'failed_recoveries': 0,
                'avg_recovery_time_hours': 0,
                'total_recovered_amount': 0.0
            })
            self.hedged_pairs = set(save_data.get('hedged_pairs', []))
            self.hedged_positions = save_data.get('hedged_positions', {})
            self.hedged_groups = save_data.get('hedged_groups', {})
            
            saved_at = save_data.get('saved_at', 'Unknown')
            
            if self.recovery_positions or self.recovery_chains or self.hedged_pairs:
                self.logger.info(f"📂 Loaded recovery data from {self.persistence_file}")
                self.logger.info(f"   Recovery positions: {len(self.recovery_positions)}")
                self.logger.info(f"   Recovery chains: {len(self.recovery_chains)}")
                self.logger.info(f"   Hedged pairs: {len(self.hedged_pairs)}")
                self.logger.info(f"   Hedged positions: {len(self.hedged_positions)}")
                self.logger.info(f"   Saved at: {saved_at}")
            else:
                self.logger.debug("No recovery data found in persistence file")
                
        except Exception as e:
            self.logger.error(f"Error loading recovery data: {e}")
            # เริ่มต้นใหม่ถ้าโหลดไม่ได้
            self.recovery_positions = {}
            self.recovery_chains = {}
            self.recovery_metrics = {
                'total_recoveries': 0,
                'successful_recoveries': 0,
                'failed_recoveries': 0,
                'avg_recovery_time_hours': 0,
                'total_recovered_amount': 0.0
            }
            self.hedged_pairs = set()
            self.hedged_positions = {}
            self.hedged_groups = {}
    
    def _update_recovery_data(self):
        """อัปเดตข้อมูล recovery และบันทึกลงไฟล์"""
        try:
            self._save_recovery_data()
        except Exception as e:
            self.logger.error(f"Error updating recovery data: {e}")
    
    def _remove_recovery_data(self, recovery_id: str):
        """ลบข้อมูล recovery และบันทึกลงไฟล์"""
        try:
            if recovery_id in self.recovery_positions:
                del self.recovery_positions[recovery_id]
            self._save_recovery_data()
        except Exception as e:
            self.logger.error(f"Error removing recovery data: {e}")
    
    def clear_hedged_data_for_group(self, group_id: str):
        """ล้างข้อมูลการแก้ไม้สำหรับกลุ่มที่ปิดแล้ว"""
        try:
            # ลบข้อมูลการแก้ไม้ที่เกี่ยวข้องกับกลุ่มนี้
            positions_to_remove = []
            for order_id, hedged_info in self.hedged_positions.items():
                if hedged_info.get('position_info', {}).get('group_id') == group_id:
                    positions_to_remove.append(order_id)
            
            for order_id in positions_to_remove:
                symbol = self.hedged_positions[order_id].get('symbol')
                if symbol:
                    self.hedged_pairs.discard(symbol)
                del self.hedged_positions[order_id]
            
            # ลบข้อมูลกลุ่ม
            if group_id in self.hedged_groups:
                del self.hedged_groups[group_id]
            
            if positions_to_remove:
                self.logger.info(f"🗑️ Cleared {len(positions_to_remove)} hedged positions for group {group_id}")
                self._update_recovery_data()
                
            # แสดงสรุปสถานะ recovery positions หลังจากล้างข้อมูล
            self.log_recovery_positions_summary()
            
        except Exception as e:
            self.logger.error(f"Error clearing hedged data for group {group_id}: {e}")
    
    def cleanup_closed_recovery_positions(self):
        """ทำความสะอาด recovery positions ที่ปิดไปแล้ว"""
        try:
            positions_to_remove = []
            
            for recovery_id, position in self.recovery_positions.items():
                if position.get('status') == 'closed':
                    # ตรวจสอบว่าเป็น positions เก่าที่ปิดไปนานแล้วหรือไม่
                    closed_at = position.get('closed_at')
                    if closed_at:
                        if isinstance(closed_at, str):
                            closed_at = datetime.fromisoformat(closed_at)
                        
                        # ลบ positions ที่ปิดไปแล้วมากกว่า 1 ชั่วโมง
                        if (datetime.now() - closed_at).total_seconds() > 3600:
                            positions_to_remove.append(recovery_id)
            
            # ลบ positions เก่า
            for recovery_id in positions_to_remove:
                del self.recovery_positions[recovery_id]
            
            if positions_to_remove:
                self.logger.info(f"🗑️ Cleaned up {len(positions_to_remove)} old closed recovery positions")
                self._update_recovery_data()
            
        except Exception as e:
            self.logger.error(f"Error cleaning up closed recovery positions: {e}")
    
    def get_hedging_status(self) -> Dict:
        """ดึงสถานะการแก้ไม้ทั้งหมด"""
        try:
            return {
                'hedged_pairs': list(self.hedged_pairs),
                'hedged_positions_count': len(self.hedged_positions),
                'hedged_groups_count': len(self.hedged_groups),
                'hedged_positions': self.hedged_positions,
                'hedged_groups': self.hedged_groups
            }
        except Exception as e:
            self.logger.error(f"Error getting hedging status: {e}")
            return {}
    
    def log_recovery_positions_summary(self):
        """แสดงสรุปสถานะ recovery positions"""
        try:
            if not self.recovery_positions:
                self.logger.info("📊 No recovery positions found")
                return
            
            active_count = 0
            closed_count = 0
            
            for position in self.recovery_positions.values():
                if position.get('status') == 'active':
                    active_count += 1
                elif position.get('status') == 'closed':
                    closed_count += 1
            
            self.logger.info("=" * 60)
            self.logger.info("📊 RECOVERY POSITIONS SUMMARY")
            self.logger.info("=" * 60)
            self.logger.info(f"Total Recovery Positions: {len(self.recovery_positions)}")
            self.logger.info(f"Active Positions: {active_count}")
            self.logger.info(f"Closed Positions: {closed_count}")
            self.logger.info(f"Hedged Pairs: {len(self.hedged_pairs)}")
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"Error logging recovery positions summary: {e}")
    
    def stop(self):
        """หยุดการทำงานของ Correlation Manager"""
        try:
            self.is_running = False
            # บันทึกข้อมูลก่อนปิด
            self._save_recovery_data()
            self.logger.info("🛑 Correlation Manager stopped")
        except Exception as e:
            self.logger.error(f"Error stopping Correlation Manager: {e}")
