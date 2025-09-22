"""
ระบบ AI Rule Engine สำหรับการตัดสินใจเทรด

ไฟล์นี้ทำหน้าที่:
- โหลดและจัดการกฎเกณฑ์การเทรดจากไฟล์ JSON
- ประเมินเงื่อนไขต่างๆ เช่น เวลา, ราคา, ความผันผวน
- คำนวณความเชื่อมั่นในการตัดสินใจ
- ติดตามผลการทำงานของกฎเกณฑ์แต่ละข้อ
- ปรับปรุงกฎเกณฑ์ตามผลการดำเนินงาน

ตัวอย่างกฎเกณฑ์:
- ถ้าเป็นช่วง Asian Session และ Arbitrage > 0.2% → เปิดตำแหน่ง
- ถ้า Volatility สูงและ Spread ต่ำ → เพิ่มขนาดตำแหน่ง
- ถ้า Drawdown > 30% → หยุดเทรด
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import re
import math

class RuleEngine:
    def __init__(self, rules_file: str = "config/rules.json"):
        self.logger = logging.getLogger(__name__)
        self.rules = self.load_rules(rules_file)
        self.performance_tracker = {}
        self.context_variables = {}
        self.rule_fire_count = {}
        
    def load_rules(self, rules_file: str) -> Dict:
        """Load rules from JSON configuration"""
        try:
            with open(rules_file, 'r') as f:
                rules = json.load(f)
            
            # Flatten all rules into a single list
            all_rules = []
            for category, rule_list in rules.items():
                for rule in rule_list:
                    rule['category'] = category
                    all_rules.append(rule)
            
            self.logger.info(f"Loaded {len(all_rules)} rules from {rules_file}")
            return all_rules
            
        except Exception as e:
            self.logger.error(f"Error loading rules: {e}")
            return []
    
    def evaluate_rules(self, context: Dict, category: str = 'all') -> 'AIDecision':
        """Evaluate rules and return decision"""
        try:
            fired_rules = []
            total_confidence = 0
            actions = []
            reasoning_parts = []
            
            # Update context with current time and date
            self._update_context_variables(context)
            
            for rule in self.rules:
                if category != 'all' and rule.get('category') != category:
                    continue
                
                if self.check_conditions(rule.get('conditions', []), context):
                    fired_rules.append(rule)
                    rule_confidence = rule.get('weight', 0.5) * rule.get('confidence', 0.5)
                    total_confidence += rule_confidence
                    actions.extend(rule.get('actions', []))
                    reasoning_parts.append(f"{rule.get('name', 'Unknown')} (conf: {rule_confidence:.2f})")
                    
                    # Track rule firing
                    rule_id = rule.get('id', 'unknown')
                    self.rule_fire_count[rule_id] = self.rule_fire_count.get(rule_id, 0) + 1
            
            # Calculate final confidence (normalize to 0-1)
            final_confidence = min(total_confidence, 1.0)
            
            # Determine if should act
            should_act = final_confidence > 0.7 and len(fired_rules) > 0
            
            # Create reasoning string
            reasoning = f"Fired {len(fired_rules)} rules: {', '.join(reasoning_parts)}"
            
            decision = AIDecision(
                should_act=should_act,
                confidence=final_confidence,
                reasoning=reasoning,
                fired_rules=fired_rules,
                actions=actions,
                context=context
            )
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Error evaluating rules: {e}")
            return AIDecision(False, 0.0, f"Error: {str(e)}", [], [], context)
    
    def check_conditions(self, conditions: List[str], context: Dict) -> bool:
        """Check if all conditions are met"""
        try:
            for condition in conditions:
                if not self.evaluate_condition(condition, context):
                    return False
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking conditions: {e}")
            return False
    
    def evaluate_condition(self, condition: str, context: Dict) -> bool:
        """Evaluate single condition"""
        try:
            # Parse condition string and evaluate against context
            # Support various condition types
            
            # Time-based conditions
            if 'current_time' in condition:
                return self._evaluate_time_condition(condition, context)
            
            # Numeric comparisons
            elif any(op in condition for op in ['>', '<', '>=', '<=', '==', '!=']):
                return self._evaluate_numeric_condition(condition, context)
            
            # String comparisons
            elif 'IN' in condition or 'NOT IN' in condition:
                return self._evaluate_string_condition(condition, context)
            
            # Boolean conditions
            elif condition in ['true', 'false']:
                return condition == 'true'
            
            # Variable existence
            elif condition.startswith('EXISTS '):
                var_name = condition.replace('EXISTS ', '').strip()
                return var_name in context
            
            # Default: treat as variable name and check if truthy
            else:
                return bool(context.get(condition, False))
                
        except Exception as e:
            self.logger.error(f"Error evaluating condition '{condition}': {e}")
            return False
    
    def _evaluate_time_condition(self, condition: str, context: Dict) -> bool:
        """Evaluate time-based conditions"""
        try:
            now = datetime.now()
            
            # Parse time ranges like "current_time >= '00:00' AND current_time <= '08:00'"
            if 'BETWEEN' in condition:
                # Format: "current_time BETWEEN '00:00' AND '08:00'"
                parts = condition.split('BETWEEN')
                if len(parts) == 2:
                    time_range = parts[1].strip()
                    start_time, end_time = time_range.split('AND')
                    start_time = start_time.strip().strip("'\"")
                    end_time = end_time.strip().strip("'\"")
                    
                    current_time_str = now.strftime('%H:%M')
                    return start_time <= current_time_str <= end_time
            
            # Parse individual time comparisons
            elif '>=' in condition or '<=' in condition or '>' in condition or '<' in condition:
                # Extract time value and operator
                time_match = re.search(r"current_time\s*([><=!]+)\s*['\"]([^'\"]+)['\"]", condition)
                if time_match:
                    operator = time_match.group(1)
                    time_value = time_match.group(2)
                    
                    current_time_str = now.strftime('%H:%M')
                    
                    if operator == '>=':
                        return current_time_str >= time_value
                    elif operator == '<=':
                        return current_time_str <= time_value
                    elif operator == '>':
                        return current_time_str > time_value
                    elif operator == '<':
                        return current_time_str < time_value
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error evaluating time condition '{condition}': {e}")
            return False
    
    def _evaluate_numeric_condition(self, condition: str, context: Dict) -> bool:
        """Evaluate numeric comparison conditions"""
        try:
            # Parse expressions like "arbitrage_percent > 0.3"
            for op in ['>=', '<=', '==', '!=', '>', '<']:
                if op in condition:
                    left, right = condition.split(op, 1)
                    left = left.strip()
                    right = right.strip()
                    
                    # Get left value from context or evaluate as literal
                    left_value = self._get_value(left, context)
                    right_value = self._get_value(right, context)
                    
                    if left_value is None or right_value is None:
                        return False
                    
                    # Perform comparison
                    if op == '>=':
                        return left_value >= right_value
                    elif op == '<=':
                        return left_value <= right_value
                    elif op == '==':
                        return left_value == right_value
                    elif op == '!=':
                        return left_value != right_value
                    elif op == '>':
                        return left_value > right_value
                    elif op == '<':
                        return left_value < right_value
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error evaluating numeric condition '{condition}': {e}")
            return False
    
    def _evaluate_string_condition(self, condition: str, context: Dict) -> bool:
        """Evaluate string comparison conditions"""
        try:
            if 'IN' in condition:
                # Format: "day_of_week IN ['monday', 'tuesday']"
                var_name, values_str = condition.split('IN', 1)
                var_name = var_name.strip()
                values_str = values_str.strip()
                
                # Extract values from list format
                values_match = re.search(r"\[(.*?)\]", values_str)
                if values_match:
                    values_str = values_match.group(1)
                    values = [v.strip().strip("'\"") for v in values_str.split(',')]
                    
                    var_value = context.get(var_name, '')
                    return var_value in values
            
            elif 'NOT IN' in condition:
                # Format: "day_of_week NOT IN ['saturday', 'sunday']"
                var_name, values_str = condition.split('NOT IN', 1)
                var_name = var_name.strip()
                values_str = values_str.strip()
                
                # Extract values from list format
                values_match = re.search(r"\[(.*?)\]", values_str)
                if values_match:
                    values_str = values_match.group(1)
                    values = [v.strip().strip("'\"") for v in values_str.split(',')]
                    
                    var_value = context.get(var_name, '')
                    return var_value not in values
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error evaluating string condition '{condition}': {e}")
            return False
    
    def _get_value(self, expression: str, context: Dict) -> Any:
        """Get value from expression (context variable or literal)"""
        try:
            expression = expression.strip()
            
            # Check if it's a context variable
            if expression in context:
                return context[expression]
            
            # Try to parse as number
            try:
                if '.' in expression:
                    return float(expression)
                else:
                    return int(expression)
            except ValueError:
                pass
            
            # Try to parse as string (remove quotes)
            if (expression.startswith("'") and expression.endswith("'")) or \
               (expression.startswith('"') and expression.endswith('"')):
                return expression[1:-1]
            
            # Return as string
            return expression
            
        except Exception as e:
            self.logger.error(f"Error getting value for '{expression}': {e}")
            return None
    
    def _update_context_variables(self, context: Dict):
        """Update context with current time and date variables"""
        try:
            now = datetime.now()
            
            context['current_time'] = now.strftime('%H:%M')
            context['current_date'] = now.strftime('%Y-%m-%d')
            context['day_of_week'] = now.strftime('%A').lower()
            context['hour'] = now.hour
            context['minute'] = now.minute
            
        except Exception as e:
            self.logger.error(f"Error updating context variables: {e}")
    
    def update_rule_performance(self, rule_id: str, success: bool, profit_loss: float):
        """Track rule performance for learning"""
        try:
            if rule_id not in self.performance_tracker:
                self.performance_tracker[rule_id] = {
                    'success_count': 0,
                    'failure_count': 0,
                    'total_pnl': 0.0,
                    'recent_performance': [],
                    'last_updated': datetime.now()
                }
            
            tracker = self.performance_tracker[rule_id]
            
            if success:
                tracker['success_count'] += 1
            else:
                tracker['failure_count'] += 1
            
            tracker['total_pnl'] += profit_loss
            tracker['recent_performance'].append({
                'timestamp': datetime.now(),
                'success': success,
                'pnl': profit_loss
            })
            
            # Keep only recent 100 records
            if len(tracker['recent_performance']) > 100:
                tracker['recent_performance'] = tracker['recent_performance'][-100:]
            
            tracker['last_updated'] = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error updating rule performance: {e}")
    
    def get_rule_performance(self, rule_id: str = None) -> Dict:
        """Get performance statistics for rules"""
        try:
            if rule_id:
                return self.performance_tracker.get(rule_id, {})
            else:
                return self.performance_tracker
                
        except Exception as e:
            self.logger.error(f"Error getting rule performance: {e}")
            return {}
    
    def get_rule_statistics(self) -> Dict:
        """Get overall rule statistics"""
        try:
            total_rules = len(self.rules)
            fired_rules = len(self.rule_fire_count)
            total_fires = sum(self.rule_fire_count.values())
            
            return {
                'total_rules': total_rules,
                'fired_rules': fired_rules,
                'total_fires': total_fires,
                'average_fires_per_rule': total_fires / total_rules if total_rules > 0 else 0,
                'most_fired_rule': max(self.rule_fire_count.items(), key=lambda x: x[1])[0] if self.rule_fire_count else None
            }
            
        except Exception as e:
            self.logger.error(f"Error getting rule statistics: {e}")
            return {}
    
    def reset_rule_fire_count(self):
        """Reset rule fire count (call at start of new session)"""
        try:
            self.rule_fire_count = {}
            self.logger.info("Rule fire count reset")
            
        except Exception as e:
            self.logger.error(f"Error resetting rule fire count: {e}")


class AIDecision:
    def __init__(self, should_act: bool, confidence: float, reasoning: str, 
                 fired_rules: List[Dict] = None, actions: List[str] = None, context: Dict = None):
        self.should_act = should_act
        self.confidence = confidence
        self.reasoning = reasoning
        self.fired_rules = fired_rules or []
        self.actions = actions or []
        self.context = context or {}
        self.position_size = 0.1  # Default
        self.position_size_multiplier = 1.0
        self.direction = {}
        self.timestamp = datetime.now()
    
    def set_position_size(self, size: float):
        """Set position size for this decision"""
        self.position_size = size
    
    def set_position_size_multiplier(self, multiplier: float):
        """Set position size multiplier"""
        self.position_size_multiplier = multiplier
    
    def set_direction(self, direction_dict: Dict[str, int]):
        """Set direction for each symbol in the decision"""
        self.direction = direction_dict
    
    def to_dict(self) -> Dict:
        """Convert decision to dictionary"""
        return {
            'should_act': self.should_act,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'fired_rules': [rule.get('name', 'Unknown') for rule in self.fired_rules],
            'actions': self.actions,
            'position_size': self.position_size,
            'position_size_multiplier': self.position_size_multiplier,
            'direction': self.direction,
            'timestamp': self.timestamp.isoformat()
        }
