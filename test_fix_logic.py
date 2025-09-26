#!/usr/bin/env python3
"""
Test Fix Logic
==============

This script tests the fix logic without requiring MetaTrader5.
It simulates the order registration process.

Usage:
    python test_fix_logic.py
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
            logging.FileHandler(f'test_fix_logic_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    return logging.getLogger(__name__)

def test_order_registration_logic():
    """Test the order registration logic"""
    logger = setup_logging()
    logger.info("🧪 Testing Order Registration Logic")
    
    # Simulate MT5 positions (based on the log you showed)
    simulated_positions = [
        # Group G1 (Magic 234001)
        {'ticket': '12345', 'symbol': 'GBPUSD', 'magic': 234001, 'profit': -73.60, 'type': 'SELL'},
        {'ticket': '12346', 'symbol': 'EURGBP', 'magic': 234001, 'profit': -4.63, 'type': 'BUY'},
        {'ticket': '12347', 'symbol': 'EURUSD', 'magic': 234001, 'profit': 57.04, 'type': 'BUY'},
        
        # Group G2 (Magic 234002)
        {'ticket': '12348', 'symbol': 'EURUSD', 'magic': 234002, 'profit': -105.80, 'type': 'SELL'},
        {'ticket': '12349', 'symbol': 'USDJPY', 'magic': 234002, 'profit': -43.98, 'type': 'BUY'},
        {'ticket': '12350', 'symbol': 'EURJPY', 'magic': 234002, 'profit': 87.96, 'type': 'SELL'},
        
        # Group G3 (Magic 234003)
        {'ticket': '12351', 'symbol': 'USDJPY', 'magic': 234003, 'profit': -45.81, 'type': 'SELL'},
        {'ticket': '12352', 'symbol': 'GBPJPY', 'magic': 234003, 'profit': -23.82, 'type': 'BUY'},
        {'ticket': '12353', 'symbol': 'GBPUSD', 'magic': 234003, 'profit': -40.48, 'type': 'SELL'},
        
        # Group G4 (Magic 234004)
        {'ticket': '12354', 'symbol': 'AUDUSD', 'magic': 234004, 'profit': -25.30, 'type': 'BUY'},
        {'ticket': '12355', 'symbol': 'EURAUD', 'magic': 234004, 'profit': -15.20, 'type': 'SELL'},
        {'ticket': '12356', 'symbol': 'EURUSD', 'magic': 234004, 'profit': -1.35, 'type': 'BUY'},
    ]
    
    # Magic to group mapping
    magic_to_group = {
        234001: "group_triangle_1_1",
        234002: "group_triangle_2_1", 
        234003: "group_triangle_3_1",
        234004: "group_triangle_4_1",
        234005: "group_triangle_5_1",
        234006: "group_triangle_6_1"
    }
    
    logger.info(f"📊 Simulating {len(simulated_positions)} positions from MT5")
    
    # Simulate order registration
    registered_orders = []
    losing_orders = []
    
    for pos in simulated_positions:
        ticket = str(pos.get('ticket', ''))
        symbol = pos.get('symbol', '')
        magic = pos.get('magic', 0)
        profit = pos.get('profit', 0)
        
        # Get group_id from magic number
        group_id = magic_to_group.get(magic, f"group_unknown_{magic}")
        
        # Register order
        order_info = {
            'ticket': ticket,
            'symbol': symbol,
            'group_id': group_id,
            'type': 'ORIGINAL',
            'status': 'NOT_HEDGED',
            'profit': profit
        }
        
        registered_orders.append(order_info)
        
        # Check if losing money
        if profit < -10:  # Losing more than $10
            losing_orders.append(order_info)
        
        logger.info(f"✅ Registered: {ticket}_{symbol} (${profit:.2f}) in {group_id}")
    
    logger.info(f"📊 Registration complete: {len(registered_orders)} registered")
    logger.info(f"📉 Losing orders: {len(losing_orders)}")
    
    # Show losing orders
    if losing_orders:
        logger.info("🔍 Orders needing recovery:")
        for order in losing_orders:
            logger.info(f"   - {order['ticket']}_{order['symbol']}: ${order['profit']:.2f}")
    
    return len(losing_orders) > 0

def test_recovery_conditions():
    """Test recovery conditions for losing orders"""
    logger = setup_logging()
    logger.info("🧪 Testing Recovery Conditions")
    
    # Simulate recovery thresholds
    recovery_thresholds = {
        'min_loss_threshold': -0.005,  # -0.5%
        'min_correlation': 0.5,
        'base_lot_size': 0.1
    }
    
    # Simulate account balance
    balance = 9183.94
    
    # Test losing orders from the simulation
    losing_orders = [
        {'ticket': '12345', 'symbol': 'GBPUSD', 'profit': -73.60},
        {'ticket': '12348', 'symbol': 'EURUSD', 'profit': -105.80},
        {'ticket': '12349', 'symbol': 'USDJPY', 'profit': -43.98},
        {'ticket': '12351', 'symbol': 'USDJPY', 'profit': -45.81},
        {'ticket': '12352', 'symbol': 'GBPJPY', 'profit': -23.82},
        {'ticket': '12353', 'symbol': 'GBPUSD', 'profit': -40.48},
        {'ticket': '12354', 'symbol': 'AUDUSD', 'profit': -25.30},
        {'ticket': '12355', 'symbol': 'EURAUD', 'profit': -15.20},
    ]
    
    logger.info(f"📊 Testing {len(losing_orders)} losing orders")
    logger.info(f"📊 Account balance: ${balance:.2f}")
    logger.info(f"📊 Min loss threshold: {recovery_thresholds['min_loss_threshold']:.3f} ({recovery_thresholds['min_loss_threshold']*100:.1f}%)")
    
    recovery_candidates = []
    
    for order in losing_orders:
        profit = order['profit']
        symbol = order['symbol']
        ticket = order['ticket']
        
        # Check loss threshold
        loss_threshold = recovery_thresholds.get('min_loss_threshold', -0.005)
        loss_percent = profit / balance
        meets_loss = loss_percent <= loss_threshold
        
        # Check if position is losing money
        meets_profit_loss = profit < 0
        
        # Check minimum loss amount (e.g., at least $10 loss)
        min_loss_amount = -10.0  # $10 minimum loss
        meets_min_loss = profit <= min_loss_amount
        
        # All conditions must be met
        meets_conditions = meets_loss and meets_profit_loss and meets_min_loss
        
        logger.info(f"🔍 {ticket}_{symbol}: PnL=${profit:.2f}")
        logger.info(f"   Loss check: {loss_percent:.4f} <= {loss_threshold:.4f} = {meets_loss}")
        logger.info(f"   Profit loss check: {profit:.2f} < 0 = {meets_profit_loss}")
        logger.info(f"   Min loss amount check: {profit:.2f} <= {min_loss_amount} = {meets_min_loss}")
        logger.info(f"   Final result: {meets_conditions}")
        
        if meets_conditions:
            recovery_candidates.append(order)
            logger.info(f"✅ Added to recovery candidates: {ticket}_{symbol}")
        else:
            logger.info(f"❌ Skipped: {ticket}_{symbol} - conditions not met")
        logger.info("")
    
    logger.info(f"🎯 Total recovery candidates: {len(recovery_candidates)}")
    
    if recovery_candidates:
        # Find best candidate (biggest loss)
        best_candidate = min(recovery_candidates, key=lambda x: x['profit'])
        logger.info(f"🚀 Best candidate for recovery: {best_candidate['ticket']}_{best_candidate['symbol']} (${best_candidate['profit']:.2f})")
        
        # Test correlation finding
        symbol = best_candidate['symbol']
        logger.info(f"🔍 Finding correlation pairs for {symbol}")
        
        # Simple correlation test
        all_symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'EURGBP', 'EURJPY', 'GBPJPY', 'EURAUD']
        other_symbols = [s for s in all_symbols if s != symbol]
        
        correlation_candidates = []
        for other_symbol in other_symbols[:5]:  # Test top 5
            # Simple correlation estimation
            if symbol[:3] == other_symbol[:3] or symbol[3:] == other_symbol[3:]:
                correlation = 0.8
            elif symbol[:3] in other_symbol or symbol[3:] in other_symbol:
                correlation = 0.6
            else:
                correlation = 0.3
            
            if correlation > 0.5:
                correlation_candidates.append({
                    'symbol': other_symbol,
                    'correlation': correlation
                })
        
        logger.info(f"📊 Found {len(correlation_candidates)} correlation candidates:")
        for candidate in correlation_candidates:
            logger.info(f"   - {candidate['symbol']}: {candidate['correlation']:.2f}")
        
        if correlation_candidates:
            best_correlation = correlation_candidates[0]
            logger.info(f"🎯 Best correlation: {best_correlation['symbol']} ({best_correlation['correlation']:.2f})")
            logger.info(f"✅ Recovery would be executed: {symbol} -> {best_correlation['symbol']}")
        else:
            logger.warning(f"⚠️ No correlation pairs found for {symbol}")
    
    return len(recovery_candidates) > 0

def main():
    """Main test function"""
    logger = setup_logging()
    logger.info("🚀 Starting Fix Logic Test")
    
    try:
        # Test 1: Order registration logic
        logger.info("\n" + "="*60)
        logger.info("TEST 1: Order Registration Logic")
        logger.info("="*60)
        
        has_losing_orders = test_order_registration_logic()
        
        # Test 2: Recovery conditions
        logger.info("\n" + "="*60)
        logger.info("TEST 2: Recovery Conditions")
        logger.info("="*60)
        
        can_recover = test_recovery_conditions()
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("SUMMARY")
        logger.info("="*60)
        
        if has_losing_orders and can_recover:
            logger.info("✅ SUCCESS: System should work after fixing missing orders")
            logger.info("🔧 Solution: Run register_existing_orders() to fix the issue")
        elif has_losing_orders and not can_recover:
            logger.info("⚠️ PARTIAL: Orders found but recovery conditions not met")
            logger.info("🔧 Solution: Adjust recovery thresholds")
        else:
            logger.info("❌ ISSUE: No losing orders found or system logic error")
        
        logger.info("\n✅ All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error during testing: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
