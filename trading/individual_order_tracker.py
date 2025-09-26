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
import json
import os
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
        
        # Persistence file
        self.persistence_file = "data/order_tracking.json"
        
        # Load existing data on startup
        self._load_from_file()
        
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
            
            # Save to file
            self._save_to_file()
            
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
            
            # Save to file
            self._save_to_file()
            
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
            List[Dict]: Orders with status NOT_HEDGED or ORPHANED
        """
        with self._lock:
            needing_recovery = []
            for order_key, order_info in self.order_tracking.items():
                status = order_info.get("status")
                if status in ["NOT_HEDGED", "ORPHANED"]:
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
                        # Order is closed - check if it was hedged
                        order_type = order_info.get('type', 'UNKNOWN')
                        status = order_info.get('status', 'UNKNOWN')
                        
                        if order_type == 'ORIGINAL' and status == 'HEDGED':
                            # Original order that was hedged is closed - need to handle recovery orders
                            recovery_orders = order_info.get('recovery_orders', [])
                            self.logger.warning(f"🚨 HEDGED ORIGINAL ORDER CLOSED: {order_key} had {len(recovery_orders)} recovery orders")
                            
                            # Check if recovery orders are still active
                            active_recovery_orders = []
                            for recovery_key in recovery_orders:
                                if recovery_key in self.order_tracking:
                                    recovery_info = self.order_tracking[recovery_key]
                                    recovery_ticket = recovery_info.get('ticket')
                                    if recovery_ticket and recovery_ticket in active_tickets:
                                        active_recovery_orders.append(recovery_key)
                            
                            if active_recovery_orders:
                                self.logger.warning(f"⚠️ {len(active_recovery_orders)} recovery orders still active - they will become orphaned")
                                # Mark recovery orders as orphaned (no original order to hedge)
                                for recovery_key in active_recovery_orders:
                                    if recovery_key in self.order_tracking:
                                        self.order_tracking[recovery_key]['status'] = 'ORPHANED'
                                        self.logger.warning(f"🔗 Marked {recovery_key} as ORPHANED")
                            
                        elif order_type == 'RECOVERY':
                            # Recovery order is closed - check if original is still active
                            hedging_for = order_info.get('hedging_for', '')
                            if hedging_for and hedging_for in self.order_tracking:
                                original_info = self.order_tracking[hedging_for]
                                original_ticket = original_info.get('ticket')
                                if original_ticket and original_ticket in active_tickets:
                                    # Original order still active - mark as not hedged
                                    self.order_tracking[hedging_for]['status'] = 'NOT_HEDGED'
                                    self.logger.warning(f"🔗 Original order {hedging_for} marked as NOT_HEDGED (recovery order closed)")
                        
                        # Mark for removal
                        orders_to_remove.append(order_key)
                        sync_results['orders_removed'] += 1
                        self.logger.info(f"🔄 Order {order_key} (Ticket: {ticket}) closed - removed from tracking")
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
                    # Save to file after removing closed orders
                    self._save_to_file()
                
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
                'not_hedged_orders': len([o for o in self.order_tracking.values() if o.get('status') == 'NOT_HEDGED']),
                'orphaned_orders': len([o for o in self.order_tracking.values() if o.get('status') == 'ORPHANED'])
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
            self.logger.info(f"   Orphaned Orders: {stats['orphaned_orders']}")
            self.logger.info(f"   Last Sync: {stats['last_sync']}")
            
    
    def force_reset_all_orders(self):
        """
        Force reset all tracked orders.
        Use with caution - for emergency recovery only.
        """
        with self._lock:
            order_count = len(self.order_tracking)
            self.order_tracking.clear()
            
            # Reset statistics
            self.stats = {
                'original_orders_registered': 0,
                'recovery_orders_registered': 0,
                'orders_hedged': 0,
                'orders_removed': 0,
                'sync_operations': 0,
                'last_sync': None
            }
            
            self.logger.warning(f"🚨 FORCE RESET: Cleared {order_count} tracked orders and reset statistics")
            
            # Save to file after clearing
            self._save_to_file()
    
    def _save_to_file(self):
        """Save order tracking data to file"""
        try:
            with self._lock:
                # Ensure data directory exists
                os.makedirs(os.path.dirname(self.persistence_file), exist_ok=True)
                
                # Convert datetime objects to strings for JSON serialization
                data_to_save = {}
                for key, order_info in self.order_tracking.items():
                    data_to_save[key] = order_info.copy()
                    # Convert datetime objects to ISO format strings
                    if 'created_at' in data_to_save[key] and isinstance(data_to_save[key]['created_at'], datetime):
                        data_to_save[key]['created_at'] = data_to_save[key]['created_at'].isoformat()
                    if 'last_sync' in data_to_save[key] and isinstance(data_to_save[key]['last_sync'], datetime):
                        data_to_save[key]['last_sync'] = data_to_save[key]['last_sync'].isoformat()
                
                # Convert stats datetime objects to strings
                stats_to_save = self.stats.copy()
                if 'last_sync' in stats_to_save and isinstance(stats_to_save['last_sync'], datetime):
                    stats_to_save['last_sync'] = stats_to_save['last_sync'].isoformat()
                
                # Save to file
                with open(self.persistence_file, 'w') as f:
                    json.dump({
                        'order_tracking': data_to_save,
                        'stats': stats_to_save,
                        'saved_at': datetime.now().isoformat()
                    }, f, indent=2)
                
                self.logger.debug(f"💾 Saved order tracking data to {self.persistence_file}")
                
        except Exception as e:
            self.logger.error(f"Error saving order tracking data: {e}")
    
    def _load_from_file(self):
        """Load order tracking data from file"""
        try:
            if not os.path.exists(self.persistence_file):
                self.logger.info("📁 No existing order tracking file found - starting fresh")
                return
            
            with open(self.persistence_file, 'r') as f:
                data = json.load(f)
            
            # Load order tracking data
            if 'order_tracking' in data:
                for key, order_info in data['order_tracking'].items():
                    # Convert ISO format strings back to datetime objects
                    if 'created_at' in order_info and isinstance(order_info['created_at'], str):
                        order_info['created_at'] = datetime.fromisoformat(order_info['created_at'])
                    if 'last_sync' in order_info and isinstance(order_info['last_sync'], str):
                        order_info['last_sync'] = datetime.fromisoformat(order_info['last_sync'])
                    
                    self.order_tracking[key] = order_info
            
            # Load stats
            if 'stats' in data:
                self.stats.update(data['stats'])
            
            # Convert last_sync from string to datetime if needed
            if 'last_sync' in self.stats and isinstance(self.stats['last_sync'], str):
                self.stats['last_sync'] = datetime.fromisoformat(self.stats['last_sync'])
            
            loaded_count = len(self.order_tracking)
            self.logger.info(f"📁 Loaded {loaded_count} orders from {self.persistence_file}")
            
        except Exception as e:
            self.logger.error(f"Error loading order tracking data: {e}")
    
    def __str__(self) -> str:
        """String representation of the tracker."""
        stats = self.get_statistics()
        return f"IndividualOrderTracker(total={stats['total_tracked_orders']}, original={stats['original_orders']}, recovery={stats['recovery_orders']}, hedged={stats['hedged_orders']})"
