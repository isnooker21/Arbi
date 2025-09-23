"""
ระบบ Adaptive Engine หลักสำหรับการเทรด Forex AI
===============================================

ไฟล์นี้ทำหน้าที่:
- รวม Arbitrage + Correlation ในที่เดียว
- จัดการ Market Regime Detection
- ควบคุม Position Sizing แบบ Dynamic
- Portfolio Risk Management
- ระบบ Never-Cut-Loss โดยใช้ Correlation Recovery

Author: AI Trading System
Version: 2.0 (Adaptive Engine)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import threading
import json

class AdaptiveEngine:
    """
    ระบบ Adaptive Engine หลัก
    
    รับผิดชอบในการประสานงานระหว่าง Arbitrage Detection
    และ Correlation Recovery แบบ Never-Cut-Loss
    """
    
    def __init__(self, broker_api, arbitrage_detector, correlation_manager, market_analyzer):
        """
        เริ่มต้นระบบ Adaptive Engine
        
        Args:
            broker_api: API สำหรับเชื่อมต่อกับโบรกเกอร์
            arbitrage_detector: ระบบตรวจจับ Arbitrage
            correlation_manager: ระบบจัดการ Correlation Recovery
            market_analyzer: ระบบวิเคราะห์ตลาด
        """
        self.broker = broker_api
        self.arbitrage_detector = arbitrage_detector
        self.correlation_manager = correlation_manager
        self.market_analyzer = market_analyzer
        
        self.logger = logging.getLogger(__name__)
        
        # Engine state
        self.is_running = False
        self.engine_mode = 'adaptive'  # adaptive, conservative, aggressive
        self.last_analysis_time = None
        
        # Performance tracking
        self.performance_metrics = {
            'total_trades': 0,
            'successful_trades': 0,
            'recovery_trades': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'win_rate': 0.0
        }
        
        # Position sizing parameters
        self.position_sizing = {
            'base_lot_size': 0.1,
            'max_position_size': 10.0,
            'risk_per_trade': 0.02,  # 2% risk per trade
            'max_portfolio_risk': 0.1,  # 10% max portfolio risk
            'account_tiers': {
                'small': {'min_balance': 5000, 'max_balance': 10000, 'lot_multiplier': 1.0},
                'medium': {'min_balance': 10000, 'max_balance': 50000, 'lot_multiplier': 1.5},
                'large': {'min_balance': 50000, 'max_balance': 100000, 'lot_multiplier': 2.0},
                'premium': {'min_balance': 100000, 'max_balance': float('inf'), 'lot_multiplier': 3.0}
            }
        }
        
        # Market regime parameters
        self.regime_parameters = {
            'volatile': {
                'arbitrage_threshold': 0.002,
                'position_size_multiplier': 0.8,
                'recovery_aggressiveness': 0.6
            },
            'trending': {
                'arbitrage_threshold': 0.0015,
                'position_size_multiplier': 1.2,
                'recovery_aggressiveness': 0.8
            },
            'ranging': {
                'arbitrage_threshold': 0.0008,
                'position_size_multiplier': 1.0,
                'recovery_aggressiveness': 0.7
            },
            'normal': {
                'arbitrage_threshold': 0.001,
                'position_size_multiplier': 1.0,
                'recovery_aggressiveness': 0.7
            }
        }
        
        # Portfolio monitoring
        self.portfolio_monitor = {
            'total_exposure': 0.0,
            'currency_exposure': {},
            'correlation_exposure': {},
            'last_rebalance_time': None
        }
        
        self.logger.info("Adaptive Engine initialized successfully")
    
    def start_adaptive_trading(self):
        """เริ่มต้นระบบ Adaptive Trading"""
        try:
            self.is_running = True
            self.logger.info("🚀 Starting Adaptive Trading Engine...")
            
            # Start main trading loop
            trading_thread = threading.Thread(target=self._adaptive_trading_loop, daemon=True)
            trading_thread.start()
            
            self.logger.info("✅ Adaptive Trading Engine started")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting adaptive trading: {e}")
            return False
    
    def stop_adaptive_trading(self):
        """หยุดระบบ Adaptive Trading"""
        try:
            self.is_running = False
            self.logger.info("🛑 Stopping Adaptive Trading Engine...")
            
            # Wait for trading thread to finish
            # Note: In a real implementation, you'd want to use proper thread synchronization
            
            self.logger.info("✅ Adaptive Trading Engine stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping adaptive trading: {e}")
    
    def _adaptive_trading_loop(self):
        """Main adaptive trading loop"""
        self.logger.info("🔄 Adaptive trading loop started")
        
        try:
            while self.is_running:
                try:
                    # Update market regime
                    self._update_market_regime()
                    
                    # Update position sizing parameters
                    self._update_position_sizing()
                    
                    # Monitor portfolio health
                    self._monitor_portfolio_health()
                    
                    # Execute adaptive trading logic
                    self._execute_adaptive_trading()
                    
                    # Update performance metrics
                    self._update_performance_metrics()
                    
                    # Sleep for 30 seconds between cycles
                    threading.Event().wait(30)
                    
                except Exception as e:
                    self.logger.error(f"Error in adaptive trading loop: {e}")
                    threading.Event().wait(60)  # Wait longer on error
            
            self.logger.info("✅ Adaptive trading loop stopped")
            
        except Exception as e:
            self.logger.error(f"Critical error in adaptive trading loop: {e}")
    
    def _update_market_regime(self):
        """อัปเดต Market Regime และปรับ parameters"""
        try:
            # Get current market regime
            market_analysis = self.market_analyzer.analyze_market_conditions()
            
            if not market_analysis:
                return
            
            current_regime = market_analysis.get('market_regime', 'normal')
            
            # Update arbitrage detector parameters
            if hasattr(self.arbitrage_detector, 'update_adaptive_parameters'):
                regime_params = self.regime_parameters.get(current_regime, self.regime_parameters['normal'])
                
                adaptive_params = {
                    'market_regime': current_regime,
                    'volatility_threshold': regime_params['arbitrage_threshold']
                }
                
                self.arbitrage_detector.update_adaptive_parameters(adaptive_params)
            
            # Update correlation manager parameters
            if hasattr(self.correlation_manager, 'update_recovery_parameters'):
                regime_params = self.regime_parameters.get(current_regime, self.regime_parameters['normal'])
                
                recovery_params = {
                    'recovery_mode': 'active',
                    'recovery_thresholds': {
                        'min_correlation': 0.6,
                        'max_correlation': 0.95,
                        'min_loss_threshold': -0.01
                    }
                }
                
                self.correlation_manager.update_recovery_parameters(recovery_params)
            
            self.logger.debug(f"Market regime updated: {current_regime}")
            
        except Exception as e:
            self.logger.error(f"Error updating market regime: {e}")
    
    def _update_position_sizing(self):
        """อัปเดต Position Sizing ตามยอดเงินในบัญชี"""
        try:
            # Get account balance
            account_info = self.broker.get_account_info()
            if not account_info:
                return
            
            balance = account_info.balance
            
            # Determine account tier
            account_tier = self._determine_account_tier(balance)
            
            # Update position sizing parameters
            tier_params = self.position_sizing['account_tiers'][account_tier]
            
            # Calculate dynamic lot size
            base_lot_size = self.position_sizing['base_lot_size']
            lot_multiplier = tier_params['lot_multiplier']
            dynamic_lot_size = base_lot_size * lot_multiplier
            
            # Update arbitrage detector lot size
            if hasattr(self.arbitrage_detector, 'update_adaptive_parameters'):
                self.arbitrage_detector.update_adaptive_parameters({
                    'position_size': dynamic_lot_size
                })
            
            self.logger.debug(f"Position sizing updated: {account_tier} tier, lot size: {dynamic_lot_size}")
            
        except Exception as e:
            self.logger.error(f"Error updating position sizing: {e}")
    
    def _determine_account_tier(self, balance: float) -> str:
        """กำหนด Account Tier ตามยอดเงิน"""
        for tier, params in self.position_sizing['account_tiers'].items():
            if params['min_balance'] <= balance < params['max_balance']:
                return tier
        return 'small'  # Default tier
    
    def _monitor_portfolio_health(self):
        """ติดตามสุขภาพ Portfolio"""
        try:
            # Get current positions
            positions = self.broker.get_current_positions()
            if not positions:
                return
            
            # Calculate portfolio metrics
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
            
            # Update portfolio monitor
            self.portfolio_monitor['total_exposure'] = total_exposure
            self.portfolio_monitor['currency_exposure'] = currency_exposure
            
            # Check if rebalancing is needed
            if self._should_rebalance_portfolio():
                self._execute_portfolio_rebalancing()
            
        except Exception as e:
            self.logger.error(f"Error monitoring portfolio health: {e}")
    
    def _should_rebalance_portfolio(self) -> bool:
        """ตรวจสอบว่าต้องทำ Portfolio Rebalancing หรือไม่"""
        try:
            # Check time-based rebalancing (every 6 hours)
            current_time = datetime.now()
            last_rebalance = self.portfolio_monitor.get('last_rebalance_time')
            
            if last_rebalance:
                hours_since_rebalance = (current_time - last_rebalance).total_seconds() / 3600
                if hours_since_rebalance < 6:
                    return False
            
            # Check exposure-based rebalancing
            currency_exposure = self.portfolio_monitor.get('currency_exposure', {})
            if not currency_exposure:
                return False
            
            # Check if any currency has excessive exposure
            max_exposure = max(abs(exposure) for exposure in currency_exposure.values())
            total_exposure = self.portfolio_monitor.get('total_exposure', 1)
            
            if max_exposure / total_exposure > 0.3:  # 30% threshold
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking rebalancing need: {e}")
            return False
    
    def _execute_portfolio_rebalancing(self):
        """ดำเนินการ Portfolio Rebalancing"""
        try:
            self.logger.info("🔄 Executing portfolio rebalancing...")
            
            # Use correlation manager's rebalancing functionality
            if hasattr(self.correlation_manager, 'perform_portfolio_rebalancing'):
                self.correlation_manager.perform_portfolio_rebalancing()
            
            # Update last rebalance time
            self.portfolio_monitor['last_rebalance_time'] = datetime.now()
            
            self.logger.info("✅ Portfolio rebalancing completed")
            
        except Exception as e:
            self.logger.error(f"Error executing portfolio rebalancing: {e}")
    
    def _execute_adaptive_trading(self):
        """ดำเนินการ Adaptive Trading Logic"""
        try:
            # Get current market regime
            market_analysis = self.market_analyzer.analyze_market_conditions()
            if not market_analysis:
                return
            
            current_regime = market_analysis.get('market_regime', 'normal')
            
            # Execute trading based on regime
            if current_regime == 'volatile':
                self._execute_volatile_market_trading()
            elif current_regime == 'trending':
                self._execute_trending_market_trading()
            elif current_regime == 'ranging':
                self._execute_ranging_market_trading()
            else:
                self._execute_normal_market_trading()
            
        except Exception as e:
            self.logger.error(f"Error executing adaptive trading: {e}")
    
    def _execute_volatile_market_trading(self):
        """ดำเนินการเทรดในตลาด Volatile"""
        try:
            self.logger.debug("Executing volatile market trading strategy")
            
            # In volatile markets, be more conservative
            # Focus on high-confidence arbitrage opportunities only
            
            # Check for recovery opportunities first
            if hasattr(self.correlation_manager, 'check_recovery_opportunities'):
                self.correlation_manager.check_recovery_opportunities()
            
            # Then check for arbitrage opportunities
            if hasattr(self.arbitrage_detector, 'detect_opportunities'):
                self.arbitrage_detector.detect_opportunities()
            
        except Exception as e:
            self.logger.error(f"Error in volatile market trading: {e}")
    
    def _execute_trending_market_trading(self):
        """ดำเนินการเทรดในตลาด Trending"""
        try:
            self.logger.debug("Executing trending market trading strategy")
            
            # In trending markets, be more aggressive
            # Look for both arbitrage and recovery opportunities
            
            # Check for arbitrage opportunities first
            if hasattr(self.arbitrage_detector, 'detect_opportunities'):
                self.arbitrage_detector.detect_opportunities()
            
            # Then check for recovery opportunities
            if hasattr(self.correlation_manager, 'check_recovery_opportunities'):
                self.correlation_manager.check_recovery_opportunities()
            
        except Exception as e:
            self.logger.error(f"Error in trending market trading: {e}")
    
    def _execute_ranging_market_trading(self):
        """ดำเนินการเทรดในตลาด Ranging"""
        try:
            self.logger.debug("Executing ranging market trading strategy")
            
            # In ranging markets, focus on arbitrage opportunities
            # Recovery opportunities are less reliable in ranging markets
            
            # Check for arbitrage opportunities
            if hasattr(self.arbitrage_detector, 'detect_opportunities'):
                self.arbitrage_detector.detect_opportunities()
            
        except Exception as e:
            self.logger.error(f"Error in ranging market trading: {e}")
    
    def _execute_normal_market_trading(self):
        """ดำเนินการเทรดในตลาด Normal"""
        try:
            self.logger.debug("Executing normal market trading strategy")
            
            # In normal markets, use balanced approach
            # Check for both arbitrage and recovery opportunities
            
            # Check for arbitrage opportunities
            if hasattr(self.arbitrage_detector, 'detect_opportunities'):
                self.arbitrage_detector.detect_opportunities()
            
            # Check for recovery opportunities
            if hasattr(self.correlation_manager, 'check_recovery_opportunities'):
                self.correlation_manager.check_recovery_opportunities()
            
        except Exception as e:
            self.logger.error(f"Error in normal market trading: {e}")
    
    def _update_performance_metrics(self):
        """อัปเดต Performance Metrics"""
        try:
            # Get performance data from components
            arbitrage_performance = {}
            if hasattr(self.arbitrage_detector, 'get_triangle_performance'):
                arbitrage_performance = self.arbitrage_detector.get_triangle_performance()
            
            correlation_performance = {}
            if hasattr(self.correlation_manager, 'get_correlation_performance'):
                correlation_performance = self.correlation_manager.get_correlation_performance()
            
            # Update metrics
            self.performance_metrics['total_trades'] = (
                arbitrage_performance.get('total_triangles', 0) + 
                correlation_performance.get('total_recoveries', 0)
            )
            
            self.performance_metrics['successful_trades'] = (
                arbitrage_performance.get('closed_triangles', 0) + 
                correlation_performance.get('closed_recoveries', 0)
            )
            
            self.performance_metrics['recovery_trades'] = correlation_performance.get('total_recoveries', 0)
            
            # Calculate win rate
            if self.performance_metrics['total_trades'] > 0:
                self.performance_metrics['win_rate'] = (
                    self.performance_metrics['successful_trades'] / self.performance_metrics['total_trades']
                )
            
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
    
    def get_adaptive_engine_status(self) -> Dict:
        """Get status of Adaptive Engine"""
        try:
            return {
                'is_running': self.is_running,
                'engine_mode': self.engine_mode,
                'performance_metrics': self.performance_metrics,
                'position_sizing': self.position_sizing,
                'portfolio_monitor': self.portfolio_monitor,
                'last_analysis_time': self.last_analysis_time
            }
            
        except Exception as e:
            self.logger.error(f"Error getting adaptive engine status: {e}")
            return {}
    
    def update_engine_parameters(self, new_params: Dict):
        """Update engine parameters dynamically"""
        try:
            if 'engine_mode' in new_params:
                self.engine_mode = new_params['engine_mode']
            
            if 'position_sizing' in new_params:
                self.position_sizing.update(new_params['position_sizing'])
            
            if 'regime_parameters' in new_params:
                self.regime_parameters.update(new_params['regime_parameters'])
            
            self.logger.info(f"Engine parameters updated: {new_params}")
            
        except Exception as e:
            self.logger.error(f"Error updating engine parameters: {e}")
    
    def get_portfolio_health(self) -> Dict:
        """Get portfolio health summary"""
        try:
            return {
                'total_exposure': self.portfolio_monitor.get('total_exposure', 0),
                'currency_exposure': self.portfolio_monitor.get('currency_exposure', {}),
                'last_rebalance_time': self.portfolio_monitor.get('last_rebalance_time'),
                'performance_metrics': self.performance_metrics
            }
            
        except Exception as e:
            self.logger.error(f"Error getting portfolio health: {e}")
            return {}
    
    def force_portfolio_rebalancing(self):
        """Force immediate portfolio rebalancing"""
        try:
            self.logger.info("🔄 Forcing portfolio rebalancing...")
            self._execute_portfolio_rebalancing()
            
        except Exception as e:
            self.logger.error(f"Error forcing portfolio rebalancing: {e}")
    
    def emergency_stop(self):
        """Emergency stop all trading activities"""
        try:
            self.logger.critical("🚨 EMERGENCY STOP ACTIVATED")
            
            # Stop adaptive trading
            self.stop_adaptive_trading()
            
            # Close all positions
            positions = self.broker.get_current_positions()
            if positions:
                for position in positions:
                    try:
                        self.broker.close_position(position['ticket'])
                    except Exception as e:
                        self.logger.error(f"Error closing position {position['ticket']}: {e}")
            
            self.logger.critical("🚨 Emergency stop completed")
            
        except Exception as e:
            self.logger.error(f"Error during emergency stop: {e}")
