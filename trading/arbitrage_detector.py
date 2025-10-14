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
import os
import sys
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("⚠️ MetaTrader5 not available - using fallback mode")

# Ensure project root is on sys.path when running this module directly
try:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if PROJECT_ROOT not in sys.path:
        sys.path.append(PROJECT_ROOT)
except Exception:
    pass
from utils.calculations import TradingCalculations
from utils.symbol_mapper import SymbolMapper
# Removed AccountTierManager - using GUI Risk per Trade only

class TriangleArbitrageDetector:
    def __init__(self, broker_api, ai_engine=None, correlation_manager=None):
        self.broker = broker_api
        # self.ai = ai_engine  # DISABLED for simple trading system
        self.correlation_manager = correlation_manager  # เพิ่ม correlation manager
        self.active_triangles = {}
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        
        # Adaptive parameters - More strict and accurate
        # self.current_regime = 'normal'  # DISABLED - not used in simple trading
        # self.market_regime = 'normal'  # DISABLED - not used in simple trading
        self.arbitrage_threshold = 0.0001  # Lower threshold (0.01 pips) for easier detection
        self.volatility_threshold = 0.0001  # Same as arbitrage_threshold for simple trading
        self.execution_timeout = 150  # Target execution speed
        self.position_size = 0.1  # Default position size
        
        # Enhanced validation parameters - ปรับให้ง่ายขึ้น
        self.min_confidence_score = 0.5  # Minimum confidence score (50%) - ลดจาก 75%
        self.max_spread_ratio = 0.5  # Maximum spread ratio (50%) - เพิ่มจาก 30%
        self.min_volume_threshold = 0.1  # Minimum volume threshold - ลดจาก 0.5
        self.price_stability_checks = 1  # Number of price stability checks - ลดจาก 3
        self.confirmation_delay = 1  # Seconds to wait for confirmation - ลดจาก 2
        
        # Group management for multiple arbitrage triangles (แยกกัน)
        self.active_groups = {}  # เก็บข้อมูลกลุ่มที่เปิดอยู่ (รวมทุกสามเหลี่ยม)
        self.group_counters = {}  # ตัวนับกลุ่มแยกตามสามเหลี่ยม
        self.is_arbitrage_paused = {}  # หยุดตรวจสอบ arbitrage ใหม่แยกตามสามเหลี่ยม
        self.used_currency_pairs = {}  # เก็บคู่เงินที่ถูกใช้ในกลุ่มที่ยังเปิดอยู่แยกตามสามเหลี่ยม
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
            # ⭐ New metrics for improved system
            'opportunities_checked': 0,
            'passed_direction_check': 0,
            'passed_feasibility_check': 0,
            'passed_balance_check': 0,
            'forward_path_selected': 0,
            'reverse_path_selected': 0,
            'avg_expected_profit': 0.0,
            'total_expected_profit': 0.0,
            'orders_cancelled_due_to_failure': 0
            # 'market_regime_changes': 0  # DISABLED - not used in simple trading
        }
        
        # Initialize pairs and combinations after logger is set
        self.available_pairs = self._get_available_pairs()
        
        # 🆕 Symbol Mapper - จับคู่ชื่อคู่เงินกับนามสกุลจริงของ Broker
        self.symbol_mapper = SymbolMapper()
        
        # 🆕 Spread Cache - เก็บข้อมูล spread จริง
        self.spread_cache = {}
        self.spread_cache_file = "data/spread_cache.json"
        self._load_spread_cache()
        
        # ใช้ 6 สามเหลี่ยม Arbitrage แยกกัน (Optimized - ทุกคู่ซ้ำ Hedged!)
        self.arbitrage_pairs = [
            'EURUSD', 'GBPUSD', 'EURGBP',  # Group 1
            'USDCHF', 'EURCHF',            # Group 2, 5
            'USDJPY', 'GBPJPY',            # Group 3
            'AUDUSD', 'USDCAD', 'AUDCAD',  # Group 4
            'NZDUSD', 'NZDCHF', 'AUDNZD'   # Group 5, 6 (ใช้ตามตาราง MT5)
        ]
        
        # 6 สามเหลี่ยม arbitrage แยกกัน (Optimized Setup - No Same-Direction Duplicates!)
        self.triangle_combinations = [
            ('EURUSD', 'GBPUSD', 'EURGBP'),    # Group 1: EUR/USD(BUY), GBP/USD(SELL), EUR/GBP
            ('EURUSD', 'USDCHF', 'EURCHF'),    # Group 2: EUR/USD(SELL), USD/CHF(BUY), EUR/CHF ✅ Hedged
            ('GBPUSD', 'USDJPY', 'GBPJPY'),    # Group 3: GBP/USD(BUY), USD/JPY(SELL), GBP/JPY ✅ Hedged
            ('AUDUSD', 'USDCAD', 'AUDCAD'),    # Group 4: AUD/USD(BUY), USD/CAD(SELL), AUD/CAD
            ('NZDUSD', 'USDCHF', 'NZDCHF'),    # Group 5: NZD/USD(BUY), USD/CHF(SELL), NZD/CHF ✅ Hedged
            ('AUDUSD', 'NZDUSD', 'AUDNZD')     # Group 6: AUD/USD(SELL), NZD/USD(SELL), AUD/NZD ✅ Hedged
        ]
        
        # 🆕 Scan and Map Symbols from Broker
        self._initialize_symbol_mapping()
        
        # เริ่มต้นตัวนับกลุ่มสำหรับแต่ละสามเหลี่ยม
        for i, triangle in enumerate(self.triangle_combinations, 1):
            triangle_name = f"triangle_{i}"
            self.group_counters[triangle_name] = 0
            self.is_arbitrage_paused[triangle_name] = False
            self.used_currency_pairs[triangle_name] = set()
        
        # Magic numbers สำหรับแต่ละสามเหลี่ยม (Optimized - All Hedged!)
        self.triangle_magic_numbers = {
            'triangle_1': 234001,  # EURUSD(BUY), GBPUSD(SELL), EURGBP
            'triangle_2': 234002,  # EURUSD(SELL), USDCHF(BUY), EURCHF ✅
            'triangle_3': 234003,  # GBPUSD(BUY), USDJPY(SELL), GBPJPY ✅
            'triangle_4': 234004,  # AUDUSD(BUY), USDCAD(SELL), AUDCAD
            'triangle_5': 234005,  # NZDUSD(BUY), USDCHF(SELL), NZDCHF ✅
            'triangle_6': 234006   # AUDUSD(SELL), NZDUSD(SELL), AUDNZD ✅
        }
        
        # ⭐ ไม่ใช้ standard_lot_size แล้ว - ใช้ risk-based calculation เท่านั้น
        
        # ⭐ เพิ่ม Account Tier Manager
        # Removed AccountTierManager - using GUI Risk per Trade only
        
        # โหลด config สำหรับ Account Tier
        self._load_tier_config()
        
        # ระบบป้องกันการส่ง recovery ซ้ำ
        self.recovery_in_progress = set()  # เก็บ group_id ที่กำลัง recovery
        
        # ระบบ Save/Load ข้อมูล
        self.persistence_file = "data/active_groups.json"
        
        # การตั้งค่าการปิดกลุ่ม
        self.profit_threshold_per_lot = 1.0  # 1 USD ต่อ lot เดี่ยว
        
        # 🆕 Trailing Stop System (Group-Level)
        self.group_trailing_stops = {}  # {group_id: {'peak': float, 'stop': float, 'active': bool}}
        
        # ⭐ โหลด Trailing Stop Config จาก adaptive_params.json
        self._load_trailing_stop_config()
        
        # 🆕 Min Profit Threshold (Scale with Balance) - จะถูกโหลดจาก config
        
        # If no triangles generated, create fallback triangles
        if len(self.triangle_combinations) == 0 and len(self.available_pairs) > 0:
            self.logger.warning("No triangles generated, creating fallback triangles...")
            self.triangle_combinations = [('EURUSD', 'GBPUSD', 'EURGBP')]  # Fixed fallback
        elif len(self.triangle_combinations) == 0:
            self.logger.error("❌ No triangles generated and no available pairs!")
        
        # Load existing active groups on startup
        self._load_active_groups()
    
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
            
            # Return all pairs (no filtering) - SymbolMapper will handle matching
            return all_pairs
            
        except Exception as e:
            self.logger.error(f"Error getting available pairs: {e}")
            return []
    
    def _initialize_symbol_mapping(self):
        """สแกนและจับคู่ symbol จาก broker"""
        try:
            self.logger.info("=" * 60)
            self.logger.info("🔍 Initializing Symbol Mapping System...")
            self.logger.info("=" * 60)
            
            # รวมคู่เงินทั้งหมดที่เราต้องการใช้
            required_pairs = list(set(self.arbitrage_pairs))
            
            # เพิ่มคู่เงินที่อาจใช้ใน recovery (28 pairs)
            recovery_pairs = [
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
            
            required_pairs.extend(recovery_pairs)
            required_pairs = list(set(required_pairs))  # ลบซ้ำ
            
            self.logger.info(f"📊 Required pairs: {len(required_pairs)}")
            
            # Scan and map
            mapping_result = self.symbol_mapper.scan_and_map(self.available_pairs, required_pairs)
            
            # Validate required pairs for arbitrage
            arbitrage_validation = self.symbol_mapper.validate_required_pairs(self.arbitrage_pairs)
            missing_arb_pairs = [p for p, valid in arbitrage_validation.items() if not valid]
            
            if missing_arb_pairs:
                self.logger.error("=" * 60)
                self.logger.error("❌ Missing required arbitrage pairs:")
                for pair in missing_arb_pairs:
                    self.logger.error(f"   {pair}")
                self.logger.error("=" * 60)
                self.logger.error("⚠️ System may not work properly without these pairs!")
            else:
                self.logger.info("=" * 60)
                self.logger.info("✅ All required arbitrage pairs are available!")
                self.logger.info("=" * 60)
            
            # Show summary
            self.logger.info("\n" + self.symbol_mapper.get_mapping_summary())
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing symbol mapping: {e}")
        
    
    def start_detection(self):
        """Start the simple trading system"""
        self.is_running = True
        self.logger.info("Starting simple trading system...")
        
        # Run simple trading in separate thread
        self.detection_thread = threading.Thread(target=self._simple_trading_loop, daemon=True)
        self.detection_thread.start()
        self.logger.info("✅ Simple trading thread started")
    
    def stop_detection(self):
        """Stop the arbitrage detection loop"""
        self.is_running = False
        # บันทึกข้อมูลก่อนปิด
        self._save_active_groups()
        self.logger.info("Stopping arbitrage detection...")
    
    def _simple_trading_loop(self):
        """Simple trading loop - ออกไม้ทันทีและต่อเนื่อง"""
        self.logger.info("🚀 Simple trading system started")
        loop_count = 0
        
        while self.is_running:
            try:
                loop_count += 1
                # self.logger.info(f"🔄 Trading loop #{loop_count} - Checking system status...")  # DISABLED - ไม่จำเป็น
                
                # Sync arbitrage orders with MT5
                if hasattr(self, 'correlation_manager') and self.correlation_manager:
                    sync_results = self.correlation_manager.order_tracker.sync_with_mt5()
                    if sync_results.get('arbitrage_orders_removed', 0) > 0:
                        self.logger.debug(f"🔄 Arbitrage sync: {sync_results['arbitrage_orders_removed']} orders removed")
                
                # เช็คจาก MT5 จริงๆ ไม่ใช่จาก memory
                all_positions = self.broker.get_all_positions()
                active_magic_numbers = set()
                
                # หา magic numbers ที่มี positions อยู่จริงใน MT5
                for pos in all_positions:
                    magic = pos.get('magic', 0)
                    if 234001 <= magic <= 234006:  # magic numbers ของ arbitrage groups
                        active_magic_numbers.add(magic)
                
                # ลบ groups ที่ไม่มี positions ใน MT5 ออกจาก memory
                groups_to_remove = []
                for group_id, group_data in list(self.active_groups.items()):
                    triangle_type = group_data.get('triangle_type', 'unknown')
                    triangle_magic = self.triangle_magic_numbers.get(triangle_type, 234000)
                    
                    if triangle_magic not in active_magic_numbers:
                        groups_to_remove.append(group_id)
                
                # ลบ groups ที่ปิดแล้ว
                for group_id in groups_to_remove:
                    self.logger.info(f"🗑️ Group {group_id} closed in MT5 - removing from memory")
                    
                    # Reset hedge tracker ก่อนลบข้อมูล
                    if hasattr(self, 'correlation_manager') and self.correlation_manager:
                        # Reset ไม้ arbitrage ทั้งหมดใน group นี้
                        group_pairs = self.group_currency_mapping.get(group_id, [])
                        for symbol in group_pairs:
                            # Individual order tracker handles cleanup automatically via sync
                            self.logger.info(f"🔄 Reset hedge tracker for {group_id}:{symbol}")
                    
                    # ตรวจสอบว่า group_id มีอยู่จริงก่อนลบ
                    if group_id in self.active_groups:
                        del self.active_groups[group_id]
                        self._save_active_groups()
                        self._reset_group_data_after_close(group_id)
                    else:
                        self.logger.warning(f"⚠️ Group {group_id} not found in active_groups - already removed")
                
                # ตรวจสอบ triangles ที่ปิดแล้วและส่งไม้ใหม่
                closed_triangles = []
                active_triangles = []
                
                # ตรวจสอบแต่ละ triangle
                for i, triangle in enumerate(self.triangle_combinations, 1):
                    triangle_name = f"triangle_{i}"
                    triangle_magic = self.triangle_magic_numbers.get(triangle_name, 234000)
                    
                    if triangle_magic in active_magic_numbers:
                        active_triangles.append(triangle_name)
                        
                        # ตรวจสอบว่าควรปิด Group หรือไม่ (ใช้ Trailing Stop Logic)
                        group_id = f"group_{triangle_name}_1"
                        
                        # ถ้ามี group_data ใน active_groups ให้ใช้ _should_close_group (มี Trailing Stop!)
                        if group_id in self.active_groups:
                            group_data = self.active_groups[group_id]
                            if self._should_close_group(group_id, group_data):
                                self.logger.info(f"✅ Group {triangle_name} meets closing criteria (Trailing Stop) - closing group")
                                self._close_group_by_magic(triangle_magic, group_id)
                                closed_triangles.append(triangle_name)
                        else:
                            # ถ้าไม่มีใน active_groups แต่มี positions ใน MT5 → orphan positions
                            self.logger.warning(f"⚠️ Found orphan positions for {triangle_name} (not in active_groups)")
                            
                            # 🆕 ไม่มีการปิดทันทีอีกต่อไป ให้ reconstruct เสมอ แล้วให้ Trailing Stop เป็นผู้ตัดสินใจ
                            all_positions = self.broker.get_all_positions()
                            orphan_pnl = sum(pos.get('profit', 0) for pos in all_positions if pos.get('magic', 0) == triangle_magic)
                            self.logger.info(f"🔄 Orphan current PnL: ${orphan_pnl:.2f} → Reconstructing group and delegating to Trailing Stop...")
                            self._reconstruct_orphan_group(triangle_name, triangle_magic, group_id)
                        continue
                        
                        # ตรวจสอบ recovery จะทำใน _check_and_close_groups
                    else:
                        # Triangle นี้ปิดแล้ว
                        closed_triangles.append(triangle_name)
                
                # แสดงสถานะเฉพาะเมื่อมีการเปลี่ยนแปลง
                if closed_triangles:
                    self.logger.debug(f"📊 Closed triangles: {closed_triangles}")
                
                # ตรวจสอบและปิด groups ที่มีกำไร (ทำใน loop ข้างบนแล้ว)
                
                # ส่งไม้ใหม่สำหรับ triangles ที่ปิดแล้ว
                if closed_triangles:
                    self.logger.debug(f"🎯 Sending new orders for closed triangles: {closed_triangles}")
                    self._send_orders_for_closed_triangles(closed_triangles)
                else:
                    self.logger.debug("⏭️ No closed triangles to process")
                
                # ถ้าไม่มี triangles ที่เปิดอยู่เลย
                if not active_triangles:
                    self.logger.info("🔄 No active triangles - resetting data")
                    self._reset_group_data()
                
                time.sleep(1.0)  # ⭐ UPGRADED: รอ 1 วินาที (เช็ค trailing stop เร็วขึ้น)
                continue
                    
            except Exception as e:
                self.logger.error(f"Trading error: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                time.sleep(1)
        
        self.logger.info("🛑 Simple trading system stopped")
    
    def _send_orders_for_closed_triangles(self, closed_triangles: List[str]):
        """⭐ ปรับปรุงใหม่ - ตรวจสอบสถานะออเดอร์จริงและ rate limiting"""
        
        # Rate limiting: ตรวจสอบเวลาที่ส่งออเดอร์ล่าสุด
        current_time = time.time()
        if current_time - self.last_order_time < self.min_order_interval:
            self.logger.debug(f"⏳ Rate limiting: waiting {self.min_order_interval - (current_time - self.last_order_time):.1f}s")
            return
        
        # ตรวจสอบ daily order limit
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.daily_order_count = 0
            self.last_reset_date = today
            self.logger.info(f"📅 Daily order count reset for {today}")
        
        if self.daily_order_count >= self.daily_order_limit:
            self.logger.warning(f"⚠️ Daily order limit reached: {self.daily_order_count}/{self.daily_order_limit}")
            return
        
        for triangle_name in closed_triangles:
            if self.is_arbitrage_paused.get(triangle_name, False):
                continue
            
            # ตรวจสอบว่ามีออเดอร์เปิดอยู่สำหรับ triangle นี้หรือไม่
            triangle_magic = self.triangle_magic_numbers.get(triangle_name, 234000)
            existing_positions = self.broker.get_all_positions()
            
            # ตรวจสอบว่ามีออเดอร์ที่ magic number นี้อยู่หรือไม่
            has_existing_orders = any(pos.get('magic', 0) == triangle_magic for pos in existing_positions)
            
            if has_existing_orders:
                self.logger.debug(f"⏭️ {triangle_name}: Still has existing orders (magic: {triangle_magic}) - skipping")
                continue
            
            triangle_index = int(triangle_name.split('_')[-1]) - 1
            if triangle_index < len(self.triangle_combinations):
                triangle = self.triangle_combinations[triangle_index]
                self.logger.debug(f"🚀 Executing new orders for {triangle_name} (no existing orders found)")
                
                # อัปเดตเวลาที่ส่งออเดอร์ล่าสุด
                self.last_order_time = current_time
                
                success = self._execute_new_triangle_orders(triangle, triangle_name)
                
                # นับจำนวนออเดอร์เฉพาะเมื่อสำเร็จ
                if success:
                    self.daily_order_count += 1
                    self.logger.info(f"📊 Order count: {self.daily_order_count}/{self.daily_order_limit}")
                else:
                    self.logger.debug(f"⚠️ Order execution failed for {triangle_name} - not counting")
    
    def _execute_new_triangle_orders(self, triangle, triangle_name):
        """⭐ ปรับปรุงใหม่ - คำนวณทิศทางและตรวจสอบก่อนส่งออเดอร์"""
        try:
            # Track: ตรวจสอบโอกาสใหม่
            self.performance_metrics['opportunities_checked'] += 1
            
            self.logger.info(f"🔍 {triangle_name}: Checking arbitrage conditions for {triangle}")
            
            # 1. คำนวณทิศทางที่ถูกต้อง
            direction_info = self.calculate_arbitrage_direction(triangle)
            
            if not direction_info:
                self.logger.info(f"❌ {triangle_name}: No profitable arbitrage opportunity - skipping")
                return
            
            # Track: ผ่านการตรวจสอบทิศทาง
            self.performance_metrics['passed_direction_check'] += 1
            if direction_info['direction'] == 'forward':
                self.performance_metrics['forward_path_selected'] += 1
            else:
                self.performance_metrics['reverse_path_selected'] += 1
            
            self.logger.info(f"✅ {triangle_name}: Direction check passed - {direction_info['direction'].upper()} path, profit: {direction_info.get('profit_percent', 0):.4f}%")
            
            # 2. ตรวจสอบความเป็นไปได้
            if not self._validate_execution_feasibility(triangle, direction_info):
                self.logger.info(f"❌ {triangle_name}: Failed feasibility check (profit: {direction_info.get('profit_percent', 0):.4f}% too low)")
                return
            
            # Track: ผ่านการตรวจสอบความเป็นไปได้
            self.performance_metrics['passed_feasibility_check'] += 1
            self.logger.info(f"✅ {triangle_name}: Feasibility check passed")
            
            # 3. ดึง balance จาก MT5
            balance = self.broker.get_account_balance()
            if not balance:
                self.logger.error("❌ Cannot get balance from MT5")
                return
            
            self.logger.info(f"💰 {triangle_name}: Account balance: ${balance:,.2f}")
            
            # 4. โหลด risk_per_trade_percent จาก config
            import json
            config_path = 'config/adaptive_params.json'
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            risk_per_trade_percent = config.get('position_sizing', {}).get('lot_calculation', {}).get('risk_per_trade_percent')
            if not risk_per_trade_percent:
                self.logger.error("❌ risk_per_trade_percent not found in config")
                risk_per_trade_percent = 1.0  # fallback
            
            self.logger.info(f"⚙️ {triangle_name}: Risk per trade: {risk_per_trade_percent}%")
            
            risk_per_trade_percent = float(risk_per_trade_percent)
            max_loss_pips = config.get('position_sizing', {}).get('lot_calculation', {}).get('max_loss_pips', 50.0)
            
            # 5. สูตร: Risk Amount = Balance × (Risk% ÷ 100)
            risk_amount = balance * (risk_per_trade_percent / 100.0)
            
            self.logger.info(f"💰 {triangle_name}: Balance=${balance:,.2f}, Risk={risk_per_trade_percent}%, Risk Amount=${risk_amount:.2f}")
            self.logger.info(f"📈 {triangle_name}: {direction_info['direction'].upper()} path - Expected profit: {direction_info['profit_percent']:.4f}%")
            
            # 6. คำนวณ lot สำหรับแต่ละคู่
            triangle_symbols = list(triangle)
            lot_sizes = {}
            
            for symbol in triangle_symbols:
                pip_value = TradingCalculations.calculate_pip_value(symbol, 1.0, self.broker)
                if pip_value <= 0:
                    self.logger.error(f"❌ Invalid pip value for {symbol}")
                    return
                
                # สูตร: Lot = Risk Amount ÷ (Pip Value × Max Loss Pips)
                lot_size = risk_amount / (pip_value * max_loss_pips)
                lot_size = max(0.01, round(lot_size, 2))
                
                lot_sizes[symbol] = lot_size
                self.logger.debug(f"   {symbol}: pip_value=${pip_value:.2f}, lot={lot_size:.2f}")
            
            # 7. ตรวจสอบความสมดุลของ Triangle
            balance_ok = self._verify_triangle_balance(triangle, lot_sizes)
            if balance_ok:
                self.performance_metrics['passed_balance_check'] += 1
                self.logger.info(f"✅ {triangle_name}: Triangle balance check passed")
            else:
                self.logger.warning(f"⚠️ {triangle_name}: Triangle not balanced, adjusting...")
                # ยังคงส่งต่อไป แต่เตือน (เพราะ deviation อาจยอมรับได้)
            
            # Track: บันทึกกำไรที่คาดหวัง
            expected_profit = direction_info.get('profit_percent', 0)
            self.performance_metrics['total_expected_profit'] += expected_profit
            if self.performance_metrics['passed_feasibility_check'] > 0:
                self.performance_metrics['avg_expected_profit'] = (
                    self.performance_metrics['total_expected_profit'] / 
                    self.performance_metrics['passed_feasibility_check']
                )
            
            # 8. ส่งออเดอร์พร้อมทิศทางที่คำนวณแล้ว
            self.logger.info(f"🚀 {triangle_name}: All checks passed! Sending orders...")
            success = self._send_new_triangle_orders(triangle, triangle_name, lot_sizes, direction_info)
            
            if success:
                self.performance_metrics['successful_trades'] += 1
                self.logger.info(f"🎉 {triangle_name}: All orders placed successfully!")
            else:
                self.logger.error(f"❌ {triangle_name}: Failed to place orders")
            
        except Exception as e:
            self.logger.error(f"Error in _execute_new_triangle_orders: {e}")
    
    def _send_new_triangle_orders(self, triangle, triangle_name, lot_sizes, direction_info):
        """⭐ ปรับปรุงใหม่ - ใช้ทิศทางที่คำนวณได้จาก direction_info"""
        try:
            triangle_symbols = list(triangle)
            triangle_magic = self.triangle_magic_numbers.get(triangle_name, 234000)
            
            # ดึงทิศทางที่คำนวณไว้
            orders_direction = direction_info.get('orders', {})
            path_direction = direction_info.get('direction', 'unknown')
            expected_profit = direction_info.get('profit_percent', 0)
            
            self.logger.info(f"🚀 Sending {path_direction.upper()} arbitrage for {triangle_name}: {triangle_symbols}")
            self.logger.info(f"   Expected Net Profit: {expected_profit:.4f}%")
            
            placed_orders = []
            
            # ส่งออเดอร์สำหรับแต่ละคู่ตามทิศทางที่คำนวณ
            for symbol in triangle_symbols:
                # ใช้ทิศทางจาก direction_info (ไม่ใช่ hard-coded)
                direction = orders_direction.get(symbol, 'BUY')
                lot_size = lot_sizes.get(symbol, 0.01)
                
                # สร้าง comment ตามหมายเลขสามเหลี่ยม
                triangle_number = triangle_name.split('_')[-1]  # ได้ 1, 2, 3, 4, 5, 6
                comment = f"G{triangle_number}_{symbol}_{direction[:1]}"  # เช่น G1_EURUSD_B
                
                # ส่งออเดอร์ (ใช้ real symbol จาก SymbolMapper)
                real_symbol = self.symbol_mapper.get_real_symbol(symbol)
                result = self.broker.place_order(
                    symbol=real_symbol,
                    order_type=direction,
                    volume=lot_size,
                    comment=comment,
                    magic=triangle_magic
                )
                
                if result and result.get('success', False):
                    placed_orders.append({
                        'symbol': symbol,
                        'direction': direction,
                        'lot_size': lot_size,
                        'ticket': result.get('ticket')
                    })
                    self.logger.info(f"✅ {symbol} {direction} {lot_size} lots - SUCCESS (Ticket: {result.get('ticket')})")
                else:
                    # ถ้าออเดอร์ล้มเหลว ยกเลิกทั้งหมดเพื่อไม่ให้เหลือ partial fill
                    error_msg = result.get('error', 'Unknown error') if result else 'No result'
                    self.logger.error(f"❌ {symbol} {direction} {lot_size} lots - FAILED: {error_msg}")
                    self.logger.warning(f"🔄 Cancelling all orders for {triangle_name} due to failure")
                    
                    # Track: นับจำนวนครั้งที่ยกเลิกออเดอร์
                    self.performance_metrics['orders_cancelled_due_to_failure'] += len(placed_orders)
                    
                    # ยกเลิกออเดอร์ที่ส่งไปแล้ว
                    for order in placed_orders:
                        try:
                            self.broker.close_position(order['ticket'])
                            self.logger.info(f"🔄 Cancelled {order['symbol']} (Ticket: {order['ticket']})")
                        except Exception as cancel_error:
                            self.logger.error(f"Error cancelling order {order['ticket']}: {cancel_error}")
                    
                    return False
            
            # บันทึกข้อมูล arbitrage ที่สำเร็จ
            self.logger.info(f"✅ {triangle_name}: All {len(placed_orders)} orders placed successfully!")
            return True
                    
        except Exception as e:
            self.logger.error(f"Error in _send_new_triangle_orders: {e}")
            return False
    
    def _send_simple_orders(self):
        """⭐ ฟังก์ชันใหม่ - ใช้แค่สูตรใหม่เท่านั้น"""
        try:
            all_positions = self.broker.get_all_positions()
            arbitrage_positions = [pos for pos in all_positions if 234001 <= pos.get('magic', 0) <= 234006]
            
            if not arbitrage_positions:
                for i, triangle in enumerate(self.triangle_combinations):
                    triangle_name = f"triangle_{i+1}"
                    if not self.is_arbitrage_paused.get(triangle_name, False):
                        self._execute_new_triangle_orders(triangle, triangle_name)
                        
        except Exception as e:
            self.logger.error(f"Error in _send_simple_orders: {e}")
    
    def _sync_active_groups_from_mt5(self, arbitrage_positions):
        """ซิงค์ข้อมูล active groups จาก MT5"""
        try:
            # เก็บข้อมูลกลุ่มจาก MT5
            mt5_groups = {}
            
            for pos in arbitrage_positions:
                magic = pos.get('magic', 0)
                comment = pos.get('comment', '')
                symbol = pos.get('symbol', '')
                
                # หาสามเหลี่ยมจาก magic number
                triangle_type = None
                for triangle_name, magic_num in self.triangle_magic_numbers.items():
                    if magic == magic_num:
                        triangle_type = triangle_name
                        break
                
                if triangle_type:
                    # แยก triangle number จาก magic number (ไม่ใช้ comment แล้ว)
                    triangle_number = triangle_type.split('_')[-1]  # ได้ 1, 2, 3, 4, 5, 6
                    group_id = f"group_{triangle_type}_{triangle_number}"
                    
                    if group_id not in mt5_groups:
                        mt5_groups[group_id] = {
                            'group_id': group_id,
                            'triangle_type': triangle_type,
                            'created_at': datetime.now(),
                            'positions': [],
                            'status': 'active',
                            'total_pnl': 0.0,
                            'recovery_chain': [],
                            'lot_sizes': {}
                        }
                    
                    # เพิ่มตำแหน่ง
                    mt5_groups[group_id]['positions'].append({
                        'symbol': symbol,
                        'order_id': pos.get('ticket'),
                        'lot_size': pos.get('volume'),
                        'entry_price': pos.get('price', 0.0),
                        'direction': pos.get('type', 'BUY'),
                        'comment': comment,
                        'magic': magic
                    })
            
            # อัปเดต active_groups
            self.active_groups = mt5_groups
            
            # อัปเดต used_currency_pairs
            for group_id, group_data in mt5_groups.items():
                triangle_type = group_data.get('triangle_type')
                if triangle_type and triangle_type not in self.used_currency_pairs:
                    self.used_currency_pairs[triangle_type] = set()
                
                for pos in group_data.get('positions', []):
                    symbol = pos.get('symbol')
                    if symbol and triangle_type:
                        self.used_currency_pairs[triangle_type].add(symbol)
            
            self.logger.info(f"🔄 Synced {len(mt5_groups)} groups from MT5")
            
        except Exception as e:
            self.logger.error(f"Error syncing active groups from MT5: {e}")
    
    def _load_tier_config(self):
        """โหลดการตั้งค่า Account Tier จาก config"""
        try:
            import json
            with open('config/adaptive_params.json', 'r', encoding='utf-8') as f:
                self.tier_config = json.load(f)
        except UnicodeDecodeError as e:
            self.logger.error(f"Unicode decode error in config file: {e}")
            # Try with different encodings
            for encoding in ['cp1252', 'latin-1', 'iso-8859-1']:
                try:
                    with open('config/adaptive_params.json', 'r', encoding=encoding) as f:
                        self.tier_config = json.load(f)
                    self.logger.info(f"Successfully loaded config with {encoding} encoding")
                    return
                except:
                    continue
            self.logger.error("Failed to load config with any encoding")
            self.tier_config = {}
        except Exception as e:
            self.logger.error(f"Error loading tier config: {e}")
            self.tier_config = {}
    
    def _get_config_value(self, path: str, default_value=None):
        """ดึงค่าจาก config โดยใช้ dot notation"""
        try:
            keys = path.split('.')
            value = self.tier_config
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default_value
            return value
        except Exception as e:
            self.logger.error(f"Error getting config value {path}: {e}")
            return default_value
    
    def reload_config(self):
        """โหลด config ใหม่ (สำหรับ GUI Settings)"""
        try:
            self._load_tier_config()
            # Removed AccountTierManager - using GUI Risk per Trade only  # รีโหลด tier manager
            
            # 🔄 Cache lot calculation config เพื่อไม่ต้องโหลดทุกครั้ง
            import json
            with open('config/adaptive_params.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.lot_calc_config = config.get('position_sizing', {}).get('lot_calculation', {})
            
            self.logger.info("✅ Account Tier config reloaded successfully")
            self.logger.info(f"🔍 Cached lot calc config: {self.lot_calc_config}")
        except Exception as e:
            self.logger.error(f"Error reloading tier config: {e}")
    
    # ⭐ ฟังก์ชันเก่าถูกลบแล้ว - ใช้ _execute_new_triangle_orders และ _send_new_triangle_orders แทน
    
    def check_group_status(self):
        """ตรวจสอบสถานะของกลุ่มที่เปิดอยู่"""
        try:
            self.logger.debug(f"🔍 Checking group status - Active groups: {len(self.active_groups)}")
            
            if not self.active_groups:
                # ถ้าไม่มีกลุ่มที่เปิดอยู่ ให้ reset ข้อมูล
                self.logger.debug("No active groups found - resetting group data")
                self._reset_group_data()
                return
            
            groups_to_close = []
            
            for group_id, group_data in list(self.active_groups.items()):
                # 🆕 ลบ Timeout 24h - Never Cut Loss = Never Expire!
                # ให้ _should_close_group() (Trailing Stop) ตัดสินเดี่ยว
                
                # ตรวจสอบ PnL จริงของแต่ละตำแหน่ง (รวม recovery positions)
                total_group_pnl = 0.0
                all_positions_profitable = True
                valid_positions = 0
                
                # คำนวณ PnL ของ arbitrage positions
                for position in group_data['positions']:
                    # หา order_id จาก broker API
                    order_id = position.get('order_id')
                    if order_id:
                        # ตรวจสอบ PnL จาก broker API
                        all_positions = self.broker.get_all_positions()
                        position_pnl = 0.0
                        position_found = False
                        
                        for pos in all_positions:
                            if pos['ticket'] == order_id:
                                position_pnl = pos['profit']
                                position_found = True
                                valid_positions += 1
                                break
                        
                        if position_found:
                            total_group_pnl += position_pnl
                            
                            # ตรวจสอบว่าตำแหน่งนี้กำไรหรือไม่
                            if position_pnl < 0:
                                all_positions_profitable = False
                            
                            self.logger.debug(f"   Arbitrage {position['symbol']}: PnL = {position_pnl:.2f} USD")
                        else:
                            self.logger.warning(f"   Position {position['symbol']} not found in broker - may be closed")
                    else:
                        self.logger.warning(f"   No order_id found for position {position['symbol']}")
                        all_positions_profitable = False
                
                # คำนวณ PnL ของ recovery positions ที่เกี่ยวข้องกับกลุ่มนี้ (using order_tracker)
                recovery_pnl = 0.0
                if self.correlation_manager:
                    all_orders = self.correlation_manager.order_tracker.get_all_orders()
                    all_positions = self.broker.get_all_positions()
                    
                    for order_key, order_data in all_orders.items():
                        # Only count recovery orders for this group
                        if (order_data.get('type') == 'RECOVERY' and 
                            order_data.get('group_id') == group_id):
                            recovery_ticket = order_data.get('ticket')
                            if recovery_ticket:
                                # ตรวจสอบ PnL ของ recovery position จาก MT5
                                for pos in all_positions:
                                    if str(pos.get('ticket')) == str(recovery_ticket):
                                        recovery_pnl += pos.get('profit', 0)
                                        symbol = order_data.get('symbol', 'N/A')
                                        self.logger.debug(f"   Recovery {symbol}: PnL = {pos['profit']:.2f} USD")
                                        break
                
                # รวม PnL ทั้งหมด (arbitrage + recovery)
                total_group_pnl += recovery_pnl
                if recovery_pnl != 0:
                    self.logger.info(f"   🔄 Recovery PnL: {recovery_pnl:.2f} USD")
                
                # ถ้าไม่มีตำแหน่งที่เปิดอยู่จริง ให้ลบกลุ่มนี้ทันที
                if valid_positions == 0:
                    self.logger.info(f"🗑️ Group {group_id} has no valid positions - removing from active groups")
                    # ลบ Group ออกจาก active_groups ทันที
                    if group_id in self.active_groups:
                        del self.active_groups[group_id]
                    # ลบ Group ออกจาก group_currency_mapping
                    if group_id in self.group_currency_mapping:
                        del self.group_currency_mapping[group_id]
                    # ลบ Group ออกจาก recovery_in_progress
                    if group_id in self.recovery_in_progress:
                        self.recovery_in_progress.remove(group_id)
                    # บันทึกการเปลี่ยนแปลง
                    self._save_active_groups()
                    continue
                
                # แสดงผล PnL รวมของกลุ่ม (เฉพาะเมื่อมีการเปลี่ยนแปลงมาก)
                pnl_status = "💰" if total_group_pnl > 0 else "💸" if total_group_pnl < 0 else "⚖️"
                # self.logger.info(f"📊 Group {group_id} PnL: {pnl_status} {total_group_pnl:.2f} USD")  # DISABLED - too verbose
                
                # คำนวณ % ของทุนจาก broker API (ใช้ Balance ไม่ใช่ Equity)
                account_balance = self.broker.get_account_balance()
                if account_balance is None:
                    account_balance = 1000.0  # fallback ถ้าไม่สามารถดึงได้
                    self.logger.warning("⚠️ Cannot get account balance, using fallback: 1000 USD")
                
                profit_percentage = (total_group_pnl / account_balance) * 100
                # self.logger.info(f"   💰 Account Balance: {account_balance:.2f} USD")  # DISABLED - too verbose
                # self.logger.info(f"   📊 Profit Percentage: {profit_percentage:.3f}%")  # DISABLED - too verbose
                
                # 🆕 ใช้ _should_close_group() แทน logic เก่า (มี Trailing Stop + Never Cut Loss!)
                if self._should_close_group(group_id, group_data):
                    self.logger.info(f"✅ Group {group_id} meets closing criteria (Trailing Stop)")
                    groups_to_close.append(group_id)
                elif total_group_pnl < 0:
                    # ถ้ายังติดลบ ตรวจสอบว่าควรเริ่ม recovery หรือไม่
                    triangle_type = group_data.get('triangle_type', 'unknown')
                    triangle_magic = self.triangle_magic_numbers.get(triangle_type, 234000)
                    
                    if self._should_start_recovery_from_mt5(triangle_magic, triangle_type):
                        # เริ่ม correlation recovery ตามเงื่อนไขที่กำหนด
                        self._start_correlation_recovery(group_id, group_data, total_group_pnl)
            
            # ปิดกลุ่มที่ครบเงื่อนไข
            if groups_to_close:
                self.logger.info(f"🎯 Found {len(groups_to_close)} groups to close: {groups_to_close}")
                for group_id in groups_to_close:
                    self.logger.info(f"🔄 Closing group {group_id}")
                    self._close_group(group_id)
            else:
                self.logger.debug("No groups meet closing criteria")
                
        except Exception as e:
            self.logger.error(f"Error checking group status: {e}")
            
    def _should_start_recovery_from_mt5(self, magic_num: int, triangle_type: str) -> bool:
        """ตรวจสอบว่าควรเริ่ม recovery หรือไม่ - เช็คจาก MT5 จริงๆ"""
        try:
            all_positions = self.broker.get_all_positions()
            group_positions = []
            total_pnl = 0.0
            
            for pos in all_positions:
                if pos.get('magic', 0) == magic_num:
                    group_positions.append(pos)
                    total_pnl += pos.get('profit', 0)
            
            if not group_positions:
                return False
            
            # ตรวจสอบว่ามีการขาดทุนหรือไม่
            if total_pnl >= 0:
                self.logger.info(f"💰 Group {triangle_type} has profit: ${total_pnl:.2f} - No recovery needed")
                # แสดงสถานะไม้ทั้งหมดแม้ว่า Group จะมีกำไร
                self._log_group_status_for_recovery(magic_num, triangle_type, group_positions, total_pnl, 0.0)
                return False
            
            # คำนวณ risk per lot
            total_lot_size = sum(pos.get('volume', 0) for pos in group_positions)
            if total_lot_size <= 0:
                return False
                
            risk_per_lot = abs(total_pnl) / total_lot_size
            
            # ไม่ใช้เงื่อนไข risk แล้ว - แสดงข้อมูลเท่านั้น
            # self.logger.info(f"📊 Group {triangle_type} risk: {risk_per_lot:.2%} (info only)")
            
            # ตรวจสอบระยะห่างราคา
            max_price_distance = 0
            
            for pos in group_positions:
                symbol = pos.get('symbol', '')
                entry_price = pos.get('price', 0)
                
                try:
                    current_price = self.broker.get_current_price(symbol)
                    if entry_price > 0 and current_price > 0:
                        if 'JPY' in symbol:
                            price_distance = abs(current_price - entry_price) * 100
                        else:
                            price_distance = abs(current_price - entry_price) * 10000
                        
                        max_price_distance = max(max_price_distance, price_distance)
                except Exception as e:
                    continue
            
            
            if max_price_distance < 10:  # ระยะห่างน้อยกว่า 10 จุด
                # แสดงสถานะไม้ทั้งหมดแม้ว่า distance จะไม่ถึง 10 pips
                self._log_group_status_for_recovery(magic_num, triangle_type, group_positions, total_pnl, max_price_distance)
                return False
            
            # ผ่านเงื่อนไขทั้งหมด - แก้ไม้ทันที
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking if should start recovery from MT5: {e}")
            return False
    
    def _log_group_status_for_recovery(self, magic_num: int, triangle_type: str, group_positions: List[Dict], total_pnl: float, max_price_distance: float):
        """แสดงสถานะไม้ทั้งหมดในกลุ่มสำหรับ recovery"""
        try:
            # สร้าง group_id จาก triangle_type
            group_id = f"group_{triangle_type}_1"
            
            # สร้าง losing_pairs list จาก group_positions
            losing_pairs = []
            for pos in group_positions:
                if pos.get('profit', 0) < 0:
                    losing_pairs.append({
                        'symbol': pos.get('symbol', ''),
                        'order_id': pos.get('ticket', ''),
                        'lot_size': pos.get('volume'),
                        'entry_price': pos.get('price', 0),
                        'pnl': pos.get('profit', 0),
                        'comment': pos.get('comment', ''),
                        'magic': pos.get('magic', 0)
                    })
            
            # ลด log ที่ซ้ำ - ใช้แค่ _log_all_groups_status แทน
            # self.correlation_manager._log_group_hedging_status(group_id, losing_pairs)
            
        except Exception as e:
            self.logger.error(f"Error logging group status for recovery: {e}")
    
    def _close_group_by_magic(self, magic_num: int, group_id: str):
        """ปิด Group โดยใช้ magic number"""
        try:
            all_positions = self.broker.get_all_positions()
            positions_to_close = []
            
            for pos in all_positions:
                if pos.get('magic', 0) == magic_num:
                    positions_to_close.append(pos)
            
            if not positions_to_close:
                self.logger.warning(f"No positions found for magic {magic_num}")
                return
            
            # 🆕 Safety Check: คำนวณ Net PnL ก่อนปิด (Never Cut Loss!)
            arbitrage_pnl = sum(pos.get('profit', 0) for pos in positions_to_close)
            recovery_pnl = 0.0
            if self.correlation_manager:
                recovery_pnl = self._get_recovery_pnl_for_group(group_id)
            
            net_pnl = arbitrage_pnl + recovery_pnl
            
            self.logger.info(f"💰 Closing Group {group_id}:")
            self.logger.info(f"   Arbitrage PnL: ${arbitrage_pnl:.2f}")
            self.logger.info(f"   Recovery PnL: ${recovery_pnl:.2f}")
            self.logger.info(f"   Net PnL: ${net_pnl:.2f}")
            
            if net_pnl < 0:
                self.logger.error(f"❌❌❌ BLOCKED! Net PnL is NEGATIVE: ${net_pnl:.2f}")
                self.logger.error(f"   NEVER CUT LOSS! Group {group_id} will NOT be closed!")
                self.logger.error(f"   Waiting for recovery to turn profitable...")
                return
            
            self.logger.info(f"✅ Net PnL is POSITIVE (${net_pnl:.2f}) - Proceeding to close...")
            
            # ปิด positions ทั้งหมด
            for pos in positions_to_close:
                try:
                    result = self.broker.close_position(pos.get('ticket'))
                    if result and result.get('success'):
                        self.logger.info(f"✅ Closed: {pos.get('symbol')} {pos.get('type')} (Order: {pos.get('ticket')})")
                    else:
                        self.logger.warning(f"❌ Failed to close: {pos.get('symbol')} {pos.get('type')}")
                except Exception as e:
                    self.logger.error(f"Error closing position {pos.get('ticket')}: {e}")
            
            # Reset hedge tracker ก่อนลบข้อมูล
            if hasattr(self, 'correlation_manager') and self.correlation_manager:
                # Reset ไม้ arbitrage ทั้งหมดใน group นี้
                group_pairs = self.group_currency_mapping.get(group_id, [])
                for symbol in group_pairs:
                    # Individual order tracker handles cleanup automatically via sync
                    self.logger.info(f"🔄 Reset hedge tracker for {group_id}:{symbol}")
            
            # ลบจาก memory และ reset ข้อมูล
            if group_id in self.active_groups:
                del self.active_groups[group_id]
            self._save_active_groups()
            self._reset_group_data_after_close(group_id)
            
            self.logger.info(f"✅ Group {group_id} closed successfully")
            
        except Exception as e:
            self.logger.error(f"Error closing group by magic: {e}")
    
    def _reconstruct_orphan_group(self, triangle_name: str, triangle_magic: int, group_id: str):
        """Reconstruct orphan group data from MT5 positions"""
        try:
            self.logger.info(f"🔄 Attempting to reconstruct orphan group: {group_id}")
            
            # ดึง positions จาก MT5
            all_positions = self.broker.get_all_positions()
            orphan_positions = [pos for pos in all_positions if pos.get('magic', 0) == triangle_magic]
            
            if not orphan_positions:
                self.logger.warning(f"⚠️ No positions found for reconstruction")
                return
            
            # สร้าง group_data ใหม่
            group_data = {
                'group_id': group_id,
                'triangle': self.triangle_combinations[int(triangle_name.split('_')[1]) - 1] if len(self.triangle_combinations) >= int(triangle_name.split('_')[1]) else ('EURUSD', 'GBPUSD', 'EURGBP'),
                'triangle_type': triangle_name,
                'created_at': datetime.now(),  # ใช้เวลาปัจจุบัน
                'positions': [],
                'status': 'active',
                'total_pnl': 0.0,
                'recovery_chain': []
            }
            
            # เพิ่ม positions ลง group_data
            for pos in orphan_positions:
                group_data['positions'].append({
                    'symbol': pos.get('symbol', ''),
                    'direction': pos.get('type', 'BUY'),
                    'order_id': pos.get('ticket'),
                    'lot_size': pos.get('volume', 0.1),
                    'entry_price': pos.get('price', 0.0),
                    'entry_time': datetime.now()  # ไม่รู้เวลาจริง ใช้ปัจจุบัน
                })
            
            # บันทึกลง active_groups
            self.active_groups[group_id] = group_data
            self._save_active_groups()
            
            self.logger.info(f"✅ Reconstructed orphan group: {group_id} with {len(orphan_positions)} positions")
            self.logger.info(f"   Group will now be managed by Trailing Stop logic")
            
        except Exception as e:
            self.logger.error(f"❌ Error reconstructing orphan group: {e}")
    
    def _should_close_group(self, group_id: str, group_data: Dict) -> bool:
        """ตรวจสอบว่าควรปิด Group หรือไม่ - ตรวจสอบกำไรรวม"""
        try:
            # ดึงข้อมูล positions จาก MT5 โดยใช้ magic number
            triangle_type = group_data.get('triangle_type', 'unknown')
            triangle_magic = self.triangle_magic_numbers.get(triangle_type, 234000)
            
            all_positions = self.broker.get_all_positions()
            group_positions = []
            total_pnl = 0.0
            
            for pos in all_positions:
                magic = pos.get('magic', 0)
                if magic == triangle_magic:
                    group_positions.append(pos)
                    total_pnl += pos.get('profit', 0)
            
            if not group_positions:
                self.logger.warning(f"⚠️ No positions found for group {group_id} (Magic: {triangle_magic})")
                self.logger.warning(f"   This could be a timing issue or positions already closed")
                return False  # ✅ ไม่ปิด! (Never Cut Loss - หา positions ไม่เจอไม่ควรปิด)
            
            # ✅ NEW: ดึง recovery PnL และคำนวณ net PnL
            recovery_pnl = 0.0
            if self.correlation_manager:
                recovery_pnl = self._get_recovery_pnl_for_group(group_id)
            
            net_pnl = total_pnl + recovery_pnl
            
            # 🆕 STEP 1: คำนวณ Min Profit Threshold (Scale with Balance)
            balance = self.broker.get_account_balance()
            if not balance or balance <= 0:
                balance = 10000.0  # Fallback
            
            # ⭐ ใช้ min_profit_base ตรงๆ ไม่คูณด้วย balance_multiplier
            min_profit_threshold = self.min_profit_base
            
            self.logger.debug(f"💰 {group_id}: Balance=${balance:.2f}, Min Profit=${min_profit_threshold:.2f} (Base $10 @ $10K)")
            
            # 🆕 STEP 2: Trailing Stop Logic (เช็ค trailing_stop_enabled ก่อน)
            if self.trailing_stop_enabled:
                if group_id not in self.group_trailing_stops:
                    self.group_trailing_stops[group_id] = {
                        'peak': 0.0,
                        'stop': 0.0,
                        'active': False
                    }
                
                trailing_data = self.group_trailing_stops[group_id]
                
                # ถ้ากำไรเกิน min_profit → เริ่ม trailing stop
                if net_pnl >= min_profit_threshold:
                    if not trailing_data['active']:
                        # เริ่ม trailing stop
                        trailing_data['active'] = True
                        trailing_data['peak'] = net_pnl
                        # 🔒 Lock 50% of Peak: Stop = max(Peak × 0.5, Peak - Distance)
                        trailing_data['stop'] = max(net_pnl * self.lock_profit_percentage, net_pnl - self.trailing_stop_distance)
                        self.logger.info(f"🎯 {group_id} Trailing Stop ACTIVATED: Peak=${net_pnl:.2f}, Stop=${trailing_data['stop']:.2f} (Lock {self.lock_profit_percentage*100:.0f}%)")
                    else:
                        # อัปเดต peak ถ้ากำไรเพิ่ม
                        if net_pnl > trailing_data['peak']:
                            trailing_data['peak'] = net_pnl
                            # 🔒 Lock 50% of Peak: Stop = max(Peak × 0.5, Peak - Distance)
                            trailing_data['stop'] = max(net_pnl * self.lock_profit_percentage, net_pnl - self.trailing_stop_distance)
                            self.logger.info(f"📈 {group_id} Peak Updated: ${net_pnl:.2f}, Stop=${trailing_data['stop']:.2f} (Lock {self.lock_profit_percentage*100:.0f}%)")
                        
                        # เช็คว่า hit trailing stop ไหม (และต้องกำไรด้วย!)
                        if net_pnl < trailing_data['stop'] and net_pnl > 0:
                            self.logger.info(f"🚨 {group_id} TRAILING STOP HIT!")
                            self.logger.info(f"   Peak: ${trailing_data['peak']:.2f}")
                            self.logger.info(f"   Stop: ${trailing_data['stop']:.2f}")
                            self.logger.info(f"   Current Net: ${net_pnl:.2f}")
                            self.logger.info(f"   Locking profit: ${net_pnl:.2f} ✅")
                            return True
                        elif net_pnl < trailing_data['stop'] and net_pnl <= 0:
                            # ถ้า hit stop แต่ติดลบ → ยกเลิก trailing, รอ recovery
                            self.logger.warning(f"⚠️ {group_id} Hit stop but negative (${net_pnl:.2f}) - Canceling trailing, waiting for recovery")
                            trailing_data['active'] = False
                            trailing_data['peak'] = 0.0
                            trailing_data['stop'] = 0.0
            else:
                # Trailing Stop ปิดอยู่ — ใช้ Min Profit เพียงอย่างเดียว
                if net_pnl >= min_profit_threshold:
                    self.logger.info(f"✅ {group_id} Min Profit Reached: ${net_pnl:.2f} >= ${min_profit_threshold:.2f} (Trailing Stop DISABLED)")
                    return True
            
            # 🆕 STEP 3: ไม่ปิดทันทีที่ถึง Min Profit — ให้ Trailing Stop ควบคุมเท่านั้น
            # หากเพิ่งถึงขั้นต่ำ ให้รอให้ trailing_data['active'] ถูกตั้งในรอบนี้ แล้วค่อยพิจารณา HIT ในรอบถัดไป
            
            # ✅ FALLBACK: แสดงสถานะถ้ากำไรแต่ยังไม่ถึง threshold
            if net_pnl > 0:
                self.logger.debug(f"💰 Group {group_id} profitable but below threshold:")
                self.logger.debug(f"   Net PnL: ${net_pnl:.2f} < Min ${min_profit_threshold:.2f}")
                if trailing_data['active']:
                    self.logger.debug(f"   Trailing: Peak=${trailing_data['peak']:.2f}, Stop=${trailing_data['stop']:.2f}")
            
            # ✅ Never Cut Loss: ไม่ปิดถ้ายังติดลบ (เฉพาะปิดเมื่อกำไรเท่านั้น)
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking if should close group: {e}")
            return False
    
    
    def _start_correlation_recovery(self, group_id: str, group_data: Dict, total_pnl: float):
        """🆕 เริ่ม Smart Recovery สำหรับกลุ่มที่ขาดทุน"""
        try:
            if not self.correlation_manager:
                self.logger.warning("Correlation manager not available")
                return
            
            # 🆕 ใช้ Smart Recovery Flow แทนการส่งข้อมูลแบบเก่า
            # ตั้งค่าว่ากำลัง recovery
            self.recovery_in_progress.add(group_id)
            
            # Smart Recovery จะทำงานผ่าน check_recovery_positions() อัตโนมัติ
            # ไม่ต้องส่งข้อมูลแบบเก่าแล้ว เพราะ Smart Recovery หาเองจาก MT5
            
        except Exception as e:
            self.logger.error(f"Error starting smart recovery: {e}")
    
    def _close_group(self, group_id: str):
        """ปิดกลุ่ม arbitrage พร้อมกันทั้งกลุ่ม"""
        try:
            if group_id not in self.active_groups:
                return
            
            group_data = self.active_groups[group_id]
            
            # ปิดออเดอร์พร้อมกันทั้งกลุ่มด้วย threading (ใช้ magic number)
            triangle_type = group_data.get('triangle_type', 'unknown')
            triangle_magic = self.triangle_magic_numbers.get(triangle_type, 234000)
            
            # ดึงข้อมูล positions จาก MT5 โดยใช้ magic number
            all_positions = self.broker.get_all_positions()
            positions_to_close = []
            for pos in all_positions:
                magic = pos.get('magic', 0)
                if magic == triangle_magic:
                    positions_to_close.append(pos)
            
            # 🆕 FINAL SAFETY CHECK: คำนวณ Net PnL อีกครั้งก่อนปิด! (Never Cut Loss!)
            arbitrage_pnl = sum(pos.get('profit', 0) for pos in positions_to_close)
            recovery_pnl = 0.0
            if self.correlation_manager:
                recovery_pnl = self._get_recovery_pnl_for_group(group_id)
            
            net_pnl = arbitrage_pnl + recovery_pnl
            
            self.logger.info(f"🔍 FINAL CHECK before closing Group {group_id}:")
            self.logger.info(f"   Arbitrage PnL: ${arbitrage_pnl:.2f}")
            self.logger.info(f"   Recovery PnL: ${recovery_pnl:.2f}")
            self.logger.info(f"   Net PnL: ${net_pnl:.2f}")
            
            if net_pnl < 0:
                self.logger.error(f"❌❌❌ BLOCKED! Net PnL turned NEGATIVE: ${net_pnl:.2f}")
                self.logger.error(f"   Price moved during execution window (Race Condition)!")
                self.logger.error(f"   NEVER CUT LOSS! Group {group_id} will NOT be closed!")
                self.logger.error(f"   Canceling Trailing Stop, waiting for recovery...")
                
                # ยกเลิก Trailing Stop (ให้เริ่มใหม่เมื่อกลับมาบวก)
                if group_id in self.group_trailing_stops:
                    self.group_trailing_stops[group_id]['active'] = False
                    self.group_trailing_stops[group_id]['peak'] = 0.0
                    self.group_trailing_stops[group_id]['stop'] = 0.0
                    self.logger.warning(f"   🔄 Trailing Stop canceled for {group_id}")
                
                return
            
            self.logger.info(f"✅ Net PnL is POSITIVE (${net_pnl:.2f}) - Proceeding to close...")
            self.logger.info(f"🔄 Closing arbitrage group {group_id}")
            self.logger.info(f"   🚀 Closing orders simultaneously...")
            
            orders_closed = 0
            close_results = []
            
            # สร้างข้อมูลการปิดออเดอร์
            close_orders = []
            for i, position in enumerate(positions_to_close):
                close_orders.append({
                    'symbol': position.get('symbol', ''),
                    'direction': position.get('type', 'BUY'),
                    'group_id': group_id,
                    'order_id': position.get('ticket'),
                    'comment': position.get('comment', ''),
                    'magic': position.get('magic', 0),
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
                        triangle_type = group_data.get('triangle_type', 'unknown')
                        triangle_number = triangle_type.split('_')[-1]  # ได้ 1, 2, 3, 4, 5, 6
                        expected_comment = f"ARB_G{triangle_number}_{order_data['symbol']}"
                        
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
                    self.logger.info(f"   ✅ {result['symbol']} {result['direction']} {pnl_status} ${pnl:.2f}")
                elif result:
                    self.logger.warning(f"   ❌ Failed to close: {result['symbol']} {result['direction']}")
                    if 'error' in result:
                        self.logger.error(f"      Error: {result['error']}")
            
            # ลบคู่เงินและ comment ออกจากรายการที่ใช้แล้ว
            if group_id in self.group_currency_mapping:
                group_pairs = self.group_currency_mapping[group_id]
                # ลบคู่เงินจาก used_currency_pairs สำหรับสามเหลี่ยมนี้
                triangle_type = group_data.get('triangle_type', 'triangle_1')
                if triangle_type in self.used_currency_pairs:
                    for pair in group_pairs:
                        self.used_currency_pairs[triangle_type].discard(pair)
                del self.group_currency_mapping[group_id]
                self.logger.info(f"   📊 คู่เงินที่ปลดล็อค: {group_pairs}")
                        
            # ปิด recovery positions ที่เกี่ยวข้องกับกลุ่มนี้ (using order_tracker)
            correlation_pnl = 0.0
            recovery_positions_closed = 0
            if self.correlation_manager:
                # _close_recovery_positions_for_group returns (pnl, count)
                correlation_pnl, recovery_positions_closed = self._close_recovery_positions_for_group(group_id)
                # ล้างข้อมูลการแก้ไม้สำหรับกลุ่มนี้
                self.correlation_manager.clear_hedged_data_for_group(group_id)
            
            # Reset hedge tracker ก่อนลบข้อมูล
            if hasattr(self, 'correlation_manager') and self.correlation_manager:
                # Reset ไม้ arbitrage ทั้งหมดใน group นี้
                group_pairs = self.group_currency_mapping.get(group_id, [])
                for symbol in group_pairs:
                    # Individual order tracker handles cleanup automatically via sync
                    self.logger.info(f"🔄 Reset hedge tracker for {group_id}:{symbol}")
            
            # ลบกลุ่มออกจาก active_groups
            self._remove_group_data(group_id)
            
            # Reset ข้อมูลหลังจากปิด Group เพื่อให้สามารถส่งไม้ใหม่ได้
            self._reset_group_data_after_close(group_id)
            
            # Reset arbitrage_sent เพื่อให้สามารถส่งออเดอร์ใหม่ได้ (สำหรับระบบเก่า - ไม่ใช้แล้ว)
            # self.arbitrage_sent = False
            # self.arbitrage_send_time = None
            
            # Reset recovery_in_progress สำหรับกลุ่มนี้
            if group_id in self.recovery_in_progress:
                self.recovery_in_progress.remove(group_id)
                self.logger.info(f"🔄 Reset recovery status for group {group_id}")
            
            # Reset group counter สำหรับสามเหลี่ยมนี้เท่านั้น
            triangle_type = group_data.get('triangle_type', 'triangle_1')
            if triangle_type in self.group_counters:
                old_counter = self.group_counters[triangle_type]
                self.group_counters[triangle_type] = 0
                self.logger.info(f"🔄 Reset {triangle_type} counter from {old_counter} to 0 - next group will be group_{triangle_type}_1")
            
            # Reset ข้อมูลกลุ่มให้ถูกต้อง
            self._reset_group_data()
            
            # Reset comment เพื่อให้สามารถใช้ comment เดิมได้อีกครั้ง
            self._reset_comments_for_group(group_id)
            
            # คำนวณ PnL รวม (Arbitrage + Correlation)
            total_combined_pnl = total_pnl + correlation_pnl
            
            # แสดงผล PnL รวมของกลุ่ม
            pnl_status = "💰" if total_combined_pnl > 0 else "💸" if total_combined_pnl < 0 else "⚖️"
            self.logger.info(f"✅ Group {group_id} closed successfully")
            self.logger.info(f"   🚀 Arbitrage orders closed: {orders_closed}/{len(positions_to_close)}")
            self.logger.info(f"   🔄 Recovery positions closed: {recovery_positions_closed}")
            self.logger.info(f"   📊 Total positions closed: {orders_closed + recovery_positions_closed}")
            self.logger.info(f"   💰 Arbitrage PnL: {total_pnl:.2f} USD")
            self.logger.info(f"   🔄 Correlation PnL: {correlation_pnl:.2f} USD")
            self.logger.info(f"   {pnl_status} Total Combined PnL: {total_combined_pnl:.2f} USD")
            self.logger.info(f"   📊 คู่เงินที่ใช้ได้แล้ว: {self.used_currency_pairs}")
            self.logger.info(f"   🔄 Comments reset for group {group_id}")
            self.logger.info("🔄 เริ่มตรวจสอบ arbitrage ใหม่")
            
        except Exception as e:
            self.logger.error(f"Error closing group {group_id}: {e}")
    
    def _get_recovery_pnl_for_group(self, group_id: str) -> float:
        """ดึง PnL ของ recovery positions ที่เกี่ยวข้องกับกลุ่ม (ไม่ปิด) - using order_tracker"""
        try:
            if not self.correlation_manager:
                return 0.0
            
            total_recovery_pnl = 0.0
            all_positions = self.broker.get_all_positions()
            all_orders = self.correlation_manager.order_tracker.get_all_orders()
            
            # หา recovery orders ที่เกี่ยวข้องกับกลุ่มนี้
            for order_key, order_data in all_orders.items():
                if (order_data.get('type') == 'RECOVERY' and 
                    order_data.get('group_id') == group_id):
                    # หา PnL จาก MT5
                    ticket = order_data.get('ticket')
                    if ticket:
                        for pos in all_positions:
                            if str(pos.get('ticket')) == str(ticket):
                                total_recovery_pnl += pos.get('profit', 0)
                                break
            
            return total_recovery_pnl
            
        except Exception as e:
            self.logger.error(f"Error getting recovery PnL for group: {e}")
            return 0.0
    
    def _get_magic_for_group(self, group_id: str) -> int:
        """Get magic number for a group_id"""
        try:
            # Extract triangle number from group_id (e.g., "group_triangle_1_1" -> "1")
            if 'triangle_' in group_id:
                triangle_part = group_id.split('triangle_')[1].split('_')[0]
                magic_map = {
                    '1': 234001,
                    '2': 234002,
                    '3': 234003,
                    '4': 234004,
                    '5': 234005,
                    '6': 234006
                }
                return magic_map.get(triangle_part, 234000)
            return 234000
        except Exception as e:
            self.logger.error(f"Error getting magic for group {group_id}: {e}")
            return 234000
    
    def _close_recovery_positions_for_group(self, group_id: str):
        """ปิด recovery positions ที่เกี่ยวข้องกับกลุ่ม arbitrage (using order_tracker) - returns (pnl, count)"""
        try:
            if not self.correlation_manager:
                return 0.0, 0
            
            # Get all orders from order_tracker
            all_orders = self.correlation_manager.order_tracker.get_all_orders()
            all_positions = self.broker.get_all_positions()
            
            # หา recovery orders ที่เกี่ยวข้องกับกลุ่มนี้
            group_data = self.active_groups.get(group_id, {})
            group_pairs = set(group_data.get('triangle', []))
            
            # Get magic number for this group
            magic_number = self._get_magic_for_group(group_id)
            
            # Find all original tickets in this group (from MT5)
            original_tickets = set()
            for pos in all_positions:
                if pos.get('magic') == magic_number:
                    # Check if it's not a recovery order
                    comment = pos.get('comment', '')
                    if not (comment.startswith('R') or comment.startswith('RECOVERY_')):
                        original_tickets.add(str(pos.get('ticket')))
            
            self.logger.info(f"🔍 Found {len(original_tickets)} original tickets in group {group_id} (magic {magic_number})")
            
            recovery_orders_to_close = []
            total_correlation_pnl = 0.0
            
            # Find recovery orders that hedge these original tickets
            for order_key, order_data in all_orders.items():
                if order_data.get('type') == 'RECOVERY':
                    # Check if this recovery is hedging any ticket from this group
                    hedging_for = order_data.get('hedging_for', '')
                    if hedging_for:
                        # Extract ticket from hedging_for key (format: ticket_symbol)
                        hedging_ticket = hedging_for.split('_')[0] if '_' in hedging_for else hedging_for
                        if hedging_ticket in original_tickets:
                            recovery_orders_to_close.append(order_data)
                            self.logger.debug(f"   Found recovery {order_data.get('ticket')} hedging {hedging_ticket}")
            
            # Close recovery orders and collect PnL
            if recovery_orders_to_close:
                self.logger.info(f"🔄 Closing {len(recovery_orders_to_close)} recovery positions for group {group_id}")
            
            for order_data in recovery_orders_to_close:
                ticket = order_data.get('ticket')
                symbol = order_data.get('symbol')
                
                if ticket and symbol:
                    # Get current PnL from MT5 before closing
                    for pos in all_positions:
                        if str(pos.get('ticket')) == str(ticket):
                            total_correlation_pnl += pos.get('profit', 0)
                            break
                    
                    # Close the order via broker using ticket (not symbol!)
                    success = self.broker.close_position(int(ticket))
                    if success:
                        self.logger.info(f"   ✅ Closed recovery order: {symbol} (Ticket: {ticket})")
                    else:
                        self.logger.warning(f"   ⚠️ Failed to close recovery order: {symbol} (Ticket: {ticket})")
            
            total_recovery_closed = len(recovery_orders_to_close)
            if total_recovery_closed > 0:
                self.logger.info(f"✅ Closed {total_recovery_closed} recovery positions for group {group_id}")
                self.logger.info(f"   💰 Total Correlation PnL: {total_correlation_pnl:.2f} USD")
            
            # Return both PnL and count
            return total_correlation_pnl, total_recovery_closed
            
        except Exception as e:
            self.logger.error(f"Error closing recovery positions for group {group_id}: {e}")
            return 0.0, 0
    
    def _reset_comments_for_group(self, group_id: str):
        """Reset comment สำหรับกลุ่มที่ปิดแล้ว"""
        try:
            # ดึงหมายเลขสามเหลี่ยม
            triangle_type = self.active_groups.get(group_id, {}).get('triangle_type', 'unknown')
            triangle_number = triangle_type.split('_')[-1]  # ได้ 1, 2, 3, 4, 5, 6
            
            # สร้าง comment patterns ที่ต้อง reset
            # ✅ Comment patterns for group identification
            # NEW FORMAT: R{ticket}_{symbol} for recovery orders
            # LEGACY: RECOVERY_G{triangle_number}_ (old format, still supported)
            comment_patterns = [
                f"G{triangle_number}_EURUSD",
                f"G{triangle_number}_GBPUSD", 
                f"G{triangle_number}_EURGBP",
                f"R",  # NEW: Recovery orders start with 'R'
                f"ARB_G{triangle_number}_"
            ]
            
            # Debug: แสดง used_currency_pairs ปัจจุบัน (สำหรับระบบเก่า - ไม่ใช้แล้ว)
            # self.logger.info(f"🔍 Current used_currency_pairs: {list(self.used_currency_pairs)}")
            # self.logger.info(f"🔍 Looking for patterns: {comment_patterns}")
            # 
            # # ตรวจสอบว่ามี comment ที่ใช้อยู่หรือไม่
            # used_comments = set()
            # for pattern in comment_patterns:
            #     # Check if any used_currency_pairs starts with this pattern
            #     for used_pair in list(self.used_currency_pairs):  # Iterate over a copy
            #         if used_pair.startswith(pattern):
            #             used_comments.add(used_pair)
            #             self.logger.info(f"✅ Found matching comment: {used_pair}")
            # 
            # # ลบ comment ที่ใช้แล้วออกจาก used_currency_pairs
            # for comment in used_comments:
            #     self.used_currency_pairs.discard(comment)
            # 
            # if used_comments:
            #     self.logger.info(f"🔄 Reset comments for group {group_id}: {used_comments}")
            #     self.logger.info(f"🔄 Remaining used_currency_pairs: {list(self.used_currency_pairs)}")
            # else:
            #     self.logger.info(f"🔄 No comments to reset for group {group_id}")
            
            self.logger.info(f"🔄 No comments to reset for group {group_id}")
            
        except Exception as e:
            self.logger.error(f"Error resetting comments for group {group_id}: {e}")
    
    def _reset_group_data(self):
        """Reset ข้อมูลกลุ่มให้ถูกต้อง (รองรับการแยกกันของแต่ละสามเหลี่ยม)"""
        try:
            # ตรวจสอบว่ามีกลุ่มที่เปิดอยู่จริงหรือไม่
            if len(self.active_groups) == 0:
                # ถ้าไม่มีกลุ่มที่เปิดอยู่ ให้ reset ข้อมูลทั้งหมด
                for triangle_name in self.used_currency_pairs:
                    self.used_currency_pairs[triangle_name].clear()
                self.group_currency_mapping.clear()
                self.recovery_in_progress.clear()
                
                # Reset group counters เมื่อไม่มีกลุ่มที่เปิดอยู่
                for triangle_name, counter in self.group_counters.items():
                    if counter > 0:
                        self.group_counters[triangle_name] = 0
                        self.logger.info(f"🔄 Reset {triangle_name} counter to 0 - next group will be group_{triangle_name}_1")
                
                self.logger.info("🔄 Reset ข้อมูลกลุ่ม - คู่เงินและ comment ทั้งหมดปลดล็อคแล้ว")
            else:
                # ถ้ายังมีกลุ่มที่เปิดอยู่ ให้ตรวจสอบข้อมูลให้ถูกต้อง
                current_used_pairs = set()
                groups_to_remove = []
                
                for group_id, group_data in list(self.active_groups.items()):
                    # ตรวจสอบว่า Group ยังเปิดอยู่จริงใน broker หรือไม่
                    valid_positions = 0
                    for position in group_data['positions']:
                        order_id = position.get('order_id')
                        if order_id:
                            all_positions = self.broker.get_all_positions()
                            for pos in all_positions:
                                if pos['ticket'] == order_id:
                                    valid_positions += 1
                                    break
                    
                    if valid_positions > 0:
                        # Group ยังเปิดอยู่จริง
                        triangle = group_data.get('triangle', [])
                        if triangle:
                            group_pairs = set(triangle)
                            current_used_pairs.update(group_pairs)
                            self.group_currency_mapping[group_id] = group_pairs
                    else:
                        # Group ไม่มี valid positions ให้ลบ
                        groups_to_remove.append(group_id)
                        self.logger.info(f"🗑️ Group {group_id} has no valid positions - removing from active groups")
                
                # ลบ Groups ที่ไม่มี valid positions
                for group_id in groups_to_remove:
                    if group_id in self.active_groups:
                        del self.active_groups[group_id]
                    if group_id in self.group_currency_mapping:
                        del self.group_currency_mapping[group_id]
                    if group_id in self.recovery_in_progress:
                        self.recovery_in_progress.remove(group_id)
                
                # อัพเดท used_currency_pairs ให้ตรงกับข้อมูลจริง
                # current_used_pairs เป็น set แต่ self.used_currency_pairs ต้องเป็น dict
                # ไม่ต้องอัพเดทเพราะใช้ magic number แล้ว
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
            
            # 🆕 แปลง symbols ผ่าน mapper
            real_pair1 = self.symbol_mapper.get_real_symbol(pair1)
            real_pair2 = self.symbol_mapper.get_real_symbol(pair2)
            real_pair3 = self.symbol_mapper.get_real_symbol(pair3)
            
            # Get current prices
            price1 = self.broker.get_current_price(real_pair1)
            price2 = self.broker.get_current_price(real_pair2)
            price3 = self.broker.get_current_price(real_pair3)
            
            if price1 is None or price2 is None or price3 is None:
                # Log missing prices for first few triangles to debug
                if triangles_checked < 5:
                    self.logger.warning(f"Missing prices for {triangle}: {pair1}={price1}, {pair2}={price2}, {pair3}={price3}")
                return None
            
            # Get spreads (with fallback)
            spread1 = self.broker.get_spread(pair1) if hasattr(self.broker, 'get_spread') else 0
            spread2 = self.broker.get_spread(pair2) if hasattr(self.broker, 'get_spread') else 0
            spread3 = self.broker.get_spread(pair3) if hasattr(self.broker, 'get_spread') else 0
            
            # ตรวจสอบว่า spread เป็น None หรือไม่
            if spread1 is None:
                spread1 = 0
            if spread2 is None:
                spread2 = 0
            if spread3 is None:
                spread3 = 0
            
            # ถ้า spread ทั้งหมดเป็น 0 (ไม่ได้ข้อมูล) ให้ใช้ค่า default
            if spread1 == 0 and spread2 == 0 and spread3 == 0:
                self.logger.debug(f"Using default spread values for {triangle} (broker data unavailable)")
                spread1 = spread2 = spread3 = 1.0  # ใช้ 1 pip เป็นค่า default
            else:
                self.logger.debug(f"Spread data for {triangle}: {pair1}={spread1:.2f}, {pair2}={spread2:.2f}, {pair3}={spread3:.2f} pips")
            
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
    
    def _get_triangle_name(self, triangle: Tuple[str, str, str]) -> str:
        """Get triangle name from triangle tuple"""
        try:
            # หา triangle name จาก triangle mapping
            for i, triangle_data in enumerate(self.triangles):
                if triangle_data == triangle:
                    return f"triangle_{i+1}"
            return "triangle_unknown"
        except Exception as e:
            self.logger.error(f"Error getting triangle name: {e}")
            return "triangle_unknown"
    
    def execute_triangle_entry(self, triangle: Tuple[str, str, str], ai_decision):
        """Execute triangle positions based on AI decision"""
        try:
            pair1, pair2, pair3 = triangle
            lot_size = ai_decision.position_size
            direction = ai_decision.direction
            
            # หา triangle_name จาก triangle
            triangle_name = self._get_triangle_name(triangle)
            
            orders = []
            
            # Place orders for each pair in the triangle
            for i, pair in enumerate(triangle):
                order_type = 'BUY' if direction.get(pair, 1) > 0 else 'SELL'
                order = self.broker.place_order(pair, order_type, lot_size)
                
                if order:
                    orders.append(order)
                    
                    # Track ไม้ arbitrage ใน hedge tracker
                    if hasattr(self, 'correlation_manager') and self.correlation_manager:
                        group_id = f"group_{triangle_name}_{self.group_counters[triangle_name]}"
                        # Individual order tracker doesn't need locking - each order is tracked individually
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
            
            # หา triangle_name จาก triangle
            triangle_name = self._get_triangle_name(triangle)
            
            orders = []
            
            # Place orders for each pair in the triangle
            for i, pair in enumerate(triangle):
                order_type = 'BUY' if direction.get(pair, 1) > 0 else 'SELL'
                order = self.broker.place_order(pair, order_type, lot_size)
                
                if order:
                    orders.append(order)
                    
                    # Track ไม้ arbitrage ใน hedge tracker
                    if hasattr(self, 'correlation_manager') and self.correlation_manager:
                        group_id = f"group_{triangle_name}_{self.group_counters[triangle_name]}"
                        # Individual order tracker doesn't need locking - each order is tracked individually
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
                # 'market_regime': self.market_regime,  # DISABLED - not used in simple trading
                'adaptive_threshold': self.volatility_threshold,
                'execution_speed_ms': self.performance_metrics['avg_execution_time']
            }
            
            self.logger.info(f"✅ NEVER-CUT-LOSS triangle executed: {triangle} with {len(orders)} orders "
                           f"(regime: normal)")  # DISABLED - not used in simple trading
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
            
            self.logger.info(f"📊 {triangle}: Spreads - {pair1}: {spread1}, {pair2}: {spread2}, {pair3}: {spread3}")
            
            # ตรวจสอบว่าได้ค่า spread หรือไม่
            if spread1 is None or spread2 is None or spread3 is None:
                self.logger.info(f"⚠️ {triangle}: Some spreads unavailable, using bid/ask calculation")
                # ถ้าไม่มีข้อมูล spread ให้อนุญาตผ่าน (ไม่บล็อก arbitrage)
                # เพราะระบบจะคำนวณต้นทุนจาก Bid-Ask ใน _calculate_total_cost แทน
                return True
            
            # Check if all spreads are below threshold - ปรับให้ยืดหยุ่นมากขึ้น
            max_spread = self._get_config_value('arbitrage_params.detection.spread_tolerance', 10.0)  # เพิ่มจาก 3.0 เป็น 10.0
            acceptable = (spread1 < max_spread and 
                         spread2 < max_spread and 
                         spread3 < max_spread)
            
            if not acceptable:
                self.logger.info(f"❌ {triangle}: Spreads too high - {spread1:.2f}, {spread2:.2f}, {spread3:.2f} pips (max: {max_spread})")
            else:
                self.logger.info(f"✅ {triangle}: All spreads acceptable (max: {max(spread1, spread2, spread3):.2f} <= {max_spread})")
            
            return acceptable
                   
        except Exception as e:
            self.logger.error(f"Error checking spread for {triangle}: {e}")
            return True  # Return True on error to not block trades
    
    def calculate_arbitrage_direction(self, triangle: Tuple[str, str, str]) -> Optional[Dict]:
        """
        ⭐ คำนวณทิศทางที่ถูกต้องสำหรับ Triangle Arbitrage
        
        คำนวณ Forward Path (BUY-BUY-SELL) และ Reverse Path (BUY-SELL-SELL)
        เลือกทางที่ให้กำไรสูงกว่าหลังหักต้นทุนทั้งหมด
        
        Returns:
            Dict with keys: direction, profit_percent, orders, raw_profit
            None if no profitable opportunity
        """
        try:
            pair1, pair2, pair3 = triangle
            
            self.logger.info(f"🧮 {triangle}: Calculating arbitrage direction...")
            
            # 1. ดึงราคา Bid/Ask
            bid1, ask1 = self._get_bid_ask(pair1)
            bid2, ask2 = self._get_bid_ask(pair2)
            bid3, ask3 = self._get_bid_ask(pair3)
            
            if not all([bid1, ask1, bid2, ask2, bid3, ask3]):
                self.logger.info(f"❌ {triangle}: Cannot get bid/ask prices")
                return None
            
            self.logger.info(f"💱 {triangle}: Prices - {pair1}: {bid1:.5f}/{ask1:.5f}, {pair2}: {bid2:.5f}/{ask2:.5f}, {pair3}: {bid3:.5f}/{ask3:.5f}")
            
            # 2. คำนวณ Forward Path (BUY pair1, BUY pair2, SELL pair3)
            # เริ่มด้วย 1 USD
            forward_step1 = 1 / ask1          # ซื้อ pair1 ได้ base currency
            forward_step2 = forward_step1 / ask2  # ซื้อ pair2 ได้ counter currency
            forward_step3 = forward_step2 * bid3  # ขาย pair3 ได้ USD กลับมา
            forward_result = forward_step3
            forward_profit_percent = (forward_result - 1.0) * 100
            
            # 3. คำนวณ Reverse Path (BUY pair3, SELL pair2, SELL pair1)
            reverse_step1 = 1 / ask3          # ซื้อ pair3
            reverse_step2 = reverse_step1 * bid2  # ขาย pair2
            reverse_step3 = reverse_step2 * bid1  # ขาย pair1 ได้ USD กลับมา
            reverse_result = reverse_step3
            reverse_profit_percent = (reverse_result - 1.0) * 100
            
            # 4. คำนวณต้นทุนรวม
            total_cost_percent = self._calculate_total_cost(triangle, bid1, ask1, bid2, ask2, bid3, ask3)
            
            self.logger.info(f"🔄 {triangle}: Forward path = {forward_profit_percent:.4f}%, Reverse path = {reverse_profit_percent:.4f}%, Cost = {total_cost_percent:.4f}%")
            
            # 5. คำนวณกำไรสุทธิ
            forward_net = forward_profit_percent - total_cost_percent
            reverse_net = reverse_profit_percent - total_cost_percent
            
            # 6. เลือกทิศทางที่ดีกว่า (ไม่ตัดสินใจ threshold ที่นี่)
            self.logger.info(f"📊 {triangle}: Net profits - Forward: {forward_net:.4f}%, Reverse: {reverse_net:.4f}%")
            
            if forward_net >= reverse_net:
                self.logger.info(f"✅ {triangle}: FORWARD path selected - Net profit: {forward_net:.4f}%")
                return {
                    'direction': 'forward',
                    'profit_percent': forward_net,
                    'raw_profit': forward_profit_percent,
                    'cost_percent': total_cost_percent,
                    'orders': {
                        pair1: 'BUY',
                        pair2: 'BUY',
                        pair3: 'SELL'
                    }
                }
            else:
                self.logger.info(f"✅ {triangle}: REVERSE path selected - Net profit: {reverse_net:.4f}%")
                return {
                    'direction': 'reverse',
                    'profit_percent': reverse_net,
                    'raw_profit': reverse_profit_percent,
                    'cost_percent': total_cost_percent,
                    'orders': {
                        pair1: 'SELL',
                        pair2: 'SELL',
                        pair3: 'BUY'
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error calculating arbitrage direction for {triangle}: {e}")
            return None
    
    def _get_bid_ask(self, symbol: str) -> Tuple[Optional[float], Optional[float]]:
        """ดึงราคา Bid และ Ask สำหรับ symbol"""
        try:
            # ใช้ real symbol
            real_symbol = self.symbol_mapper.get_real_symbol(symbol)
            
            # ใช้ MT5 ดึงราคา
            tick = mt5.symbol_info_tick(real_symbol)
            
            if tick:
                return tick.bid, tick.ask
            
            # 🔮 Intelligent fallback: ใช้ราคาปัจจุบัน + estimated spread
            price = self.broker.get_current_price(symbol)
            if price:
                # ใช้ estimated spread แทนการเรียก broker.get_spread()
                estimated_spread = self._get_estimated_spread_for_pair(symbol)
                
                # แปลง spread จาก pips เป็นราคา
                if 'JPY' in symbol:
                    spread_price = estimated_spread * 0.01
                else:
                    spread_price = estimated_spread * 0.0001
                
                bid = price - spread_price / 2
                ask = price + spread_price / 2
                
                self.logger.debug(f"📊 {symbol}: Using estimated spread {estimated_spread} pips")
                return bid, ask
            
            return None, None
            
        except Exception as e:
            self.logger.error(f"Error getting bid/ask for {symbol}: {e}")
            return None, None
    
    def _calculate_total_cost(self, triangle: Tuple[str, str, str], 
                            bid1: float, ask1: float, 
                            bid2: float, ask2: float, 
                            bid3: float, ask3: float) -> float:
        """
        คำนวณต้นทุนรวมทั้งหมด (Spread + Commission + Slippage)
        """
        try:
            # ตรวจสอบว่ามีข้อมูล Bid-Ask ครบถ้วนหรือไม่
            if None in [bid1, ask1, bid2, ask2, bid3, ask3]:
                self.logger.warning(f"Incomplete bid/ask data for {triangle}")
                return 0.5  # Return default 0.5% if incomplete data
            
            # 1. Spread Cost (คำนวณจากความต่างระหว่าง Bid-Ask)
            spread_cost_1 = (ask1 - bid1) / bid1 * 100
            spread_cost_2 = (ask2 - bid2) / bid2 * 100
            spread_cost_3 = (ask3 - bid3) / bid3 * 100
            spread_cost_total = spread_cost_1 + spread_cost_2 + spread_cost_3
            
            # 2. Commission Cost (ดึงจาก config หรือใช้ค่า default)
            commission_rate = self._get_config_value('arbitrage_params.execution.commission_rate', 0.0001)
            commission_cost = commission_rate * 3 * 100  # 3 legs
            
            # 3. Slippage Cost (ดึงจาก config หรือใช้ค่า default)
            slippage = self._get_config_value('arbitrage_params.execution.max_slippage', 0.0005)
            slippage_cost = slippage * 3 * 100  # 3 legs
            
            # รวมต้นทุน
            total_cost = spread_cost_total + commission_cost + slippage_cost
            
            self.logger.debug(f"Cost breakdown for {triangle}: Spread={spread_cost_total:.4f}%, Commission={commission_cost:.4f}%, Slippage={slippage_cost:.4f}%, Total={total_cost:.4f}%")
            
            return total_cost
            
        except Exception as e:
            self.logger.error(f"Error calculating total cost: {e}")
            return 0.5  # Return default 0.5% if error
    
    # ==================================================================================
    # 🎯 INTELLIGENT SCORING SYSTEM (6 FACTORS)
    # ==================================================================================
    
    def _calculate_opportunity_score(self, triangle: Tuple[str, str, str], direction_info: Dict) -> Optional[Dict]:
        """🎯 คำนวณคะแนนโอกาส Arbitrage จาก 6 ปัจจัยหลัก (0-100 คะแนน)"""
        try:
            factors = {}
            
            # Factor 1: Profit Score (0-35 คะแนน)
            profit_data = self._get_profit_score(direction_info)
            factors['profit'] = profit_data
            
            # Factor 2: Spread Score (0-20 คะแนน)
            spread_data = self._get_spread_score(triangle)
            factors['spread'] = spread_data
            
            # Factor 3: Market Condition Score (0-20 คะแนน)
            market_data = self._get_market_condition_score(triangle)
            factors['market'] = market_data
            
            # Factor 4: Time Pattern Score (0-10 คะแนน)
            time_data = self._get_time_pattern_score()
            factors['time'] = time_data
            
            # Factor 5: Execution Probability (0-10 คะแนน)
            execution_data = self._get_execution_probability_score(triangle, direction_info)
            factors['execution'] = execution_data
            
            # Factor 6: Risk Score (0-5 คะแนน)
            risk_data = self._get_risk_score(triangle, direction_info)
            factors['risk'] = risk_data
            
            # คำนวณคะแนนรวม
            total_score = sum(f['score'] for f in factors.values())
            
            return {
                'total_score': total_score,
                'factors': factors
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating opportunity score: {e}")
            return None
    
    def _get_profit_score(self, direction_info: Dict) -> Dict:
        """📈 คะแนนจากกำไรที่คาดหวัง (0-35 คะแนน) | 0.05%=35, 0.03%=21, 0.01%=7"""
        try:
            profit_percent = direction_info.get('profit_percent', 0)
            
            if profit_percent >= 0.05:
                score = 35.0
            elif profit_percent >= 0.005:
                score = (profit_percent / 0.05) * 35.0
            else:
                score = 0.0
            
            return {
                'score': min(score, 35.0),
                'weight': 0.35,
                'value': profit_percent
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating profit score: {e}")
            return {'score': 0.0, 'weight': 0.35, 'value': 0.0}
    
    def _get_spread_score(self, triangle: Tuple[str, str, str]) -> Dict:
        """📊 คะแนนจาก Spread (0-20 คะแนน) | <=2pips=20, 5pips=10, >=10pips=0"""
        try:
            pair1, pair2, pair3 = triangle
            
            # 🔍 พยายามดึงข้อมูลจริงก่อน - ไม่ว่าจะเชื่อมต่อหรือไม่
            spreads = []
            real_data_count = 0
            
            for pair in [pair1, pair2, pair3]:
                real_pair = self.symbol_mapper.get_real_symbol(pair)
                
                # ลองดึงข้อมูลจริงหลายวิธี
                real_spread = self._try_get_real_spread(pair, real_pair)
                
                if real_spread is not None:
                    spreads.append(real_spread)
                    real_data_count += 1
                    self.logger.debug(f"📊 {pair} ({real_pair}): Real spread {real_spread:.2f} pips")
                else:
                    # ใช้ estimated ถ้าไม่สามารถดึงข้อมูลจริงได้
                    estimated = self._get_estimated_spread_for_pair(pair)
                    spreads.append(estimated)
                    self.logger.debug(f"📊 {pair} ({real_pair}): Estimated spread {estimated:.2f} pips")
            
            avg_spread = sum(spreads) / 3.0
            
            # แสดงข้อมูลว่าได้ข้อมูลจริงกี่ตัว
            if real_data_count == 0:
                self.logger.warning(f"⚠️ {triangle}: No real spread data - using all estimated spreads")
            elif real_data_count < 3:
                self.logger.info(f"📊 {triangle}: {real_data_count}/3 real spreads, {3-real_data_count} estimated")
            else:
                self.logger.info(f"✅ {triangle}: All 3 real spreads available")
            
            # บันทึก cache ถ้ามีข้อมูลใหม่
            if real_data_count > 0:
                self._save_spread_cache()
            
            if avg_spread <= 2.0:
                score = 20.0
            elif avg_spread >= 10.0:
                score = 0.0
            else:
                score = 20.0 - ((avg_spread - 2.0) / 8.0) * 20.0
            
            return {
                'score': max(0.0, min(score, 20.0)),
                'weight': 0.20,
                'value': avg_spread
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating spread score: {e}")
            return {'score': 10.0, 'weight': 0.20, 'value': 5.0}
    
    def _get_estimated_spreads(self, triangle: Tuple[str, str, str]) -> List[float]:
        """🔮 คำนวณ estimated spreads สำหรับ triangle ทั้งหมด"""
        pair1, pair2, pair3 = triangle
        return [
            self._get_estimated_spread_for_pair(pair1),
            self._get_estimated_spread_for_pair(pair2),
            self._get_estimated_spread_for_pair(pair3)
        ]
    
    def _get_estimated_spread_for_pair(self, pair: str) -> float:
        """🔮 คำนวณ estimated spread ตามประเภทคู่เงิน (ฉลาดกว่า fallback!)"""
        pair = pair.upper()
        
        # Major pairs - spread ต่ำ (1.5-3.0 pips)
        major_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD']
        if pair in major_pairs:
            return 2.0
        
        # EUR crosses - spread ปานกลาง (2.0-4.0 pips)
        eur_crosses = ['EURGBP', 'EURJPY', 'EURCHF', 'EURAUD', 'EURNZD', 'EURCAD']
        if pair in eur_crosses:
            return 3.0
        
        # GBP crosses - spread ปานกลาง (2.5-4.5 pips)
        gbp_crosses = ['GBPJPY', 'GBPCHF', 'GBPAUD', 'GBPNZD', 'GBPCAD']
        if pair in gbp_crosses:
            return 3.5
        
        # AUD/NZD crosses - spread สูง (3.0-5.0 pips)
        aud_nzd_crosses = ['AUDJPY', 'AUDCHF', 'AUDCAD', 'AUDNZD', 'NZDJPY', 'NZDCHF', 'NZDCAD']
        if pair in aud_nzd_crosses:
            return 4.0
        
        # CAD/CHF crosses - spread สูง (3.5-5.5 pips)
        cad_chf_crosses = ['CADJPY', 'CADCHF', 'CHFJPY']
        if pair in cad_chf_crosses:
            return 4.5
        
        # Default - spread ปานกลาง
        return 3.0
    
    def _try_get_real_spread(self, base_symbol: str, real_symbol: str) -> Optional[float]:
        """🔍 พยายามดึงข้อมูล spread จริงหลายวิธี"""
        try:
            # วิธีที่ 0: ลองดึงจาก cache ก่อน
            cached_spread = self._get_cached_spread(base_symbol)
            if cached_spread is not None:
                self.logger.debug(f"📋 {base_symbol}: Using cached spread {cached_spread:.2f} pips")
                return cached_spread
            
            # วิธีที่ 1: ใช้ broker.get_spread()
            spread = self.broker.get_spread(base_symbol)
            if spread is not None and spread > 0:
                # บันทึกลง cache
                self._update_spread_cache(base_symbol, spread)
                return spread
            
            # วิธีที่ 2: ใช้ MT5 โดยตรง (ถ้ามี)
            try:
                import MetaTrader5 as mt5
                if mt5.initialize():
                    # 🔧 Force login ถ้ายังไม่ได้เชื่อมต่อ
                    account_info = mt5.account_info()
                    if account_info is None:
                        self.logger.info("🔌 MT5 not connected - attempting login...")
                        if mt5.login():
                            account_info = mt5.account_info()
                            if account_info:
                                self.logger.info(f"✅ MT5 Connected - Account: {account_info.login}")
                    
                    # ลองดึงจาก real symbol
                    tick = mt5.symbol_info_tick(real_symbol)
                    if tick and tick.bid is not None and tick.ask is not None:
                        spread_price = tick.ask - tick.bid
                        
                        # แปลงเป็น pips
                        symbol_info = mt5.symbol_info(real_symbol)
                        if symbol_info:
                            digits = symbol_info.digits
                            if digits == 5 or digits == 3:
                                spread_pips = spread_price * 10000
                            elif digits == 4 or digits == 2:
                                spread_pips = spread_price * 10000
                            else:
                                spread_pips = spread_price * 10000
                            
                            if spread_pips > 0:
                                # บันทึกลง cache
                                self._update_spread_cache(base_symbol, spread_pips)
                                self.logger.info(f"📊 Real spread from MT5: {base_symbol} = {spread_pips:.2f} pips")
                                return spread_pips
                    
                    mt5.shutdown()
            except ImportError:
                pass  # MT5 ไม่พร้อมใช้งาน
            
            # วิธีที่ 3: คำนวณจาก bid/ask ที่มี
            bid, ask = self._get_bid_ask(base_symbol)
            if bid is not None and ask is not None and ask > bid:
                spread_price = ask - bid
                # แปลงเป็น pips
                if 'JPY' in base_symbol:
                    spread_pips = spread_price * 100
                else:
                    spread_pips = spread_price * 10000
                
                if spread_pips > 0:
                    # บันทึกลง cache
                    self._update_spread_cache(base_symbol, spread_pips)
                    return spread_pips
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error getting real spread for {base_symbol}: {e}")
            return None
    
    def _load_spread_cache(self):
        """📂 โหลดข้อมูล spread cache จากไฟล์"""
        try:
            import json
            import os
            
            if os.path.exists(self.spread_cache_file):
                with open(self.spread_cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    self.spread_cache = cache_data.get('spreads', {})
                    self.logger.info(f"📂 Loaded {len(self.spread_cache)} spread cache entries")
            else:
                self.logger.debug("No spread cache file found - starting with empty cache")
                
        except Exception as e:
            self.logger.error(f"Error loading spread cache: {e}")
            self.spread_cache = {}
    
    def _save_spread_cache(self):
        """💾 บันทึกข้อมูล spread cache ลงไฟล์"""
        try:
            import json
            import os
            from datetime import datetime
            
            cache_data = {
                "_comment": "Spread Cache - เก็บข้อมูล spread จริงจากโบรกเกอร์",
                "_last_updated": datetime.now().isoformat(),
                "_source": "Real broker data",
                "spreads": self.spread_cache,
                "metadata": {
                    "broker": "MetaTrader5",
                    "timeframe": "real-time",
                    "accuracy": "high",
                    "note": "ข้อมูลนี้จะถูกอัปเดตเมื่อดึงข้อมูลจริงได้"
                }
            }
            
            os.makedirs(os.path.dirname(self.spread_cache_file), exist_ok=True)
            with open(self.spread_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
                
            self.logger.debug(f"💾 Saved spread cache with {len(self.spread_cache)} entries")
            
        except Exception as e:
            self.logger.error(f"Error saving spread cache: {e}")
    
    def _update_spread_cache(self, symbol: str, spread: float):
        """🔄 อัปเดต spread cache"""
        if spread > 0:
            self.spread_cache[symbol.upper()] = spread
            self.logger.debug(f"🔄 Updated spread cache: {symbol} = {spread:.2f} pips")
    
    def _get_cached_spread(self, symbol: str) -> Optional[float]:
        """📋 ดึงข้อมูล spread จาก cache"""
        return self.spread_cache.get(symbol.upper())
    
    def _get_market_condition_score(self, triangle: Tuple[str, str, str]) -> Dict:
        """🌍 คะแนนจากสภาพตลาด (0-20 คะแนน) | Ranging=20, Normal=15, Trending=10, Volatile=5"""
        try:
            current_regime = self._get_current_market_regime()
            regime_scores = {'ranging': 20.0, 'normal': 15.0, 'trending': 10.0, 'volatile': 5.0}
            base_score = regime_scores.get(current_regime, 10.0)
            
            volatility_adjustment = 0.0
            try:
                if hasattr(self, 'market_analyzer') and self.market_analyzer:
                    market_conditions = self.market_analyzer.analyze_market_conditions(list(triangle))
                    volatility = market_conditions.get('volatility_level', 0.001)
                    if volatility < 0.0005:
                        volatility_adjustment = 2.0
                    elif volatility > 0.002:
                        volatility_adjustment = -3.0
            except Exception:
                pass
            
            final_score = base_score + volatility_adjustment
            
            return {
                'score': max(0.0, min(final_score, 20.0)),
                'weight': 0.20,
                'regime': current_regime.upper()
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating market condition score: {e}")
            return {'score': 10.0, 'weight': 0.20, 'regime': 'UNKNOWN'}
    
    def _get_time_pattern_score(self) -> Dict:
        """🕐 คะแนนจากเวลา (0-10 คะแนน) | LDN/NY=10, LDN=9, NY=9, Asian=6, Off=3"""
        try:
            current_time = datetime.now()
            hour_gmt = current_time.hour
            
            if 13 <= hour_gmt < 17:
                score, session = 10.0, "London/NY Overlap"
            elif 7 <= hour_gmt < 16:
                score, session = 9.0, "London"
            elif 12 <= hour_gmt < 21:
                score, session = 9.0, "NY"
            elif 0 <= hour_gmt < 9:
                score, session = 6.0, "Asian"
            else:
                score, session = 3.0, "Off-hours"
            
            return {
                'score': score,
                'weight': 0.10,
                'session': session
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating time pattern score: {e}")
            return {'score': 5.0, 'weight': 0.10, 'session': 'Unknown'}
    
    def _get_execution_probability_score(self, triangle: Tuple[str, str, str], direction_info: Dict) -> Dict:
        """⚡ คะแนนจากโอกาสสำเร็จ (0-10 คะแนน) | Profit/Cost ratio >= 2.0 = 100%"""
        try:
            profit_percent = direction_info.get('profit_percent', 0)
            cost_percent = direction_info.get('cost_percent', 0.5)
            profit_cost_ratio = profit_percent / cost_percent if cost_percent > 0 else 0
            
            if profit_cost_ratio >= 2.0:
                probability = 100.0
            elif profit_cost_ratio >= 0.5:
                probability = ((profit_cost_ratio - 0.5) / 1.5) * 100.0
            else:
                probability = 0.0
            
            score = (probability / 100.0) * 10.0
            
            return {
                'score': min(score, 10.0),
                'weight': 0.10,
                'probability': probability
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating execution probability: {e}")
            return {'score': 5.0, 'weight': 0.10, 'probability': 50.0}
    
    def _get_risk_score(self, triangle: Tuple[str, str, str], direction_info: Dict) -> Dict:
        """⚠️ คะแนนจากความเสี่ยง (0-5 คะแนน) | 0 groups=5, <50%=4, <80%=3, >=80%=1"""
        try:
            num_active_groups = len(self.active_groups)
            max_groups = self._get_config_value('system_limits.max_concurrent_groups', 5)
            
            if num_active_groups == 0:
                risk_level, score = "VERY LOW", 5.0
            elif num_active_groups < max_groups * 0.5:
                risk_level, score = "LOW", 4.0
            elif num_active_groups < max_groups * 0.8:
                risk_level, score = "MEDIUM", 3.0
            else:
                risk_level, score = "HIGH", 1.0
            
            return {
                'score': score,
                'weight': 0.05,
                'level': risk_level
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating risk score: {e}")
            return {'score': 3.0, 'weight': 0.05, 'level': 'MEDIUM'}
    
    def _get_adaptive_score_threshold(self) -> float:
        """🎯 Adaptive Threshold | Volatile=80, Trending=75, Normal=70, Ranging=65"""
        try:
            current_regime = self._get_current_market_regime()
            regime_thresholds = {'volatile': 80.0, 'trending': 75.0, 'normal': 70.0, 'ranging': 65.0}
            return regime_thresholds.get(current_regime, 70.0)
        except Exception as e:
            self.logger.error(f"Error getting adaptive threshold: {e}")
            return 70.0
    
    def _get_current_market_regime(self) -> str:
        """📊 ดึง Market Regime ปัจจุบัน | volatile/trending/ranging/normal"""
        try:
            if hasattr(self, 'market_analyzer') and self.market_analyzer:
                try:
                    conditions = self.market_analyzer.analyze_market_conditions()
                    return conditions.get('market_regime', 'normal').lower()
                except Exception:
                    pass
            
            try:
                data = self.broker.get_historical_data('EURUSD', 'H1', 24)
                if data is not None and len(data) > 10:
                    returns = data['close'].pct_change().dropna()
                    volatility = returns.std()
                    if volatility > 0.002:
                        return 'volatile'
                    elif volatility < 0.0005:
                        return 'ranging'
                    else:
                        return 'normal'
            except Exception:
                pass
            
            return 'normal'
        except Exception as e:
            self.logger.error(f"Error getting market regime: {e}")
            return 'normal'
    
    # ==================================================================================
    # END OF INTELLIGENT SCORING SYSTEM
    # ==================================================================================
    
    def _validate_execution_feasibility(self, triangle: Tuple[str, str, str], direction_info: Dict) -> bool:
        """⭐ UPGRADED: Intelligent Multi-Factor Scoring (6 factors, 0-100 score, adaptive threshold)"""
        try:
            if not direction_info:
                self.logger.info(f"❌ {triangle}: No direction info provided")
                return False
            
            # คำนวณคะแนนจาก 6 ปัจจัย
            score_result = self._calculate_opportunity_score(triangle, direction_info)
            
            if not score_result:
                self.logger.info(f"❌ {triangle}: Failed to calculate score")
                return False
            
            total_score = score_result['total_score']
            factors = score_result['factors']
            
            # Log รายละเอียดคะแนน
            self.logger.info(f"")
            self.logger.info(f"{'='*60}")
            self.logger.info(f"📊 INTELLIGENT SCORING SYSTEM - {triangle}")
            self.logger.info(f"{'='*60}")
            self.logger.info(f"✓ Profit Score:     {factors['profit']['score']:5.1f} / 35  ({factors['profit']['value']:.4f}%)")
            self.logger.info(f"✓ Spread Score:     {factors['spread']['score']:5.1f} / 20  ({factors['spread']['value']:.1f} pips avg)")
            self.logger.info(f"✓ Market Score:     {factors['market']['score']:5.1f} / 20  ({factors['market']['regime']})")
            self.logger.info(f"✓ Time Score:       {factors['time']['score']:5.1f} / 10  ({factors['time']['session']})")
            self.logger.info(f"✓ Execution Score:  {factors['execution']['score']:5.1f} / 10  ({factors['execution']['probability']:.0f}%)")
            self.logger.info(f"✓ Risk Score:       {factors['risk']['score']:5.1f} / 5   ({factors['risk']['level']})")
            self.logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            self.logger.info(f"📈 TOTAL SCORE:     {total_score:.1f} / 100")
            
            # ใช้ adaptive threshold ตาม market regime
            adaptive_threshold = self._get_adaptive_score_threshold()
            
            self.logger.info(f"🎯 Threshold:       {adaptive_threshold:.1f} ({self._get_current_market_regime().upper()} market)")
            self.logger.info(f"{'='*60}")
            
            # ตัดสินใจ
            if total_score >= adaptive_threshold:
                self.logger.info(f"✅ DECISION: ENTER TRADE ({total_score:.1f} >= {adaptive_threshold:.1f})")
                self.logger.info(f"")
                
                # Track metrics
                self.performance_metrics['passed_feasibility_check'] = self.performance_metrics.get('passed_feasibility_check', 0) + 1
                
                return True
            else:
                self.logger.info(f"❌ DECISION: SKIP ({total_score:.1f} < {adaptive_threshold:.1f})")
                self.logger.info(f"")
                return False
            
        except Exception as e:
            self.logger.error(f"Error in intelligent scoring: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def _verify_triangle_balance(self, triangle: Tuple[str, str, str], lot_sizes: Dict) -> bool:
        """
        ⭐ ตรวจสอบว่า lot sizes ที่คำนวณได้ทำให้ triangle สมดุลหรือไม่
        """
        try:
            pair1, pair2, pair3 = triangle
            
            # ดึงราคาปัจจุบัน
            price1 = self.broker.get_current_price(pair1)
            price2 = self.broker.get_current_price(pair2)
            price3 = self.broker.get_current_price(pair3)
            
            if not all([price1, price2, price3]):
                self.logger.warning(f"Cannot get prices for balance check: {triangle}")
                return False
            
            # คำนวณมูลค่าแต่ละ leg
            lot1 = lot_sizes.get(pair1, 0.01)
            lot2 = lot_sizes.get(pair2, 0.01)
            lot3 = lot_sizes.get(pair3, 0.01)
            
            # มูลค่าใน USD (approximate)
            value1 = lot1 * 100000 * price1
            value2 = lot2 * 100000 * price2 * price3  # EUR/GBP ต้องแปลงเป็น USD
            value3 = lot3 * 100000 * price3
            
            # คำนวณความแตกต่าง
            max_value = max(value1, value2, value3)
            min_value = min(value1, value2, value3)
            avg_value = (value1 + value2 + value3) / 3
            
            if avg_value == 0:
                return False
            
            deviation_percent = ((max_value - min_value) / avg_value) * 100
            
            self.logger.info(f"📊 {triangle}: Triangle Balance - {pair1}=${value1:.0f}, {pair2}=${value2:.0f}, {pair3}=${value3:.0f}, Deviation={deviation_percent:.1f}%")
            
            # ยอมรับได้ถ้าต่างกันไม่เกินค่าใน config - ปรับให้ยืดหยุ่นขึ้น
            max_deviation = self._get_config_value('arbitrage_params.triangles.balance_tolerance_percent', 25.0)
            
            if deviation_percent > max_deviation:
                self.logger.info(f"❌ {triangle}: Imbalance too high ({deviation_percent:.1f}% > {max_deviation}%)")
                return False
            
            self.logger.info(f"✅ {triangle}: Balance acceptable (deviation {deviation_percent:.1f}% <= {max_deviation}%)")
            return True
            
        except Exception as e:
            self.logger.error(f"Error verifying triangle balance: {e}")
            return True  # Return True on error to not block trades
    
    def log_performance_summary(self):
        """
        ⭐ แสดงสรุป Performance Metrics ของระบบ Arbitrage ที่ปรับปรุงแล้ว
        """
        try:
            metrics = self.performance_metrics
            
            # คำนวณ conversion rates
            checked = metrics['opportunities_checked']
            if checked > 0:
                direction_pass_rate = (metrics['passed_direction_check'] / checked) * 100
                feasibility_pass_rate = (metrics['passed_feasibility_check'] / checked) * 100
                balance_pass_rate = (metrics['passed_balance_check'] / checked) * 100
                success_rate = (metrics['successful_trades'] / checked) * 100
            else:
                direction_pass_rate = feasibility_pass_rate = balance_pass_rate = success_rate = 0
            
            # สรุป Forward vs Reverse
            forward = metrics['forward_path_selected']
            reverse = metrics['reverse_path_selected']
            total_paths = forward + reverse
            if total_paths > 0:
                forward_pct = (forward / total_paths) * 100
                reverse_pct = (reverse / total_paths) * 100
            else:
                forward_pct = reverse_pct = 0
            
            self.logger.info("=" * 80)
            self.logger.info("📊 ARBITRAGE SYSTEM PERFORMANCE SUMMARY (IMPROVED)")
            self.logger.info("=" * 80)
            self.logger.info(f"Total Opportunities Checked: {checked}")
            self.logger.info(f"")
            self.logger.info(f"✅ Passed Direction Check: {metrics['passed_direction_check']} ({direction_pass_rate:.1f}%)")
            self.logger.info(f"   └─ Forward Path: {forward} ({forward_pct:.1f}%)")
            self.logger.info(f"   └─ Reverse Path: {reverse} ({reverse_pct:.1f}%)")
            self.logger.info(f"")
            self.logger.info(f"✅ Passed Feasibility Check: {metrics['passed_feasibility_check']} ({feasibility_pass_rate:.1f}%)")
            self.logger.info(f"✅ Passed Balance Check: {metrics['passed_balance_check']} ({balance_pass_rate:.1f}%)")
            self.logger.info(f"")
            self.logger.info(f"🎯 Successful Trades: {metrics['successful_trades']} ({success_rate:.1f}%)")
            self.logger.info(f"💰 Average Expected Profit: {metrics['avg_expected_profit']:.4f}%")
            self.logger.info(f"")
            self.logger.info(f"❌ Orders Cancelled (Failures): {metrics['orders_cancelled_due_to_failure']}")
            self.logger.info("=" * 80)
            
            # คำนวณ Filter Effectiveness
            if checked > 0:
                filtered_out = checked - metrics['successful_trades']
                filter_effectiveness = (filtered_out / checked) * 100
                self.logger.info(f"🔍 Filter Effectiveness: {filter_effectiveness:.1f}% of opportunities filtered out")
                self.logger.info(f"   (This prevents losing trades from poor arbitrage opportunities)")
            
            self.logger.info("=" * 80)
            
        except Exception as e:
            self.logger.error(f"Error logging performance summary: {e}")
    
    def get_active_triangles(self) -> Dict:
        """Get all active triangles"""
        return self.active_triangles
    
    def get_triangle_performance(self) -> Dict:
        """Get performance statistics for triangles"""
        try:
            # Ensure active_triangles is a dict
            if not isinstance(self.active_triangles, dict):
                self.logger.warning(f"active_triangles is not dict: {type(self.active_triangles)}")
                return {
                    'total_triangles': 0,
                    'active_triangles': 0,
                    'closed_triangles': 0,
                    'adaptive_threshold': self.volatility_threshold,
                    'avg_execution_time_ms': 0,
                    'total_opportunities': 0,
                    'successful_trades': 0
                }
            
            total_triangles = len(self.active_triangles)
            active_triangles = 0
            closed_triangles = 0
            
            # Count triangles by status
            for t in self.active_triangles.values():
                if isinstance(t, dict):
                    status = t.get('status', 'unknown')
                    if status == 'active':
                        active_triangles += 1
                    elif status == 'closed':
                        closed_triangles += 1
                else:
                    # If t is not a dict, assume it's active
                    active_triangles += 1
        
            return {
                'total_triangles': total_triangles,
                'active_triangles': active_triangles,
                'closed_triangles': closed_triangles,
                'adaptive_threshold': self.volatility_threshold,
                'avg_execution_time_ms': self.performance_metrics.get('avg_execution_time', 0),
                'total_opportunities': self.performance_metrics.get('total_opportunities', 0),
                'successful_trades': self.performance_metrics.get('successful_trades', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error in get_triangle_performance: {e}")
            return {
                'total_triangles': 0,
                'active_triangles': 0,
                'closed_triangles': 0,
                'adaptive_threshold': 0,
                'avg_execution_time_ms': 0,
                'total_opportunities': 0,
                'successful_trades': 0
        }
    
    def get_adaptive_parameters(self) -> Dict:
        """Get current adaptive parameters"""
        return {
            # 'market_regime': self.market_regime,  # DISABLED - not used in simple trading
            'volatility_threshold': self.volatility_threshold,
            'adaptive_thresholds': self.adaptive_thresholds,
            'execution_speed_ms': self.execution_speed_ms,
            'performance_metrics': self.performance_metrics
        }
    
    def update_adaptive_parameters(self, new_params: Dict):
        """Update adaptive parameters dynamically"""
        try:
            # if 'market_regime' in new_params:  # DISABLED - not used in simple trading
            #     self.market_regime = new_params['market_regime']
            
            if 'volatility_threshold' in new_params:
                self.volatility_threshold = new_params['volatility_threshold']
            
            if 'execution_speed_ms' in new_params:
                self.execution_speed_ms = new_params['execution_speed_ms']
            
            if 'adaptive_thresholds' in new_params:
                self.adaptive_thresholds.update(new_params['adaptive_thresholds'])
            
            # self.logger.info(f"Adaptive parameters updated: {new_params}")  # DISABLED - too verbose
            
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
                # 'market_regime': self.market_regime,  # DISABLED - not used in simple trading
                'adaptive_threshold': self.volatility_threshold,
                'execution_speed_ms': self.performance_metrics['avg_execution_time'],
                'duplicate_prevention': {
                    'used_currency_pairs': {k: list(v) for k, v in self.used_currency_pairs.items()},
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
                'used_currency_pairs': {k: list(v) for k, v in self.used_currency_pairs.items()},
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
            # ตรวจสอบว่าคู่เงินนี้ถูกใช้ในสามเหลี่ยมใดๆ หรือไม่
            for triangle_name, used_pairs in self.used_currency_pairs.items():
                if symbol in used_pairs:
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Error checking currency pair availability: {e}")
            return False
    
    def _save_active_groups(self):
        """บันทึกข้อมูล active groups ลงไฟล์ (รองรับการแยกกันของแต่ละสามเหลี่ยม)"""
        try:
            import json
            import os
            
            # สร้างโฟลเดอร์ data ถ้าไม่มี
            os.makedirs(os.path.dirname(self.persistence_file), exist_ok=True)
            
            # เตรียมข้อมูลสำหรับบันทึก (รองรับการแยกกันของแต่ละสามเหลี่ยม)
            save_data = {
                'active_groups': self.active_groups,
                'recovery_in_progress': list(self.recovery_in_progress),
                'group_counters': self.group_counters,  # แยกตามสามเหลี่ยม
                'is_arbitrage_paused': self.is_arbitrage_paused,  # แยกตามสามเหลี่ยม
                'used_currency_pairs': {k: list(v) for k, v in self.used_currency_pairs.items()},  # แยกตามสามเหลี่ยม
                'group_currency_mapping': self.group_currency_mapping,
                # 'arbitrage_sent': self.arbitrage_sent,  # ไม่ใช้แล้ว - ระบบเก่า
                # 'arbitrage_send_time': self.arbitrage_send_time.isoformat() if self.arbitrage_send_time else None,  # ไม่ใช้แล้ว - ระบบเก่า
                'saved_at': datetime.now().isoformat()
            }
            
            # บันทึกลงไฟล์
            with open(self.persistence_file, 'w') as f:
                json.dump(save_data, f, indent=2, default=str)
            
            self.logger.debug(f"💾 Saved {len(self.active_groups)} active groups to {self.persistence_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving active groups: {e}")
    
    def _load_active_groups(self):
        """โหลดข้อมูล active groups จากไฟล์ (รองรับการแยกกันของแต่ละสามเหลี่ยม)"""
        try:
            import json
            import os
            from datetime import datetime
            
            if not os.path.exists(self.persistence_file):
                self.logger.debug("No persistence file found, starting fresh")
                return
            
            with open(self.persistence_file, 'r') as f:
                save_data = json.load(f)
            
            # โหลดข้อมูลกลับมา (รองรับการแยกกันของแต่ละสามเหลี่ยม)
            self.active_groups = save_data.get('active_groups', {})
            self.recovery_in_progress = set(save_data.get('recovery_in_progress', []))
            
            # โหลดข้อมูลแยกตามสามเหลี่ยม
            self.group_counters = save_data.get('group_counters', {})
            self.is_arbitrage_paused = save_data.get('is_arbitrage_paused', {})
            
            # แปลง used_currency_pairs กลับเป็น set
            used_currency_pairs_data = save_data.get('used_currency_pairs', {})
            if isinstance(used_currency_pairs_data, dict):
                # รูปแบบใหม่: แยกตามสามเหลี่ยม
                self.used_currency_pairs = {k: set(v) for k, v in used_currency_pairs_data.items()}
            else:
                # รูปแบบเก่า: global set (backward compatibility)
                self.used_currency_pairs = {f"triangle_{i}": set(used_currency_pairs_data) for i in range(1, 7)}
            
            self.group_currency_mapping = save_data.get('group_currency_mapping', {})
            # self.arbitrage_sent = save_data.get('arbitrage_sent', False)  # ไม่ใช้แล้ว - ระบบเก่า
            
            # แปลง arbitrage_send_time กลับเป็น datetime (ไม่ใช้แล้ว - ระบบเก่า)
            # arbitrage_send_time_str = save_data.get('arbitrage_send_time')
            # if arbitrage_send_time_str:
            #     self.arbitrage_send_time = datetime.fromisoformat(arbitrage_send_time_str)
            # else:
            #     self.arbitrage_send_time = None
            
            saved_at = save_data.get('saved_at', 'Unknown')
            
            if self.active_groups:
                self.logger.info(f"📂 Loaded {len(self.active_groups)} active groups from {self.persistence_file}")
                self.logger.info(f"   Groups: {list(self.active_groups.keys())}")
                self.logger.info(f"   Recovery in progress: {list(self.recovery_in_progress)}")
                self.logger.info(f"   Saved at: {saved_at}")
            else:
                self.logger.debug("No active groups found in persistence file")
                
        except Exception as e:
            self.logger.error(f"Error loading active groups: {e}")
            # เริ่มต้นใหม่ถ้าโหลดไม่ได้
            self.active_groups = {}
            self.recovery_in_progress = set()
            # self.group_counter = 0  # ไม่ใช้แล้ว - ใช้ group_counters แทน
            # self.arbitrage_sent = False  # ไม่ใช้แล้ว - ระบบเก่า
            # self.arbitrage_send_time = None  # ไม่ใช้แล้ว - ระบบเก่า
            # self.used_currency_pairs = set()  # ไม่ใช้แล้ว - ใช้ used_currency_pairs แทน
            self.group_currency_mapping = {}
    
    def _update_group_data(self, group_id: str, group_data: Dict):
        """อัปเดตข้อมูลกลุ่มและบันทึกลงไฟล์"""
        try:
            self.active_groups[group_id] = group_data
            self._save_active_groups()
        except Exception as e:
            self.logger.error(f"Error updating group data: {e}")
    
    def _remove_group_data(self, group_id: str):
        """ลบข้อมูลกลุ่มและบันทึกลงไฟล์"""
        try:
            if group_id in self.active_groups:
                del self.active_groups[group_id]
            self.recovery_in_progress.discard(group_id)
            self._save_active_groups()
        except Exception as e:
            self.logger.error(f"Error removing group data: {e}")
    
    def _reset_group_data_after_close(self, group_id: str):
        """Reset ข้อมูลหลังจากปิด Group เพื่อให้สามารถส่งไม้ใหม่ได้"""
        try:
            # ดึงข้อมูล triangle_type จาก group_id
            triangle_type = None
            for gid, gdata in list(self.active_groups.items()):
                if gid == group_id:
                    triangle_type = gdata.get('triangle_type', 'unknown')
                    break
            
            # ถ้าไม่พบใน active_groups ให้ลองหาจาก group_id
            if not triangle_type:
                if 'triangle_1' in group_id:
                    triangle_type = 'triangle_1'
                elif 'triangle_2' in group_id:
                    triangle_type = 'triangle_2'
                elif 'triangle_3' in group_id:
                    triangle_type = 'triangle_3'
                elif 'triangle_4' in group_id:
                    triangle_type = 'triangle_4'
                elif 'triangle_5' in group_id:
                    triangle_type = 'triangle_5'
                elif 'triangle_6' in group_id:
                    triangle_type = 'triangle_6'
            
            if triangle_type:
                # ล้างข้อมูล used_currency_pairs สำหรับ triangle นี้
                if triangle_type in self.used_currency_pairs:
                    self.used_currency_pairs[triangle_type].clear()
                    self.logger.info(f"🔄 Cleared used_currency_pairs for {triangle_type}")
                
                # Reset group counter สำหรับ triangle นี้
                if triangle_type in self.group_counters:
                    self.group_counters[triangle_type] = 0
                    self.logger.info(f"🔄 Reset {triangle_type} counter to 0 - next group will be group_{triangle_type}_1")
                
                # Reset hedge tracker สำหรับ group นี้
                if hasattr(self, 'correlation_manager') and self.correlation_manager:
                    # Reset ไม้ arbitrage ทั้งหมดใน group นี้
                    group_pairs = self.group_currency_mapping.get(group_id, [])
                    for symbol in group_pairs:
                        # Individual order tracker handles cleanup automatically via sync
                        self.logger.info(f"🔄 Reset hedge tracker for {group_id}:{symbol}")
                
                # ลบข้อมูล group_currency_mapping สำหรับ group นี้
                if group_id in self.group_currency_mapping:
                    del self.group_currency_mapping[group_id]
                    self.logger.info(f"🔄 Removed group_currency_mapping for {group_id}")
                
                self.logger.info(f"✅ Reset data for {triangle_type} after closing {group_id}")
            else:
                self.logger.warning(f"⚠️ Could not determine triangle_type for {group_id}")
                
        except Exception as e:
            self.logger.error(f"Error resetting group data after close: {e}")
    
    def set_profit_threshold_per_lot(self, threshold_per_lot: float):
        """ตั้งค่าเป้าหมายกำไรต่อ lot สำหรับการปิดกลุ่ม"""
        try:
            self.profit_threshold_per_lot = threshold_per_lot
            self.logger.info(f"🎯 Profit threshold per lot set to {threshold_per_lot} USD")
        except Exception as e:
            self.logger.error(f"Error setting profit threshold per lot: {e}")
    
    def get_profit_threshold_per_lot(self) -> float:
        """ดึงค่าเป้าหมายกำไรต่อ lot ปัจจุบัน"""
        return self.profit_threshold_per_lot
    
    def get_enhanced_group_data_for_gui(self, group_id: str) -> Dict:
        """ดึงข้อมูลเพิ่มเติมสำหรับ GUI (Net PnL, Recovery count, Trailing Stop status)"""
        try:
            # Get basic group data
            group_data = self.active_groups.get(group_id, {})
            
            # Calculate Arbitrage PnL
            arbitrage_pnl = 0.0
            arbitrage_count = len(group_data.get('positions', []))
            
            triangle_type = group_data.get('triangle_type', 'unknown')
            triangle_magic = self.triangle_magic_numbers.get(triangle_type, 234000)
            
            all_positions = self.broker.get_all_positions()
            for pos in all_positions:
                if pos.get('magic') == triangle_magic:
                    arbitrage_pnl += pos.get('profit', 0)
            
            # Calculate Recovery PnL
            recovery_pnl = 0.0
            recovery_count = 0
            if self.correlation_manager:
                recovery_pnl = self._get_recovery_pnl_for_group(group_id)
                
                # Count recovery orders
                all_orders = self.correlation_manager.order_tracker.get_all_orders()
                for order_key, order_data in all_orders.items():
                    if order_data.get('type') == 'RECOVERY':
                        # Check if this recovery belongs to this group
                        hedging_for = order_data.get('hedging_for', '')
                        if hedging_for:
                            # Extract original ticket
                            original_ticket = hedging_for.split('_')[0] if '_' in hedging_for else None
                            if original_ticket:
                                # Check if original ticket belongs to this group
                                for pos in all_positions:
                                    if str(pos.get('ticket')) == str(original_ticket) and pos.get('magic') == triangle_magic:
                                        recovery_count += 1
                                        break
            
            # Calculate Net PnL
            net_pnl = arbitrage_pnl + recovery_pnl
            
            # Calculate Min Profit Target (scaled with balance)
            balance = self.broker.get_account_balance()
            if not balance or balance <= 0:
                balance = 10000.0
            
            # ⭐ ใช้ min_profit_base ตรงๆ ไม่คูณด้วย balance_multiplier
            min_profit_target = self.min_profit_base
            
            # Get Trailing Stop Status
            trailing_active = False
            trailing_peak = 0.0
            trailing_stop = 0.0
            
            if group_id in self.group_trailing_stops:
                trailing_data = self.group_trailing_stops[group_id]
                trailing_active = trailing_data.get('active', False)
                trailing_peak = trailing_data.get('peak', 0.0)
                trailing_stop = trailing_data.get('stop', 0.0)
            
            # Return enhanced data
            return {
                'arbitrage_pnl': arbitrage_pnl,
                'recovery_pnl': recovery_pnl,
                'net_pnl': net_pnl,
                'arbitrage_count': arbitrage_count,
                'recovery_count': recovery_count,
                'min_profit_target': min_profit_target,
                'trailing_active': trailing_active,
                'trailing_peak': trailing_peak,
                'trailing_stop': trailing_stop,
                'balance': balance
            }
        except Exception as e:
            self.logger.error(f"Error getting enhanced group data: {e}")
            return {
                'arbitrage_pnl': 0.0,
                'recovery_pnl': 0.0,
                'net_pnl': 0.0,
                'arbitrage_count': 0,
                'recovery_count': 0,
                'min_profit_target': 5.0,
                'trailing_active': False,
                'trailing_peak': 0.0,
                'trailing_stop': 0.0,
                'balance': 10000.0
            }
    
    def update_active_groups_with_enhanced_data(self):
        """อัปเดตข้อมูลเพิ่มเติมใน active_groups สำหรับ GUI"""
        try:
            for group_id in list(self.active_groups.keys()):
                enhanced_data = self.get_enhanced_group_data_for_gui(group_id)
                self.active_groups[group_id].update(enhanced_data)
        except Exception as e:
            self.logger.error(f"Error updating active groups with enhanced data: {e}")
    
    def _load_trailing_stop_config(self):
        """โหลด Trailing Stop Config จาก adaptive_params.json"""
        try:
            import json
            import os
            
            try:
                import json
                with open('config/adaptive_params.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception:
                config_path = 'config/adaptive_params.json'
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                else:
                    config = {}
            
            # Load arbitrage params
            arb_params = config.get('arbitrage_params', {})
            detection = arb_params.get('detection', {})
            closing = arb_params.get('closing', {})
            triangles = arb_params.get('triangles', {})
            
            # ⭐ Load Trailing Stop Settings
            self.trailing_stop_enabled = closing.get('trailing_stop_enabled', True)
            self.trailing_stop_distance = closing.get('trailing_stop_distance', 10.0)
            self.min_profit_base = closing.get('min_profit_base', 10.0)
            self.min_profit_base_balance = closing.get('min_profit_base_balance', 10000.0)
            self.lock_profit_percentage = closing.get('lock_profit_percentage', 0.5)
            
            # ⭐ Load Arbitrage Detection Settings
            self.min_arbitrage_threshold = detection.get('min_threshold', 0.0001)
            self.spread_tolerance = detection.get('spread_tolerance', 0.5)
            
            # ⭐ Load Triangle Settings
            self.max_active_triangles_config = triangles.get('max_active_triangles', 4)
            
            self.logger.info("=" * 60)
            self.logger.info("✅ ARBITRAGE CONFIG LOADED")
            self.logger.info("=" * 60)
            self.logger.info(f"🔒 Trailing Stop: {'ENABLED' if self.trailing_stop_enabled else 'DISABLED'}")
            if self.trailing_stop_enabled:
                self.logger.info(f"   Distance: ${self.trailing_stop_distance}")
                self.logger.info(f"   Min Profit: ${self.min_profit_base} @ ${self.min_profit_base_balance}")
                self.logger.info(f"   Lock Profit: {self.lock_profit_percentage*100:.0f}% of Peak")
            self.logger.info(f"⚡ Min Threshold: {self.min_arbitrage_threshold}")
            self.logger.info(f"📊 Spread Tolerance: {self.spread_tolerance} pips")
            self.logger.info(f"🔺 Max Active Triangles: {self.max_active_triangles_config}")
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"❌ Error loading trailing stop config: {e}")
            # Fallback values
            self.trailing_stop_enabled = True
            self.trailing_stop_distance = 10.0
            self.min_profit_base = 10.0
            self.min_profit_base_balance = 10000.0
            self.lock_profit_percentage = 0.5
            self.min_arbitrage_threshold = 0.0001
            self.spread_tolerance = 0.5
            self.max_active_triangles_config = 4
    
    def reload_config(self):
        """โหลดการตั้งค่าใหม่จาก config file (Hot Reload!)"""
        try:
            self.logger.info("🔄 Reloading arbitrage config from adaptive_params.json...")
            self._load_trailing_stop_config()
            self.logger.info("✅ Arbitrage config reloaded!")
            return True
                
        except Exception as e:
            self.logger.error(f"❌ Error reloading arbitrage config: {e}")
            return False
