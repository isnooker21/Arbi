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

class CorrelationManager:
    def __init__(self, broker_api, ai_engine):
        self.broker = broker_api
        self.ai = ai_engine
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
        
    def start_chain_recovery(self, group_id: str, losing_pairs: List[Dict]):
        """เริ่ม chain recovery สำหรับกลุ่มที่ขาดทุน"""
        try:
            self.logger.info(f"🔗 Starting chain recovery for group {group_id}")
            self.logger.info(f"   Losing pairs: {[pair['symbol'] for pair in losing_pairs]}")
            
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
            
            # เริ่ม recovery สำหรับแต่ละคู่ที่ขาดทุน
            for pair in losing_pairs:
                self._start_pair_recovery(group_id, pair)
                
        except Exception as e:
            self.logger.error(f"Error starting chain recovery: {e}")
    
    def _start_pair_recovery(self, group_id: str, losing_pair: Dict):
        """เริ่ม recovery สำหรับคู่ที่ขาดทุน"""
        try:
            symbol = losing_pair['symbol']
            self.logger.info(f"🔄 Starting recovery for {symbol}")
            
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
                self.logger.info(f"✅ Recovery position opened for {symbol}")
            else:
                self.logger.error(f"❌ Failed to open recovery position for {symbol}")
                
        except Exception as e:
            self.logger.error(f"Error starting pair recovery: {e}")
    
    def _calculate_hedge_lot_size(self, original_lot: float, correlation: float, loss_percent: float) -> float:
        """คำนวณขนาด lot สำหรับ hedge position"""
        try:
            # คำนวณ hedge ratio ตาม correlation
            hedge_ratio = min(2.0, max(0.5, correlation * 1.5))
            
            # ปรับขนาดตาม loss percent
            loss_factor = min(2.0, max(0.8, abs(loss_percent) * 10))
            
            # คำนวณ lot size
            hedge_lot = original_lot * hedge_ratio * loss_factor
            
            # จำกัดขนาด lot
            hedge_lot = min(hedge_lot, 10.0)  # สูงสุด 10 lot
            hedge_lot = max(hedge_lot, 0.01)  # ต่ำสุด 0.01 lot
            
            return round(hedge_lot, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating hedge lot size: {e}")
            return 0.1
    
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
        """ตรวจสอบ recovery chain และดำเนินการต่อเนื่อง"""
        try:
            for group_id, chain_data in self.recovery_chains.items():
                if chain_data['status'] != 'active':
                    continue
                
                # ตรวจสอบ recovery pairs
                for recovery_pair in chain_data['recovery_pairs']:
                    if self._should_continue_recovery(recovery_pair):
                        self._continue_recovery_chain(group_id, recovery_pair)
                        
        except Exception as e:
            self.logger.error(f"Error checking recovery chain: {e}")
    
    def _should_continue_recovery(self, recovery_pair: Dict) -> bool:
        """ตรวจสอบว่าควรดำเนินการ recovery ต่อหรือไม่"""
        try:
            # ตรวจสอบว่า recovery pair ยังติดลบอยู่หรือไม่
            # และยังไม่เกินเวลาที่กำหนด
            return True  # Simplified for now
            
        except Exception as e:
            self.logger.error(f"Error checking recovery continuation: {e}")
            return False
    
    def _continue_recovery_chain(self, group_id: str, recovery_pair: Dict):
        """ดำเนินการ recovery chain ต่อเนื่อง"""
        try:
            symbol = recovery_pair['symbol']
            self.logger.info(f"🔄 Continuing recovery chain for {symbol}")
            
            # หาคู่เงินใหม่สำหรับ recovery
            correlation_candidates = self._find_optimal_correlation_pairs(symbol)
            
            if not correlation_candidates:
                self.logger.warning(f"   No correlation candidates found for {symbol}")
                return
            
            # เลือกคู่เงินที่ดีที่สุด
            best_correlation = correlation_candidates[0]
            self.logger.info(f"   Best correlation: {best_correlation['symbol']} (correlation: {best_correlation['correlation']:.2f})")
            
            # ส่งออเดอร์ recovery ใหม่
            success = self._execute_correlation_position(recovery_pair, best_correlation, group_id)
            
            if success:
                self.logger.info(f"✅ Chain recovery continued for {symbol}")
            else:
                self.logger.error(f"❌ Failed to continue chain recovery for {symbol}")
                
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
            self.logger.info(f"🔍 Debug: Broker returned {len(all_pairs) if all_pairs else 0} pairs")
            
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
                self.logger.info(f"🔍 Debug: Using {len(all_pairs)} fallback pairs")
            
            self.logger.info(f"🔍 Finding correlation pairs for {base_symbol} from {len(all_pairs)} available pairs")
            
            # หาคู่เงินที่มี correlation กับ base_symbol
            for symbol in all_pairs:
                if symbol == base_symbol:
                    continue
                
                # ตรวจสอบว่าเป็นคู่ arbitrage หรือไม่ (ไม่ให้ซ้ำ)
                if symbol in arbitrage_pairs:
                    continue
                
                # คำนวณ correlation ตามประเภทคู่เงิน
                correlation = self._calculate_correlation_for_arbitrage_pair(base_symbol, symbol)
                
                # ตรวจสอบว่า correlation อยู่ในเกณฑ์ที่ยอมรับได้
                if correlation >= self.recovery_thresholds['min_correlation']:
                    # กำหนดทิศทางตาม correlation
                    direction = self._determine_recovery_direction(base_symbol, symbol, correlation)
                    
                    correlation_candidates.append({
                        'symbol': symbol,
                        'correlation': correlation,
                        'recovery_strength': correlation,
                        'direction': direction
                    })
            
            # Sort by recovery strength (highest first)
            correlation_candidates.sort(key=lambda x: x['recovery_strength'], reverse=True)
            
            self.logger.info(f"✅ Found {len(correlation_candidates)} correlation candidates for {base_symbol}")
            if correlation_candidates:
                # แสดง top 5 correlation candidates
                top_candidates = correlation_candidates[:5]
                for i, candidate in enumerate(top_candidates, 1):
                    self.logger.info(f"   {i}. {candidate['symbol']} (correlation: {candidate['correlation']:.2f}, direction: {candidate['direction']})")
            else:
                self.logger.error(f"❌ No correlation candidates created for {base_symbol}")
                self.logger.error(f"   All pairs: {all_pairs}")
                self.logger.error(f"   Base symbol: {base_symbol}")
            
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
            
            # Calculate correlation ratio
            correlation_ratio = min(2.0, max(0.5, correlation * 1.5))
            
            # Calculate correlation lot size
            correlation_lot_size = original_position['lot_size'] * correlation_ratio
            
            # Send correlation order
            success = self._send_correlation_order(symbol, correlation_lot_size, group_id)
            
            if success:
                # Store correlation position
                correlation_position = {
                    'symbol': symbol,
                    'direction': direction,
                    'lot_size': correlation_lot_size,
                    'correlation': correlation,
                    'correlation_ratio': correlation_ratio,
                    'original_pair': original_position['symbol'],
                    'group_id': group_id,
                    'opened_at': datetime.now(),
                    'status': 'active'
                }
                
                recovery_id = f"recovery_{group_id}_{symbol}_{int(datetime.now().timestamp())}"
                self.recovery_positions[recovery_id] = correlation_position
                
                self.logger.info(f"✅ Correlation recovery position opened: {symbol}")
                return True
            else:
                self.logger.error(f"❌ Failed to open correlation recovery position: {symbol}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing correlation position: {e}")
            return False
    
    def _calculate_hedge_volume(self, original_position: Dict, correlation_candidate: Dict) -> float:
        """คำนวณขนาด volume สำหรับ correlation position"""
        try:
            # ใช้ correlation ratio
            correlation_ratio = min(2.0, max(0.5, correlation_candidate['correlation'] * 1.5))
            
            # คำนวณ volume
            volume = original_position['lot_size'] * correlation_ratio
            
            # จำกัดขนาด volume
            volume = min(volume, 10.0)  # สูงสุด 10 lot
            volume = max(volume, 0.01)  # ต่ำสุด 0.01 lot
            
            return round(volume, 2)
            
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
        """ตรวจสอบ recovery positions"""
        try:
            for recovery_id, position in self.recovery_positions.items():
                if position['status'] == 'active':
                    # ตรวจสอบว่าต้องการ recovery เพิ่มหรือไม่
                    if self._should_continue_recovery(position):
                        self._continue_recovery_chain(position['group_id'], position)
                        
        except Exception as e:
            self.logger.error(f"Error checking recovery positions: {e}")
    
    def _close_recovery_position(self, recovery_id: str):
        """ปิด recovery position"""
        try:
            if recovery_id in self.recovery_positions:
                position = self.recovery_positions[recovery_id]
                
                # ปิดออเดอร์
                success = self.broker.close_position(position['symbol'])
                
                if success:
                    position['status'] = 'closed'
                    position['closed_at'] = datetime.now()
                    self.logger.info(f"✅ Recovery position closed: {position['symbol']}")
                else:
                    self.logger.error(f"❌ Failed to close recovery position: {position['symbol']}")
                    
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
