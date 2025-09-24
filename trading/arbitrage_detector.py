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
from utils.calculations import TradingCalculations

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
            'avg_execution_time': 0
            # 'market_regime_changes': 0  # DISABLED - not used in simple trading
        }
        
        # Initialize pairs and combinations after logger is set
        self.available_pairs = self._get_available_pairs()
        
        # ใช้เฉพาะคู่เงิน Arbitrage 3 คู่ที่กำหนด
        self.arbitrage_pairs = ['EURUSD', 'GBPUSD', 'EURGBP']
        self.triangle_combinations = [('EURUSD', 'GBPUSD', 'EURGBP')]  # Fixed triangle combination
        
        # ใช้ lot size ปกติ 0.1 สำหรับทุกคู่เงิน
        self.standard_lot_size = 0.1
        
        # ระบบป้องกันการส่ง recovery ซ้ำ
        self.recovery_in_progress = set()  # เก็บ group_id ที่กำลัง recovery
        
        # ระบบ Save/Load ข้อมูล
        self.persistence_file = "data/active_groups.json"
        
        # การตั้งค่าการปิดกลุ่ม
        self.profit_threshold_per_lot = 1.0  # 1 USD ต่อ lot เดี่ยว
        
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
        
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system

    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
    # Method removed - not used in simple system
    
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
                self.logger.info(f"🔄 Trading loop #{loop_count} - Checking system status...")
                
                # ตรวจสอบว่ามีกลุ่มที่เปิดอยู่จริงหรือไม่
                if len(self.active_groups) > 0:
                    # ตรวจสอบว่า Group ยังเปิดอยู่จริงใน broker หรือไม่
                    has_valid_groups = False
                    for group_id, group_data in list(self.active_groups.items()):
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
                            has_valid_groups = True
                            break
                        else:
                            # ลบ Group ที่ไม่มี valid positions
                            self.logger.info(f"🗑️ Group {group_id} has no valid positions - removing from active groups")
                            del self.active_groups[group_id]
                            # บันทึกการเปลี่ยนแปลง
                            self._save_active_groups()
                    
                    if has_valid_groups:
                        self.logger.info(f"📊 Found {len(self.active_groups)} active groups - monitoring positions...")
                        
                        # แสดงสถานะไม้ทุกครั้งที่ตรวจสอบ
                        for group_id, group_data in self.active_groups.items():
                            self.logger.info(f"🔍 Checking group {group_id} for recovery conditions...")
                            # เรียก correlation manager เพื่อตรวจสอบพร้อมแสดงสถานะ
                            if self.correlation_manager:
                                # ดึงข้อมูล losing pairs จาก group_data
                                losing_pairs = []
                                positions_list = group_data.get('positions', [])
                                
                                # positions เป็น list ของ position data
                                for position_data in positions_list:
                                    if position_data.get('order_id'):
                                        losing_pairs.append({
                                            'symbol': position_data.get('symbol', ''),
                                            'order_id': position_data.get('order_id'),
                                            'lot_size': position_data.get('lot_size', 0.1),
                                            'entry_price': position_data.get('entry_price', 0.0)
                                        })
                                
                                # เรียกฟังก์ชันที่แสดงสถานะการแก้ไม้
                                self.correlation_manager.check_recovery_positions_with_status(group_id, losing_pairs)
                        
                        time.sleep(30.0)  # รอ 30 วินาที (ลด log ที่ไม่จำเป็น)
                        continue
                    else:
                        # ถ้าไม่มี Group ที่เปิดอยู่จริง ให้ reset ข้อมูล
                        self.logger.info("🔄 No valid groups found - resetting group data")
                        self._reset_group_data()
                
                # ออกไม้ทันทีตามคู่เงินที่กำหนด
                self.logger.info("🎯 No active groups - attempting to send new orders...")
                self._send_simple_orders()
                
                # รอ 30 วินาทีก่อนตรวจสอบอีกครั้ง (ลด log ที่ไม่จำเป็น)
                self.logger.info("⏰ Waiting 30 seconds before next check...")
                time.sleep(30.0)
                    
            except Exception as e:
                self.logger.error(f"Trading error: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                time.sleep(1)
        
        self.logger.info("🛑 Simple trading system stopped")
    
    def _send_simple_orders(self):
        """ส่งออเดอร์ง่ายๆ ตามคู่เงินที่กำหนด - ใช้ balance-based lot sizing"""
        try:
            self.logger.info("🔍 Starting _send_simple_orders...")
            
            # ดึง balance จาก broker
            self.logger.info("🔍 Getting account balance...")
            balance = self.broker.get_account_balance()
            if not balance:
                self.logger.error("❌ Cannot get account balance - using default lot size")
                balance = 10000  # Fallback balance
            
            self.logger.info(f"💰 Account Balance: {balance:.2f} USD")
            
            # คำนวณ lot sizes ให้ pip value เท่ากัน + scale ตาม balance
            self.logger.info("🔍 Calculating lot sizes...")
            triangle_symbols = ['EURUSD', 'GBPUSD', 'EURGBP']
            lot_sizes = TradingCalculations.get_uniform_triangle_lots(
                triangle_symbols=triangle_symbols,
                balance=balance,
                target_pip_value=10.0,  # $10 pip value base
                broker_api=self.broker  # ส่ง broker API สำหรับดึงอัตราแลกเปลี่ยน
            )
            
            self.logger.info(f"📊 Calculated lot sizes: {lot_sizes}")
            
            # สร้างกลุ่มใหม่
            self.logger.info("🔍 Creating new group...")
            self.group_counter += 1
            group_id = f"simple_group_{self.group_counter}"
            self.logger.info(f"🆕 Creating new group: {group_id} (Counter: {self.group_counter})")
            
            # สร้างข้อมูลกลุ่ม
            self.logger.info("🔍 Setting up group data...")
            group_data = {
                'group_id': group_id,
                'triangle': ('EURUSD', 'GBPUSD', 'EURGBP'),
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
            
            # สร้างข้อมูลออเดอร์ทั้ง 3 คู่ พร้อม lot sizes
            orders_to_send = [
                {'symbol': 'EURUSD', 'direction': 'BUY', 'group_id': group_id, 'index': 0, 'lot_size': lot_sizes.get('EURUSD', 0.01)},
                {'symbol': 'GBPUSD', 'direction': 'SELL', 'group_id': group_id, 'index': 1, 'lot_size': lot_sizes.get('GBPUSD', 0.01)},
                {'symbol': 'EURGBP', 'direction': 'BUY', 'group_id': group_id, 'index': 2, 'lot_size': lot_sizes.get('EURGBP', 0.01)}
            ]
            
            # ส่งออเดอร์พร้อมกันด้วย threading
            self.logger.info("🔍 Setting up threading for order execution...")
            threads = []
            results = [None] * 3
            
            def send_single_order(order_data, result_index):
                """ส่งออเดอร์เดี่ยวใน thread แยก"""
                try:
                    self.logger.info(f"🔍 Thread {result_index}: Starting order for {order_data['symbol']}")
                    
                    # สร้าง comment
                    group_number = group_id.split('_')[-1]
                    comment = f"SIMPLE_G{group_number}_{order_data['symbol']}"
                    
                    # ใช้ lot size ที่คำนวณแล้ว
                    lot_size = order_data.get('lot_size', 0.01)
                    
                    self.logger.info(f"🔍 Thread {result_index}: Sending {order_data['symbol']} {order_data['direction']} {lot_size} lot")
                    result = self.broker.place_order(
                        symbol=order_data['symbol'],
                        order_type=order_data['direction'],
                        volume=lot_size,
                        comment=comment
                    )
                    
                    if result and result.get('retcode') == 10009:
                        results[result_index] = {
                            'success': True,
                            'symbol': order_data['symbol'],
                            'direction': order_data['direction'],
                            'order_id': result.get('order_id'),
                            'index': result_index
                        }
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
                    # ดึงราคาปัจจุบันเป็น entry price
                    entry_price = self.broker.get_current_price(result['symbol'])
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
                        'comment': f"SIMPLE_G{group_id.split('_')[-1]}_{result['symbol']}"
                    })
                    self.logger.info(f"✅ Order sent: {result['symbol']} {result['direction']} {lot_size} lot")
                elif result:
                    self.logger.error(f"❌ Order failed: {result['symbol']} {result['direction']}")
                    if 'error' in result:
                        self.logger.error(f"   Error: {result['error']}")
            
            # ตรวจสอบว่าส่งออเดอร์สำเร็จครบ 3 คู่
            if orders_sent == 3:
                # เก็บ comment ใน used_currency_pairs เพื่อให้ reset ได้
                group_number = group_id.split('_')[-1]
                for result in results:
                    if result and result.get('success'):
                        comment = f"SIMPLE_G{group_number}_{result['symbol']}"
                        self.used_currency_pairs.add(comment)
                        self.logger.debug(f"💾 Added comment to used_currency_pairs: {comment}")
                
                self._update_group_data(group_id, group_data)
                self.logger.info(f"✅ Simple group {group_id} created successfully")
                self.logger.info(f"   🚀 Orders sent: {orders_sent}/3")
                self.logger.info(f"   ⏱️ Execution time: {total_execution_time:.1f}ms")
                self.logger.info("🔄 เริ่มใช้ระบบ Correlation Recovery")
            else:
                self.logger.error(f"❌ Failed to create simple group {group_id}")
                self.logger.error(f"   Orders sent: {orders_sent}/3")
                
        except Exception as e:
            self.logger.error(f"Error sending simple orders: {e}")
    
    def detect_opportunities(self):
        """Legacy method - ไม่ใช้แล้ว ใช้ _send_simple_orders แทน"""
        self.logger.debug("🔍 detect_opportunities called (legacy method - not used)")
        return
    
    def _create_arbitrage_group(self, triangle: Tuple[str, str, str], opportunity: Dict) -> bool:
        """Legacy method - ไม่ใช้แล้ว ใช้ _send_simple_orders แทน"""
        self.logger.debug("🔍 _create_arbitrage_group called (legacy method - not used)")
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
            self.logger.debug(f"🔍 Checking group status - Active groups: {len(self.active_groups)}")
            
            if not self.active_groups:
                # ถ้าไม่มีกลุ่มที่เปิดอยู่ ให้ reset ข้อมูล
                self.logger.debug("No active groups found - resetting group data")
                self._reset_group_data()
                return
            
            groups_to_close = []
            
            for group_id, group_data in self.active_groups.items():
                # ตรวจสอบว่ากลุ่มหมดเวลา 24 ชั่วโมง
                created_at = group_data['created_at']
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)
                
                if (datetime.now() - created_at).total_seconds() > 86400:  # 24 hours
                    self.logger.warning(f"⏰ Group {group_id} expired after 24 hours")
                    groups_to_close.append(group_id)
                    continue
                
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
                
                # คำนวณ PnL ของ recovery positions ที่เกี่ยวข้องกับกลุ่มนี้
                recovery_pnl = 0.0
                if self.correlation_manager:
                    for recovery_id, recovery_data in self.correlation_manager.recovery_positions.items():
                        if recovery_data.get('group_id') == group_id and recovery_data.get('status') == 'active':
                            recovery_order_id = recovery_data.get('order_id')
                            if recovery_order_id:
                                # ตรวจสอบ PnL ของ recovery position
                                all_positions = self.broker.get_all_positions()
                                for pos in all_positions:
                                    if pos['ticket'] == recovery_order_id:
                                        recovery_pnl += pos['profit']
                                        self.logger.debug(f"   Recovery {recovery_data['symbol']}: PnL = {pos['profit']:.2f} USD")
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
                
                # คำนวณกำไรต่อ lot เดี่ยว (รวม recovery positions)
                # นับจำนวน positions ทั้งหมด (arbitrage + recovery)
                total_positions_count = len(group_data['positions'])
                if self.correlation_manager:
                    recovery_count = sum(1 for recovery_data in self.correlation_manager.recovery_positions.values() 
                                       if recovery_data.get('group_id') == group_id and recovery_data.get('status') == 'active')
                    total_positions_count += recovery_count
                
                # ใช้จำนวน positions จริงในการคำนวณ
                if total_positions_count > 0:
                    profit_per_single_lot = total_group_pnl / total_positions_count
                else:
                    profit_per_single_lot = 0.0
                
                # self.logger.info(f"   📊 Total Positions: {total_positions_count} (Arbitrage: {len(group_data['positions'])}, Recovery: {total_positions_count - len(group_data['positions'])})")  # DISABLED - too verbose
                
                # ปิดกลุ่มเมื่อกำไรต่อ lot เดี่ยว ถึงเป้าหมาย
                if profit_per_single_lot >= self.profit_threshold_per_lot:
                    self.logger.info(f"✅ Group {group_id} reached profit target - Total PnL: {total_group_pnl:.2f} USD")
                    self.logger.info(f"✅ Closing group {group_id} - All positions will be closed together")
                    self.logger.info(f"   🎯 Profit per single lot: {profit_per_single_lot:.2f} USD (Target: {self.profit_threshold_per_lot} USD)")
                    groups_to_close.append(group_id)
                elif total_group_pnl > 0:
                    self.logger.info(f"💰 Group {group_id} profitable but below threshold - Total PnL: {total_group_pnl:.2f} USD")
                    self.logger.info(f"   🎯 Profit per single lot: {profit_per_single_lot:.2f} USD (Target: {self.profit_threshold_per_lot} USD)")
                elif self._should_start_recovery(group_id, group_data, total_group_pnl, profit_percentage):
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
    
    def _should_start_recovery(self, group_id: str, group_data: Dict, total_pnl: float, profit_percentage: float) -> bool:
        """ตรวจสอบว่าควรเริ่ม recovery หรือไม่ - เงื่อนไข 2 ชั้น"""
        try:
            # เงื่อนไข 0: ตรวจสอบว่าไม่มีการ recovery อยู่แล้ว
            if group_id in self.recovery_in_progress:
                self.logger.debug(f"⏳ Group {group_id} already in recovery - skipping")
                return False
            
            # เงื่อนไข 1: ตรวจสอบ correlation manager
            if not self.correlation_manager:
                return False
            
            # เงื่อนไข 2: คำนวณ risk per lot (ชั้นที่ 1)
            total_lot_size = sum(pos.get('lot_size', pos.get('volume', 0)) for pos in group_data['positions'])
            if total_lot_size <= 0:
                return False
                
            risk_per_lot = abs(total_pnl) / total_lot_size
            self.logger.info(f"🔍 Recovery check for {group_id}: PnL={total_pnl:.2f}, Lot size={total_lot_size:.1f}, Risk per lot={risk_per_lot:.2%}")
            
            if risk_per_lot < 0.05:  # risk น้อยกว่า 5%
                self.logger.info(f"⏳ Group {group_id} risk too low ({risk_per_lot:.2%}) - Waiting for 5%")
                return False
            
            # เงื่อนไข 3: ตรวจสอบระยะห่างราคา (ชั้นที่ 2)
            max_price_distance = 0
            self.logger.info(f"🔍 Checking price distance for {group_id}...")
            
            for position in group_data['positions']:
                symbol = position['symbol']
                entry_price = position.get('entry_price', 0)
                
                # ดึงราคาปัจจุบัน
                try:
                    current_price = self.broker.get_current_price(symbol)
                    if entry_price > 0 and current_price > 0:
                        # คำนวณ price distance ตามประเภทคู่เงิน
                        if 'JPY' in symbol:
                            # คู่เงินที่มี JPY ใช้ 100 เป็นตัวคูณ
                            price_distance = abs(current_price - entry_price) * 100
                        else:
                            # คู่เงินอื่นใช้ 10000 เป็นตัวคูณ
                            price_distance = abs(current_price - entry_price) * 10000
                        
                        max_price_distance = max(max_price_distance, price_distance)
                        self.logger.info(f"📊 {symbol}: Entry {entry_price:.5f}, Current {current_price:.5f}, Distance {price_distance:.1f} pips")
                    else:
                        self.logger.warning(f"⚠️ {symbol}: Entry price {entry_price}, Current price {current_price}")
                except Exception as e:
                    self.logger.warning(f"Could not get price for {symbol}: {e}")
                    continue
            
            self.logger.info(f"🔍 Max price distance: {max_price_distance:.1f} pips (required: 10 pips)")
            
            if max_price_distance < 10:  # ระยะห่างน้อยกว่า 10 จุด
                self.logger.info(f"⏳ Group {group_id} price distance too small ({max_price_distance:.1f} pips) - Waiting for 10 pips")
                return False
            
            # ผ่านเงื่อนไขทั้งหมด - แก้ไม้ทันที
            self.logger.info(f"✅ Group {group_id} meets recovery conditions - Risk: {risk_per_lot:.2%}, Distance: {max_price_distance:.1f} pips")
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking recovery conditions: {e}")
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
            
            # ลบคู่เงินและ comment ออกจากรายการที่ใช้แล้ว
            if group_id in self.group_currency_mapping:
                group_pairs = self.group_currency_mapping[group_id]
                self.used_currency_pairs -= group_pairs
                del self.group_currency_mapping[group_id]
                self.logger.info(f"   📊 คู่เงินที่ปลดล็อค: {group_pairs}")
            
            # ลบ comment ออกจาก used_currency_pairs
            group_number = group_id.split('_')[-1]
            comments_to_remove = []
            for comment in list(self.used_currency_pairs):
                if comment.startswith(f"SIMPLE_G{group_number}_"):
                    comments_to_remove.append(comment)
            
            for comment in comments_to_remove:
                self.used_currency_pairs.discard(comment)
                self.logger.debug(f"🗑️ Removed comment from used_currency_pairs: {comment}")
            
            if comments_to_remove:
                self.logger.info(f"   🔄 Comments removed: {comments_to_remove}")
            
            # ปิด recovery positions ที่เกี่ยวข้องกับกลุ่มนี้
            correlation_pnl = 0.0
            recovery_positions_closed = 0
            if self.correlation_manager:
                correlation_pnl = self._close_recovery_positions_for_group(group_id)
                # นับจำนวน recovery positions ที่ปิด (ใช้ข้อมูลจาก log)
                recovery_positions_closed = len([r for r in self.correlation_manager.recovery_positions.values() 
                                               if r.get('status') == 'closed' and r.get('group_id') == group_id])
                # ล้างข้อมูลการแก้ไม้สำหรับกลุ่มนี้
                self.correlation_manager.clear_hedged_data_for_group(group_id)
            
            # ลบกลุ่มออกจาก active_groups
            self._remove_group_data(group_id)
            
            # Reset arbitrage_sent เพื่อให้สามารถส่งออเดอร์ใหม่ได้
            self.arbitrage_sent = False
            self.arbitrage_send_time = None
            
            # Reset recovery_in_progress สำหรับกลุ่มนี้
            if group_id in self.recovery_in_progress:
                self.recovery_in_progress.remove(group_id)
                self.logger.info(f"🔄 Reset recovery status for group {group_id}")
            
            # Reset group counter กลับไปเป็น 0 เมื่อปิดกลุ่มแล้ว
            old_counter = self.group_counter
            self.group_counter = 0
            self.logger.info(f"🔄 Reset group counter from {old_counter} to 0 - next group will be simple_group_1")
            
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
    
    def _close_recovery_positions_for_group(self, group_id: str):
        """ปิด recovery positions ที่เกี่ยวข้องกับกลุ่ม arbitrage และคืนค่า PnL รวม"""
        try:
            if not self.correlation_manager:
                return 0.0
            
            # หา recovery positions ที่เกี่ยวข้องกับกลุ่มนี้
            group_data = self.active_groups.get(group_id, {})
            group_pairs = set(group_data.get('triangle', []))
            
            recovery_positions_to_close = []
            total_correlation_pnl = 0.0
            
            # ตรวจสอบ recovery positions ทั้งหมด
            for recovery_id, recovery_data in self.correlation_manager.recovery_positions.items():
                # ตรวจสอบหลายวิธีเพื่อหา original symbol
                original_symbol = ''
                
                # วิธีที่ 1: จาก original_pair
                if 'original_pair' in recovery_data:
                    original_symbol = recovery_data['original_pair']
                # วิธีที่ 2: จาก original_position
                elif 'original_position' in recovery_data:
                    original_symbol = recovery_data['original_position'].get('symbol', '')
                # วิธีที่ 3: จาก group_id
                elif recovery_data.get('group_id') == group_id:
                    original_symbol = 'MATCH'  # ใช้เป็น flag
                
                # ถ้า recovery position นี้เกี่ยวข้องกับกลุ่ม arbitrage นี้
                if (original_symbol in group_pairs) or (original_symbol == 'MATCH'):
                    recovery_positions_to_close.append(recovery_id)
                    self.logger.info(f"🔍 Found recovery position {recovery_id} for group {group_id} (original: {original_symbol})")
            
            # ปิด recovery positions ที่เกี่ยวข้องและเก็บ PnL
            if recovery_positions_to_close:
                self.logger.info(f"🔄 Closing {len(recovery_positions_to_close)} recovery positions for group {group_id}")
                for recovery_id in recovery_positions_to_close:
                    self.logger.info(f"   🔄 Closing recovery position {recovery_id}")
                    pnl = self.correlation_manager._close_recovery_position(recovery_id)
                    if pnl is not None:
                        total_correlation_pnl += pnl
            
            # ปิด recovery positions ทั้งหมดที่เกี่ยวข้องกับกลุ่มนี้ (เพิ่มเติม)
            # ตรวจสอบ recovery positions ที่มี group_id ตรงกัน
            additional_recovery_positions = []
            for recovery_id, recovery_data in self.correlation_manager.recovery_positions.items():
                if recovery_data.get('group_id') == group_id and recovery_id not in recovery_positions_to_close:
                    additional_recovery_positions.append(recovery_id)
            
            # ปิด recovery positions เพิ่มเติมและเก็บ PnL
            if additional_recovery_positions:
                self.logger.info(f"🔄 Closing {len(additional_recovery_positions)} additional recovery positions for group {group_id}")
                for recovery_id in additional_recovery_positions:
                    self.logger.info(f"   🔄 Closing additional recovery position {recovery_id}")
                    pnl = self.correlation_manager._close_recovery_position(recovery_id)
                    if pnl is not None:
                        total_correlation_pnl += pnl
            
            total_recovery_closed = len(recovery_positions_to_close) + len(additional_recovery_positions)
            if total_recovery_closed > 0:
                self.logger.info(f"✅ Closed {total_recovery_closed} recovery positions for group {group_id}")
                self.logger.info(f"   💰 Total Correlation PnL: {total_correlation_pnl:.2f} USD")
            
            return total_correlation_pnl
            
        except Exception as e:
            self.logger.error(f"Error closing recovery positions for group {group_id}: {e}")
            return 0.0
    
    def _reset_comments_for_group(self, group_id: str):
        """Reset comment สำหรับกลุ่มที่ปิดแล้ว"""
        try:
            # ดึงหมายเลขกลุ่ม
            group_number = group_id.split('_')[-1]
            
            # สร้าง comment patterns ที่ต้อง reset
            comment_patterns = [
                f"SIMPLE_G{group_number}_EURUSD",
                f"SIMPLE_G{group_number}_GBPUSD", 
                f"SIMPLE_G{group_number}_EURGBP",
                f"RECOVERY_G{group_number}_",
                f"ARB_G{group_number}_"
            ]
            
            # Debug: แสดง used_currency_pairs ปัจจุบัน
            self.logger.info(f"🔍 Current used_currency_pairs: {list(self.used_currency_pairs)}")
            self.logger.info(f"🔍 Looking for patterns: {comment_patterns}")
            
            # ตรวจสอบว่ามี comment ที่ใช้อยู่หรือไม่
            used_comments = set()
            for pattern in comment_patterns:
                # Check if any used_currency_pairs starts with this pattern
                for used_pair in list(self.used_currency_pairs):  # Iterate over a copy
                    if used_pair.startswith(pattern):
                        used_comments.add(used_pair)
                        self.logger.info(f"✅ Found matching comment: {used_pair}")
            
            # ลบ comment ที่ใช้แล้วออกจาก used_currency_pairs
            for comment in used_comments:
                self.used_currency_pairs.discard(comment)
            
            if used_comments:
                self.logger.info(f"🔄 Reset comments for group {group_id}: {used_comments}")
                self.logger.info(f"🔄 Remaining used_currency_pairs: {list(self.used_currency_pairs)}")
            else:
                self.logger.info(f"🔄 No comments to reset for group {group_id}")
            
        except Exception as e:
            self.logger.error(f"Error resetting comments for group {group_id}: {e}")
    
    def _reset_group_data(self):
        """Reset ข้อมูลกลุ่มให้ถูกต้อง"""
        try:
            # ตรวจสอบว่ามีกลุ่มที่เปิดอยู่จริงหรือไม่
            if len(self.active_groups) == 0:
                # ถ้าไม่มีกลุ่มที่เปิดอยู่ ให้ reset ข้อมูลทั้งหมด
                self.used_currency_pairs.clear()
                self.group_currency_mapping.clear()
                self.recovery_in_progress.clear()
                # Reset group counter เมื่อไม่มีกลุ่มที่เปิดอยู่
                old_counter = self.group_counter
                self.group_counter = 0
                self.logger.info("🔄 Reset ข้อมูลกลุ่ม - คู่เงินและ comment ทั้งหมดปลดล็อคแล้ว")
                self.logger.info(f"🔄 Reset group counter from {old_counter} to 0 - next group will be simple_group_1")
            else:
                # ถ้ายังมีกลุ่มที่เปิดอยู่ ให้ตรวจสอบข้อมูลให้ถูกต้อง
                current_used_pairs = set()
                groups_to_remove = []
                
                for group_id, group_data in self.active_groups.items():
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
        total_triangles = len(self.active_triangles)
        active_triangles = sum(1 for t in self.active_triangles.values() if t['status'] == 'active')
        closed_triangles = sum(1 for t in self.active_triangles.values() if t['status'] == 'closed')
        
        return {
            'total_triangles': total_triangles,
            'active_triangles': active_triangles,
            'closed_triangles': closed_triangles,
            # 'market_regime': self.market_regime,  # DISABLED - not used in simple trading
            'adaptive_threshold': self.volatility_threshold,
            'avg_execution_time_ms': self.performance_metrics['avg_execution_time'],
            'total_opportunities': self.performance_metrics['total_opportunities'],
            'successful_trades': self.performance_metrics['successful_trades'],
            # 'market_regime_changes': self.performance_metrics['market_regime_changes'],  # DISABLED - not used in simple trading
            'used_currency_pairs': list(self.used_currency_pairs),
            'active_groups_count': len(self.active_groups),
            'group_currency_mapping': self.group_currency_mapping
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
    
    def _save_active_groups(self):
        """บันทึกข้อมูล active groups ลงไฟล์"""
        try:
            import json
            import os
            
            # สร้างโฟลเดอร์ data ถ้าไม่มี
            os.makedirs(os.path.dirname(self.persistence_file), exist_ok=True)
            
            # เตรียมข้อมูลสำหรับบันทึก
            save_data = {
                'active_groups': self.active_groups,
                'recovery_in_progress': list(self.recovery_in_progress),
                'group_counter': self.group_counter,
                'arbitrage_sent': self.arbitrage_sent,
                'arbitrage_send_time': self.arbitrage_send_time.isoformat() if self.arbitrage_send_time else None,
                'used_currency_pairs': list(self.used_currency_pairs),
                'group_currency_mapping': self.group_currency_mapping,
                'saved_at': datetime.now().isoformat()
            }
            
            # บันทึกลงไฟล์
            with open(self.persistence_file, 'w') as f:
                json.dump(save_data, f, indent=2, default=str)
            
            self.logger.debug(f"💾 Saved {len(self.active_groups)} active groups to {self.persistence_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving active groups: {e}")
    
    def _load_active_groups(self):
        """โหลดข้อมูล active groups จากไฟล์"""
        try:
            import json
            import os
            from datetime import datetime
            
            if not os.path.exists(self.persistence_file):
                self.logger.debug("No persistence file found, starting fresh")
                return
            
            with open(self.persistence_file, 'r') as f:
                save_data = json.load(f)
            
            # โหลดข้อมูลกลับมา
            self.active_groups = save_data.get('active_groups', {})
            self.recovery_in_progress = set(save_data.get('recovery_in_progress', []))
            self.group_counter = save_data.get('group_counter', 0)
            self.arbitrage_sent = save_data.get('arbitrage_sent', False)
            
            # แปลง arbitrage_send_time กลับเป็น datetime
            arbitrage_send_time_str = save_data.get('arbitrage_send_time')
            if arbitrage_send_time_str:
                self.arbitrage_send_time = datetime.fromisoformat(arbitrage_send_time_str)
            else:
                self.arbitrage_send_time = None
            
            self.used_currency_pairs = set(save_data.get('used_currency_pairs', []))
            self.group_currency_mapping = save_data.get('group_currency_mapping', {})
            
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
            self.group_counter = 0
            self.arbitrage_sent = False
            self.arbitrage_send_time = None
            self.used_currency_pairs = set()
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
