"""
Professional Hedge Tracking System
=================================

A simple, accurate, and reliable position state management system that can precisely 
remember hedge status from order placement to closure.

Key Features:
- Instant Lock: Lock position immediately when hedge order is placed (prevent duplicates)
- Real-time Status: Track actual position status from MT5
- Auto-reset: Automatically reset position to available when hedge is closed
- Continuous Operation: System works continuously without manual intervention

Position Lifecycle:
AVAILABLE → HEDGING → ACTIVE → AVAILABLE (loop)
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
from enum import Enum


class PositionStatus(Enum):
    """Position status enumeration"""
    AVAILABLE = "AVAILABLE"      # Ready to be hedged
    HEDGING = "HEDGING"          # Currently placing hedge order (locked to prevent duplicates)
    ACTIVE = "ACTIVE"            # Hedge order is active in MT5
    ERROR = "ERROR"              # Error state (requires manual intervention)


class ProfessionalHedgeTracker:
    """
    Professional hedge tracking system with simple, reliable state management.
    
    This class replaces the complex multi-layered tracking system with a single
    source of truth for position hedge status.
    """
    
    def __init__(self, broker_api):
        """
        Initialize the professional hedge tracker.
        
        Args:
            broker_api: Broker API instance for MT5 communication
        """
        self.broker = broker_api
        self.logger = logging.getLogger(__name__)
        
        # Single source of truth for position states
        # Key: f"{group_id}:{symbol}", Value: PositionState
        self.positions: Dict[str, Dict] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Performance tracking
        self.stats = {
            'total_locks': 0,
            'total_activations': 0,
            'total_resets': 0,
            'duplicate_prevented': 0,
            'sync_operations': 0,
            'last_sync': None
        }
        
        self.logger.info("🚀 Professional Hedge Tracker initialized")
    
    def lock_position(self, group_id: str, symbol: str) -> bool:
        """
        Lock position immediately when starting to hedge.
        
        This prevents duplicate hedge orders on the same position.
        
        Args:
            group_id: Trading group identifier
            symbol: Currency pair symbol
            
        Returns:
            bool: True if position was successfully locked, False if already locked
        """
        with self._lock:
            position_key = f"{group_id}:{symbol}"
            
            # Check if position is available
            if position_key in self.positions:
                current_status = self.positions[position_key].get('status', PositionStatus.AVAILABLE.value)
                if current_status == PositionStatus.HEDGING.value:
                    self.stats['duplicate_prevented'] += 1
                    self.logger.warning(f"🚫 Position {position_key} already being hedged - preventing duplicate")
                    return False
                elif current_status == PositionStatus.ACTIVE.value:
                    self.stats['duplicate_prevented'] += 1
                    self.logger.warning(f"🚫 Position {position_key} already has active hedge - preventing duplicate")
                    return False
            
            # Lock the position
            self.positions[position_key] = {
                'status': PositionStatus.HEDGING.value,
                'group_id': group_id,
                'symbol': symbol,
                'locked_at': datetime.now(),
                'order_id': None,
                'hedge_symbol': None,
                'activated_at': None,
                'last_sync': datetime.now()
            }
            
            self.stats['total_locks'] += 1
            self.logger.info(f"🔒 Position locked: {position_key}")
            return True
    
    def activate_position(self, group_id: str, symbol: str, order_id: str, hedge_symbol: str) -> bool:
        """
        Mark position as active after successful hedge order.
        
        Args:
            group_id: Trading group identifier
            symbol: Original currency pair symbol
            order_id: MT5 order ID of the hedge position
            hedge_symbol: Currency pair symbol of the hedge position
            
        Returns:
            bool: True if position was successfully activated
        """
        with self._lock:
            position_key = f"{group_id}:{symbol}"
            
            if position_key not in self.positions:
                self.logger.error(f"❌ Cannot activate position {position_key} - not found in tracker")
                return False
            
            current_status = self.positions[position_key].get('status', PositionStatus.AVAILABLE.value)
            if current_status != PositionStatus.HEDGING.value:
                self.logger.error(f"❌ Cannot activate position {position_key} - not in HEDGING state (current: {current_status})")
                return False
            
            # Activate the position
            self.positions[position_key].update({
                'status': PositionStatus.ACTIVE.value,
                'order_id': order_id,
                'hedge_symbol': hedge_symbol,
                'activated_at': datetime.now(),
                'last_sync': datetime.now()
            })
            
            self.stats['total_activations'] += 1
            self.logger.info(f"✅ Position activated: {position_key} -> {hedge_symbol} (Order: {order_id})")
            self.logger.debug(f"🔍 DEBUG: All positions after activation: {self.positions}")
            return True
    
    def reset_position(self, group_id: str, symbol: str) -> bool:
        """
        Reset position to available after hedge closure.
        
        Args:
            group_id: Trading group identifier
            symbol: Currency pair symbol
            
        Returns:
            bool: True if position was successfully reset
        """
        with self._lock:
            position_key = f"{group_id}:{symbol}"
            
            if position_key not in self.positions:
                self.logger.debug(f"Position {position_key} not found in tracker - already available")
                return True
            
            # Get position info before reset
            position_info = self.positions[position_key]
            old_status = position_info.get('status', PositionStatus.AVAILABLE.value)
            hedge_symbol = position_info.get('hedge_symbol', 'Unknown')
            
            # Remove the position (reset to available)
            del self.positions[position_key]
            
            self.stats['total_resets'] += 1
            self.logger.debug(f"🔄 Position reset: {position_key} (was {old_status}, hedge: {hedge_symbol})")
            return True
    
    def is_position_available(self, group_id: str, symbol: str) -> bool:
        """
        Check if position can be hedged.
        
        Args:
            group_id: Trading group identifier
            symbol: Currency pair symbol
            
        Returns:
            bool: True if position is available for hedging
        """
        with self._lock:
            position_key = f"{group_id}:{symbol}"
            
            # Position is available if not in tracker or in ERROR state
            if position_key not in self.positions:
                return True
            
            current_status = self.positions[position_key].get('status', PositionStatus.AVAILABLE.value)
            return current_status == PositionStatus.ERROR.value
    
    def get_position_status(self, group_id: str, symbol: str) -> str:
        """
        Get current position status.
        
        Args:
            group_id: Trading group identifier
            symbol: Currency pair symbol
            
        Returns:
            str: Current position status
        """
        with self._lock:
            position_key = f"{group_id}:{symbol}"
            
            if position_key not in self.positions:
                self.logger.debug(f"🔍 Position {position_key} not found in tracker - returning AVAILABLE")
                return PositionStatus.AVAILABLE.value
            
            status = self.positions[position_key].get('status', PositionStatus.AVAILABLE.value)
            self.logger.debug(f"🔍 Position {position_key} status: {status}")
            return status
    
    def get_position_info(self, group_id: str, symbol: str) -> Optional[Dict]:
        """
        Get detailed position information.
        
        Args:
            group_id: Trading group identifier
            symbol: Currency pair symbol
            
        Returns:
            Dict: Position information or None if not found
        """
        with self._lock:
            position_key = f"{group_id}:{symbol}"
            return self.positions.get(position_key)
    
    def sync_with_mt5(self) -> Dict:
        """
        Sync position status with actual MT5 positions.
        
        This method:
        1. Queries actual positions from MT5
        2. Auto-detects closed positions
        3. Handles connection failures gracefully
        
        Returns:
            Dict: Sync operation results
        """
        with self._lock:
            sync_results = {
                'positions_checked': 0,
                'positions_reset': 0,
                'errors': 0,
                'sync_time': datetime.now()
            }
            
            try:
                # Get all positions from MT5
                all_positions = self.broker.get_all_positions()
                if not all_positions:
                    # If no positions in MT5, check if we have tracked positions that need reset
                    if self.positions:
                        self.logger.warning("⚠️ No positions returned from MT5 during sync - checking tracked positions")
                        # Reset all tracked positions since none exist in MT5
                        for position_key in list(self.positions.keys()):
                            group_id, symbol = position_key.split(':', 1)
                            self.reset_position(group_id, symbol)
                            sync_results['positions_reset'] += 1
                            sync_results['positions_checked'] += 1
                    return sync_results
                
                # Create set of active order IDs for quick lookup
                active_order_ids: Set[str] = set()
                for pos in all_positions:
                    order_id = str(pos.get('ticket', ''))
                    if order_id:
                        active_order_ids.add(order_id)
                
                # Check each tracked position
                positions_to_reset = []
                for position_key, position_info in self.positions.items():
                    sync_results['positions_checked'] += 1
                    
                    order_id = position_info.get('order_id')
                    if not order_id:
                        continue
                    
                    # Check if hedge order is still active in MT5
                    if order_id not in active_order_ids:
                        # Position is closed - mark for reset
                        positions_to_reset.append(position_key)
                        sync_results['positions_reset'] += 1
                        self.logger.debug(f"🔄 Position {position_key} (Order: {order_id}) not found in MT5 - will reset")
                    else:
                        self.logger.debug(f"✅ Position {position_key} (Order: {order_id}) still active in MT5")
                
                # Reset closed positions
                for position_key in positions_to_reset:
                    group_id, symbol = position_key.split(':', 1)
                    self.reset_position(group_id, symbol)
                
                self.stats['sync_operations'] += 1
                self.stats['last_sync'] = datetime.now()
                
                if sync_results['positions_reset'] > 0:
                    self.logger.info(f"🔄 Sync completed: {sync_results['positions_checked']} checked, {sync_results['positions_reset']} reset")
                
            except Exception as e:
                sync_results['errors'] += 1
                self.logger.error(f"❌ Error during MT5 sync: {e}")
            
            return sync_results
    
    def get_all_positions(self) -> Dict[str, Dict]:
        """
        Get all tracked positions.
        
        Returns:
            Dict: All tracked positions
        """
        with self._lock:
            return self.positions.copy()
    
    def get_positions_by_status(self, status: PositionStatus) -> Dict[str, Dict]:
        """
        Get positions filtered by status.
        
        Args:
            status: Position status to filter by
            
        Returns:
            Dict: Positions with the specified status
        """
        with self._lock:
            filtered_positions = {}
            for position_key, position_info in self.positions.items():
                if position_info.get('status') == status.value:
                    filtered_positions[position_key] = position_info
            return filtered_positions
    
    def get_statistics(self) -> Dict:
        """
        Get tracker statistics.
        
        Returns:
            Dict: Tracker statistics
        """
        with self._lock:
            stats = self.stats.copy()
            stats.update({
                'total_tracked_positions': len(self.positions),
                'available_positions': len(self.get_positions_by_status(PositionStatus.AVAILABLE)),
                'hedging_positions': len(self.get_positions_by_status(PositionStatus.HEDGING)),
                'active_positions': len(self.get_positions_by_status(PositionStatus.ACTIVE)),
                'error_positions': len(self.get_positions_by_status(PositionStatus.ERROR))
            })
            return stats
    
    def log_status_summary(self):
        """Log a summary of all tracked positions."""
        with self._lock:
            stats = self.get_statistics()
            
            self.logger.info("📊 HEDGE TRACKER STATUS SUMMARY:")
            self.logger.info(f"   Total Tracked: {stats['total_tracked_positions']}")
            self.logger.info(f"   Active Hedges: {stats['active_positions']}")
            self.logger.info(f"   Currently Hedging: {stats['hedging_positions']}")
            self.logger.info(f"   Error States: {stats['error_positions']}")
            self.logger.info(f"   Duplicates Prevented: {stats['duplicate_prevented']}")
            self.logger.info(f"   Last Sync: {stats['last_sync']}")
            
            # Log active positions details
            active_positions = self.get_positions_by_status(PositionStatus.ACTIVE)
            if active_positions:
                self.logger.info("   Active Hedges:")
                for position_key, info in active_positions.items():
                    hedge_symbol = info.get('hedge_symbol', 'Unknown')
                    order_id = info.get('order_id', 'Unknown')
                    activated_at = info.get('activated_at', 'Unknown')
                    self.logger.info(f"     - {position_key} -> {hedge_symbol} (Order: {order_id}, Since: {activated_at})")
    
    def cleanup_stale_positions(self, max_age_hours: int = 24):
        """
        Clean up positions that have been stuck in HEDGING state for too long.
        
        Args:
            max_age_hours: Maximum age in hours before considering position stale
        """
        with self._lock:
            current_time = datetime.now()
            stale_positions = []
            
            for position_key, position_info in self.positions.items():
                status = position_info.get('status', PositionStatus.AVAILABLE.value)
                if status == PositionStatus.HEDGING.value:
                    locked_at = position_info.get('locked_at')
                    if locked_at and (current_time - locked_at).total_seconds() > max_age_hours * 3600:
                        stale_positions.append(position_key)
            
            for position_key in stale_positions:
                group_id, symbol = position_key.split(':', 1)
                self.logger.warning(f"🧹 Cleaning up stale position: {position_key}")
                self.reset_position(group_id, symbol)
            
            if stale_positions:
                self.logger.info(f"🧹 Cleaned up {len(stale_positions)} stale positions")
    
    def force_reset_all_positions(self):
        """
        Force reset all positions to available state.
        Use with caution - this should only be used for emergency recovery.
        """
        with self._lock:
            position_count = len(self.positions)
            self.positions.clear()
            self.logger.warning(f"🚨 FORCE RESET: Cleared {position_count} tracked positions")
    
    def __str__(self) -> str:
        """String representation of the tracker."""
        stats = self.get_statistics()
        return f"ProfessionalHedgeTracker(positions={stats['total_tracked_positions']}, active={stats['active_positions']}, duplicates_prevented={stats['duplicate_prevented']})"
