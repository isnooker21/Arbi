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
        
        # 🆕 Smart Recovery Priority Queue
        # Priority based on loss amount and urgency
        self.recovery_priority_queue: List[Dict] = []
        
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
    
    def is_order_tracked(self, ticket: str, symbol: str) -> bool:
        """
        Check if an order is already tracked.
        
        Args:
            ticket: Order ticket
            symbol: Currency pair symbol
            
        Returns:
            bool: True if order is tracked
        """
        with self._lock:
            order_key = f"{ticket}_{symbol}"
            return order_key in self.order_tracking
    
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
        Auto-register existing positions that aren't tracked.
        
        Returns:
            Dict: Sync operation results
        """
        with self._lock:
            sync_results = {
                'orders_checked': 0,
                'orders_removed': 0,
                'orders_auto_registered': 0,
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
                
                # 🆕 AUTO-REGISTER existing positions that aren't tracked
                for pos in all_positions:
                    ticket = str(pos.get('ticket', ''))
                    symbol = pos.get('symbol', '')
                    comment = pos.get('comment', '')
                    
                    if ticket and symbol:
                        order_key = f"{ticket}_{symbol}"
                        
                        # Check if this order is already tracked
                        if order_key not in self.order_tracking:
                            # Determine order type from comment
                            is_recovery = self._is_recovery_comment(comment)
                            order_type = "RECOVERY" if is_recovery else "ORIGINAL"
                            
                            # Auto-register order
                            group_id = self._extract_group_from_comment(comment, symbol)
                            
                            order_data = {
                                "ticket": ticket,
                                "symbol": symbol,
                                "group_id": group_id,
                                "type": order_type,
                                "status": "NOT_HEDGED",
                                "recovery_orders": [],
                                "created_at": datetime.now(),
                                "last_sync": datetime.now(),
                                "auto_registered": True,  # Flag to indicate this was auto-registered
                                "comment": comment  # Store original comment
                            }
                            
                            # For recovery orders, try to find the original order they're hedging
                            if is_recovery:
                                original_order_key = self._find_original_order_for_recovery(order_data)
                                if original_order_key:
                                    order_data["hedging_for"] = original_order_key
                                    # Update original order's recovery list
                                    if original_order_key in self.order_tracking:
                                        if order_key not in self.order_tracking[original_order_key].get("recovery_orders", []):
                                            self.order_tracking[original_order_key].setdefault("recovery_orders", []).append(order_key)
                                            # Mark original as hedged
                                            self.order_tracking[original_order_key]["status"] = "HEDGED"
                                    order_data["status"] = "HEDGED"
                                else:
                                    order_data["status"] = "ORPHANED"  # Recovery without original
                            
                            self.order_tracking[order_key] = order_data
                            
                            if is_recovery:
                                self.stats['recovery_orders_registered'] += 1
                                self.logger.info(f"🔄 Auto-registered existing RECOVERY position: {order_key} in {group_id}")
                            else:
                                self.stats['original_orders_registered'] += 1
                                self.logger.info(f"🔄 Auto-registered existing ORIGINAL position: {order_key} in {group_id}")
                            
                            sync_results['orders_auto_registered'] += 1
                
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
                
                if sync_results['orders_removed'] > 0 or sync_results['orders_auto_registered'] > 0:
                    self.logger.info(f"🔄 Sync completed: {sync_results['orders_checked']} checked, {sync_results['orders_removed']} removed, {sync_results['orders_auto_registered']} auto-registered")
                    # Save to file after changes
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
            # Calculate current statistics from actual data
            total_tracked = len(self.order_tracking)
            original_orders = len([o for o in self.order_tracking.values() if o.get('type') == 'ORIGINAL'])
            recovery_orders = len([o for o in self.order_tracking.values() if o.get('type') == 'RECOVERY'])
            
            # Count hedged orders (only ORIGINAL orders that are HEDGED)
            hedged_orders = len([o for o in self.order_tracking.values() 
                               if o.get('type') == 'ORIGINAL' and o.get('status') == 'HEDGED'])
            
            # Count not hedged orders (only ORIGINAL orders that are NOT_HEDGED)
            not_hedged_orders = len([o for o in self.order_tracking.values() 
                                   if o.get('type') == 'ORIGINAL' and o.get('status') == 'NOT_HEDGED'])
            
            # Count orphaned orders
            orphaned_orders = len([o for o in self.order_tracking.values() if o.get('status') == 'ORPHANED'])
            
            # Return current statistics (not accumulated)
            return {
                'total_tracked_orders': total_tracked,
                'original_orders': original_orders,
                'recovery_orders': recovery_orders,
                'hedged_orders': hedged_orders,
                'not_hedged_orders': not_hedged_orders,
                'orphaned_orders': orphaned_orders,
                'priority_queue_size': len(self.recovery_priority_queue),
                'last_sync': self.stats.get('last_sync'),
                # Keep accumulated stats for reference
                'total_original_registered': self.stats.get('original_orders_registered', 0),
                'total_recovery_registered': self.stats.get('recovery_orders_registered', 0),
                'total_orders_removed': self.stats.get('orders_removed', 0),
                'total_sync_operations': self.stats.get('sync_operations', 0)
            }
    
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
            
            # Show accumulated statistics for reference
            if stats.get('total_original_registered', 0) > 0:
                self.logger.info("📈 ACCUMULATED STATISTICS:")
                self.logger.info(f"   Total Original Registered: {stats['total_original_registered']}")
                self.logger.info(f"   Total Recovery Registered: {stats['total_recovery_registered']}")
                self.logger.info(f"   Total Orders Removed: {stats['total_orders_removed']}")
                self.logger.info(f"   Total Sync Operations: {stats['total_sync_operations']}")
            
    
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
            
            # Clear priority queue
            self.recovery_priority_queue.clear()
            
            # Save to file after clearing
            self._save_to_file()
    
    def _extract_group_from_comment(self, comment: str, symbol: str) -> str:
        """
        Extract group ID from comment or generate one based on symbol.
        
        Args:
            comment: MT5 position comment
            symbol: Currency pair symbol
            
        Returns:
            str: Group ID
        """
        try:
            if comment:
                # Try to extract group from comment patterns like "G1_EURUSD", "group_triangle_1_1", etc.
                if comment.startswith('G'):
                    # Pattern: G1_EURUSD, G2_GBPUSD, etc.
                    parts = comment.split('_')
                    if len(parts) >= 1:
                        group_part = parts[0]
                        if group_part.startswith('G') and len(group_part) > 1:
                            group_num = group_part[1:]
                            try:
                                group_num = int(group_num)
                                return f"G{group_num}"
                            except ValueError:
                                pass
                
                elif 'group_' in comment:
                    # Pattern: group_triangle_1_1, group_triangle_2_1, etc.
                    parts = comment.split('_')
                    if len(parts) >= 3:
                        triangle_type = parts[1]  # triangle_1, triangle_2, etc.
                        group_num = parts[2]
                        return f"G{group_num}"
            
            # Fallback: Generate group based on symbol
            # Map major currency pairs to groups
            major_pairs = {
                'EURUSD': 'G1', 'GBPUSD': 'G1', 'EURGBP': 'G1',
                'EURUSD': 'G2', 'USDCHF': 'G2', 'EURCHF': 'G2', 
                'GBPUSD': 'G3', 'USDJPY': 'G3', 'GBPJPY': 'G3',
                'AUDUSD': 'G4', 'USDCAD': 'G4', 'AUDCAD': 'G4',
                'NZDUSD': 'G5', 'USDCHF': 'G5', 'NZDCHF': 'G5',
                'AUDUSD': 'G6', 'NZDUSD': 'G6', 'AUDNZD': 'G6'
            }
            
            # Clean symbol (remove broker suffixes)
            clean_symbol = symbol.replace('.v', '').replace('.m', '').replace('p', '').replace('a', '')
            return major_pairs.get(clean_symbol, 'G1')  # Default to G1
            
        except Exception as e:
            self.logger.debug(f"Error extracting group from comment '{comment}': {e}")
            return 'G1'  # Default fallback
    
    def _is_recovery_comment(self, comment: str) -> bool:
        """
        Check if comment indicates a recovery order.
        
        Args:
            comment: MT5 position comment
            
        Returns:
            bool: True if this is a recovery order
        """
        if not comment:
            return False
        
        # Check for recovery patterns
        return (comment.startswith('RECOVERY_') or 
                comment.startswith('R') or
                'RECOVERY' in comment.upper())
    
    def _find_original_order_for_recovery(self, recovery_order: Dict) -> Optional[str]:
        """
        Try to find the original order that this recovery order is hedging.
        
        Args:
            recovery_order: Recovery order data
            
        Returns:
            Optional[str]: Original order key if found, None otherwise
        """
        try:
            comment = recovery_order.get('comment', '')
            symbol = recovery_order.get('symbol', '')
            group_id = recovery_order.get('group_id', '')
            
            if not comment:
                return None
            
            # ✅ Parse recovery comment patterns
            # NEW FORMAT: R{ticket}_{symbol} (e.g., R3317086_EURUSD)
            # LEGACY: RECOVERY_G6_EURUSD_TO_GBPUSD_L1 (old format, still supported)
            
            if comment.startswith('R') and '_' in comment and not comment.startswith('RECOVERY_'):
                # NEW SHORT FORMAT: R3317086_EURUSD
                parts = comment.split('_')
                if len(parts) >= 2:
                    ticket_part = parts[0][1:]  # Remove 'R' prefix
                    # The ticket part should be in our tracking
                    # Look for original order with this ticket
                    for order_key, order_info in self.order_tracking.items():
                        if (order_info.get('ticket', '').endswith(ticket_part) and
                            order_info.get('type') == 'ORIGINAL'):
                            return order_key
            
            elif comment.startswith('RECOVERY_'):
                # LEGACY FORMAT: RECOVERY_G6_EURUSD_TO_GBPUSD_L1
                # Extract original symbol from comment
                parts = comment.split('_')
                if len(parts) >= 3:
                    group_part = parts[1]  # G6
                    original_symbol_part = parts[2]  # EURUSD
                    
                    # Clean original symbol
                    original_symbol = original_symbol_part.replace('TO', '').replace('L1', '').replace('L2', '')
                    
                    # Look for original order in same group
                    for order_key, order_info in self.order_tracking.items():
                        if (order_info.get('group_id') == group_id and
                            order_info.get('symbol') == original_symbol and
                            order_info.get('type') == 'ORIGINAL'):
                            return order_key
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error finding original order for recovery: {e}")
            return None
    
    def _symbols_match(self, sym1: str, sym2: str) -> bool:
        """
        Check if two symbols match (ignoring broker suffixes).
        
        Args:
            sym1: First symbol
            sym2: Second symbol
            
        Returns:
            bool: True if symbols match
        """
        if not sym1 or not sym2:
            return False
        
        # Clean symbols by removing common broker suffixes
        clean1 = sym1.replace('.v', '').replace('.m', '').replace('p', '').replace('a', '')
        clean2 = sym2.replace('.v', '').replace('.m', '').replace('p', '').replace('a', '')
        
        return clean1 == clean2
    
    # 🆕 Smart Recovery Priority Queue Methods
    
    def add_to_priority_queue(self, order_key: str, priority_score: float, order_data: Dict):
        """
        Add order to priority queue for Smart Recovery.
        
        Args:
            order_key: Order key (ticket_symbol)
            priority_score: Priority score (higher = more urgent)
            order_data: Order information
        """
        with self._lock:
            # Remove if already exists
            self.recovery_priority_queue = [item for item in self.recovery_priority_queue 
                                          if item.get('order_key') != order_key]
            
            # Add new item
            queue_item = {
                'order_key': order_key,
                'priority_score': priority_score,
                'order_data': order_data,
                'added_at': datetime.now()
            }
            
            self.recovery_priority_queue.append(queue_item)
            
            # Sort by priority (highest first)
            self.recovery_priority_queue.sort(key=lambda x: x['priority_score'], reverse=True)
            
            self.logger.debug(f"🎯 Added {order_key} to priority queue (score: {priority_score:.2f})")
    
    def get_next_priority_order(self) -> Optional[Dict]:
        """
        Get the next highest priority order from queue.
        
        Returns:
            Optional[Dict]: Next priority order or None if queue is empty
        """
        with self._lock:
            if not self.recovery_priority_queue:
                return None
            
            # Get highest priority item
            next_item = self.recovery_priority_queue[0]
            
            # Remove from queue
            self.recovery_priority_queue.pop(0)
            
            return next_item
    
    def clear_priority_queue(self):
        """Clear the priority queue."""
        with self._lock:
            queue_size = len(self.recovery_priority_queue)
            self.recovery_priority_queue.clear()
            if queue_size > 0:
                self.logger.info(f"🧹 Cleared {queue_size} items from priority queue")
    
    def get_priority_queue_status(self) -> Dict:
        """
        Get priority queue status.
        
        Returns:
            Dict: Queue status information
        """
        with self._lock:
            if not self.recovery_priority_queue:
                return {'size': 0, 'top_priority': None}
            
            top_item = self.recovery_priority_queue[0]
            return {
                'size': len(self.recovery_priority_queue),
                'top_priority': {
                    'order_key': top_item['order_key'],
                    'priority_score': top_item['priority_score'],
                    'added_at': top_item['added_at']
                }
            }
    
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
                        try:
                            order_info['created_at'] = datetime.fromisoformat(order_info['created_at'])
                        except ValueError:
                            order_info['created_at'] = datetime.now()
                    if 'last_sync' in order_info and isinstance(order_info['last_sync'], str):
                        try:
                            order_info['last_sync'] = datetime.fromisoformat(order_info['last_sync'])
                        except ValueError:
                            order_info['last_sync'] = datetime.now()
                    
                    self.order_tracking[key] = order_info
            
            # Load stats
            if 'stats' in data:
                self.stats.update(data['stats'])
            
            # Convert last_sync from string to datetime if needed
            if 'last_sync' in self.stats and isinstance(self.stats['last_sync'], str):
                try:
                    self.stats['last_sync'] = datetime.fromisoformat(self.stats['last_sync'])
                except ValueError:
                    self.stats['last_sync'] = datetime.now()
            
            loaded_count = len(self.order_tracking)
            self.logger.info(f"📁 Loaded {loaded_count} orders from {self.persistence_file}")
            
        except Exception as e:
            self.logger.error(f"Error loading order tracking data: {e}")
    
    def __str__(self) -> str:
        """String representation of the tracker."""
        stats = self.get_statistics()
        return f"IndividualOrderTracker(total={stats['total_tracked_orders']}, original={stats['original_orders']}, recovery={stats['recovery_orders']}, hedged={stats['hedged_orders']})"
