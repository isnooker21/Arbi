"""
หน้าต่างหลักของระบบเทรด Forex AI

ไฟล์นี้ทำหน้าที่:
- แสดงหน้าจอควบคุมระบบเทรดทั้งหมด
- เชื่อมต่อกับ Broker (MetaTrader5, OANDA, FXCM)
- ควบคุมการเริ่ม/หยุดระบบเทรด
- แสดงสถานะ AI Engine และการตัดสินใจ
- ติดตามผลการเทรดและตำแหน่งที่เปิดอยู่
- แสดงกราฟและข้อมูลสถิติแบบ Real-time

ส่วนประกอบหลัก:
- Connection Panel: เชื่อมต่อ Broker
- Control Panel: ควบคุมระบบเทรด
- AI Dashboard: แสดงสถานะ AI
- Monitoring Panel: ติดตามผลการเทรด
- Charts: แสดงกราฟราคา
- Logs: แสดงบันทึกการทำงาน
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import logging
from datetime import datetime
import json

class MainWindow:
    def __init__(self, auto_setup=True):
        self.root = tk.Tk()
        self.root.title("🎯 Forex Arbitrage AI Trading System")
        self.root.geometry("1200x700")
        self.root.configure(bg='#000000')
        self.root.minsize(1000, 600)
        
        # Initialize variables
        self.trading_system = None
        self.is_trading = False
        self.connection_status = "Disconnected"
        self.auto_setup = auto_setup
        
        # Configure styles
        self.setup_styles()
        
        # Setup UI
        self.setup_ui()
        
        # Setup logging
        self.setup_logging()
        
        # Auto Setup if requested
        if self.auto_setup:
            self.root.after(1000, self.auto_connect)  # Delay 1 second to ensure GUI is ready
        
    def setup_styles(self):
        """Configure custom styles for the application"""
        style = ttk.Style()
        
        # Configure theme
        style.theme_use('clam')
        
        # Smooth professional dark theme color scheme
        colors = {
            'bg_primary': '#0d1117',
            'bg_secondary': '#161b22',
            'bg_tertiary': '#21262d',
            'accent_blue': '#58a6ff',
            'accent_green': '#3fb950',
            'accent_red': '#f85149',
            'accent_yellow': '#d29922',
            'accent_orange': '#fd7e14',
            'text_primary': '#f0f6fc',
            'text_secondary': '#c9d1d9',
            'text_muted': '#8b949e',
            'border': '#30363d',
            'highlight': '#1f2937',
            'success': '#3fb950',
            'warning': '#d29922',
            'danger': '#f85149'
        }
        
        # Configure main styles
        style.configure('Title.TLabel', 
                       background=colors['bg_primary'], 
                       foreground=colors['accent_blue'],
                       font=('Segoe UI', 18, 'bold'))
        
        style.configure('Header.TLabel', 
                       background=colors['bg_secondary'], 
                       foreground=colors['text_primary'],
                       font=('Segoe UI', 11, 'bold'))
        
        style.configure('SubHeader.TLabel', 
                       background=colors['bg_secondary'], 
                       foreground=colors['text_secondary'],
                       font=('Segoe UI', 10, 'bold'))
        
        # Professional button styles
        style.configure('Success.TButton',
                       background=colors['success'],
                       foreground='#ffffff',
                       font=('Segoe UI', 11, 'bold'),
                       borderwidth=0,
                       focuscolor='none',
                       relief='flat',
                       padding=(16, 8))
        
        style.configure('Warning.TButton',
                       background=colors['warning'],
                       foreground='#000000',
                       font=('Segoe UI', 11, 'bold'),
                       borderwidth=0,
                       focuscolor='none',
                       relief='flat',
                       padding=(16, 8))
        
        style.configure('Danger.TButton',
                       background=colors['danger'],
                       foreground='#ffffff',
                       font=('Segoe UI', 11, 'bold'),
                       borderwidth=0,
                       focuscolor='none',
                       relief='flat',
                       padding=(16, 8))
        
        style.configure('Primary.TButton',
                       background=colors['accent_blue'],
                       foreground='#ffffff',
                       font=('Segoe UI', 11, 'bold'),
                       borderwidth=0,
                       focuscolor='none',
                       relief='flat',
                       padding=(16, 8))
        
        style.configure('Secondary.TButton',
                       background=colors['bg_tertiary'],
                       foreground=colors['text_primary'],
                       font=('Segoe UI', 10),
                       borderwidth=1,
                       focuscolor='none',
                       relief='flat',
                       padding=(12, 6))
        
        # Professional hover effects
        style.map('Success.TButton',
                 background=[('active', '#059669')])
        style.map('Warning.TButton',
                 background=[('active', '#d97706')])
        style.map('Danger.TButton',
                 background=[('active', '#b91c1c')])
        style.map('Primary.TButton',
                 background=[('active', '#0056b3')])
        style.map('Secondary.TButton',
                 background=[('active', colors['highlight'])])
        
        # Label styles
        style.configure('Info.TLabel',
                       background=colors['bg_primary'],
                       foreground=colors['accent_blue'])
        
        style.configure('Success.TLabel',
                       background=colors['bg_primary'],
                       foreground=colors['accent_green'])
        
        style.configure('Warning.TLabel',
                       background=colors['bg_primary'],
                       foreground=colors['accent_yellow'])
        
        style.configure('Danger.TLabel',
                       background=colors['bg_primary'],
                       foreground=colors['accent_red'])
        
        style.configure('Muted.TLabel',
                       background=colors['bg_primary'],
                       foreground=colors['text_muted'])
        
        # Frame styles
        style.configure('Card.TFrame',
                       background=colors['bg_secondary'],
                       relief='raised',
                       borderwidth=1)
        
        style.configure('Panel.TFrame',
                       background=colors['bg_tertiary'],
                       relief='flat')
        
        # Entry styles
        style.configure('Modern.TEntry',
                       fieldbackground=colors['bg_tertiary'],
                       foreground=colors['text_primary'],
                       borderwidth=1,
                       insertcolor=colors['accent_blue'])
        
        # Combobox styles
        style.configure('Modern.TCombobox',
                       fieldbackground=colors['bg_tertiary'],
                       foreground=colors['text_primary'],
                       borderwidth=1,
                       arrowcolor=colors['accent_blue'])
        
        # Smooth treeview styles
        style.configure('Treeview',
                       background=colors['bg_secondary'],
                       foreground=colors['text_primary'],
                       fieldbackground=colors['bg_secondary'],
                       font=('Segoe UI', 10),
                       borderwidth=0)
        
        style.configure('Treeview.Heading',
                       background=colors['bg_tertiary'],
                       foreground=colors['text_primary'],
                       font=('Segoe UI', 10, 'bold'),
                       borderwidth=0)
        
        style.map('Treeview',
                 background=[('selected', colors['accent_blue'])],
                 foreground=[('selected', colors['text_primary'])])
        
        # Smooth notebook styles
        style.configure('TNotebook',
                       background=colors['bg_primary'],
                       borderwidth=0)
        
        style.configure('TNotebook.Tab',
                       background=colors['bg_secondary'],
                       foreground=colors['text_secondary'],
                       padding=[20, 10],
                       font=('Segoe UI', 10, 'bold'),
                       borderwidth=0)
        
        style.map('TNotebook.Tab',
                 background=[('selected', colors['accent_blue']),
                           ('active', colors['bg_tertiary'])],
                 foreground=[('selected', colors['text_primary']),
                           ('active', colors['text_primary'])])
        
        # Map hover effects
        style.map('Success.TButton',
                 background=[('active', '#00e676')])
        
        style.map('Warning.TButton',
                 background=[('active', '#ffb300')])
        
        style.map('Danger.TButton',
                 background=[('active', '#ff3838')])
        
        style.map('Primary.TButton',
                 background=[('active', '#00b8d4')])
        
        style.map('Secondary.TButton',
                 background=[('active', colors['bg_tertiary'])])
    
    def auto_connect(self):
        """Auto connect to MT5"""
        def auto_connect_thread():
            try:
                self.log_message("กำลังทำ Auto Setup...")
                
                # Import and create trading system
                from main import TradingSystem
                self.trading_system = TradingSystem(auto_setup=True)
                
                # Update connection status
                self.connection_status = "Connected"
                self.update_connection_status()
                
                # Update account info
                if self.trading_system.broker_api and self.trading_system.broker_api.account_info:
                    account = self.trading_system.broker_api.account_info
                    self.account_info_label.config(text=f"Account: {account.login} | Balance: {account.balance:.2f} {account.currency}")
                    self.log_message(f"เชื่อมต่อสำเร็จ - Account: {account.login}, Balance: {account.balance:.2f}")
                else:
                    self.log_message("เชื่อมต่อสำเร็จ แต่ไม่สามารถดึงข้อมูลบัญชีได้")
                
            except Exception as e:
                self.connection_status = "Failed"
                self.update_connection_status()
                self.log_message(f"Auto Setup ล้มเหลว: {str(e)}")
        
        # Run in separate thread
        threading.Thread(target=auto_connect_thread, daemon=True).start()
    
    def update_connection_status(self):
        """Update connection status display"""
        if self.connection_status == "Connected":
            self.connection_status_label.config(text="🟢 Connected", style="Success.TLabel")
            self.connect_button.config(text="Disconnect", style="Danger.TButton")
        elif self.connection_status == "Failed":
            self.connection_status_label.config(text="🔴 Failed", style="Danger.TLabel")
            self.connect_button.config(text="Retry", style="Warning.TButton")
        else:
            self.connection_status_label.config(text="🔴 Disconnected", style="Danger.TLabel")
            self.connect_button.config(text="Connect", style="Primary.TButton")
        
    def setup_ui(self):
        """Setup the main user interface"""
        # Create main container with professional layout
        main_container = ttk.Frame(self.root, style='Card.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create main content area
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # Create connection frame
        self.create_connection_frame(main_container)
        
        # Create control frame
        self.create_control_frame(main_container)
        
        # Create AI frame
        self.create_ai_frame(main_container)
        
        # Create monitoring frame
        self.create_monitoring_frame(main_container)
        
        # Create chart frame
        self.create_chart_frame(main_container)
        
        # Create log frame
        self.create_log_frame(main_container)
        
    def create_connection_frame(self, parent):
        """Create professional broker connection controls"""
        frame = ttk.LabelFrame(parent, text="🔗 Broker Connection", style='Header.TLabel')
        frame.pack(fill=tk.X, padx=8, pady=8)
        
        # Connection controls - compact layout
        connection_row = ttk.Frame(frame)
        connection_row.pack(fill=tk.X, padx=8, pady=6)
        
        # Connection button
        ttk.Button(connection_row, text="🔧 Connect", 
                  command=self.auto_connect, style='Primary.TButton').pack(side=tk.LEFT, padx=10)
        
        # Settings button
        ttk.Button(connection_row, text="⚙️ Settings", 
                  command=self.open_settings, style='Secondary.TButton').pack(side=tk.LEFT, padx=10)
        
        # Status display
        status_frame = ttk.Frame(frame)
        status_frame.pack(fill=tk.X, padx=8, pady=4)
        
        ttk.Label(status_frame, text="Status:", style='Info.TLabel').pack(side=tk.LEFT, padx=5)
        self.connection_status_label = ttk.Label(status_frame, text="🔴 Disconnected", 
                                               style='Danger.TLabel')
        self.connection_status_label.pack(side=tk.LEFT, padx=8)
        
        # Account info
        self.account_info_label = ttk.Label(status_frame, text="Account: Not Connected", 
                                          style='Muted.TLabel')
        self.account_info_label.pack(side=tk.RIGHT, padx=5)
    
    def auto_connect(self):
        """Auto connect to MT5 - simplified version"""
        def auto_connect_thread():
            try:
                self.log_message("กำลังทำ Auto Setup...")
                
                # Import and create trading system
                from main import TradingSystem
                self.trading_system = TradingSystem(auto_setup=True)
                
                # Update connection status in main thread
                self.root.after(0, self._update_connection_success)
                
            except Exception as e:
                # Update connection status in main thread
                self.root.after(0, lambda: self._update_connection_failed(str(e)))
        
        # Run in separate thread
        threading.Thread(target=auto_connect_thread, daemon=True).start()
    
    def _update_connection_success(self):
        """Update connection status on success - called from main thread"""
        self.connection_status = "Connected"
        self.log_message("เชื่อมต่อสำเร็จ!")
        
        # Update connection status display
        self.connection_status_label.config(text="🟢 Connected", style='Success.TLabel')
        
        # Update account info if available
        if self.trading_system and self.trading_system.broker_api and self.trading_system.broker_api.account_info:
            account = self.trading_system.broker_api.account_info
            self.account_info_label.config(text=f"Account: {account.login} | Balance: {account.balance:.2f} {account.currency}")
            self.log_message(f"Account: {account.login} | Balance: {account.balance:.2f} {account.currency}")
        else:
            self.account_info_label.config(text="Account: Connected")
    
    def _update_connection_failed(self, error_msg):
        """Update connection status on failure - called from main thread"""
        self.connection_status = "Failed"
        self.log_message(f"Auto Setup ล้มเหลว: {error_msg}")
        
        # Update connection status display
        self.connection_status_label.config(text="🔴 Failed", style='Danger.TLabel')
        self.account_info_label.config(text="Account: Connection Failed")
    
    def open_settings(self):
        """Open settings window"""
        try:
            from gui.settings import SettingsWindow
            settings_window = SettingsWindow(self.root)
        except Exception as e:
            self.log_message(f"ไม่สามารถเปิดหน้าต่างตั้งค่า: {e}")
        
    def create_control_frame(self, parent):
        """Create professional trading control panel"""
        frame = ttk.LabelFrame(parent, text="🎮 Trading Control", style='Header.TLabel')
        frame.pack(fill=tk.X, padx=8, pady=8)
        
        # System toggles - compact layout
        toggle_frame = ttk.Frame(frame)
        toggle_frame.pack(fill=tk.X, padx=8, pady=6)
        
        self.arbitrage_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(toggle_frame, text="Arbitrage System", 
                       variable=self.arbitrage_enabled, style='Info.TLabel').pack(side=tk.LEFT, padx=10)
        
        self.correlation_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(toggle_frame, text="Correlation System", 
                       variable=self.correlation_enabled, style='Info.TLabel').pack(side=tk.LEFT, padx=10)
        
        # Trading controls - compact layout
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, padx=8, pady=6)
        
        ttk.Button(button_frame, text="▶️ START", 
                  command=self.start_trading, 
                  style="Success.TButton").pack(side=tk.LEFT, padx=8)
        
        ttk.Button(button_frame, text="⏸️ STOP", 
                  command=self.stop_trading,
                  style="Warning.TButton").pack(side=tk.LEFT, padx=8)
        
        ttk.Button(button_frame, text="🛑 EMERGENCY", 
                  command=self.emergency_stop,
                  style="Danger.TButton").pack(side=tk.LEFT, padx=8)
        
        # Status display - compact
        status_frame = ttk.Frame(frame)
        status_frame.pack(fill=tk.X, padx=8, pady=4)
        
        ttk.Label(status_frame, text="Status:", style='Info.TLabel').pack(side=tk.LEFT, padx=5)
        self.trading_status_label = ttk.Label(status_frame, text="⏸️ Stopped", 
                                            style='Warning.TLabel')
        self.trading_status_label.pack(side=tk.LEFT, padx=8)
        
    def create_ai_frame(self, parent):
        """Create professional AI control and monitoring"""
        frame = ttk.LabelFrame(parent, text="🤖 AI Engine", style='Header.TLabel')
        frame.pack(fill=tk.X, padx=8, pady=8)
        
        # AI status - compact layout
        ai_status_frame = ttk.Frame(frame)
        ai_status_frame.pack(fill=tk.X, padx=8, pady=6)
        
        ttk.Label(ai_status_frame, text="Status:", style='Info.TLabel').pack(side=tk.LEFT, padx=5)
        self.ai_status_label = ttk.Label(ai_status_frame, text="🟢 Active", style='Success.TLabel')
        self.ai_status_label.pack(side=tk.LEFT, padx=8)
        
        # Rule counts
        ttk.Label(ai_status_frame, text="Rules:", style='Info.TLabel').pack(side=tk.LEFT, padx=15)
        self.active_rules_label = ttk.Label(ai_status_frame, text="247", style='Info.TLabel')
        self.active_rules_label.pack(side=tk.LEFT, padx=5)
        
        # Confidence level - compact
        confidence_frame = ttk.Frame(frame)
        confidence_frame.pack(fill=tk.X, padx=8, pady=4)
        
        ttk.Label(confidence_frame, text="Confidence:", style='Info.TLabel').pack(side=tk.LEFT, padx=5)
        self.confidence_var = tk.DoubleVar()
        self.confidence_progress = ttk.Progressbar(confidence_frame, variable=self.confidence_var, 
                                                 maximum=100, length=200, style='TProgressbar')
        self.confidence_progress.pack(side=tk.LEFT, padx=8)
        
        # Last decision - compact
        decision_frame = ttk.Frame(frame)
        decision_frame.pack(fill=tk.X, padx=8, pady=4)
        
        ttk.Label(decision_frame, text="Decision:", style='Info.TLabel').pack(side=tk.LEFT, padx=5)
        self.last_decision_label = ttk.Label(decision_frame, text="⏳ Waiting...", style='Muted.TLabel')
        self.last_decision_label.pack(side=tk.LEFT, padx=8)
        
    def create_monitoring_frame(self, parent):
        """Create professional monitoring and statistics frame"""
        frame = ttk.LabelFrame(parent, text="📊 Trading Monitor", style='Header.TLabel')
        frame.pack(fill=tk.X, padx=8, pady=8)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(frame)
        notebook.pack(fill=tk.X, padx=8, pady=8)
        
        # Positions tab
        positions_frame = ttk.Frame(notebook)
        notebook.add(positions_frame, text="Positions")
        
        # Positions treeview
        columns = ('Symbol', 'Type', 'Volume', 'Price', 'PnL', 'Status')
        self.positions_tree = ttk.Treeview(positions_frame, columns=columns, show='headings', height=6)
        
        for col in columns:
            self.positions_tree.heading(col, text=col)
            self.positions_tree.column(col, width=100)
        
        self.positions_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Scrollbar for positions
        positions_scrollbar = ttk.Scrollbar(positions_frame, orient="vertical", command=self.positions_tree.yview)
        positions_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.positions_tree.configure(yscrollcommand=positions_scrollbar.set)
        
        # Performance tab
        performance_frame = ttk.Frame(notebook)
        notebook.add(performance_frame, text="Performance")
        
        # Performance labels - compact layout
        stats_frame = ttk.Frame(performance_frame)
        stats_frame.pack(fill=tk.X, padx=8, pady=8)
        
        # Row 1
        row1 = ttk.Frame(stats_frame)
        row1.pack(fill=tk.X, pady=4)
        
        ttk.Label(row1, text="Total PnL:", style='Info.TLabel').pack(side=tk.LEFT, padx=5)
        self.total_pnl_label = ttk.Label(row1, text="$0.00", style='Info.TLabel')
        self.total_pnl_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(row1, text="Win Rate:", style='Info.TLabel').pack(side=tk.LEFT, padx=20)
        self.win_rate_label = ttk.Label(row1, text="0%", style='Info.TLabel')
        self.win_rate_label.pack(side=tk.LEFT, padx=10)
        
        # Row 2
        row2 = ttk.Frame(stats_frame)
        row2.pack(fill=tk.X, pady=4)
        
        ttk.Label(row2, text="Total Trades:", style='Info.TLabel').pack(side=tk.LEFT, padx=5)
        self.total_trades_label = ttk.Label(row2, text="0", style='Info.TLabel')
        self.total_trades_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(row2, text="Active Triangles:", style='Info.TLabel').pack(side=tk.LEFT, padx=20)
        self.active_triangles_label = ttk.Label(row2, text="0", style='Info.TLabel')
        self.active_triangles_label.pack(side=tk.LEFT, padx=10)
        
    def create_chart_frame(self, parent):
        """Create professional chart display frame"""
        frame = ttk.LabelFrame(parent, text="📊 Charts", style='Header.TLabel')
        frame.pack(fill=tk.X, padx=8, pady=8)
        
        # Placeholder for charts
        self.chart_label = ttk.Label(frame, text="📊 Charts will be displayed here\n\nReal-time price charts and analysis will appear in this area.", 
                                   style='Muted.TLabel', anchor=tk.CENTER)
        self.chart_label.pack(padx=5, pady=20)
        
        # Chart controls
        chart_controls = ttk.Frame(frame)
        chart_controls.pack(padx=5, pady=5)
        
        ttk.Button(chart_controls, text="Open Charts", command=self.open_charts, 
                  style='Primary.TButton').pack(side=tk.LEFT)
        ttk.Button(chart_controls, text="Refresh", command=self.refresh_charts, 
                  style='Secondary.TButton').pack(side=tk.LEFT, padx=(10, 0))
        
    def create_log_frame(self, parent):
        """Create professional log display frame"""
        frame = ttk.LabelFrame(parent, text="📝 System Log", style='Header.TLabel')
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Professional log text area
        self.log_text = scrolledtext.ScrolledText(frame, height=6, bg='#0a0a0a', 
                                                fg='#ffffff', font=('Consolas', 10), insertbackground='#007acc',
                                                selectbackground='#374151', selectforeground='#ffffff',
                                                relief='flat', borderwidth=0)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Clear log button - compact
        ttk.Button(frame, text="🗑️ Clear", 
                  command=self.clear_log, style='Secondary.TButton').pack(padx=8, pady=4)
    
    def open_charts(self):
        """Open charts window"""
        try:
            from gui.charts import RealTimeCharts
            if self.trading_system and self.trading_system.broker_api:
                charts_window = RealTimeCharts(self.root, self.trading_system.broker_api)
            else:
                self.log_message("ไม่สามารถเปิดกราฟได้ - ยังไม่ได้เชื่อมต่อ Broker")
        except Exception as e:
            self.log_message(f"ไม่สามารถเปิดกราฟได้: {e}")
    
    def refresh_charts(self):
        """Refresh charts"""
        self.log_message("กำลังรีเฟรชกราฟ...")
    
    def start_trading(self):
        """Start trading"""
        if not self.trading_system:
            self.log_message("ยังไม่ได้เชื่อมต่อ Broker")
            return
        
        self.is_trading = True
        self.trading_status_label.config(text="🟢 Running", style='Success.TLabel')
        self.log_message("เริ่มต้นการเทรด")
    
    def stop_trading(self):
        """Stop trading"""
        self.is_trading = False
        self.trading_status_label.config(text="⏸️ Stopped", style='Warning.TLabel')
        self.log_message("หยุดการเทรด")
    
    def emergency_stop(self):
        """Emergency stop"""
        self.is_trading = False
        self.trading_status_label.config(text="🛑 Emergency Stop", style='Danger.TLabel')
        self.log_message("EMERGENCY STOP - หยุดการเทรดทันที!")
    
    def clear_log(self):
        """Clear log text"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("ล้าง Log แล้ว")
    
    def log_message(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        
    def setup_logging(self):
        """Setup logging to display in GUI"""
        # Create custom handler for GUI
        self.log_handler = GUILogHandler(self.log_text)
        self.log_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.log_handler.setFormatter(formatter)
        
        # Add handler to root logger
        logging.getLogger().addHandler(self.log_handler)
        
    def connect_broker(self):
        """Connect to broker"""
        try:
            broker_type = self.broker_var.get()
            login = self.login_var.get()
            password = self.password_var.get()
            
            if not login or not password:
                messagebox.showerror("Error", "Please enter login and password")
                return
            
            # Import and initialize broker API
            from trading.broker_api import BrokerAPI
            
            broker_api = BrokerAPI(broker_type)
            success = broker_api.connect(login=int(login), password=password)
            
            if success:
                self.connection_status = "Connected"
                self.connection_status_label.config(text="Connected", style='Success.TLabel')
                self.log_message("Successfully connected to broker", "INFO")
            else:
                self.connection_status = "Failed"
                self.connection_status_label.config(text="Failed", style='Danger.TLabel')
                self.log_message("Failed to connect to broker", "ERROR")
                
        except Exception as e:
            self.log_message(f"Connection error: {str(e)}", "ERROR")
            messagebox.showerror("Connection Error", str(e))
    
    def start_trading(self):
        """Start the trading system"""
        try:
            if self.is_trading:
                self.log_message("Trading already started", "WARNING")
                return
            
            if self.connection_status != "Connected":
                messagebox.showerror("Error", "Please connect to broker first")
                return
            
            # Initialize trading system
            from main import TradingSystem
            
            self.trading_system = TradingSystem()
            
            # Start trading in separate thread
            trading_thread = threading.Thread(target=self._start_trading_thread, daemon=True)
            trading_thread.start()
            
            self.is_trading = True
            self.trading_status_label.config(text="Running", style='Success.TLabel')
            self.log_message("Trading system started", "INFO")
            
        except Exception as e:
            self.log_message(f"Error starting trading: {str(e)}", "ERROR")
            messagebox.showerror("Error", str(e))
    
    def _start_trading_thread(self):
        """Start trading system in separate thread"""
        try:
            if self.trading_system:
                self.trading_system.start()
        except Exception as e:
            self.log_message(f"Trading thread error: {str(e)}", "ERROR")
    
    def stop_trading(self):
        """Stop the trading system"""
        try:
            if not self.is_trading:
                self.log_message("Trading not started", "WARNING")
                return
            
            if self.trading_system:
                self.trading_system.stop()
            
            self.is_trading = False
            self.trading_status_label.config(text="Stopped", style='Warning.TLabel')
            self.log_message("Trading system stopped", "INFO")
            
        except Exception as e:
            self.log_message(f"Error stopping trading: {str(e)}", "ERROR")
    
    def emergency_stop(self):
        """Emergency stop all trading"""
        try:
            if self.trading_system:
                self.trading_system.emergency_stop()
            
            self.is_trading = False
            self.trading_status_label.config(text="EMERGENCY STOP", style='Danger.TLabel')
            self.log_message("EMERGENCY STOP activated", "CRITICAL")
            
        except Exception as e:
            self.log_message(f"Emergency stop error: {str(e)}", "ERROR")
    
    def log_message(self, message, level="INFO"):
        """Add message to log display"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {level}: {message}\n"
            
            self.log_text.insert(tk.END, log_entry)
            self.log_text.see(tk.END)
            
            # Limit log size
            lines = self.log_text.get("1.0", tk.END).split('\n')
            if len(lines) > 1000:
                self.log_text.delete("1.0", "100.0")
                
        except Exception as e:
            print(f"Error logging message: {e}")
    
    def clear_log(self):
        """Clear the log display"""
        self.log_text.delete("1.0", tk.END)
    
    def update_ui(self):
        """Update UI elements (call periodically)"""
        try:
            # Update AI status
            if self.trading_system and hasattr(self.trading_system, 'ai_engine'):
                # Update confidence
                confidence = getattr(self.trading_system.ai_engine, 'last_confidence', 0)
                self.confidence_var.set(confidence * 100)
                
                # Update last decision
                last_decision = getattr(self.trading_system.ai_engine, 'last_decision', "Waiting...")
                self.last_decision_label.config(text=str(last_decision)[:50] + "...")
            
            # Update positions
            self.update_positions()
            
            # Update performance
            self.update_performance()
            
        except Exception as e:
            self.log_message(f"UI update error: {str(e)}", "ERROR")
    
    def update_positions(self):
        """Update positions display"""
        try:
            # Clear existing items
            for item in self.positions_tree.get_children():
                self.positions_tree.delete(item)
            
            # Add sample data (replace with actual position data)
            sample_positions = [
                ("EURUSD", "BUY", "0.1", "1.0850", "+$15.50", "Active"),
                ("GBPUSD", "SELL", "0.1", "1.2650", "-$8.25", "Active"),
                ("USDJPY", "BUY", "0.1", "149.50", "+$22.75", "Active")
            ]
            
            for position in sample_positions:
                self.positions_tree.insert("", "end", values=position)
                
        except Exception as e:
            self.log_message(f"Error updating positions: {str(e)}", "ERROR")
    
    def update_performance(self):
        """Update performance display"""
        try:
            # Update performance labels (replace with actual data)
            self.total_pnl_label.config(text="$1,250.75")
            self.win_rate_label.config(text="68.5%")
            self.total_trades_label.config(text="127")
            self.active_triangles_label.config(text="3")
            
        except Exception as e:
            self.log_message(f"Error updating performance: {str(e)}", "ERROR")
    
    def run(self):
        """Start the GUI application"""
        try:
            # Start UI update loop
            self.update_ui()
            self.root.after(1000, self.run)  # Update every second
            
            # Start main loop
            self.root.mainloop()
            
        except Exception as e:
            self.log_message(f"GUI error: {str(e)}", "ERROR")


class GUILogHandler(logging.Handler):
    """Custom log handler for GUI display"""
    
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
    
    def emit(self, record):
        try:
            msg = self.format(record)
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)
        except Exception:
            pass


# Main application entry point
if __name__ == "__main__":
    app = MainWindow()
    app.run()
