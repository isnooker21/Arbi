"""
Individual Order Tracking System
===============================

Tracks each order individually by ticket number rather than grouping by symbol.
Provides accurate hedge status for each specific order.

Key Features:
- Individual ticket-based tracking
- Original vs Recovery order distinction  
- Chain recovery support
- No false positive hedge detection
- Real-time MT5 synchronization
"""

import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional, Set

class IndividualOrderTracker:
    """
    Individual order tracking system.
    
    Tracks each order by unique ticket rather than symbol/group grouping.
    Prevents false hedge detection and supports chain recovery.
    """
    
    def __init__(self, broker_api):
        """
        Initialize the individual order tracker.
        
        Args:
            broker_api: Broker API instance for MT5 communication
        """
        self.broker = broker_api
        self.logger = logging.getLogger(__name__)
        
        # Individual order tracking
        # Key: f"{ticket}_{symbol}", Value: order_info
        self.order_tracking: Dict[str, Dict] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self.stats = {
            'original_orders_registered': 0,
            'recovery_orders_registered': 0,
            'orders_hedged': 0,
            'orders_removed': 0,
            'sync_operations': 0,
            'last_sync': None
        }
        
        self.logger.info("🚀 Individual Order Tracker initialized")
    
    def register_original_order(self, ticket: str, symbol: str, group_id: str) -> bool:
        """
        Register original arbitrage order.
        
        Args:
            ticket: MT5 order ticket
            symbol: Currency pair symbol
            group_id: Trading group identifier
            
        Returns:
            bool: True if order was successfully registered
        """
        with self._lock:
            order_key = f"{ticket}_{symbol}"
            
            if order_key in self.order_tracking:
                self.logger.warning(f"🚫 Order {order_key} already registered")
                return False
            
            self.order_tracking[order_key] = {
                "ticket": ticket,
                "symbol": symbol,
                "group_id": group_id,
                "type": "ORIGINAL",
                "status": "NOT_HEDGED",
                "recovery_orders": [],  # List of recovery orders for this position
                "created_at": datetime.now(),
                "last_sync": datetime.now()
            }
            
            self.stats['original_orders_registered'] += 1
            self.logger.info(f"📝 Original order registered: {order_key}")
            return True
    
    def register_recovery_order(self, recovery_ticket: str, recovery_symbol: str, 
                              original_ticket: str, original_symbol: str) -> bool:
        """
        Register recovery order and mark original as hedged.
        
        Args:
            recovery_ticket: Recovery order ticket
            recovery_symbol: Recovery order symbol
            original_ticket: Original order ticket being hedged
            original_symbol: Original order symbol being hedged
            
        Returns:
            bool: True if recovery order was successfully registered
        """
        with self._lock:
            original_key = f"{original_ticket}_{original_symbol}"
            recovery_key = f"{recovery_ticket}_{recovery_symbol}"
            
            # Check if original order exists
            if original_key not in self.order_tracking:
                self.logger.error(f"❌ Original order {original_key} not found for recovery")
                return False
            
            # Mark original order as hedged
            self.order_tracking[original_key]["status"] = "HEDGED"
            self.order_tracking[original_key]["recovery_orders"].append(recovery_key)
            
            # Add recovery order
            self.order_tracking[recovery_key] = {
                "ticket": recovery_ticket,
                "symbol": recovery_symbol,
                "type": "RECOVERY",
                "status": "NOT_HEDGED",
                "hedging_for": original_key,  # Which order this is hedging
                "recovery_orders": [],  # Chain recovery orders
                "created_at": datetime.now(),
                "last_sync": datetime.now()
            }
            
            self.stats['recovery_orders_registered'] += 1
            self.stats['orders_hedged'] += 1
            
            self.logger.info(f"✅ Recovery registered: {original_key} → {recovery_key}")
            return True
    
    def is_order_hedged(self, ticket: str, symbol: str) -> bool:
        """
        Check if specific order is already hedged.
        
        Args:
            ticket: Order ticket
            symbol: Order symbol
            
        Returns:
            bool: True if order is hedged
        """
        with self._lock:
            order_key = f"{ticket}_{symbol}"
            if order_key in self.order_tracking:
                return self.order_tracking[order_key]["status"] == "HEDGED"
            return False
    
    def needs_recovery(self, ticket: str, symbol: str) -> bool:
        """
        Check if order needs recovery (NOT_HEDGED and exists in tracking).
        
        Args:
            ticket: Order ticket
            symbol: Order symbol
            
        Returns:
            bool: True if order needs recovery
        """
        with self._lock:
            order_key = f"{ticket}_{symbol}"
            if order_key in self.order_tracking:
                return self.order_tracking[order_key]["status"] == "NOT_HEDGED"
            return False
    
    def get_order_info(self, ticket: str, symbol: str) -> Optional[Dict]:
        """
        Get detailed order information.
        
        Args:
            ticket: Order ticket
            symbol: Order symbol
            
        Returns:
            Dict: Order information or None if not found
        """
        with self._lock:
            order_key = f"{ticket}_{symbol}"
            return self.order_tracking.get(order_key)
    
    def get_all_orders(self) -> Dict[str, Dict]:
        """
        Get all tracked orders.
        
        Returns:
            Dict: All tracked orders
        """
        with self._lock:
            return self.order_tracking.copy()
    
    def get_orders_needing_recovery(self) -> List[Dict]:
        """
        Get all orders that need recovery.
        
        Returns:
            List[Dict]: Orders with status NOT_HEDGED
        """
        with self._lock:
            needing_recovery = []
            for order_key, order_info in self.order_tracking.items():
                if order_info.get("status") == "NOT_HEDGED":
                    needing_recovery.append(order_info)
            return needing_recovery
    
    def sync_with_mt5(self) -> Dict:
        """
        Sync order status with actual MT5 positions.
        Remove orders that are no longer active in MT5.
        
        Returns:
            Dict: Sync operation results
        """
        with self._lock:
            sync_results = {
                'orders_checked': 0,
                'orders_removed': 0,
                'errors': 0,
                'sync_time': datetime.now()
            }
            
            try:
                # Get all positions from MT5
                all_positions = self.broker.get_all_positions()
                if not all_positions:
                    self.logger.warning("⚠️ No positions returned from MT5 during sync")
                    return sync_results
                
                # Create set of active tickets for quick lookup
                active_tickets: Set[str] = set()
                for pos in all_positions:
                    ticket = str(pos.get('ticket', ''))
                    if ticket:
                        active_tickets.add(ticket)
                
                # Check each tracked order
                orders_to_remove = []
                for order_key, order_info in self.order_tracking.items():
                    sync_results['orders_checked'] += 1
                    
                    ticket = order_info.get('ticket')
                    if not ticket:
                        continue
                    
                    # Check if order is still active in MT5
                    if ticket not in active_tickets:
                        # Order is closed - mark for removal
                        orders_to_remove.append(order_key)
                        sync_results['orders_removed'] += 1
                        self.logger.debug(f"🔄 Order {order_key} (Ticket: {ticket}) not found in MT5 - will remove")
                    else:
                        self.logger.debug(f"✅ Order {order_key} (Ticket: {ticket}) still active in MT5")
                
                # Remove closed orders
                for order_key in orders_to_remove:
                    del self.order_tracking[order_key]
                
                self.stats['sync_operations'] += 1
                self.stats['last_sync'] = datetime.now()
                self.stats['orders_removed'] += sync_results['orders_removed']
                
                if sync_results['orders_removed'] > 0:
                    self.logger.info(f"🔄 Sync completed: {sync_results['orders_checked']} checked, {sync_results['orders_removed']} removed")
                
            except Exception as e:
                sync_results['errors'] += 1
                self.logger.error(f"❌ Error during MT5 sync: {e}")
            
            return sync_results
    
    def get_statistics(self) -> Dict:
        """
        Get tracker statistics.
        
        Returns:
            Dict: Tracker statistics
        """
        with self._lock:
            stats = self.stats.copy()
            stats.update({
                'total_tracked_orders': len(self.order_tracking),
                'original_orders': len([o for o in self.order_tracking.values() if o.get('type') == 'ORIGINAL']),
                'recovery_orders': len([o for o in self.order_tracking.values() if o.get('type') == 'RECOVERY']),
                'hedged_orders': len([o for o in self.order_tracking.values() if o.get('status') == 'HEDGED']),
                'not_hedged_orders': len([o for o in self.order_tracking.values() if o.get('status') == 'NOT_HEDGED'])
            })
            return stats
    
    def log_status_summary(self):
        """Log a summary of all tracked orders."""
        with self._lock:
            stats = self.get_statistics()
            
            self.logger.info("📊 INDIVIDUAL ORDER TRACKER STATUS SUMMARY:")
            self.logger.info(f"   Total Tracked Orders: {stats['total_tracked_orders']}")
            self.logger.info(f"   Original Orders: {stats['original_orders']}")
            self.logger.info(f"   Recovery Orders: {stats['recovery_orders']}")
            self.logger.info(f"   Hedged Orders: {stats['hedged_orders']}")
            self.logger.info(f"   Not Hedged Orders: {stats['not_hedged_orders']}")
            self.logger.info(f"   Last Sync: {stats['last_sync']}")
            
            # Log detailed order information
            not_hedged_orders = [o for o in self.order_tracking.values() if o.get('status') == 'NOT_HEDGED']
            if not_hedged_orders:
                self.logger.info("   Orders Needing Recovery:")
                for order in not_hedged_orders[:5]:  # Show max 5
                    ticket = order.get('ticket')
                    symbol = order.get('symbol')
                    order_type = order.get('type')
                    self.logger.info(f"     - {ticket}_{symbol} ({order_type})")
            
            # Log hedged orders
            hedged_orders = [o for o in self.order_tracking.values() if o.get('status') == 'HEDGED']
            if hedged_orders:
                self.logger.info("   Hedged Orders:")
                for order in hedged_orders[:5]:  # Show max 5
                    ticket = order.get('ticket')
                    symbol = order.get('symbol')
                    order_type = order.get('type')
                    recovery_orders = order.get('recovery_orders', [])
                    self.logger.info(f"     - {ticket}_{symbol} ({order_type}) -> {len(recovery_orders)} recovery orders")
    
    def force_reset_all_orders(self):
        """
        Force reset all tracked orders.
        Use with caution - for emergency recovery only.
        """
        with self._lock:
            order_count = len(self.order_tracking)
            self.order_tracking.clear()
            self.logger.warning(f"🚨 FORCE RESET: Cleared {order_count} tracked orders")
    
    def __str__(self) -> str:
        """String representation of the tracker."""
        stats = self.get_statistics()
        return f"IndividualOrderTracker(total={stats['total_tracked_orders']}, original={stats['original_orders']}, recovery={stats['recovery_orders']}, hedged={stats['hedged_orders']})"
