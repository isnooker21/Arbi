"""
ระบบจัดการความเสี่ยงในการเทรด

ไฟล์นี้ทำหน้าที่:
- ควบคุมขนาดตำแหน่งตามความเสี่ยง
- ตั้งค่า Stop Loss และ Take Profit
- ตรวจสอบ Daily Loss Limit
- คำนวณ Maximum Drawdown
- จัดการ Emergency Stop

ฟีเจอร์หลัก:
- Position Sizing: คำนวณขนาดตำแหน่งที่เหมาะสม
- Risk Limits: ตั้งขีดจำกัดความเสี่ยง
- Drawdown Control: ควบคุมการขาดทุนสูงสุด
- Time-based Exits: ปิดตำแหน่งตามเวลา
- Emergency Stop: หยุดเทรดในกรณีฉุกเฉิน
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
import json
import os

class RiskManager:
    def __init__(self, config_file: str = "config/settings.json"):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_file)
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.max_drawdown = 0.0
        self.peak_balance = 0.0
        self.risk_limits = self.config.get('risk_management', {})
        
        # Enhanced Risk Management
        self.max_exposure_per_pair = self.risk_limits.get('max_exposure_per_pair', 0.02)  # 2%
        self.max_total_exposure = self.risk_limits.get('max_total_exposure', 0.1)        # 10%
        self.current_exposures = {}  # {symbol: exposure_percent}
        self.active_positions = {}   # {symbol: [position_data]}
        self.volatility_data = {}    # {symbol: volatility}
        
        # Circuit Breaker
        self.is_tripped = False
        self.trip_time = None
        self.trip_reason = None
        self.error_count = 0
        self.total_operations = 0
        self.cooldown_minutes = self.risk_limits.get('cooldown_minutes', 30)
        
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            # Use config helper to support EXE and user override
            try:
                from utils.config_helper import get_config_path
                cfg_path = get_config_path(os.path.basename(config_file))
            except Exception:
                cfg_path = config_file
            with open(cfg_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return {}
    
    def should_trigger_stop_loss(self, position: Dict) -> bool:
        """Check if position should trigger stop loss - DISABLED for Never-Cut-Loss strategy"""
        # DISABLED: ระบบ Never-Cut-Loss ไม่ใช้ stop loss
        return False
    
    def should_trigger_take_profit(self, position: Dict) -> bool:
        """Check if position should trigger take profit"""
        try:
            current_pnl = position.get('profit', 0)
            entry_price = position.get('price', 0)
            current_price = position.get('current_price', entry_price)
            
            if entry_price == 0:
                return False
            
            # Calculate percentage profit
            if position.get('type') == 'BUY':
                profit_percent = (current_price - entry_price) / entry_price * 100
            else:  # SELL
                profit_percent = (entry_price - current_price) / entry_price * 100
            
            take_profit_percent = self.risk_limits.get('take_profit_percent', 1.0)
            
            return profit_percent >= take_profit_percent
            
        except Exception as e:
            self.logger.error(f"Error checking take profit: {e}")
            return False
    
    def should_trigger_trailing_stop(self, position: Dict) -> bool:
        """Check if position should trigger trailing stop"""
        try:
            current_pnl = position.get('profit', 0)
            max_profit = position.get('max_profit', 0)
            
            # Only apply trailing stop if position was profitable
            if max_profit <= 0:
                return False
            
            # Calculate trailing stop threshold (50% of max profit)
            trailing_threshold = max_profit * 0.5
            
            return current_pnl < trailing_threshold
            
        except Exception as e:
            self.logger.error(f"Error checking trailing stop: {e}")
            return False
    
    def should_trigger_max_drawdown(self, position: Dict) -> bool:
        """Check if position should trigger max drawdown limit"""
        try:
            current_drawdown = position.get('current_drawdown', 0)
            max_drawdown_percent = self.risk_limits.get('max_drawdown_percent', 30)
            
            return current_drawdown >= max_drawdown_percent
            
        except Exception as e:
            self.logger.error(f"Error checking max drawdown: {e}")
            return False
    
    def should_trigger_time_exit(self, position: Dict) -> bool:
        """Check if position should trigger time-based exit"""
        try:
            entry_time = position.get('entry_time')
            if not entry_time:
                return False
            
            # Convert to datetime if it's a string
            if isinstance(entry_time, str):
                try:
                    entry_time = datetime.fromisoformat(entry_time)
                except ValueError:
                    entry_time = datetime.now()
            
            position_age = datetime.now() - entry_time
            max_hold_time = timedelta(seconds=self.config.get('trading', {}).get('position_hold_time', 3600))
            
            return position_age > max_hold_time
            
        except Exception as e:
            self.logger.error(f"Error checking time exit: {e}")
            return False
    
    def calculate_position_size(self, symbol: str, account_balance: float, 
                              risk_percent: float = 1.0, pip_value: float = 10.0, max_loss_pips: float = 100) -> float:
        """
        Calculate appropriate position size based on proper risk management
        
        Args:
            symbol: Trading symbol
            account_balance: Account balance in USD
            risk_percent: Risk percentage (e.g., 1.0 means 1% risk if move 100 pips)
            pip_value: Pip value per 1.0 lot (default $10 for major pairs)
            max_loss_pips: Maximum pips to move before hitting risk limit
            
        Returns:
            float: Calculated lot size
        """
        try:
            # 🎯 สูตร Risk Management ที่ถูกต้อง
            # Risk Amount = Balance × (Risk% ÷ 100)
            # Lot Size = Risk Amount ÷ (Pip Value × Max Loss Pips)
            
            # Calculate risk amount
            risk_amount = account_balance * (risk_percent / 100.0)
            
            # Calculate pip value for max_loss_pips
            pip_value_for_risk = pip_value * max_loss_pips
            
            # Calculate lot size
            position_size = risk_amount / pip_value_for_risk
            
            # Apply minimum and maximum limits
            min_size = 0.01
            max_size = 5.0
            
            # Round to valid lot size (0.01 step)
            position_size = round(position_size / 0.01) * 0.01
            
            final_size = max(min_size, min(position_size, max_size))
            
            self.logger.info(f"💰 Risk Manager Proper Lot Calculation:")
            self.logger.info(f"   Balance=${account_balance:.2f}")
            self.logger.info(f"   Risk={risk_percent}% => Risk Amount=${risk_amount:.2f}")
            self.logger.info(f"   Max Loss Pips={max_loss_pips}")
            self.logger.info(f"   Pip Value=${pip_value:.2f}/lot")
            self.logger.info(f"   Risk Pip Value=${pip_value_for_risk:.2f} ({max_loss_pips} pips)")
            self.logger.info(f"   Final Lot={final_size:.4f}")
            self.logger.info(f"   ✅ If move {max_loss_pips} pips → Loss = ${final_size * pip_value * max_loss_pips:.2f} ({risk_percent}% of balance)")
            
            return final_size
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.01  # Minimum fallback
    
    def check_daily_limits(self, current_pnl: float) -> bool:
        """Check if daily limits have been exceeded"""
        try:
            # DISABLED: ระบบ Never-Cut-Loss ไม่ใช้ daily loss limit
            # Update daily PnL
            self.daily_pnl = current_pnl
            
            # ไม่มีการตรวจสอบ daily loss limit
            return False
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking daily limits: {e}")
            return False
    
    def update_drawdown(self, current_balance: float):
        """Update maximum drawdown tracking"""
        try:
            # Update peak balance
            if current_balance > self.peak_balance:
                self.peak_balance = current_balance
            
            # Calculate current drawdown
            current_drawdown = (self.peak_balance - current_balance) / self.peak_balance * 100
            
            # Update maximum drawdown
            if current_drawdown > self.max_drawdown:
                self.max_drawdown = current_drawdown
                
        except Exception as e:
            self.logger.error(f"Error updating drawdown: {e}")
    
    def should_stop_trading(self) -> bool:
        """Check if trading should be stopped due to risk limits"""
        try:
            # DISABLED: ระบบ Never-Cut-Loss ไม่ใช้ daily loss limit
            # if self.daily_pnl <= -self.risk_limits.get('max_daily_loss', 1000):
            #     return True
            
            # Check maximum drawdown
            if self.max_drawdown >= self.risk_limits.get('max_drawdown_percent', 30):
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking stop trading condition: {e}")
            return False
    
    def reset_daily_limits(self):
        """Reset daily limits (call at start of new trading day)"""
        try:
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.logger.info("Daily limits reset")
            
        except Exception as e:
            self.logger.error(f"Error resetting daily limits: {e}")
    
    def get_risk_status(self) -> Dict:
        """Get current risk management status"""
        try:
            return {
                'daily_pnl': self.daily_pnl,
                'daily_trades': self.daily_trades,
                'max_drawdown': self.max_drawdown,
                'peak_balance': self.peak_balance,
                'current_drawdown': (self.peak_balance - self.daily_pnl) / self.peak_balance * 100 if self.peak_balance > 0 else 0,
                'stop_trading': self.should_stop_trading(),
                'limits': self.risk_limits
            }
            
        except Exception as e:
            self.logger.error(f"Error getting risk status: {e}")
            return {}
    
    def validate_trade(self, symbol: str, order_type: str, volume: float, 
                      account_balance: float) -> Dict:
        """Validate a trade before execution"""
        try:
            validation_result = {
                'valid': True,
                'warnings': [],
                'errors': [],
                'adjusted_volume': volume
            }
            
            # Check if trading should be stopped
            if self.should_stop_trading():
                validation_result['valid'] = False
                validation_result['errors'].append("Trading stopped due to risk limits")
                return validation_result
            
            # Check daily limits
            if self.check_daily_limits(self.daily_pnl):
                validation_result['valid'] = False
                validation_result['errors'].append("Daily loss limit exceeded")
                return validation_result
            
            # Validate position size
            max_volume = self.calculate_position_size(symbol, account_balance, 2.0)  # 2% risk
            if volume > max_volume:
                validation_result['warnings'].append(f"Volume {volume} exceeds recommended {max_volume}")
                validation_result['adjusted_volume'] = max_volume
            
            # Check symbol restrictions (if any)
            restricted_symbols = self.config.get('trading', {}).get('restricted_symbols', [])
            if symbol in restricted_symbols:
                validation_result['valid'] = False
                validation_result['errors'].append(f"Symbol {symbol} is restricted")
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error validating trade: {e}")
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': [],
                'adjusted_volume': 0
            }
    
    def log_trade(self, symbol: str, order_type: str, volume: float, 
                 price: float, pnl: float = 0):
        """Log a trade for risk tracking"""
        try:
            self.daily_trades += 1
            
            # Update daily PnL
            self.daily_pnl += pnl
            
            # Update drawdown
            self.update_drawdown(self.daily_pnl)
            
            self.logger.info(f"Trade logged: {symbol} {order_type} {volume} @ {price}, "
                           f"PnL: {pnl:.2f}, Daily PnL: {self.daily_pnl:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error logging trade: {e}")
    
    # Enhanced Risk Management Functions
    def check_position_limits(self, symbol: str, proposed_volume: float, 
                            account_balance: float) -> tuple[bool, str]:
        """ตรวจสอบขีดจำกัดตำแหน่ง"""
        try:
            # ตรวจสอบการเปิดเผยต่อคู่เงิน
            current_exposure = self.current_exposures.get(symbol, 0)
            proposed_exposure = (proposed_volume * self.get_contract_value(symbol)) / account_balance
            
            if current_exposure + proposed_exposure > self.max_exposure_per_pair:
                return False, f"Per-pair exposure limit exceeded for {symbol}"
            
            # ตรวจสอบการเปิดเผยรวม
            total_exposure = sum(self.current_exposures.values()) + proposed_exposure
            if total_exposure > self.max_total_exposure:
                return False, "Total exposure limit exceeded"
            
            # ตรวจสอบตำแหน่งซ้ำซ้อน
            if self.has_conflicting_position(symbol, proposed_volume):
                return False, f"Conflicting position exists for {symbol}"
            
            return True, "Position approved"
            
        except Exception as e:
            self.logger.error(f"Error checking position limits for {symbol}: {e}")
            return False, f"Error checking position limits: {str(e)}"
    
    def calculate_position_size(self, symbol: str, risk_percent: float, 
                              stop_loss_pips: float, account_balance: float) -> float:
        """คำนวณขนาดตำแหน่งแบบ Dynamic"""
        try:
            # คำนวณความผันผวน
            volatility = self.get_symbol_volatility(symbol)
            volatility_adjustment = min(1.0, 1.0 / (volatility * 100))
            
            # คำนวณขนาดตำแหน่งพื้นฐาน
            risk_amount = account_balance * (risk_percent / 100)
            pip_value = self.get_pip_value(symbol)
            base_position_size = risk_amount / (stop_loss_pips * pip_value)
            
            # ปรับตามความผันผวน
            adjusted_size = base_position_size * volatility_adjustment
            
            # ใช้ขีดจำกัดตำแหน่ง
            max_allowed = (account_balance * self.max_exposure_per_pair) / self.get_contract_value(symbol)
            final_size = min(adjusted_size, max_allowed)
            
            # จำกัดขนาดขั้นต่ำและสูงสุด
            min_size = 0.01
            max_size = 10.0
            final_size = max(min_size, min(final_size, max_size))
            
            return round(final_size, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating position size for {symbol}: {e}")
            return 0.01
    
    def update_exposure(self, symbol: str, volume: float, action: str = "add"):
        """อัปเดตการเปิดเผยความเสี่ยง"""
        try:
            contract_value = self.get_contract_value(symbol) * volume
            account_balance = self.get_account_balance()
            exposure = contract_value / account_balance if account_balance > 0 else 0
            
            if action == "add":
                self.current_exposures[symbol] = self.current_exposures.get(symbol, 0) + exposure
            elif action == "remove":
                self.current_exposures[symbol] = max(0, self.current_exposures.get(symbol, 0) - exposure)
            
        except Exception as e:
            self.logger.error(f"Error updating exposure for {symbol}: {e}")
    
    def has_conflicting_position(self, symbol: str, volume: float) -> bool:
        """ตรวจสอบว่ามีตำแหน่งขัดแย้งหรือไม่"""
        try:
            if symbol not in self.active_positions:
                return False
            
            for pos in self.active_positions[symbol]:
                if pos.get('status') == 'active':
                    pos_volume = pos.get('volume', 0)
                    if abs(pos_volume + volume) < abs(pos_volume):
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking conflicting position for {symbol}: {e}")
            return False
    
    def get_symbol_volatility(self, symbol: str) -> float:
        """รับความผันผวนของสัญลักษณ์"""
        return self.volatility_data.get(symbol, 0.5)
    
    def get_contract_value(self, symbol: str) -> float:
        """รับมูลค่าสัญญาของสัญลักษณ์"""
        return 100000  # Standard lot
    
    def get_pip_value(self, symbol: str) -> float:
        """รับมูลค่า pip ของสัญลักษณ์"""
        return 10.0  # Standard pip value
    
    def get_account_balance(self) -> float:
        """รับยอดเงินในบัญชี"""
        try:
            # Try to get balance from broker if available
            if hasattr(self, 'broker_api') and self.broker_api and self.broker_api.is_connected():
                balance = self.broker_api.get_account_balance()
                if balance is not None:
                    return balance
            
            # ไม่มี fallback - ต้องได้จาก broker เท่านั้น
            return None
        except Exception as e:
            self.logger.error(f"Error getting account balance: {e}")
            return None
    
    def update_account_balance(self, balance: float):
        """อัปเดตยอดเงินในบัญชี"""
        self.account_balance = balance
    
    # Circuit Breaker Functions
    def check_circuit_breaker(self, current_pnl: float, account_balance: float) -> bool:
        """ตรวจสอบเงื่อนไข Circuit Breaker"""
        try:
            # DISABLED: ระบบ Never-Cut-Loss ไม่ใช้ daily loss limit
            # if abs(current_pnl) > self.risk_limits.get('max_daily_loss', 1000):
            #     self.trip_circuit_breaker("Daily loss limit exceeded")
            #     return False
            
            # ตรวจสอบ drawdown
            if account_balance > 0:
                if account_balance > self.peak_balance:
                    self.peak_balance = account_balance
                
                drawdown_percent = (self.peak_balance - account_balance) / self.peak_balance * 100
                if drawdown_percent > self.risk_limits.get('max_drawdown_percent', 30):
                    self.trip_circuit_breaker("Drawdown limit exceeded")
                    return False
            
            # ตรวจสอบ error rate
            if self.total_operations > 0:
                error_rate = (self.error_count / self.total_operations) * 100
                if error_rate > self.risk_limits.get('max_error_rate', 50):
                    self.trip_circuit_breaker("Error rate too high")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking circuit breaker: {e}")
            return False
    
    def trip_circuit_breaker(self, reason: str):
        """Trip ระบบ Circuit Breaker"""
        try:
            if not self.is_tripped:
                self.is_tripped = True
                self.trip_time = datetime.now()
                self.trip_reason = reason
                self.logger.critical(f"CIRCUIT BREAKER TRIPPED: {reason}")
                
        except Exception as e:
            self.logger.error(f"Error tripping circuit breaker: {e}")
    
    def can_trade(self) -> bool:
        """ตรวจสอบว่าสามารถเทรดได้หรือไม่"""
        try:
            if not self.is_tripped:
                return True
            
            # ตรวจสอบ cooldown period
            if self.trip_time and datetime.now() - self.trip_time > timedelta(minutes=self.cooldown_minutes):
                self.reset_circuit_breaker()
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking if can trade: {e}")
            return False
    
    def reset_circuit_breaker(self):
        """รีเซ็ตระบบ Circuit Breaker"""
        try:
            self.is_tripped = False
            self.trip_time = None
            self.trip_reason = None
            self.error_count = 0
            self.total_operations = 0
            self.logger.info("Circuit breaker reset")
            
        except Exception as e:
            self.logger.error(f"Error resetting circuit breaker: {e}")
    
    def record_operation(self, success: bool = True):
        """บันทึกการดำเนินงาน"""
        try:
            self.total_operations += 1
            if not success:
                self.error_count += 1
                
        except Exception as e:
            self.logger.error(f"Error recording operation: {e}")
    
    def get_enhanced_status(self) -> Dict:
        """รับสถานะ Enhanced Risk Manager"""
        try:
            current_drawdown = 0.0
            if self.peak_balance > 0:
                current_drawdown = (self.peak_balance - self.get_account_balance()) / self.peak_balance * 100
            
            error_rate = 0.0
            if self.total_operations > 0:
                error_rate = (self.error_count / self.total_operations) * 100
            
            return {
                'is_tripped': self.is_tripped,
                'trip_time': self.trip_time.isoformat() if self.trip_time else None,
                'trip_reason': self.trip_reason,
                'can_trade': self.can_trade(),
                'daily_pnl': self.daily_pnl,
                'daily_trades': self.daily_trades,
                'error_count': self.error_count,
                'total_operations': self.total_operations,
                'error_rate': error_rate,
                'current_balance': self.get_account_balance(),
                'peak_balance': self.peak_balance,
                'current_drawdown': current_drawdown,
                'current_exposures': self.current_exposures,
                'active_positions': {symbol: len(positions) for symbol, positions in self.active_positions.items()},
                'limits': {
                    'max_drawdown_percent': self.risk_limits.get('max_drawdown_percent', 30),
                    'max_error_rate': self.risk_limits.get('max_error_rate', 50),
                    'cooldown_minutes': self.cooldown_minutes,
                    'max_exposure_per_pair': self.max_exposure_per_pair,
                    'max_total_exposure': self.max_total_exposure
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting enhanced status: {e}")
            return {}
