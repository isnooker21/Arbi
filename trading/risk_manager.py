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

class RiskManager:
    def __init__(self, config_file: str = "config/settings.json"):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_file)
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.max_drawdown = 0.0
        self.peak_balance = 0.0
        self.risk_limits = self.config.get('risk_management', {})
        
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return {}
    
    def should_trigger_stop_loss(self, position: Dict) -> bool:
        """Check if position should trigger stop loss"""
        try:
            current_pnl = position.get('profit', 0)
            entry_price = position.get('price', 0)
            current_price = position.get('current_price', entry_price)
            
            if entry_price == 0:
                return False
            
            # Calculate percentage loss
            if position.get('type') == 'BUY':
                loss_percent = (entry_price - current_price) / entry_price * 100
            else:  # SELL
                loss_percent = (current_price - entry_price) / entry_price * 100
            
            stop_loss_percent = self.risk_limits.get('stop_loss_percent', 2.0)
            
            return loss_percent >= stop_loss_percent
            
        except Exception as e:
            self.logger.error(f"Error checking stop loss: {e}")
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
                entry_time = datetime.fromisoformat(entry_time)
            
            position_age = datetime.now() - entry_time
            max_hold_time = timedelta(seconds=self.config.get('trading', {}).get('position_hold_time', 3600))
            
            return position_age > max_hold_time
            
        except Exception as e:
            self.logger.error(f"Error checking time exit: {e}")
            return False
    
    def calculate_position_size(self, symbol: str, account_balance: float, 
                              risk_percent: float = 1.0) -> float:
        """Calculate appropriate position size based on risk management"""
        try:
            base_lot_size = self.config.get('trading', {}).get('base_lot_size', 0.1)
            multiplier = self.risk_limits.get('position_size_multiplier', 1.5)
            
            # Calculate risk amount
            risk_amount = account_balance * (risk_percent / 100)
            
            # Calculate position size based on risk
            # This is a simplified calculation - in practice, you'd need
            # to consider pip value, stop loss distance, etc.
            position_size = (risk_amount / 1000) * base_lot_size * multiplier
            
            # Apply minimum and maximum limits
            min_size = 0.01
            max_size = 10.0
            
            return max(min_size, min(position_size, max_size))
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.1  # Default fallback
    
    def check_daily_limits(self, current_pnl: float) -> bool:
        """Check if daily limits have been exceeded"""
        try:
            max_daily_loss = self.risk_limits.get('max_daily_loss', 1000)
            
            # Update daily PnL
            self.daily_pnl = current_pnl
            
            # Check if daily loss limit exceeded
            if current_pnl <= -max_daily_loss:
                self.logger.warning(f"Daily loss limit exceeded: {current_pnl:.2f}")
                return True
            
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
            # Check daily loss limit
            if self.daily_pnl <= -self.risk_limits.get('max_daily_loss', 1000):
                return True
            
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
