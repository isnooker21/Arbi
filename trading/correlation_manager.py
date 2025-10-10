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
from typing import Dict, List, Tuple, Optional, Set
import threading
import os
import sys

# Ensure project root is on sys.path when running this module directly
try:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if PROJECT_ROOT not in sys.path:
        sys.path.append(PROJECT_ROOT)
except Exception:
    pass

# Removed AccountTierManager - using GUI Risk per Trade only
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
                self.logger.warning(f"⚠️ Unknown group_id format: '{group_id}' → using default magic 234000")
                return 234000  # default
        except Exception as e:
            self.logger.error(f"Error getting magic number from group_id {group_id}: {e}")
            return 234000  # return default on error
    
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
            # ใช้ predefined list เพื่อให้มีคู่เงินครบถ้วน (Expanded for Correlation Trading!)
            all_pairs = [
                # Major Pairs (USD-based)
                'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD',
                
                # EUR Crosses
                'EURGBP', 'EURJPY', 'EURCHF', 'EURAUD', 'EURCAD', 'EURNZD',
                
                # GBP Crosses
                'GBPJPY', 'GBPCHF', 'GBPAUD', 'GBPCAD', 'GBPNZD',
                
                # JPY Crosses
                'AUDJPY', 'CADJPY', 'CHFJPY', 'NZDJPY',
                
                # AUD Crosses
                'AUDCAD', 'AUDCHF', 'AUDNZD',
                
                # NZD Crosses
                'NZDCAD', 'NZDCHF',
                
                # CAD Crosses
                'CADCHF'
            ]
            
            # ลบคู่ที่ซ้ำ
            all_pairs = list(set(all_pairs))
            all_pairs.sort()
            
            self.logger.debug(f"📊 All currency pairs available: {len(all_pairs)} pairs")
            return all_pairs
            
        except Exception as e:
            self.logger.error(f"Error getting all currency pairs: {e}")
            # Fallback to comprehensive list if error (28 pairs total!)
            return [
                # Major Pairs
                'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD',
                # EUR Crosses
                'EURGBP', 'EURJPY', 'EURCHF', 'EURAUD', 'EURCAD', 'EURNZD',
                # GBP Crosses
                'GBPJPY', 'GBPCHF', 'GBPAUD', 'GBPCAD', 'GBPNZD',
                # JPY Crosses
                'AUDJPY', 'CADJPY', 'CHFJPY', 'NZDJPY',
                # AUD Crosses
                'AUDCAD', 'AUDCHF', 'AUDNZD',
                # NZD Crosses
                'NZDCAD', 'NZDCHF',
                # CAD Crosses
                'CADCHF'
            ]
    
    def _is_recovery_comment(self, comment: str) -> bool:
        """
        เช็คว่า comment เป็น recovery order ไหม
        รองรับหลาย format:
        - 'RECOVERY_...'  (legacy format)
        - 'R...'          (short format)
        - ที่มีคำว่า 'RECOVERY' อยู่ในนั้น
        """
        if not comment:
            return False
        return (comment.startswith('RECOVERY_') or 
                comment.startswith('R') or
                'RECOVERY' in comment.upper())
    
    def __init__(self, broker_api, ai_engine=None, symbol_mapper=None):
        self.broker = broker_api
        self.ai_engine = ai_engine  # ✅ Enable AI engine for correlation data
        self.symbol_mapper = symbol_mapper  # 🆕 Symbol Mapper for translating pair names
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
        
        # 🤖 ML-Ready Systems (Optional - won't break if disabled)
        try:
            from data.ml_logger import MLRecoveryLogger
            from data.pair_selector_bandit import PairSelectorBandit
            
            ml_logging_enabled = getattr(self, 'ml_logging_enabled', True)
            bandit_enabled = getattr(self, 'bandit_enabled', True)
            
            if ml_logging_enabled:
                self.ml_logger = MLRecoveryLogger()
                self.logger.info("🤖 ML Logger initialized")
            else:
                self.ml_logger = None
                
            if bandit_enabled:
                self.pair_bandit = PairSelectorBandit(
                    exploration_rate=getattr(self, 'bandit_exploration_rate', 0.2),
                    learning_rate=getattr(self, 'bandit_learning_rate', 0.1)
                )
                self.logger.info("🎰 Multi-Armed Bandit initialized")
            else:
                self.pair_bandit = None
                
        except Exception as e:
            self.logger.warning(f"⚠️ ML systems not available: {e}")
            self.ml_logger = None
            self.pair_bandit = None
        
        # Log startup completion
        self.logger.info("🚀 Individual Order Tracker initialized")
        self.order_tracker.log_status_summary()
        
        # Auto-register existing orders on startup (DISABLED - to avoid registering old orders)
        # self.logger.info("🔧 Auto-registering existing MT5 positions...")
        # try:
        #     self.register_existing_orders()
        # except Exception as e:
        #     self.logger.error(f"❌ Error in auto-registration: {e}")
        #     import traceback
        #     self.logger.error(f"Traceback: {traceback.format_exc()}")
        
        self.logger.info("ℹ️ Auto-registration disabled - only new orders will be tracked")
        
        # 🆕 Clear old order tracking data on startup (optional)
        # Uncomment the line below if you want to start fresh
        # self.clear_old_order_tracking()
        
        # 🆕 Reset order tracker to match real MT5 positions (recommended)
        # Uncomment the line below to reset tracker to match real positions
        # self.reset_tracker_to_match_mt5()
        
        # 🆕 Enable auto-registration if needed (optional)
        # Uncomment the line below if you want to auto-register new orders
        # self._enable_auto_registration()
        
        self.logger.info("✅ CorrelationManager initialization completed")
    
    def _load_config_from_file(self):
        """โหลดการตั้งค่าจาก config file"""
        try:
            import json
            import os
            # โหลด config โดยตรง
            try:
                import json
                with open('config/adaptive_params.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception:
                # Fallback to direct path if helper unavailable
                config_path = 'config/adaptive_params.json'
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                else:
                    config = {}
                
            # โหลด recovery parameters
            recovery_params = config.get('recovery_params', {})
            correlation_thresholds = recovery_params.get('correlation_thresholds', {})
            loss_thresholds = recovery_params.get('loss_thresholds', {})
            hedge_ratios = recovery_params.get('hedge_ratios', {})
            timing = recovery_params.get('timing', {})
            
            # โหลด position sizing จาก config
            position_sizing = config.get('position_sizing', {})
            lot_calc = position_sizing.get('lot_calculation', {})
            risk_mgmt = position_sizing.get('risk_management', {})
            
            # ⭐ โหลด risk_per_trade_percent สำหรับการคำนวณ lot อัตโนมัติ
            self.use_risk_based_sizing = lot_calc.get('use_risk_based_sizing', True)
            self.risk_per_trade_percent = lot_calc.get('risk_per_trade_percent')
            if self.risk_per_trade_percent is None:
                raise ValueError("❌ risk_per_trade_percent not found in config - must be set in GUI Settings")
            
            
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
                'base_lot_size': lot_calc.get('base_lot_size'),  # ⭐ ไม่มี fallback - ต้องมี config
                'risk_per_trade_percent': self.risk_per_trade_percent  # ⭐ เพิ่ม risk_per_trade_percent
            }
            
            # โหลด diversification settings
            diversification = recovery_params.get('diversification', {})
            self.max_symbol_usage = diversification.get('max_usage_per_symbol', 3)
            
            # โหลด chain recovery settings (% based)
            chain_recovery = recovery_params.get('chain_recovery', {})
            self.chain_recovery_enabled = chain_recovery.get('enabled', True)
            self.max_chain_depth = chain_recovery.get('max_chain_depth', 3)
            self.min_loss_percent_for_chain = chain_recovery.get('min_loss_percent_for_chain', -1.0)  # 1% of balance
            
            # โหลด price distance และ position age
            self.min_price_distance_pips = loss_thresholds.get('min_price_distance_pips', 10)
            self.min_position_age_seconds = timing.get('min_position_age_seconds', 60)
            
            # โหลด trend analysis settings
            trend_settings = recovery_params.get('trend_analysis', {})
            self.trend_analysis_enabled = trend_settings.get('enabled', True)
            self.trend_periods = trend_settings.get('periods', 50)
            self.trend_confidence_threshold = trend_settings.get('confidence_threshold', 0.4)
            self.enable_chain_on_low_confidence = trend_settings.get('enable_chain_on_low_confidence', True)
            
            # โหลด ML logging settings
            ml_settings = recovery_params.get('ml_logging', {})
            self.ml_logging_enabled = ml_settings.get('enabled', True)
            self.log_market_features = ml_settings.get('log_market_features', True)
            
            # โหลด multi-armed bandit settings
            bandit_settings = recovery_params.get('multi_armed_bandit', {})
            self.bandit_enabled = bandit_settings.get('enabled', True)
            self.bandit_exploration_rate = bandit_settings.get('exploration_rate', 0.2)
            self.bandit_learning_rate = bandit_settings.get('learning_rate', 0.1)
            
            # โหลด chain recovery settings
            chain_settings = recovery_params.get('chain_recovery', {})
            self.chain_recovery_enabled = chain_settings.get('enabled', True)
            self.chain_recovery_mode = chain_settings.get('mode', 'conditional')
            self.max_chain_depth = chain_settings.get('max_chain_depth', 2)
            self.min_loss_percent_for_chain = chain_settings.get('min_loss_percent_for_chain', -1.0)
            self.chain_only_when_trend_uncertain = chain_settings.get('only_when_trend_uncertain', True)
            
            # โหลด risk management parameters
            risk_mgmt = config.get('position_sizing', {}).get('risk_management', {})
            # ⭐ ลบ portfolio_balance_threshold - ใช้แค่ risk_per_trade เท่านั้น
            # self.portfolio_balance_threshold = risk_mgmt.get('max_portfolio_risk', 0.05)
            self.max_concurrent_groups = risk_mgmt.get('max_concurrent_groups', 4)
            
            # ⭐ ใช้ risk-based calculation แทน fixed min/max hedge lot
            
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
                self.logger.info(f"   Min Loss for Chain: {abs(self.min_loss_percent_for_chain):.0%} of balance")
                for bal in [5000, 10000, 50000]:
                    amount = bal * self.min_loss_percent_for_chain
                    self.logger.info(f"   - Balance ${bal:,}: >= ${abs(amount):.2f}")
            
            # แสดง ML systems status
            if self.trend_analysis_enabled:
                self.logger.info(f"📈 Trend Analysis: ENABLED (confidence threshold: {self.trend_confidence_threshold:.1%})")
            if self.ml_logging_enabled:
                self.logger.info(f"🤖 ML Logging: ENABLED (ready for training)")
            if self.bandit_enabled:
                self.logger.info(f"🎰 Pair Bandit: ENABLED (explore: {self.bandit_exploration_rate:.1%})")
            
            self.logger.info(f"📦 Hedge Ratio: {self.recovery_thresholds['hedge_ratio_range'][0]} - {self.recovery_thresholds['hedge_ratio_range'][1]}")
            self.logger.info(f"🎯 Max Symbol Usage: {self.max_symbol_usage} times")
            self.logger.info(f"📏 Base Lot Size: {self.recovery_thresholds['base_lot_size']}")
            self.logger.info(f"🔧 Recovery Lot: ใช้ Risk-Based Calculation (ตาม risk_per_trade_percent)")
            self.logger.info(f"⚙️ System Limits: Max Groups {self.max_concurrent_groups} (ใช้แค่ Risk per Trade)")
            self.logger.info(f"⭐ Risk-Based Sizing: {'ENABLED' if self.use_risk_based_sizing else 'DISABLED'}")
            if self.use_risk_based_sizing:
                self.logger.info(f"💰 Risk Per Trade: {self.risk_per_trade_percent}% of balance")
                self.logger.info(f"   Examples (with 100 pips risk):")
                for bal in [5000, 10000, 50000, 100000]:
                    # คำนวณ lot โดยประมาณ
                    risk_amount = bal * (self.risk_per_trade_percent / 100)
                    approx_lot = risk_amount / (10 * 100)  # pip_value ~$10, 100 pips
                    self.logger.info(f"   - Balance ${bal:,}: ~{approx_lot:.2f} lot")
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"❌ Error loading config: {e}")
            self.logger.info("🔄 Using fallback configuration")
            self._set_fallback_config()
    
    def _set_fallback_config(self):
        """ตั้งค่า fallback เมื่อไม่สามารถโหลด config ได้ (% based)"""
        # ⭐ ไม่มี fallback - ต้องมี config
        raise ValueError("❌ Cannot initialize without config - GUI Settings required")
        
        self.recovery_thresholds = {
            'min_correlation': 0.6,      # ความสัมพันธ์ขั้นต่ำ 60%
            'max_correlation': 0.95,     # ความสัมพันธ์สูงสุด 95%
            'min_loss_percent': -0.005,  # ขาดทุนขั้นต่ำ -0.5% ของ balance (% based)
            'use_percentage_based': True, # ใช้ % based
            'max_recovery_time_hours': 24, # เวลาสูงสุด 24 ชั่วโมง
            'hedge_ratio_range': (0.7, 1.3),  # ขนาด hedge ratio
            'wait_time_minutes': 5,      # รอ 5 นาทีก่อนแก้ไม้
            'cooldown_between_checks': 10,  # เช็คทุก 10 วินาที
            'base_lot_size': 0.05,       # ขนาด lot เริ่มต้น
            'risk_per_trade_percent': self.risk_per_trade_percent  # ⭐ เพิ่ม risk_per_trade_percent
        }
        
        # Diversification settings
        self.max_symbol_usage = 3  # ใช้ symbol เดียวกันได้สูงสุด 3 ครั้ง
        
        # Chain recovery settings (% based)
        self.chain_recovery_enabled = True  # เปิด chain recovery
        self.max_chain_depth = 3  # แก้ได้ลึกสุด 3 ระดับ
        self.min_loss_percent_for_chain = -1.0  # Recovery ต้องขาดทุน >= 1% ของ balance
        
        # Price distance และ position age
        self.min_price_distance_pips = 10  # ต้องห่าง >= 10 pips
        self.min_position_age_seconds = 60  # ต้องเปิดมา >= 60 วินาที
        
        # ⭐ ลบ portfolio_balance_threshold - ใช้แค่ risk_per_trade เท่านั้น
        # self.portfolio_balance_threshold = 0.05  # 5% imbalance threshold
        
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
                
                # ข้าม recovery positions (รองรับหลาย format)
                if self._is_recovery_comment(comment):
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
                    if pos.get('magic', 0) == magic and self._is_recovery_comment(pos.get('comment', '')):
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
                if magic == magic_number and not self._is_recovery_comment(comment) and pnl < 0:
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
                # คำนวณ loss percent ของ balance
                balance = self.broker.get_account_balance()
                if not balance:
                    continue
                loss_percent_of_balance = abs(pnl) / balance
                price_distance = self._calculate_price_distance(pos)
                
                # ผ่านเงื่อนไข Distance ≥ 10 pips
                if price_distance >= 10:
                    suitable_pairs.append({
                        'pair': pos,
                        'symbol': symbol,
                        'order_id': order_id,
                        'pnl': pnl,
                        'loss_percent_of_balance': loss_percent_of_balance,
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
                elif magic == 234000 and self._is_recovery_comment(comment):
                    # Recovery orders ที่มี default magic (234000)
                    recovery_positions_all.append(pos)
                elif self._is_recovery_comment(comment):
                    # Recovery orders ที่มี magic number อื่นๆ
                    recovery_positions_all.append(pos)
            
            # แสดงสถานะแต่ละ Group เรียงตาม Group
            for magic in sorted(groups_data.keys()):
                group_number = self._get_group_number_from_magic(magic)
                group_positions = groups_data[magic]
                
                # แยกประเภทไม้ (รองรับทั้ง 'RECOVERY_' และ 'R' format)
                arbitrage_positions = [pos for pos in group_positions if not self._is_recovery_comment(pos.get('comment', ''))]
                recovery_positions = [pos for pos in group_positions if self._is_recovery_comment(pos.get('comment', ''))]
                
                # เพิ่ม recovery orders ที่มี magic number เดียวกับ group นี้
                # (recovery orders ใช้ magic number เดียวกับ group แต่มี comment ขึ้นต้นด้วย 'R')
                for recovery_pos in recovery_positions_all:
                    recovery_magic = recovery_pos.get('magic', 0)
                    recovery_comment = recovery_pos.get('comment', '')
                    
                    # Case 1: Magic number ตรงกัน
                    if recovery_magic == magic:
                        if recovery_pos not in recovery_positions:
                            recovery_positions.append(recovery_pos)
                    # Case 2: Magic = 234000 (default) → ใช้ comment เพื่อหา original ticket
                    elif recovery_magic == 234000 and recovery_comment.startswith('R'):
                        # Comment format: R{ticket}_{symbol}
                        try:
                            # Extract original ticket from comment
                            ticket_part = recovery_comment.split('_')[0][1:]  # Remove 'R' prefix
                            
                            # Find original position with this ticket
                            for orig_pos in all_positions:
                                if str(orig_pos.get('ticket', '')).endswith(ticket_part):
                                    if orig_pos.get('magic', 0) == magic:
                                        # Original position is in this group!
                                        if recovery_pos not in recovery_positions:
                                            recovery_positions.append(recovery_pos)
                                        break
                        except Exception as e:
                            self.logger.debug(f"Could not parse recovery comment: {recovery_comment}")
                
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
                                
                                
                                # แสดงโซ่การแก้ไม้แบบหลายชั้น (recursive)
                                if recovery_orders:
                                    self._display_recovery_chain(
                                        recovery_orders,
                                        parent_symbol=symbol,
                                        parent_ticket=ticket,
                                        indent_level=2,
                                        visited=set()
                                    )
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
    
    # ฟังก์ชันนี้ถูกลบออกแล้ว - ใช้ calculate_lot_from_balance แทน
    
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
            # ✅ NEW FORMAT: Check comment pattern "R{ticket}_{symbol}"
            # Example: R3317086_EURUSD
            
            # แยก comment เพื่อหา original symbol
            if comment.startswith('R') and '_' in comment:
                # รูปแบบใหม่: R3317086_EURUSD
                if original_symbol in comment:
                    self.logger.info(f"✅ Recovery suitable: {original_symbol} -> {recovery_symbol} (new format)")
                    return True
            
            # Legacy support: Old format (RECOVERY_G{group}_{symbol})
            if 'RECOVERY_' in comment and original_symbol in comment:
                self.logger.info(f"✅ Recovery suitable: {original_symbol} -> {recovery_symbol} (legacy format)")
                return True
            
            self.logger.info(f"❌ Recovery not suitable: {original_symbol} -> {recovery_symbol} (comment: {comment})")
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking recovery suitability: {e}")
            return False
    
    # ฟังก์ชันนี้ถูกลบออกแล้ว - ไม่ใช้แล้ว
    
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
            
            # 🆕 แปลง symbol ผ่าน mapper
            real_symbol = self.symbol_mapper.get_real_symbol(symbol) if self.symbol_mapper else symbol
            
            # ดึงราคาปัจจุบัน
            current_price = self.broker.get_current_price(real_symbol)
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
            # คำนวณ loss percent ของ balance
            balance = self.broker.get_account_balance()
            if not balance:
                self.logger.error("❌ Cannot get account balance from MT5 - skipping hedge check")
                return
            loss_percent_of_balance = abs(pnl) / balance
            price_distance = self._calculate_price_distance(losing_pair)
            
            self.logger.debug(f"🔍 Checking hedging conditions for {symbol} (Order: {order_id}):")
            self.logger.info(f"   PnL: ${pnl:.2f} (LOSS)")
            self.logger.info(f"   Loss: {loss_percent_of_balance:.2%} of balance")
            self.logger.info(f"   Distance: {price_distance:.1f} pips (need ≥10) {'✅' if price_distance >= 10 else '❌'}")
            
            # แสดงข้อมูลการคำนวณให้ชัดเจน
            if price_distance == 0.0:
                self.logger.warning(f"   ⚠️ Price distance is 0.0 - checking calculation...")
                # ดึงข้อมูลจาก broker อีกครั้งเพื่อ debug
                all_positions = self.broker.get_all_positions()
                for pos in all_positions:
                    if pos['ticket'] == order_id:
                        entry_price = pos.get('price', 0.0)  # ใช้ 'price' แทน 'price_open'
                        # 🆕 แปลง symbol ผ่าน mapper
                        real_symbol = self.symbol_mapper.get_real_symbol(symbol) if self.symbol_mapper else symbol
                        current_price = self.broker.get_current_price(real_symbol)
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
        """⭐ ใช้ระบบใหม่เท่านั้น - TradingCalculations.calculate_lot_from_balance"""
        try:
            from utils.calculations import TradingCalculations
            
            # ดึง balance จาก broker
            balance = self.broker.get_account_balance()
            if not balance:
                self.logger.error("❌ Cannot get account balance from MT5 - skipping hedge calculation")
                return 0.0
            
            # คำนวณ pip value สำหรับ hedge symbol
            pip_value = TradingCalculations.calculate_pip_value(hedge_symbol, 1.0, self.broker)
            if pip_value <= 0:
                self.logger.error(f"❌ Invalid pip value for {hedge_symbol} - skipping hedge calculation")
                return 0.0
            
            # ⭐ ใช้ระบบใหม่เท่านั้น - Risk-Based Sizing
            hedge_lot = TradingCalculations.calculate_lot_from_balance(
                balance=balance,
                pip_value=pip_value,
                risk_percent=self.risk_per_trade_percent,
                max_loss_pips=100.0
            )
            
            # ⭐ ไม่ปรับตาม correlation - ใช้ lot size ที่คำนวณจาก risk เท่านั้น
            
            # Round to valid lot size
            hedge_lot = TradingCalculations.round_to_valid_lot_size(hedge_lot)
            
            self.logger.info(f"💰 Risk-Based Hedge Calculation:")
            self.logger.info(f"   Balance: ${balance:.2f}")
            self.logger.info(f"   Risk: {self.risk_per_trade_percent}%")
            self.logger.info(f"   Correlation: {abs(correlation):.3f}")
            self.logger.info(f"   Hedge Lot: {hedge_lot:.4f}")
            
            return float(hedge_lot)
            
        except Exception as e:
            self.logger.error(f"❌ Error in risk-based hedge calculation: {e}")
            return 0.0
    
    # REMOVED: _send_hedge_order() - Legacy method removed
    # This method created old comment format: "RECOVERY_G{group}_{symbol}_L{level}"
    # Now using _send_correlation_order() exclusively with format: "R{ticket}_{symbol}"
    
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
            
            # เงื่อนไข 1: Risk 1% ของ balance
            balance = self.broker.get_account_balance()
            if not balance or balance <= 0:
                self.logger.debug(f"🔍 {symbol}: Cannot get account balance")
                return False
            
            loss_percent_of_balance = abs(position_pnl) / balance
            
            if loss_percent_of_balance < 0.01:  # loss น้อยกว่า 1% ของ balance
                self.logger.debug(f"⏳ {symbol} loss too low ({loss_percent_of_balance:.1%} of balance) - Waiting for 1%")
                return False
            
            # เงื่อนไข 2: ระยะห่าง 10 pips
            entry_price = recovery_pair.get('entry_price', 0)
            if entry_price > 0:
                try:
                    # 🆕 แปลง symbol ผ่าน mapper
                    real_symbol = self.symbol_mapper.get_real_symbol(symbol) if self.symbol_mapper else symbol
                    current_price = self.broker.get_current_price(real_symbol)
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
            self.logger.info(f"✅ {symbol} meets recovery conditions - Loss: {loss_percent_of_balance:.2%} of balance, Distance: {price_distance:.1f} pips")
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
                elif key in ['account_balance', 'account_equity', 'free_margin']:
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
            # รายการคู่เงินที่ยอมรับ (เพิ่ม NZD pairs กลับมา)
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
            # 🆕 แปลง symbols ผ่าน mapper
            real_base = self.symbol_mapper.get_real_symbol(base_symbol) if self.symbol_mapper else base_symbol
            real_target = self.symbol_mapper.get_real_symbol(target_symbol) if self.symbol_mapper else target_symbol
            
            # ดึงข้อมูลราคาจาก MT5
            base_price = self.broker.get_current_price(real_base)
            target_price = self.broker.get_current_price(real_target)
            
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
    
    def _analyze_trend(self, symbol: str) -> Dict:
        """
        วิเคราะห์ trend ของคู่เงิน (NEW - for ML and smart direction)
        
        Returns:
            Dict with trend, strength, confidence
        """
        try:
            # Get historical data
            periods = getattr(self, 'trend_periods', 50)
            historical_data = self.broker.get_historical_data(symbol, 'M5', periods)
            
            if historical_data is None or len(historical_data) < 20:
                return {'trend': 'UNKNOWN', 'strength': 0, 'confidence': 0}
            
            # Calculate moving averages
            closes = historical_data['close'].values
            ma_fast = closes[-10:].mean()  # MA 10
            ma_slow = closes[-20:].mean()  # MA 20
            current_price = closes[-1]
            
            # Calculate slope
            import numpy as np
            x = np.arange(len(closes))
            slope = np.polyfit(x, closes, 1)[0]
            
            # Determine trend
            if ma_fast > ma_slow * 1.001 and slope > 0:
                trend = 'UP'
                strength = abs((ma_fast - ma_slow) / ma_slow)
            elif ma_fast < ma_slow * 0.999 and slope < 0:
                trend = 'DOWN'
                strength = abs((ma_fast - ma_slow) / ma_slow)
            else:
                trend = 'SIDEWAYS'
                strength = abs((ma_fast - ma_slow) / ma_slow)
            
            # Confidence (0-1)
            confidence = min(strength * 100, 1.0)
            
            return {
                'trend': trend,
                'strength': strength,
                'confidence': confidence,
                'ma_fast': ma_fast,
                'ma_slow': ma_slow,
                'current_price': current_price,
                'slope': slope
            }
            
        except Exception as e:
            self.logger.debug(f"Error analyzing trend for {symbol}: {e}")
            return {'trend': 'UNKNOWN', 'strength': 0, 'confidence': 0}
    
    def _determine_recovery_direction(self, base_symbol: str, target_symbol: str, correlation: float, original_position: Dict = None) -> str:
        """กำหนดทิศทางการ recovery โดยใช้ Trend Analysis (ENHANCED - backward compatible)"""
        try:
            # 🆕 STEP 1: ถ้าเปิด Trend Analysis → ใช้ trend
            if getattr(self, 'trend_analysis_enabled', False):
                trend_analysis = self._analyze_trend(target_symbol)
                trend = trend_analysis['trend']
                confidence = trend_analysis['confidence']
                threshold = getattr(self, 'trend_confidence_threshold', 0.4)
                
                self.logger.info(f"📈 Trend: {target_symbol} = {trend} (confidence: {confidence:.1%})")
                
                # ถ้า trend ชัดเจน → เชื่อใจได้
                if confidence >= threshold:
                    if trend == 'UP':
                        self.logger.info(f"   ✅ Uptrend → BUY {target_symbol}")
                        return 'BUY'
                    elif trend == 'DOWN':
                        self.logger.info(f"   ✅ Downtrend → SELL {target_symbol}")
                        return 'SELL'
                else:
                    self.logger.info(f"   ⚠️ Low confidence or sideways → using correlation method")
            
            # ⚡ FALLBACK: ใช้วิธีเดิม (correlation based) - backward compatible!
            original_direction = None
            if original_position:
                original_direction = original_position.get('type', 'SELL')
            
            if original_direction == 'BUY':
                return 'BUY'
            elif original_direction == 'SELL':
                return 'SELL'
            else:
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
            # Try different ticket fields - position data might use 'order_id' instead of 'ticket'
            original_ticket = str(original_position.get('ticket', '')) or str(original_position.get('order_id', ''))
            
            # Debug: Show ticket information
            self.logger.info(f"🔍 DEBUG: Original position data:")
            self.logger.info(f"   Ticket: '{original_ticket}' (type: {type(original_ticket)})")
            self.logger.info(f"   Symbol: {original_symbol}")
            self.logger.info(f"   Position keys: {list(original_position.keys())}")
            self.logger.info(f"   Raw ticket: {repr(original_position.get('ticket', 'NOT_FOUND'))}")
            self.logger.info(f"   Raw order_id: {repr(original_position.get('order_id', 'NOT_FOUND'))}")
            
            self.logger.info(f"🎯 Starting recovery for ticket {original_ticket}_{original_symbol}")
            
            # ✅ CRITICAL CHECK #1: Skip if ticket is empty
            if not original_ticket or original_ticket.strip() == '':
                self.logger.warning(f"🚫 INVALID TICKET: Ticket is empty for {original_symbol} - skipping")
                return False
            
            # ✅ CRITICAL CHECK #2: Verify this ticket is not already hedged
            if self.order_tracker.is_order_hedged(original_ticket, original_symbol):
                self.logger.warning(f"🚫 DUPLICATE PREVENTION: Ticket {original_ticket}_{original_symbol} already hedged - skipping")
                return False
            
            # ✅ CRITICAL CHECK #3: Double-check in case of race condition
            if not self.order_tracker.needs_recovery(original_ticket, original_symbol):
                # Try to register the order if it's not in the tracker
                self.logger.warning(f"🚫 Order {original_ticket}_{original_symbol} not in tracker - attempting to register")
                
                # Extract group_id from magic number
                magic = original_position.get('magic', 234000)
                if magic in [234001, 234002, 234003, 234004, 234005, 234006]:
                    group_num = str(magic)[-1]
                    group_id = f"group_triangle_{group_num}_1"
                    
                    # Register the order
                    success = self.order_tracker.register_original_order(
                        original_ticket, original_symbol, group_id
                    )
                    
                    if success:
                        self.logger.info(f"✅ Successfully registered {original_ticket}_{original_symbol} in tracker")
                        # Check again if it needs recovery
                        if not self.order_tracker.needs_recovery(original_ticket, original_symbol):
                            self.logger.warning(f"🚫 DUPLICATE PREVENTION: Ticket {original_ticket}_{original_symbol} still doesn't need recovery - skipping")
                            return False
                    else:
                        self.logger.error(f"❌ Failed to register {original_ticket}_{original_symbol} in tracker - skipping")
                        return False
                else:
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
            
            # Calculate correlation volume using new system
            correlation_volume = self._calculate_hedge_lot_size(
                original_lot=original_lot,
                correlation=correlation,
                loss_percent=0.0,
                original_symbol=original_symbol,
                hedge_symbol=correlation_candidate.get('symbol', '')
            )
            
            # คำนวณ lot size ตาม balance-based sizing
            original_lot = original_position.get('lot_size') or original_position.get('volume')
            if original_lot is None:
                self.logger.error("❌ No lot_size or volume in original_position - skipping hedge")
                return False
            
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
                    # 📋 แสดง log เมื่อสร้าง recovery order สำเร็จ
                    self.logger.info("")
                    self.logger.info("=" * 60)
                    self.logger.info("🛡️ RECOVERY ORDER CREATED - ไม้แก้ถูกสร้าง")
                    self.logger.info("=" * 60)
                    self.logger.info("📍 Original Order (ไม้ที่โดนแก้):")
                    self.logger.info(f"   Ticket: {original_ticket}")
                    self.logger.info(f"   Symbol: {original_symbol}")
                    self.logger.info(f"   PnL: ${original_position.get('profit', 0):.2f}")
                    self.logger.info("")
                    self.logger.info("🔧 Recovery Order (ไม้แก้):")
                    self.logger.info(f"   Ticket: {recovery_ticket}")
                    self.logger.info(f"   Symbol: {symbol}")
                    self.logger.info(f"   Direction: {direction}")
                    self.logger.info(f"   Lot Size: {correlation_lot_size:.2f}")
                    self.logger.info(f"   Correlation: {correlation:.2f}")
                    self.logger.info("")
                    self.logger.info(f"🔗 ความเชื่อมโยง: {original_symbol} (Ticket {original_ticket}) ← แก้โดย → {symbol} (Ticket {recovery_ticket})")
                    
                    # ✅ CRITICAL: Register recovery immediately
                    success = self.order_tracker.register_recovery_order(
                        recovery_ticket, symbol,           # Recovery order info
                        original_ticket, original_symbol   # Original order being hedged
                    )
                    
                    if success:
                        self.logger.info("✅ RECOVERY REGISTERED IN TRACKER")
                        self.logger.info(f"   🎯 ไม้เดิม: {original_ticket}_{original_symbol} (สถานะ: NOT_HEDGED → HEDGED)")
                        self.logger.info(f"   🛡️ ไม้แก้: {recovery_ticket}_{symbol} (สถานะ: NOT_HEDGED)")
                        self.logger.info(f"   🔗 เชื่อมโยง: {original_ticket}_{original_symbol} ← แก้โดย → {recovery_ticket}_{symbol}")
                    else:
                        self.logger.error(f"❌ Failed to register recovery for {original_ticket}_{original_symbol}")
                        return False
                    
                    self.logger.info("=" * 60)
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
            self.logger.info(f"   Lot Size: {original_position.get('lot_size', 'N/A')}")
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
    
    # ⭐ ฟังก์ชันนี้ถูกลบออกแล้ว - ใช้ _calculate_hedge_lot_size แทน
    
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
            
            self.logger.info(f"🔢 Recovery magic number: {magic_number} (from group_id: '{group_id}')")
            
            # Determine direction based on correlation
            order_type = self._calculate_hedge_direction(original_position, symbol)
            
            # 🆕 แปลง symbol ผ่าน mapper
            real_symbol = self.symbol_mapper.get_real_symbol(symbol) if self.symbol_mapper else symbol
            
            # ส่งออเดอร์
            result = self.broker.place_order(
                symbol=real_symbol,
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
        """🆕 Direct Order Processing: ตรวจสอบและแก้ไม้ทุกคู่โดยตรง"""
        try:
            # Cooldown check to prevent excessive logging (ใช้ค่าจาก config)
            current_time = datetime.now()
            cooldown = self.recovery_thresholds.get('cooldown_between_checks', 10)
            
            if hasattr(self, 'last_recovery_check'):
                elapsed = (current_time - self.last_recovery_check).total_seconds()
                if elapsed < cooldown:
                    return
            
            self.last_recovery_check = current_time
            
            # 🔄 STEP 1: Sync individual order tracker with MT5
            sync_results = self.order_tracker.sync_with_mt5()
            if sync_results.get('orders_removed', 0) > 0:
                self.logger.info(f"🔄 Synced: {sync_results['orders_removed']} orders removed")
            
            # 🆕 STEP 2: Direct Order Processing
            self._direct_order_recovery()
            
        except Exception as e:
            self.logger.error(f"Error in direct order recovery check: {e}")
    
    def _smart_recovery_flow(self):
        """🆕 Smart Recovery Flow: 3-Stage Process"""
        try:
            current_time = datetime.now()
            
            # 📊 แสดงสถานะทุก Group ทุก 30 วินาที
            if not hasattr(self, '_last_status_log'):
                self._last_status_log = current_time
                self._log_all_groups_status()
            elif (current_time - self._last_status_log).total_seconds() > 30:
                self._log_all_groups_status()
                self._last_status_log = current_time
            
            # 🎯 STAGE 1: ARBITRAGE - หา Group ที่ติดลบ
            arbitrage_groups = self._find_losing_arbitrage_groups()
            
            if arbitrage_groups:
                self.logger.info(f"🎯 STAGE 1: Found {len(arbitrage_groups)} groups with losing positions")
                # 🎯 STAGE 2: CORRELATION - แก้ไม้ที่ติดลบในแต่ละ Group
                for group_id, losing_positions in arbitrage_groups.items():
                    self._process_group_correlation_recovery(group_id, losing_positions)
            else:
                self.logger.info(f"🎯 STAGE 1: No losing arbitrage groups found - checking chain recovery")
                # 🎯 STAGE 3: CHAIN - ตรวจหา Recovery Orders ที่ยังติดลบ
                chain_candidates = self._find_chain_recovery_candidates()
                if chain_candidates:
                    self.logger.info(f"🔗 STAGE 3: Found {len(chain_candidates)} chain recovery candidates")
                    for candidate in chain_candidates:
                        self._start_individual_recovery(candidate)
                else:
                    self.logger.info(f"🔗 STAGE 3: No chain recovery candidates found")
            
        except Exception as e:
            self.logger.error(f"❌ Smart Recovery Flow error: {e}")
    
    def _direct_order_recovery(self):
        """🆕 Direct Order Processing: ตรวจสอบและแก้ไม้ทุกคู่โดยตรง"""
        try:
            self.logger.info(f"🚀 Direct Order Processing: Starting recovery check...")
            
            # ดึง positions ทั้งหมดจาก MT5
            all_positions = self.broker.get_all_positions()
            self.logger.info(f"📊 Total positions from MT5: {len(all_positions)}")
            
            # แยกประเภทไม้
            arbitrage_orders = []
            recovery_orders = []
            
            for position in all_positions:
                profit = position.get('profit', 0)
                comment = position.get('comment', '')
                
                # ตรวจสอบว่าเป็นไม้ติดลบ
                if profit >= 0:
                    continue
                
                # แยกประเภทไม้
                if self._is_recovery_order(position):
                    recovery_orders.append(position)
                else:
                    arbitrage_orders.append(position)
            
            self.logger.info(f"📊 Arbitrage Orders: {len(arbitrage_orders)} | Recovery Orders: {len(recovery_orders)}")
            
            # 1. แก้ไม้ Arbitrage (ด้วย Correlation)
            arbitrage_recovery_count = 0
            for position in arbitrage_orders:
                if self._meets_recovery_conditions(position):
                    success = self._start_individual_recovery(position)
                    if success:
                        arbitrage_recovery_count += 1
            
            # 2. แก้ไม้ Recovery (ด้วย Chain Recovery)
            chain_recovery_count = 0
            for position in recovery_orders:
                if self._meets_recovery_conditions(position):
                    success = self._start_individual_recovery(position)
                    if success:
                        chain_recovery_count += 1
            
            # แสดงสรุป
            total_recovery = arbitrage_recovery_count + chain_recovery_count
            if total_recovery > 0:
                self.logger.info(f"✅ Direct Processing: Arbitrage Recovery: {arbitrage_recovery_count} | Chain Recovery: {chain_recovery_count}")
            else:
                self.logger.info(f"📊 Direct Processing: No recovery started")
                
        except Exception as e:
            self.logger.error(f"❌ Direct Order Processing error: {e}")
    
    def _log_all_groups_status(self):
        """📊 แสดงตารางสถานะทุก Group"""
        try:
            all_positions = self.broker.get_all_positions()
            
            # เก็บข้อมูลแต่ละ Group
            groups_data = {}
            
            for magic in [234001, 234002, 234003, 234004, 234005, 234006]:
                group_positions = []
                total_pnl = 0.0
                losing_count = 0
                hedged_count = 0
                
                for pos in all_positions:
                    if pos.get('magic', 0) == magic:
                        comment = pos.get('comment', '')
                        if comment and comment.startswith('G') and '_' in comment:
                            group_positions.append(pos)
                            profit = pos.get('profit', 0)
                            total_pnl += profit
                            
                            if profit < 0:
                                losing_count += 1
                                
                                # เช็คว่าแก้ไม้แล้วหรือยัง
                                ticket = str(pos.get('ticket', ''))
                                symbol = pos.get('symbol', '')
                                if self.order_tracker.is_order_hedged(ticket, symbol):
                                    hedged_count += 1
                
                if group_positions:
                    group_id = self._get_group_id_from_magic(magic)
                    groups_data[group_id] = {
                        'total': len(group_positions),
                        'losing': losing_count,
                        'hedged': hedged_count,
                        'pnl': total_pnl
                    }
            
            # แสดงตาราง
            if groups_data:
                self.logger.info("=" * 80)
                self.logger.info("📊 SMART RECOVERY STATUS - ALL GROUPS")
                self.logger.info("=" * 80)
                self.logger.info(f"{'Group':<20} {'Stage':<15} {'Positions':<12} {'Losing':<10} {'Hedged':<10} {'PnL':<12}")
                self.logger.info("-" * 80)
                
                for group_id, data in sorted(groups_data.items()):
                    # กำหนด Stage
                    if data['losing'] == 0:
                        stage = "✅ Stable"
                        stage_color = ""
                    elif data['hedged'] == data['losing']:
                        stage = "🟢 Stage 2 Done"
                        stage_color = ""
                    elif data['hedged'] > 0:
                        stage = "🔧 Stage 2"
                        stage_color = ""
                    else:
                        stage = "🔴 Stage 1"
                        stage_color = ""
                    
                    pnl_icon = "🔴" if data['pnl'] < 0 else "🟢"
                    
                    self.logger.info(f"{group_id:<20} {stage:<15} {data['total']:<12} "
                                   f"{data['losing']:<10} {data['hedged']:<10} "
                                   f"{pnl_icon} ${data['pnl']:>8.2f}")
                
                self.logger.info("=" * 80)
                
                # 📋 แสดงรายละเอียดแต่ละ Group
                self._log_detailed_group_info(all_positions)
            
        except Exception as e:
            self.logger.error(f"❌ Error logging groups status: {e}")
    
    def _log_recovery_chain(self, parent_ticket: str, recovery_map: Dict, depth: int):
        """แสดง recovery chain แบบ recursive (หลายขั้น)"""
        try:
            if parent_ticket not in recovery_map:
                return
                
            recovery_chain = recovery_map[parent_ticket]
            for i, recovery_pos in enumerate(recovery_chain, 1):
                rec_ticket = recovery_pos.get('ticket', '')
                rec_symbol = recovery_pos.get('symbol', '')
                rec_profit = recovery_pos.get('profit', 0)
                rec_lot_size = recovery_pos.get('volume', 0)
                
                rec_profit_icon = "🔴" if rec_profit < 0 else "🟢"
                indent = "         " + "  " * depth  # เพิ่ม indent ตามขั้น
                
                self.logger.info(f"{indent}🔧 Recovery #{depth}.{i}: {rec_symbol} | Ticket: {rec_ticket} | Lot: {rec_lot_size} | PnL: ${rec_profit:.2f}")
                
                # แสดง recovery ของ recovery (recursive)
                self._log_recovery_chain(rec_ticket, recovery_map, depth + 1)
                
        except Exception as e:
            self.logger.error(f"❌ Error logging recovery chain: {e}")
    
    def _log_detailed_group_info(self, all_positions: List[Dict]):
        """📋 แสดงรายละเอียดแต่ละ Group: คู่เงิน, ไม้ไหนแก้ไม้ไหน"""
        try:
            for magic in [234001, 234002, 234003, 234004, 234005, 234006]:
                group_positions = []
                recovery_positions = []
                
                # แยก original และ recovery positions
                for pos in all_positions:
                    if pos.get('magic', 0) == magic:
                        comment = pos.get('comment', '')
                        if comment and comment.startswith('G') and '_' in comment:
                            group_positions.append(pos)
                        elif self._is_recovery_comment(comment):
                            recovery_positions.append(pos)
                
                if group_positions:
                    group_id = self._get_group_id_from_magic(magic)
                    total_pnl = sum(pos.get('profit', 0) for pos in group_positions)
                    
                    self.logger.info("")
                    self.logger.info(f"🔍 {group_id} DETAILS:")
                    self.logger.info(f"   📊 Total PnL: ${total_pnl:.2f}")
                    self.logger.info(f"   📈 Trading Chain:")
                    self.logger.info("")
                    
                    # สร้าง mapping ของ recovery orders
                    recovery_map = {}
                    for pos in recovery_positions:
                        comment = pos.get('comment', '')
                        if comment.startswith('R') and '_' in comment:
                            # Extract original ticket from comment (R3317086_EURUSD -> 3317086)
                            ticket_part = comment[1:].split('_')[0] if len(comment.split('_')) > 1 else ""
                            # ค้นหา ticket ที่ลงท้ายด้วย ticket_part
                            for orig_pos in group_positions:
                                orig_ticket = str(orig_pos.get('ticket', ''))
                                if orig_ticket.endswith(ticket_part):
                                    if orig_ticket not in recovery_map:
                                        recovery_map[orig_ticket] = []
                                    recovery_map[orig_ticket].append(pos)
                                    break
                    
                    # แสดงแต่ละ original position และ recovery chain
                    for idx, pos in enumerate(group_positions, 1):
                        ticket = str(pos.get('ticket', ''))
                        symbol = pos.get('symbol', '')
                        profit = pos.get('profit', 0)
                        lot_size = pos.get('volume', 0)
                        
                        # แสดง original position
                        profit_icon = "🔴" if profit < 0 else "🟢"
                        
                        self.logger.info(f"   🎯 Original #{idx}: {symbol} | Ticket: {ticket} | Lot: {lot_size:.2f} | PnL: ${profit:.2f} {profit_icon}")
                        
                        # แสดงสถานะและ recovery chain
                        if profit >= 0:
                            self.logger.info(f"      ✅ ไม่ต้องแก้ (กำไร)")
                        else:
                            # ตรวจสอบว่ามี recovery หรือยัง
                            if ticket in recovery_map:
                                # แสดง recovery chain
                                self._display_recovery_chain_tree(recovery_map, ticket, indent_level=1)
                            else:
                                # ยังไม่มี recovery - แสดงเหตุผล
                                is_hedged = self.order_tracker.is_order_hedged(ticket, symbol)
                                if is_hedged:
                                    self.logger.info(f"      ✅ แก้ไม้แล้ว (HEDGED)")
                                else:
                                    # ตรวจสอบว่าทำไมยังไม่แก้
                                    reason = self._get_no_recovery_reason(pos)
                                    self.logger.info(f"      ⏳ {reason}")
                        
                        self.logger.info("")
            
        except Exception as e:
            self.logger.error(f"❌ Error logging detailed group info: {e}")
    
    def _display_recovery_chain_tree(self, recovery_map: Dict, parent_ticket: str, indent_level: int = 1):
        """แสดง recovery chain แบบ tree structure"""
        try:
            if parent_ticket not in recovery_map:
                return
            
            recovery_chain = recovery_map[parent_ticket]
            for recovery_pos in recovery_chain:
                rec_ticket = str(recovery_pos.get('ticket', ''))
                rec_symbol = recovery_pos.get('symbol', '')
                rec_profit = recovery_pos.get('profit', 0)
                rec_lot_size = recovery_pos.get('volume', 0)
                
                rec_profit_icon = "🔴" if rec_profit < 0 else "🟢"
                
                # สร้าง indent
                indent = "      " + ("   " * indent_level)
                arrow = "↳"
                
                # กำหนด label ตามระดับ
                if indent_level == 1:
                    label = "🛡️ Recovery"
                else:
                    label = "🛡️ Chain Recovery"
                
                self.logger.info(f"{indent}{arrow} {label}: {rec_symbol} | Ticket: {rec_ticket} | Lot: {rec_lot_size:.2f} | PnL: ${rec_profit:.2f} {rec_profit_icon}")
                
                # แสดง recovery ของ recovery (recursive)
                if rec_ticket in recovery_map:
                    self._display_recovery_chain_tree(recovery_map, rec_ticket, indent_level + 1)
        
        except Exception as e:
            self.logger.debug(f"Error displaying recovery chain: {e}")
    
    def _get_no_recovery_reason(self, position: Dict) -> str:
        """หาเหตุผลว่าทำไมยังไม่แก้ไม้"""
        try:
            symbol = position.get('symbol', '')
            profit = position.get('profit', 0)
            entry_price = position.get('entry_price', 0)
            
            # ตรวจสอบ distance
            current_price = self.broker.get_current_price(symbol)
            if current_price and entry_price:
                price_distance = abs(current_price - entry_price)
                pip_value = 0.0001 if 'JPY' not in symbol else 0.01
                distance_pips = price_distance / pip_value
                
                if distance_pips < self.min_price_distance_pips:
                    return f"รอเงื่อนไข (distance {distance_pips:.1f} < {self.min_price_distance_pips} pips)"
            
            # ตรวจสอบ loss threshold
            balance = self.broker.get_account_balance()
            min_loss = balance * abs(self.recovery_thresholds.get('min_loss_percent', 0.5)) / 100
            if abs(profit) < min_loss:
                return f"รอเงื่อนไข (loss ${abs(profit):.2f} < ${min_loss:.2f})"
            
            # ตรวจสอบ position age
            # (ถ้ามีการเก็บ opened_at time สามารถเช็คได้)
            
            return "รอเงื่อนไข"
            
        except Exception as e:
            return "รอเงื่อนไข"
    
    def _find_losing_arbitrage_groups(self) -> Dict[str, List[Dict]]:
        """🎯 STAGE 1: หา Arbitrage Groups ที่มีคู่ติดลบ"""
        try:
            losing_groups = {}
            
            # 🆕 Debug: แสดงจำนวน positions ทั้งหมด
            all_positions = self.broker.get_all_positions()
            self.logger.info(f"🔍 DEBUG: Total positions from MT5: {len(all_positions)}")
            
            # ตรวจสอบ Groups ทั้งหมด (Magic 234001-234006)
            for magic in [234001, 234002, 234003, 234004, 234005, 234006]:
                group_positions = []
                
                # หา positions ใน group นี้
                all_positions = self.broker.get_all_positions()
                for pos in all_positions:
                    if pos.get('magic', 0) == magic:
                        # ตรวจสอบว่าเป็น original arbitrage order (ไม่ใช่ recovery)
                        comment = pos.get('comment', '')
                        # 🆕 รองรับเฉพาะ G comments (Arbitrage Orders เท่านั้น)
                        if comment and comment.startswith('G') and '_' in comment:
                            group_positions.append(pos)
                        # 🆕 ถ้าไม่มี comment ให้รวมด้วย (ไม้เก่าที่ไม่มี comment)
                        elif not comment:
                            group_positions.append(pos)
                        # ❌ ข้าม R comments ทั้งหมด (Recovery Orders ไม่ใช่ Arbitrage Orders)
                
                # ถ้า Group มีคู่ติดลบ
                if group_positions:
                    losing_positions = [pos for pos in group_positions if pos.get('profit', 0) < 0]
                    
                    if losing_positions:
                        group_id = self._get_group_id_from_magic(magic)
                        losing_groups[group_id] = losing_positions
                        self.logger.info(f"🔍 DEBUG: Found {len(losing_positions)} losing positions in {group_id}")
                    else:
                        self.logger.info(f"🔍 DEBUG: Group {magic} has {len(group_positions)} positions but none are losing")
                else:
                    self.logger.info(f"🔍 DEBUG: Group {magic} has no positions")
            
            self.logger.info(f"🔍 DEBUG: Total losing groups found: {len(losing_groups)}")
            return losing_groups
            
        except Exception as e:
            self.logger.error(f"❌ STAGE 1 error: {e}")
            return {}
    
    def _process_group_correlation_recovery(self, group_id: str, losing_positions: List[Dict]):
        """🎯 STAGE 2: แก้ไม้ Correlation สำหรับ Group"""
        try:
            # แก้ไม้ที่ติดลบแต่ละคู่
            recovery_count = 0
            skipped_count = 0
            
            for position in losing_positions:
                ticket = str(position.get('ticket', ''))
                symbol = position.get('symbol', '')
                profit = position.get('profit', 0)
                
                # ตรวจสอบว่าไม้นี้ยังไม่แก้
                if self.order_tracker.is_order_hedged(ticket, symbol):
                    skipped_count += 1
                    continue
                
                # ตรวจสอบเงื่อนไขการแก้ไม้
                if self._meets_recovery_conditions(position):
                    self.logger.info(f"🔧 {group_id} | {symbol}: ${profit:.2f} | STAGE 2: Starting Correlation Recovery")
                    success = self._start_individual_recovery(position)
                    if success:
                        recovery_count += 1
                else:
                    # 🆕 Debug: แสดงว่าทำไมไม้ไม่ผ่านเงื่อนไข
                    self.logger.info(f"❌ {group_id} | {symbol}: ${profit:.2f} | STAGE 2: Failed recovery conditions")
                    skipped_count += 1
            
            # Log สรุปเฉพาะเมื่อมีการทำงาน
            if recovery_count > 0:
                self.logger.info(f"✅ {group_id}: Started {recovery_count} recovery | Skipped {skipped_count} | STAGE 2: Complete")
                
        except Exception as e:
            self.logger.error(f"❌ {group_id} STAGE 2 error: {e}")
    
    def _find_chain_recovery_candidates(self) -> List[Dict]:
        """🎯 STAGE 3: หา Recovery Orders ที่ยังติดลบ (Chain Recovery)"""
        try:
            chain_candidates = []
            
            # หา Recovery Orders ที่ยังติดลบ
            all_positions = self.broker.get_all_positions()
            for pos in all_positions:
                comment = pos.get('comment', '')
                profit = pos.get('profit', 0)
                
                # ตรวจสอบว่าเป็น Recovery Order
                if self._is_recovery_order(pos) and profit < 0:
                    # ตรวจสอบเงื่อนไข Chain Recovery
                    if self._meets_recovery_conditions(pos):
                        chain_candidates.append(pos)
                    else:
                        # 🆕 Debug: แสดงว่าทำไมไม้แก้ไม่ผ่านเงื่อนไข
                        symbol = pos.get('symbol', '')
                        self.logger.info(f"❌ STAGE 3 | {symbol}: ${profit:.2f} | Failed chain recovery conditions")
            
            return chain_candidates
            
        except Exception as e:
            self.logger.error(f"Error finding chain recovery candidates: {e}")
            return []
    
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
            
            # 🆕 แปลง symbol ผ่าน mapper
            real_symbol = self.symbol_mapper.get_real_symbol(symbol) if self.symbol_mapper else symbol
            current_price = self.broker.get_current_price(real_symbol)
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
        """Check if position meets recovery conditions"""
        try:
            # Try different ticket fields
            ticket = str(position.get('ticket', '')) or str(position.get('order_id', ''))
            symbol = position.get('symbol', '')
            profit = position.get('profit', 0)
            comment = position.get('comment', '')
            
            # 🔗 Check if it's a recovery order (Chain Recovery Logic)
            if self._is_recovery_order(position):
                if not self.chain_recovery_enabled:
                    self.logger.debug(f"❌ {symbol} (Ticket: {ticket}): Chain recovery disabled")
                    return False
                
                chain_depth = self._get_recovery_chain_depth(ticket, symbol)
                max_chain_depth = self.recovery_thresholds.get('max_chain_depth', 5)
                
                if chain_depth >= max_chain_depth:
                    self.logger.debug(f"❌ {symbol} (Ticket: {ticket}): Chain depth {chain_depth} >= {max_chain_depth}")
                    return False
                
                balance = self.broker.get_account_balance()
                if not balance:
                    self.logger.error("❌ Cannot get account balance from MT5 - skipping chain recovery check")
                    return False
                loss_percent = profit / balance
                min_chain_percent = self.recovery_thresholds.get('min_loss_percent_for_chain', -1) / 100
                
                if loss_percent > min_chain_percent:
                    self.logger.debug(f"❌ {symbol} (Ticket: {ticket}): Chain loss {loss_percent:.4f} ({loss_percent*100:.2f}%) > {min_chain_percent:.4f}")
                    return False
            
            # Check if position already has recovery orders
            order_info = self.order_tracker.get_order_info(ticket, symbol)
            if order_info:
                recovery_orders = order_info.get('recovery_orders', [])
                if recovery_orders:
                    return False
            
            # Check if position is already hedged (ข้ามการตรวจสอบ tracking ชั่วคราว)
            # if self.order_tracker.is_order_hedged(ticket, symbol):
            #     return False
            
            # Check if position is losing money
            if profit >= 0:
                self.logger.debug(f"💰 {symbol} (Ticket: {ticket}): PROFIT ${profit:.2f} - No recovery needed")
                return False
            
            # 💡 Percentage-based loss check (ใช้ค่าจาก config)
            balance = self.broker.get_account_balance()
            if not balance:
                self.logger.error("❌ Cannot get account balance from MT5 - skipping recovery check")
                return False
            loss_percent = profit / balance
            min_loss_percent = self.recovery_thresholds.get('min_loss_percent', -0.005)
            
            if loss_percent > min_loss_percent:
                self.logger.debug(f"❌ {symbol} (Ticket: {ticket}): Loss {loss_percent:.4f} ({loss_percent*100:.2f}%) < {min_loss_percent:.4f} ({abs(min_loss_percent)*100:.1f}%)")
                return False
            
            # 🆕 Check price distance (ใช้ค่าจาก config)
            price_distance_pips = self._calculate_price_distance_pips(position)
            min_distance = self.recovery_thresholds.get('min_price_distance_pips', 10)
            
            if price_distance_pips < min_distance:
                self.logger.debug(f"❌ {symbol} (Ticket: {ticket}): Distance {price_distance_pips:.1f} pips < {min_distance} pips")
                return False
            
            # 🆕 Check position age (ใช้ค่าจาก config)
            position_age = self._get_position_age_seconds(position)
            min_age = self.recovery_thresholds.get('min_position_age_seconds', 60)
            
            if position_age < min_age:
                self.logger.debug(f"❌ {symbol} (Ticket: {ticket}): Age {position_age:.0f}s < {min_age}s")
                return False
            
            # ✅ All conditions met
            self.logger.info(f"✅ {symbol} (Ticket: {ticket}): All conditions met - Loss {loss_percent:.4f}, Distance {price_distance_pips:.1f}pips, Age {position_age:.0f}s")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Recovery condition check error: {e}")
            return False
    
    def _start_individual_recovery(self, position: Dict):
        """Start recovery for individual position"""
        try:
            # Try different ticket fields
            ticket = position.get('ticket', '') or position.get('order_id', '')
            symbol = position.get('symbol', '')
            profit = position.get('profit', 0)
            lot_size = position.get('volume', 0)
            direction = position.get('type', 'UNKNOWN')
            entry_price = position.get('entry_price', 0)
            
            # ✅ CRITICAL: Final check before starting recovery
            if self.order_tracker.is_order_hedged(ticket, symbol):
                return
            
            if not self.order_tracker.needs_recovery(ticket, symbol):
                return
            
            # 📋 แสดง log เมื่อเริ่มแก้ไม้
            self.logger.info("=" * 60)
            self.logger.info("🔧 RECOVERY START - แก้ไม้ขาดทุน")
            self.logger.info("=" * 60)
            self.logger.info("📍 Original Order (ไม้ที่ต้องแก้):")
            self.logger.info(f"   Ticket: {ticket}")
            self.logger.info(f"   Symbol: {symbol}")
            self.logger.info(f"   Direction: {direction}")
            self.logger.info(f"   Lot Size: {lot_size:.2f}")
            self.logger.info(f"   Entry Price: {entry_price:.5f}")
            self.logger.info(f"   Current PnL: ${profit:.2f}")
            self.logger.info("")
            self.logger.info("🎯 กำลังหาคู่เงินที่เหมาะสมเพื่อแก้ไม้นี้...")
            
            # Find correlation pairs
            correlation_candidates = self._find_correlation_pairs_for_symbol(symbol)
            
            if correlation_candidates:
                best_correlation = correlation_candidates[0]
                self.logger.info(f"✅ พบคู่เงินที่เหมาะสม: {best_correlation.get('symbol', 'N/A')} (Correlation: {best_correlation.get('correlation', 0):.2f})")
                self.logger.info("=" * 60)
                recovery_symbol = best_correlation.get('symbol', 'UNKNOWN')
                correlation = best_correlation.get('correlation', 0.0)
                
                # ✅ Get magic number from original position
                original_magic = position.get('magic', 234000)
                
                # Create group_id that matches the magic number format
                if original_magic in [234001, 234002, 234003, 234004, 234005, 234006]:
                    group_num = str(original_magic)[-1]  # Extract last digit (1-6)
                    group_id = f"group_triangle_{group_num}_1"
                else:
                    # Fallback for non-standard magic numbers
                    group_id = f"recovery_{ticket}_{symbol}"
                
                self.logger.info(f"🔧 {group_id} | {symbol} → {recovery_symbol} | Corr: {correlation:.2f} | Opening Recovery")
                
                success = self._execute_correlation_position(position, best_correlation, group_id)
                if success:
                    self.logger.info(f"✅ {group_id} | {symbol} → {recovery_symbol} | Recovery Opened Successfully")
                else:
                    self.logger.warning(f"❌ {group_id} | {symbol} → {recovery_symbol} | Recovery Failed")
            else:
                self.logger.warning(f"⚠️ {symbol}: No correlation pairs found")
                
        except Exception as e:
            self.logger.error(f"❌ Recovery start error: {e}")
    
    def _display_recovery_chain(self, recovery_orders: List[str], parent_symbol: str = "", parent_ticket: str = "", indent_level: int = 1, visited: Set[str] = None):
        """Display recovery chain recursively and show hedge linkage.
        Example:
           └─ EURGBP (R:34009119) → hedge GBPUSD (T:3398xxx): $-5.38 🔴
        """
        try:
            if visited is None:
                visited = set()
            indent = "   " + "  " * indent_level  # เพิ่ม indent ตาม level
            
            if not recovery_orders:
                return
            
            for recovery_key in recovery_orders:
                if recovery_key in visited:
                    continue
                visited.add(recovery_key)
                if recovery_key in self.order_tracker.order_tracking:
                    recovery_info = self.order_tracker.order_tracking[recovery_key]
                    recovery_symbol = recovery_info.get('symbol', '')
                    recovery_ticket = recovery_info.get('ticket', '')
                    recovery_status = recovery_info.get('status', 'UNKNOWN')
                    
                    # หา recovery position จาก MT5
                    recovery_position = self._get_position_by_ticket(recovery_ticket)
                    if recovery_position:
                        recovery_pnl = recovery_position.get('profit', 0)
                        recovery_icon = "🟢" if recovery_pnl >= 0 else "🔴"
                        linkage = f" → hedge {parent_symbol} (T:{parent_ticket})" if parent_symbol else ""
                        self.logger.info(f"{indent}└─ {recovery_symbol} (R:{recovery_ticket}){linkage}: ${recovery_pnl:,.2f} {recovery_icon}")
                        
                        # ตรวจสอบว่า recovery order นี้ถูก hedge หรือไม่
                        if recovery_status == 'HEDGED':
                            recovery_recovery_orders = recovery_info.get('recovery_orders', [])
                            if recovery_recovery_orders:
                                # แสดง recovery orders ของ recovery order (chain recovery)
                                self._display_recovery_chain(
                                    recovery_recovery_orders,
                                    parent_symbol=recovery_symbol,
                                    parent_ticket=str(recovery_ticket),
                                    indent_level=indent_level + 1,
                                    visited=visited
                                )
                    else:
                        # Recovery order ไม่พบใน MT5 (อาจถูกปิดแล้ว)
                        linkage = f" → hedge {parent_symbol} (T:{parent_ticket})" if parent_symbol else ""
                        self.logger.info(f"{indent}└─ {recovery_symbol} (R:{recovery_ticket}){linkage}: [CLOSED]")
                else:
                    pass
                        
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
            # Check broker connection first
            if not self.broker or not hasattr(self.broker, '_connected') or not self.broker._connected:
                self.logger.error(f"❌ Broker not connected - cannot calculate real correlations for {symbol}")
                self.logger.error(f"❌ This is why the system falls back to default correlations")
                return []
            
            # Get correlations from AI engine
            correlations = {}
            if self.ai_engine:
                correlations = self.ai_engine.get_correlations(symbol)
            
            if not correlations:
                # Try fallback: use default correlations directly
                if hasattr(self.ai_engine, '_get_default_correlations'):
                    correlations = self.ai_engine._get_default_correlations(symbol)
                    if not correlations:
                        self.logger.warning(f"⚠️ {symbol}: No correlations available")
                        return []
                else:
                    self.logger.warning(f"⚠️ {symbol}: AI engine not available")
                    return []
            
            correlation_candidates = []
            
            # Try negative correlations first (with relaxed threshold)
            for pair, correlation_value in correlations.items():
                # ✅ FILTER 1: Check for common currency but allow strong negative correlations
                has_common = self._has_common_currency(symbol, pair)
                
                if has_common:
                    # Allow JPY pairs to correlate with each other (common in forex)
                    if 'JPY' in symbol and 'JPY' in pair:
                        pass  # Allow
                    # RELAXED: Allow strong negative correlations even with common currency
                    elif correlation_value <= -0.4:
                        pass  # Allow
                    else:
                        continue
                
                # ✅ FILTER 2: Only accept negative correlations
                if correlation_value >= -0.1:
                    continue
                
                # Strong negative correlation (good for hedging)
                if correlation_value <= -0.98:
                    continue
                
                # ✅ NEW FILTER 3: Check if symbol is not overused (max 2 times)
                if not self._is_recovery_symbol_available(pair, max_usage=2):
                    continue
                
                correlation_candidates.append({
                    'symbol': pair,
                    'correlation': correlation_value,
                    'direction': 'opposite',  # Negative correlation = opposite direction
                    'has_common_currency': has_common
                })
            
            # Fallback: Use strong positive correlations (trade opposite direction)
            if not correlation_candidates:
                self.logger.debug(f"{symbol}: No negative correlations - trying inverse strategy")
                
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
            correlation_candidates.sort(key=lambda x: x['correlation'])
            
            # Log only if no candidates found
            if not correlation_candidates:
                self.logger.warning(f"⚠️ {symbol}: No valid correlation pairs found")
            
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
                comment = pos.get('comment', '')
                
                if not ticket or not symbol:
                    continue
                
                # STRICT VALIDATION: Only track arbitrage orders with specific magic and comment patterns
                if not (234001 <= magic <= 234006):
                    continue
                
                # Additional validation: Check comment pattern (G1_, G2_, etc.)
                if not comment or not comment.startswith('G') or '_' not in comment:
                    self.logger.debug(f"⚠️ Skipping order {ticket}_{symbol}: Invalid comment pattern '{comment}'")
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
                    self.logger.info(f"🆕 Auto-registered new order: {ticket}_{symbol} (${profit:.2f}) (comment: {comment})")
            
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
                comment = pos.get('comment', '')
                
                if not ticket or not symbol:
                    continue
                
                # STRICT VALIDATION: Only register arbitrage orders with specific magic and comment patterns
                if not (234001 <= magic <= 234006):
                    self.logger.debug(f"⚠️ Skipping order {ticket}_{symbol}: Magic {magic} not in range 234001-234006")
                    continue
                
                # Additional validation: Check comment pattern (G1_, G2_, etc.)
                if not comment or not comment.startswith('G') or '_' not in comment:
                    self.logger.debug(f"⚠️ Skipping order {ticket}_{symbol}: Invalid comment pattern '{comment}'")
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
                    self.logger.info(f"✅ Registered: {ticket}_{symbol} (${profit:.2f}) in {group_id} (comment: {comment})")
                else:
                    self.logger.warning(f"❌ Failed to register: {ticket}_{symbol}")
            
            self.logger.info(f"📊 Registration complete: {registered_count} registered, {skipped_count} already tracked")
            
            # Show updated statistics (only if there are orders)
            stats = self.order_tracker.get_statistics()
            if stats['total_tracked_orders'] > 0:
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
    
    def clear_old_order_tracking(self):
        """Clear all old order tracking data to start fresh"""
        try:
            self.logger.info("🧹 CLEARING OLD ORDER TRACKING DATA")
            
            # Clear order tracker
            if hasattr(self, 'order_tracker') and self.order_tracker:
                self.order_tracker.force_reset_all_orders()
                self.logger.info("✅ Order tracker cleared")
            
            # Clear recovery data files
            import os
            files_to_clear = [
                "data/order_tracking.json",
                "data/active_groups.json",
                "data/recovery_positions.json"
            ]
            
            for file_path in files_to_clear:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        self.logger.info(f"🗑️ Removed: {file_path}")
                    except Exception as e:
                        self.logger.warning(f"⚠️ Could not remove {file_path}: {e}")
            
            self.logger.info("✅ Old tracking data cleared - system ready for fresh start")
            
        except Exception as e:
            self.logger.error(f"❌ Error clearing old tracking data: {e}")
    
    def _enable_auto_registration(self):
        """Enable auto-registration of new orders (use with caution)"""
        try:
            self.logger.info("🔧 ENABLING AUTO-REGISTRATION")
            self.logger.warning("⚠️ Auto-registration will track ALL orders with magic 234001-234006")
            self.logger.warning("⚠️ Make sure this is what you want!")
            
            # Enable auto-registration by uncommenting the line in check_recovery_chain
            # This is a manual process for safety
            self.logger.info("ℹ️ To enable auto-registration, uncomment the line in check_recovery_chain()")
            self.logger.info("ℹ️ Line: # self._auto_register_new_orders()")
            
        except Exception as e:
            self.logger.error(f"❌ Error enabling auto-registration: {e}")
    
    def reset_tracker_to_match_mt5(self):
        """Reset order tracker to match real MT5 positions"""
        try:
            self.logger.info("🔄 RESETTING ORDER TRACKER TO MATCH MT5")
            
            # Check broker connection
            if not self.broker:
                self.logger.error("❌ Broker not initialized - cannot reset tracker")
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
            
            # Get current tracker stats
            stats_before = self.order_tracker.get_statistics()
            self.logger.info(f"📊 Before reset: {stats_before['total_tracked_orders']} tracked orders")
            
            # Force reset all orders
            self.order_tracker.force_reset_all_orders()
            self.logger.info("🧹 Cleared all tracked orders")
            
            # Get all MT5 positions
            all_positions = self.broker.get_all_positions()
            self.logger.info(f"📊 Found {len(all_positions)} positions in MT5")
            
            if not all_positions:
                self.logger.warning("⚠️ No positions found in MT5")
                return
            
            # Register only valid arbitrage orders
            registered_count = 0
            skipped_count = 0
            
            for pos in all_positions:
                ticket = str(pos.get('ticket', ''))
                symbol = pos.get('symbol', '')
                magic = pos.get('magic', 0)
                comment = pos.get('comment', '')
                profit = pos.get('profit', 0)
                
                if not ticket or not symbol:
                    continue
                
                # STRICT VALIDATION: Only register arbitrage orders
                if not (234001 <= magic <= 234006):
                    self.logger.debug(f"⚠️ Skipping order {ticket}_{symbol}: Magic {magic} not in range 234001-234006")
                    skipped_count += 1
                    continue
                
                # Additional validation: Check comment pattern
                if not comment or not comment.startswith('G') or '_' not in comment:
                    self.logger.debug(f"⚠️ Skipping order {ticket}_{symbol}: Invalid comment pattern '{comment}'")
                    skipped_count += 1
                    continue
                
                # Determine group_id from magic number
                group_id = self._get_group_id_from_magic(magic)
                
                # Register as original order
                success = self.order_tracker.register_original_order(ticket, symbol, group_id)
                if success:
                    registered_count += 1
                    self.logger.info(f"✅ Registered: {ticket}_{symbol} (${profit:.2f}) in {group_id} (comment: {comment})")
                else:
                    self.logger.warning(f"❌ Failed to register: {ticket}_{symbol}")
            
            # Show final statistics
            stats_after = self.order_tracker.get_statistics()
            self.logger.info(f"📊 After reset: {stats_after['total_tracked_orders']} tracked orders")
            self.logger.info(f"📊 Registration complete: {registered_count} registered, {skipped_count} skipped")
            
            # Show updated statistics
            self.order_tracker.log_status_summary()
            
        except Exception as e:
            self.logger.error(f"❌ Error resetting tracker: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
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
    
    def reload_config(self):
        """โหลดการตั้งค่าใหม่จาก config file (Hot Reload!)"""
        try:
            self.logger.info("🔄 Reloading config from adaptive_params.json...")
            self._load_config_from_file()
            
            # Reinitialize ML components if needed
            if self.ml_logging_enabled and not hasattr(self, 'ml_logger'):
                from data.ml_logger import MLRecoveryLogger
                self.ml_logger = MLRecoveryLogger()
            
            if self.bandit_enabled and not hasattr(self, 'pair_bandit'):
                from data.pair_selector_bandit import PairSelectorBandit
                self.pair_bandit = PairSelectorBandit(
                    exploration_rate=self.bandit_exploration_rate,
                    learning_rate=self.bandit_learning_rate
                )
            
            self.logger.info("✅ Config reloaded successfully!")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error reloading config: {e}")
            return False
