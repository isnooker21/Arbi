"""
ระบบจัดการตำแหน่งการเทรด
========================

ไฟล์นี้ทำหน้าที่:
- ติดตามและจัดการตำแหน่งที่เปิดอยู่ทั้งหมด
- ตรวจสอบสถานะกำไร/ขาดทุนของแต่ละตำแหน่ง
- จัดการคำสั่ง Stop Loss และ Take Profit
- ตรวจสอบเงื่อนไขการปิดตำแหน่งอัตโนมัติ
- บันทึกประวัติการเทรดและสถิติ

Author: AI Trading System
Version: 1.0
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
import threading

class PositionManager:
    """
    ระบบจัดการตำแหน่งการเทรดหลัก
    
    รับผิดชอบในการติดตาม จัดการ และควบคุมตำแหน่งการเทรด
    รวมถึงการตรวจสอบความเสี่ยงและผลกำไร
    """
    
    def __init__(self, broker_api, risk_manager):
        """
        เริ่มต้นระบบจัดการตำแหน่ง
        
        Args:
            broker_api: API สำหรับเชื่อมต่อกับโบรกเกอร์
            risk_manager: ระบบจัดการความเสี่ยง
        """
        self.broker = broker_api
        self.risk_manager = risk_manager
        self.positions = {}
        self.position_history = []
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        
    def start_position_monitoring(self):
        """
        เริ่มต้นระบบติดตามตำแหน่ง
        
        เปิดระบบติดตามตำแหน่งการเทรดแบบเรียลไทม์
        ในเธรดแยกเพื่อไม่ให้กระทบการทำงานหลัก
        """
        self.is_running = True
        self.logger.info("Starting position monitoring...")
        
        # Run in separate thread
        monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        monitoring_thread.start()
    
    def stop_position_monitoring(self):
        """
        หยุดระบบติดตามตำแหน่ง
        
        ปิดระบบติดตามตำแหน่งการเทรด
        """
        self.is_running = False
        self.logger.info("Stopping position monitoring...")
    
    def _monitoring_loop(self):
        """
        ลูปหลักสำหรับติดตามตำแหน่ง
        
        ทำงานในเธรดแยกเพื่อ:
        - อัปเดตสถานะตำแหน่งทั้งหมด
        - ตรวจสอบเงื่อนไขความเสี่ยง
        - ตรวจสอบเป้าหมายกำไร/ขาดทุน
        """
        while self.is_running:
            try:
                # Update all positions
                self.update_all_positions()
                
                # Check for risk management triggers
                self.check_risk_triggers()
                
                # Check for profit/loss targets
                self.check_profit_loss_targets()
                
                # Sleep for 1 second
                threading.Event().wait(1)
                
            except Exception as e:
                self.logger.error(f"Error in position monitoring loop: {e}")
                threading.Event().wait(5)
    
    def update_all_positions(self):
        """Update all active positions from broker"""
        try:
            broker_positions = self.broker.get_all_positions()
            
            for position in broker_positions:
                position_id = position['ticket']
                
                # Update existing position or create new one
                if position_id in self.positions:
                    self.positions[position_id].update(position)
                else:
                    self.positions[position_id] = {
                        **position,
                        'entry_time': datetime.now(),
                        'status': 'active',
                        'max_profit': 0,
                        'max_loss': 0,
                        'current_drawdown': 0
                    }
                
                # Update performance metrics
                self._update_position_metrics(position_id)
                
        except Exception as e:
            self.logger.error(f"Error updating positions: {e}")
    
    def _update_position_metrics(self, position_id: str):
        """Update performance metrics for a position"""
        try:
            if position_id not in self.positions:
                return
            
            position = self.positions[position_id]
            current_pnl = position.get('profit', 0)
            
            # Update max profit
            if current_pnl > position['max_profit']:
                position['max_profit'] = current_pnl
            
            # Update max loss
            if current_pnl < position['max_loss']:
                position['max_loss'] = current_pnl
            
            # Calculate current drawdown
            if position['max_profit'] > 0:
                position['current_drawdown'] = (position['max_profit'] - current_pnl) / position['max_profit'] * 100
            else:
                position['current_drawdown'] = 0
                
        except Exception as e:
            self.logger.error(f"Error updating position metrics for {position_id}: {e}")
    
    def check_risk_triggers(self):
        """Check for risk management triggers"""
        try:
            for position_id, position in self.positions.items():
                if position['status'] != 'active':
                    continue
                
                # Check stop loss
                if self.risk_manager.should_trigger_stop_loss(position):
                    self.logger.warning(f"Stop loss triggered for position {position_id}")
                    self.close_position(position_id, "stop_loss")
                
                # Check maximum drawdown
                elif self.risk_manager.should_trigger_max_drawdown(position):
                    self.logger.warning(f"Max drawdown triggered for position {position_id}")
                    self.close_position(position_id, "max_drawdown")
                
                # Check time-based exit
                elif self.risk_manager.should_trigger_time_exit(position):
                    self.logger.info(f"Time-based exit triggered for position {position_id}")
                    self.close_position(position_id, "time_exit")
                    
        except Exception as e:
            self.logger.error(f"Error checking risk triggers: {e}")
    
    def check_profit_loss_targets(self):
        """Check for profit/loss targets"""
        try:
            for position_id, position in self.positions.items():
                if position['status'] != 'active':
                    continue
                
                current_pnl = position.get('profit', 0)
                
                # Check take profit
                if current_pnl > 0 and self.risk_manager.should_trigger_take_profit(position):
                    self.logger.info(f"Take profit triggered for position {position_id}")
                    self.close_position(position_id, "take_profit")
                
                # Check trailing stop
                elif self.risk_manager.should_trigger_trailing_stop(position):
                    self.logger.info(f"Trailing stop triggered for position {position_id}")
                    self.close_position(position_id, "trailing_stop")
                    
        except Exception as e:
            self.logger.error(f"Error checking profit/loss targets: {e}")
    
    def close_position(self, position_id: str, reason: str = "manual") -> bool:
        """Close a specific position"""
        try:
            if position_id not in self.positions:
                self.logger.warning(f"Position {position_id} not found")
                return False
            
            position = self.positions[position_id]
            
            # Close position with broker
            success = self.broker.close_position(position_id)
            
            if success:
                # Update position status
                position['status'] = 'closed'
                position['close_time'] = datetime.now()
                position['close_reason'] = reason
                position['final_pnl'] = position.get('profit', 0)
                
                # Move to history
                self.position_history.append(position.copy())
                
                # Remove from active positions
                del self.positions[position_id]
                
                self.logger.info(f"Closed position {position_id} - Reason: {reason}, "
                               f"Final PnL: {position['final_pnl']:.2f}")
                return True
            else:
                self.logger.error(f"Failed to close position {position_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error closing position {position_id}: {e}")
            return False
    
    def close_all_positions(self, reason: str = "manual") -> int:
        """Close all active positions"""
        closed_count = 0
        
        try:
            position_ids = list(self.positions.keys())
            
            for position_id in position_ids:
                if self.close_position(position_id, reason):
                    closed_count += 1
            
            self.logger.info(f"Closed {closed_count} positions - Reason: {reason}")
            return closed_count
            
        except Exception as e:
            self.logger.error(f"Error closing all positions: {e}")
            return closed_count
    
    def get_position_summary(self) -> Dict:
        """Get summary of all positions"""
        try:
            active_positions = [p for p in self.positions.values() if p['status'] == 'active']
            closed_positions = self.position_history
            
            total_pnl = sum(p.get('profit', 0) for p in active_positions)
            total_realized_pnl = sum(p.get('final_pnl', 0) for p in closed_positions)
            
            return {
                'active_positions': len(active_positions),
                'closed_positions': len(closed_positions),
                'total_unrealized_pnl': total_pnl,
                'total_realized_pnl': total_realized_pnl,
                'total_pnl': total_pnl + total_realized_pnl,
                'positions': {
                    'active': active_positions,
                    'closed': closed_positions[-10:]  # Last 10 closed positions
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting position summary: {e}")
            return {}
    
    def get_position_performance(self) -> Dict:
        """Get performance statistics"""
        try:
            closed_positions = self.position_history
            
            if not closed_positions:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'average_win': 0,
                    'average_loss': 0,
                    'profit_factor': 0,
                    'max_drawdown': 0
                }
            
            # Calculate basic statistics
            total_trades = len(closed_positions)
            winning_trades = [p for p in closed_positions if p.get('final_pnl', 0) > 0]
            losing_trades = [p for p in closed_positions if p.get('final_pnl', 0) < 0]
            
            win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
            
            # Calculate average win/loss
            average_win = np.mean([p['final_pnl'] for p in winning_trades]) if winning_trades else 0
            average_loss = np.mean([p['final_pnl'] for p in losing_trades]) if losing_trades else 0
            
            # Calculate profit factor
            total_wins = sum(p['final_pnl'] for p in winning_trades)
            total_losses = abs(sum(p['final_pnl'] for p in losing_trades))
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
            
            # Calculate maximum drawdown
            cumulative_pnl = np.cumsum([p['final_pnl'] for p in closed_positions])
            running_max = np.maximum.accumulate(cumulative_pnl)
            drawdown = running_max - cumulative_pnl
            max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
            
            return {
                'total_trades': total_trades,
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': win_rate,
                'average_win': average_win,
                'average_loss': average_loss,
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown,
                'total_wins': total_wins,
                'total_losses': total_losses
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating position performance: {e}")
            return {}
    
    def get_positions_by_symbol(self, symbol: str) -> List[Dict]:
        """Get all positions for a specific symbol"""
        try:
            return [p for p in self.positions.values() 
                   if p.get('symbol') == symbol and p['status'] == 'active']
        except Exception as e:
            self.logger.error(f"Error getting positions for symbol {symbol}: {e}")
            return []
    
    def get_stuck_positions(self, min_age_hours: int = 1) -> List[Dict]:
        """Get positions that have been open for too long and are losing"""
        try:
            stuck_positions = []
            cutoff_time = datetime.now() - timedelta(hours=min_age_hours)
            
            for position in self.positions.values():
                if (position['status'] == 'active' and 
                    position.get('entry_time', datetime.now()) < cutoff_time and
                    position.get('profit', 0) < 0):
                    stuck_positions.append(position)
            
            return stuck_positions
            
        except Exception as e:
            self.logger.error(f"Error getting stuck positions: {e}")
            return []
    
    def add_position_comment(self, position_id: str, comment: str):
        """Add a comment to a position"""
        try:
            if position_id in self.positions:
                if 'comments' not in self.positions[position_id]:
                    self.positions[position_id]['comments'] = []
                
                self.positions[position_id]['comments'].append({
                    'timestamp': datetime.now(),
                    'comment': comment
                })
                
                self.logger.info(f"Added comment to position {position_id}: {comment}")
                return True
            else:
                self.logger.warning(f"Position {position_id} not found for comment")
                return False
                
        except Exception as e:
            self.logger.error(f"Error adding comment to position {position_id}: {e}")
            return False
