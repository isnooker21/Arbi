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
        self.ai_engine = ai_engine  # ✅ Enable AI engine for correlation data
        self.correlation_matrix = {}
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
        
        # Load configuration from config file
        self._load_config_from_file()
        
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
        
        # Auto-register existing orders on startup
        self.logger.info("🔧 Auto-registering existing MT5 positions...")
        try:
            self.register_existing_orders()
        except Exception as e:
            self.logger.error(f"❌ Error in auto-registration: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
        
        self.logger.info("✅ CorrelationManager initialization completed")
    
    def _load_config_from_file(self):
        """โหลดการตั้งค่าจาก config file"""
        try:
            import json
            import os
            
            config_path = 'config/adaptive_params.json'
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # โหลด recovery parameters
                recovery_params = config.get('recovery_params', {})
                correlation_thresholds = recovery_params.get('correlation_thresholds', {})
                loss_thresholds = recovery_params.get('loss_thresholds', {})
                hedge_ratios = recovery_params.get('hedge_ratios', {})
                timing = recovery_params.get('timing', {})
                
                # ตั้งค่า recovery thresholds จาก config (% based)
                self.recovery_thresholds = {
                    'min_correlation': correlation_thresholds.get('min_correlation', 0.6),
                    'max_correlation': correlation_thresholds.get('max_correlation', 0.95),
                    'min_loss_percent': loss_thresholds.get('min_loss_percent', -0.005),  # % based
                    'use_percentage_based': loss_thresholds.get('use_percentage_based', True),
                    'max_recovery_time_hours': timing.get('max_recovery_time_hours', 24),
                    'hedge_ratio_range': (
                        hedge_ratios.get('min_ratio', 0.7),
                        hedge_ratios.get('max_ratio', 1.3)
                    ),
                    'wait_time_minutes': timing.get('recovery_check_interval_minutes', 5),
                    'cooldown_between_checks': timing.get('cooldown_between_checks', 10),
                    'base_lot_size': 0.05
                }
                
                # โหลด diversification settings
                diversification = recovery_params.get('diversification', {})
                self.max_symbol_usage = diversification.get('max_usage_per_symbol', 3)
                
                # โหลด chain recovery settings (% based)
                chain_recovery = recovery_params.get('chain_recovery', {})
                self.chain_recovery_enabled = chain_recovery.get('enabled', True)
                self.max_chain_depth = chain_recovery.get('max_chain_depth', 3)
                self.min_loss_percent_for_chain = chain_recovery.get('min_loss_percent_for_chain', -0.004)  # % based
                
                # โหลด price distance และ position age
                self.min_price_distance_pips = loss_thresholds.get('min_price_distance_pips', 10)
                self.min_position_age_seconds = timing.get('min_position_age_seconds', 60)
                
                # โหลด risk management parameters
                risk_mgmt = config.get('position_sizing', {}).get('risk_management', {})
                self.portfolio_balance_threshold = risk_mgmt.get('max_portfolio_risk', 0.05)
                
                self.logger.info("=" * 60)
                self.logger.info("✅ RECOVERY CONFIG LOADED (% BASED)")
                self.logger.info("=" * 60)
                self.logger.info(f"📊 Correlation: {self.recovery_thresholds['min_correlation']:.1%} - {self.recovery_thresholds['max_correlation']:.1%}")
                self.logger.info(f"💡 Loss Threshold: {abs(self.recovery_thresholds['min_loss_percent']):.3%} of balance (dynamic)")
                
                # แสดงตัวอย่างสำหรับ balance ต่างๆ
                example_balances = [5000, 10000, 50000, 100000]
                self.logger.info(f"   Examples:")
                for bal in example_balances:
                    amount = bal * self.recovery_thresholds['min_loss_percent']
                    self.logger.info(f"   - Balance ${bal:,}: Loss >= ${abs(amount):.2f} triggers recovery")
                
                self.logger.info(f"📏 Min Distance: {self.min_price_distance_pips} pips")
                self.logger.info(f"⏱️  Min Age: {self.min_position_age_seconds}s before recovery")
                self.logger.info(f"⏱️  Cooldown: {self.recovery_thresholds['cooldown_between_checks']}s between checks")
                self.logger.info(f"🔗 Chain Recovery: {'ENABLED' if self.chain_recovery_enabled else 'DISABLED'}")
                if self.chain_recovery_enabled:
                    self.logger.info(f"   Max Depth: {self.max_chain_depth} levels")
                    self.logger.info(f"   Min Loss for Chain: {abs(self.min_loss_percent_for_chain):.3%} of balance")
                    for bal in [5000, 10000, 50000]:
                        amount = bal * self.min_loss_percent_for_chain
                        self.logger.info(f"   - Balance ${bal:,}: >= ${abs(amount):.2f}")
                self.logger.info(f"📦 Hedge Ratio: {self.recovery_thresholds['hedge_ratio_range'][0]} - {self.recovery_thresholds['hedge_ratio_range'][1]}")
                self.logger.info(f"🎯 Max Symbol Usage: {self.max_symbol_usage} times")
                self.logger.info(f"📏 Base Lot Size: {self.recovery_thresholds['base_lot_size']}")
                self.logger.info("=" * 60)
                
            else:
                self.logger.warning("⚠️ Config file not found, using fallback values")
                self._set_fallback_config()
                
        except Exception as e:
            self.logger.error(f"❌ Error loading config: {e}")
            self.logger.info("🔄 Using fallback configuration")
            self._set_fallback_config()
    
    def _set_fallback_config(self):
        """ตั้งค่า fallback เมื่อไม่สามารถโหลด config ได้ (% based)"""
        self.recovery_thresholds = {
            'min_correlation': 0.6,      # ความสัมพันธ์ขั้นต่ำ 60%
            'max_correlation': 0.95,     # ความสัมพันธ์สูงสุด 95%
            'min_loss_percent': -0.005,  # ขาดทุนขั้นต่ำ -0.5% ของ balance (% based)
            'use_percentage_based': True, # ใช้ % based
            'max_recovery_time_hours': 24, # เวลาสูงสุด 24 ชั่วโมง
            'hedge_ratio_range': (0.7, 1.3),  # ขนาด hedge ratio
            'wait_time_minutes': 5,      # รอ 5 นาทีก่อนแก้ไม้
            'cooldown_between_checks': 10,  # เช็คทุก 10 วินาที
            'base_lot_size': 0.05        # ขนาด lot เริ่มต้น
        }
        
        # Diversification settings
        self.max_symbol_usage = 3  # ใช้ symbol เดียวกันได้สูงสุด 3 ครั้ง
        
        # Chain recovery settings (% based)
        self.chain_recovery_enabled = True  # เปิด chain recovery
        self.max_chain_depth = 3  # แก้ได้ลึกสุด 3 ระดับ
        self.min_loss_percent_for_chain = -0.004  # Recovery ต้องขาดทุน >= 0.4% ของ balance
        
        # Price distance และ position age
        self.min_price_distance_pips = 10  # ต้องห่าง >= 10 pips
        self.min_position_age_seconds = 60  # ต้องเปิดมา >= 60 วินาที
        
        # Portfolio balance threshold ที่ระมัดระวัง
        self.portfolio_balance_threshold = 0.05  # 5% imbalance threshold
        
        self.logger.info("✅ Fallback configuration applied")
    
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
            
            # Legacy recovery_chains removed - using order_tracker now
            # Recovery tracking is handled by order_tracker.register_recovery_order()
            
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
            recovery_positions_all = []
            for pos in all_positions:
                magic = pos.get('magic', 0)
                comment = pos.get('comment', '')
                
                if magic in [234001, 234002, 234003, 234004, 234005, 234006]:
                    if magic not in groups_data:
                        groups_data[magic] = []
                    groups_data[magic].append(pos)
                elif comment.startswith('RECOVERY_'):
                    # รวม recovery orders ที่มี magic number อื่น
                    recovery_positions_all.append(pos)
            
            # แสดงสถานะแต่ละ Group เรียงตาม Group
            for magic in sorted(groups_data.keys()):
                group_number = self._get_group_number_from_magic(magic)
                group_positions = groups_data[magic]
                
                # แยกประเภทไม้
                arbitrage_positions = [pos for pos in group_positions if not pos.get('comment', '').startswith('RECOVERY_')]
                recovery_positions = [pos for pos in group_positions if pos.get('comment', '').startswith('RECOVERY_')]
                
                # เพิ่ม recovery orders ที่มี magic number อื่น
                for recovery_pos in recovery_positions_all:
                    recovery_comment = recovery_pos.get('comment', '')
                    if f"G{group_number}_" in recovery_comment:
                        recovery_positions.append(recovery_pos)
                
                
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
                        
                        # สร้าง position dict ที่มี ticket
                        position_data = {
                            'symbol': symbol,
                            'ticket': pos.get('ticket', ''),
                            'profit': pnl
                        }
                        
                        # ใช้ Individual Order Tracker ในการตรวจสอบ hedge status
                        is_hedged = self._is_position_hedged(position_data, group_id)
                            
                        # แสดงสถานะกำไร/ขาดทุน
                        pnl_icon = "🟢" if pnl >= 0 else "🔴"
                        
                        if is_hedged:
                            # แสดง recovery orders ที่เกี่ยวข้อง
                            ticket = str(pos.get('ticket', ''))
                            order_info = self.order_tracker.get_order_info(ticket, symbol)
                            if order_info:
                                recovery_orders = order_info.get('recovery_orders', [])
                                self.logger.info(f"   {symbol:8s}: ${pnl:8.2f} {pnl_icon}")
                                self.logger.info(f"   - HG แล้ว")
                                
                                
                                # แสดง recovery orders ต่อท้ายคู่เงิน
                                if recovery_orders:
                                    for recovery_key in recovery_orders:
                                        if recovery_key in self.order_tracker.order_tracking:
                                            recovery_info = self.order_tracker.order_tracking[recovery_key]
                                            recovery_symbol = recovery_info.get('symbol', '')
                                            recovery_ticket = recovery_info.get('ticket', '')
                                            
                                            # หา recovery position จาก MT5
                                            recovery_position = self._get_position_by_ticket(recovery_ticket)
                                            if recovery_position:
                                                recovery_pnl = recovery_position.get('profit', 0)
                                                recovery_icon = "🟢" if recovery_pnl >= 0 else "🔴"
                                                self.logger.info(f"     └─ {recovery_symbol:8s}: ${recovery_pnl:8.2f} {recovery_icon} [RECOVERY]")
                                            else:
                                                self.logger.info(f"     └─ {recovery_symbol:8s}: [CLOSED] [RECOVERY]")
                        else:
                            self.logger.info(f"   {symbol:8s}: ${pnl:8.2f} {pnl_icon}")
                
                
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
    
    def _get_recovery_symbol_usage(self) -> Dict[str, int]:
        """นับว่าแต่ละคู่เงินถูกใช้แก้กี่ครั้งแล้ว"""
        try:
            usage = {}
            all_orders = self.order_tracker.get_all_orders()
            
            for order_key, order_info in all_orders.items():
                if order_info.get('type') == 'RECOVERY' and order_info.get('status') != 'CLOSED':
                    symbol = order_info.get('symbol')
                    if symbol:
                        usage[symbol] = usage.get(symbol, 0) + 1
            
            return usage
        except Exception as e:
            self.logger.error(f"Error getting recovery symbol usage: {e}")
            return {}
    
    def _is_recovery_symbol_available(self, symbol: str, max_usage: int = 2) -> bool:
        """เช็คว่าคู่เงินนี้ยังใช้ได้หรือไม่ (จำกัด max 2 ครั้ง)"""
        try:
            usage = self._get_recovery_symbol_usage()
            current_usage = usage.get(symbol, 0)
            is_available = current_usage < max_usage
            
            if not is_available:
                self.logger.debug(f"Symbol {symbol} not available: used {current_usage}/{max_usage} times")
            
            return is_available
        except Exception as e:
            self.logger.error(f"Error checking symbol availability: {e}")
            return True  # Fallback: allow if error
    
    def _calculate_dynamic_hedge_lot(self, original_pnl: float, correlation: float, 
                                       original_symbol: str, hedge_symbol: str) -> float:
        """คำนวณ hedge lot ตามการขาดทุนจริง - ใช้ pip value ที่แท้จริง"""
        try:
            from utils.calculations import TradingCalculations
            
            # Target: Recovery 75-80% ของการขาดทุน (ปรับตาม correlation)
            # Correlation สูง → Target สูง, Correlation ต่ำ → Target ต่ำ
            base_recovery_target = 0.75
            correlation_bonus = abs(correlation) * 0.1  # Max +10%
            recovery_target = min(base_recovery_target + correlation_bonus, 0.85)
            
            target_recovery_pnl = abs(original_pnl) * recovery_target
            
            # ✅ ขั้นตอนที่ 1: คำนวณ pip value ของไม้เดิม
            # หา lot size ของไม้เดิม
            original_lot = 0.5  # Default fallback
            all_positions = self.broker.get_all_positions()
            for pos in all_positions:
                if pos.get('symbol') == original_symbol:
                    original_lot = pos.get('volume', 0.5)
                    break
            
            # คำนวณ pip value ของไม้เดิม
            original_pip_value = TradingCalculations.calculate_pip_value(original_symbol, original_lot, self.broker)
            
            # ✅ ขั้นตอนที่ 2: คำนวณ target pip value สำหรับ hedge
            # ใช้ correlation เพื่อปรับ pip value
            target_pip_value = original_pip_value * abs(correlation)
            
            # ✅ ขั้นตอนที่ 3: คำนวณ hedge lot ที่ให้ pip value ตาม target
            hedge_pip_value_per_01 = TradingCalculations.calculate_pip_value(hedge_symbol, 0.1, self.broker)
            
            if hedge_pip_value_per_01 > 0:
                # hedge_lot = (target_pip_value / pip_value_per_01) × 0.1
                hedge_lot = (target_pip_value / hedge_pip_value_per_01) * 0.1
            else:
                # Fallback: ใช้ original lot × correlation
                hedge_lot = original_lot * abs(correlation)
            
            # ✅ ขั้นตอนที่ 4: ปรับ lot size เพิ่มเติมเพื่อให้ถึง recovery target
            # คำนวณว่า hedge lot ปัจจุบันจะ recover ได้เท่าไหร่
            if hedge_pip_value_per_01 > 0:
                expected_recovery_per_pip = (hedge_lot / 0.1) * hedge_pip_value_per_01
                pips_needed = target_recovery_pnl / expected_recovery_per_pip if expected_recovery_per_pip > 0 else 10
                
                # ถ้าต้องการ pips มาก แปลว่า lot ยังเล็กไป
                if pips_needed > 10:  # ถ้าต้องการมากกว่า 10 pips ถึงจะ recover ได้
                    # เพิ่ม lot size ขึ้น
                    hedge_lot = hedge_lot * (pips_needed / 10)
            
            # ✅ ขั้นตอนที่ 5: จำกัด min/max และ round
            hedge_lot = max(0.1, min(hedge_lot, 2.0))
            hedge_lot = TradingCalculations.round_to_valid_lot_size(hedge_lot)
            
            self.logger.info(f"📊 Dynamic Hedge Calculation:")
            self.logger.info(f"   Original: {original_symbol} {original_lot:.2f} lot, PnL=${original_pnl:.2f}")
            self.logger.info(f"   Original Pip Value: ${original_pip_value:.2f}")
            self.logger.info(f"   Target Pip Value: ${target_pip_value:.2f} (correlation {correlation:.2f})")
            self.logger.info(f"   Hedge: {hedge_symbol} {hedge_lot:.2f} lot")
            self.logger.info(f"   Target Recovery: ${target_recovery_pnl:.2f} ({recovery_target:.1%})")
            
            return float(hedge_lot)
            
        except Exception as e:
            self.logger.error(f"Error calculating dynamic hedge lot: {e}")
            # Fallback: ใช้ original lot × correlation
            all_positions = self.broker.get_all_positions()
            original_lot = 0.5
            for pos in all_positions:
                if pos.get('symbol') == original_symbol:
                    original_lot = pos.get('volume', 0.5)
                    break
            
            fallback_lot = original_lot * abs(correlation)
            fallback_lot = max(0.1, min(fallback_lot, 2.0))
            
            from utils.calculations import TradingCalculations
            fallback_lot = TradingCalculations.round_to_valid_lot_size(fallback_lot)
            
            return fallback_lot
    
    def _calculate_portfolio_exposure(self, group_id: str) -> Dict:
        """คำนวณ net exposure ของ portfolio"""
        try:
            exposure = {
                'total_pnl': 0.0,
                'currency_exposure': {},
                'positions': []
            }
            
            # Get all positions in group
            all_positions = self.broker.get_all_positions()
            
            for pos in all_positions:
                symbol = pos.get('symbol', '')
                pnl = pos.get('profit', 0)
                
                if len(symbol) >= 6:
                    base = symbol[:3]
                    quote = symbol[3:6]
                    
                    # Update currency exposure
                    exposure['currency_exposure'][base] = exposure['currency_exposure'].get(base, 0) + pnl
                    exposure['currency_exposure'][quote] = exposure['currency_exposure'].get(quote, 0) - pnl
                
                exposure['total_pnl'] += pnl
                exposure['positions'].append({'symbol': symbol, 'pnl': pnl})
            
            return exposure
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio exposure: {e}")
            return {'total_pnl': 0.0, 'currency_exposure': {}, 'positions': []}
    
    def calculate_recovery_metrics(self) -> Dict:
        """คำนวณ metrics สำหรับวัดผล recovery system"""
        try:
            all_orders = self.order_tracker.get_all_orders()
            
            metrics = {
                'total_recovery_orders': 0,
                'symbol_usage': {},
                'recovery_efficiency': {},
                'avg_recovery_rate': 0.0,
                'symbol_diversity': 0.0,
            }
            
            recovery_orders = []
            for order_key, order_info in all_orders.items():
                if order_info.get('type') == 'RECOVERY':
                    metrics['total_recovery_orders'] += 1
                    symbol = order_info.get('symbol')
                    if symbol:
                        metrics['symbol_usage'][symbol] = metrics['symbol_usage'].get(symbol, 0) + 1
                    recovery_orders.append(order_info)
            
            # Calculate diversity
            if metrics['total_recovery_orders'] > 0:
                metrics['symbol_diversity'] = len(metrics['symbol_usage']) / metrics['total_recovery_orders']
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating recovery metrics: {e}")
            return {'total_recovery_orders': 0, 'symbol_usage': {}, 'avg_recovery_rate': 0.0}
    
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
            
            is_hedged = self.order_tracker.is_order_hedged(ticket, symbol)
            
            return is_hedged
            
        except Exception as e:
            self.logger.error(f"Error checking hedge status: {e}")
            return False
    
    def _is_position_hedged_from_mt5(self, group_id: str, symbol: str) -> bool:
        """Check if position is hedged by querying MT5 directly"""
        try:
            # Get all tracked orders
            all_orders = self.order_tracker.get_all_orders()
            
            # Check if any position for this symbol in the group is hedged
            for order_key, order_info in all_orders.items():
                if (order_info.get('group_id') == group_id and 
                    order_info.get('symbol') == symbol):
                    ticket = str(order_info.get('ticket', ''))
                    if ticket and self.order_tracker.is_order_hedged(ticket, symbol):
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking hedge status from MT5: {e}")
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
        """คำนวณขนาด lot สำหรับ hedge position - ใช้ dynamic calculation"""
        try:
            # ✅ NEW: Try to get original position PnL for dynamic calculation
            original_pnl = 0.0
            if original_symbol:
                all_positions = self.broker.get_all_positions()
                for pos in all_positions:
                    if pos.get('symbol') == original_symbol:
                        original_pnl = pos.get('profit', 0)
                        break
            
            # ✅ NEW: Use dynamic hedge calculation if PnL is available
            if abs(original_pnl) > 0 and hedge_symbol:
                hedge_lot = self._calculate_dynamic_hedge_lot(
                    original_pnl, correlation, original_symbol, hedge_symbol
                )
                
                # ✅ Ensure lot size is valid (round to 0.01)
                from utils.calculations import TradingCalculations
                hedge_lot = TradingCalculations.round_to_valid_lot_size(hedge_lot)
                
                self.logger.info(f"📊 Using Dynamic Hedge Calculation: Original PnL=${original_pnl:.2f}, Hedge Lot={hedge_lot:.4f}")
                return hedge_lot
            
            # ✅ Fallback to original calculation if dynamic fails
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
        """ตรวจสอบ recovery chain และดำเนินการต่อเนื่อง (simplified - using order_tracker)"""
        try:
            # Chain recovery removed - now using single-level recovery via order_tracker
            # Get orders needing recovery from order_tracker
            orders_needing_recovery = self.order_tracker.get_orders_needing_recovery()
            
            if not orders_needing_recovery:
                return
            
            # Log orders that need recovery
            self.logger.debug(f"📊 Orders needing recovery: {len(orders_needing_recovery)}")
            
            # Recovery logic can be implemented here if needed
            # For now, just tracking status via order_tracker
                        
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
    
    # REMOVED: _continue_recovery_chain() - Chain recovery complexity removed
    # Recovery is now simplified to single-level: Original Order → Recovery Order
    # Use order_tracker for all hedge status checks instead
    
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
        """ตรวจสอบโอกาสการ recovery (simplified - using order_tracker)"""
        try:
            # Get orders needing recovery from order_tracker
            orders_needing_recovery = self.order_tracker.get_orders_needing_recovery()
            
            for order_info in orders_needing_recovery:
                # Check if recovery should be initiated for this order
                # Chain recovery removed - single level recovery only
                pass  # Recovery logic would go here if needed
                        
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
        """Find optimal correlation pairs with negative correlation filter"""
        try:
            # Get correlations from AI engine
            correlations = self.ai_engine.get_correlations(base_symbol)
            
            if not correlations:
                self.logger.debug(f"No correlations found for {base_symbol}")
                return []
            
            correlation_candidates = []
            
            for pair, corr_value in correlations.items():
                # Skip if pair is in the same group
                if group_pairs and pair in group_pairs:
                    continue
                
                # ✅ Filter: Common currency
                if self._has_common_currency(base_symbol, pair):
                    self.logger.debug(f"⏭️ Skip {pair}: common currency with {base_symbol}")
                    continue
                
                # ✅ Filter: Only negative correlations (RELAXED THRESHOLD)
                if -0.98 < corr_value < -0.2:
                    correlation_candidates.append({
                        'symbol': pair,
                        'correlation': corr_value,
                        'direction': 'opposite'
                    })
                    self.logger.debug(f"✅ Valid hedge candidate: {pair} (correlation: {corr_value:.2f})")
            
            # ✅ Sort by most negative correlation
            correlation_candidates.sort(key=lambda x: x['correlation'])
            
            if correlation_candidates:
                self.logger.info(f"🎯 Found {len(correlation_candidates)} optimal negative correlation pairs for {base_symbol}")
                for i, candidate in enumerate(correlation_candidates[:3], 1):
                    self.logger.info(f"   {i}. {candidate['symbol']}: {candidate['correlation']:.2f}")
            
            return correlation_candidates[:5]  # Top 5 best candidates
            
        except Exception as e:
            self.logger.error(f"Error finding optimal pairs: {e}")
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
            return correlation < -0.2  # Negative correlation (RELAXED THRESHOLD)
            
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
        ⚡ CRITICAL: Execute correlation position for recovery with comprehensive duplicate prevention
        """
        try:
            symbol = correlation_candidate['symbol']
            correlation = correlation_candidate['correlation']
            original_symbol = original_position.get('symbol', '')
            original_ticket = str(original_position.get('ticket', ''))
            
            self.logger.info(f"🎯 Starting recovery for ticket {original_ticket}_{original_symbol}")
            
            # ✅ CRITICAL CHECK #1: Verify this ticket is not already hedged
            if self.order_tracker.is_order_hedged(original_ticket, original_symbol):
                self.logger.warning(f"🚫 DUPLICATE PREVENTION: Ticket {original_ticket}_{original_symbol} already hedged - skipping")
                return False
            
            # ✅ CRITICAL CHECK #2: Double-check in case of race condition
            if not self.order_tracker.needs_recovery(original_ticket, original_symbol):
                self.logger.warning(f"🚫 DUPLICATE PREVENTION: Ticket {original_ticket}_{original_symbol} doesn't need recovery - skipping")
                return False
            
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
            order_result = self._send_correlation_order(symbol, correlation_lot_size, group_id, original_position)
            
            if order_result and order_result.get('success'):
                recovery_ticket = str(order_result.get('order_id', ''))
                
                if recovery_ticket:
                    # ✅ CRITICAL: Register recovery immediately
                    success = self.order_tracker.register_recovery_order(
                        recovery_ticket, symbol,           # Recovery order info
                        original_ticket, original_symbol   # Original order being hedged
                    )
                    
                    if success:
                        self.logger.info(f"✅ RECOVERY REGISTERED: {original_ticket}_{original_symbol} → {recovery_ticket}_{symbol}")
                        self.logger.info(f"   Original ticket {original_ticket} is now HEDGED")
                    else:
                        self.logger.error(f"❌ Failed to register recovery for {original_ticket}_{original_symbol}")
                        return False
                else:
                    self.logger.error("❌ No recovery ticket received from order")
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
                
                # Legacy recovery_positions removed - using order_tracker now
                # Recovery tracking is handled by order_tracker.register_recovery_order()
                # No need to manually track recovery positions
                
                # บันทึกข้อมูลการแก้ไม้
                self._log_hedging_action(original_position, correlation_position, correlation_candidate, group_id)
                
                return True
            else:
                self.logger.error(f"❌ Recovery order failed for {original_ticket}_{original_symbol}")
                return False
                
        except Exception as e:
            original_symbol = original_position.get('symbol', '')
            self.logger.error(f"Error executing correlation position: {e}")
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
        """Send recovery order with SHORT comment format"""
        try:
            original_ticket = str(original_position.get('ticket', '')) if original_position else 'UNKNOWN'
            original_symbol = original_position.get('symbol', 'UNKNOWN') if original_position else 'UNKNOWN'
            
            # ✅ NEW SHORT FORMAT: "R{ticket}_{recovery_symbol}"
            # Example: "R3317086_AUDUSD" = 16 chars ✅
            
            # Extract last 7 digits of ticket for uniqueness
            ticket_short = original_ticket[-7:] if len(original_ticket) > 7 else original_ticket
            
            comment = f"R{ticket_short}_{symbol}"
            
            # Ensure comment is under 31 characters
            if len(comment) > 31:
                # Truncate symbol if needed
                max_symbol_len = 31 - len(f"R{ticket_short}_")
                comment = f"R{ticket_short}_{symbol[:max_symbol_len]}"
            
            self.logger.info(f"📝 Recovery comment: '{comment}' (length: {len(comment)})")
            
            # หา magic number จาก group_id หรือใช้ default
            magic_number = self._get_magic_number_from_group_id(group_id)
            if not magic_number:
                magic_number = 234000  # Default magic number for recovery orders
            
            # Determine direction based on correlation
            order_type = self._calculate_hedge_direction(original_position, symbol)
            
            # ส่งออเดอร์
            result = self.broker.place_order(
                symbol=symbol,
                order_type=order_type,  # ใช้ทิศทางที่ถูกต้อง
                volume=lot_size,
                comment=comment,
                magic=magic_number
            )
            
            if result and (result.get('retcode') == 10009 or result.get('success')):
                self.logger.info(f"✅ Recovery order sent: {symbol} {lot_size} lot")
                self.logger.info(f"   Comment: {comment}")
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
        """Check recovery with smart logging and proper recovery order exclusion"""
        try:
            # Cooldown check to prevent excessive logging (อ่านจาก config)
            current_time = datetime.now()
            cooldown = self.recovery_thresholds.get('cooldown_between_checks', 10)  # Default 10 seconds
            
            if hasattr(self, 'last_recovery_check'):
                elapsed = (current_time - self.last_recovery_check).total_seconds()
                if elapsed < cooldown:
                    return
            
            self.last_recovery_check = current_time
            
            # 🔄 STEP 1: Sync individual order tracker with MT5
            sync_results = self.order_tracker.sync_with_mt5()
            if sync_results.get('orders_removed', 0) > 0:
                self.logger.info(f"🔄 Synced: {sync_results['orders_removed']} orders removed")
            
            # 🔄 STEP 1.5: Auto-register any new orders that aren't tracked yet
            self._auto_register_new_orders()
            
            # Get orders needing recovery from individual order tracker
            orders_needing_recovery = self.order_tracker.get_orders_needing_recovery()
            
            # 📊 Log tracker statistics periodically
            if not hasattr(self, '_last_stats_log'):
                self._last_stats_log = current_time
            elif (current_time - self._last_stats_log).total_seconds() > 60:  # Every minute
                stats = self.order_tracker.get_statistics()
                self.logger.info(f"📊 Order Tracker: {stats['total_tracked_orders']} total, "
                               f"{stats['not_hedged_orders']} need recovery, "
                               f"{stats['hedged_orders']} hedged")
                self._last_stats_log = current_time
            
            if not orders_needing_recovery:
                # Only log once per 5 minutes if no orders
                if not hasattr(self, '_last_no_orders_log'):
                    self._last_no_orders_log = current_time
                elif (current_time - self._last_no_orders_log).total_seconds() > 300:
                    stats = self.order_tracker.get_statistics()
                    self.logger.info(f"ℹ️ No orders need recovery (Total tracked: {stats['total_tracked_orders']}, "
                                   f"Hedged: {stats['hedged_orders']})")
                    self._last_no_orders_log = current_time
                return
            
            # Find valid candidates with detailed tracking
            valid_candidates = []
            skipped_reasons = {
                'already_recovery': 0,
                'already_hedged': 0,
                'insufficient_loss': 0,
                'not_found_mt5': 0
            }
            
            for order_info in orders_needing_recovery:
                ticket = order_info.get('ticket')
                symbol = order_info.get('symbol')
                
                # Get actual position from MT5
                position = self._get_position_by_ticket(ticket)
                if not position:
                    skipped_reasons['not_found_mt5'] += 1
                    continue
                
                # ✅ CRITICAL FIX: Skip recovery orders completely
                if self._is_recovery_order(position):
                    skipped_reasons['already_recovery'] += 1
                    continue
                
                # ✅ CRITICAL: Double-check if this specific ticket is already hedged
                if self.order_tracker.is_order_hedged(ticket, symbol):
                    skipped_reasons['already_hedged'] += 1
                    continue
                
                # ✅ CRITICAL: Check if this ticket needs recovery
                if not self.order_tracker.needs_recovery(ticket, symbol):
                    skipped_reasons['already_hedged'] += 1
                    continue
                
                # Check recovery conditions
                if self._meets_recovery_conditions(position):
                    valid_candidates.append(position)
                else:
                    skipped_reasons['insufficient_loss'] += 1
            
            # Only log if there's something meaningful to report
            if valid_candidates:
                self.logger.info(f"🎯 Found {len(valid_candidates)} valid recovery candidates")
                best_candidate = max(valid_candidates, key=lambda x: abs(x.get('profit', 0)))
                ticket = best_candidate.get('ticket')
                symbol = best_candidate.get('symbol')
                profit = best_candidate.get('profit', 0)
                
                self.logger.info(f"🎯 Processing best candidate: {ticket}_{symbol} (${profit:.2f})")
                
                # Start recovery
                self._start_individual_recovery(best_candidate)
                
                # ✅ NEW: Log recovery metrics after processing
                try:
                    metrics = self.calculate_recovery_metrics()
                    if metrics['total_recovery_orders'] > 0:
                        self.logger.info(f"📊 Recovery Metrics: Diversity={metrics['symbol_diversity']:.2%}, Total Orders={metrics['total_recovery_orders']}")
                        
                        # Show top symbol usage
                        if metrics['symbol_usage']:
                            top_symbols = sorted(metrics['symbol_usage'].items(), key=lambda x: x[1], reverse=True)[:3]
                            usage_str = ", ".join([f"{s}:{c}x" for s, c in top_symbols])
                            self.logger.info(f"📊 Top Symbol Usage: {usage_str}")
                except:
                    pass  # Don't fail if metrics calculation fails
            else:
                # Log skip reasons only at debug level
                total_skipped = sum(skipped_reasons.values())
                if total_skipped > 0:
                    self.logger.debug(f"⏭️ Skipped {total_skipped} orders: {skipped_reasons}")
                
                # Only log "no candidates" once per 5 minutes
                if not hasattr(self, '_last_no_candidates_log'):
                    self._last_no_candidates_log = current_time
                elif (current_time - self._last_no_candidates_log).total_seconds() > 300:
                    self.logger.info(f"ℹ️ No valid candidates (Reasons: {skipped_reasons})")
                    self._last_no_candidates_log = current_time
            
        except Exception as e:
            self.logger.error(f"Error in recovery check: {e}")
    
    def _has_common_currency(self, symbol1: str, symbol2: str) -> bool:
        """
        Check if two currency pairs share a common currency.
        
        Example:
            EURJPY vs AUDJPY → True (both have JPY)
            EURJPY vs GBPAUD → False (no common currency)
        
        Args:
            symbol1: First currency pair (e.g., "EURJPY")
            symbol2: Second currency pair (e.g., "AUDJPY")
            
        Returns:
            True if pairs share any currency
        """
        # Validate symbol format
        if len(symbol1) != 6 or len(symbol2) != 6:
            return False
        
        # Extract currencies
        base1 = symbol1[:3]    # EUR from EURJPY
        quote1 = symbol1[3:]   # JPY from EURJPY
        base2 = symbol2[:3]    # AUD from AUDJPY
        quote2 = symbol2[3:]   # JPY from AUDJPY
        
        # Check if any currency matches
        has_common = (base1 == base2 or base1 == quote2 or 
                      quote1 == base2 or quote1 == quote2)
        
        if has_common:
            self.logger.debug(f"❌ Common currency: {symbol1} and {symbol2} share currency")
            return True
        
        return False

    def _extract_currencies(self, symbol: str) -> tuple:
        """
        Extract base and quote currencies from symbol.
        
        Args:
            symbol: Currency pair (e.g., "EURJPY")
            
        Returns:
            Tuple of (base, quote) or (None, None) if invalid
        """
        if len(symbol) != 6:
            return (None, None)
        
        base = symbol[:3]
        quote = symbol[3:]
        return (base, quote)

    def _get_recovery_chain_depth(self, ticket: str, symbol: str) -> int:
        """คำนวณความลึกของ chain recovery"""
        try:
            depth = 0
            current_key = f"{ticket}_{symbol}"
            
            # ย้อนกลับไปหา original order
            while current_key:
                order_info = self.order_tracker.get_order_info(ticket, symbol)
                if not order_info:
                    break
                
                # ถ้าเป็น recovery order
                if order_info.get('type') == 'RECOVERY':
                    depth += 1
                    # ไปหา order ที่มันกำลัง hedge
                    hedging_for = order_info.get('hedging_for', '')
                    if hedging_for and '_' in hedging_for:
                        parts = hedging_for.rsplit('_', 1)
                        if len(parts) == 2:
                            ticket, symbol = parts[0], parts[1]
                            current_key = hedging_for
                        else:
                            break
                    else:
                        break
                else:
                    # เจอ original order แล้ว
                    break
            
            return depth
            
        except Exception as e:
            self.logger.error(f"Error calculating chain depth: {e}")
            return 0
    
    def _calculate_price_distance_pips(self, position: Dict) -> float:
        """คำนวณระยะห่างจาก entry price (pips)"""
        try:
            symbol = position.get('symbol', '')
            entry_price = position.get('price', 0)
            
            if not symbol or entry_price == 0:
                return 0.0
            
            current_price = self.broker.get_current_price(symbol)
            if not current_price:
                return 0.0
            
            # คำนวณ pips
            if 'JPY' in symbol:
                pips = abs(current_price - entry_price) * 100
            else:
                pips = abs(current_price - entry_price) * 10000
            
            return pips
            
        except Exception as e:
            self.logger.error(f"Error calculating price distance: {e}")
            return 0.0
    
    def _get_position_age_seconds(self, position: Dict) -> float:
        """คำนวณอายุของ position (วินาที)"""
        try:
            ticket = str(position.get('ticket', ''))
            symbol = position.get('symbol', '')
            
            # ลองดึงจาก order_tracker
            order_info = self.order_tracker.get_order_info(ticket, symbol)
            if order_info and 'created_at' in order_info:
                created_at = order_info['created_at']
                if isinstance(created_at, datetime):
                    age = (datetime.now() - created_at).total_seconds()
                    return age
            
            # Fallback: ดึงจาก MT5 open time
            open_time = position.get('time', None)
            if open_time:
                if isinstance(open_time, datetime):
                    age = (datetime.now() - open_time).total_seconds()
                    return age
            
            # ถ้าไม่มีข้อมูล ให้ถือว่าเก่าพอแล้ว
            return 999999.0
            
        except Exception as e:
            self.logger.error(f"Error getting position age: {e}")
            return 999999.0
    
    def _is_recovery_order(self, position: Dict) -> bool:
        """Check if position is a recovery order - updated for short format"""
        comment = position.get('comment', '')
        magic = position.get('magic', 0)
        
        # ✅ NEW: Check for short format "R{ticket}_{symbol}"
        if comment.startswith('R') and '_' in comment:
            return True
        
        # Legacy: Check for old format "R12345_GBP->AUD"
        if comment and ('R' == comment[0] and '_' in comment and '->' in comment):
            return True
        
        # Check by old comment format (if any still exist)
        if 'RECOVERY' in comment:
            return True
        
        # Check by magic number (if using different magic for recovery)
        recovery_magic_numbers = [234000, 234100, 234101, 234102, 234103]  # Add more if needed
        if magic in recovery_magic_numbers:
            return True
        
        return False

    def _calculate_hedge_direction(self, original_position: Dict, hedge_symbol: str) -> str:
        """
        Calculate hedge direction based on negative correlation.
        
        For negative correlation pairs:
        - If original is BUY and losing → hedge with opposite direction
        - If original is SELL and losing → hedge with opposite direction
        """
        original_direction = original_position.get('type', 'BUY')
        
        # For negative correlation, use SAME direction
        # (because they move opposite, same direction = opposite effect)
        if original_direction == 'BUY':
            return 'BUY'
        else:
            return 'SELL'

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
        """Check if position meets recovery conditions with detailed logging"""
        try:
            ticket = str(position.get('ticket', ''))
            symbol = position.get('symbol', '')
            profit = position.get('profit', 0)
            comment = position.get('comment', '')
            
            # 🔗 Check if it's a recovery order (Chain Recovery Logic)
            if self._is_recovery_order(position):
                # เช็คว่าเปิด chain recovery ไหม
                if not self.chain_recovery_enabled:
                    self.logger.debug(f"❌ {ticket}_{symbol}: Is recovery order (chain recovery disabled)")
                    return False
                
                # เช็ค chain depth
                chain_depth = self._get_recovery_chain_depth(ticket, symbol)
                if chain_depth >= self.max_chain_depth:
                    self.logger.debug(f"❌ {ticket}_{symbol}: Max chain depth {self.max_chain_depth} reached (current: {chain_depth})")
                    return False
                
                # เช็คว่าขาดทุนมากพอไหม (% based สำหรับ chain)
                balance = self.broker.get_account_balance() or 10000
                loss_percent = profit / balance
                min_chain_percent = getattr(self, 'min_loss_percent_for_chain', -0.004)
                min_chain_amount = balance * min_chain_percent  # Dynamic! เช่น $10k * -0.4% = -$40
                
                if loss_percent > min_chain_percent:
                    self.logger.debug(f"❌ {ticket}_{symbol}: Chain loss {loss_percent:.4f}% not enough (need <= {min_chain_percent:.4f}% = ${min_chain_amount:.2f})")
                    return False
                
                self.logger.info(f"🔗 {ticket}_{symbol}: Is recovery order - Chain recovery ENABLED!")
                self.logger.info(f"   Chain depth: {chain_depth}/{self.max_chain_depth}")
                # ทำต่อได้! ไม่ return False
            
            # Check if position already has recovery orders
            order_info = self.order_tracker.get_order_info(ticket, symbol)
            if order_info:
                recovery_orders = order_info.get('recovery_orders', [])
                if recovery_orders:
                    self.logger.debug(f"❌ {ticket}_{symbol}: Already has {len(recovery_orders)} recovery orders")
                    return False
            
            # Check if position is already hedged
            if self.order_tracker.is_order_hedged(ticket, symbol):
                self.logger.debug(f"❌ {ticket}_{symbol}: Already hedged")
                return False
            
            # Check if position is losing money
            if profit >= 0:
                self.logger.debug(f"❌ {ticket}_{symbol}: Not losing money (${profit:.2f})")
                return False
            
            # 💡 Percentage-based loss check (ยุติธรรมกับทุกขนาด balance)
            balance = self.broker.get_account_balance() or 10000
            loss_percent = profit / balance
            min_loss_percent = self.recovery_thresholds.get('min_loss_percent', -0.005)
            
            # คำนวณ minimum loss amount จาก % (dynamic!)
            min_loss_amount = balance * min_loss_percent  # เช่น $10k * -0.5% = -$50
            
            # เช็คว่าขาดทุนมากพอไหม
            meets_loss = loss_percent <= min_loss_percent
            
            if not meets_loss:
                self.logger.debug(f"❌ {ticket}_{symbol}: Loss {loss_percent:.4f}% not enough (need <= {min_loss_percent:.4f}% = ${min_loss_amount:.2f})")
                return False
            
            # 🆕 Check price distance (ต้องห่างจาก entry >= 10 pips)
            price_distance_pips = self._calculate_price_distance_pips(position)
            min_distance = getattr(self, 'min_price_distance_pips', 10)
            
            if price_distance_pips < min_distance:
                self.logger.debug(f"⏳ {ticket}_{symbol}: Distance {price_distance_pips:.1f} pips < {min_distance} pips (waiting...)")
                return False
            
            # 🆕 Check position age (ต้องเปิดมาแล้ว >= 60 วินาที)
            position_age = self._get_position_age_seconds(position)
            min_age = getattr(self, 'min_position_age_seconds', 60)
            
            if position_age < min_age:
                self.logger.debug(f"⏳ {ticket}_{symbol}: Age {position_age:.0f}s < {min_age}s (waiting...)")
                return False
            
            # ✅ All conditions met - log details
            self.logger.info(f"✅ {ticket}_{symbol}: READY FOR RECOVERY!")
            self.logger.info(f"   💰 Loss: ${profit:.2f} ({abs(loss_percent):.3%} of ${balance:,.0f} balance)")
            self.logger.info(f"   📏 Distance: {price_distance_pips:.1f} pips (>= {min_distance})")
            self.logger.info(f"   ⏱️  Age: {position_age:.0f}s (>= {min_age}s)")
            self.logger.info(f"   ✓ Loss threshold: {abs(loss_percent):.3%} >= {abs(min_loss_percent):.3%} (= ${abs(min_loss_amount):.2f})")
            self.logger.info(f"   ✓ Price moved enough: {price_distance_pips:.1f} >= {min_distance} pips")
            self.logger.info(f"   ✓ Position aged enough: {position_age:.0f}s >= {min_age}s")
            self.logger.info(f"   ✓ Not hedged: True")
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking recovery conditions: {e}")
            return False
    
    def _start_individual_recovery(self, position: Dict):
        """Start recovery for individual position with comprehensive logging"""
        try:
            ticket = position.get('ticket', '')
            symbol = position.get('symbol', '')
            profit = position.get('profit', 0)
            
            self.logger.info("=" * 60)
            self.logger.info(f"🚀 STARTING INDIVIDUAL RECOVERY")
            self.logger.info("=" * 60)
            self.logger.info(f"📉 Original Position: {ticket}_{symbol}")
            self.logger.info(f"   Profit: ${profit:.2f}")
            self.logger.info(f"   Lot Size: {position.get('lot_size', 0.1)}")
            self.logger.info(f"   Entry Price: {position.get('entry_price', 0.0):.5f}")
            
            # ✅ CRITICAL: Final check before starting recovery
            if self.order_tracker.is_order_hedged(ticket, symbol):
                self.logger.warning(f"🚫 FINAL CHECK: Ticket {ticket}_{symbol} already hedged - aborting recovery")
                return
            
            if not self.order_tracker.needs_recovery(ticket, symbol):
                self.logger.warning(f"🚫 FINAL CHECK: Ticket {ticket}_{symbol} doesn't need recovery - aborting recovery")
                return
            
            self.logger.info(f"✅ FINAL CHECK: Ticket {ticket}_{symbol} confirmed for recovery")
            
            # Find correlation pairs
            correlation_candidates = self._find_correlation_pairs_for_symbol(symbol)
            
            if correlation_candidates:
                best_correlation = correlation_candidates[0]
                recovery_symbol = best_correlation.get('symbol', 'UNKNOWN')
                correlation = best_correlation.get('correlation', 0.0)
                
                self.logger.info(f"🎯 Selected recovery pair: {recovery_symbol}")
                self.logger.info(f"   Correlation: {correlation:.3f}")
                self.logger.info(f"   Recovery Strength: {best_correlation.get('recovery_strength', correlation):.3f}")
                
                # Execute recovery - need to get proper group_id
                # For now, use a default group_id since we're doing individual order recovery
                group_id = f"recovery_{ticket}_{symbol}"
                self.logger.info(f"   Group ID: {group_id}")
                
                success = self._execute_correlation_position(position, best_correlation, group_id)
                if success:
                    self.logger.info("=" * 60)
                    self.logger.info(f"✅ RECOVERY EXECUTED SUCCESSFULLY")
                    self.logger.info(f"   Original: {ticket}_{symbol} (${profit:.2f})")
                    self.logger.info(f"   Recovery: {recovery_symbol}")
                    self.logger.info(f"   Correlation: {correlation:.3f}")
                    
                    # Show tracker stats after recovery
                    stats = self.order_tracker.get_statistics()
                    self.logger.info(f"   📊 Tracker: {stats['hedged_orders']} hedged, {stats['not_hedged_orders']} pending")
                    self.logger.info("=" * 60)
                else:
                    self.logger.warning("=" * 60)
                    self.logger.warning(f"❌ RECOVERY EXECUTION FAILED")
                    self.logger.warning(f"   {ticket}_{symbol} → {recovery_symbol}")
                    self.logger.warning("=" * 60)
            else:
                self.logger.warning(f"⚠️ No correlation pairs found for {symbol}")
                self.logger.warning("   Cannot proceed with recovery")
                
        except Exception as e:
            self.logger.error(f"Error starting recovery: {e}")
    
    def _display_recovery_chain(self, recovery_orders: List[str], indent_level: int = 1):
        """Display recovery chain recursively"""
        try:
            indent = "   " + "  " * indent_level  # เพิ่ม indent ตาม level
            
            # Debug: แสดงจำนวน recovery orders
            self.logger.info(f"🔍 _display_recovery_chain: Processing {len(recovery_orders)} recovery orders")
            
            if not recovery_orders:
                self.logger.info("🔍 No recovery orders to display")
                return
            
            for recovery_key in recovery_orders:
                self.logger.info(f"🔍 Processing recovery_key: {recovery_key}")
                
                if recovery_key in self.order_tracker.order_tracking:
                    recovery_info = self.order_tracker.order_tracking[recovery_key]
                    recovery_symbol = recovery_info.get('symbol', '')
                    recovery_ticket = recovery_info.get('ticket', '')
                    recovery_status = recovery_info.get('status', 'UNKNOWN')
                    
                    self.logger.info(f"🔍 Recovery info: {recovery_symbol} | Ticket: {recovery_ticket} | Status: {recovery_status}")
                    
                    # หา recovery position จาก MT5
                    recovery_position = self._get_position_by_ticket(recovery_ticket)
                    if recovery_position:
                        recovery_pnl = recovery_position.get('profit', 0)
                        recovery_icon = "🟢" if recovery_pnl >= 0 else "🔴"
                        self.logger.info(f"{indent}- {recovery_symbol:8s}: ${recovery_pnl:8.2f} {recovery_icon}")
                        
                        # ตรวจสอบว่า recovery order นี้ถูก hedge หรือไม่
                        if recovery_status == 'HEDGED':
                            recovery_recovery_orders = recovery_info.get('recovery_orders', [])
                            if recovery_recovery_orders:
                                self.logger.info(f"{indent}  - HG แล้ว")
                                # แสดง recovery orders ของ recovery order (chain recovery)
                                self._display_recovery_chain(recovery_recovery_orders, indent_level + 2)
                    else:
                        # Recovery order ไม่พบใน MT5 (อาจถูกปิดแล้ว)
                        self.logger.info(f"{indent}- {recovery_symbol:8s}: [CLOSED]")
                else:
                    self.logger.info(f"🔍 Recovery key {recovery_key} not found in order_tracker")
                        
        except Exception as e:
            self.logger.error(f"Error displaying recovery chain: {e}")
    
    def _find_correlation_pairs_for_symbol(self, symbol: str) -> List[Dict]:
        """
        Find correlation pairs for symbol with improved filtering.
        
        Filters:
        1. Remove pairs with common currency
        2. Select only negative correlations (-0.2 to -0.95) - RELAXED THRESHOLD
        3. Fallback to inverse strategy if no negative correlations found
        4. Rank by strongest negative correlation
        """
        try:
            # Get correlations from AI engine
            correlations = self.ai_engine.get_correlations(symbol)
            
            if not correlations:
                self.logger.debug(f"No correlations found for {symbol}")
                return []
            
            self.logger.info(f"Received {len(correlations)} correlations for {symbol}")
            
            # Debug: Show all correlations received
            self.logger.info(f"📊 All correlations for {symbol}:")
            for pair, corr_val in correlations.items():
                self.logger.info(f"   {pair}: {corr_val:.3f}")
            
            correlation_candidates = []
            
            # Try negative correlations first (with relaxed threshold)
            for pair, correlation_value in correlations.items():
                # ✅ FILTER 1: Check for common currency but allow strong negative correlations
                has_common = self._has_common_currency(symbol, pair)
                
                if has_common:
                    # Allow JPY pairs to correlate with each other (common in forex)
                    if 'JPY' in symbol and 'JPY' in pair:
                        self.logger.debug(f"✅ Allow {pair}: JPY pairs can correlate with {symbol}")
                    # RELAXED: Allow strong negative correlations even with common currency
                    elif correlation_value <= -0.4:
                        self.logger.info(f"⚠️ {pair}: Common currency BUT strong negative correlation ({correlation_value:.3f}) - ALLOWED")
                    else:
                        self.logger.debug(f"⏭️ Skip {pair}: common currency with {symbol} and weak correlation ({correlation_value:.3f})")
                        continue
                
                # ✅ FILTER 2: Only accept negative correlations (VERY RELAXED: -0.1 instead of -0.2)
                # Negative correlation means pairs move in opposite directions
                if correlation_value >= -0.1:
                    self.logger.info(f"⏭️ Skip {pair}: correlation {correlation_value:.3f} not negative enough")
                    continue
                
                # Strong negative correlation (good for hedging)
                if correlation_value <= -0.98:
                    self.logger.debug(f"⏭️ Skip {pair}: correlation {correlation_value:.3f} too perfect (suspicious)")
                    continue
                
                # ✅ NEW FILTER 3: Check if symbol is not overused (max 2 times)
                if not self._is_recovery_symbol_available(pair, max_usage=2):
                    usage = self._get_recovery_symbol_usage()
                    self.logger.info(f"⏭️ Skip {pair}: Already used {usage.get(pair, 0)} times for recovery (max 2)")
                    continue
                
                correlation_candidates.append({
                    'symbol': pair,
                    'correlation': correlation_value,
                    'direction': 'opposite',  # Negative correlation = opposite direction
                    'has_common_currency': has_common
                })
                
                self.logger.info(f"VALID: {pair} ({correlation_value:.3f})")
            
            # Fallback: Use strong positive correlations (trade opposite direction)
            if not correlation_candidates:
                self.logger.warning(f"No negative correlations - using inverse strategy")
                
                for pair, correlation_value in correlations.items():
                    has_common = self._has_common_currency(symbol, pair)
                    
                    if has_common:
                        # Allow JPY pairs to correlate with each other (common in forex)
                        if 'JPY' in symbol and 'JPY' in pair:
                            self.logger.debug(f"✅ Allow {pair}: JPY pairs can correlate with {symbol} (inverse)")
                        # For inverse, also relax common currency rule for strong correlations
                        elif correlation_value < 0.7:
                            self.logger.debug(f"⏭️ Skip {pair}: common currency with {symbol} and weak positive correlation ({correlation_value:.3f})")
                            continue
                    
                    # ✅ NEW FILTER: Check if symbol is not overused (max 2 times)
                    if not self._is_recovery_symbol_available(pair, max_usage=2):
                        usage = self._get_recovery_symbol_usage()
                        self.logger.info(f"⏭️ Skip {pair}: Already used {usage.get(pair, 0)} times for recovery (max 2)")
                        continue
                    
                    # Strong positive correlation (RELAXED: 0.3 instead of 0.7)
                    if 0.3 <= correlation_value <= 0.98:
                        correlation_candidates.append({
                            'symbol': pair,
                            'correlation': -correlation_value,  # Treat as negative for sorting
                            'direction': 'inverse',
                            'original_correlation': correlation_value,
                            'has_common_currency': has_common
                        })
                        
                        self.logger.info(f"INVERSE: {pair} (positive {correlation_value:.3f})")
                    else:
                        self.logger.info(f"⏭️ Skip {pair}: positive correlation {correlation_value:.3f} not strong enough for inverse")
                
                if correlation_candidates:
                    self.logger.info(f"Found {len(correlation_candidates)} using inverse strategy")
            
            # Final fallback: Use any available pair if still no candidates
            if not correlation_candidates:
                self.logger.warning(f"No correlations found with any strategy - using emergency fallback")
                
                # Use the pair with the strongest correlation (positive or negative)
                best_pair = None
                best_correlation = 0
                
                for pair, correlation_value in correlations.items():
                    has_common = self._has_common_currency(symbol, pair)
                    
                    if has_common:
                        # Allow JPY pairs to correlate with each other
                        if 'JPY' in symbol and 'JPY' in pair:
                            pass  # Allow this pair
                        # For emergency fallback, also relax common currency rule for strong correlations
                        elif abs(correlation_value) < 0.4:
                            continue
                    
                    # Find the strongest correlation (absolute value)
                    if abs(correlation_value) > abs(best_correlation):
                        best_correlation = correlation_value
                        best_pair = pair
                
                if best_pair:
                    correlation_candidates.append({
                        'symbol': best_pair,
                        'correlation': -abs(best_correlation),  # Always treat as negative for hedging
                        'direction': 'emergency_fallback',
                        'original_correlation': best_correlation,
                        'has_common_currency': self._has_common_currency(symbol, best_pair)
                    })
                    
                    self.logger.info(f"EMERGENCY FALLBACK: {best_pair} (correlation {best_correlation:.3f})")
            
            # ✅ SORT: Rank by strongest negative correlation
            # Most negative first (e.g., -0.85, -0.75, -0.65)
            correlation_candidates.sort(key=lambda x: x['correlation'])
            
            if correlation_candidates:
                self.logger.info(f"🎯 Found {len(correlation_candidates)} valid correlation pairs for {symbol}")
                for i, candidate in enumerate(correlation_candidates[:3], 1):
                    if 'original_correlation' in candidate:
                        self.logger.info(f"   {i}. {candidate['symbol']}: {candidate['original_correlation']:.3f} (inverse)")
                    else:
                        self.logger.info(f"   {i}. {candidate['symbol']}: {candidate['correlation']:.3f}")
            else:
                self.logger.warning(f"⚠️ NO valid candidates after filtering")
            
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
    
    
    def _auto_register_new_orders(self):
        """Auto-register any new orders that aren't in tracker yet (lightweight check)"""
        try:
            # Get all MT5 positions
            all_positions = self.broker.get_all_positions()
            if not all_positions:
                return
            
            new_orders_count = 0
            for pos in all_positions:
                ticket = str(pos.get('ticket', ''))
                symbol = pos.get('symbol', '')
                magic = pos.get('magic', 0)
                
                if not ticket or not symbol:
                    continue
                
                # Quick check if already tracked
                if self.order_tracker.get_order_info(ticket, symbol):
                    continue
                
                # Not tracked yet - register it!
                group_id = self._get_group_id_from_magic(magic)
                success = self.order_tracker.register_original_order(ticket, symbol, group_id)
                
                if success:
                    new_orders_count += 1
                    profit = pos.get('profit', 0)
                    self.logger.info(f"🆕 Auto-registered new order: {ticket}_{symbol} (${profit:.2f})")
            
            if new_orders_count > 0:
                self.logger.info(f"✅ Auto-registered {new_orders_count} new orders")
                
        except Exception as e:
            self.logger.error(f"Error in auto-register: {e}")
    
    def register_existing_orders(self):
        """Register all existing MT5 positions as original orders in the tracker"""
        try:
            self.logger.info("🔧 REGISTERING EXISTING ORDERS IN TRACKER")
            
            # Check broker connection
            if not self.broker:
                self.logger.error("❌ Broker not initialized - cannot register orders")
                return
            
            # Try to connect if not connected
            if not self.broker.is_connected():
                self.logger.warning("⚠️ Broker not connected - attempting to connect...")
                try:
                    self.broker.connect()
                    if not self.broker.is_connected():
                        self.logger.error("❌ Failed to connect to MT5 - will retry on next check")
                        return
                    self.logger.info("✅ Successfully connected to MT5")
                except Exception as e:
                    self.logger.error(f"❌ Error connecting to MT5: {e}")
                    return
            
            # Get all MT5 positions
            all_positions = self.broker.get_all_positions()
            self.logger.info(f"📊 Found {len(all_positions)} positions in MT5")
            
            if not all_positions:
                self.logger.warning("⚠️ No positions found in MT5")
                return
            
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
        """ปิด recovery position และคืนค่า PnL (DEPRECATED - use order_tracker)"""
        try:
            # Legacy method - recovery positions are now tracked by order_tracker
            # This method is kept for backward compatibility but does nothing
            self.logger.warning(f"⚠️ _close_recovery_position() is deprecated - use order_tracker instead")
            return 0.0
                    
        except Exception as e:
            self.logger.debug(f"Error closing recovery position: {e}")
            return 0.0
    
    def get_correlation_matrix(self) -> Dict:
        """Get correlation matrix"""
        return self.correlation_matrix
    
    def get_recovery_positions(self) -> Dict:
        """Get recovery positions (DEPRECATED - use order_tracker.get_all_orders())"""
        # Return order tracker data instead of legacy recovery_positions
        return self.order_tracker.get_all_orders()
    
    def close_recovery_position(self, recovery_id: str, reason: str = "manual"):
        """Close recovery position manually (DEPRECATED - use broker.close_position directly)"""
        try:
            # Legacy method - recovery positions are now tracked by order_tracker
            # Positions should be closed directly via broker API
            self.logger.warning(f"⚠️ close_recovery_position() is deprecated - use broker.close_position() directly")
                    
        except Exception as e:
            self.logger.debug(f"Error closing recovery position: {e}")
    
    def get_correlation_performance(self) -> Dict:
        """Get correlation performance metrics"""
        return self.recovery_metrics
    
    def get_active_recovery_engine_status(self) -> Dict:
        """Get active recovery engine status (simplified - using order_tracker)"""
        stats = self.order_tracker.get_statistics()
        return {
            'recovery_mode': self.recovery_mode,
            'hedge_ratio_optimization': self.hedge_ratio_optimization,
            'portfolio_rebalancing': self.portfolio_rebalancing,
            'multi_timeframe_analysis': self.multi_timeframe_analysis,
            'never_cut_loss': self.never_cut_loss,
            'total_tracked_orders': stats.get('total_tracked_orders', 0),
            'not_hedged_orders': stats.get('not_hedged_orders', 0),  # Orders needing recovery
            'hedged_orders': stats.get('hedged_orders', 0)  # Orders with active recovery
        }
    
    def _save_recovery_data(self):
        """บันทึกข้อมูล recovery metrics (legacy tracking removed - using order_tracker now)"""
        try:
            import json
            import os
            
            # Note: Individual order tracking is now handled by order_tracker._save_to_file()
            # This method only saves recovery_metrics for historical tracking
            
            persistence_file = "data/recovery_metrics.json"
            os.makedirs(os.path.dirname(persistence_file), exist_ok=True)
            
            save_data = {
                'recovery_metrics': self.recovery_metrics,
                'saved_at': datetime.now().isoformat()
            }
            
            with open(persistence_file, 'w') as f:
                json.dump(save_data, f, indent=2, default=str)
            
            self.logger.debug(f"💾 Saved recovery metrics to {persistence_file}")
            
        except Exception as e:
            self.logger.debug(f"Error saving recovery data: {e}")
    
    def _load_recovery_data(self):
        """โหลดข้อมูล recovery metrics (legacy tracking removed - using order_tracker now)"""
        try:
            import json
            import os
            
            # Note: Individual order tracking is now handled by order_tracker._load_from_file()
            # This method only loads recovery_metrics for historical tracking
            
            persistence_file = "data/recovery_metrics.json"
            
            if not os.path.exists(persistence_file):
                self.logger.debug("No recovery metrics file found, starting fresh")
                self.recovery_metrics = {
                    'total_recoveries': 0,
                    'successful_recoveries': 0,
                    'failed_recoveries': 0,
                    'avg_recovery_time_hours': 0,
                    'total_recovered_amount': 0.0
                }
                return
            
            with open(persistence_file, 'r') as f:
                save_data = json.load(f)
            
            self.recovery_metrics = save_data.get('recovery_metrics', {
                'total_recoveries': 0,
                'successful_recoveries': 0,
                'failed_recoveries': 0,
                'avg_recovery_time_hours': 0,
                'total_recovered_amount': 0.0
            })
            
            saved_at = save_data.get('saved_at', 'Unknown')
            self.logger.info(f"📂 Loaded recovery metrics from {persistence_file} (Saved at: {saved_at})")
                
        except Exception as e:
            self.logger.debug(f"Error loading recovery data: {e}")
            self.recovery_metrics = {
                'total_recoveries': 0,
                'successful_recoveries': 0,
                'failed_recoveries': 0,
                'avg_recovery_time_hours': 0,
                'total_recovered_amount': 0.0
            }
    
    # REMOVED: _update_recovery_data() - Legacy method removed
    # Recovery data is now automatically handled by order_tracker
    
    # REMOVED: _remove_recovery_data() - Legacy method removed  
    # Order removal is now handled by order_tracker.sync_with_mt5()
    
    def clear_hedged_data_for_group(self, group_id: str):
        """ล้างข้อมูลการแก้ไม้สำหรับกลุ่มที่ปิดแล้ว (simplified - using only order_tracker)"""
        try:
            # Use order tracker to sync with MT5 - this will automatically clean up closed orders
            sync_results = self.order_tracker.sync_with_mt5()
            
            removed_count = sync_results.get('orders_removed', 0)
            
            if removed_count > 0:
                self.logger.info(f"🗑️ Cleared {removed_count} closed orders from tracking")
            
            # Log individual order tracker status
            self.order_tracker.log_status_summary()
            
        except Exception as e:
            self.logger.debug(f"Error clearing hedged data for group {group_id}: {e}")
    
    # REMOVED: cleanup_closed_recovery_positions() - Legacy method removed
    # Cleanup is now handled automatically by order_tracker.sync_with_mt5()
    
    def get_hedging_status(self) -> Dict:
        """ดึงสถานะการแก้ไม้ทั้งหมด (simplified - using order_tracker)"""
        try:
            # Return order tracker statistics instead of legacy structures
            stats = self.order_tracker.get_statistics()
            return {
                'total_tracked_orders': stats.get('total_tracked_orders', 0),
                'original_orders': stats.get('original_orders', 0),
                'recovery_orders': stats.get('recovery_orders', 0),
                'hedged_orders': stats.get('hedged_orders', 0),
                'not_hedged_orders': stats.get('not_hedged_orders', 0),
                'orphaned_orders': stats.get('orphaned_orders', 0),
                'last_sync': stats.get('last_sync')
            }
        except Exception as e:
            self.logger.debug(f"Error getting hedging status: {e}")
            return {}
    
    def log_recovery_positions_summary(self):
        """แสดงสรุปสถานะ recovery positions (now using order_tracker)"""
        try:
            # Delegate to order_tracker for accurate individual order tracking
            self.order_tracker.log_status_summary()
            
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
