"""
ระบบตัดสินใจอัตโนมัติสำหรับการเทรด Arbitrage
==============================================

ไฟล์นี้เป็นส่วนหลักของระบบ AI ที่ทำหน้าที่:
- ประเมินโอกาส Arbitrage และการฟื้นตัวของ Correlation
- วิเคราะห์ข้อมูลตลาดและเงื่อนไขต่างๆ
- ใช้ Machine Learning เพื่อปรับปรุงการตัดสินใจ
- กำหนดขนาดและทิศทางของ Position
- บันทึกและติดตามผลการตัดสินใจ

Author: AI Trading System
Version: 1.0
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import json
from .rule_engine import AIDecision

class DecisionEngine:
    """
    ระบบตัดสินใจหลักสำหรับการเทรด Arbitrage
    
    รับผิดชอบในการประเมินโอกาสการเทรดและตัดสินใจว่าจะดำเนินการหรือไม่
    โดยใช้ข้อมูลจาก Rule Engine, Learning Module และ Market Analyzer
    """
    
    def __init__(self, rule_engine, learning_module, market_analyzer):
        """
        เริ่มต้นระบบตัดสินใจ
        
        Args:
            rule_engine: ระบบกฎเกณฑ์สำหรับการประเมิน
            learning_module: ระบบ Machine Learning
            market_analyzer: ระบบวิเคราะห์ตลาด
        """
        self.rule_engine = rule_engine
        self.learning_module = learning_module
        self.market_analyzer = market_analyzer
        self.logger = logging.getLogger(__name__)
        self.decision_history = []
        self.performance_tracker = {}
        
    def evaluate_arbitrage_opportunity(self, opportunity: Dict) -> 'AIDecision':
        """
        ประเมินโอกาส Arbitrage และตัดสินใจ
        
        วิเคราะห์โอกาสการทำ Arbitrage โดยพิจารณาจาก:
        - เงื่อนไขตลาดปัจจุบัน
        - กฎเกณฑ์ที่กำหนดไว้
        - ข้อมูลจาก Machine Learning
        - ขนาดและทิศทางของ Position
        
        Args:
            opportunity: ข้อมูลโอกาส Arbitrage
            
        Returns:
            AIDecision: การตัดสินใจพร้อมเหตุผลและพารามิเตอร์
        """
        try:
            # Get current market conditions
            market_conditions = self.market_analyzer.analyze_market_conditions()
            
            # Prepare context for rule evaluation
            context = self._prepare_arbitrage_context(opportunity, market_conditions)
            
            # Evaluate rules
            decision = self.rule_engine.evaluate_rules(context, 'arbitrage_detection')
            
            # Enhance decision with learning module insights
            if decision.should_act:
                decision = self._enhance_decision_with_learning(decision, opportunity, market_conditions)
            
            # Set position parameters
            self._set_position_parameters(decision, opportunity, market_conditions)
            
            # Record decision
            self._record_decision(decision, opportunity, 'arbitrage')
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Error evaluating arbitrage opportunity: {e}")
            return AIDecision(False, 0.0, f"Error: {str(e)}", [], [], {})
    
    def evaluate_flexible_opportunity(self, opportunity: Dict) -> 'AIDecision':
        """
        ประเมินโอกาส Flexible Trading (Trend, Momentum, Scalping, Grid, etc.)
        
        วิเคราะห์โอกาสการเทรดแบบยืดหยุ่นโดยพิจารณาจาก:
        - ประเภทการเทรด (trend_following, momentum, scalping, grid)
        - เงื่อนไขตลาดปัจจุบัน
        - กฎเกณฑ์ที่กำหนดไว้
        - ข้อมูลจาก Machine Learning
        
        Args:
            opportunity: ข้อมูลโอกาส Flexible Trading
            
        Returns:
            AIDecision: การตัดสินใจพร้อมเหตุผลและพารามิเตอร์
        """
        try:
            # Get current market conditions
            market_conditions = self.market_analyzer.analyze_market_conditions()
            
            # Prepare context for rule evaluation
            context = self._prepare_flexible_context(opportunity, market_conditions)
            
            # Evaluate rules based on trading type
            trading_type = opportunity.get('trading_type', 'unknown')
            decision = self.rule_engine.evaluate_rules(context, 'flexible_trading')
            
            # Enhance decision with learning module insights
            if decision.should_act:
                decision = self._enhance_decision_with_learning(decision, opportunity, market_conditions)
            
            # Set position parameters based on trading type
            self._set_flexible_position_parameters(decision, opportunity, market_conditions)
            
            # Record decision
            self._record_decision(decision, opportunity, f'flexible_{trading_type}')
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Error evaluating flexible opportunity: {e}")
            return AIDecision(False, 0.0, f"Error: {str(e)}", [], [], {})
    
    def evaluate_recovery_opportunity(self, opportunity: Dict) -> 'AIDecision':
        """
        ประเมินโอกาสการฟื้นตัวของ Correlation
        
        วิเคราะห์โอกาสในการทำการเทรดเพื่อฟื้นตัวจากความสัมพันธ์
        ระหว่างคู่เงินที่ผิดปกติ
        
        Args:
            opportunity: ข้อมูลโอกาสการฟื้นตัว
            
        Returns:
            AIDecision: การตัดสินใจพร้อมเหตุผลและพารามิเตอร์
        """
        try:
            # Get current market conditions
            market_conditions = self.market_analyzer.analyze_market_conditions()
            
            # Prepare context for rule evaluation
            context = self._prepare_recovery_context(opportunity, market_conditions)
            
            # Evaluate rules
            decision = self.rule_engine.evaluate_rules(context, 'correlation_recovery')
            
            # Enhance decision with learning module insights
            if decision.should_act:
                decision = self._enhance_decision_with_learning(decision, opportunity, market_conditions)
            
            # Set position parameters
            self._set_recovery_parameters(decision, opportunity, market_conditions)
            
            # Record decision
            self._record_decision(decision, opportunity, 'recovery')
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Error evaluating recovery opportunity: {e}")
            return AIDecision(False, 0.0, f"Error: {str(e)}", [], [], {})
    
    def _prepare_arbitrage_context(self, opportunity: Dict, market_conditions: Dict) -> Dict:
        """
        เตรียมข้อมูลบริบทสำหรับการประเมินกฎเกณฑ์ Arbitrage
        
        รวมข้อมูลจากโอกาส Arbitrage และเงื่อนไขตลาด
        เพื่อใช้ในการประเมินกฎเกณฑ์
        
        Args:
            opportunity: ข้อมูลโอกาส Arbitrage
            market_conditions: เงื่อนไขตลาดปัจจุบัน
            
        Returns:
            Dict: ข้อมูลบริบทที่พร้อมใช้
        """
        try:
            context = {
                'arbitrage_percent': opportunity.get('arbitrage_percent', 0),
                'triangle': opportunity.get('triangle', []),
                'timestamp': opportunity.get('timestamp', datetime.now()),
                'spread_acceptable': opportunity.get('spread_acceptable', False),
                'volatility': opportunity.get('volatility', 0),
                
                # Market conditions
                'overall_trend': market_conditions.get('overall_trend', 'unknown'),
                'volatility_level': market_conditions.get('volatility_level', 'medium'),
                'session_type': market_conditions.get('session_type', 'unknown'),
                'market_sentiment': market_conditions.get('market_sentiment', 'neutral'),
                
                # Multi-timeframe analysis
                'h1_trend': self._extract_trend_from_analysis(opportunity.get('h1', {})),
                'm30_structure': self._extract_structure_from_analysis(opportunity.get('m30', {})),
                'm15_condition': self._extract_condition_from_analysis(opportunity.get('m15', {})),
                'm5_signal': self._extract_signal_from_analysis(opportunity.get('m5', {})),
                'm1_signal': self._extract_signal_from_analysis(opportunity.get('m1', {}))
            }
            
            # Add symbol-specific conditions
            triangle = opportunity.get('triangle', [])
            for i, symbol in enumerate(triangle):
                if symbol in market_conditions.get('conditions', {}):
                    symbol_condition = market_conditions['conditions'][symbol]
                    context[f'{symbol}_trend'] = symbol_condition.get('trend', 'unknown')
                    context[f'{symbol}_volatility'] = symbol_condition.get('volatility', 0)
                    context[f'{symbol}_rsi'] = symbol_condition.get('rsi', 50)
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error preparing arbitrage context: {e}")
            return {}
    
    def _prepare_flexible_context(self, opportunity: Dict, market_conditions: Dict) -> Dict:
        """
        เตรียมข้อมูลบริบทสำหรับการประเมินกฎเกณฑ์ Flexible Trading
        
        รวมข้อมูลจากโอกาสการเทรดแบบยืดหยุ่นและเงื่อนไขตลาด
        เพื่อใช้ในการประเมินกฎเกณฑ์
        
        Args:
            opportunity: ข้อมูลโอกาส Flexible Trading
            market_conditions: เงื่อนไขตลาดปัจจุบัน
            
        Returns:
            Dict: ข้อมูลบริบทที่พร้อมใช้
        """
        try:
            context = {
                'pair': opportunity.get('pair', ''),
                'trading_type': opportunity.get('trading_type', ''),
                'direction': opportunity.get('direction', ''),
                'timestamp': opportunity.get('timestamp', datetime.now()),
                
                # Trading type specific conditions
                'trend_strength': opportunity.get('trend_strength', 0),
                'price_momentum': opportunity.get('price_momentum', 0),
                'momentum': opportunity.get('momentum', 0),
                'rsi': opportunity.get('rsi', 50),
                'volatility': opportunity.get('volatility', 0),
                'price_change': opportunity.get('price_change', 0),
                'spread': opportunity.get('spread', 0),
                'price_range': opportunity.get('price_range', 0),
                
                # Market conditions
                'overall_trend': market_conditions.get('overall_trend', 'unknown'),
                'volatility_level': market_conditions.get('volatility_level', 'medium'),
                'session_type': market_conditions.get('session_type', 'unknown'),
                'market_condition': market_conditions.get('market_condition', 'normal'),
                
                # Current time variables
                'current_time': datetime.now().strftime('%H:%M'),
                'day_of_week': datetime.now().strftime('%A').lower()
            }
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error preparing flexible context: {e}")
            return {}
    
    def _prepare_recovery_context(self, opportunity: Dict, market_conditions: Dict) -> Dict:
        """
        เตรียมข้อมูลบริบทสำหรับการประเมินกฎเกณฑ์การฟื้นตัว
        
        รวมข้อมูลจากโอกาสการฟื้นตัวและเงื่อนไขตลาด
        เพื่อใช้ในการประเมินกฎเกณฑ์
        
        Args:
            opportunity: ข้อมูลโอกาสการฟื้นตัว
            market_conditions: เงื่อนไขตลาดปัจจุบัน
            
        Returns:
            Dict: ข้อมูลบริบทที่พร้อมใช้
        """
        try:
            context = {
                'base_pair': opportunity.get('base_pair', ''),
                'recovery_pair': opportunity.get('recovery_pair', ''),
                'correlation': opportunity.get('correlation', 0),
                'suggested_direction': opportunity.get('suggested_direction', 'unknown'),
                'base_pnl': opportunity.get('base_pnl', 0),
                'base_volume': opportunity.get('base_volume', 0),
                'timestamp': opportunity.get('timestamp', datetime.now()),
                
                # Market conditions
                'overall_trend': market_conditions.get('overall_trend', 'unknown'),
                'volatility_level': market_conditions.get('volatility_level', 'medium'),
                'session_type': market_conditions.get('session_type', 'unknown'),
                'market_sentiment': market_conditions.get('market_sentiment', 'neutral'),
                
                # Position age (if available)
                'position_age': self._calculate_position_age(opportunity)
            }
            
            # Add pair-specific conditions
            base_pair = opportunity.get('base_pair', '')
            recovery_pair = opportunity.get('recovery_pair', '')
            
            if base_pair in market_conditions.get('conditions', {}):
                base_condition = market_conditions['conditions'][base_pair]
                context['base_pair_trend'] = base_condition.get('trend', 'unknown')
                context['base_pair_volatility'] = base_condition.get('volatility', 0)
            
            if recovery_pair in market_conditions.get('conditions', {}):
                recovery_condition = market_conditions['conditions'][recovery_pair]
                context['recovery_pair_trend'] = recovery_condition.get('trend', 'unknown')
                context['recovery_pair_volatility'] = recovery_condition.get('volatility', 0)
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error preparing recovery context: {e}")
            return {}
    
    def _enhance_decision_with_learning(self, decision: 'AIDecision', opportunity: Dict, 
                                      market_conditions: Dict) -> 'AIDecision':
        """
        ปรับปรุงการตัดสินใจด้วยข้อมูลจาก Learning Module
        
        ใช้ Machine Learning เพื่อ:
        - ทำนายความสำเร็จของโอกาส Arbitrage
        - ระบุรูปแบบตลาดที่เกี่ยวข้อง
        - ปรับระดับความมั่นใจในการตัดสินใจ
        
        Args:
            decision: การตัดสินใจเริ่มต้น
            opportunity: ข้อมูลโอกาส
            market_conditions: เงื่อนไขตลาด
            
        Returns:
            AIDecision: การตัดสินใจที่ปรับปรุงแล้ว
        """
        try:
            # Get learning module prediction if available
            if hasattr(self.learning_module, 'predict_arbitrage_success'):
                features = {
                    'arbitrage_percent': opportunity.get('arbitrage_percent', 0),
                    'volatility': market_conditions.get('average_volatility', 0),
                    'spread': opportunity.get('spread', 0),
                    'trend_strength': self._calculate_average_trend_strength(market_conditions),
                    'correlation_strength': opportunity.get('correlation', 0),
                    'hour': datetime.now().hour,
                    'dayofweek': datetime.now().weekday(),
                    'month': datetime.now().month
                }
                
                prediction = self.learning_module.predict_arbitrage_success(features)
                
                if 'success_probability' in prediction:
                    # Adjust confidence based on learning prediction
                    learning_confidence = prediction['success_probability']
                    decision.confidence = (decision.confidence + learning_confidence) / 2
                    
                    # Add learning insight to reasoning
                    decision.reasoning += f" | Learning prediction: {learning_confidence:.2f}"
            
            # Apply market pattern insights
            patterns = self.learning_module.identify_market_patterns(days=7)
            if 'patterns' in patterns and patterns['patterns']:
                # Find matching patterns
                matching_patterns = self._find_matching_patterns(opportunity, patterns['patterns'])
                if matching_patterns:
                    avg_success_rate = np.mean([p['success_rate'] for p in matching_patterns])
                    if avg_success_rate > 0.7:
                        decision.confidence = min(decision.confidence * 1.1, 1.0)
                        decision.reasoning += f" | Pattern match: {avg_success_rate:.2f}"
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Error enhancing decision with learning: {e}")
            return decision
    
    def _set_position_parameters(self, decision: 'AIDecision', opportunity: Dict, 
                               market_conditions: Dict):
        """
        กำหนดพารามิเตอร์ของ Position สำหรับการตัดสินใจ Arbitrage
        
        คำนวณ:
        - ขนาด Position ตามความมั่นใจและความผันผวน
        - ทิศทางสำหรับแต่ละคู่เงินใน Triangle
        - ตัวคูณขนาด Position
        
        Args:
            decision: การตัดสินใจ
            opportunity: ข้อมูลโอกาส Arbitrage
            market_conditions: เงื่อนไขตลาด
        """
        try:
            # Base position size
            base_lot_size = 0.1
            
            # Adjust based on confidence
            confidence_multiplier = decision.confidence
            
            # Adjust based on volatility
            volatility = market_conditions.get('average_volatility', 0.5)
            if volatility > 1.0:  # High volatility
                volatility_multiplier = 0.8
            elif volatility < 0.3:  # Low volatility
                volatility_multiplier = 1.2
            else:
                volatility_multiplier = 1.0
            
            # Adjust based on arbitrage percentage
            arbitrage_percent = opportunity.get('arbitrage_percent', 0)
            if arbitrage_percent > 0.5:  # High arbitrage opportunity
                arbitrage_multiplier = 1.3
            elif arbitrage_percent < 0.2:  # Low arbitrage opportunity
                arbitrage_multiplier = 0.7
            else:
                arbitrage_multiplier = 1.0
            
            # Calculate final position size
            final_lot_size = (base_lot_size * confidence_multiplier * 
                            volatility_multiplier * arbitrage_multiplier)
            
            # Apply limits
            final_lot_size = max(0.01, min(final_lot_size, 1.0))
            
            decision.set_position_size(final_lot_size)
            decision.set_position_size_multiplier(arbitrage_multiplier)
            
            # Set direction for each pair in triangle
            triangle = opportunity.get('triangle', [])
            direction = {}
            for symbol in triangle:
                # Simple direction logic - can be enhanced
                direction[symbol] = 1 if arbitrage_percent > 0 else -1
            
            decision.set_direction(direction)
            
        except Exception as e:
            self.logger.error(f"Error setting position parameters: {e}")
    
    def _set_flexible_position_parameters(self, decision: 'AIDecision', opportunity: Dict, 
                                        market_conditions: Dict):
        """
        กำหนดพารามิเตอร์ของ Position สำหรับการตัดสินใจ Flexible Trading
        
        คำนวณ:
        - ขนาด Position ตามประเภทการเทรดและความมั่นใจ
        - ทิศทางตามสัญญาณการเทรด
        - ตัวคูณขนาด Position
        
        Args:
            decision: การตัดสินใจ
            opportunity: ข้อมูลโอกาส Flexible Trading
            market_conditions: เงื่อนไขตลาด
        """
        try:
            # Base position size
            base_lot_size = 0.1
            
            # Adjust based on confidence
            confidence_multiplier = decision.confidence
            
            # Adjust based on trading type
            trading_type = opportunity.get('trading_type', '')
            type_multiplier = {
                'trend_following': 1.0,
                'momentum': 0.8,
                'scalping': 0.5,
                'grid': 0.6,
                'breakout': 0.9,
                'mean_reversion': 0.7
            }.get(trading_type, 0.8)
            
            # Adjust based on volatility
            volatility = opportunity.get('volatility', 0)
            if volatility > 1.0:  # High volatility
                volatility_multiplier = 0.8
            elif volatility < 0.3:  # Low volatility
                volatility_multiplier = 1.2
            else:
                volatility_multiplier = 1.0
            
            # Calculate final position size
            final_lot_size = (base_lot_size * confidence_multiplier * 
                            type_multiplier * volatility_multiplier)
            
            # Apply limits
            final_lot_size = max(0.01, min(final_lot_size, 1.0))
            
            decision.set_position_size(final_lot_size)
            decision.set_position_size_multiplier(type_multiplier)
            
            # Set direction
            direction = opportunity.get('direction', 'BUY')
            decision.set_direction({'main': direction})
            
        except Exception as e:
            self.logger.error(f"Error setting flexible position parameters: {e}")
    
    def _set_recovery_parameters(self, decision: 'AIDecision', opportunity: Dict, 
                               market_conditions: Dict):
        """
        กำหนดพารามิเตอร์ของ Position สำหรับการตัดสินใจการฟื้นตัว
        
        คำนวณ:
        - ขนาด Position ตามความแข็งแกร่งของ Correlation
        - ทิศทางตามความสัมพันธ์ระหว่างคู่เงิน
        - ตัวคูณขนาด Position
        
        Args:
            decision: การตัดสินใจ
            opportunity: ข้อมูลโอกาสการฟื้นตัว
            market_conditions: เงื่อนไขตลาด
        """
        try:
            # Base position size from base pair
            base_volume = opportunity.get('base_volume', 0.1)
            
            # Adjust based on correlation strength
            correlation = abs(opportunity.get('correlation', 0))
            correlation_multiplier = correlation  # Stronger correlation = larger position
            
            # Adjust based on confidence
            confidence_multiplier = decision.confidence
            
            # Calculate final position size
            final_lot_size = base_volume * correlation_multiplier * confidence_multiplier
            
            # Apply limits
            final_lot_size = max(0.01, min(final_lot_size, 2.0))
            
            decision.set_position_size(final_lot_size)
            decision.set_position_size_multiplier(correlation_multiplier)
            
            # Set direction based on correlation
            recovery_pair = opportunity.get('recovery_pair', '')
            suggested_direction = opportunity.get('suggested_direction', 'same')
            
            direction = {}
            if suggested_direction == 'opposite':
                direction[recovery_pair] = -1
            else:
                direction[recovery_pair] = 1
            
            decision.set_direction(direction)
            
        except Exception as e:
            self.logger.error(f"Error setting recovery parameters: {e}")
    
    def _extract_trend_from_analysis(self, analysis: Dict) -> str:
        """
        สกัดข้อมูลเทรนด์จากการวิเคราะห์ Timeframe
        
        วิเคราะห์ทิศทางของเทรนด์จากข้อมูลการวิเคราะห์
        และส่งคืนเป็น bullish, bearish หรือ sideways
        
        Args:
            analysis: ข้อมูลการวิเคราะห์ Timeframe
            
        Returns:
            str: ทิศทางเทรนด์ (bullish/bearish/sideways/unknown)
        """
        try:
            if analysis.get('status') != 'success':
                return 'unknown'
            
            trends = analysis.get('trend', {})
            if not trends:
                return 'unknown'
            
            # Count trend directions
            trend_values = list(trends.values())
            bullish_count = trend_values.count('bullish')
            bearish_count = trend_values.count('bearish')
            
            if bullish_count > bearish_count:
                return 'bullish'
            elif bearish_count > bullish_count:
                return 'bearish'
            else:
                return 'sideways'
                
        except Exception as e:
            self.logger.error(f"Error extracting trend: {e}")
            return 'unknown'
    
    def _extract_structure_from_analysis(self, analysis: Dict) -> str:
        """
        สกัดข้อมูลโครงสร้างจากการวิเคราะห์ Timeframe
        
        ระบุรูปแบบ Support/Resistance หรือโครงสร้างปกติ
        
        Args:
            analysis: ข้อมูลการวิเคราะห์ Timeframe
            
        Returns:
            str: โครงสร้าง (support/resistance/normal/unknown)
        """
        try:
            if analysis.get('status') != 'success':
                return 'unknown'
            
            structures = analysis.get('structure', {})
            if not structures:
                return 'unknown'
            
            # Look for support/resistance patterns
            structure_values = list(structures.values())
            if 'support' in structure_values:
                return 'support'
            elif 'resistance' in structure_values:
                return 'resistance'
            else:
                return 'normal'
                
        except Exception as e:
            self.logger.error(f"Error extracting structure: {e}")
            return 'unknown'
    
    def _extract_condition_from_analysis(self, analysis: Dict) -> str:
        """
        สกัดข้อมูลสภาพตลาดจากการวิเคราะห์ Timeframe
        
        ระบุระดับความผันผวนของตลาด
        
        Args:
            analysis: ข้อมูลการวิเคราะห์ Timeframe
            
        Returns:
            str: สภาพตลาด (high_volatility/low_volatility/normal/unknown)
        """
        try:
            if analysis.get('status') != 'success':
                return 'unknown'
            
            # Check volatility levels
            volatilities = analysis.get('volatility', {})
            if not volatilities:
                return 'normal'
            
            avg_volatility = np.mean(list(volatilities.values()))
            
            if avg_volatility > 1.0:
                return 'high_volatility'
            elif avg_volatility < 0.3:
                return 'low_volatility'
            else:
                return 'normal'
                
        except Exception as e:
            self.logger.error(f"Error extracting condition: {e}")
            return 'normal'
    
    def _extract_signal_from_analysis(self, analysis: Dict) -> str:
        """
        สกัดความแข็งแกร่งของสัญญาณจากการวิเคราะห์ Timeframe
        
        ประเมินความแข็งแกร่งของสัญญาณโดยพิจารณาจาก:
        - จำนวนเทรนด์ที่แข็งแกร่ง
        - ระดับความผันผวน
        
        Args:
            analysis: ข้อมูลการวิเคราะห์ Timeframe
            
        Returns:
            str: ความแข็งแกร่งสัญญาณ (strong/medium/weak/unknown)
        """
        try:
            if analysis.get('status') != 'success':
                return 'weak'
            
            # Combine trend and volatility for signal strength
            trends = analysis.get('trend', {})
            volatilities = analysis.get('volatility', {})
            
            if not trends or not volatilities:
                return 'weak'
            
            # Count strong trends
            trend_values = list(trends.values())
            strong_trends = trend_values.count('bullish') + trend_values.count('bearish')
            
            # Check volatility
            avg_volatility = np.mean(list(volatilities.values()))
            
            if strong_trends >= 2 and avg_volatility > 0.5:
                return 'strong'
            elif strong_trends >= 1 and avg_volatility > 0.3:
                return 'medium'
            else:
                return 'weak'
                
        except Exception as e:
            self.logger.error(f"Error extracting signal: {e}")
            return 'weak'
    
    def _calculate_position_age(self, opportunity: Dict) -> int:
        """
        คำนวณอายุของ Position เป็นวินาที
        
        ใช้สำหรับการประเมินโอกาสการฟื้นตัว
        
        Args:
            opportunity: ข้อมูลโอกาส
            
        Returns:
            int: อายุของ Position เป็นวินาที
        """
        try:
            timestamp = opportunity.get('timestamp', datetime.now())
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            age = (datetime.now() - timestamp).total_seconds()
            return int(age)
            
        except Exception as e:
            self.logger.error(f"Error calculating position age: {e}")
            return 0
    
    def _calculate_average_trend_strength(self, market_conditions: Dict) -> float:
        """
        คำนวณความแข็งแกร่งของเทรนด์เฉลี่ยของทุกสัญลักษณ์
        
        ใช้สำหรับการปรับปรุงการตัดสินใจด้วย Learning Module
        
        Args:
            market_conditions: เงื่อนไขตลาด
            
        Returns:
            float: ความแข็งแกร่งของเทรนด์เฉลี่ย
        """
        try:
            conditions = market_conditions.get('conditions', {})
            if not conditions:
                return 0.0
            
            trend_strengths = []
            for symbol_condition in conditions.values():
                if 'trend_strength' in symbol_condition:
                    trend_strengths.append(symbol_condition['trend_strength'])
            
            return np.mean(trend_strengths) if trend_strengths else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating average trend strength: {e}")
            return 0.0
    
    def _find_matching_patterns(self, opportunity: Dict, patterns: List[Dict]) -> List[Dict]:
        """
        หารูปแบบที่ตรงกับโอกาสปัจจุบัน
        
        เปรียบเทียบลักษณะของโอกาสกับรูปแบบที่เรียนรู้มา
        เพื่อปรับปรุงการตัดสินใจ
        
        Args:
            opportunity: ข้อมูลโอกาสปัจจุบัน
            patterns: รายการรูปแบบที่เรียนรู้
            
        Returns:
            List[Dict]: รายการรูปแบบที่ตรงกัน
        """
        try:
            matching_patterns = []
            
            for pattern in patterns:
                # Check if pattern characteristics match
                characteristics = pattern.get('characteristics', {})
                
                # Match volatility level
                volatility_match = False
                if characteristics.get('high_volatility', False):
                    if opportunity.get('volatility', 0) > 0.5:
                        volatility_match = True
                else:
                    if opportunity.get('volatility', 0) <= 0.5:
                        volatility_match = True
                
                # Match arbitrage level
                arbitrage_match = False
                if characteristics.get('high_arbitrage', False):
                    if opportunity.get('arbitrage_percent', 0) > 0.3:
                        arbitrage_match = True
                else:
                    if opportunity.get('arbitrage_percent', 0) <= 0.3:
                        arbitrage_match = True
                
                if volatility_match and arbitrage_match:
                    matching_patterns.append(pattern)
            
            return matching_patterns
            
        except Exception as e:
            self.logger.error(f"Error finding matching patterns: {e}")
            return []
    
    def _record_decision(self, decision: 'AIDecision', opportunity: Dict, decision_type: str):
        """
        บันทึกการตัดสินใจเพื่อการวิเคราะห์
        
        เก็บข้อมูลการตัดสินใจทั้งหมดเพื่อ:
        - วิเคราะห์ประสิทธิภาพ
        - ปรับปรุงระบบ
        - ติดตามสถิติ
        
        Args:
            decision: การตัดสินใจ
            opportunity: ข้อมูลโอกาส
            decision_type: ประเภทการตัดสินใจ
        """
        try:
            decision_record = {
                'timestamp': datetime.now(),
                'decision_type': decision_type,
                'should_act': decision.should_act,
                'confidence': decision.confidence,
                'reasoning': decision.reasoning,
                'opportunity': opportunity,
                'decision': decision.to_dict()
            }
            
            self.decision_history.append(decision_record)
            
            # Keep only last 1000 decisions
            if len(self.decision_history) > 1000:
                self.decision_history = self.decision_history[-1000:]
                
        except Exception as e:
            self.logger.error(f"Error recording decision: {e}")
    
    def get_decision_statistics(self) -> Dict:
        """
        ดึงสถิติการตัดสินใจ
        
        คำนวณและส่งคืนสถิติต่างๆ ของการตัดสินใจ:
        - จำนวนการตัดสินใจทั้งหมด
        - จำนวนการตัดสินใจแต่ละประเภท
        - อัตราการตัดสินใจเชิงบวก
        - ความมั่นใจเฉลี่ย
        
        Returns:
            Dict: สถิติการตัดสินใจ
        """
        try:
            if not self.decision_history:
                return {'total_decisions': 0}
            
            total_decisions = len(self.decision_history)
            arbitrage_decisions = len([d for d in self.decision_history if d['decision_type'] == 'arbitrage'])
            recovery_decisions = len([d for d in self.decision_history if d['decision_type'] == 'recovery'])
            
            positive_decisions = len([d for d in self.decision_history if d['should_act']])
            avg_confidence = np.mean([d['confidence'] for d in self.decision_history])
            
            return {
                'total_decisions': total_decisions,
                'arbitrage_decisions': arbitrage_decisions,
                'recovery_decisions': recovery_decisions,
                'positive_decisions': positive_decisions,
                'decision_rate': positive_decisions / total_decisions if total_decisions > 0 else 0,
                'average_confidence': avg_confidence
            }
            
        except Exception as e:
            self.logger.error(f"Error getting decision statistics: {e}")
            return {}
