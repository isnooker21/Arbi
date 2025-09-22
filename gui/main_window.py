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
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Forex Arbitrage AI Trading System")
        self.root.geometry("1400x800")
        self.root.configure(bg='#2b2b2b')
        
        # Initialize variables
        self.trading_system = None
        self.is_trading = False
        self.connection_status = "Disconnected"
        
        # Configure styles
        self.setup_styles()
        
        # Setup UI
        self.setup_ui()
        
        # Setup logging
        self.setup_logging()
        
    def setup_styles(self):
        """Configure custom styles for the application"""
        style = ttk.Style()
        
        # Configure theme
        style.theme_use('clam')
        
        # Configure colors
        style.configure('Title.TLabel', 
                       background='#2b2b2b', 
                       foreground='#ffffff',
                       font=('Arial', 16, 'bold'))
        
        style.configure('Header.TLabel', 
                       background='#3b3b3b', 
                       foreground='#ffffff',
                       font=('Arial', 12, 'bold'))
        
        style.configure('Success.TButton',
                       background='#28a745',
                       foreground='#ffffff')
        
        style.configure('Warning.TButton',
                       background='#ffc107',
                       foreground='#000000')
        
        style.configure('Danger.TButton',
                       background='#dc3545',
                       foreground='#ffffff')
        
        style.configure('Info.TLabel',
                       background='#2b2b2b',
                       foreground='#17a2b8')
        
        style.configure('Success.TLabel',
                       background='#2b2b2b',
                       foreground='#28a745')
        
        style.configure('Warning.TLabel',
                       background='#2b2b2b',
                       foreground='#ffc107')
        
        style.configure('Danger.TLabel',
                       background='#2b2b2b',
                       foreground='#dc3545')
        
    def setup_ui(self):
        """Setup the main user interface"""
        # Create main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
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
        """Create broker connection controls"""
        frame = ttk.LabelFrame(parent, text="Broker Connection", style='Header.TLabel')
        frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # Connection fields
        ttk.Label(frame, text="Broker:", style='Info.TLabel').grid(row=0, column=0, padx=5, pady=5)
        self.broker_var = tk.StringVar(value="MetaTrader5")
        broker_combo = ttk.Combobox(frame, textvariable=self.broker_var, 
                                  values=["MetaTrader5", "OANDA", "FXCM"], width=15)
        broker_combo.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(frame, text="Login:", style='Info.TLabel').grid(row=0, column=2, padx=5, pady=5)
        self.login_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.login_var, width=15).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(frame, text="Password:", style='Info.TLabel').grid(row=0, column=4, padx=5, pady=5)
        self.password_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.password_var, show="*", width=15).grid(row=0, column=5, padx=5, pady=5)
        
        # Connection controls
        self.auto_login_var = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Auto Login", 
                       variable=self.auto_login_var, style='Info.TLabel').grid(row=0, column=6, padx=5, pady=5)
        
        ttk.Button(frame, text="Connect", 
                  command=self.connect_broker).grid(row=0, column=7, padx=5, pady=5)
        
        # Status indicator
        self.connection_status_label = ttk.Label(frame, text="Disconnected", 
                                               style='Danger.TLabel')
        self.connection_status_label.grid(row=0, column=8, padx=5, pady=5)
        
    def create_control_frame(self, parent):
        """Create trading control panel"""
        frame = ttk.LabelFrame(parent, text="Trading Control", style='Header.TLabel')
        frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # System toggles
        self.arbitrage_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Arbitrage System", 
                       variable=self.arbitrage_enabled, style='Info.TLabel').grid(row=0, column=0, padx=5, pady=5)
        
        self.correlation_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Correlation System", 
                       variable=self.correlation_enabled, style='Info.TLabel').grid(row=0, column=1, padx=5, pady=5)
        
        # Trading controls
        ttk.Button(frame, text="START TRADING", 
                  command=self.start_trading, 
                  style="Success.TButton").grid(row=0, column=2, padx=10, pady=5)
        
        ttk.Button(frame, text="STOP TRADING", 
                  command=self.stop_trading,
                  style="Warning.TButton").grid(row=0, column=3, padx=10, pady=5)
        
        ttk.Button(frame, text="EMERGENCY STOP", 
                  command=self.emergency_stop,
                  style="Danger.TButton").grid(row=0, column=4, padx=10, pady=5)
        
        # Status display
        self.trading_status_label = ttk.Label(frame, text="Stopped", 
                                            style='Warning.TLabel')
        self.trading_status_label.grid(row=0, column=5, padx=5, pady=5)
        
    def create_ai_frame(self, parent):
        """Create AI control and monitoring"""
        frame = ttk.LabelFrame(parent, text="AI Engine", style='Header.TLabel')
        frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # AI status
        ttk.Label(frame, text="AI Status:", style='Info.TLabel').grid(row=0, column=0, padx=5, pady=5)
        self.ai_status_label = ttk.Label(frame, text="Active", style='Success.TLabel')
        self.ai_status_label.grid(row=0, column=1, padx=5, pady=5)
        
        # Rule counts
        ttk.Label(frame, text="Active Rules:", style='Info.TLabel').grid(row=0, column=2, padx=5, pady=5)
        self.active_rules_label = ttk.Label(frame, text="247", style='Info.TLabel')
        self.active_rules_label.grid(row=0, column=3, padx=5, pady=5)
        
        # Confidence level
        ttk.Label(frame, text="Confidence:", style='Info.TLabel').grid(row=0, column=4, padx=5, pady=5)
        self.confidence_var = tk.DoubleVar()
        self.confidence_progress = ttk.Progressbar(frame, variable=self.confidence_var, 
                                                 maximum=100, length=200)
        self.confidence_progress.grid(row=0, column=5, padx=5, pady=5)
        
        # Last decision
        ttk.Label(frame, text="Last Decision:", style='Info.TLabel').grid(row=1, column=0, padx=5, pady=5)
        self.last_decision_label = ttk.Label(frame, text="Waiting...", style='Info.TLabel')
        self.last_decision_label.grid(row=1, column=1, columnspan=4, sticky="w", padx=5, pady=5)
        
    def create_monitoring_frame(self, parent):
        """Create monitoring and statistics frame"""
        frame = ttk.LabelFrame(parent, text="Trading Monitor", style='Header.TLabel')
        frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(frame)
        notebook.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # Positions tab
        positions_frame = ttk.Frame(notebook)
        notebook.add(positions_frame, text="Positions")
        
        # Positions treeview
        columns = ('Symbol', 'Type', 'Volume', 'Price', 'PnL', 'Status')
        self.positions_tree = ttk.Treeview(positions_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.positions_tree.heading(col, text=col)
            self.positions_tree.column(col, width=100)
        
        self.positions_tree.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # Scrollbar for positions
        positions_scrollbar = ttk.Scrollbar(positions_frame, orient="vertical", command=self.positions_tree.yview)
        positions_scrollbar.grid(row=0, column=1, sticky="ns")
        self.positions_tree.configure(yscrollcommand=positions_scrollbar.set)
        
        # Performance tab
        performance_frame = ttk.Frame(notebook)
        notebook.add(performance_frame, text="Performance")
        
        # Performance labels
        ttk.Label(performance_frame, text="Total PnL:", style='Info.TLabel').grid(row=0, column=0, padx=5, pady=5)
        self.total_pnl_label = ttk.Label(performance_frame, text="$0.00", style='Info.TLabel')
        self.total_pnl_label.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(performance_frame, text="Win Rate:", style='Info.TLabel').grid(row=0, column=2, padx=5, pady=5)
        self.win_rate_label = ttk.Label(performance_frame, text="0%", style='Info.TLabel')
        self.win_rate_label.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(performance_frame, text="Total Trades:", style='Info.TLabel').grid(row=1, column=0, padx=5, pady=5)
        self.total_trades_label = ttk.Label(performance_frame, text="0", style='Info.TLabel')
        self.total_trades_label.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(performance_frame, text="Active Triangles:", style='Info.TLabel').grid(row=1, column=2, padx=5, pady=5)
        self.active_triangles_label = ttk.Label(performance_frame, text="0", style='Info.TLabel')
        self.active_triangles_label.grid(row=1, column=3, padx=5, pady=5)
        
    def create_chart_frame(self, parent):
        """Create chart display frame"""
        frame = ttk.LabelFrame(parent, text="Charts", style='Header.TLabel')
        frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # Placeholder for charts
        self.chart_label = ttk.Label(frame, text="Charts will be displayed here", 
                                   style='Info.TLabel')
        self.chart_label.grid(row=0, column=0, padx=5, pady=5)
        
    def create_log_frame(self, parent):
        """Create log display frame"""
        frame = ttk.LabelFrame(parent, text="System Log", style='Header.TLabel')
        frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(frame, height=8, bg='#1e1e1e', 
                                                fg='#ffffff', font=('Consolas', 9))
        self.log_text.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # Clear log button
        ttk.Button(frame, text="Clear Log", 
                  command=self.clear_log).grid(row=1, column=0, padx=5, pady=5)
        
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
