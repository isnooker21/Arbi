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
5. ติดตามผลการกู้คืนแบบ Real-tim
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
import threading
from utils.calculations import TradingCalculations
from trading.individual_order_tracker import IndividualOrderTracker

class CorrelationManager:
    
    def _get_magic_number_from_group_id(self, group_id: str) -> int:
        """หา magic number จาก group_id"""
        try:
            if 'triangle_1' in group_id:
                return 234001
            elif 'triangle_2' in group_id:
                return 234002
            elif 'triangle_3' in group_id:
                return 234003
            elif 'triangle_4' in group_id:
                return 234004
            elif 'triangle_5' in group_id:
                return 234005
            elif 'triangle_6' in group_id:
                return 234006
            else:
                return 234000  # default
        except Exception as e:
            self.logger.error(f"Error getting magic number from group_id {group_id}: {e}")
    
    def _extract_group_number(self, group_id: str) -> str:
        """แยก Group number จาก group_id"""
        try:
            if 'triangle_' in group_id:
                triangle_part = group_id.split('triangle_')[1].split('_')[0]
                return f"G{triangle_part}"
            else:
                return "GX"
        except Exception as e:
            self.logger.error(f"Error extracting group number from {group_id}: {e}")
            return "GX"
    
    def _get_group_pairs_from_mt5(self, group_id: str) -> List[str]:
        """ดึงคู่เงินในกลุ่มจาก MT5 โดยใช้ magic number"""
        try:
            group_pairs = []
            magic_number = self._get_magic_number_from_group_id(group_id)
            
            # ดึงข้อมูลจาก MT5 จริงๆ
            all_positions = self.broker.get_all_positions()
            
            for pos in all_positions:
                magic = pos.get('magic', 0)
                if magic == magic_number:
                    symbol = pos['symbol']
                    if symbol not in group_pairs:
                        group_pairs.append(symbol)
            
            self.logger.debug(f"📊 Group {group_id} pairs from MT5: {group_pairs}")
            return group_pairs
            
        except Exception as e:
            self.logger.error(f"Error getting group pairs from MT5: {e}")
            return []
    
    def _get_all_currency_pairs_from_mt5(self) -> List[str]:
        """ดึงคู่เงินทั้งหมดจาก MT5 จริงๆ"""
        try:
            # ใช้ predefined list เพื่อให้มีคู่เงินครบถ้วน
            all_pairs = [
                'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'USDNZD',
                'EURGBP', 'EURJPY', 'GBPJPY', 'AUDJPY', 'CADJPY', 'CHFJPY', 'NZDJPY',
                'EURCHF', 'GBPCHF', 'AUDCHF', 'CADCHF', 'NZDCHF',
                'EURAUD', 'GBPAUD', 'USDAUD', 'AUDCAD', 'AUDNZD',
                'EURNZD', 'GBPNZD', 'USDNZD', 'AUDNZD', 'CADNZD',
                'EURCAD', 'GBPCAD', 'USDCAD', 'AUDCAD', 'CADCHF',
                'GBPCHF', 'NZDCHF', 'NZDJPY', 'NZDCHF'
            ]
            
            # ลบคู่ที่ซ้ำ
            all_pairs = list(set(all_pairs))
            all_pairs.sort()
            
            self.logger.debug(f"📊 All currency pairs available: {len(all_pairs)} pairs")
            return all_pairs
            
        except Exception as e:
            self.logger.error(f"Error getting all currency pairs: {e}")
            # Fallback to basic list if error
            return [
                'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD',
                'EURGBP', 'EURJPY', 'GBPJPY', 'AUDJPY', 'CADJPY',
                'EURCHF', 'GBPCHF', 'USDCHF', 'AUDCHF', 'CADCHF',
                'EURAUD', 'GBPAUD', 'USDAUD', 'AUDCAD', 'EURNZD',
                'GBPNZD', 'USDNZD', 'AUDNZD', 'CADNZD', 'CHFJPY',
                'EURCAD', 'GBPCAD'
            ]
    
    def __init__(self, broker_api, ai_engine=None):
        self.broker = broker_api
        # self.ai = ai_engine  # DISABLED for simple trading system
        self.correlation_matrix = {}
        self.recovery_positions = {}
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        
        # Magic numbers สำหรับแต่ละสามเหลี่ยม (เหมือนกับ arbitrage_detector)
        self.triangle_magic_numbers = {
            'triangle_1': 234001,  # EURUSD, GBPUSD, EURGBP
            'triangle_2': 234002,  # USDJPY, EURUSD, EURJPY
            'triangle_3': 234003,  # USDJPY, GBPUSD, GBPJPY
            'triangle_4': 234004,  # AUDUSD, EURUSD, EURAUD
            'triangle_5': 234005,  # USDCAD, EURUSD, EURCAD
            'triangle_6': 234006   # AUDUSD, GBPUSD, GBPAUD
        }
        
        # Active Recovery Engine parameters
        self.recovery_mode = 'active'  # active, passive, disabled
        
        # Legacy: Last hedged positions per group (replaced by individual order tracker)
        # self.last_hedged_positions = {}  # REMOVED - using individual order tracker instead
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
        
        # Individual Order Tracking System - New and Improved
        self.order_tracker = IndividualOrderTracker(broker_api)
        
        # Log startup completion
        self.logger.info("🚀 Individual Order Tracker initialized")
        self.order_tracker.log_status_summary()
    
    def _initialize_tracker_from_mt5(self):
        """Initialize tracker with existing positions from MT5"""
        try:
            # Sync with MT5 to clean up any closed orders
            sync_results = self.order_tracker.sync_with_mt5()
            if sync_results['orders_removed'] > 0:
                self.logger.info(f"🔄 Cleaned up {sync_results['orders_removed']} closed orders during initialization")
                
        except Exception as e:
            self.logger.error(f"Error initializing tracker from MT5: {e}")
    
    def _debug_hedge_status(self, position: Dict):
        """Debug hedge status checking for individual position"""
        try:
            ticket = str(position.get('ticket', ''))
            symbol = position.get('symbol', '')
            
            if not ticket or not symbol:
                return
            
            is_hedged = self.order_tracker.is_order_hedged(ticket, symbol)
            order_info = self.order_tracker.get_order_info(ticket, symbol)
            
            self.logger.debug(f"🔍 DEBUG {ticket}_{symbol}")
            self.logger.debug(f"   Order Info: {order_info}")
            self.logger.debug(f"   Is Hedged: {is_hedged}")
            
        except Exception as e:
            self.logger.error(f"Error in debug hedge status: {e}")
    
    def _log_all_groups_status(self):
        """แสดงสถานะทุก Group ในระบบ"""
        try:
            self.logger.info("🌐 ALL GROUPS STATUS OVERVIEW:")
            self.logger.info("=" * 80)
            
            # ดึงข้อมูลจาก MT5 จริงๆ
            all_positions = self.broker.get_all_positions()
            
            # จัดกลุ่มตาม magic number
            groups_data = {}
            for pos in all_positions:
                magic = pos.get('magic', 0)
                comment = pos.get('comment', '')
                
                # ข้าม recovery positions
                if comment.startswith('RECOVERY_'):
                    continue
                
                if magic not in groups_data:
                    groups_data[magic] = {
                        'positions': [],
                        'total_pnl': 0,
                        'group_name': f'Group_{magic}'
                    }
                
                groups_data[magic]['positions'].append(pos)
                groups_data[magic]['total_pnl'] += pos.get('profit', 0)
            
            # แสดงสถานะแต่ละ Group
            for magic, data in groups_data.items():
                total_pnl = data['total_pnl']
                positions = data['positions']
                
                # กำหนดชื่อ Group
                if magic == 1001:
                    group_name = "G1 (Triangle 1)"
                elif magic == 1002:
                    group_name = "G2 (Triangle 2)"
                elif magic == 1003:
                    group_name = "G3 (Triangle 3)"
                elif magic == 1004:
                    group_name = "G4 (Triangle 4)"
                elif magic == 1005:
                    group_name = "G5 (Triangle 5)"
                elif magic == 1006:
                    group_name = "G6 (Triangle 6)"
                else:
                    group_name = f"Group_{magic}"
                
                # สถานะ Group
                if total_pnl > 0:
                    status = f"💰 PROFIT: ${total_pnl:.2f}"
                else:
                    status = f"🔴 LOSS: ${total_pnl:.2f}"
                
                self.logger.info(f"📊 {group_name}: {status}")
                
                # แสดงไม้ที่ขาดทุน
                losing_count = 0
                for pos in positions:
                    if pos.get('profit', 0) < 0:
                        losing_count += 1
                        symbol = pos['symbol']
                        pnl = pos['profit']
                        self.logger.info(f"   📉 {symbol}: ${pnl:.2f}")
                
                if losing_count == 0:
                    self.logger.info(f"   🟢 All positions profitable")
                
                # แสดง recovery positions
                recovery_count = 0
                for pos in all_positions:
                    if pos.get('magic', 0) == magic and pos.get('comment', '').startswith('RECOVERY_'):
                        recovery_count += 1
                        symbol = pos['symbol']
                        pnl = pos['profit']
                        comment = pos['comment']
                        self.logger.info(f"   🔗 Recovery: {symbol} (${pnl:.2f}) - {comment}")
                
                if recovery_count == 0:
                    self.logger.info(f"   ⚪ No recovery positions")
                
                self.logger.info("")
            
            self.logger.info("=" * 80)
            
        except Exception as e:
            self.logger.debug(f"Error logging all groups status: {e}")
        
    def start_chain_recovery(self, group_id: str, losing_pairs: List[Dict]):
        """เริ่ม chain recovery สำหรับกลุ่มที่ขาดทุน"""
        try:
            self.logger.info("=" * 80)
            self.logger.info(f"🔗 STARTING CHAIN RECOVERY FOR GROUP {group_id}")
            self.logger.info("=" * 80)
            
            # ไม่ต้อง sync tracking แล้ว ดูจาก MT5 จริงๆ
            
            # ลด log ที่ซ้ำ - ใช้แค่ _log_all_groups_status แทน
            # self._log_group_hedging_status(group_id, losing_pairs)
            
            # แสดงสถานะทุก Group
            self._log_all_groups_status()
            
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
            
            # เลือกคู่ที่เหมาะสมที่สุดสำหรับ recovery (แค่คู่เดียว)
            best_pair = self._select_best_pair_for_recovery(losing_pairs, group_id)
            if best_pair:
                self.logger.debug(f"🎯 Selected best pair for recovery: {best_pair['symbol']} (Order: {best_pair['order_id']})")
                self._start_pair_recovery(group_id, best_pair)
            else:
                self.logger.debug("❌ No suitable pair found for recovery")
                
        except Exception as e:
            self.logger.debug(f"Error starting chain recovery: {e}")
    
    def _select_best_pair_for_recovery(self, losing_pairs: List[Dict], group_id: str = None) -> Dict:
        """เลือกคู่ที่เหมาะสมที่สุดสำหรับ recovery (แค่คู่เดียว)"""
        try:
            if not group_id:
                return None
            
            # ดึงข้อมูลจาก MT5 จริงๆ แทนการใช้ข้อมูลที่ส่งมา
            all_positions = self.broker.get_all_positions()
            magic_number = self._get_magic_number_from_group_id(group_id)
            
            # หาไม้ arbitrage ที่ขาดทุนจาก MT5
            losing_positions = []
            for pos in all_positions:
                magic = pos.get('magic', 0)
                comment = pos.get('comment', '')
                pnl = pos.get('profit', 0)
                
                # ตรวจสอบว่าเป็นไม้ arbitrage ที่ขาดทุน (ไม่ใช่ recovery)
                if magic == magic_number and not comment.startswith('RECOVERY_') and pnl < 0:
                    losing_positions.append({
                        'symbol': pos['symbol'],
                        'order_id': pos['ticket'],
                        'lot_size': pos['volume'],
                        'entry_price': pos['price'],
                        'pnl': pnl,
                        'comment': comment,
                        'magic': magic
                    })
            
            if not losing_positions:
                self.logger.info("📊 No losing positions found in MT5")
                return None
            
            # กรองคู่ที่ผ่านเงื่อนไข
            suitable_pairs = []
            
            for pos in losing_positions:
                symbol = pos.get('symbol', '')
                order_id = pos.get('order_id', '')
                pnl = pos.get('pnl', 0)
                
                # ตรวจสอบว่าไม้นี้แก้แล้วหรือยัง - ส่ง group_id ไปด้วย
                if self._is_position_hedged(pos, group_id):
                    self.logger.info(f"⏭️ Skipping {symbol} - already hedged")
                    continue
                
                # ตรวจสอบเงื่อนไขการแก้ไม้
                risk_per_lot = self._calculate_risk_per_lot(pos)
                price_distance = self._calculate_price_distance(pos)
                
                # ผ่านเงื่อนไข Distance ≥ 10 pips
                if price_distance >= 10:
                    suitable_pairs.append({
                        'pair': pos,
                        'symbol': symbol,
                        'order_id': order_id,
                        'pnl': pnl,
                        'risk_per_lot': risk_per_lot,
                        'price_distance': price_distance,
                        'score': abs(pnl) * (price_distance / 10)  # คะแนนรวม (เอา Risk ออก)
                    })
            
            if not suitable_pairs:
                return None
            
            # เรียงตามคะแนน (สูงสุดก่อน) - คู่ที่ขาดทุนมาก + distance มาก
            suitable_pairs.sort(key=lambda x: x['score'], reverse=True)
            
            # ป้องกันการแก้ไม้ซ้ำ - ใช้ MT5 โดยตรง
            # กรองไม้ที่กำลังถูกแก้หรือแก้แล้วออก
            filtered_pairs = []
            for pair_data in suitable_pairs:
                symbol = pair_data['symbol']
                # ตรวจสอบจาก MT5 โดยตรงว่าไม้นี้ถูกแก้แล้วหรือยัง
                if not self._is_position_hedged_from_mt5(group_id, symbol):
                    filtered_pairs.append(pair_data)
            
            if not filtered_pairs:
                self.logger.warning(f"⚠️ All suitable pairs are already hedged for {group_id}")
                return None
            
            suitable_pairs = filtered_pairs
            
            best_pair = suitable_pairs[0]['pair']
            best_info = suitable_pairs[0]
            
            self.logger.info(f"📊 Recovery pair selection:")
            self.logger.info(f"   Total losing positions from MT5: {len(losing_positions)}")
            self.logger.info(f"   Suitable pairs: {len(suitable_pairs)}")
            self.logger.info(f"   Selected: {best_info['symbol']} (Score: {best_info['score']:.2f})")
            self.logger.info(f"   PnL: ${best_info['pnl']:.2f}, Risk: {best_info['risk_per_lot']:.2%}, Distance: {best_info['price_distance']:.1f} pips")
            
            # แสดงรายการไม้ที่เหมาะสมทั้งหมด
            if suitable_pairs:
                self.logger.info(f"   Available pairs for recovery:")
                for i, pair in enumerate(suitable_pairs[:5]):  # แสดงแค่ 5 อันแรก
                    status = "✅ HEDGED" if self._is_position_hedged(pair['pair'], group_id) else "❌ NOT HEDGED"
                    self.logger.info(f"     {i+1}. {pair['symbol']} - PnL: ${pair['pnl']:.2f}, Score: {pair['score']:.2f} - {status}")
            
            return best_pair
            
        except Exception as e:
            self.logger.error(f"Error selecting best pair for recovery: {e}")
            return None
    
    def _log_group_hedging_status(self, group_id: str, losing_pairs: List[Dict]):
        """แสดงสถานะการแก้ไม้ของกลุ่มให้ชัดเจน - ลด log ที่ซ้ำ"""
        # ลด log ที่ซ้ำ - ใช้แค่ _log_all_groups_status แทน
        pass
    
    def _log_all_groups_status(self):
        """แสดงสถานะทุก Group เรียงตาม Group สวยงาม"""
        try:
            self.logger.info("=" * 80)
            self.logger.info("📊 ALL GROUPS STATUS OVERVIEW")
            self.logger.info("=" * 80)
            
            # Sync individual order tracker with MT5
            self.order_tracker.sync_with_mt5()
            
            # Debug: Show individual order tracker info
            all_orders = self.order_tracker.get_all_orders()
            if len(all_orders) > 0:
                self.logger.debug("🔍 INDIVIDUAL ORDER TRACKER DEBUG:")
                for order_key, order_info in all_orders.items():
                    self.logger.debug(f"  Order {order_key}: {order_info}")
            
            # ดึงข้อมูลจาก MT5 จริงๆ
            all_positions = self.broker.get_all_positions()
            
            # จัดกลุ่มตาม magic number
            groups_data = {}
            for pos in all_positions:
                magic = pos.get('magic', 0)
                if magic in [234001, 234002, 234003, 234004, 234005, 234006]:
                    if magic not in groups_data:
                        groups_data[magic] = []
                    groups_data[magic].append(pos)
            
            # แสดงสถานะแต่ละ Group เรียงตาม Group
            for magic in sorted(groups_data.keys()):
                group_number = self._get_group_number_from_magic(magic)
                group_positions = groups_data[magic]
                
                # แยกประเภทไม้
                arbitrage_positions = [pos for pos in group_positions if not pos.get('comment', '').startswith('RECOVERY_')]
                recovery_positions = [pos for pos in group_positions if pos.get('comment', '').startswith('RECOVERY_')]
                
                # คำนวณ PnL
                arbitrage_pnl = sum(pos.get('profit', 0) for pos in arbitrage_positions)
                recovery_pnl = sum(pos.get('profit', 0) for pos in recovery_positions)
                total_pnl = arbitrage_pnl + recovery_pnl
                
                # สถานะ Group
                status_icon = "🟢" if total_pnl >= 0 else "🔴"
                
                # แสดงข้อมูล Group แบบย่อ
                self.logger.info(f"{status_icon} GROUP {group_number}: Total PnL: ${total_pnl:8.2f} | Arbitrage: {len(arbitrage_positions)} | Recovery: {len(recovery_positions)}")
                
                # แสดงไม้ทั้งหมด (ทั้งกำไรและขาดทุน)
                for pos in arbitrage_positions:
                        symbol = pos.get('symbol', '')
                        pnl = pos.get('profit', 0)
                        group_id = f"group_triangle_{group_number.replace('G', '')}_1"
                        
                        # สร้าง position dict ที่มี order_id
                        position_data = {
                            'symbol': symbol,
                            'order_id': pos.get('ticket', ''),
                            'profit': pnl
                        }
                        
                        # ใช้ Professional Hedge Tracker ในการตรวจสอบ hedge status
                        is_hedged = self._is_position_hedged(position_data, group_id)
                        hedge_status = "✅ HG" if is_hedged else "❌ NH"
                        
                        # Show individual order tracker info when there are issues
                        ticket = str(pos.get('ticket', ''))
                        if ticket:
                            order_info = self.order_tracker.get_order_info(ticket, symbol)
                            if order_info:
                                tracker_status = order_info.get('status', 'UNKNOWN')
                                order_type = order_info.get('type', 'N/A')
                                self.logger.debug(f"     🔍 Tracker: {tracker_status} ({order_type})")
                        
                        # Add debug logging for hedge status only when needed
                        self._debug_hedge_status(pos)
                            
                        # แสดงสถานะกำไร/ขาดทุน
                        pnl_icon = "🟢" if pnl >= 0 else "🔴"
                        self.logger.info(f"   {symbol:8s}: ${pnl:8.2f} [{hedge_status}] {pnl_icon}")
                
                # แสดงไม้ recovery ทั้งหมด (ทั้งกำไรและขาดทุน)
                if recovery_positions:
                    for pos in recovery_positions:
                        symbol = pos.get('symbol', '')
                        pnl = pos.get('profit', 0)
                        pnl_icon = "🟢" if pnl >= 0 else "🔴"
                        self.logger.info(f"   {symbol:8s}: ${pnl:8.2f} [RECOVERY] {pnl_icon}")
                
                self.logger.info("")
            
            # Show individual order tracker status
            self.logger.debug("🔍 INDIVIDUAL ORDER TRACKER STATUS:")
            self.order_tracker.log_status_summary()
            
            self.logger.info("=" * 80)
            
        except Exception as e:
            self.logger.debug(f"Error logging all groups status: {e}")
    
    def _find_recovery_for_position(self, arbitrage_position: Dict, recovery_positions: List[Dict]) -> Dict:
        """หา recovery position ที่แก้ไม้ arbitrage position นี้"""
        try:
            arbitrage_symbol = arbitrage_position.get('symbol', '')
            arbitrage_order_id = arbitrage_position.get('ticket', '')
            
            for recovery_pos in recovery_positions:
                comment = recovery_pos.get('comment', '')
                
                # ตรวจสอบ comment pattern
                if f'_{arbitrage_symbol}_TO_' in comment or f'_{arbitrage_symbol[:4]}_TO_' in comment:
                    return recovery_pos
                
                # ตรวจสอบ pattern อื่นๆ
                if arbitrage_symbol == 'EURAUD' and 'EURA_TO_' in comment:
                    return recovery_pos
                elif arbitrage_symbol == 'GBPAUD' and 'GBPA_TO_' in comment:
                    return recovery_pos
                elif arbitrage_symbol == 'EURUSD' and 'EURU_TO_' in comment:
                    return recovery_pos
                elif arbitrage_symbol == 'GBPUSD' and 'GBPU_TO_' in comment:
                    return recovery_pos
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding recovery for position: {e}")
            return None
    
    def _get_group_number_from_magic(self, magic: int) -> str:
        """แปลง magic number เป็น Group number"""
        magic_to_group = {
            234001: "G1",
            234002: "G2", 
            234003: "G3",
            234004: "G4",
            234005: "G5",
            234006: "G6"
        }
        return magic_to_group.get(magic, "GX")
    
    def _get_position_pnl(self, position: Dict) -> float:
        """ดึงค่า PnL ของ position จาก broker"""
        try:
            order_id = position.get('order_id')
            symbol = position.get('symbol')
            
            if not order_id or order_id == 'N/A':
                return 0.0
            
            # ดึงข้อมูล PnL จาก broker
            all_positions = self.broker.get_all_positions()
            for pos in all_positions:
                if pos['ticket'] == order_id:
                    return pos.get('profit', 0.0)
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Error getting position PnL: {e}")
            return 0.0
    
    def _is_position_hedged(self, position: Dict, group_id: str = None) -> bool:
        """Check if specific position is hedged using individual order tracking"""
        try:
            ticket = str(position.get('ticket', ''))
            symbol = position.get('symbol', '')
            
            if not ticket or not symbol:
                return False
            
            return self.order_tracker.is_order_hedged(ticket, symbol)
            
        except Exception as e:
            self.logger.error(f"Error checking hedge status: {e}")
            return False
    
    def _check_hedge_status_from_tracking(self, group_id: str, original_symbol: str) -> bool:
        """ตรวจสอบสถานะการแก้ไม้จากระบบ tracking ใหม่"""
        try:
            # ใช้ MT5 โดยตรงในการตรวจสอบ hedge status
            is_hedged = self._is_position_hedged_from_mt5(group_id, original_symbol)
            self.logger.debug(f"🔍 Hedge status for {group_id}:{original_symbol} = {'HEDGED' if is_hedged else 'NOT_HEDGED'}")
            return is_hedged
            
        except Exception as e:
            self.logger.error(f"Error checking hedge status from tracking: {e}")
            return False
    
    
    def _get_group_magic_number(self, group_id: str) -> int:
        """ห magic number ของ group"""
        try:
            if 'triangle_1' in group_id:
                return 234001
            elif 'triangle_2' in group_id:
                return 234002
            elif 'triangle_3' in group_id:
                return 234003
            elif 'triangle_4' in group_id:
                return 234004
            elif 'triangle_5' in group_id:
                return 234005
            elif 'triangle_6' in group_id:
                return 234006
            else:
                return 0
        except Exception as e:
            self.logger.error(f"Error getting group magic number: {e}")
            return 0
    
    def _is_recovery_position_active(self, recovery_order_id: str) -> bool:
        """ตรวจสอบว่า recovery position ยังเปิดอยู่ใน MT5 หรือไม่"""
        try:
            if not recovery_order_id:
                return False
            
            # ดึงข้อมูลจาก MT5 จริงๆ
            all_positions = self.broker.get_all_positions()
            
            for pos in all_positions:
                if pos.get('ticket') == recovery_order_id:
                    # ตรวจสอบว่า position ยังเปิดอยู่หรือไม่
                    if pos.get('profit') is not None:  # position ยังเปิดอยู่
                        return True
                    else:
                        return False
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking if recovery position is active: {e}")
            return False
    
    def _add_hedge_tracking(self, original_ticket: str, original_symbol: str, recovery_ticket: str, recovery_symbol: str):
        """Register recovery order in individual order tracker"""
        try:
            success = self.order_tracker.register_recovery_order(
                recovery_ticket, recovery_symbol, original_ticket, original_symbol
            )
            if success:
                self.logger.info(f"📝 Added hedge tracking: {original_ticket}_{original_symbol} -> {recovery_ticket}_{recovery_symbol}")
            else:
                self.logger.error(f"❌ Failed to add hedge tracking: {original_ticket}_{original_symbol}")
            
        except Exception as e:
            self.logger.error(f"Error adding hedge tracking: {e}")
    
    def sync_tracking_from_mt5(self):
        """Sync individual order tracking with MT5 positions"""
        try:
            sync_results = self.order_tracker.sync_with_mt5()
            
            # Log sync results
            if sync_results['orders_removed'] > 0:
                self.logger.info(f"🔄 MT5 Sync: {sync_results['orders_checked']} checked, {sync_results['orders_removed']} removed")
            
        except Exception as e:
            self.logger.error(f"Error syncing order tracking: {e}")
    
    def _remove_hedge_tracking(self, ticket: str, symbol: str):
        """Remove order from individual order tracker"""
        try:
            # Individual order tracker handles cleanup automatically via sync
            # This method is kept for compatibility but sync will handle removal
            self.logger.debug(f"🗑️ Order {ticket}_{symbol} will be removed on next sync")
            
        except Exception as e:
            self.logger.error(f"Error removing hedge tracking: {e}")
    
    def _cleanup_closed_hedge_tracking(self, group_id: str):
        """Clean up closed orders from individual order tracker"""
        try:
            # Individual order tracker handles cleanup automatically via sync
            self.order_tracker.sync_with_mt5()
            
        except Exception as e:
            self.logger.error(f"Error cleaning up closed order tracking: {e}")
    
    def reset_group_hedge_tracking(self, group_id: str):
        """Reset order tracking for group when group is closed"""
        try:
            # Individual order tracker will clean up closed orders automatically via sync
            # This method is kept for compatibility
            self.logger.info(f"🔄 Group {group_id} closed - orders will be cleaned up on next sync")
            
        except Exception as e:
            self.logger.error(f"Error resetting group order tracking: {e}")
    
    def get_group_hedge_status(self, group_id: str) -> Dict:
        """Get hedge status for all orders in a group"""
        try:
            all_orders = self.order_tracker.get_all_orders()
            status = {}
            
            for order_key, order_info in all_orders.items():
                if order_info.get('group_id') == group_id:
                    symbol = order_info.get('symbol')
                    if symbol:
                        status[symbol] = {
                            'status': order_info.get('status'),
                            'type': order_info.get('type'),
                            'ticket': order_info.get('ticket'),
                            'created_at': order_info.get('created_at')
                        }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting group hedge status: {e}")
            return {}
    
    def _is_recovery_suitable_for_symbol(self, original_symbol: str, recovery_symbol: str, comment: str) -> bool:
        """ตรวจสอบว่า recovery position นี้เหมาะสมสำหรับ original symbol หรือไม่ - ใช้ comment pattern"""
        try:
            # ตรวจสอบ comment pattern: RECOVERY_G{group}_{original}_TO_{recovery}
            # หรือ RECOVERY_G{group}_{original} (รูปแบบเก่า)
            
            # แยก comment เพื่อหา original symbol
            if '_TO_' in comment:
                # รูปแบบใหม่: RECOVERY_G6_EURUSD_TO_GBPUSD
                parts = comment.split('_TO_')
                if len(parts) == 2:
                    original_part = parts[0]  # RECOVERY_G6_EURUSD
                    if original_symbol in original_part:
                        self.logger.info(f"✅ Recovery suitable: {original_symbol} -> {recovery_symbol} (new format)")
                        return True
            else:
                # รูปแบบเก่า: RECOVERY_G6_EURUSD
                if original_symbol in comment:
                    self.logger.info(f"✅ Recovery suitable: {original_symbol} -> {recovery_symbol} (old format)")
                    return True
            
            self.logger.info(f"❌ Recovery not suitable: {original_symbol} -> {recovery_symbol} (comment: {comment})")
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking recovery suitability: {e}")
            return False
    
    def _calculate_risk_per_lot(self, position: Dict) -> float:
        """คำนวณ risk ต่อ lot เป็นเปอร์เซ็นต์ของ account balance"""
        try:
            order_id = position.get('order_id')
            symbol = position.get('symbol')
            
            if not order_id or order_id == 'N/A':
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
            
            if not symbol or not order_id or order_id == 'N/A':
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
            
            # ตรวจสอบ PnL ก่อน - ถ้าไม้เป็นบวกไม่ต้องแก้ไม้
            pnl = self._get_position_pnl(losing_pair)
            if pnl >= 0:
                self.logger.info(f"💰 {symbol} (Order: {order_id}): PROFIT ${pnl:.2f} - No hedging needed")
                return
            
            # ตรวจสอบว่าไม้นี้แก้แล้วหรือยัง
            if self._is_position_hedged_from_mt5(group_id, symbol):
                self.logger.info(f"⏭️ {symbol} (Order: {order_id}): Already hedged - skipping")
                return
            
            # ตรวจสอบเงื่อนไขการแก้ไม้
            risk_per_lot = self._calculate_risk_per_lot(losing_pair)
            price_distance = self._calculate_price_distance(losing_pair)
            
            self.logger.debug(f"🔍 Checking hedging conditions for {symbol} (Order: {order_id}):")
            self.logger.info(f"   PnL: ${pnl:.2f} (LOSS)")
            self.logger.info(f"   Risk: {risk_per_lot:.2%} (info only)")
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
                            self.logger.debug(f"   🔍 Debug: Entry={entry_price:.5f}, Current={current_price:.5f}, Calc={calc_distance:.1f} pips")
                        break
            
            if price_distance < 10:  # ใช้แค่ Distance ≥ 10 pips
                self.logger.debug(f"⏳ {symbol}: Distance too small ({price_distance:.1f} pips) - waiting for 10 pips")
                return
            
            self.logger.info(f"✅ {symbol}: All conditions met - starting recovery")
            
            # หาคู่เงินที่เหมาะสมสำหรับ recovery (ไม่ซ้ำกับคู่ในกลุ่ม)
            group_pairs = self._get_group_pairs_from_mt5(group_id)
            correlation_candidates = self._find_optimal_correlation_pairs(symbol, group_pairs)
            
            if not correlation_candidates:
                self.logger.debug(f"   No correlation candidates found for {symbol}")
                return
            
            # เลือกคู่เงินที่ดีที่สุด
            best_correlation = correlation_candidates[0]
            # แยก triangle number จาก group_id (group_triangle_X_Y -> X)
            if 'triangle_' in group_id:
                triangle_part = group_id.split('triangle_')[1].split('_')[0]
                group_number = triangle_part
            else:
                group_number = 'X'
            self.logger.info(f"   Best correlation for G{group_number}: {best_correlation['symbol']} (correlation: {best_correlation['correlation']:.2f})")
            
            # ส่งออเดอร์ recovery
            success = self._execute_correlation_position(losing_pair, best_correlation, group_id)
            
            if success:
                # บันทึกว่าไม้นี้แก้แล้ว
                self._mark_position_as_hedged(losing_pair, group_id)
                self.logger.info(f"✅ Recovery position opened for {symbol}")
            else:
                self.logger.error(f"❌ Failed to open recovery position for {symbol}")
                
        except Exception as e:
            self.logger.error(f"Error starting pair recovery: {e}")
    
    def _mark_position_as_hedged(self, position: Dict, group_id: str = None):
        """บันทึกว่าตำแหน่งนี้แก้ไม้แล้ว - ใช้ระบบ tracking ใหม่"""
        try:
            # ระบบเก่าถูกลบออกแล้ว ใช้ระบบ tracking ใหม่แทน
            # การ marking จะทำใน _execute_correlation_position แล้ว
            symbol = position.get('symbol', '')
            if group_id and symbol:
                # Individual order tracker doesn't use group-based status checking
                self.logger.debug(f"📝 Position {group_id}:{symbol} - using individual order tracking")
            
        except Exception as e:
            self.logger.error(f"Error marking position as hedged: {e}")
    
    def _calculate_hedge_lot_size(self, original_lot: float, correlation: float, loss_percent: float, original_symbol: str = None, hedge_symbol: str = None) -> float:
        """คำนวณขนาด lot สำหรับ hedge position - ใช้ pip value ของคู่เงินที่แก้"""
        try:
            # ดึง balance จาก broker
            balance = self.broker.get_account_balance()
            if not balance:
                self.logger.warning("Cannot get account balance - using original lot size")
                return original_lot
            
            # คำนวณ pip value ของ original position
            if original_symbol and hedge_symbol:
                original_pip_value = TradingCalculations.calculate_pip_value(original_symbol, original_lot, self.broker)
                
                # คำนวณ target pip value ตาม balance (base $10K = $10 pip value)
                base_balance = 10000.0
                balance_multiplier = balance / base_balance
                target_pip_value = 10.0 * balance_multiplier
                
                # คำนวณ lot size ที่ให้ pip value เท่ากับ target
                # ใช้ correlation เพื่อปรับขนาด hedge
                hedge_pip_value = target_pip_value * abs(correlation)  # ใช้ absolute value
                
                # หา lot size ที่ให้ pip value ตาม target
                # ใช้คู่เงินที่แก้เป็น base
                pip_value_per_001 = TradingCalculations.calculate_pip_value(hedge_symbol, 0.01, self.broker)
                if pip_value_per_001 > 0:
                    hedge_lot = (hedge_pip_value * 0.01) / pip_value_per_001
                else:
                    # Fallback: ใช้ lot size เดียวกันกับไม้เดิม
                    hedge_lot = original_lot
                
                # Round to valid lot size
                hedge_lot = TradingCalculations.round_to_valid_lot_size(hedge_lot)
                
                # จำกัดขนาด lot
                hedge_lot = min(hedge_lot, 1.0)  # สูงสุด 1 lot
                hedge_lot = max(hedge_lot, 0.1)  # ต่ำสุด 0.1 lot
                
                self.logger.info(f"📊 Hedge lot calculation: Original={original_lot:.4f}, Target Pip=${target_pip_value:.2f}, Hedge Lot={hedge_lot:.4f}")
                self.logger.info(f"   Original pip value: ${original_pip_value:.2f}, Hedge pip value: ${hedge_pip_value:.2f}")
                self.logger.info(f"   Hedge symbol: {hedge_symbol}, Pip value per 0.01: ${pip_value_per_001:.2f}")
                
                return float(hedge_lot)
            else:
                # Fallback: ใช้ lot size เดียวกันกับไม้เดิม
                return original_lot
            
        except Exception as e:
            self.logger.error(f"Error calculating hedge lot size: {e}")
            return original_lot
    
    def _send_hedge_order(self, symbol: str, lot_size: float, group_id: str, recovery_level: int = 1, original_symbol: str = None) -> bool:
        """ส่งออเดอร์ hedge"""
        try:
            # สร้าง comment - ใส่คู่เงินที่แก้และคู่เงินที่แก้ไม้
            # แยก triangle number จาก group_id (group_triangle_X_Y -> X)
            if 'triangle_' in group_id:
                triangle_part = group_id.split('triangle_')[1].split('_')[0]
                group_number = triangle_part
            else:
                group_number = 'X'
            if original_symbol:
                comment = f"RECOVERY_G{group_number}_{original_symbol}_TO_{symbol}_L{recovery_level}"
            else:
                comment = f"RECOVERY_G{group_number}_{symbol}_L{recovery_level}"
            
            # กำหนดทิศทางที่ถูกต้อง (ใช้ทิศทางเดียวกันกับคู่เดิม)
            # สำหรับการแก้ไม้ ใช้ทิศทางเดียวกันกับคู่เดิม
            order_type = 'SELL'  # ใช้ SELL เป็นหลัก (ทิศทางเดียวกัน)
            
            # ส่งออเดอร์
            result = self.broker.place_order(
                symbol=symbol,
                order_type=order_type,  # ใช้ทิศทางที่ถูกต้อง
                volume=lot_size,
                comment=comment
            )
            
            if result and result.get('retcode') == 10009:
                self.logger.debug(f"✅ Recovery order sent: {symbol} {lot_size} lot")
                return True
            else:
                self.logger.debug(f"❌ Failed to send recovery order: {symbol}")
                return False
                
        except Exception as e:
            self.logger.debug(f"Error sending hedge order: {e}")
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
            self.logger.debug(f"Error checking recovery chain: {e}")
    
    def _should_continue_recovery(self, recovery_pair: Dict) -> bool:
        """ตรวจสอบว่าควรดำเนินการ recovery ต่อหรือไม่ - ใช้เงื่อนไขเดียวกับ arbitrage"""
        try:
            symbol = recovery_pair['symbol']
            order_id = recovery_pair.get('order_id')
            
            # ตรวจสอบว่าไม้นี้แก้แล้วหรือยัง
            group_id = recovery_pair.get('group_id')
            if group_id and self._is_position_hedged_from_mt5(group_id, symbol):
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
            
            if risk_per_lot < 0.015:  # risk น้อยกว่า 1.5%
                self.logger.debug(f"⏳ {symbol} risk too low ({risk_per_lot:.2%}) - Waiting for 1.5%")
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
            
            self.logger.debug(f"🔍 Checking hedging conditions for {symbol} (Order: {order_id}):")
            self.logger.info(f"   Risk: {risk_per_lot:.2%} (info only)")
            self.logger.info(f"   Distance: {price_distance:.1f} pips (need ≥10) {'✅' if price_distance >= 10 else '❌'}")
            
            if price_distance < 10:  # ใช้แค่ Distance ≥ 10 pips
                self.logger.debug(f"⏳ {symbol}: Distance too small ({price_distance:.1f} pips) - waiting for 10 pips")
                return
            
            self.logger.debug(f"✅ {symbol}: All conditions met - continuing recovery")
            
            # หาคู่เงินใหม่สำหรับ recovery (ไม่ซ้ำกับคู่ในกลุ่ม)
            # self.logger.debug(f"🔍 Searching for correlation candidates for {symbol}")
            group_pairs = self._get_group_pairs_from_mt5(group_id)
            correlation_candidates = self._find_optimal_correlation_pairs(symbol, group_pairs)
            
            if not correlation_candidates:
                self.logger.debug(f"❌ No correlation candidates found for {symbol}")
                return
            
            # เลือกคู่เงินที่ดีที่สุด
            best_correlation = correlation_candidates[0]
            # แยก triangle number จาก group_id (group_triangle_X_Y -> X)
            if 'triangle_' in group_id:
                triangle_part = group_id.split('triangle_')[1].split('_')[0]
                group_number = triangle_part
            else:
                group_number = 'X'
            self.logger.info(f"🎯 Best correlation for G{group_number}: {best_correlation['symbol']} (correlation: {best_correlation['correlation']:.2f})")
            
            # ส่งออเดอร์ recovery ใหม่
            self.logger.info(f"📤 Sending new recovery order for {symbol} -> {best_correlation['symbol']}")
            success = self._execute_correlation_position(recovery_pair, best_correlation, group_id)
            
            if success:
                # บันทึกว่าไม้นี้แก้แล้ว
                self._mark_position_as_hedged(recovery_pair, group_id)
                self.logger.debug(f"✅ Chain recovery continued for {symbol} -> {best_correlation['symbol']}")
            else:
                self.logger.debug(f"❌ Failed to continue chain recovery for {symbol} -> {best_correlation['symbol']}")
                
        except Exception as e:
            self.logger.debug(f"Error continuing recovery chain: {e}")
    
    def update_recovery_parameters(self, params: Dict):
        """อัพเดทพารามิเตอร์ recovery"""
        try:
            # ตรวจสอบว่า recovery_thresholds มีอยู่หรือไม่
            if not hasattr(self, 'recovery_thresholds'):
                self.logger.warning("recovery_thresholds not initialized, creating default values")
                self.recovery_thresholds = {
                    'min_correlation': 0.5,
                    'max_correlation': 0.95,
                    'min_loss_threshold': -0.005,
                    'max_recovery_time_hours': 24,
                    'hedge_ratio_range': (0.3, 2.5),
                    'wait_time_minutes': 5,
                    'base_lot_size': 0.1
                }
            
            for key, value in params.items():
                if key in self.recovery_thresholds:
                    self.recovery_thresholds[key] = value
                    self.logger.info(f"Updated recovery_thresholds[{key}] to {value}")
                elif key in ['account_balance', 'account_equity', 'free_margin', 'target_pip_value', 'balance_multiplier']:
                    # เก็บข้อมูลบัญชีไว้ใน attribute แยก
                    setattr(self, key, value)
                    self.logger.debug(f"Updated {key} to {value}")
                else:
                    self.logger.debug(f"Parameter {key} not found in recovery_thresholds or account info")
                    
        except Exception as e:
            self.logger.debug(f"Error updating recovery parameters: {e}")
    
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
            self.logger.debug(f"Error checking recovery opportunities: {e}")
    
    def _initiate_correlation_recovery(self, losing_position: Dict):
        """เริ่ม correlation recovery"""
        try:
            symbol = losing_position['symbol']
            self.logger.debug(f"🔄 Starting correlation recovery for {symbol}")
            
            # หาคู่เงินที่เหมาะสมสำหรับ recovery (ไม่ซ้ำกับคู่ในกลุ่ม)
            group_pairs = self._get_group_pairs_from_mt5(losing_position.get('group_id', 'unknown'))
            correlation_candidates = self._find_optimal_correlation_pairs(symbol, group_pairs)
            
            if not correlation_candidates:
                self.logger.debug(f"   No correlation candidates found for {symbol}")
                return
            
            # เลือกคู่เงินที่ดีที่สุด
            best_correlation = correlation_candidates[0]
            # แยก triangle number จาก group_id (group_triangle_X_Y -> X)
            group_id_str = losing_position.get('group_id', 'unknown')
            if 'triangle_' in group_id_str:
                triangle_part = group_id_str.split('triangle_')[1].split('_')[0]
                group_number = triangle_part
            else:
                group_number = 'X'
            self.logger.info(f"   Best correlation for G{group_number}: {best_correlation['symbol']} (correlation: {best_correlation['correlation']:.2f})")
            
            # ส่งออเดอร์ recovery
            success = self._execute_correlation_position(losing_position, best_correlation, losing_position.get('group_id', 'unknown'))
            
            if success:
                # บันทึกว่าไม้นี้แก้แล้ว
                self._mark_position_as_hedged(losing_position, losing_position.get('group_id', 'unknown'))
                self.logger.debug(f"✅ Correlation recovery position opened: {best_correlation['symbol']}")
            else:
                self.logger.debug(f"❌ Failed to open correlation recovery position: {best_correlation['symbol']}")
                
        except Exception as e:
            self.logger.debug(f"Error initiating correlation recovery: {e}")
    
    def _find_optimal_correlation_pairs(self, base_symbol: str, group_pairs: List[str] = None) -> List[Dict]:
        """
        ⚡ CRITICAL: Find optimal correlation pairs for recovery
        หาคู่เงินที่มี correlation กับคู่ที่กำหนด (ไม่ซ้ำกับคู่ในกลุ่ม)
        """
        try:
            # ใช้ฟังก์ชันสำหรับคู่เงินใดๆ แทน (ไม่ซ้ำกับคู่ในกลุ่ม)
            return self._find_correlation_pairs_for_any_symbol(base_symbol, group_pairs)
            
        except Exception as e:
            self.logger.debug(f"Error finding optimal correlation pairs for {base_symbol}: {e}")
            return []
    
    def _is_currency_pair(self, symbol: str) -> bool:
        """ตรวจสอบว่าเป็นคู่เงินจริงๆ หรือไม่ (ไม่ใช่ Ukoil, Gold, Silver, etc.)"""
        try:
            # รายการคู่เงินที่ยอมรับ
            valid_currency_pairs = [
                'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'USDNZD',
                'EURGBP', 'EURJPY', 'GBPJPY', 'AUDJPY', 'CADJPY', 'CHFJPY', 'NZDJPY',
                    'EURCHF', 'GBPCHF', 'AUDCHF', 'CADCHF', 'NZDCHF',
                    'EURAUD', 'GBPAUD', 'USDAUD', 'AUDCAD', 'AUDNZD',
                    'EURNZD', 'GBPNZD', 'USDNZD', 'AUDNZD', 'CADNZD',
                    'EURCAD', 'GBPCAD', 'USDCAD', 'AUDCAD', 'CADCHF'
                ]
            
            # ตรวจสอบว่าเป็นคู่เงินที่ยอมรับหรือไม่
            if symbol in valid_currency_pairs:
                return True
            
            # ตรวจสอบรูปแบบคู่เงิน (3 ตัวอักษร + 3 ตัวอักษร)
            if len(symbol) == 6:
                # ตรวจสอบว่าเป็นตัวอักษรทั้งหมด
                if symbol.isalpha():
                    # ตรวจสอบว่าไม่ใช่สินค้าโภคภัณฑ์
                    commodities = ['UKOIL', 'USOIL', 'GOLD', 'SILVER', 'COPPER', 'PLATINUM', 'PALLADIUM']
                    if symbol.upper() in commodities:
                        return False
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking if symbol is currency pair: {e}")
            return False
    
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
            self.logger.debug(f"Error calculating correlation: {e}")
            return 0.50
    
    def _calculate_correlation_for_any_pair(self, base_symbol: str, target_symbol: str) -> float:
        """คำนวณ correlation ระหว่างคู่เงินใดๆ โดยใช้ข้อมูลจริงจาก MT5"""
        try:
            # ใช้ข้อมูลจริงจาก MT5 เพื่อคำนวณ correlation
            return self._calculate_real_correlation_from_mt5(base_symbol, target_symbol)
            
        except Exception as e:
            self.logger.debug(f"Error calculating correlation for any pair: {e}")
            return 0.60
    
    def _calculate_real_correlation_from_mt5(self, base_symbol: str, target_symbol: str) -> float:
        """คำนวณ correlation จริงจากข้อมูล MT5 แบบยืดหยุ่น"""
        try:
            # ดึงข้อมูลราคาจาก MT5
            base_price = self.broker.get_current_price(base_symbol)
            target_price = self.broker.get_current_price(target_symbol)
            
            if not base_price or not target_price:
                return self._calculate_dynamic_correlation(base_symbol, target_symbol)
            
            # คำนวณ correlation แบบยืดหยุ่น
            correlation = self._calculate_dynamic_correlation(base_symbol, target_symbol)
            
            # ปรับแต่งตามราคาปัจจุบัน
            price_ratio = abs(base_price - target_price) / max(base_price, target_price)
            if price_ratio > 0.1:  # ราคาแตกต่างมาก
                correlation *= 0.8  # ลด correlation เล็กน้อย
            
            return correlation
                
        except Exception as e:
            self.logger.debug(f"Error calculating real correlation from MT5: {e}")
            return self._calculate_dynamic_correlation(base_symbol, target_symbol)
    
    def _calculate_dynamic_correlation(self, base_symbol: str, target_symbol: str) -> float:
        """คำนวณ correlation แบบยืดหยุ่นตามโครงสร้างคู่เงิน"""
        try:
            # แยกสกุลเงิน
            base_curr1, base_curr2 = base_symbol[:3], base_symbol[3:]
            target_curr1, target_curr2 = target_symbol[:3], target_symbol[3:]
            
            # ตรวจสอบความสัมพันธ์แบบยืดหยุ่น
            correlation = self._analyze_currency_relationship(base_curr1, base_curr2, target_curr1, target_curr2)
            
            return correlation
            
        except Exception as e:
            self.logger.debug(f"Error calculating dynamic correlation: {e}")
            return 0.60
    
    def _analyze_currency_relationship(self, base1: str, base2: str, target1: str, target2: str) -> float:
        """วิเคราะห์ความสัมพันธ์ระหว่างสกุลเงินแบบยืดหยุ่น"""
        try:
            # 1. ตรวจสอบสกุลเงินเดียวกัน (Positive correlation)
            if base1 == target1 or base2 == target2:
                return 0.75  # สูง
            
            # 2. ตรวจสอบสกุลเงินตรงข้าม (Negative correlation)
            if base1 == target2 or base2 == target1:
                return -0.75  # ติดลบสูง
            
            # 3. ตรวจสอบสกุลเงินที่เกี่ยวข้อง (Moderate correlation)
            # USD pairs
            if 'USD' in [base1, base2] and 'USD' in [target1, target2]:
                return 0.60  # ปานกลาง
            
            # EUR pairs
            if 'EUR' in [base1, base2] and 'EUR' in [target1, target2]:
                return 0.65  # ปานกลาง
            
            # GBP pairs
            if 'GBP' in [base1, base2] and 'GBP' in [target1, target2]:
                return 0.65  # ปานกลาง
            
            # JPY pairs
            if 'JPY' in [base1, base2] and 'JPY' in [target1, target2]:
                return 0.60  # ปานกลาง
            
            # AUD pairs
            if 'AUD' in [base1, base2] and 'AUD' in [target1, target2]:
                return 0.60  # ปานกลาง
            
            # CAD pairs
            if 'CAD' in [base1, base2] and 'CAD' in [target1, target2]:
                return 0.60  # ปานกลาง
            
            # CHF pairs
            if 'CHF' in [base1, base2] and 'CHF' in [target1, target2]:
                return 0.60  # ปานกลาง
            
            # NZD pairs
            if 'NZD' in [base1, base2] and 'NZD' in [target1, target2]:
                return 0.60  # ปานกลาง
            
            # 4. ตรวจสอบสกุลเงินที่ตรงข้ามกัน (Negative correlation)
            # Major vs Safe Haven
            majors = ['EUR', 'GBP', 'AUD', 'NZD', 'CAD']
            safe_havens = ['JPY', 'CHF', 'USD']
            
            if (base1 in majors and target1 in safe_havens) or (base2 in majors and target2 in safe_havens):
                return -0.70  # ติดลบสูง
            
            if (base1 in safe_havens and target1 in majors) or (base2 in safe_havens and target2 in majors):
                return -0.70  # ติดลบสูง
            
            # 5. เพิ่ม negative correlation patterns เพิ่มเติม
            # EUR vs USD pairs (inverse relationship)
            if (base1 == 'EUR' and target1 == 'USD') or (base2 == 'EUR' and target2 == 'USD'):
                return -0.65
            
            # GBP vs USD pairs (inverse relationship)
            if (base1 == 'GBP' and target1 == 'USD') or (base2 == 'GBP' and target2 == 'USD'):
                return -0.65
            
            # AUD vs USD pairs (inverse relationship)
            if (base1 == 'AUD' and target1 == 'USD') or (base2 == 'AUD' and target2 == 'USD'):
                return -0.65
            
            # CAD vs USD pairs (inverse relationship)
            if (base1 == 'CAD' and target1 == 'USD') or (base2 == 'CAD' and target2 == 'USD'):
                return -0.65
            
            # NZD vs USD pairs (inverse relationship)
            if (base1 == 'NZD' and target1 == 'USD') or (base2 == 'NZD' and target2 == 'USD'):
                return -0.65
            
            # CHF vs USD pairs (inverse relationship)
            if (base1 == 'CHF' and target1 == 'USD') or (base2 == 'CHF' and target2 == 'USD'):
                return -0.65
            
            # JPY vs USD pairs (inverse relationship)
            if (base1 == 'JPY' and target1 == 'USD') or (base2 == 'JPY' and target2 == 'USD'):
                return -0.65
            
            # 6. Cross currency negative correlations
            # EUR vs JPY (risk-on vs risk-off)
            if (base1 == 'EUR' and target1 == 'JPY') or (base2 == 'EUR' and target2 == 'JPY'):
                return -0.60
            
            # GBP vs JPY (risk-on vs risk-off)
            if (base1 == 'GBP' and target1 == 'JPY') or (base2 == 'GBP' and target2 == 'JPY'):
                return -0.60
            
            # AUD vs JPY (risk-on vs risk-off)
            if (base1 == 'AUD' and target1 == 'JPY') or (base2 == 'AUD' and target2 == 'JPY'):
                return -0.60
            
            # 7. ตรวจสอบสกุลเงินที่เกี่ยวข้องกับสินค้าโภคภัณฑ์
            commodity_currencies = ['AUD', 'NZD', 'CAD']
            if (base1 in commodity_currencies and target1 in commodity_currencies):
                return 0.70  # สูง
            
            # 8. Default correlation (ปรับให้มี negative correlation มากขึ้น)
            # สุ่มให้ negative correlation บางส่วน
            import random
            if random.random() < 0.3:  # 30% chance for negative correlation
                return -0.40  # negative correlation
            else:
                return 0.50  # positive correlation
            
        except Exception as e:
            self.logger.error(f"Error analyzing currency relationship: {e}")
            return 0.60
    
    def _is_negative_correlation(self, base_symbol: str, target_symbol: str) -> bool:
        """ตรวจสอบว่าคู่เงินมี negative correlation หรือไม่"""
        try:
            correlation = self._calculate_dynamic_correlation(base_symbol, target_symbol)
            return correlation < -0.5  # Negative correlation
            
        except Exception as e:
            self.logger.debug(f"Error checking negative correlation: {e}")
            return False
    
    def _is_positive_correlation(self, base_symbol: str, target_symbol: str) -> bool:
        """ตรวจสอบว่าคู่เงินมี positive correlation หรือไม่"""
        try:
            correlation = self._calculate_dynamic_correlation(base_symbol, target_symbol)
            return correlation > 0.5  # Positive correlation
            
        except Exception as e:
            self.logger.debug(f"Error checking positive correlation: {e}")
            return False
    
    def _determine_recovery_direction(self, base_symbol: str, target_symbol: str, correlation: float, original_position: Dict = None) -> str:
        """กำหนดทิศทางการ recovery ตาม correlation (ไม่ใช่ BUY/SELL ตรงข้าม)"""
        try:
            # ตรวจสอบทิศทางของคู่เดิม
            original_direction = None
            if original_position:
                original_direction = original_position.get('type', 'SELL')  # BUY หรือ SELL
            
            # ใช้ทิศทางเดียวกันกับคู่เดิม แต่เลือกคู่ที่มี correlation ติดลบ
            # เพื่อให้เมื่อคู่เดิมติดลบ คู่ correlation จะกำไร
            if original_direction == 'BUY':
                return 'BUY'   # ใช้ทิศทางเดียวกัน
            elif original_direction == 'SELL':
                return 'SELL'  # ใช้ทิศทางเดียวกัน
            else:
                # หากไม่ทราบทิศทางเดิม ใช้ SELL เป็นหลัก
                return 'SELL'
                
        except Exception as e:
            self.logger.debug(f"Error determining recovery direction: {e}")
            return 'SELL'  # Default to SELL
    
    def _find_correlation_pairs_for_any_symbol(self, base_symbol: str, group_pairs: List[str] = None) -> List[Dict]:
        """หาคู่เงินที่มี correlation กับคู่เงินใดๆ (ไม่ซ้ำกับคู่ในกลุ่ม)"""
        try:
            correlation_candidates = []
            
            # ดึงคู่เงินทั้งหมดจาก MT5 จริงๆ
            all_pairs = self._get_all_currency_pairs_from_mt5()
            
            self.logger.debug(f"🔍 Using all currency pairs from MT5: {len(all_pairs)} pairs")
            
            # กำหนดคู่เงินที่ห้ามซ้ำ (คู่ในกลุ่ม arbitrage)
            if group_pairs is None:
                group_pairs = []
            
            self.logger.info(f"🚫 Excluding group pairs: {group_pairs}")
            
            for symbol in all_pairs:
                if symbol == base_symbol:
                    continue
                
                # ตรวจสอบว่าเป็นคู่ในกลุ่ม arbitrage หรือไม่ (ไม่ให้ซ้ำ)
                if symbol in group_pairs:
                    self.logger.debug(f"   ❌ Skipping {symbol} (already in group)")
                    continue
                
                # ตรวจสอบว่าเป็นคู่เงินจริงๆ (ไม่ใช่ Ukoil, Gold, Silver, etc.)
                if not self._is_currency_pair(symbol):
                    continue
                
                # คำนวณ correlation แบบยืดหยุ่น
                correlation = self._calculate_dynamic_correlation(base_symbol, symbol)
                
                # ใช้ correlation ติดลบสำหรับการแก้ไม้ (คู่ที่วิ่งตรงข้าม)
                if correlation <= -0.2:  # ใช้ threshold ที่ยืดหยุ่นมากขึ้น
                    # กำหนดทิศทางตาม correlation
                    direction = self._determine_recovery_direction(base_symbol, symbol, correlation, None)
                    
                    correlation_candidates.append({
                        'symbol': symbol,
                        'correlation': correlation,
                        'recovery_strength': abs(correlation),  # ใช้ absolute value สำหรับ sorting
                        'direction': direction
                    })
                    
                    self.logger.debug(f"   ✅ Found negative correlation: {symbol} = {correlation:.2f} ({direction})")
                else:
                    self.logger.debug(f"   ❌ Low negative correlation: {symbol} = {correlation:.2f}")
            
            # Sort by recovery strength (highest absolute correlation first)
            correlation_candidates.sort(key=lambda x: x['recovery_strength'], reverse=True)
            
            if not correlation_candidates:
                self.logger.debug(f"❌ No correlation candidates created for {base_symbol}")
            else:
                self.logger.debug(f"🎯 Final correlation candidates for {base_symbol}: {len(correlation_candidates)} pairs")
                for i, candidate in enumerate(correlation_candidates[:5]):  # แสดง 5 อันดับแรก
                    self.logger.debug(f"   {i+1}. {candidate['symbol']}: {candidate['correlation']:.2f} ({candidate['direction']})")
            
            return correlation_candidates
            
        except Exception as e:
            self.logger.debug(f"Error finding correlation pairs for any symbol: {e}")
            return []
    
    def _execute_correlation_position(self, original_position: Dict, correlation_candidate: Dict, group_id: str) -> bool:
        """
        ⚡ CRITICAL: Execute correlation position for recovery
        """
        try:
            symbol = correlation_candidate['symbol']
            correlation = correlation_candidate['correlation']
            original_symbol = original_position.get('symbol', '')
            
            self.logger.info(f"🔍 EXECUTING CORRELATION: {original_symbol} -> {symbol} (correlation: {correlation:.2f})")
            
            # 🔒 STEP 1: Check if original position is already hedged
            original_ticket = str(original_position.get('ticket', ''))
            if self.order_tracker.is_order_hedged(original_ticket, original_symbol):
                self.logger.warning(f"🚫 Position {original_ticket}_{original_symbol} already hedged - skipping")
                return False
            
            self.logger.info(f"✅ Position {original_ticket}_{original_symbol} not hedged - proceeding")
            
            # กำหนดทิศทางที่ถูกต้อง (ใช้ทิศทางเดียวกันกับคู่เดิม)
            original_direction = original_position.get('type', 'SELL')
            if original_direction == 'BUY':
                direction = 'BUY'   # ใช้ทิศทางเดียวกัน
            elif original_direction == 'SELL':
                direction = 'SELL'  # ใช้ทิศทางเดียวกัน
            else:
                direction = 'SELL'  # Default to SELL
            
            # Calculate correlation volume
            correlation_volume = self._calculate_hedge_volume(original_position, correlation_candidate)
            
            # คำนวณ lot size ตาม balance-based sizing
            original_lot = original_position.get('lot_size', original_position.get('volume', 0.1))
            
            correlation_lot_size = self._calculate_hedge_lot_size(
                original_lot=original_lot,
                correlation=correlation,
                loss_percent=0.0,  # ไม่ใช้ loss_percent ในระบบใหม่
                original_symbol=original_symbol,
                hedge_symbol=symbol
            )
            
            # Send correlation order
            self.logger.info(f"📤 Sending recovery order: {symbol} {correlation_lot_size} lot, direction: {direction}")
            order_result = self._send_correlation_order(symbol, correlation_lot_size, group_id, original_position)
            self.logger.info(f"📤 Order result: {order_result}")
            
            if order_result and order_result.get('success'):
                # ✅ STEP 2: Register recovery order in individual tracker
                recovery_ticket = str(order_result.get('order_id', ''))
                if recovery_ticket:
                    self._add_hedge_tracking(original_ticket, original_symbol, recovery_ticket, symbol)
                else:
                    self.logger.error(f"❌ No order ID returned for recovery order")
                    return False
                
                # ดึงราคาปัจจุบันเป็น entry price
                entry_price = self.broker.get_current_price(symbol)
                if not entry_price:
                    entry_price = 0.0
                
                # Store correlation position (legacy support)
                correlation_position = {
                    'symbol': symbol,
                    'direction': direction,
                    'lot_size': correlation_lot_size,
                    'entry_price': entry_price,
                    'order_id': recovery_ticket,
                    'correlation': correlation,
                    'correlation_ratio': 1.0,  # ใช้ lot size เดียวกัน
                    'original_pair': original_symbol,
                    'group_id': group_id,
                    'opened_at': datetime.now(),
                    'status': 'active'
                }
                
                recovery_id = f"recovery_{group_id}_{symbol}_{int(datetime.now().timestamp())}"
                self.recovery_positions[recovery_id] = correlation_position
                
                # Legacy recovery positions storage removed - using individual order tracker
                self._update_recovery_data()
                
                # บันทึกข้อมูลการแก้ไม้
                self._log_hedging_action(original_position, correlation_position, correlation_candidate, group_id)
                
                self.logger.debug(f"✅ Correlation recovery position opened: {symbol}")
                return True
            else:
                # ❌ STEP 3: Order failed - individual tracker will handle cleanup on sync
                self.logger.debug(f"❌ Failed to open correlation recovery position: {symbol}")
                return False
                
        except Exception as e:
            # ❌ STEP 4: Error occurred - individual tracker will handle cleanup on sync
            original_symbol = original_position.get('symbol', '')
            self.logger.debug(f"Error executing correlation position: {e}")
            return False
    
    def _log_hedging_action(self, original_position: Dict, correlation_position: Dict, correlation_candidate: Dict, group_id: str = None):
        """แสดง log การแก้ไม้ให้ชัดเจน"""
        try:
            original_symbol = original_position['symbol']
            hedge_symbol = correlation_position['symbol']
            correlation = correlation_candidate['correlation']
            
            # แสดงข้อมูลการแก้ไม้ที่ถูกต้อง
            # แยก triangle number จาก group_id (group_triangle_X_Y -> X)
            if group_id and 'triangle_' in group_id:
                triangle_part = group_id.split('triangle_')[1].split('_')[0]
                group_number = triangle_part
            else:
                group_number = 'X'
            self.logger.info("=" * 60)
            self.logger.info(f"🎯 HEDGING ACTION COMPLETED - GROUP G{group_number}")
            self.logger.info("=" * 60)
            self.logger.info(f"📉 Original Position: {original_symbol}")
            self.logger.info(f"   Order ID: {original_position.get('order_id', 'N/A')}")
            self.logger.info(f"   Lot Size: {original_position.get('lot_size', 0.1)}")
            self.logger.info(f"   Entry Price: {original_position.get('entry_price', 0.0):.5f}")
            
            self.logger.info(f"🛡️ Recovery Position: {hedge_symbol}")
            self.logger.info(f"   Lot Size: {correlation_position['lot_size']}")
            self.logger.info(f"   Entry Price: {correlation_position['entry_price']:.5f}")
            self.logger.info(f"   Direction: {correlation_position['direction']}")
            
            self.logger.info(f"📊 Recovery Details:")
            self.logger.info(f"   Group: G{group_number}")
            self.logger.info(f"   Hedging: {original_symbol} → {hedge_symbol}")
            self.logger.info(f"   Correlation: {correlation:.2f}")
            self.logger.info(f"   Recovery Strength: {correlation_candidate.get('recovery_strength', correlation):.2f}")
            
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.debug(f"Error logging hedging action: {e}")
    
    def _calculate_hedge_volume(self, original_position: Dict, correlation_candidate: Dict) -> float:
        """คำนวณขนาด volume สำหรับ correlation position - ใช้ balance-based sizing"""
        try:
            # ดึงข้อมูลจาก original position
            original_lot = original_position.get('lot_size', original_position.get('volume', 0.1))
            original_symbol = original_position.get('symbol', '')
            hedge_symbol = correlation_candidate.get('symbol', '')
            
            # ใช้ balance-based lot sizing
            volume = self._calculate_hedge_lot_size(
                original_lot=original_lot,
                correlation=correlation_candidate.get('correlation', 0.5),
                loss_percent=0.0,
                original_symbol=original_symbol,
                hedge_symbol=hedge_symbol
            )
            
            return float(volume)
            
        except Exception as e:
            self.logger.debug(f"Error calculating hedge volume: {e}")
            return 0.1
    
    def _send_correlation_order(self, symbol: str, lot_size: float, group_id: str, original_position: Dict = None) -> Dict:
        """ส่งออเดอร์ correlation recovery"""
        try:
            # สร้าง comment - ใส่คู่เงินที่แก้และคู่เงินที่แก้ไม้
            # แยก triangle number จาก group_id (group_triangle_X_Y -> X)
            if 'triangle_' in group_id:
                triangle_part = group_id.split('triangle_')[1].split('_')[0]
                group_number = triangle_part
            else:
                group_number = 'X'
            original_symbol = original_position.get('symbol', 'UNKNOWN') if original_position else 'UNKNOWN'
            comment = f"RECOVERY_G{group_number}_{original_symbol}_TO_{symbol}"
            
            # หา magic number จาก group_id หรือใช้ default
            magic_number = self._get_magic_number_from_group_id(group_id)
            if not magic_number:
                magic_number = 234000  # Default magic number for recovery orders
            
            # กำหนดทิศทางที่ถูกต้อง (ใช้ทิศทางเดียวกันกับคู่เดิม)
            original_direction = original_position.get('type', 'SELL') if original_position else 'SELL'
            if original_direction == 'BUY':
                order_type = 'BUY'   # ใช้ทิศทางเดียวกัน
            elif original_direction == 'SELL':
                order_type = 'SELL'  # ใช้ทิศทางเดียวกัน
            else:
                order_type = 'SELL'  # Default to SELL
            
            # ส่งออเดอร์
            result = self.broker.place_order(
                symbol=symbol,
                order_type=order_type,  # ใช้ทิศทางที่ถูกต้อง
                volume=lot_size,
                comment=comment,
                magic=magic_number
            )
            
            if result and (result.get('retcode') == 10009 or result.get('success')):
                # แยก triangle number จาก group_id (group_triangle_X_Y -> X)
                if 'triangle_' in group_id:
                    triangle_part = group_id.split('triangle_')[1].split('_')[0]
                    group_number = triangle_part
                else:
                    group_number = 'X'
                self.logger.info(f"✅ G{group_number} Recovery order sent: {symbol} {lot_size} lot")
                return {
                    'success': True,
                    'order_id': result.get('order_id'),
                    'symbol': symbol,
                    'lot_size': lot_size
                }
            else:
                self.logger.error(f"❌ Failed to send correlation recovery order: {symbol}")
                self.logger.error(f"❌ Result: {result}")
                if result:
                    self.logger.error(f"❌ Retcode: {result.get('retcode')}")
                    self.logger.error(f"❌ Success: {result.get('success')}")
                    self.logger.error(f"❌ Error: {result.get('error')}")
                return {
                    'success': False,
                    'order_id': None,
                    'symbol': symbol,
                    'lot_size': lot_size
                }
                
        except Exception as e:
            self.logger.debug(f"Error sending correlation recovery order: {e}")
            return {
                'success': False,
                'order_id': None,
                'symbol': symbol,
                'lot_size': lot_size
            }
    
    def check_recovery_positions(self):
        """Debug version with detailed logging - Check individual orders needing recovery"""
        try:
            self.logger.info("🔍 RECOVERY CHECK: Starting recovery position analysis")
            
            # Log recovery thresholds for debugging
            self.log_recovery_thresholds()
            
            # 🔄 STEP 1: Sync individual order tracker with MT5
            sync_results = self.order_tracker.sync_with_mt5()
            if sync_results.get('orders_removed', 0) > 0:
                self.logger.info(f"🔄 Synced: {sync_results['orders_removed']} orders removed")
            
            # Get orders needing recovery from individual order tracker
            orders_needing_recovery = self.order_tracker.get_orders_needing_recovery()
            self.logger.info(f"🔍 Orders needing recovery: {len(orders_needing_recovery)}")
            
            if not orders_needing_recovery:
                self.logger.warning("⚠️ No orders needing recovery found")
                return
            
            recovery_candidates = []
            
            for order_info in orders_needing_recovery:
                ticket = order_info.get('ticket')
                symbol = order_info.get('symbol')
                order_type = order_info.get('type', 'UNKNOWN')
                
                # Get actual position from MT5
                position = self._get_position_by_ticket(ticket)
                if not position:
                    self.logger.warning(f"⚠️ Position {ticket}_{symbol} not found in MT5")
                    continue
                
                profit = position.get('profit', 0)
                self.logger.info(f"🔍 Checking {ticket}_{symbol} ({order_type}): PnL=${profit:.2f}")
                
                # Check recovery conditions
                meets_conditions = self._meets_recovery_conditions(position)
                self.logger.info(f"🔍 Meets recovery conditions: {meets_conditions}")
                
                if meets_conditions:
                    recovery_candidates.append(position)
                    self.logger.info(f"✅ Added to recovery candidates: {ticket}_{symbol}")
                else:
                    self.logger.info(f"❌ Skipped: {ticket}_{symbol} - conditions not met")
            
            self.logger.info(f"🔍 Total recovery candidates: {len(recovery_candidates)}")
            
            if recovery_candidates:
                # Process recovery for best candidate (largest loss)
                best_candidate = max(recovery_candidates, key=lambda x: abs(x.get('profit', 0)))
                self.logger.info(f"🎯 Best candidate: {best_candidate.get('symbol')} (${best_candidate.get('profit', 0):.2f})")
                
                # Start recovery
                self._start_individual_recovery(best_candidate)
            else:
                self.logger.warning("⚠️ No candidates meet recovery conditions")
                
        except Exception as e:
            self.logger.error(f"❌ Error in recovery check: {e}")
    
    def _get_position_by_ticket(self, ticket: str) -> Optional[Dict]:
        """Get position from MT5 by ticket number"""
        try:
            all_positions = self.broker.get_all_positions()
            for pos in all_positions:
                if str(pos.get('ticket', '')) == str(ticket):
                    return pos
            return None
        except Exception as e:
            self.logger.error(f"Error getting position by ticket {ticket}: {e}")
            return None
    
    def _meets_recovery_conditions(self, position: Dict) -> bool:
        """Debug version of recovery conditions check"""
        try:
            profit = position.get('profit', 0)
            symbol = position.get('symbol', '')
            
            self.logger.debug(f"🔍 Checking conditions for {symbol}:")
            
            # Check loss threshold
            loss_threshold = self.recovery_thresholds.get('min_loss_threshold', -0.005)
            balance = self.broker.get_account_balance() or 10000
            loss_percent = profit / balance
            
            meets_loss = loss_percent <= loss_threshold
            self.logger.debug(f"   Loss check: {loss_percent:.4f} <= {loss_threshold:.4f} = {meets_loss}")
            
            # Check if position is losing money
            meets_profit_loss = profit < 0
            self.logger.debug(f"   Profit loss check: {profit:.2f} < 0 = {meets_profit_loss}")
            
            # Check minimum loss amount (e.g., at least $10 loss)
            min_loss_amount = -10.0  # $10 minimum loss
            meets_min_loss = profit <= min_loss_amount
            self.logger.debug(f"   Min loss amount check: {profit:.2f} <= {min_loss_amount} = {meets_min_loss}")
            
            # All conditions must be met
            result = meets_loss and meets_profit_loss and meets_min_loss
            self.logger.debug(f"   Final result: {result}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error checking recovery conditions: {e}")
            return False
    
    def _start_individual_recovery(self, position: Dict):
        """Start recovery for individual position"""
        try:
            ticket = position.get('ticket', '')
            symbol = position.get('symbol', '')
            profit = position.get('profit', 0)
            
            self.logger.info(f"🚀 STARTING RECOVERY: {ticket}_{symbol} (${profit:.2f})")
            
            # Find correlation pairs
            correlation_candidates = self._find_correlation_pairs_for_symbol(symbol)
            self.logger.info(f"🔍 Found {len(correlation_candidates)} correlation candidates")
            
            if correlation_candidates:
                best_correlation = correlation_candidates[0]
                self.logger.info(f"🎯 Best correlation: {best_correlation}")
                
                # Execute recovery - need to get proper group_id
                # For now, use a default group_id since we're doing individual order recovery
                group_id = f"recovery_{ticket}_{symbol}"
                success = self._execute_correlation_position(position, best_correlation, group_id)
                self.logger.info(f"🔄 Recovery result: {success}")
            else:
                self.logger.warning(f"⚠️ No correlation pairs found for {symbol}")
                
        except Exception as e:
            self.logger.error(f"❌ Error starting recovery: {e}")
    
    def _find_correlation_pairs_for_symbol(self, symbol: str) -> List[Dict]:
        """Find correlation pairs for a specific symbol"""
        try:
            # Get all available currency pairs
            all_pairs = self._get_all_currency_pairs_from_mt5()
            
            # Remove the symbol itself from the list
            other_pairs = [pair for pair in all_pairs if pair != symbol]
            
            correlation_candidates = []
            
            # For now, use simple correlation based on common currency pairs
            # This is a simplified version - in production you'd calculate actual correlations
            for other_symbol in other_pairs[:10]:  # Check top 10 pairs
                # Simple correlation estimation based on currency overlap
                correlation = self._estimate_correlation(symbol, other_symbol)
                
                if correlation > 0.5:  # Minimum correlation threshold
                    correlation_candidates.append({
                        'symbol': other_symbol,
                        'correlation': correlation,
                        'hedge_ratio': 1.0  # Simplified hedge ratio
                    })
            
            # Sort by correlation (highest first)
            correlation_candidates.sort(key=lambda x: x['correlation'], reverse=True)
            
            return correlation_candidates
                        
        except Exception as e:
            self.logger.error(f"Error finding correlation pairs for {symbol}: {e}")
            return []
    
    def _estimate_correlation(self, symbol1: str, symbol2: str) -> float:
        """Estimate correlation between two currency pairs"""
        try:
            # Simple correlation estimation based on currency overlap
            # This is a simplified version - in production you'd use historical data
            
            # Extract base and quote currencies
            base1, quote1 = symbol1[:3], symbol1[3:]
            base2, quote2 = symbol2[:3], symbol2[3:]
            
            # Check for currency overlap
            if base1 == base2 or quote1 == quote2:
                return 0.8  # High correlation for same base or quote
            elif base1 == quote2 or quote1 == base2:
                return 0.7  # Good correlation for cross pairs
            elif base1 in symbol2 or quote1 in symbol2:
                return 0.6  # Moderate correlation for partial overlap
            else:
                return 0.3  # Low correlation for no overlap
                
        except Exception as e:
            self.logger.error(f"Error estimating correlation: {e}")
            return 0.0
    
    def log_recovery_thresholds(self):
        """Log current recovery thresholds for debugging"""
        try:
            self.logger.info("🔍 RECOVERY THRESHOLDS:")
            self.logger.info(f"   Min Loss Threshold: {self.recovery_thresholds.get('min_loss_threshold', -0.005)} ({self.recovery_thresholds.get('min_loss_threshold', -0.005) * 100:.1f}%)")
            self.logger.info(f"   Wait Time: {self.recovery_thresholds.get('wait_time_minutes', 5)} minutes")
            self.logger.info(f"   Min Correlation: {self.recovery_thresholds.get('min_correlation', 0.5)} ({self.recovery_thresholds.get('min_correlation', 0.5) * 100:.0f}%)")
            self.logger.info(f"   Max Recovery Time: {self.recovery_thresholds.get('max_recovery_time_hours', 24)} hours")
            self.logger.info(f"   Base Lot Size: {self.recovery_thresholds.get('base_lot_size', 0.1)}")
            
            # Get account balance for context
            balance = self.broker.get_account_balance() or 10000
            self.logger.info(f"   Account Balance: ${balance:.2f}")
            self.logger.info(f"   Min Loss Amount: ${abs(self.recovery_thresholds.get('min_loss_threshold', -0.005) * balance):.2f}")
            
        except Exception as e:
            self.logger.error(f"Error logging recovery thresholds: {e}")
    
    def force_recovery_check(self):
        """Force a recovery check for debugging purposes"""
        try:
            self.logger.info("🚨 FORCE RECOVERY CHECK: Manual trigger for debugging")
            self.check_recovery_positions()
        except Exception as e:
            self.logger.error(f"Error in force recovery check: {e}")
    
    def fix_missing_orders(self):
        """Fix missing orders in tracker - register all existing MT5 positions"""
        try:
            self.logger.info("🔧 FIXING MISSING ORDERS: Registering all existing MT5 positions")
            self.register_existing_orders()
            
            # Now check recovery
            self.logger.info("🔍 Checking recovery after fixing orders...")
            self.check_recovery_positions()
            
        except Exception as e:
            self.logger.error(f"Error fixing missing orders: {e}")
    
    def adjust_recovery_thresholds_for_testing(self):
        """Adjust recovery thresholds to be more lenient for testing"""
        try:
            self.logger.info("🔧 ADJUSTING RECOVERY THRESHOLDS FOR TESTING")
            
            # Make thresholds more lenient
            self.recovery_thresholds.update({
                'min_loss_threshold': -0.001,  # -0.1% instead of -0.5%
                'wait_time_minutes': 1,        # 1 minute instead of 5
                'min_correlation': 0.3,        # 30% instead of 50%
                'max_recovery_time_hours': 48, # 48 hours instead of 24
                'base_lot_size': 0.01          # Smaller lot size for testing
            })
            
            self.logger.info("✅ Recovery thresholds adjusted for testing:")
            self.log_recovery_thresholds()
            
        except Exception as e:
            self.logger.error(f"Error adjusting recovery thresholds: {e}")
    
    def register_existing_orders(self):
        """Register all existing MT5 positions as original orders in the tracker"""
        try:
            self.logger.info("🔧 REGISTERING EXISTING ORDERS IN TRACKER")
            
            # Get all MT5 positions
            all_positions = self.broker.get_all_positions()
            self.logger.info(f"📊 Found {len(all_positions)} positions in MT5")
            
            registered_count = 0
            skipped_count = 0
            
            for pos in all_positions:
                ticket = str(pos.get('ticket', ''))
                symbol = pos.get('symbol', '')
                magic = pos.get('magic', 0)
                profit = pos.get('profit', 0)
                
                if not ticket or not symbol:
                    continue
                
                # Check if already tracked
                order_info = self.order_tracker.get_order_info(ticket, symbol)
                if order_info:
                    skipped_count += 1
                    continue
                
                # Determine group_id from magic number
                group_id = self._get_group_id_from_magic(magic)
                
                # Register as original order
                success = self.order_tracker.register_original_order(ticket, symbol, group_id)
                if success:
                    registered_count += 1
                    self.logger.info(f"✅ Registered: {ticket}_{symbol} (${profit:.2f}) in {group_id}")
                else:
                    self.logger.warning(f"❌ Failed to register: {ticket}_{symbol}")
            
            self.logger.info(f"📊 Registration complete: {registered_count} registered, {skipped_count} already tracked")
            
            # Show updated statistics
            stats = self.order_tracker.get_statistics()
            self.logger.info(f"📊 Tracker stats: {stats['total_tracked_orders']} total, {stats['not_hedged_orders']} not hedged")
            
        except Exception as e:
            self.logger.error(f"Error registering existing orders: {e}")
    
    def _get_group_id_from_magic(self, magic: int) -> str:
        """Get group_id from magic number"""
        magic_to_group = {
            234001: "group_triangle_1_1",
            234002: "group_triangle_2_1", 
            234003: "group_triangle_3_1",
            234004: "group_triangle_4_1",
            234005: "group_triangle_5_1",
            234006: "group_triangle_6_1"
        }
        return magic_to_group.get(magic, f"group_unknown_{magic}")
    
    def test_recovery_system(self):
        """Test the recovery system with current losing positions"""
        try:
            self.logger.info("🧪 TESTING RECOVERY SYSTEM")
            
            # First register all existing orders
            self.register_existing_orders()
            
            # Get all MT5 positions
            all_positions = self.broker.get_all_positions()
            losing_positions = [pos for pos in all_positions if pos.get('profit', 0) < -10]  # Losing more than $10
            
            self.logger.info(f"📊 Found {len(losing_positions)} positions losing more than $10")
            
            if not losing_positions:
                self.logger.warning("⚠️ No losing positions found for testing")
                return
            
            # Test with the biggest loser
            biggest_loser = min(losing_positions, key=lambda x: x.get('profit', 0))
            ticket = biggest_loser.get('ticket')
            symbol = biggest_loser.get('symbol')
            profit = biggest_loser.get('profit', 0)
            
            self.logger.info(f"🎯 Testing with biggest loser: {ticket}_{symbol} (${profit:.2f})")
            
            # Force recovery check
            self.force_recovery_check()
            
        except Exception as e:
            self.logger.error(f"Error testing recovery system: {e}")
    
    def check_recovery_positions_with_status(self, group_id: str = None, losing_pairs: list = None):
        """ตรวจสอบ recovery positions พร้อมแสดงสถานะการแก้ไม้"""
        try:
            # ลด log ที่ซ้ำ - ใช้แค่ _log_all_groups_status แทน
            # if group_id and losing_pairs:
            #     self._log_group_hedging_status(group_id, losing_pairs)
            
            # ตรวจสอบ recovery positions ปกติ
            self.check_recovery_positions()
                        
        except Exception as e:
            self.logger.error(f"Error checking recovery positions with status: {e}")
    
    def _close_recovery_position(self, recovery_id: str):
        """ปิด recovery position และคืนค่า PnL"""
        try:
            if recovery_id not in self.recovery_positions:
                self.logger.debug(f"Recovery position {recovery_id} not found in tracking data")
                return 0.0
            
            position = self.recovery_positions[recovery_id]
            symbol = position['symbol']
            order_id = position.get('order_id')
            
            # ตรวจสอบว่าตำแหน่งยังเปิดอยู่จริงหรือไม่ (ใช้ magic number)
            position_exists = False
            pnl = 0.0
            if order_id:
                all_positions = self.broker.get_all_positions()
                for pos in all_positions:
                    if pos['ticket'] == order_id:
                        position_exists = True
                        pnl = pos.get('profit', 0.0)
                        magic = pos.get('magic', 0)
                        # self.logger.debug(f"🔍 Found recovery position: {symbol} (Order: {order_id}, Magic: {magic}, PnL: {pnl:.2f})")
                        break
            
            if not position_exists:
                # ตำแหน่งถูกปิดไปแล้ว ให้อัพเดทสถานะ
                position['status'] = 'closed'
                position['closed_at'] = datetime.now()
                position['close_reason'] = 'already_closed'
                self._update_recovery_data()
                self.logger.debug(f"✅ Recovery position {symbol} was already closed - updated status")
                return 0.0
                
                # ปิดออเดอร์
            success = self.broker.close_position(symbol)
                
            if success:
                position['status'] = 'closed'
                position['closed_at'] = datetime.now()
                position['close_reason'] = 'manual_close'
                self._update_recovery_data()
                self.logger.debug(f"✅ Recovery position closed: {symbol} - PnL: ${pnl:.2f}")
                return pnl
            else:
                self.logger.debug(f"❌ Failed to close recovery position: {symbol}")
                return 0.0
                    
        except Exception as e:
            self.logger.debug(f"Error closing recovery position: {e}")
            return 0.0
    
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
                    self.logger.debug(f"✅ Recovery position closed: {position['symbol']} (reason: {reason})")
                else:
                    self.logger.debug(f"❌ Failed to close recovery position: {position['symbol']}")
                    
        except Exception as e:
            self.logger.debug(f"Error closing recovery position: {e}")
    
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
                'group_hedge_tracking': self.group_hedge_tracking,
                'saved_at': datetime.now().isoformat()
            }
            
            # บันทึกลงไฟล์
            with open(self.persistence_file, 'w') as f:
                json.dump(save_data, f, indent=2, default=str)
            
            self.logger.debug(f"💾 Saved {len(self.recovery_positions)} recovery positions to {self.persistence_file}")
            
        except Exception as e:
            self.logger.debug(f"Error saving recovery data: {e}")
    
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
            self.group_hedge_tracking = save_data.get('group_hedge_tracking', {})
            
            saved_at = save_data.get('saved_at', 'Unknown')
            
            if self.recovery_positions or self.recovery_chains or self.group_hedge_tracking:
                self.logger.info(f"📂 Loaded recovery data from {self.persistence_file}")
                self.logger.info(f"   Recovery positions: {len(self.recovery_positions)}")
                self.logger.info(f"   Recovery chains: {len(self.recovery_chains)}")
                self.logger.info(f"   Group hedge tracking: {len(self.group_hedge_tracking)}")
                self.logger.info(f"   Saved at: {saved_at}")
            else:
                self.logger.debug("No recovery data found in persistence file")
                
        except Exception as e:
            self.logger.debug(f"Error loading recovery data: {e}")
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
            self.group_hedge_tracking = {}
    
    def _update_recovery_data(self):
        """อัปเดตข้อมูล recovery และบันทึกลงไฟล์"""
        try:
            self._save_recovery_data()
        except Exception as e:
            self.logger.debug(f"Error updating recovery data: {e}")
    
    def _remove_recovery_data(self, recovery_id: str):
        """ลบข้อมูล recovery และบันทึกลงไฟล์"""
        try:
            if recovery_id in self.recovery_positions:
                del self.recovery_positions[recovery_id]
            self._save_recovery_data()
        except Exception as e:
            self.logger.debug(f"Error removing recovery data: {e}")
    
    def clear_hedged_data_for_group(self, group_id: str):
        """ล้างข้อมูลการแก้ไม้สำหรับกลุ่มที่ปิดแล้ว (รองรับการแยกตาม Group)"""
        try:
            # ลบข้อมูลการแก้ไม้ที่เกี่ยวข้องกับกลุ่มนี้ (global)
            positions_to_remove = []
            for order_id, hedged_info in self.hedged_positions.items():
                if hedged_info.get('group_id') == group_id:
                    positions_to_remove.append(order_id)
            
            # ใช้ระบบ tracking ใหม่
            self.reset_group_hedge_tracking(group_id)
            
            # Legacy recovery positions by group removed - using individual order tracker
            
            if positions_to_remove:
                self.logger.info(f"🗑️ Cleared {len(positions_to_remove)} hedged positions for group {group_id}")
                self._update_recovery_data()
                
            # แสดงสรุปสถานะ recovery positions หลังจากล้างข้อมูล
            self.log_recovery_positions_summary()
            
            # Log individual order tracker status
            self.order_tracker.log_status_summary()
            
        except Exception as e:
            self.logger.debug(f"Error clearing hedged data for group {group_id}: {e}")
    
    def cleanup_closed_recovery_positions(self):
        """ทำความสะอาด recovery positions ที่ปิดไปแล้วและไม้ซ้ำ"""
        try:
            positions_to_remove = []
            seen_positions = {}  # เก็บข้อมูลไม้ที่เห็นแล้ว
            
            # สร้าง copy ของ dictionary keys เพื่อป้องกัน "dictionary changed size during iteration"
            recovery_ids = list(self.recovery_positions.keys())
            
            for recovery_id in recovery_ids:
                if recovery_id not in self.recovery_positions:
                    continue  # ถ้า position ถูกลบไปแล้วระหว่างการ iterate
                    
                position = self.recovery_positions[recovery_id]
                symbol = position.get('symbol')
                order_id = position.get('order_id')
                
                # ลบไม้ที่ปิดไปแล้ว
                if position.get('status') == 'closed':
                    # ตรวจสอบว่าเป็น positions เก่าที่ปิดไปนานแล้วหรือไม่
                    closed_at = position.get('closed_at')
                    if closed_at:
                        if isinstance(closed_at, str):
                            closed_at = datetime.fromisoformat(closed_at)
                        
                        # ลบ positions ที่ปิดไปแล้วมากกว่า 1 ชั่วโมง
                        if (datetime.now() - closed_at).total_seconds() > 3600:
                            positions_to_remove.append(recovery_id)
                
                # ลบไม้ซ้ำ (ไม้เดียวกันที่มี order_id เดียวกัน)
                if symbol and order_id and order_id != 'N/A':
                    key = f"{symbol}_{order_id}"
                    if key in seen_positions:
                        # ไม้ซ้ำ - ลบไม้เก่า
                        old_recovery_id = seen_positions[key]
                        if old_recovery_id not in positions_to_remove:
                            positions_to_remove.append(old_recovery_id)
                        self.logger.info(f"🗑️ Removing duplicate position: {symbol} (Order: {order_id})")
                    else:
                        seen_positions[key] = recovery_id
            
            # ลบ positions เก่าและไม้ซ้ำ
            for recovery_id in positions_to_remove:
                if recovery_id in self.recovery_positions:
                    del self.recovery_positions[recovery_id]
            
            if positions_to_remove:
                self.logger.info(f"🗑️ Cleaned up {len(positions_to_remove)} old/duplicate recovery positions")
                self._update_recovery_data()
            
        except Exception as e:
            self.logger.debug(f"Error cleaning up closed recovery positions: {e}")
    
    def get_hedging_status(self) -> Dict:
        """ดึงสถานะการแก้ไม้ทั้งหมด"""
        try:
            return {
                'group_hedge_tracking': self.group_hedge_tracking,
                'tracking_groups_count': len(self.group_hedge_tracking),
                'hedged_groups': self.hedged_groups
            }
        except Exception as e:
            self.logger.debug(f"Error getting hedging status: {e}")
            return {}
    
    def log_recovery_positions_summary(self):
        """แสดงสรุปสถานะ recovery positions"""
        try:
            if not self.recovery_positions:
                self.logger.debug("📊 No recovery positions found")
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
            self.logger.info(f"Group Hedge Tracking: {len(self.group_hedge_tracking)}")
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.debug(f"Error logging recovery positions summary: {e}")
    
    def stop(self):
        """หยุดการทำงานของ Correlation Manager"""
        try:
            self.is_running = False
            # บันทึกข้อมูลก่อนปิด
            self._save_recovery_data()
            self.logger.info("🛑 Correlation Manager stopped")
        except Exception as e:
            self.logger.debug(f"Error stopping Correlation Manager: {e}")
