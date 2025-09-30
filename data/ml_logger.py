"""
ML-Ready Logging System
======================

Comprehensive logging system for machine learning training.
Captures all relevant features, decisions, and outcomes.

Features:
- Rich market state capture
- Decision process logging
- Result tracking
- Database persistence
- Export for ML training
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, Optional

class MLRecoveryLogger:
    """
    ML-ready logging system for recovery attempts.
    
    Logs comprehensive data for future ML training:
    - Market conditions
    - Decision features
    - Execution details
    - Results and outcomes
    """
    
    def __init__(self, db_path: str = "data/trading_system.db"):
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        self._init_database()
        self.logger.info("🤖 ML Logger initialized")
    
    def _init_database(self):
        """Initialize ML logging tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # ML Recovery Logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ml_recovery_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    customer_id TEXT,
                    
                    -- Original Position
                    original_ticket TEXT,
                    original_symbol TEXT,
                    original_direction TEXT,
                    original_entry REAL,
                    original_current REAL,
                    original_loss_usd REAL,
                    original_loss_percent REAL,
                    original_lot_size REAL,
                    original_age_seconds REAL,
                    original_distance_pips REAL,
                    
                    -- Account State
                    account_balance REAL,
                    account_equity REAL,
                    margin_level REAL,
                    open_positions INT,
                    
                    -- Market Features
                    original_trend TEXT,
                    original_trend_confidence REAL,
                    original_volatility REAL,
                    market_session TEXT,
                    hour_of_day INT,
                    day_of_week INT,
                    
                    -- Recovery Decision
                    recovery_symbol TEXT,
                    recovery_direction TEXT,
                    recovery_lot_size REAL,
                    correlation REAL,
                    decision_method TEXT,
                    trend_confidence REAL,
                    
                    -- Candidates Considered
                    num_candidates INT,
                    best_correlation REAL,
                    candidates_json TEXT,
                    
                    -- Execution
                    requested_price REAL,
                    filled_price REAL,
                    slippage REAL,
                    spread REAL,
                    execution_time_ms INT,
                    recovery_ticket TEXT,
                    
                    -- Result
                    recovery_pnl REAL,
                    duration_seconds REAL,
                    exit_price REAL,
                    success BOOLEAN,
                    net_pnl REAL,
                    
                    -- Chain Info
                    is_chain_recovery BOOLEAN,
                    chain_depth INT,
                    parent_ticket TEXT,
                    
                    -- ML Features (JSON)
                    technical_indicators TEXT,
                    correlation_features TEXT,
                    metadata TEXT
                )
            ''')
            
            # Create indexes for fast queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ml_timestamp ON ml_recovery_logs(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ml_customer ON ml_recovery_logs(customer_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ml_success ON ml_recovery_logs(success)')
            
            conn.commit()
            conn.close()
            
            self.logger.info("✅ ML logging tables initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing ML logging: {e}")
    
    def log_recovery_attempt(self, recovery_data: Dict):
        """
        Log comprehensive recovery attempt data.
        
        Args:
            recovery_data: Dict containing all recovery information
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Extract data
            original = recovery_data.get('original', {})
            account = recovery_data.get('account', {})
            market = recovery_data.get('market', {})
            decision = recovery_data.get('decision', {})
            execution = recovery_data.get('execution', {})
            result = recovery_data.get('result', {})
            chain_info = recovery_data.get('chain_info', {})
            
            # Insert into database
            cursor.execute('''
                INSERT INTO ml_recovery_logs (
                    customer_id,
                    original_ticket, original_symbol, original_direction,
                    original_entry, original_current, original_loss_usd,
                    original_loss_percent, original_lot_size,
                    original_age_seconds, original_distance_pips,
                    account_balance, account_equity, margin_level, open_positions,
                    original_trend, original_trend_confidence, original_volatility,
                    market_session, hour_of_day, day_of_week,
                    recovery_symbol, recovery_direction, recovery_lot_size,
                    correlation, decision_method, trend_confidence,
                    num_candidates, best_correlation, candidates_json,
                    requested_price, filled_price, slippage, spread,
                    execution_time_ms, recovery_ticket,
                    recovery_pnl, duration_seconds, exit_price, success, net_pnl,
                    is_chain_recovery, chain_depth, parent_ticket,
                    technical_indicators, correlation_features, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                recovery_data.get('customer_id', 'default'),
                original.get('ticket'), original.get('symbol'), original.get('direction'),
                original.get('entry'), original.get('current'), original.get('loss_usd'),
                original.get('loss_percent'), original.get('lot_size'),
                original.get('age_seconds'), original.get('distance_pips'),
                account.get('balance'), account.get('equity'), account.get('margin_level'), account.get('open_positions'),
                market.get('original_trend'), market.get('original_trend_confidence'), market.get('original_volatility'),
                market.get('session'), market.get('hour'), market.get('day_of_week'),
                decision.get('recovery_symbol'), decision.get('recovery_direction'), decision.get('recovery_lot_size'),
                decision.get('correlation'), decision.get('method'), decision.get('trend_confidence'),
                decision.get('num_candidates'), decision.get('best_correlation'), json.dumps(decision.get('candidates', [])),
                execution.get('requested_price'), execution.get('filled_price'), execution.get('slippage'), execution.get('spread'),
                execution.get('execution_time_ms'), execution.get('recovery_ticket'),
                result.get('recovery_pnl'), result.get('duration_seconds'), result.get('exit_price'), 
                result.get('success'), result.get('net_pnl'),
                chain_info.get('is_chain'), chain_info.get('depth'), chain_info.get('parent_ticket'),
                json.dumps(recovery_data.get('technical_indicators', {})),
                json.dumps(recovery_data.get('correlation_features', {})),
                json.dumps(recovery_data.get('metadata', {}))
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.debug(f"📊 ML Log saved: {original.get('ticket')}_{original.get('symbol')}")
            
        except Exception as e:
            self.logger.error(f"Error logging ML data: {e}")
    
    def export_for_training(self, output_file: str = "data/ml_training_data.json", 
                           min_samples: int = 100) -> bool:
        """
        Export logged data for ML training.
        
        Args:
            output_file: Output JSON file path
            min_samples: Minimum samples required
            
        Returns:
            bool: True if export successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM ml_recovery_logs')
            count = cursor.fetchone()[0]
            
            if count < min_samples:
                self.logger.warning(f"⚠️ Only {count} samples (need {min_samples})")
                return False
            
            # Export all data
            cursor.execute('SELECT * FROM ml_recovery_logs')
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            # Convert to list of dicts
            data = []
            for row in rows:
                data.append(dict(zip(columns, row)))
            
            # Save to JSON
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            conn.close()
            
            self.logger.info(f"✅ Exported {count} samples to {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting ML data: {e}")
            return False
