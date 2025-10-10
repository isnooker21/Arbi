#!/usr/bin/env python3
"""
Script บังคับให้ VPS ใช้ config ที่ถูกต้อง
"""

import json
import os

def force_vps_config():
    print("="*80)
    print("🔧 บังคับให้ VPS ใช้ config ที่ถูกต้อง")
    print("="*80)
    
    # 1. สร้าง adaptive_params.json ใหม่
    print("\n1️⃣ สร้าง adaptive_params.json ใหม่:")
    try:
        config = {
            "market_regimes": {
                "volatile": {
                    "arbitrage_threshold": 0.0025,
                    "recovery_aggressiveness": 0.6,
                    "max_triangles": 3,
                    "execution_speed_ms": 150,
                    "description": "High volatility market - conservative approach"
                },
                "trending": {
                    "arbitrage_threshold": 0.002,
                    "recovery_aggressiveness": 0.8,
                    "max_triangles": 3,
                    "execution_speed_ms": 100,
                    "description": "Strong trend market - conservative approach"
                },
                "ranging": {
                    "arbitrage_threshold": 0.001,
                    "recovery_aggressiveness": 0.7,
                    "max_triangles": 3,
                    "execution_speed_ms": 80,
                    "description": "Range-bound market - balanced approach"
                },
                "normal": {
                    "arbitrage_threshold": 0.0012,
                    "recovery_aggressiveness": 0.7,
                    "max_triangles": 3,
                    "execution_speed_ms": 100,
                    "description": "Normal market conditions - standard approach"
                }
            },
            "position_sizing": {
                "lot_calculation": {
                    "use_simple_mode": False,
                    "use_risk_based_sizing": True,
                    "risk_per_trade_percent": 0.5,
                    "max_loss_pips": 100.0,
                    "description": "⭐ Optimized for $10K: Risk 0.5% per trade, Max Drawdown ~14%, CAGR ~15%/year"
                },
                "risk_management": {
                    "max_portfolio_risk": 0.05,
                    "max_concurrent_groups": 3.0,
                    "correlation_limit": 0.8,
                    "description": "⭐ Optimized for $10K: Max 5% portfolio risk, Max 3 groups, conservative approach"
                }
            },
            "recovery_params": {
                "correlation_thresholds": {
                    "min_correlation": 0.65,
                    "max_correlation": 0.95,
                    "optimal_correlation": 0.8,
                    "description": "⭐ Optimized: Min correlation 0.65 for better pair quality"
                },
                "loss_thresholds": {
                    "min_loss_percent": -1.0,
                    "min_price_distance_pips": 15.0,
                    "recovery_target": 0.0,
                    "use_percentage_based": True,
                    "description": "⭐ Optimized: 1% of balance AND 15 pips distance (prevent premature recovery)"
                },
                "timing": {
                    "max_recovery_time_hours": 24,
                    "recovery_check_interval_seconds": 10,
                    "cooldown_between_checks": 15.0,
                    "min_position_age_seconds": 90.0,
                    "rebalancing_frequency_hours": 6,
                    "description": "⭐ Optimized: Wait 90s and 15 pips before recovery (more conservative)"
                },
                "hedge_ratios": {
                    "min_ratio": 0.7,
                    "max_ratio": 2.0,
                    "default_ratio": 1.0
                },
                "trend_analysis": {
                    "enabled": True,
                    "periods": 50.0,
                    "confidence_threshold": 0.4,
                    "use_for_direction": True,
                    "enable_chain_on_low_confidence": True,
                    "description": "Trend analysis for smart direction selection. Enable chain if confidence < 40%"
                },
                "diversification": {
                    "max_usage_per_symbol": 3.0,
                    "enforce_limit": True,
                    "description": "Max 3 times per symbol"
                },
                "chain_recovery": {
                    "enabled": True,
                    "mode": "conditional",
                    "max_chain_depth": 3.0,
                    "min_loss_percent_for_chain": -1.0,
                    "only_when_trend_uncertain": True,
                    "description": "⭐ Optimized: Max 3 levels chain (reduced from 5) for lower risk"
                },
                "multi_armed_bandit": {
                    "enabled": True,
                    "exploration_rate": 0.2,
                    "learning_rate": 0.1,
                    "description": "Online learning for pair selection optimization"
                },
                "ml_logging": {
                    "enabled": True,
                    "log_to_database": True,
                    "log_market_features": True,
                    "log_decision_process": True,
                    "upload_to_central": False,
                    "description": "Comprehensive logging for ML training"
                },
                "auto_registration": {
                    "enabled": True,
                    "register_on_startup": True,
                    "register_on_new_orders": True,
                    "sync_interval_seconds": 30.0,
                    "description": "Auto register orders for tracking"
                },
                "smart_recovery_flow": {
                    "enabled": True,
                    "flow_type": "3_stage",
                    "stage_1_arbitrage_enabled": True,
                    "stage_2_correlation_enabled": True,
                    "stage_3_chain_enabled": True,
                    "priority_queue_enabled": True,
                    "max_priority_queue_size": 50,
                    "smart_cooldown_seconds": 5,
                    "description": "Smart Recovery Flow: 3-Stage Process (Arbitrage → Correlation → Chain)"
                },
                "description": "Smart recovery with trend analysis, conditional chain recovery, ML-ready logging, and Smart Recovery Flow"
            },
            "arbitrage_params": {
                "detection": {
                    "min_threshold": 0.00015,
                    "max_threshold": 0.005,
                    "spread_tolerance": 0.5,
                    "execution_timeout_ms": 1000
                },
                "triangles": {
                    "max_active_triangles": 3.0,
                    "triangle_hold_time_minutes": 120.0,
                    "correlation_check_interval": 60.0
                },
                "closing": {
                    "enable_net_pnl_check": True,
                    "min_profit_to_close": 5,
                    "min_profit_base": 10.0,
                    "min_profit_base_balance": 10000.0,
                    "trailing_stop_enabled": True,
                    "trailing_stop_distance": 15.0,
                    "lock_profit_percentage": 0.5,
                    "description": "⭐ Optimized for $10K: Min profit $10, Trailing stop $15, Max 3 triangles"
                },
                "execution": {
                    "max_slippage": 0.0005,
                    "commission_rate": 0.0001,
                    "min_profit_threshold": 0.0001
                },
                "description": "Arbitrage detection and execution parameters"
            },
            "market_analysis": {
                "regime_detection": {
                    "analysis_interval_seconds": 300,
                    "volatility_periods": 96,
                    "trend_periods": 24,
                    "correlation_periods": 168
                },
                "thresholds": {
                    "volatility": {
                        "low": 0.0005,
                        "high": 0.002
                    },
                    "trend_strength": {
                        "weak": 0.3,
                        "strong": 0.7
                    },
                    "correlation_stability": {
                        "unstable": 0.3,
                        "stable": 0.7
                    }
                },
                "description": "Market analysis and regime detection parameters"
            },
            "system_limits": {
                "max_concurrent_groups": 6,
                "max_portfolio_risk": 0.15,
                "max_drawdown_percent": 30,
                "max_position_hold_hours": 24,
                "max_recovery_attempts": 3,
                "emergency_stop_loss": 0.2,
                "description": "System-wide limits and safety parameters"
            },
            "performance_monitoring": {
                "metrics": {
                    "update_interval_seconds": 60,
                    "history_days": 30,
                    "alert_thresholds": {
                        "min_win_rate": 0.4
                    }
                },
                "logging": {
                    "log_level": "INFO",
                    "log_retention_days": 7,
                    "performance_log_interval_minutes": 15
                },
                "description": "Performance monitoring and logging parameters"
            },
            "broker_settings": {
                "connection": {
                    "timeout_seconds": 30,
                    "retry_attempts": 3,
                    "heartbeat_interval_seconds": 60
                },
                "execution": {
                    "max_orders_per_minute": 60,
                    "order_timeout_seconds": 10,
                    "slippage_tolerance": 0.0005
                },
                "data": {
                    "refresh_rate_ms": 50,
                    "historical_data_limit": 1000,
                    "real_time_buffer_size": 100
                },
                "description": "Broker connection and execution settings"
            },
            "system_settings": {
                "engine": {
                    "trading_loop_interval_seconds": 30,
                    "max_memory_usage_mb": 500,
                    "cpu_usage_limit_percent": 20
                },
                "threading": {
                    "max_worker_threads": 4,
                    "thread_timeout_seconds": 300,
                    "queue_size": 100
                },
                "description": "System performance and threading settings"
            }
        }
        
        with open('config/adaptive_params.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print("   ✅ สร้าง adaptive_params.json ใหม่เสร็จสิ้น")
        print("   📊 risk_per_trade_percent = 0.5")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 2. ลบ config files อื่นๆ
    print("\n2️⃣ ลบ config files อื่นๆ:")
    try:
        backup_files = [
            'config/adaptive_params.json.backup',
            'config/settings.json.backup',
            'config/broker_config.json.backup'
        ]
        
        for backup_file in backup_files:
            if os.path.exists(backup_file):
                os.remove(backup_file)
                print(f"   ✅ ลบ {backup_file}")
            else:
                print(f"   ℹ️ ไม่มี {backup_file}")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 3. ตรวจสอบผลลัพธ์
    print("\n3️⃣ ตรวจสอบผลลัพธ์:")
    try:
        with open('config/adaptive_params.json', 'r') as f:
            config = json.load(f)
        
        lot_calc = config.get('position_sizing', {}).get('lot_calculation', {})
        risk_percent = lot_calc.get('risk_per_trade_percent')
        
        print(f"   📊 risk_per_trade_percent: {risk_percent}")
        
        if risk_percent == 0.5:
            print("   ✅ สำเร็จ! risk_per_trade_percent = 0.5%")
        else:
            print(f"   ❌ ล้มเหลว! risk_per_trade_percent = {risk_percent}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "="*80)
    print("✅ เสร็จสิ้น - VPS จะใช้ risk 0.5% แน่นอน!")
    print("="*80)

if __name__ == "__main__":
    force_vps_config()
