#!/usr/bin/env python3
"""
Debug Recovery System
====================

This script helps debug the recovery system by:
1. Checking individual order tracker status
2. Forcing recovery checks
3. Displaying recovery thresholds
4. Testing recovery conditions

Usage:
    python debug_recovery.py
"""

import sys
import os
import logging
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading.broker_api import BrokerAPI
from trading.correlation_manager import CorrelationManager
from trading.individual_order_tracker import IndividualOrderTracker

def setup_logging():
    """Setup detailed logging for debugging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'debug_recovery_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    return logging.getLogger(__name__)

def main():
    """Main debug function"""
    logger = setup_logging()
    logger.info("🔍 Starting Recovery System Debug")
    
    try:
        # Initialize broker API
        logger.info("🔌 Connecting to broker...")
        broker = BrokerAPI("MetaTrader5")
        
        if not broker.connect():
            logger.error("❌ Failed to connect to broker")
            return False
        
        logger.info("✅ Connected to broker")
        
        # Initialize correlation manager
        logger.info("🚀 Initializing correlation manager...")
        correlation_manager = CorrelationManager(broker)
        
        # Test 1: Check individual order tracker status
        logger.info("\n" + "="*60)
        logger.info("TEST 1: Individual Order Tracker Status")
        logger.info("="*60)
        
        order_tracker = correlation_manager.order_tracker
        stats = order_tracker.get_statistics()
        
        logger.info(f"📊 Order Tracker Statistics:")
        logger.info(f"   Total Tracked Orders: {stats['total_tracked_orders']}")
        logger.info(f"   Original Orders: {stats['original_orders']}")
        logger.info(f"   Recovery Orders: {stats['recovery_orders']}")
        logger.info(f"   Hedged Orders: {stats['hedged_orders']}")
        logger.info(f"   Not Hedged Orders: {stats['not_hedged_orders']}")
        
        # Test 2: Check orders needing recovery
        logger.info("\n" + "="*60)
        logger.info("TEST 2: Orders Needing Recovery")
        logger.info("="*60)
        
        orders_needing_recovery = order_tracker.get_orders_needing_recovery()
        logger.info(f"🔍 Orders needing recovery: {len(orders_needing_recovery)}")
        
        for order_info in orders_needing_recovery:
            ticket = order_info.get('ticket')
            symbol = order_info.get('symbol')
            order_type = order_info.get('type')
            logger.info(f"   - {ticket}_{symbol} ({order_type})")
        
        # Test 3: Check recovery thresholds
        logger.info("\n" + "="*60)
        logger.info("TEST 3: Recovery Thresholds")
        logger.info("="*60)
        
        correlation_manager.log_recovery_thresholds()
        
        # Test 4: Adjust thresholds for testing
        logger.info("\n" + "="*60)
        logger.info("TEST 4: Adjust Recovery Thresholds for Testing")
        logger.info("="*60)
        
        correlation_manager.adjust_recovery_thresholds_for_testing()
        
        # Test 5: Force recovery check
        logger.info("\n" + "="*60)
        logger.info("TEST 5: Force Recovery Check")
        logger.info("="*60)
        
        correlation_manager.force_recovery_check()
        
        # Test 6: Check MT5 positions
        logger.info("\n" + "="*60)
        logger.info("TEST 6: MT5 Positions")
        logger.info("="*60)
        
        all_positions = broker.get_all_positions()
        logger.info(f"📊 Total MT5 positions: {len(all_positions)}")
        
        losing_positions = [pos for pos in all_positions if pos.get('profit', 0) < 0]
        logger.info(f"📉 Losing positions: {len(losing_positions)}")
        
        for pos in losing_positions[:5]:  # Show top 5 losing positions
            ticket = pos.get('ticket')
            symbol = pos.get('symbol')
            profit = pos.get('profit', 0)
            logger.info(f"   - {ticket}_{symbol}: ${profit:.2f}")
        
        logger.info("\n✅ Debug completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error during debug: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False
    
    finally:
        # Disconnect from broker
        if 'broker' in locals():
            broker.disconnect()
            logger.info("🔌 Disconnected from broker")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
