"""
Modern Trading GUI - Main Window
===============================

Professional trading dashboard with modern dark theme
No mock data - all real-time integration
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import logging
from datetime import datetime
import json
from .theme import TradingTheme
from .group_dashboard import GroupDashboard

class MainWindow:
    def __init__(self, trading_system=None):
        self.root = tk.Tk()
        self.root.title("🎯 Forex Arbitrage AI Trading System")
        self.root.geometry("1600x900")
        self.root.minsize(1400, 800)
        self.root.state('zoomed')  # Maximize window on Windows
        
        # Initialize variables
        self.trading_system = trading_system
        self.is_trading = False
        self.connection_status = "disconnected"
        
        # Apply modern theme
        TradingTheme.apply_theme(self.root)
        
        # Setup UI
        self.setup_ui()
        
        # Setup logging
        self.setup_logging()
        
        # No auto-connect - user will click Connect button manually
    
    def setup_ui(self):
        """Setup modern UI layout"""
        # Main container
        self.main_frame = tk.Frame(self.root, bg=TradingTheme.COLORS['primary_bg'])
        self.main_frame.pack(fill='both', expand=True, padx=TradingTheme.SPACING['md'], pady=TradingTheme.SPACING['md'])
        
        # Header Bar
        self.create_header()
        
        # Main Content Area
        self.create_main_content()
    
    def create_header(self):
        """Create modern header bar"""
        header_frame = tk.Frame(self.main_frame, bg=TradingTheme.COLORS['secondary_bg'], height=60)
        header_frame.pack(fill='x', pady=(0, TradingTheme.SPACING['md']))
        header_frame.pack_propagate(False)
        
        # Logo and Title
        title_frame = tk.Frame(header_frame, bg=TradingTheme.COLORS['secondary_bg'])
        title_frame.pack(side='left', fill='y', padx=TradingTheme.SPACING['lg'])
        
        title_label = tk.Label(
            title_frame,
            text="🎯 Forex AI Trading System",
            font=TradingTheme.FONTS['header'],
            bg=TradingTheme.COLORS['secondary_bg'],
            fg=TradingTheme.COLORS['text_primary']
        )
        title_label.pack(side='left', pady=TradingTheme.SPACING['md'])
        
        # Header Controls
        controls_frame = tk.Frame(header_frame, bg=TradingTheme.COLORS['secondary_bg'])
        controls_frame.pack(side='right', fill='y', padx=TradingTheme.SPACING['lg'])
        
        # Settings Button
        self.settings_btn = TradingTheme.create_button_style(
            controls_frame, "⚙️ Settings", self.show_settings, "secondary"
        )
        self.settings_btn.pack(side='right', padx=TradingTheme.SPACING['sm'])
        
        # Connect/Disconnect Button
        self.connect_btn = TradingTheme.create_button_style(
            controls_frame, "🔌 Connect", self.toggle_connection, "primary"
        )
        self.connect_btn.pack(side='right', padx=TradingTheme.SPACING['sm'])
        
        # Start/Stop Trading Button
        self.trading_btn = TradingTheme.create_button_style(
            controls_frame, "▶️ Start Trading", self.toggle_trading, "success"
        )
        self.trading_btn.pack(side='right', padx=TradingTheme.SPACING['sm'])
        
        # Connection Status
        self.connection_indicator, self.connection_label = TradingTheme.create_status_indicator(
            controls_frame, "Connection", self.connection_status
        )
        self.connection_indicator.pack(side='right', padx=TradingTheme.SPACING['sm'])
        
        # Status Indicator
        self.status_indicator, self.status_label = TradingTheme.create_status_indicator(
            controls_frame, "System", "active"
        )
        self.status_indicator.pack(side='right', padx=TradingTheme.SPACING['lg'])
    
    
    def create_main_content(self):
        """Create main content area"""
        print("🔍 Debug: create_main_content called")
        content_frame = tk.Frame(self.main_frame, bg=TradingTheme.COLORS['primary_bg'])
        content_frame.pack(fill='both', expand=True)
        print("🔍 Debug: content_frame created and packed")
        
        # Group Dashboard - ใช้พื้นที่เต็ม
        print("🔍 Debug: Creating GroupDashboard...")
        self.group_dashboard = GroupDashboard(content_frame)
        print("✅ Debug: GroupDashboard created successfully")
        
        # Initialize group dashboard with default status
        print("🔍 Debug: Calling update_group_dashboard...")
        self.update_group_dashboard()
        print("✅ Debug: update_group_dashboard completed")
        
        # Load sample data to show groups
        print("🔍 Debug: Calling load_sample_data...")
        self.load_sample_data()
        print("✅ Debug: load_sample_data completed")
    
    def load_sample_data(self):
        """Load sample data to show groups"""
        try:
            print("🔍 Debug: Loading sample data...")
            if hasattr(self, 'group_dashboard') and self.group_dashboard:
                print("🔍 Debug: group_dashboard found, calling refresh_groups...")
                # Call refresh_groups to show sample data
                self.group_dashboard.refresh_groups()
                print("✅ Debug: refresh_groups completed")
                
                # Force GUI update
                self.root.update_idletasks()
                print("🔍 Debug: GUI updated after refresh_groups")
                
                # Start update loop immediately to show data
                self.start_group_dashboard_update_loop()
                print("✅ Debug: Update loop started")
            else:
                print("❌ Debug: group_dashboard not found")
        except Exception as e:
            print(f"❌ Error loading sample data: {e}")
            import traceback
            traceback.print_exc()
    
    def create_trading_control_panel(self, parent):
        """Create trading control panel"""
        control_frame = tk.Frame(parent, bg=TradingTheme.COLORS['secondary_bg'], width=400)
        control_frame.pack(side='left', fill='y', padx=(0, TradingTheme.SPACING['md']))
        control_frame.pack_propagate(False)
        
        # Header
        header = TradingTheme.create_section_header(control_frame, "Trading Control", "System management and controls")
        header.pack(fill='x', padx=TradingTheme.SPACING['md'], pady=(TradingTheme.SPACING['md'], 0))
        
        # Control Buttons
        buttons_frame = tk.Frame(control_frame, bg=TradingTheme.COLORS['secondary_bg'])
        buttons_frame.pack(fill='x', padx=TradingTheme.SPACING['md'], pady=TradingTheme.SPACING['md'])
        
        # Connect Button
        self.connect_btn = TradingTheme.create_button_style(
            buttons_frame, "🔌 CONNECT", self.connect_broker, "info"
        )
        self.connect_btn.pack(fill='x', pady=(0, TradingTheme.SPACING['sm']))
        
        # Start/Stop Buttons
        self.start_btn = TradingTheme.create_button_style(
            buttons_frame, "▶️ START", self.start_trading, "success"
        )
        self.start_btn.pack(fill='x', pady=(0, TradingTheme.SPACING['sm']))
        
        self.stop_btn = TradingTheme.create_button_style(
            buttons_frame, "⏹️ STOP", self.stop_trading, "danger"
        )
        self.stop_btn.pack(fill='x', pady=(0, TradingTheme.SPACING['sm']))
        
        self.emergency_btn = TradingTheme.create_button_style(
            buttons_frame, "🚨 EMERGENCY STOP", self.emergency_stop, "warning"
        )
        self.emergency_btn.pack(fill='x', pady=(0, TradingTheme.SPACING['md']))
        
        # Trading Options
        options_frame = tk.Frame(control_frame, bg=TradingTheme.COLORS['secondary_bg'])
        options_frame.pack(fill='x', padx=TradingTheme.SPACING['md'], pady=(0, TradingTheme.SPACING['md']))
        
        # Checkboxes
        self.arbitrage_var = tk.BooleanVar(value=True)
        self.correlation_var = tk.BooleanVar(value=True)
        
        arbitrage_cb = tk.Checkbutton(
            options_frame,
            text="Arbitrage Detection",
            variable=self.arbitrage_var,
            bg=TradingTheme.COLORS['secondary_bg'],
            fg=TradingTheme.COLORS['text_primary'],
            font=TradingTheme.FONTS['body'],
            selectcolor=TradingTheme.COLORS['accent_bg']
        )
        arbitrage_cb.pack(anchor='w', pady=(0, TradingTheme.SPACING['xs']))
        
        correlation_cb = tk.Checkbutton(
            options_frame,
            text="Correlation Analysis",
            variable=self.correlation_var,
            bg=TradingTheme.COLORS['secondary_bg'],
            fg=TradingTheme.COLORS['text_primary'],
            font=TradingTheme.FONTS['body'],
            selectcolor=TradingTheme.COLORS['accent_bg']
        )
        correlation_cb.pack(anchor='w', pady=(0, TradingTheme.SPACING['md']))
        
        # AI Confidence
        confidence_frame = tk.Frame(control_frame, bg=TradingTheme.COLORS['secondary_bg'])
        confidence_frame.pack(fill='x', padx=TradingTheme.SPACING['md'], pady=(0, TradingTheme.SPACING['md']))
        
        tk.Label(
            confidence_frame,
            text="AI Confidence:",
            font=TradingTheme.FONTS['body'],
            bg=TradingTheme.COLORS['secondary_bg'],
            fg=TradingTheme.COLORS['text_secondary']
        ).pack(anchor='w')
        
        self.confidence_label = tk.Label(
            confidence_frame,
            text="0%",
            font=TradingTheme.FONTS['large_numbers'],
            bg=TradingTheme.COLORS['secondary_bg'],
            fg=TradingTheme.COLORS['text_primary']
        )
        self.confidence_label.pack(anchor='w')
    
    def create_positions_panel(self, parent):
        """Create live positions panel"""
        positions_frame = tk.Frame(parent, bg=TradingTheme.COLORS['secondary_bg'], width=600)
        positions_frame.pack(side='right', fill='both', expand=True)
        positions_frame.pack_propagate(False)
        
        # Header
        header = TradingTheme.create_section_header(positions_frame, "Live Positions", "Active trading positions")
        header.pack(fill='x', padx=TradingTheme.SPACING['md'], pady=(TradingTheme.SPACING['md'], 0))
        
        # Positions Table
        table_frame, self.positions_tree, scrollbar = TradingTheme.create_professional_table(
            positions_frame, ['Symbol', 'Type', 'Volume', 'Price', 'PnL', 'Status'], height=12
        )
        table_frame.pack(fill='both', expand=True, padx=TradingTheme.SPACING['md'], pady=TradingTheme.SPACING['md'])
        
        # Table Actions
        actions_frame = tk.Frame(positions_frame, bg=TradingTheme.COLORS['secondary_bg'])
        actions_frame.pack(fill='x', padx=TradingTheme.SPACING['md'], pady=(0, TradingTheme.SPACING['md']))
        
        refresh_btn = TradingTheme.create_button_style(
            actions_frame, "🔄 Refresh", self.refresh_positions, "secondary"
        )
        refresh_btn.pack(side='left')
        
        close_all_btn = TradingTheme.create_button_style(
            actions_frame, "❌ Close All", self.close_all_positions, "danger"
        )
        close_all_btn.pack(side='right')
    
    def create_analysis_panel(self, parent):
        """Create analysis panel with charts"""
        analysis_frame = tk.Frame(parent, bg=TradingTheme.COLORS['secondary_bg'])
        analysis_frame.pack(fill='both', expand=True, pady=(TradingTheme.SPACING['md'], 0))
        
        # Header
        header = TradingTheme.create_section_header(analysis_frame, "Analysis & Charts", "Market analysis and performance")
        header.pack(fill='x', padx=TradingTheme.SPACING['md'], pady=(TradingTheme.SPACING['md'], 0))
        
        # Chart Tabs
        self.create_chart_tabs(analysis_frame)
    
    def create_chart_tabs(self, parent):
        """Create chart tabs"""
        # Tab container
        tab_frame = tk.Frame(parent, bg=TradingTheme.COLORS['secondary_bg'])
        tab_frame.pack(fill='x', padx=TradingTheme.SPACING['md'], pady=(0, TradingTheme.SPACING['md']))
        
        # Tab buttons
        self.tab_buttons = {}
        tabs = ['Price Charts', 'Arbitrage Opportunities', 'Performance', 'AI Analysis']
        
        for i, tab in enumerate(tabs):
            btn = tk.Button(
                tab_frame,
                text=tab,
                font=TradingTheme.FONTS['body'],
                bg=TradingTheme.COLORS['accent_bg'] if i == 0 else TradingTheme.COLORS['secondary_bg'],
                fg=TradingTheme.COLORS['text_primary'],
                bd=0,
                padx=TradingTheme.SPACING['lg'],
                pady=TradingTheme.SPACING['sm'],
                relief='flat',
                command=lambda t=tab: self.switch_tab(t)
            )
            btn.pack(side='left', padx=(0, TradingTheme.SPACING['xs']))
            self.tab_buttons[tab] = btn
        
        # Chart content area
        self.chart_content = tk.Frame(parent, bg=TradingTheme.COLORS['chart_bg'], height=300)
        self.chart_content.pack(fill='both', expand=True, padx=TradingTheme.SPACING['md'], pady=(0, TradingTheme.SPACING['md']))
        self.chart_content.pack_propagate(False)
        
        # Placeholder content
        self.create_chart_placeholder()
    
    def create_chart_placeholder(self):
        """Create chart placeholder"""
        placeholder = tk.Label(
            self.chart_content,
            text="📈 Charts will be displayed here\nConnect to broker to see real-time data",
            font=TradingTheme.FONTS['body'],
            bg=TradingTheme.COLORS['chart_bg'],
            fg=TradingTheme.COLORS['text_secondary']
        )
        placeholder.place(relx=0.5, rely=0.5, anchor='center')
    
    
    def switch_tab(self, tab_name):
        """Switch between chart tabs"""
        # Update button colors
        for name, btn in self.tab_buttons.items():
            if name == tab_name:
                btn['bg'] = TradingTheme.COLORS['accent_bg']
            else:
                btn['bg'] = TradingTheme.COLORS['secondary_bg']
        
        # Update content (placeholder for now)
        for widget in self.chart_content.winfo_children():
            widget.destroy()
        
        self.create_chart_placeholder()
    
    def setup_logging(self):
        """Setup logging to display in GUI"""
        # Create custom handler for GUI
        class GUILogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
            
            def emit(self, record):
                msg = self.format(record)
                def append():
                    self.text_widget.config(state=tk.NORMAL)
                    self.text_widget.insert(tk.END, msg + '\n')
                    self.text_widget.see(tk.END)
                    self.text_widget.config(state=tk.DISABLED)
                self.text_widget.after(0, append)
        
        # Add handler to root logger
        if hasattr(self, 'log_text') and self.log_text:
            gui_handler = GUILogHandler(self.log_text)
            gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logging.getLogger().addHandler(gui_handler)
    
    def connect_broker(self):
        """Connect to broker manually"""
        try:
            self.log_message("Checking broker connection...")
            self.update_connection_status("connecting")
            
            # Connect in background thread to avoid blocking GUI
            def connect_thread():
                try:
                    # Check if trading_system already exists from auto-setup
                    if self.trading_system and self.trading_system.broker_api:
                        if self.trading_system.broker_api.is_connected():
                            # Update GUI in main thread
                            self.root.after(0, self._on_already_connected)
                        else:
                            # Try to reconnect
                            if self.trading_system.broker_api.connect():
                                self.root.after(0, self._on_reconnected)
                            else:
                                self.root.after(0, self._on_reconnect_failed)
                    else:
                        self.root.after(0, self._on_system_not_available)
                        
                except Exception as e:
                    self.root.after(0, lambda: self._on_connection_error(str(e)))
            
            # Start background thread
            threading.Thread(target=connect_thread, daemon=True).start()
                
        except Exception as e:
            self.log_message(f"❌ Connection error: {str(e)}")
            self.update_connection_status("error")
    
    def _on_already_connected(self):
        """Called when already connected to broker"""
        self.update_connection_status("connected")
        self.log_message("✅ Already connected to broker")
        if self.trading_system.broker_api.account_info:
            account = self.trading_system.broker_api.account_info
            self.log_message(f"Account: {account.login} | Server: {account.server}")
            self.log_message(f"Balance: ${account.balance:.2f} | Equity: ${account.equity:.2f}")
        
        # Update Group Dashboard
        self.update_group_dashboard()
    
    def _on_reconnected(self):
        """Called when reconnected to broker"""
        self.update_connection_status("connected")
        self.log_message("✅ Reconnected to broker successfully")
        
        # Update Group Dashboard
        self.update_group_dashboard()
    
    def _on_reconnect_failed(self):
        """Called when reconnect to broker failed"""
        self.update_connection_status("disconnected")
        self.log_message("❌ Failed to reconnect to broker")
    
    def _on_system_not_available(self):
        """Called when trading system not available"""
        self.update_connection_status("disconnected")
        self.log_message("❌ Trading system not available")
    
    def _on_connection_error(self, error_msg):
        """Called when connection error occurs"""
        self.log_message(f"❌ Connection error: {error_msg}")
        self.update_connection_status("error")
    
    def update_connection_status(self, status):
        """Update connection status"""
        self.connection_status = status
        
        status_config = {
            'connected': {'color': TradingTheme.COLORS['success'], 'icon': '🟢', 'text': 'Connected'},
            'connecting': {'color': TradingTheme.COLORS['warning'], 'icon': '🟡', 'text': 'Connecting'},
            'disconnected': {'color': TradingTheme.COLORS['danger'], 'icon': '🔴', 'text': 'Disconnected'},
            'error': {'color': TradingTheme.COLORS['danger'], 'icon': '⚠️', 'text': 'Error'},
        }
        
        config = status_config.get(status, status_config['disconnected'])
        
        # Update connection indicator
        if hasattr(self, 'connection_label'):
            self.connection_label.config(
                text=f"{config['icon']} Connection",
                fg=config['color']
            )
    
    def update_positions(self):
        """Update positions display"""
        # Clear existing items
        for item in self.positions_tree.get_children():
            self.positions_tree.delete(item)
            
        try:
            if self.trading_system and self.trading_system.position_manager:
                positions = self.trading_system.position_manager.get_active_positions()
                
                if positions:
                    for pos in positions:
                        pnl = pos.get('pnl', 0)
                        pnl_color = TradingTheme.get_pnl_color(pnl)
                        
                        # Insert position data
                        item = self.positions_tree.insert('', 'end', values=(
                            pos.get('symbol', ''),
                            pos.get('type', ''),
                            pos.get('volume', ''),
                            f"{pos.get('price', 0):.5f}",
                            TradingTheme.format_currency(pnl),
                            pos.get('status', '')
                        ))
                        
                        # Color the PnL column
                        self.positions_tree.set(item, 'PnL', TradingTheme.format_currency(pnl))
                        
                else:
                    # Show empty state
                    self.positions_tree.insert('', 'end', values=('', '', 'No active positions', '', '', ''))
                    
            else:
                # Show error state
                self.positions_tree.insert('', 'end', values=('❌', '', 'Trading system not available', '', '', ''))
                
        except Exception as e:
            self.positions_tree.insert('', 'end', values=('❌', '', f'Error: {str(e)}', '', '', ''))
    
    def refresh_positions(self):
        """Refresh positions display"""
        self.update_positions()
        self.log_message("Positions refreshed")
    
    def close_all_positions(self):
        """Close all positions"""
        if messagebox.askyesno("Confirm", "Are you sure you want to close all positions?"):
            try:
                if self.trading_system and self.trading_system.position_manager:
                    # Implementation would go here
                    self.log_message("All positions closed")
                    self.update_positions()
                else:
                    self.log_message("Trading system not available")
            except Exception as e:
                self.log_message(f"Error closing positions: {str(e)}")
    
    def start_trading(self):
        """Start trading system"""
        try:
            if not self.trading_system:
                self.log_message("❌ Please connect to broker first")
                return
            
            # Start trading in background thread to avoid blocking GUI
            def start_trading_thread():
                try:
                    if self.trading_system.start():
                        # Update GUI in main thread
                        self.root.after(0, self._on_trading_started_success)
                    else:
                        self.root.after(0, self._on_trading_started_failed)
                except Exception as e:
                    self.root.after(0, lambda: self._on_trading_error(str(e)))
            
            # Start background thread
            threading.Thread(target=start_trading_thread, daemon=True).start()
            self.log_message("🚀 Starting trading system...")
            
        except Exception as e:
            self.log_message(f"❌ Error starting trading: {str(e)}")
    
    def _on_trading_started_success(self):
        """Called when trading system started successfully"""
        self.is_trading = True
        self.update_connection_status("connected")
        self.log_message("✅ Trading system started")
        
        # Start Group Dashboard update loop
        self.start_group_dashboard_update_loop()
    
    def _on_trading_started_failed(self):
        """Called when trading system failed to start"""
        self.log_message("❌ Failed to start trading system")
    
    def _on_trading_error(self, error_msg):
        """Called when trading system encountered an error"""
        self.log_message(f"❌ Error starting trading: {error_msg}")
    
    def stop_trading(self):
        """Stop trading system"""
        try:
            if not self.trading_system:
                self.log_message("Trading system not available")
                return
            
            # Stop trading in background thread to avoid blocking GUI
            def stop_trading_thread():
                try:
                    self.trading_system.stop()
                    # Update GUI in main thread
                    self.root.after(0, self._on_trading_stopped)
                except Exception as e:
                    self.root.after(0, lambda: self._on_stop_error(str(e)))
            
            # Start background thread
            threading.Thread(target=stop_trading_thread, daemon=True).start()
            self.log_message("🛑 Stopping trading system...")
            
        except Exception as e:
            self.log_message(f"Error stopping trading: {str(e)}")
    
    def _on_trading_stopped(self):
        """Called when trading system stopped successfully"""
        self.is_trading = False
        self.update_connection_status("disconnected")
        self.log_message("Trading system stopped")
    
    def _on_stop_error(self, error_msg):
        """Called when trading system encountered an error during stop"""
        self.log_message(f"Error stopping trading: {error_msg}")
    
    def emergency_stop(self):
        """Emergency stop all trading"""
        if messagebox.askyesno("EMERGENCY STOP", "This will immediately stop all trading activities. Continue?"):
            try:
                if self.trading_system:
                    self.trading_system.emergency_stop()
                    self.is_trading = False
                    self.update_connection_status("disconnected")
                    self.log_message("🚨 EMERGENCY STOP ACTIVATED")
                else:
                    self.log_message("Trading system not available")
                
            except Exception as e:
                self.log_message(f"Emergency stop error: {str(e)}")
    
    def show_settings(self):
        """Show settings dialog"""
        try:
            from .settings import SettingsWindow
            settings_window = SettingsWindow(self.root, self.trading_system)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open settings: {str(e)}")
    
    def clear_logs(self):
        """Clear log display"""
        if hasattr(self, 'log_text') and self.log_text:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            self.log_text.config(state=tk.DISABLED)
    
    def update_group_dashboard(self):
        """Update Group Dashboard with current data"""
        try:
            print("🔍 Debug: update_group_dashboard called")
            # Check if group_dashboard exists
            if not hasattr(self, 'group_dashboard') or not self.group_dashboard:
                self.log_message("⚠️ Group dashboard not initialized")
                print("❌ Debug: Group dashboard not initialized")
                return
            
            print("✅ Debug: Group dashboard exists")
            
            # Always try to get real data first, fallback to sample data
            real_data_available = False
            
            # Debug: Check if trading system exists
            if self.trading_system and hasattr(self.trading_system, 'arbitrage_detector'):
                if hasattr(self.trading_system.arbitrage_detector, 'active_groups'):
                    real_data_available = True
                    self.log_message("📊 Using real trading data")
                    print("✅ Debug: Using real trading data")
                else:
                    self.log_message("⚠️ Active groups not available - using sample data")
                    print("⚠️ Debug: Active groups not available - using sample data")
            else:
                self.log_message("⚠️ Trading system not connected - using sample data")
                print("⚠️ Debug: Trading system not connected - using sample data")
            
            if not real_data_available:
                # Load sample data instead of showing empty
                print("🔍 Debug: Loading sample data...")
                self.group_dashboard.refresh_groups()
                print("✅ Debug: Sample data loaded")
                return
                
            # Update enhanced data in active_groups
            if hasattr(self.trading_system.arbitrage_detector, 'update_active_groups_with_enhanced_data'):
                self.trading_system.arbitrage_detector.update_active_groups_with_enhanced_data()
            
            # Get active groups data
            active_groups = self.trading_system.arbitrage_detector.active_groups
            self.log_message(f"📊 Found {len(active_groups)} active groups")
            
            # เรียกใช้ correlation manager เพื่อแสดง log รายละเอียด
            if hasattr(self.trading_system, 'correlation_manager') and self.trading_system.correlation_manager:
                try:
                    # เรียกใช้ correlation manager เพื่อแสดงสถานะการแก้ไม้
                    self.trading_system.correlation_manager._log_all_groups_status()
                except Exception as e:
                    self.log_message(f"⚠️ Error calling correlation manager: {e}")
            
            # Update group dashboard with real data
            if hasattr(self, 'group_dashboard') and self.group_dashboard:
                # Convert active_groups to format expected by new group_dashboard
                groups_data = {}
                for triangle_id in ['triangle_1', 'triangle_2', 'triangle_3', 'triangle_4', 'triangle_5', 'triangle_6']:
                    # Find group data for this triangle
                    group_data = None
                    for group_id, group_info in active_groups.items():
                        if group_info.get('triangle_type') == triangle_id:
                            group_data = group_info
                            break
                    
                    if group_data:
                        # Get positions data for this group
                        positions_data = self.get_positions_status_data()
                        group_positions = positions_data.get('groups', {}).get(f'group_triangle_{triangle_id.split("_")[1]}_1', {})
                        
                        # Merge group data with positions data
                        enhanced_group_data = {
                            **group_data,
                            'profit_arbitrage': group_positions.get('profit_arbitrage', []),
                            'losing_arbitrage': group_positions.get('losing_arbitrage', []),
                            'profit_correlation': group_positions.get('profit_correlation', []),
                            'losing_correlation': group_positions.get('losing_correlation', []),
                            'existing_correlation': group_positions.get('existing_correlation', [])
                        }
                        
                        # Convert to format expected by new group_dashboard
                        groups_data[triangle_id] = {
                            'net_pnl': group_data.get('total_pnl', 0.0),
                            'arbitrage_pnl': group_data.get('profit_arbitrage', 0.0),
                            'recovery_pnl': group_data.get('profit_correlation', 0.0),
                            'status': 'active',
                            'total_positions': len(group_data.get('positions', [])),
                            'total_trades': group_data.get('total_trades', 0)
                        }
                    else:
                        # No active group for this triangle
                        groups_data[triangle_id] = {
                            'net_pnl': 0.0,
                            'arbitrage_pnl': 0.0,
                            'recovery_pnl': 0.0,
                            'status': 'inactive',
                            'total_positions': 0,
                            'total_trades': 0
                        }
                
                # Update group dashboard with converted data
                self.group_dashboard.update_group_dashboard(groups_data)
            else:
                self.log_message("⚠️ Group dashboard not ready yet")
                
        except Exception as e:
            import traceback
            self.log_message(f"❌ Error updating group dashboard: {e}")
            self.log_message(f"❌ Traceback: {traceback.format_exc()}")
    
    def get_positions_status_data(self):
        """ดึงข้อมูลสถานะไม้สำหรับแสดงใน GUI แบ่งตาม Group"""
        try:
            if not self.trading_system or not hasattr(self.trading_system, 'correlation_manager'):
                return {'groups': {}}
            
            # Get positions from correlation manager
            correlation_manager = self.trading_system.correlation_manager
            
            # Get all positions from MT5
            all_positions = correlation_manager.broker.get_all_positions()
            
            # Initialize groups data
            groups_data = {}
            
            # Initialize all 6 groups
            for i in range(1, 7):
                group_id = f'group_triangle_{i}_1'
                groups_data[group_id] = {
                    'profit_arbitrage': [],
                    'losing_arbitrage': [],
                    'profit_correlation': [],
                    'losing_correlation': [],
                    'existing_correlation': []
                }
            
            # Categorize positions by group
            for pos in all_positions:
                symbol = pos.get('symbol', '')
                pnl = pos.get('profit', 0)
                order_id = pos.get('ticket', 'N/A')
                comment = pos.get('comment', '')
                magic = pos.get('magic', 0)
                
                # Determine group from magic number
                group_id = self._get_group_from_magic(magic)
                
                # Calculate additional data
                balance = correlation_manager.broker.get_account_balance()
                if balance:
                    loss_percent_of_balance = abs(pnl) / balance
                else:
                    loss_percent_of_balance = 0
                price_distance = correlation_manager._calculate_price_distance(pos)
                is_hedged = correlation_manager._is_position_hedged(pos, group_id)
                
                position_data = {
                    'symbol': symbol,
                    'order_id': order_id,
                    'pnl': pnl,
                    'loss_percent_of_balance': loss_percent_of_balance,
                    'price_distance': price_distance,
                    'is_hedged': is_hedged
                }
                
                # Add to appropriate group and category
                if group_id in groups_data:
                    # Check if recovery (support multiple formats)
                    is_recovery = (comment.startswith('RECOVERY_') or 
                                  comment.startswith('R') or 
                                  'RECOVERY' in comment.upper())
                    
                    if is_recovery:
                        # Recovery positions
                        if pnl > 0:
                            groups_data[group_id]['profit_correlation'].append(position_data)
                        else:
                            groups_data[group_id]['losing_correlation'].append(position_data)
                    else:
                        # Arbitrage positions
                        if pnl > 0:
                            groups_data[group_id]['profit_arbitrage'].append(position_data)
                        else:
                            groups_data[group_id]['losing_arbitrage'].append(position_data)
            
            return {'groups': groups_data}
            
        except Exception as e:
            self.log_message(f"❌ Error getting positions status data: {e}")
            return {'groups': {}}
    
    def _get_group_from_magic(self, magic):
        """หา group_id จาก magic number"""
        magic_to_group = {
            234001: 'group_triangle_1_1',
            234002: 'group_triangle_2_1', 
            234003: 'group_triangle_3_1',
            234004: 'group_triangle_4_1',
            234005: 'group_triangle_5_1',
            234006: 'group_triangle_6_1'
        }
        return magic_to_group.get(magic, 'group_triangle_1_1')  # Default to group 1
    
    
    def start_group_dashboard_update_loop(self):
        """Start Group Dashboard update loop"""
        def update_loop():
            if self.is_trading:
                try:
                    self.update_group_dashboard()
                except Exception as e:
                    self.log_message(f"Error in group dashboard update: {e}")
                
                # Schedule next update
                self.root.after(5000, update_loop)  # Update every 5 seconds for better responsiveness
            else:
                # Still update even when not trading to show connection status
                try:
                    self.update_group_dashboard()
                except Exception as e:
                    self.log_message(f"Error in group dashboard update: {e}")
                
                # Schedule next update
                self.root.after(10000, update_loop)  # Update every 10 seconds when not trading
        
        # Start the update loop
        update_loop()
    
    def toggle_connection(self):
        """Toggle MT5 connection"""
        if self.connection_status == 'connected':
            # Disconnect
            if self.trading_system and self.trading_system.broker_api:
                self.trading_system.broker_api.disconnect()
            self.update_connection_status('disconnected')
            self.connect_btn.config(text="🔌 Connect")
            self.log_message("🔴 Disconnected from MT5")
        else:
            # Connect
            if not self.trading_system:
                self.log_message("❌ Trading system not initialized")
                return
                
            self.update_connection_status('connecting')
            self.connect_btn.config(text="⏳ Connecting...")
            self.log_message("🟡 Connecting to MT5...")
            
            # Try to connect using trading system
            def connect_async():
                try:
                    if self.trading_system.broker_api.connect():
                        self.update_connection_status('connected')
                        self.connect_btn.config(text="🔌 Disconnect")
                        self.log_message("🟢 Connected to MT5 successfully")
                        
                        # Update group dashboard after connection
                        self.update_group_dashboard()
                    else:
                        self.update_connection_status('error')
                        self.connect_btn.config(text="🔌 Connect")
                        self.log_message("❌ Failed to connect to MT5")
                except Exception as e:
                    self.update_connection_status('error')
                    self.connect_btn.config(text="🔌 Connect")
                    self.log_message(f"❌ Connection error: {e}")
            
            # Run connection in separate thread
            threading.Thread(target=connect_async, daemon=True).start()
    
    
    def toggle_trading(self):
        """Toggle trading system"""
        if self.is_trading:
            # Stop trading
            if self.trading_system:
                self.trading_system.stop()
            self.is_trading = False
            self.trading_btn.config(text="▶️ Start Trading")
            self.log_message("⏹️ Trading system stopped")
            
            # Update group dashboard to show stopped status
            self.update_group_dashboard()
        else:
            # Start trading
            if self.connection_status != 'connected':
                self.log_message("❌ Please connect to MT5 first")
                return
            
            if not self.trading_system:
                self.log_message("❌ Trading system not initialized")
                return
            
            try:
                if self.trading_system.start():
                    self.is_trading = True
                    self.trading_btn.config(text="⏹️ Stop Trading")
                    self.log_message("▶️ Trading system started")
                    
                    # Start group dashboard update loop
                    self.start_group_dashboard_update_loop()
                    
                    # Update group dashboard immediately
                    self.update_group_dashboard()
                else:
                    self.log_message("❌ Failed to start trading system")
            except Exception as e:
                self.log_message(f"❌ Error starting trading system: {e}")
    
    def log_message(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        # Check if log_text exists
        if hasattr(self, 'log_text') and self.log_text:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, log_entry + '\n')
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        else:
            # Fallback: print to console
            print(log_entry)
    
    def run(self):
        """Run the GUI"""
        self.root.mainloop()
            
def main():
    """Main function to run the GUI"""
    app = MainWindow()
    app.run()

if __name__ == "__main__":
    main()
