"""
Multi-Armed Bandit for Pair Selection
====================================

Online learning system that learns which currency pairs
work best for recovery in different situations.

Uses UCB1 (Upper Confidence Bound) algorithm for
exploration-exploitation balance.
"""

import json
import logging
import math
from typing import Dict, List
from datetime import datetime

class PairSelectorBandit:
    """
    Multi-Armed Bandit for smart pair selection.
    
    Learns from experience which pairs work best for recovery
    and gradually improves selection over time.
    """
    
    def __init__(self, exploration_rate: float = 0.2, learning_rate: float = 0.1):
        self.logger = logging.getLogger(__name__)
        self.exploration_rate = exploration_rate
        self.learning_rate = learning_rate
        
        # Arms (currency pairs) statistics
        self.arms = {}  # {symbol: {attempts, wins, avg_pnl, last_update}}
        
        # Persistence
        self.persistence_file = "data/bandit_state.json"
        self._load_state()
        
        self.logger.info(f"🎰 Multi-Armed Bandit initialized (exploration: {exploration_rate:.1%})")
    
    def select_pair(self, candidates: List[Dict], use_bandit: bool = True) -> Dict:
        """
        Select best pair using UCB1 algorithm.
        
        Args:
            candidates: List of candidate pairs with correlation info
            use_bandit: If False, fallback to correlation-based selection
            
        Returns:
            Selected pair dict
        """
        if not use_bandit or not candidates:
            # Fallback: select by correlation
            return max(candidates, key=lambda x: abs(x.get('correlation', 0)))
        
        try:
            total_attempts = sum(arm.get('attempts', 0) for arm in self.arms.values())
            
            # Calculate UCB score for each candidate
            scored_candidates = []
            for candidate in candidates:
                symbol = candidate['symbol']
                
                # Initialize if new
                if symbol not in self.arms:
                    self.arms[symbol] = {
                        'attempts': 0,
                        'wins': 0,
                        'total_pnl': 0,
                        'avg_pnl': 0,
                        'last_update': datetime.now().isoformat()
                    }
                
                arm = self.arms[symbol]
                attempts = arm['attempts']
                
                # UCB1 score
                if attempts == 0:
                    # Encourage exploration of new arms
                    ucb_score = float('inf')
                else:
                    # Exploitation: average reward
                    avg_reward = arm['avg_pnl'] / 100  # Normalize
                    
                    # Exploration bonus
                    exploration_bonus = math.sqrt(
                        (2 * math.log(total_attempts + 1)) / attempts
                    )
                    
                    ucb_score = avg_reward + self.exploration_rate * exploration_bonus
                
                scored_candidates.append({
                    **candidate,
                    'ucb_score': ucb_score,
                    'bandit_attempts': attempts,
                    'bandit_win_rate': arm['wins'] / attempts if attempts > 0 else 0,
                    'bandit_avg_pnl': arm['avg_pnl']
                })
            
            # Select pair with highest UCB score
            best_pair = max(scored_candidates, key=lambda x: x['ucb_score'])
            
            self.logger.info(f"🎰 Bandit selected: {best_pair['symbol']}")
            self.logger.info(f"   UCB Score: {best_pair['ucb_score']:.3f}")
            self.logger.info(f"   Win Rate: {best_pair['bandit_win_rate']:.1%} ({best_pair['bandit_attempts']} attempts)")
            
            return best_pair
            
        except Exception as e:
            self.logger.error(f"Error in bandit selection: {e}")
            # Fallback
            return max(candidates, key=lambda x: abs(x.get('correlation', 0)))
    
    def update(self, symbol: str, success: bool, pnl: float):
        """
        Update bandit statistics after recovery attempt.
        
        Args:
            symbol: Currency pair symbol
            success: True if recovery was successful
            pnl: Profit/loss from recovery
        """
        try:
            if symbol not in self.arms:
                self.arms[symbol] = {
                    'attempts': 0,
                    'wins': 0,
                    'total_pnl': 0,
                    'avg_pnl': 0,
                    'last_update': datetime.now().isoformat()
                }
            
            arm = self.arms[symbol]
            
            # Update statistics
            arm['attempts'] += 1
            if success:
                arm['wins'] += 1
            arm['total_pnl'] += pnl
            
            # Exponential moving average for avg_pnl
            if arm['attempts'] == 1:
                arm['avg_pnl'] = pnl
            else:
                arm['avg_pnl'] = arm['avg_pnl'] * (1 - self.learning_rate) + pnl * self.learning_rate
            
            arm['last_update'] = datetime.now().isoformat()
            
            # Log update
            win_rate = arm['wins'] / arm['attempts']
            self.logger.info(f"🎰 Bandit updated: {symbol}")
            self.logger.info(f"   Win Rate: {win_rate:.1%} ({arm['wins']}/{arm['attempts']})")
            self.logger.info(f"   Avg PnL: ${arm['avg_pnl']:.2f}")
            
            # Save state periodically
            if arm['attempts'] % 10 == 0:
                self._save_state()
            
        except Exception as e:
            self.logger.error(f"Error updating bandit: {e}")
    
    def get_statistics(self) -> Dict:
        """Get bandit statistics"""
        stats = {}
        for symbol, arm in self.arms.items():
            attempts = arm['attempts']
            stats[symbol] = {
                'attempts': attempts,
                'wins': arm['wins'],
                'win_rate': arm['wins'] / attempts if attempts > 0 else 0,
                'avg_pnl': arm['avg_pnl'],
                'total_pnl': arm['total_pnl']
            }
        return stats
    
    def _save_state(self):
        """Save bandit state to file"""
        try:
            with open(self.persistence_file, 'w') as f:
                json.dump({
                    'arms': self.arms,
                    'exploration_rate': self.exploration_rate,
                    'learning_rate': self.learning_rate,
                    'saved_at': datetime.now().isoformat()
                }, f, indent=2)
            
            self.logger.debug(f"💾 Bandit state saved")
            
        except Exception as e:
            self.logger.error(f"Error saving bandit state: {e}")
    
    def _load_state(self):
        """Load bandit state from file"""
        try:
            with open(self.persistence_file, 'r') as f:
                data = json.load(f)
            
            self.arms = data.get('arms', {})
            loaded_arms = len(self.arms)
            
            if loaded_arms > 0:
                self.logger.info(f"📂 Loaded bandit state: {loaded_arms} pairs learned")
            
        except FileNotFoundError:
            self.logger.info("📁 No existing bandit state found")
        except Exception as e:
            self.logger.error(f"Error loading bandit state: {e}")
