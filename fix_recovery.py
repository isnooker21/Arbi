#!/usr/bin/env python3
"""
Fix Recovery System
==================

This script fixes the recovery system by registering all existing MT5 positions
in the individual order tracker.

Usage:
    python fix_recovery.py
"""

import sys
import os
import logging
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """Setup detailed logging for debugging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'fix_recovery_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    return logging.getLogger(__name__)

def main():
    """Main fix function"""
    logger = setup_logging()
    logger.info("🔧 Starting Recovery System Fix")
    
    try:
        # Import required modules
        from trading.broker_api import BrokerAPI
        from trading.correlation_manager import CorrelationManager
        
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
        
        # Fix missing orders
        logger.info("\n" + "="*60)
        logger.info("STEP 1: Fix Missing Orders")
        logger.info("="*60)
        
        correlation_manager.fix_missing_orders()
        
        # Test recovery system
        logger.info("\n" + "="*60)
        logger.info("STEP 2: Test Recovery System")
        logger.info("="*60)
        
        correlation_manager.test_recovery_system()
        
        logger.info("\n✅ Recovery system fix completed!")
        
    except Exception as e:
        logger.error(f"❌ Error during fix: {e}")
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
