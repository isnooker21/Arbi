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

# Ensure project root is on sys.path when running this module directly
try:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if PROJECT_ROOT not in sys.path:
        sys.path.append(PROJECT_ROOT)
except Exception:
    pass
from utils.calculations import TradingCalculations
from utils.symbol_mapper import SymbolMapper

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
        self.arbitrage_threshold = 0.008  # Higher threshold (0.8 pips) for better accuracy
        self.volatility_threshold = 0.008  # Same as arbitrage_threshold for simple trading
        self.execution_timeout = 150  # Target execution speed
        self.position_size = 0.1  # Default position size
        
        # Enhanced validation parameters
        self.min_confidence_score = 0.75  # Minimum confidence score (75%)
        self.max_spread_ratio = 0.3  # Maximum spread ratio (30%)
        self.min_volume_threshold = 0.5  # Minimum volume threshold
        self.price_stability_checks = 3  # Number of price stability checks
        self.confirmation_delay = 2  # Seconds to wait for confirmation
        
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
            'avg_execution_time': 0
            # 'market_regime_changes': 0  # DISABLED - not used in simple trading
        }
        
        # Initialize pairs and combinations after logger is set
        self.available_pairs = self._get_available_pairs()
        
        # 🆕 Symbol Mapper - จับคู่ชื่อคู่เงินกับนามสกุลจริงของ Broker
        self.symbol_mapper = SymbolMapper()
        
        # ใช้ 6 สามเหลี่ยม Arbitrage แยกกัน (Optimized - ทุกคู่ซ้ำ Hedged!)
        self.arbitrage_pairs = [
            'EURUSD', 'GBPUSD', 'EURGBP',  # Group 1
            'USDCHF', 'EURCHF',            # Group 2, 5
            'USDJPY', 'GBPJPY',            # Group 3
            'AUDUSD', 'USDCAD', 'AUDCAD',  # Group 4
            'NZDUSD', 'NZDCHF', 'AUDNZD'   # Group 5, 6
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
        
        # ใช้ lot size ปกติ 0.1 สำหรับทุกคู่เงิน
        self.standard_lot_size = 0.1
        
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
                    
                    del self.active_groups[group_id]
                    self._save_active_groups()
                    self._reset_group_data_after_close(group_id)
                
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
                
                # แสดงสถานะ
                if active_triangles:
                    self.logger.info(f"📊 Active triangles: {active_triangles}")
                if closed_triangles:
                    self.logger.info(f"📊 Closed triangles: {closed_triangles}")
                
                # ตรวจสอบและปิด groups ที่มีกำไร (ทำใน loop ข้างบนแล้ว)
                
                # ส่งไม้ใหม่สำหรับ triangles ที่ปิดแล้ว
                if closed_triangles:
                    self.logger.info(f"🎯 Sending new orders for closed triangles: {closed_triangles}")
                    self._send_orders_for_closed_triangles(closed_triangles)
                
                # ถ้าไม่มี triangles ที่เปิดอยู่เลย
                if not active_triangles:
                    self.logger.info("🔄 No active triangles - resetting data")
                    self._reset_group_data()
                
                time.sleep(30.0)  # รอ 30 วินาที
                continue
                    
            except Exception as e:
                self.logger.error(f"Trading error: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                time.sleep(1)
        
        self.logger.info("🛑 Simple trading system stopped")
    
    def _send_orders_for_closed_triangles(self, closed_triangles: List[str]):
        """ส่งออเดอร์ใหม่สำหรับ triangles ที่ปิดแล้ว"""
        try:
            # ดึง balance จาก broker
            balance = self.broker.get_account_balance()
            if not balance:
                self.logger.error("❌ Cannot get account balance - using default lot size")
                balance = 10000  # Fallback balance
            
            for triangle_name in closed_triangles:
                # ตรวจสอบว่าสามเหลี่ยมนี้ถูก pause หรือไม่
                if self.is_arbitrage_paused.get(triangle_name, False):
                    self.logger.info(f"⏸️ {triangle_name} is paused - skipping")
                    continue
                
                # หา triangle combination
                triangle_index = int(triangle_name.split('_')[-1]) - 1
                if triangle_index < len(self.triangle_combinations):
                    triangle = self.triangle_combinations[triangle_index]
                    
                    # ส่งออเดอร์สำหรับสามเหลี่ยมนี้
                    self.logger.info(f"🚀 Sending new orders for {triangle_name}: {triangle}")
                    self._send_orders_for_triangle(triangle, triangle_name, balance)
                else:
                    self.logger.warning(f"⚠️ Invalid triangle index for {triangle_name}")
                
        except Exception as e:
            self.logger.error(f"Error in _send_orders_for_closed_triangles: {e}")
    
    def _send_simple_orders(self):
        """ส่งออเดอร์ง่ายๆ สำหรับทุกสามเหลี่ยม arbitrage - ใช้ balance-based lot sizing"""
        try:
            # ดึง balance จาก broker
            balance = self.broker.get_account_balance()
            if not balance:
                self.logger.error("❌ Cannot get account balance - using default lot size")
                balance = 10000  # Fallback balance
            
            # ตรวจสอบไม้จาก MT5 ก่อน
            all_positions = self.broker.get_all_positions()
            
            # ตรวจสอบว่ามีไม้ arbitrage อยู่หรือไม่ (ใช้ magic number)
            arbitrage_positions = []
            for pos in all_positions:
                magic = pos.get('magic', 0)
                if 234001 <= magic <= 234006:
                    arbitrage_positions.append(pos)
            
            # ซิงค์ข้อมูลจาก MT5 กับ memory
            self._sync_active_groups_from_mt5(arbitrage_positions)
            
            # ตรวจสอบแต่ละสามเหลี่ยมว่าสามารถส่งออเดอร์ได้หรือไม่
            for i, triangle in enumerate(self.triangle_combinations, 1):
                triangle_name = f"triangle_{i}"
                
                # ตรวจสอบว่าสามเหลี่ยมนี้ถูก pause หรือไม่
                if self.is_arbitrage_paused.get(triangle_name, False):
                    continue
                
                # ตรวจสอบว่ามีไม้ arbitrage สำหรับสามเหลี่ยมนี้อยู่แล้วหรือไม่ใน MT5 (ใช้ magic number)
                has_arbitrage_positions = False
                triangle_magic = self.triangle_magic_numbers.get(triangle_name, 234000)
                
                for pos in arbitrage_positions:
                    magic = pos.get('magic', 0)
                    if magic == triangle_magic:
                        has_arbitrage_positions = True
                        break
                
                if has_arbitrage_positions:
                    continue  # ข้ามไปสามเหลี่ยมถัดไป
                
                # ส่งออเดอร์สำหรับสามเหลี่ยมนี้
                self.logger.info(f"🚀 Sending orders for {triangle_name}: {triangle}")
                self._send_orders_for_triangle(triangle, triangle_name, balance)
                
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
                        'lot_size': pos.get('volume', 0.1),
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
    
    def _send_orders_for_triangle(self, triangle, triangle_name, balance):
        """ส่งออเดอร์สำหรับสามเหลี่ยมเดียว"""
        try:
            self.logger.info(f"🔍 Processing {triangle_name}: {triangle}")
            
            # โหลดค่าจาก config
            from utils.config_helper import load_config
            config = load_config('adaptive_params.json')
            lot_calc_config = config.get('position_sizing', {}).get('lot_calculation', {})
            use_simple_mode = lot_calc_config.get('use_simple_mode', False)
            use_risk_based_sizing = lot_calc_config.get('use_risk_based_sizing', True)
            risk_per_trade_percent = lot_calc_config.get('risk_per_trade_percent', 1.5)

            self.logger.info(f"🔍 DEBUG: Arbitrage Detector - Config for Lot Calc:")
            self.logger.info(f"   use_simple_mode={use_simple_mode}")
            self.logger.info(f"   use_risk_based_sizing={use_risk_based_sizing}")
            self.logger.info(f"   risk_per_trade_percent={risk_per_trade_percent}")
            self.logger.info(f"   Current Balance: ${balance}")

            # คำนวณ lot sizes ให้ pip value เท่ากัน + scale ตาม balance
            triangle_symbols = list(triangle)
            lot_sizes = TradingCalculations.get_uniform_triangle_lots(
                triangle_symbols=triangle_symbols,
                balance=balance,
                target_pip_value=5.0,  # $5 pip value base (reduced from $10 for lower risk)
                broker_api=self.broker,  # ส่ง broker API สำหรับดึงอัตราแลกเปลี่ยน
                use_simple_mode=use_simple_mode,  # ใช้ค่าจาก config
                use_risk_based_sizing=use_risk_based_sizing,  # 🔥 ส่ง risk-based flag
                risk_per_trade_percent=risk_per_trade_percent  # 🔥 ส่ง risk percentage
            )
            self.logger.info(f"🔍 DEBUG: Arbitrage Detector - Calculated Lot Sizes: {lot_sizes}")
            
            self.logger.info(f"📊 {triangle_name} lot sizes: {lot_sizes}")
            
            # สร้างกลุ่มใหม่สำหรับสามเหลี่ยมนี้
            self.group_counters[triangle_name] += 1
            group_id = f"group_{triangle_name}_{self.group_counters[triangle_name]}"
            self.logger.info(f"🆕 Creating new group: {group_id} for {triangle_name}")
            
            # สร้างข้อมูลกลุ่ม
            group_data = {
                'group_id': group_id,
                'triangle': triangle,
                'triangle_type': triangle_name,
                'created_at': datetime.now(),
                'positions': [],
                'status': 'active',
                'total_pnl': 0.0,
                'recovery_chain': [],
                'lot_sizes': lot_sizes  # เก็บ lot sizes ไว้ในกลุ่ม
            }
            
            # ส่งออเดอร์ 3 คู่พร้อมกัน
            self.logger.info("🔍 Preparing to send orders...")
            orders_sent = 0
            order_results = []
            
            # สร้างข้อมูลออเดอร์ทั้ง 3 คู่ พร้อม lot sizes (ใช้ triangle parameter)
            orders_to_send = []
            for i, symbol in enumerate(triangle):
                # กำหนดทิศทางตามลำดับ: คู่แรก BUY, คู่ที่สอง SELL, คู่ที่สาม BUY
                direction = 'BUY' if i % 2 == 0 else 'SELL'
                orders_to_send.append({
                    'symbol': symbol,
                    'direction': direction,
                    'group_id': group_id,
                    'index': i,
                    'lot_size': lot_sizes.get(symbol, 0.01)
                })
            
            # ส่งออเดอร์พร้อมกันด้วย threading
            self.logger.info("🔍 Setting up threading for order execution...")
            threads = []
            results = [None] * 3
            
            def send_single_order(order_data, result_index):
                """ส่งออเดอร์เดี่ยวใน thread แยก"""
                try:
                    self.logger.info(f"🔍 Thread {result_index}: Starting order for {order_data['symbol']}")
                    
                    # Note: Individual order tracker doesn't prevent duplicates at this level
                    # Duplicate prevention is handled by the broker API and order execution
                    
                    # สร้าง comment ตามหมายเลขสามเหลี่ยม (1-6)
                    triangle_number = triangle_name.split('_')[-1]  # ได้ 1, 2, 3, 4, 5, 6
                    comment = f"G{triangle_number}_{order_data['symbol']}"
                    
                    # ใช้ lot size ที่คำนวณแล้ว
                    lot_size = order_data.get('lot_size', 0.01)
                    
                    # ใช้ magic number สำหรับสามเหลี่ยมนี้
                    magic_number = self.triangle_magic_numbers.get(triangle_name, 234000)
                    
                    # 🆕 แปลง symbol ผ่าน mapper
                    real_symbol = self.symbol_mapper.get_real_symbol(order_data['symbol'])
                    
                    self.logger.info(f"🔍 Thread {result_index}: Sending {order_data['symbol']} → {real_symbol} {order_data['direction']} {lot_size} lot (Magic: {magic_number})")
                    result = self.broker.place_order(
                        symbol=real_symbol,
                        order_type=order_data['direction'],
                        volume=lot_size,
                        comment=comment,
                        magic=magic_number
                    )
                    
                    if result and result.get('retcode') == 10009:
                        results[result_index] = {
                            'success': True,
                            'symbol': order_data['symbol'],
                            'direction': order_data['direction'],
                            'order_id': result.get('order_id'),
                            'index': result_index
                        }
                        
                        # Register original arbitrage order in individual order tracker
                        if hasattr(self, 'correlation_manager') and self.correlation_manager:
                            group_id = f"group_{triangle_name}_{self.group_counters[triangle_name]}"
                            order_id = result.get('order_id')
                            if order_id:
                                success = self.correlation_manager.order_tracker.register_original_order(
                                    str(order_id), order_data['symbol'], group_id
                                )
                                if success:
                                    self.logger.info(f"✅ Original arbitrage order registered: {order_id}_{order_data['symbol']} in {group_id}")
                                else:
                                    self.logger.warning(f"⚠️ Failed to register original arbitrage order: {order_id}_{order_data['symbol']}")
                    else:
                        results[result_index] = {
                            'success': False,
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
            self.logger.info("🔍 Starting order threads...")
            for i, order_data in enumerate(orders_to_send):
                thread = threading.Thread(
                    target=send_single_order, 
                    args=(order_data, i),
                    daemon=True
                )
                threads.append(thread)
                thread.start()
            
            # รอให้ออเดอร์ทั้งหมดเสร็จสิ้น
            self.logger.info("🔍 Waiting for all threads to complete...")
            for thread in threads:
                thread.join(timeout=5.0)
            
            self.logger.info("🔍 All threads completed, processing results...")
            
            end_time = datetime.now()
            total_execution_time = (end_time - start_time).total_seconds() * 1000
            
            # ตรวจสอบผลลัพธ์
            for result in results:
                if result and result['success']:
                    orders_sent += 1
                    # 🆕 แปลง symbol ผ่าน mapper
                    real_symbol = self.symbol_mapper.get_real_symbol(result['symbol'])
                    # ดึงราคาปัจจุบันเป็น entry price
                    entry_price = self.broker.get_current_price(real_symbol)
                    if not entry_price:
                        entry_price = 0.0
                    
                    # ใช้ lot_size ที่คำนวณแล้ว
                    lot_size = lot_sizes.get(result['symbol'], 0.01)
                    
                    group_data['positions'].append({
                        'symbol': result['symbol'],
                        'direction': result['direction'],
                        'lot_size': lot_size,
                        'entry_price': entry_price,
                        'status': 'active',
                        'order_id': result.get('order_id'),
                        'comment': f"G{group_id.split('_')[-1]}_{result['symbol']}"
                    })
                    self.logger.info(f"✅ Order sent: {result['symbol']} {result['direction']} {lot_size} lot")
                elif result:
                    self.logger.error(f"❌ Order failed: {result['symbol']} {result['direction']}")
                    if 'error' in result:
                        self.logger.error(f"   Error: {result['error']}")
            
            # ตรวจสอบว่าส่งออเดอร์สำเร็จครบ 3 คู่
            if orders_sent == 3:
                # เก็บ comment ใน used_currency_pairs เพื่อให้ reset ได้
                triangle_number = triangle_name.split('_')[-1]  # ได้ 1, 2, 3, 4, 5, 6
                for result in results:
                    if result and result.get('success'):
                        comment = f"G{triangle_number}_{result['symbol']}"
                        # เก็บคู่เงินใน used_currency_pairs สำหรับสามเหลี่ยมนี้
                        if triangle_name not in self.used_currency_pairs:
                            self.used_currency_pairs[triangle_name] = set()
                        self.used_currency_pairs[triangle_name].add(result['symbol'])
                        self.logger.debug(f"💾 Added {result['symbol']} to used_currency_pairs[{triangle_name}]")
                
                self._update_group_data(group_id, group_data)
                self.logger.info(f"✅ Group {group_id} created successfully")
                self.logger.info(f"   🚀 Orders sent: {orders_sent}/3")
                self.logger.info(f"   ⏱️ Execution time: {total_execution_time:.1f}ms")
                self.logger.info("🔄 เริ่มใช้ระบบ Correlation Recovery")
            else:
                self.logger.error(f"❌ Failed to create group {group_id}")
                self.logger.error(f"   Orders sent: {orders_sent}/3")
                
        except Exception as e:
            self.logger.error(f"Error sending orders: {e}")
    
    def detect_opportunities(self):
        """Legacy method - ไม่ใช้แล้ว ใช้ _send_simple_orders แทน"""
        self.logger.debug("🔍 detect_opportunities called (legacy method - not used)")
        return
    
    def _create_arbitrage_group(self, triangle: Tuple[str, str, str], opportunity: Dict) -> bool:
        """Legacy method - ไม่ใช้แล้ว ใช้ _send_simple_orders แทน"""
        self.logger.debug("🔍 _create_arbitrage_group called (legacy method - not used)")
        return False
    
    def _send_arbitrage_order(self, symbol: str, direction: str, group_id: str, triangle_name: str = None) -> bool:
        """ส่งออเดอร์ arbitrage"""
        try:            
            # สร้าง comment ที่แสดงกลุ่มและลำดับ
            if triangle_name:
                triangle_number = triangle_name.split('_')[-1]  # ได้ 1, 2, 3, 4, 5, 6
            else:
                # Fallback: ใช้ group_id
                triangle_number = group_id.split('_')[-1]
            comment = f"ARB_G{triangle_number}_{symbol}"
            
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
                
                # Track ไม้ arbitrage ใน individual order tracker
                if hasattr(self, 'correlation_manager') and self.correlation_manager:
                    # Individual order tracker doesn't need locking - each order is tracked individually
                    pass
                
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
                        self.logger.info(f"🔄 Group {group_id} losing - Total PnL: {total_group_pnl:.2f} USD ({profit_percentage:.2f}%)")
                        self.logger.info(f"🔄 Starting correlation recovery - Never cut loss")
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
            total_lot_size = sum(pos.get('volume', 0.1) for pos in group_positions)
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
            self.logger.info(f"✅ Group {triangle_type} meets recovery conditions - Distance: {max_price_distance:.1f} pips")
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
                        'lot_size': pos.get('volume', 0.1),
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
            
            balance_multiplier = balance / self.min_profit_base_balance
            min_profit_threshold = self.min_profit_base * balance_multiplier
            
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
                # แก้ทุกคู่ที่ติดลบพร้อมกัน
                self.logger.info(f"🔄 Starting correlation recovery for {len(losing_pairs)} losing pairs")
                for pair in losing_pairs:
                    self.logger.info(f"   📉 {pair['symbol']}: {pair['loss_percent']:.2f}% loss")
                
                # ตั้งค่าว่ากำลัง recovery
                self.recovery_in_progress.add(group_id)
                
                # ส่ง recovery สำหรับทุกคู่ที่ติดลบพร้อมกัน
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
            comment_patterns = [
                f"G{triangle_number}_EURUSD",
                f"G{triangle_number}_GBPUSD", 
                f"G{triangle_number}_EURGBP",
                f"RECOVERY_G{triangle_number}_",
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
            
            balance_multiplier = balance / self.min_profit_base_balance
            min_profit_target = self.min_profit_base * balance_multiplier
            
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
                from utils.config_helper import load_config
                config = load_config('adaptive_params.json')
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
