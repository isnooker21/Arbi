"""
ระบบจัดการ Correlation และการกู้คืนตำแหน่งแบบ Active Recovery Engine
================================================================

ไฟล์นี้ทำหน้าที่:
- เปลี่ยนจาก monitoring เป็น active recovery
- เพิ่ม multi-timeframe correlation analysis
- เพิ่ม hedge ratio optimization
- เพิ่ม portfolio rebalancing logic
- ระบบ Never-Cut-Loss โดยใช้ Correlation Hedge
- การจัดการ Recovery แบบ Real-time

ตัวอย่างการทำงาน:
1. ตรวจพบตำแหน่ง EUR/USD ขาดทุน
2. หาคู่เงินที่มีความสัมพันธ์สูง เช่น GBP/USD
3. คำนวณ hedge ratio ที่เหมาะสม
4. ใช้ AI วิเคราะห์โอกาสการกู้คืน
5. เปิดตำแหน่ง GBP/USD ในทิศทางที่เหมาะสม
6. ติดตามผลการกู้คืนแบบ Real-time
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
        
        # Active Recovery Engine parameters
        self.recovery_mode = 'active'  # active, passive, disabled
        self.hedge_ratio_optimization = True
        self.portfolio_rebalancing = True
        self.multi_timeframe_analysis = True
        
        # Recovery thresholds
        self.recovery_thresholds = {
            'min_correlation': 0.6,      # Minimum correlation for recovery
            'max_correlation': 0.95,     # Maximum correlation (avoid over-hedging)
            'min_loss_threshold': -0.01, # Minimum loss to trigger recovery (-1%)
            'max_recovery_time_hours': 24, # Maximum time to hold recovery position
            'hedge_ratio_range': (0.5, 2.0)  # Hedge ratio range
        }
        
        # Performance tracking
        self.recovery_metrics = {
            'total_recoveries': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'avg_recovery_time_hours': 0,
            'total_recovered_amount': 0.0
        }
        
        # Multi-timeframe correlation cache
        self.correlation_cache = {
            'h1': {},
            'h4': {},
            'd1': {}
        }
        
        # Portfolio rebalancing parameters
        self.portfolio_balance_threshold = 0.1  # 10% imbalance threshold
        self.rebalancing_frequency_hours = 6    # Rebalance every 6 hours
        
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
        self.logger.info("🔗 Correlation monitoring started")
        
        while self.is_running:
            try:
                # Update correlation matrix every 5 minutes
                self.calculate_correlations()
                
                # Check for recovery opportunities
                self.check_recovery_opportunities()
                
                # Sleep for 5 minutes
                threading.Event().wait(300)
                
            except Exception as e:
                self.logger.error(f"Correlation monitoring error: {e}")
                threading.Event().wait(60)
        
        self.logger.info("🔗 Correlation monitoring stopped")
    
    def find_optimal_hedge_pairs(self, base_pair: str, loss_amount: float) -> List[Dict]:
        """
        หาคู่เงินที่เหมาะสมสำหรับการ hedge ตาม loss amount
        
        Args:
            base_pair: คู่เงินที่ขาดทุน
            loss_amount: จำนวนเงินที่ขาดทุน
            
        Returns:
            List[Dict]: รายการคู่เงินที่เหมาะสมสำหรับการ hedge
        """
        try:
            if base_pair not in self.correlation_matrix:
                self.logger.warning(f"No correlation data for {base_pair}")
                return []
            
            hedge_candidates = []
            
            for hedge_pair, correlation in self.correlation_matrix[base_pair].items():
                # Check correlation strength
                if abs(correlation) < self.recovery_thresholds['min_correlation']:
                    continue
                
                if abs(correlation) > self.recovery_thresholds['max_correlation']:
                    continue
                
                # Calculate hedge ratio
                hedge_ratio = self.calculate_recovery_position_size(base_pair, hedge_pair, loss_amount, correlation)
                
                if hedge_ratio is None:
                    continue
                
                # Check if hedge ratio is within acceptable range
                min_ratio, max_ratio = self.recovery_thresholds['hedge_ratio_range']
                if not (min_ratio <= hedge_ratio <= max_ratio):
                    continue
                
                # Calculate expected recovery potential
                recovery_potential = self._calculate_recovery_potential(base_pair, hedge_pair, correlation, hedge_ratio)
                
                hedge_candidate = {
                    'hedge_pair': hedge_pair,
                    'correlation': correlation,
                    'hedge_ratio': hedge_ratio,
                    'recovery_potential': recovery_potential,
                    'direction': 'opposite' if correlation > 0 else 'same',
                    'priority_score': abs(correlation) * recovery_potential
                }
                
                hedge_candidates.append(hedge_candidate)
            
            # Sort by priority score (highest first)
            hedge_candidates.sort(key=lambda x: x['priority_score'], reverse=True)
            
            self.logger.info(f"Found {len(hedge_candidates)} hedge candidates for {base_pair}")
            return hedge_candidates[:5]  # Return top 5 candidates
            
        except Exception as e:
            self.logger.error(f"Error finding optimal hedge pairs for {base_pair}: {e}")
            return []
    
    def calculate_recovery_position_size(self, base_pair: str, hedge_pair: str, 
                                       loss_amount: float, correlation: float) -> Optional[float]:
        """
        คำนวณขนาดตำแหน่งที่เหมาะสมสำหรับการ recovery
        
        Args:
            base_pair: คู่เงินที่ขาดทุน
            hedge_pair: คู่เงินที่ใช้ในการ hedge
            loss_amount: จำนวนเงินที่ขาดทุน
            correlation: ความสัมพันธ์ระหว่างคู่เงิน
            
        Returns:
            Optional[float]: ขนาดตำแหน่งที่เหมาะสม หรือ None ถ้าไม่เหมาะสม
        """
        try:
            # Get current prices
            base_price = self.broker.get_current_price(base_pair)
            hedge_price = self.broker.get_current_price(hedge_pair)
            
            if base_price is None or hedge_price is None:
                return None
            
            # Calculate base position size
            base_volume = abs(loss_amount) / (base_price * 0.01)  # Rough calculation
            
            # Calculate hedge ratio based on correlation
            if abs(correlation) < 0.1:
                return None  # Too weak correlation
            
            # Hedge ratio calculation
            # Strong correlation = lower hedge ratio needed
            # Weak correlation = higher hedge ratio needed
            hedge_ratio = 1.0 / abs(correlation)
            
            # Adjust for correlation direction
            if correlation < 0:
                hedge_ratio *= 1.2  # Negative correlation needs slightly more hedge
            
            # Calculate final hedge position size
            hedge_volume = base_volume * hedge_ratio
            
            # Apply position size limits
            max_position_size = 10.0  # Maximum 10 lots
            min_position_size = 0.01  # Minimum 0.01 lots
            
            if hedge_volume > max_position_size:
                hedge_volume = max_position_size
            elif hedge_volume < min_position_size:
                hedge_volume = min_position_size
            
            return hedge_volume
            
        except Exception as e:
            self.logger.error(f"Error calculating recovery position size: {e}")
            return None
    
    def execute_correlation_hedge(self, hedge_opportunity: Dict) -> bool:
        """
        เปิดตำแหน่ง correlation hedge
        
        Args:
            hedge_opportunity: ข้อมูลโอกาสการ hedge
            
        Returns:
            bool: True ถ้าสำเร็จ, False ถ้าล้มเหลว
        """
        try:
            base_pair = hedge_opportunity['base_pair']
            hedge_pair = hedge_opportunity['hedge_pair']
            hedge_ratio = hedge_opportunity['hedge_ratio']
            direction = hedge_opportunity['direction']
            
            # Determine order direction
            if direction == 'opposite':
                # If positive correlation, trade opposite direction
                order_type = 'SELL' if hedge_opportunity['correlation'] > 0 else 'BUY'
            else:
                # If negative correlation, trade same direction
                order_type = 'BUY' if hedge_opportunity['correlation'] < 0 else 'SELL'
            
            # Place hedge order
            order = self.broker.place_order(hedge_pair, order_type, hedge_ratio)
            
            if order:
                # Store recovery position
                recovery_id = f"{base_pair}_{hedge_pair}_{datetime.now().timestamp()}"
                self.recovery_positions[recovery_id] = {
                    'base_pair': base_pair,
                    'hedge_pair': hedge_pair,
                    'order': order,
                    'hedge_ratio': hedge_ratio,
                    'correlation': hedge_opportunity['correlation'],
                    'direction': direction,
                    'entry_time': datetime.now(),
                    'recovery_potential': hedge_opportunity['recovery_potential'],
                    'status': 'active',
                    'recovery_type': 'correlation_hedge'
                }
                
                self.logger.info(f"✅ Correlation hedge executed: {hedge_pair} {order_type} "
                               f"{hedge_ratio:.3f} (correlation: {hedge_opportunity['correlation']:.3f})")
                
                # Update metrics
                self.recovery_metrics['total_recoveries'] += 1
                
                return True
            else:
                self.logger.error(f"Failed to place hedge order for {hedge_pair}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing correlation hedge: {e}")
            return False
    
    def monitor_recovery_progress(self):
        """
        ติดตามผลการกู้คืนแบบ Real-time
        """
        try:
            current_time = datetime.now()
            
            for recovery_id, recovery_data in self.recovery_positions.items():
                if recovery_data['status'] != 'active':
                    continue
                
                # Check if recovery has exceeded maximum time
                entry_time = recovery_data['entry_time']
                hours_elapsed = (current_time - entry_time).total_seconds() / 3600
                
                if hours_elapsed > self.recovery_thresholds['max_recovery_time_hours']:
                    self.logger.warning(f"Recovery {recovery_id} exceeded maximum time, closing...")
                    self.close_recovery_position(recovery_id, "timeout")
                    continue
                
                # Check recovery progress
                progress = self._calculate_recovery_progress(recovery_data)
                
                if progress['should_close']:
                    self.logger.info(f"Recovery {recovery_id} completed successfully, closing...")
                    self.close_recovery_position(recovery_id, "success")
                    
                    # Update metrics
                    self.recovery_metrics['successful_recoveries'] += 1
                    self.recovery_metrics['total_recovered_amount'] += progress['recovered_amount']
                    
                elif progress['should_adjust']:
                    self.logger.info(f"Recovery {recovery_id} needs adjustment...")
                    self._adjust_recovery_position(recovery_data, progress)
                
        except Exception as e:
            self.logger.error(f"Error monitoring recovery progress: {e}")
    
    def _calculate_recovery_potential(self, base_pair: str, hedge_pair: str, 
                                    correlation: float, hedge_ratio: float) -> float:
        """
        คำนวณศักยภาพการกู้คืน
        
        Args:
            base_pair: คู่เงินที่ขาดทุน
            hedge_pair: คู่เงินที่ใช้ในการ hedge
            correlation: ความสัมพันธ์ระหว่างคู่เงิน
            hedge_ratio: อัตราส่วนการ hedge
            
        Returns:
            float: ศักยภาพการกู้คืน (0-1)
        """
        try:
            # Base potential from correlation strength
            correlation_potential = abs(correlation)
            
            # Adjust for hedge ratio efficiency
            optimal_ratio = 1.0 / abs(correlation) if abs(correlation) > 0.1 else 1.0
            ratio_efficiency = 1.0 - abs(hedge_ratio - optimal_ratio) / optimal_ratio
            ratio_efficiency = max(0, ratio_efficiency)  # Ensure non-negative
            
            # Calculate final potential
            recovery_potential = correlation_potential * ratio_efficiency
            
            return min(recovery_potential, 1.0)  # Cap at 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating recovery potential: {e}")
            return 0.0
    
    def _calculate_recovery_progress(self, recovery_data: Dict) -> Dict:
        """
        คำนวณความคืบหน้าการกู้คืน
        
        Args:
            recovery_data: ข้อมูลการกู้คืน
            
        Returns:
            Dict: ข้อมูลความคืบหน้า
        """
        try:
            base_pair = recovery_data['base_pair']
            hedge_pair = recovery_data['hedge_pair']
            
            # Get current PnL for both pairs
            base_pnl = self._get_position_pnl(base_pair)
            hedge_pnl = self._get_position_pnl(hedge_pair)
            
            if base_pnl is None or hedge_pnl is None:
                return {'should_close': False, 'should_adjust': False, 'recovered_amount': 0.0}
            
            # Calculate total PnL
            total_pnl = base_pnl + hedge_pnl
            
            # Determine if recovery is complete
            should_close = total_pnl >= 0  # Break even or profit
            
            # Determine if adjustment is needed
            should_adjust = False
            if not should_close:
                # If still losing but hedge is working, might need adjustment
                if hedge_pnl > 0 and abs(hedge_pnl) > abs(base_pnl) * 0.5:
                    should_adjust = True
            
            return {
                'should_close': should_close,
                'should_adjust': should_adjust,
                'recovered_amount': max(0, total_pnl),
                'base_pnl': base_pnl,
                'hedge_pnl': hedge_pnl,
                'total_pnl': total_pnl
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating recovery progress: {e}")
            return {'should_close': False, 'should_adjust': False, 'recovered_amount': 0.0}
    
    def _get_position_pnl(self, pair: str) -> Optional[float]:
        """Get current PnL for a specific pair"""
        try:
            # This would typically get PnL from broker
            # For now, return a mock value
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Error getting position PnL for {pair}: {e}")
            return None
    
    def _adjust_recovery_position(self, recovery_data: Dict, progress: Dict):
        """
        ปรับแต่งตำแหน่งการกู้คืน
        
        Args:
            recovery_data: ข้อมูลการกู้คืน
            progress: ข้อมูลความคืบหน้า
        """
        try:
            # This would implement position adjustment logic
            # For now, just log the adjustment
            self.logger.info(f"Adjusting recovery position: {recovery_data['base_pair']} -> {recovery_data['hedge_pair']}")
            
        except Exception as e:
            self.logger.error(f"Error adjusting recovery position: {e}")
    
    def calculate_correlations(self, lookback_days: int = 30, timeframes: List[str] = ['H1', 'H4', 'D1']):
        """
        คำนวณ correlation matrix แบบขยายด้วย multiple timeframes และ weighted correlation
        
        Parameters:
        - lookback_days: จำนวนวันที่ใช้ในการคำนวณ (default: 30 วัน)
        - timeframes: รายการ timeframes ที่ใช้ ['H1', 'H4', 'D1']
        """
        try:
            all_pairs = self.broker.get_available_pairs()
            
            if not all_pairs:
                self.logger.warning("No pairs available for correlation calculation")
                return {}
            
            # Filter only Major and Minor pairs
            major_minor_currencies = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD']
            pairs = []
            
            for pair in all_pairs:
                # Check if pair contains only major/minor currencies
                if len(pair) == 6:  # Standard pair format like EURUSD
                    currency1 = pair[:3]
                    currency2 = pair[3:]
                    if currency1 in major_minor_currencies and currency2 in major_minor_currencies:
                        pairs.append(pair)
            
            self.logger.info(f"Filtered {len(pairs)} Major/Minor pairs for correlation analysis")
            
            correlations = {}
            
            for pair1 in pairs:
                correlations[pair1] = {}
                
                for pair2 in pairs:
                    if pair1 != pair2:
                        # คำนวณ correlation สำหรับแต่ละ timeframe
                        correlation_scores = []
                        weights = []
                        
                        for tf in timeframes:
                            # คำนวณจำนวนชั่วโมงสำหรับแต่ละ timeframe
                            hours = lookback_days * 24 if tf == 'H1' else (lookback_days * 6 if tf == 'H4' else lookback_days)
                            
                            data1 = self.broker.get_historical_data(pair1, tf, hours)
                            data2 = self.broker.get_historical_data(pair2, tf, hours)
                            
                            if self._validate_correlation_data(data1, data2):
                                # คำนวณ weighted correlation สำหรับ timeframe นี้
                                correlation = self._calculate_weighted_correlation(data1, data2)
                                correlation_scores.append(correlation)
                                
                                # กำหนด weight: H1=0.5, H4=0.3, D1=0.2
                                weight = 0.5 if tf == 'H1' else (0.3 if tf == 'H4' else 0.2)
                                weights.append(weight)
                        
                        # คำนวณ weighted average correlation
                        if correlation_scores:
                            final_correlation = sum(c*w for c, w in zip(correlation_scores, weights)) / sum(weights)
                            correlations[pair1][pair2] = final_correlation
                        else:
                            correlations[pair1][pair2] = 0.0
            
            self.correlation_matrix = correlations
            self.logger.info(f"Updated enhanced correlation matrix for {len(pairs)} pairs using {lookback_days} days")
            return correlations
            
        except Exception as e:
            self.logger.error(f"Error calculating enhanced correlations: {e}")
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
    
    def _validate_correlation_data(self, data1: pd.DataFrame, data2: pd.DataFrame) -> bool:
        """
        ตรวจสอบความถูกต้องของข้อมูลสำหรับการคำนวณ correlation
        
        Parameters:
        - data1, data2: ข้อมูล DataFrame
        
        Returns:
        - True ถ้าข้อมูลถูกต้อง, False ถ้าไม่ถูกต้อง
        """
        try:
            if data1 is None or data2 is None:
                return False
            
            if len(data1) < 10 or len(data2) < 10:
                return False
            
            if len(data1) != len(data2):
                return False
            
            # ตรวจสอบข้อมูลที่ไม่มีค่า
            if data1['close'].isna().any() or data2['close'].isna().any():
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating correlation data: {e}")
            return False
    
    def _calculate_weighted_correlation(self, data1: pd.DataFrame, data2: pd.DataFrame, 
                                      decay_factor: float = 0.1) -> float:
        """
        คำนวณ weighted correlation โดยให้ความสำคัญกับข้อมูลล่าสุดมากขึ้น
        
        Parameters:
        - data1, data2: ข้อมูล DataFrame
        - decay_factor: ปัจจัยการลดลง (ยิ่งมากยิ่งให้ความสำคัญกับข้อมูลล่าสุด)
        
        Returns:
        - Weighted correlation coefficient
        """
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
            
            # Create weights (ข้อมูลล่าสุดมี weight สูงกว่า)
            n = len(aligned_returns)
            weights = np.exp(-decay_factor * np.arange(n-1, -1, -1))
            weights = weights / weights.sum()  # Normalize weights
            
            # Calculate weighted correlation
            data1_array = aligned_returns['close_1'].values
            data2_array = aligned_returns['close_2'].values
            
            # Weighted covariance
            mean1 = np.average(data1_array, weights=weights)
            mean2 = np.average(data2_array, weights=weights)
            
            cov = np.average((data1_array - mean1) * (data2_array - mean2), weights=weights)
            var1 = np.average((data1_array - mean1) ** 2, weights=weights)
            var2 = np.average((data2_array - mean2) ** 2, weights=weights)
            
            if var1 == 0 or var2 == 0:
                return 0.0
            
            correlation = cov / np.sqrt(var1 * var2)
            
            return correlation if not np.isnan(correlation) else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating weighted correlation: {e}")
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
        """Check for recovery opportunities using Active Recovery Engine"""
        try:
            if self.recovery_mode != 'active':
                return
            
            # Get stuck positions (losing positions)
            stuck_positions = self.broker.get_stuck_positions()
            
            if not stuck_positions:
                return
            
            self.logger.info(f"🔍 Checking {len(stuck_positions)} stuck positions for recovery opportunities...")
            
            for position in stuck_positions:
                pair = position['symbol']
                current_pnl = position.get('unrealized_pnl', 0)
                
                # Only look for recovery if position is losing
                if current_pnl >= self.recovery_thresholds['min_loss_threshold']:
                    continue
                
                self.logger.info(f"🔍 Analyzing recovery for {pair} (PnL: {current_pnl:.2f})")
                
                # Find optimal hedge pairs
                hedge_candidates = self.find_optimal_hedge_pairs(pair, current_pnl)
                
                if not hedge_candidates:
                    self.logger.warning(f"No hedge candidates found for {pair}")
                    continue
                
                # Evaluate each hedge candidate
                for hedge_candidate in hedge_candidates:
                    # Create recovery opportunity
                    opportunity = {
                        'base_pair': pair,
                        'hedge_pair': hedge_candidate['hedge_pair'],
                        'correlation': hedge_candidate['correlation'],
                        'hedge_ratio': hedge_candidate['hedge_ratio'],
                        'recovery_potential': hedge_candidate['recovery_potential'],
                        'direction': hedge_candidate['direction'],
                        'base_pnl': current_pnl,
                        'base_volume': position.get('volume', 0),
                        'timestamp': datetime.now()
                    }
                    
                    # AI evaluation for recovery
                    ai_decision = self.ai.evaluate_recovery_opportunity(opportunity)
                    
                    if ai_decision.should_act and ai_decision.confidence > 0.6:
                        self.logger.info(f"🎯 ACTIVE RECOVERY OPPORTUNITY: {pair} -> {hedge_candidate['hedge_pair']}, "
                                       f"Correlation: {hedge_candidate['correlation']:.3f}, "
                                       f"Potential: {hedge_candidate['recovery_potential']:.3f}, "
                                       f"Confidence: {ai_decision.confidence:.2f}")
                        
                        # Execute correlation hedge
                        success = self.execute_correlation_hedge(opportunity)
                        
                        if success:
                            self.logger.info(f"✅ Recovery initiated for {pair}")
                            break  # Move to next stuck position
                        else:
                            self.logger.warning(f"❌ Failed to execute recovery for {pair}")
                    else:
                        self.logger.debug(f"🔍 Recovery opportunity below threshold: {pair} -> {hedge_candidate['hedge_pair']}, "
                                        f"Confidence: {ai_decision.confidence:.2f}")
            
            # Monitor existing recovery progress
            self.monitor_recovery_progress()
                    
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
            'correlation_pairs_tracked': len(self.correlation_matrix),
            'recovery_metrics': self.recovery_metrics,
            'recovery_mode': self.recovery_mode
        }
    
    def get_active_recovery_engine_status(self) -> Dict:
        """Get status of Active Recovery Engine"""
        try:
            return {
                'recovery_mode': self.recovery_mode,
                'hedge_ratio_optimization': self.hedge_ratio_optimization,
                'portfolio_rebalancing': self.portfolio_rebalancing,
                'multi_timeframe_analysis': self.multi_timeframe_analysis,
                'recovery_thresholds': self.recovery_thresholds,
                'recovery_metrics': self.recovery_metrics,
                'active_recoveries': len([r for r in self.recovery_positions.values() if r['status'] == 'active']),
                'total_recovery_positions': len(self.recovery_positions)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting recovery engine status: {e}")
            return {}
    
    def update_recovery_parameters(self, new_params: Dict):
        """Update recovery parameters dynamically"""
        try:
            if 'recovery_mode' in new_params:
                self.recovery_mode = new_params['recovery_mode']
            
            if 'recovery_thresholds' in new_params:
                self.recovery_thresholds.update(new_params['recovery_thresholds'])
            
            if 'hedge_ratio_optimization' in new_params:
                self.hedge_ratio_optimization = new_params['hedge_ratio_optimization']
            
            if 'portfolio_rebalancing' in new_params:
                self.portfolio_rebalancing = new_params['portfolio_rebalancing']
            
            if 'multi_timeframe_analysis' in new_params:
                self.multi_timeframe_analysis = new_params['multi_timeframe_analysis']
            
            self.logger.info(f"Recovery parameters updated: {new_params}")
            
        except Exception as e:
            self.logger.error(f"Error updating recovery parameters: {e}")
    
    def perform_portfolio_rebalancing(self):
        """Perform portfolio rebalancing if needed"""
        try:
            if not self.portfolio_rebalancing:
                return
            
            # Check if rebalancing is needed
            if not self._should_rebalance_portfolio():
                return
            
            self.logger.info("🔄 Performing portfolio rebalancing...")
            
            # Get current portfolio positions
            current_positions = self.broker.get_current_positions()
            
            if not current_positions:
                return
            
            # Analyze portfolio balance
            balance_analysis = self._analyze_portfolio_balance(current_positions)
            
            if balance_analysis['imbalance_detected']:
                # Execute rebalancing
                rebalancing_actions = self._calculate_rebalancing_actions(balance_analysis)
                
                for action in rebalancing_actions:
                    self._execute_rebalancing_action(action)
                
                self.logger.info(f"✅ Portfolio rebalancing completed: {len(rebalancing_actions)} actions")
            else:
                self.logger.debug("Portfolio is balanced, no rebalancing needed")
                
        except Exception as e:
            self.logger.error(f"Error performing portfolio rebalancing: {e}")
    
    def _should_rebalance_portfolio(self) -> bool:
        """Check if portfolio rebalancing is needed"""
        try:
            # Check time-based rebalancing
            current_time = datetime.now()
            if hasattr(self, 'last_rebalancing_time'):
                hours_since_rebalancing = (current_time - self.last_rebalancing_time).total_seconds() / 3600
                if hours_since_rebalancing < self.rebalancing_frequency_hours:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking rebalancing need: {e}")
            return False
    
    def _analyze_portfolio_balance(self, positions: List[Dict]) -> Dict:
        """Analyze portfolio balance"""
        try:
            total_exposure = 0
            currency_exposure = {}
            
            for position in positions:
                symbol = position['symbol']
                volume = position['volume']
                
                # Extract currencies
                if len(symbol) == 6:
                    base_currency = symbol[:3]
                    quote_currency = symbol[3:]
                    
                    # Add to currency exposure
                    if base_currency not in currency_exposure:
                        currency_exposure[base_currency] = 0
                    if quote_currency not in currency_exposure:
                        currency_exposure[quote_currency] = 0
                    
                    currency_exposure[base_currency] += volume
                    currency_exposure[quote_currency] -= volume
                    
                    total_exposure += abs(volume)
            
            # Calculate imbalance
            max_imbalance = max(abs(exposure) for exposure in currency_exposure.values()) if currency_exposure else 0
            imbalance_ratio = max_imbalance / total_exposure if total_exposure > 0 else 0
            
            imbalance_detected = imbalance_ratio > self.portfolio_balance_threshold
            
            return {
                'imbalance_detected': imbalance_detected,
                'imbalance_ratio': imbalance_ratio,
                'currency_exposure': currency_exposure,
                'total_exposure': total_exposure,
                'max_imbalance': max_imbalance
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing portfolio balance: {e}")
            return {'imbalance_detected': False}
    
    def _calculate_rebalancing_actions(self, balance_analysis: Dict) -> List[Dict]:
        """Calculate rebalancing actions needed"""
        try:
            actions = []
            currency_exposure = balance_analysis['currency_exposure']
            
            # Find currencies with excessive exposure
            for currency, exposure in currency_exposure.items():
                if abs(exposure) > balance_analysis['total_exposure'] * self.portfolio_balance_threshold:
                    # Create rebalancing action
                    action = {
                        'currency': currency,
                        'exposure': exposure,
                        'action_type': 'reduce' if exposure > 0 else 'increase',
                        'target_exposure': 0,  # Target neutral exposure
                        'priority': abs(exposure)  # Higher exposure = higher priority
                    }
                    actions.append(action)
            
            # Sort by priority
            actions.sort(key=lambda x: x['priority'], reverse=True)
            
            return actions
            
        except Exception as e:
            self.logger.error(f"Error calculating rebalancing actions: {e}")
            return []
    
    def _execute_rebalancing_action(self, action: Dict):
        """Execute a rebalancing action"""
        try:
            # This would implement actual rebalancing logic
            # For now, just log the action
            self.logger.info(f"Rebalancing action: {action['currency']} "
                           f"({action['action_type']}, exposure: {action['exposure']:.3f})")
            
            # Update last rebalancing time
            self.last_rebalancing_time = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error executing rebalancing action: {e}")
