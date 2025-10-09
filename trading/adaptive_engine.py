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
from utils.symbol_mapper import SymbolMapper

class AdaptiveEngine:
    """
    ระบบ Adaptive Engine หลัก
    
    รับผิดชอบในการประสานงานระหว่าง Arbitrage Detection
    และ Correlation Recovery แบบ Never-Cut-Loss
    """
    
    def __init__(self, broker_api, arbitrage_detector, correlation_manager, market_analyzer=None):
        """
        เริ่มต้นระบบ Adaptive Engine
        
        Args:
            broker_api: API สำหรับเชื่อมต่อกับโบรกเกอร์
            arbitrage_detector: ระบบตรวจจับ Arbitrage
            correlation_manager: ระบบจัดการ Correlation Recovery
            market_analyzer: ระบบวิเคราะห์ตลาด (DISABLED for simple trading)
        """
        self.broker = broker_api
        self.arbitrage_detector = arbitrage_detector
        self.correlation_manager = correlation_manager
        # self.market_analyzer = market_analyzer  # DISABLED for simple trading system
        
        # 🆕 Symbol Mapper for translating broker symbols to standard format
        self.symbol_mapper = SymbolMapper()
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize symbol mapping first
        self._initialize_symbol_mapping()
        
        # Initialize correlation matrix
        self.correlation_matrix = {}
        self._initialize_correlation_matrix()
        
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
            # Update market regime - DISABLED for simple trading system
            # self._update_market_regime()
                    
                    # Update position sizing parameters
                    self._update_position_sizing()
                    
                    # Monitor portfolio health
                    self._monitor_portfolio_health()
                    
                    # Execute adaptive trading logic
                    self._execute_adaptive_trading()
                    
                    # Check group status for arbitrage detector
                    if hasattr(self.arbitrage_detector, 'check_group_status'):
                        self.arbitrage_detector.check_group_status()
                    
                    # Check recovery chain for correlation manager
                    if hasattr(self.correlation_manager, 'check_recovery_chain'):
                        self.correlation_manager.check_recovery_chain()
                    
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
        """อัปเดต Market Regime และปรับ parameters - DISABLED"""
        try:
            # DISABLED: Market regime detection ไม่ใช้ในระบบ simple trading
            return
            
            # OLD CODE - DISABLED
            # # Get current market regime
            # market_analysis = self.market_analyzer.analyze_market_conditions()
            # 
            # if not market_analysis:
            #     return
            # 
            # current_regime = market_analysis.get('market_regime', 'normal')
            # 
            # # Update arbitrage detector parameters
            # if hasattr(self.arbitrage_detector, 'update_adaptive_parameters'):
            #     regime_params = self.regime_parameters.get(current_regime, self.regime_parameters['normal'])
            #     
            #     adaptive_params = {
            #         'market_regime': current_regime,
            #         'volatility_threshold': regime_params['arbitrage_threshold']
            #     }
            #     
            #     self.arbitrage_detector.update_adaptive_parameters(adaptive_params)
            # 
            # # Update correlation manager parameters
            # if hasattr(self.correlation_manager, 'update_recovery_parameters'):
            #     regime_params = self.regime_parameters.get(current_regime, self.regime_parameters['normal'])
            #     
            #     recovery_params = {
            #         'recovery_mode': 'active',
            #         'recovery_thresholds': {
            #             'min_correlation': 0.6,
            #             'max_correlation': 0.95,
            #             'min_loss_threshold': -0.01
            #         }
            #     }
            #     
            #     self.correlation_manager.update_recovery_parameters(recovery_params)
            # 
            # self.logger.debug(f"Market regime updated: {current_regime}")
            
        except Exception as e:
            self.logger.error(f"Error updating market regime: {e}")
    
    def _update_position_sizing(self):
        """อัปเดต Position Sizing ตามยอดเงินในบัญชี - ใช้ uniform pip value"""
        try:
            # Get account balance real-time
            balance = self.broker.get_account_balance()
            if not balance:
                self.logger.error("❌ Cannot get account balance from MT5 - skipping position sizing update")
                return
            
            # Get account equity for more accurate sizing
            equity = self.broker.get_account_equity()
            if not equity:
                self.logger.error("❌ Cannot get account equity from MT5 - skipping position sizing update")
                return
            
            # Get free margin
            free_margin = self.broker.get_free_margin()
            if not free_margin:
                self.logger.error("❌ Cannot get free margin from MT5 - skipping position sizing update")
                return
            
            # self.logger.info(f"💰 Account Status - Balance: {balance:.2f}, Equity: {equity:.2f}, Free Margin: {free_margin:.2f}")  # DISABLED - too verbose
            
            # Calculate balance multiplier for uniform pip value (reduced for lower risk)
            base_balance = 10000.0
            balance_multiplier = balance / base_balance
            target_pip_value = 5.0 * balance_multiplier  # Reduced from 10.0 to 5.0
            
            # self.logger.info(f"📊 Uniform pip value: Base=${10.0:.2f}, Multiplier={balance_multiplier:.2f}x, Target=${target_pip_value:.2f}")  # DISABLED - too verbose
            
            # Update arbitrage detector with balance information
            if hasattr(self.arbitrage_detector, 'update_adaptive_parameters'):
                self.arbitrage_detector.update_adaptive_parameters({
                    'account_balance': balance,
                    'account_equity': equity,
                    'free_margin': free_margin,
                    'target_pip_value': target_pip_value,
                    'balance_multiplier': balance_multiplier
                })
            
            # Update correlation manager with balance information
            if hasattr(self.correlation_manager, 'update_recovery_parameters'):
                self.correlation_manager.update_recovery_parameters({
                    'account_balance': balance,
                    'account_equity': equity,
                    'free_margin': free_margin,
                    'target_pip_value': target_pip_value,
                    'balance_multiplier': balance_multiplier
                })
            
            # self.logger.info(f"📊 Position sizing updated: Balance=${balance:.2f}, Target Pip Value=${target_pip_value:.2f}")  # DISABLED - too verbose
            
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
            positions = self.broker.get_all_positions()
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
            # ตรวจสอบว่ามีกลุ่ม arbitrage เปิดอยู่หรือไม่
            if hasattr(self.arbitrage_detector, 'active_groups') and len(self.arbitrage_detector.active_groups) > 0:
                self.logger.debug("⏸️ มีกลุ่ม arbitrage เปิดอยู่ - ข้ามการตรวจสอบใหม่")
                return
            
            # ตรวจสอบว่ามีคู่เงินที่ถูกใช้แล้วหรือไม่
            if hasattr(self.arbitrage_detector, 'used_currency_pairs') and len(self.arbitrage_detector.used_currency_pairs) > 0:
                self.logger.debug("⏸️ มีคู่เงินที่ถูกใช้แล้ว - ข้ามการตรวจสอบใหม่")
                return
            
            # Get current market regime - DISABLED for simple trading system
            # market_analysis = self.market_analyzer.analyze_market_conditions()
            # market_analysis = None
            # if not market_analysis:
            #     return
            
            # current_regime = market_analysis.get('market_regime', 'normal')
            current_regime = 'normal'  # Default regime for simple trading
            
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
            
            # ตรวจสอบว่ามีกลุ่ม arbitrage เปิดอยู่หรือไม่
            if hasattr(self.arbitrage_detector, 'active_groups') and len(self.arbitrage_detector.active_groups) > 0:
                self.logger.debug("⏸️ มีกลุ่ม arbitrage เปิดอยู่ - ข้ามการตรวจสอบใหม่")
                return
            
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
            
            # ตรวจสอบว่ามีกลุ่ม arbitrage เปิดอยู่หรือไม่
            if hasattr(self.arbitrage_detector, 'active_groups') and len(self.arbitrage_detector.active_groups) > 0:
                self.logger.debug("⏸️ มีกลุ่ม arbitrage เปิดอยู่ - ข้ามการตรวจสอบใหม่")
                return
            
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
            
            # ตรวจสอบว่ามีกลุ่ม arbitrage เปิดอยู่หรือไม่
            if hasattr(self.arbitrage_detector, 'active_groups') and len(self.arbitrage_detector.active_groups) > 0:
                self.logger.debug("⏸️ มีกลุ่ม arbitrage เปิดอยู่ - ข้ามการตรวจสอบใหม่")
                return
            
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
            
            # ตรวจสอบว่ามีกลุ่ม arbitrage เปิดอยู่หรือไม่
            if hasattr(self.arbitrage_detector, 'active_groups') and len(self.arbitrage_detector.active_groups) > 0:
                self.logger.debug("⏸️ มีกลุ่ม arbitrage เปิดอยู่ - ข้ามการตรวจสอบใหม่")
                return
            
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
                self.logger.debug(f"Arbitrage performance type: {type(arbitrage_performance)}")
            
            correlation_performance = {}
            if hasattr(self.correlation_manager, 'get_correlation_performance'):
                correlation_performance = self.correlation_manager.get_correlation_performance()
                self.logger.debug(f"Correlation performance type: {type(correlation_performance)}")
            
            # Ensure both are dictionaries
            if not isinstance(arbitrage_performance, dict):
                self.logger.warning(f"Arbitrage performance is not dict: {type(arbitrage_performance)}")
                arbitrage_performance = {}
            
            if not isinstance(correlation_performance, dict):
                self.logger.warning(f"Correlation performance is not dict: {type(correlation_performance)}")
                correlation_performance = {}
            
            # Update metrics
            self.performance_metrics['total_trades'] = (
                arbitrage_performance.get('total_triangles', 0) + 
                correlation_performance.get('total_recoveries', 0)
            )
            
            self.performance_metrics['successful_trades'] = (
                arbitrage_performance.get('closed_triangles', 0) + 
                correlation_performance.get('successful_recoveries', 0)
            )
            
            self.performance_metrics['recovery_trades'] = correlation_performance.get('total_recoveries', 0)
            
            # Calculate win rate
            if self.performance_metrics['total_trades'] > 0:
                self.performance_metrics['win_rate'] = (
                    self.performance_metrics['successful_trades'] / self.performance_metrics['total_trades']
                )
            
        except Exception as e:
            import traceback
            self.logger.error(f"Error updating performance metrics: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
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
    
    def get_correlations(self, symbol: str) -> Dict[str, float]:
        """
        Get correlation data for a symbol.
        
        Returns negative correlations for hedging purposes.
        
        Args:
            symbol: Currency pair symbol (e.g., "GBPJPY")
            
        Returns:
            Dict mapping pairs to correlation values
            Example: {'EURAUD': -0.75, 'USDCAD': -0.68, ...}
        """
        try:
            # Check if correlation_manager has correlation data
            if hasattr(self.correlation_manager, 'correlation_matrix'):
                correlation_matrix = self.correlation_manager.correlation_matrix
                
                if symbol in correlation_matrix:
                    self.logger.debug(f"✅ Found correlation data for {symbol} from correlation_manager")
                    return correlation_matrix[symbol]
            
            # Check if we have correlation data in our own matrix
            if symbol in self.correlation_matrix:
                self.logger.debug(f"✅ Found correlation data for {symbol} from adaptive_engine")
                return self.correlation_matrix[symbol]
            
            # Fallback: Calculate correlations on-demand
            self.logger.warning(f"⚠️ No cached correlations for {symbol}, calculating...")
            correlations = self._calculate_on_demand_correlations(symbol)
            
            if correlations:
                self.logger.info(f"✅ Calculated {len(correlations)} correlations for {symbol}")
                # Cache the calculated correlations
                self.correlation_matrix[symbol] = correlations
                return correlations
            
            # Try alternative calculation methods before falling back to defaults
            self.logger.warning(f"⚠️ Standard calculation failed for {symbol}, trying alternative methods...")
            correlations = self._calculate_correlations_alternative(symbol)
            
            if correlations:
                self.logger.info(f"✅ Alternative calculation found {len(correlations)} correlations for {symbol}")
                # Cache the calculated correlations
                self.correlation_matrix[symbol] = correlations
                return correlations
            
            # Last resort: Use default correlations (but log warning)
            self.logger.warning(f"⚠️ All calculation methods failed - using default correlations for {symbol}")
            self.logger.warning(f"⚠️ This means the system cannot calculate real correlations from market data")
            default_correlations = self._get_default_correlations(symbol)
            if default_correlations:
                self.logger.warning(f"⚠️ Using {len(default_correlations)} default correlations as fallback")
            return default_correlations
            
        except Exception as e:
            self.logger.error(f"Error getting correlations for {symbol}: {e}")
            return self._get_default_correlations(symbol)

    def _initialize_symbol_mapping(self):
        """Initialize symbol mapping from broker"""
        try:
            self.logger.info("🔄 Initializing symbol mapping...")
            
            # Get available pairs from broker
            all_pairs = self.broker.get_available_pairs()
            if not all_pairs:
                self.logger.warning("No pairs available from broker for symbol mapping")
                return
            
            # Define required pairs for correlation calculation
            required_pairs = [
                'EURUSD', 'GBPUSD', 'USDJPY', 'EURJPY', 'GBPJPY',
                'AUDUSD', 'NZDUSD', 'USDCAD', 'USDCHF', 'EURGBP',
                'AUDNZD', 'AUDCAD', 'NZDCAD', 'AUDCHF', 'NZDCHF',
                'CADCHF', 'EURCHF', 'GBPCHF', 'EURAUD', 'GBPAUD'
            ]
            
            # Scan and map symbols
            mapping_result = self.symbol_mapper.scan_and_map(all_pairs, required_pairs)
            
            # Show mapping summary
            self.logger.info("\n" + self.symbol_mapper.get_mapping_summary())
            
        except Exception as e:
            self.logger.error(f"Error initializing symbol mapping: {e}")

    def _calculate_on_demand_correlations(self, symbol: str, lookback_days: int = 30) -> Dict[str, float]:
        """
        Calculate correlations on-demand from historical data.
        
        Args:
            symbol: Base symbol
            lookback_days: Days of historical data to use
            
        Returns:
            Dict of {pair: correlation_value}
        """
        try:
            import pandas as pd
            import numpy as np
            
            # Get all available pairs
            all_pairs = self.broker.get_available_pairs()
            if not all_pairs:
                return {}
            
            # Filter major/minor pairs
            major_minor_currencies = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD']
            filtered_pairs = []
            
            self.logger.info(f"📊 Filtering pairs from {len(all_pairs)} total pairs...")
            
            for pair in all_pairs:
                if len(pair) >= 6:  # Support both 6-char and 7-char symbols (like AUDNZDP)
                    currency1 = pair[:3]
                    currency2 = pair[3:6] if len(pair) == 6 else pair[3:6]  # Handle AUDNZDP format
                    if currency1 in major_minor_currencies and currency2 in major_minor_currencies:
                        if pair != symbol:  # Don't correlate with self
                            filtered_pairs.append(pair)
            
            self.logger.info(f"✅ Filtered to {len(filtered_pairs)} major/minor pairs")
            if len(filtered_pairs) == 0:
                self.logger.warning("❌ No major/minor pairs found - this will cause correlation calculation to fail")
                self.logger.warning(f"   Symbol format: {symbol} (length: {len(symbol)})")
                self.logger.warning(f"   Sample pairs: {all_pairs[:5] if all_pairs else 'None'}")
                return {}
            
            # Get historical data for base symbol (convert to real broker symbol)
            real_symbol = self.symbol_mapper.get_real_symbol(symbol)
            self.logger.info(f"📊 Getting historical data for {symbol} → {real_symbol} ({lookback_days} days)")
            base_data = self.broker.get_historical_data(real_symbol, 'H1', lookback_days * 24)
            
            if base_data is None:
                self.logger.warning(f"❌ No historical data returned for {symbol}")
                return {}
            
            if len(base_data) < 10:
                self.logger.warning(f"❌ Insufficient data for {symbol}: only {len(base_data)} bars (need ≥10)")
                return {}
            
            self.logger.info(f"✅ Got {len(base_data)} bars of data for {symbol}")
            
            correlations = {}
            
            # Calculate correlation with each pair
            self.logger.info(f"🔄 Calculating correlations with {len(filtered_pairs[:20])} pairs...")
            for i, pair in enumerate(filtered_pairs[:20]):  # Limit to 20 pairs to save time
                try:
                    # Convert pair to real broker symbol
                    real_pair = self.symbol_mapper.get_real_symbol(pair)
                    self.logger.debug(f"   [{i+1}/20] Getting data for {pair} → {real_pair}")
                    pair_data = self.broker.get_historical_data(real_pair, 'H1', lookback_days * 24)
                    
                    if pair_data is None:
                        self.logger.debug(f"   ❌ No data for {pair}")
                        continue
                    
                    if len(pair_data) < 10:
                        self.logger.debug(f"   ❌ Insufficient data for {pair}: {len(pair_data)} bars")
                        continue
                    
                    # Align data by timestamp
                    merged = pd.merge(
                        base_data[['close']], 
                        pair_data[['close']], 
                        left_index=True, 
                        right_index=True, 
                        suffixes=('_base', '_pair')
                    )
                    
                    if len(merged) < 10:
                        continue
                    
                    # Calculate returns
                    returns_base = merged['close_base'].pct_change().dropna()
                    returns_pair = merged['close_pair'].pct_change().dropna()
                    
                    # Calculate correlation
                    if len(returns_base) > 5 and len(returns_pair) > 5:
                        correlation = returns_base.corr(returns_pair)
                        
                        if not np.isnan(correlation):
                            correlations[pair] = float(correlation)
                            
                            # Log EVERY correlation calculated
                            if correlation < -0.5:
                                self.logger.info(f"   ✅ {symbol} vs {pair} = {correlation:.3f} (STRONG NEGATIVE)")
                            elif correlation < -0.2:
                                self.logger.info(f"   ✅ {symbol} vs {pair} = {correlation:.3f} (WEAK NEGATIVE)")
                            elif correlation > 0.7:
                                self.logger.info(f"   ✅ {symbol} vs {pair} = {correlation:.3f} (STRONG POSITIVE)")
                            else:
                                self.logger.debug(f"   ✅ {symbol} vs {pair} = {correlation:.3f}")
                        else:
                            self.logger.debug(f"   ❌ NaN correlation for {symbol} vs {pair}")
                    else:
                        self.logger.debug(f"   ❌ Insufficient returns data: {len(returns_base)} vs {len(returns_pair)}")
                            
                except Exception as e:
                    self.logger.debug(f"Error calculating correlation for {pair}: {e}")
                    continue
            
            # Log summary
            if correlations:
                positive_count = len([v for v in correlations.values() if v > 0])
                negative_count = len([v for v in correlations.values() if v < 0])
                
                self.logger.info(f"CORRELATION SUMMARY for {symbol}:")
                self.logger.info(f"   Total: {len(correlations)}")
                self.logger.info(f"   Positive: {positive_count}")
                self.logger.info(f"   Negative: {negative_count}")
            
            return correlations
            
        except Exception as e:
            self.logger.error(f"Error in on-demand correlation calculation: {e}")
            return {}

    def _calculate_correlations_alternative(self, symbol: str) -> Dict[str, float]:
        """
        Alternative correlation calculation using tick data when historical data fails.
        
        Args:
            symbol: Base symbol
            
        Returns:
            Dict of {pair: correlation_value}
        """
        try:
            import pandas as pd
            import numpy as np
            
            self.logger.info(f"🔄 Trying alternative correlation calculation for {symbol}")
            
            # Get current tick data for all pairs
            tick_data = self.broker.get_tick_data()
            if not tick_data:
                self.logger.warning("No tick data available for alternative calculation")
                return {}
            
            # Filter major/minor pairs
            major_minor_currencies = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD']
            filtered_pairs = []
            
            for pair in tick_data.keys():
                if len(pair) >= 6:  # Support both 6-char and 7-char symbols
                    currency1 = pair[:3]
                    currency2 = pair[3:6] if len(pair) == 6 else pair[3:6]  # Handle AUDNZDP format
                    if currency1 in major_minor_currencies and currency2 in major_minor_currencies:
                        if pair != symbol and pair in tick_data:
                            filtered_pairs.append(pair)
            
            # Convert symbol to real broker symbol
            real_symbol = self.symbol_mapper.get_real_symbol(symbol)
            if real_symbol not in tick_data:
                self.logger.warning(f"Base symbol {symbol} → {real_symbol} not in tick data")
                return {}
            
            correlations = {}
            base_price = tick_data[real_symbol].get('last', 0)
            
            if base_price <= 0:
                self.logger.warning(f"Invalid base price for {symbol}: {base_price}")
                return {}
            
            # Calculate price-based correlations (simplified)
            for pair in filtered_pairs[:15]:  # Limit to 15 pairs
                try:
                    # Convert pair to real broker symbol
                    real_pair = self.symbol_mapper.get_real_symbol(pair)
                    if real_pair not in tick_data:
                        continue
                    
                    pair_price = tick_data[real_pair].get('last', 0)
                    if pair_price <= 0:
                        continue
                    
                    # Simple price correlation calculation
                    # This is a simplified approach - in reality you'd need more data points
                    price_ratio = pair_price / base_price
                    
                    # Estimate correlation based on currency relationships
                    # This is a heuristic approach when real correlation calculation fails
                    currency1_base = symbol[:3]
                    currency2_base = symbol[3:]
                    currency1_pair = pair[:3]
                    currency2_pair = pair[3:]
                    
                    # Calculate estimated correlation based on currency relationships
                    estimated_correlation = self._estimate_correlation_from_currencies(
                        currency1_base, currency2_base, currency1_pair, currency2_pair
                    )
                    
                    if estimated_correlation is not None:
                        correlations[pair] = estimated_correlation
                        self.logger.info(f"   {symbol} vs {pair} = {estimated_correlation:.3f} (estimated)")
                        
                except Exception as e:
                    self.logger.debug(f"Error calculating alternative correlation for {pair}: {e}")
                    continue
            
            self.logger.info(f"✅ Alternative calculation found {len(correlations)} correlations for {symbol}")
            return correlations
            
        except Exception as e:
            self.logger.error(f"Error in alternative correlation calculation: {e}")
            return {}

    def _estimate_correlation_from_currencies(self, base1: str, base2: str, pair1: str, pair2: str) -> Optional[float]:
        """
        Estimate correlation based on currency relationships.
        
        Args:
            base1, base2: Base currency pair currencies
            pair1, pair2: Target currency pair currencies
            
        Returns:
            Estimated correlation value or None
        """
        try:
            # Currency strength relationships (simplified)
            currency_strength = {
                'USD': 1.0, 'EUR': 0.95, 'GBP': 0.90, 'JPY': 0.85,
                'CHF': 0.80, 'AUD': 0.75, 'CAD': 0.70, 'NZD': 0.65
            }
            
            # Calculate base pair strength
            base_strength = currency_strength.get(base1, 0.5) - currency_strength.get(base2, 0.5)
            
            # Calculate target pair strength
            pair_strength = currency_strength.get(pair1, 0.5) - currency_strength.get(pair2, 0.5)
            
            # Estimate correlation based on strength relationship
            if abs(base_strength - pair_strength) < 0.1:
                return 0.7  # Strong positive correlation
            elif abs(base_strength - pair_strength) > 0.5:
                return -0.6  # Strong negative correlation
            else:
                return 0.2  # Weak positive correlation
                
        except Exception as e:
            self.logger.debug(f"Error estimating correlation: {e}")
            return None

    def _get_default_correlations(self, symbol: str) -> Dict[str, float]:
        """
        Get default negative correlations for common pairs.
        
        These are approximate correlations for hedging purposes.
        """
        default_correlations = {
            'EURUSD': {
                'USDCHF': -0.85, 'USDCAD': -0.72, 'GBPAUD': -0.68,
                'NZDUSD': -0.65, 'AUDCAD': -0.75, 'GBPCHF': -0.80
            },
            'GBPUSD': {
                'USDCHF': -0.80, 'USDCAD': -0.70, 'EURAUD': -0.65,
                'AUDCAD': -0.68, 'NZDCAD': -0.62
            },
            'USDJPY': {
                'EURUSD': -0.75, 'GBPUSD': -0.70, 'AUDUSD': -0.65,
                'NZDUSD': -0.60
            },
            'EURJPY': {
                'GBPAUD': -0.72, 'AUDNZD': -0.65, 'NZDCAD': -0.60,
                'USDCHF': -0.70
            },
            'GBPJPY': {
                'EURAUD': -0.75, 'AUDCAD': -0.68, 'NZDUSD': -0.62,
                'USDCHF': -0.70, 'EURCHF': -0.68
            },
            'AUDJPY': {
                'EURAUD': -0.70, 'GBPAUD': -0.65, 'USDCHF': -0.68
            },
            'USDCAD': {
                'EURUSD': -0.75, 'GBPUSD': -0.70, 'AUDUSD': -0.65
            },
            'USDCHF': {
                'EURUSD': -0.85, 'GBPUSD': -0.80, 'AUDUSD': -0.75
            },
            'AUDUSD': {
                'USDCHF': -0.75, 'USDCAD': -0.70, 'EURCHF': -0.68,
                'GBPCHF': -0.65, 'NZDUSD': -0.72
            },
            'NZDUSD': {
                'USDCHF': -0.70, 'USDCAD': -0.65, 'EURCHF': -0.62,
                'GBPCHF': -0.60, 'AUDUSD': -0.72
            },
            'AUDNZD': {
                'EURUSD': -0.68, 'GBPUSD': -0.65, 'USDJPY': -0.60,
                'EURJPY': -0.65, 'GBPJPY': -0.62
            },
            'AUDNZDP': {
                'EURUSD': -0.68, 'GBPUSD': -0.65, 'USDJPY': -0.60,
                'EURJPY': -0.65, 'GBPJPY': -0.62
            },
            'AUDCAD': {
                'EURUSD': -0.75, 'GBPUSD': -0.68, 'USDCHF': -0.70,
                'EURCHF': -0.65, 'GBPCHF': -0.62
            },
            'NZDCAD': {
                'EURUSD': -0.62, 'GBPUSD': -0.60, 'USDCHF': -0.65,
                'EURCHF': -0.58, 'GBPCHF': -0.55
            },
            'AUDCHF': {
                'EURUSD': -0.68, 'GBPUSD': -0.65, 'USDCHF': -0.70,
                'EURCHF': -0.72, 'GBPCHF': -0.68
            },
            'NZDCHF': {
                'EURUSD': -0.62, 'GBPUSD': -0.60, 'USDCHF': -0.65,
                'EURCHF': -0.58, 'GBPCHF': -0.55
            },
            'CADCHF': {
                'EURUSD': -0.70, 'GBPUSD': -0.68, 'USDCHF': -0.75,
                'EURCHF': -0.72, 'GBPCHF': -0.70
            }
        }
        
        if symbol in default_correlations:
            self.logger.info(f"📊 Using default correlations for {symbol}")
            return default_correlations[symbol]
        
        # If symbol not in defaults, return empty dict
        self.logger.warning(f"⚠️ No default correlations available for {symbol}")
        return {}

    def _initialize_correlation_matrix(self):
        """Initialize correlation matrix on startup"""
        try:
            self.logger.info("🔄 Initializing correlation matrix...")
            
            # Check if correlation_manager has existing data
            if self.correlation_manager and hasattr(self.correlation_manager, 'correlation_matrix'):
                existing_matrix = self.correlation_manager.correlation_matrix
                if existing_matrix:
                    self.correlation_matrix = existing_matrix
                    self.logger.info(f"✅ Loaded {len(self.correlation_matrix)} correlations from correlation_manager")
                    return
            
            # Calculate correlations
            all_pairs = self.broker.get_available_pairs()
            if not all_pairs:
                self.logger.warning("⚠️ No pairs available for correlation calculation")
                return
            
            # Filter major/minor pairs
            major_minor_currencies = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD']
            filtered_pairs = []
            
            for pair in all_pairs:
                if len(pair) == 6:
                    currency1 = pair[:3]
                    currency2 = pair[3:]
                    if currency1 in major_minor_currencies and currency2 in major_minor_currencies:
                        filtered_pairs.append(pair)
            
            self.logger.info(f"🔄 Calculating correlations for {len(filtered_pairs)} pairs...")
            
            # Calculate correlations between all pairs
            for base_pair in filtered_pairs[:15]:  # Limit to avoid long initialization
                try:
                    correlations = self._calculate_on_demand_correlations(base_pair, lookback_days=30)
                    if correlations:
                        self.correlation_matrix[base_pair] = correlations
                except Exception as e:
                    self.logger.debug(f"Error calculating correlations for {base_pair}: {e}")
                    continue
            
            self.logger.info(f"✅ Correlation matrix initialized with {len(self.correlation_matrix)} pairs")
            
        except Exception as e:
            self.logger.error(f"Error initializing correlation matrix: {e}")

    def emergency_stop(self):
        """Emergency stop all trading activities"""
        try:
            self.logger.critical("🚨 EMERGENCY STOP ACTIVATED")
            
            # Stop adaptive trading
            self.stop_adaptive_trading()
            
            # Close all positions
            positions = self.broker.get_all_positions()
            if positions:
                for position in positions:
                    try:
                        self.broker.close_position(position['ticket'])
                    except Exception as e:
                        self.logger.error(f"Error closing position {position['ticket']}: {e}")
            
            self.logger.critical("🚨 Emergency stop completed")
            
        except Exception as e:
            self.logger.error(f"Error during emergency stop: {e}")
