"""
ระบบจัดการ Correlation และการกู้คืนตำแหน่ง

ไฟล์นี้ทำหน้าที่:
- คำนวณความสัมพันธ์ระหว่างคู่เงิน (Correlation)
- ตรวจจับตำแหน่งที่ติดขาดทุน (Stuck Positions)
- หาคู่เงินที่เกี่ยวข้องเพื่อใช้ในการกู้คืน
- ใช้ AI ในการตัดสินใจกลยุทธ์การกู้คืน
- จัดการ Grid Trading สำหรับการกู้คืน

ตัวอย่างการทำงาน:
1. ตรวจพบตำแหน่ง EUR/USD ขาดทุน
2. หาคู่เงินที่มีความสัมพันธ์สูง เช่น GBP/USD
3. ใช้ AI วิเคราะห์โอกาสการกู้คืน
4. เปิดตำแหน่ง GBP/USD ในทิศทางที่เหมาะสม
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
        
    def start_correlation_monitoring(self):
        """Start correlation monitoring and recovery system"""
        self.is_running = True
        self.logger.info("Starting correlation monitoring...")
        
        # Run in separate thread
        monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        monitoring_thread.start()
    
    def stop_correlation_monitoring(self):
        """Stop correlation monitoring"""
        self.is_running = False
        self.logger.info("Stopping correlation monitoring...")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Update correlation matrix every 5 minutes
                self.calculate_correlations()
                
                # Check for recovery opportunities
                self.check_recovery_opportunities()
                
                # Sleep for 5 minutes
                threading.Event().wait(300)
                
            except Exception as e:
                self.logger.error(f"Error in correlation monitoring loop: {e}")
                threading.Event().wait(60)
    
    def calculate_correlations(self, lookback_hours: int = 24):
        """Calculate correlation matrix for all pairs"""
        try:
            pairs = self.broker.get_available_pairs()
            
            if not pairs:
                self.logger.warning("No pairs available for correlation calculation")
                return {}
            
            correlations = {}
            
            for pair1 in pairs:
                correlations[pair1] = {}
                data1 = self.broker.get_historical_data(pair1, 'H1', lookback_hours)
                
                if data1 is None or len(data1) < 10:
                    continue
                
                for pair2 in pairs:
                    if pair1 != pair2:
                        data2 = self.broker.get_historical_data(pair2, 'H1', lookback_hours)
                        
                        if data2 is None or len(data2) < 10:
                            continue
                        
                        corr = self.calculate_pair_correlation(data1, data2)
                        correlations[pair1][pair2] = corr
            
            self.correlation_matrix = correlations
            self.logger.info(f"Updated correlation matrix for {len(pairs)} pairs")
            return correlations
            
        except Exception as e:
            self.logger.error(f"Error calculating correlations: {e}")
            return {}
    
    def calculate_pair_correlation(self, data1: pd.DataFrame, data2: pd.DataFrame) -> float:
        """Calculate correlation between two pairs"""
        try:
            # Align data by timestamp
            merged = pd.merge(data1[['close']], data2[['close']], 
                            left_index=True, right_index=True, 
                            suffixes=('_1', '_2'))
            
            if len(merged) < 10:
                return 0.0
            
            # Calculate returns
            returns1 = merged['close_1'].pct_change().dropna()
            returns2 = merged['close_2'].pct_change().dropna()
            
            # Align returns
            aligned_returns = pd.merge(returns1, returns2, left_index=True, right_index=True)
            
            if len(aligned_returns) < 5:
                return 0.0
            
            # Calculate correlation
            correlation = aligned_returns['close_1'].corr(aligned_returns['close_2'])
            
            return correlation if not np.isnan(correlation) else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating pair correlation: {e}")
            return 0.0
    
    def find_recovery_opportunities(self, stuck_positions: List[Dict]) -> List[Dict]:
        """Find correlation pairs for recovery"""
        recovery_opportunities = []
        
        try:
            for position in stuck_positions:
                pair = position['symbol']
                current_pnl = position.get('unrealized_pnl', 0)
                
                # Only look for recovery if position is losing
                if current_pnl >= 0:
                    continue
                
                # Find highly correlated pairs
                if pair in self.correlation_matrix:
                    for corr_pair, correlation in self.correlation_matrix[pair].items():
                        if abs(correlation) > 0.6:  # Minimum correlation threshold
                            
                            # Determine suggested direction
                            if correlation > 0:
                                # Positive correlation - opposite direction
                                suggested_direction = 'opposite'
                            else:
                                # Negative correlation - same direction
                                suggested_direction = 'same'
                            
                            opportunity = {
                                'base_pair': pair,
                                'recovery_pair': corr_pair,
                                'correlation': correlation,
                                'suggested_direction': suggested_direction,
                                'base_pnl': current_pnl,
                                'base_volume': position.get('volume', 0),
                                'timestamp': datetime.now()
                            }
                            
                            recovery_opportunities.append(opportunity)
            
            self.logger.info(f"Found {len(recovery_opportunities)} recovery opportunities")
            return recovery_opportunities
            
        except Exception as e:
            self.logger.error(f"Error finding recovery opportunities: {e}")
            return []
    
    def check_recovery_opportunities(self):
        """Check for recovery opportunities and execute if approved by AI"""
        try:
            # Get stuck positions (losing positions older than 1 hour)
            stuck_positions = self.broker.get_stuck_positions()
            
            if not stuck_positions:
                return
            
            # Find recovery opportunities
            recovery_opportunities = self.find_recovery_opportunities(stuck_positions)
            
            for opportunity in recovery_opportunities:
                # AI evaluation for recovery
                ai_decision = self.ai.evaluate_recovery_opportunity(opportunity)
                
                if ai_decision.should_act and ai_decision.confidence > 0.6:
                    self.logger.info(f"Executing recovery for {opportunity['base_pair']} "
                                   f"using {opportunity['recovery_pair']}")
                    self.execute_recovery_strategy(opportunity, ai_decision)
                    
        except Exception as e:
            self.logger.error(f"Error checking recovery opportunities: {e}")
    
    def execute_recovery_strategy(self, opportunity: Dict, ai_decision):
        """Execute correlation-based recovery"""
        try:
            base_pair = opportunity['base_pair']
            recovery_pair = opportunity['recovery_pair']
            direction = opportunity['suggested_direction']
            
            # Calculate position size based on correlation strength
            correlation_strength = abs(opportunity['correlation'])
            base_volume = opportunity['base_volume']
            
            # Scale position size based on correlation
            recovery_volume = base_volume * correlation_strength * ai_decision.position_size_multiplier
            
            # Determine order direction
            if direction == 'opposite':
                # If positive correlation, trade opposite direction
                order_type = 'SELL' if opportunity['correlation'] > 0 else 'BUY'
            else:
                # If negative correlation, trade same direction
                order_type = 'BUY' if opportunity['correlation'] < 0 else 'SELL'
            
            # Place recovery order
            order = self.broker.place_order(recovery_pair, order_type, recovery_volume)
            
            if order:
                # Store recovery position
                recovery_id = f"{base_pair}_{recovery_pair}_{datetime.now().timestamp()}"
                self.recovery_positions[recovery_id] = {
                    'base_pair': base_pair,
                    'recovery_pair': recovery_pair,
                    'order': order,
                    'correlation': opportunity['correlation'],
                    'entry_time': datetime.now(),
                    'ai_decision': ai_decision,
                    'status': 'active'
                }
                
                self.logger.info(f"Recovery order placed: {recovery_pair} {order_type} "
                               f"{recovery_volume} (Correlation: {opportunity['correlation']:.3f})")
                return True
            else:
                self.logger.error(f"Failed to place recovery order for {recovery_pair}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing recovery strategy: {e}")
            return False
    
    def calculate_grid_levels(self, opportunity: Dict, num_levels: int = 5) -> List[Dict]:
        """Calculate grid levels for recovery strategy"""
        try:
            recovery_pair = opportunity['recovery_pair']
            current_price = self.broker.get_current_price(recovery_pair)
            
            if current_price is None:
                return []
            
            # Calculate grid spacing based on volatility
            volatility = self._calculate_pair_volatility(recovery_pair)
            grid_spacing = volatility * 0.5  # 50% of volatility
            
            levels = []
            for i in range(num_levels):
                level_price = current_price + (i + 1) * grid_spacing
                level_price_down = current_price - (i + 1) * grid_spacing
                
                levels.append({
                    'level': i + 1,
                    'price_up': level_price,
                    'price_down': level_price_down,
                    'lot_size': opportunity['base_volume'] * (0.5 ** i),  # Decreasing lot sizes
                    'direction_up': 'BUY',
                    'direction_down': 'SELL'
                })
            
            return levels
            
        except Exception as e:
            self.logger.error(f"Error calculating grid levels: {e}")
            return []
    
    def should_enter_grid_level(self, level: Dict) -> bool:
        """Check if should enter a specific grid level"""
        try:
            # Check if price has reached the level
            current_price = self.broker.get_current_price(level['recovery_pair'])
            
            if current_price is None:
                return False
            
            # Check if price is within 5 pips of the level
            price_tolerance = 0.0005
            
            return (abs(current_price - level['price_up']) < price_tolerance or
                   abs(current_price - level['price_down']) < price_tolerance)
                   
        except Exception as e:
            self.logger.error(f"Error checking grid level entry: {e}")
            return False
    
    def _calculate_pair_volatility(self, pair: str) -> float:
        """Calculate volatility for a specific pair"""
        try:
            data = self.broker.get_historical_data(pair, 'H1', 24)
            
            if data is None or len(data) < 10:
                return 0.001  # Default volatility
            
            returns = data['close'].pct_change().dropna()
            return returns.std()
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility for {pair}: {e}")
            return 0.001
    
    def get_correlation_matrix(self) -> Dict:
        """Get current correlation matrix"""
        return self.correlation_matrix
    
    def get_recovery_positions(self) -> Dict:
        """Get all active recovery positions"""
        return self.recovery_positions
    
    def close_recovery_position(self, recovery_id: str, reason: str = "manual"):
        """Close a specific recovery position"""
        try:
            if recovery_id not in self.recovery_positions:
                return False
            
            recovery_data = self.recovery_positions[recovery_id]
            order = recovery_data['order']
            
            # Close the order
            success = self.broker.close_order(order['order_id'])
            
            if success:
                recovery_data['status'] = 'closed'
                recovery_data['close_time'] = datetime.now()
                recovery_data['close_reason'] = reason
                
                self.logger.info(f"Closed recovery position {recovery_id} - Reason: {reason}")
                return True
            else:
                self.logger.error(f"Failed to close recovery position {recovery_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error closing recovery position {recovery_id}: {e}")
            return False
    
    def get_correlation_performance(self) -> Dict:
        """Get performance statistics for correlation system"""
        total_recoveries = len(self.recovery_positions)
        active_recoveries = sum(1 for r in self.recovery_positions.values() if r['status'] == 'active')
        closed_recoveries = sum(1 for r in self.recovery_positions.values() if r['status'] == 'closed')
        
        return {
            'total_recoveries': total_recoveries,
            'active_recoveries': active_recoveries,
            'closed_recoveries': closed_recoveries,
            'correlation_pairs_tracked': len(self.correlation_matrix)
        }
