"""
หน้าต่างตั้งค่าระบบเทรด
=======================

ไฟล์นี้ทำหน้าที่:
- แสดงและแก้ไขการตั้งค่าระบบทั้งหมด
- จัดการการตั้งค่า Broker และการเชื่อมต่อ
- จัดการกฎเกณฑ์การเทรดและพารามิเตอร์ AI
- จัดการการตั้งค่าความเสี่ยงและการจัดการเงิน
- บันทึกและโหลดการตั้งค่าจากไฟล์ JSON

Author: AI Trading System
Version: 1.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from typing import Dict, Any
from .theme import TradingTheme

class SettingsWindow:
    def __init__(self, parent):
        self.parent = parent
        self.settings = {}
        self.original_settings = {}
        
        # Create settings window
        self.settings_window = tk.Toplevel(parent)
        self.settings_window.title("⚙️ System Settings - การตั้งค่าระบบ")
        self.settings_window.geometry("1000x700")
        self.settings_window.configure(bg='#2b2b2b')
        
        # Load settings
        self.load_settings()
        
        # Setup UI
        self.setup_ui()
        
    def load_settings(self):
        """Load settings from configuration files"""
        try:
            # Load main settings
            with open('config/settings.json', 'r', encoding='utf-8') as f:
                self.settings = json.load(f)
            
            # Load broker config
            with open('config/broker_config.json', 'r', encoding='utf-8') as f:
                broker_config = json.load(f)
                self.settings['broker_config'] = broker_config
            
            # Load rules (if exists)
            if os.path.exists('config/rules.json'):
                with open('config/rules.json', 'r', encoding='utf-8') as f:
                    rules = json.load(f)
                    self.settings['rules'] = rules
            else:
                self.settings['rules'] = {}
            
            # Load adaptive params
            with open('config/adaptive_params.json', 'r', encoding='utf-8') as f:
                adaptive_params = json.load(f)
                self.settings['adaptive_params'] = adaptive_params
            
            # Store original settings for comparison
            self.original_settings = json.loads(json.dumps(self.settings))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load settings: {str(e)}")
            self.settings = self.get_default_settings()
            self.original_settings = json.loads(json.dumps(self.settings))
    
    def get_default_settings(self) -> Dict[str, Any]:
        """
        ดึงการตั้งค่าเริ่มต้นของระบบ
        
        ส่งคืนการตั้งค่าเริ่มต้นเมื่อไม่สามารถโหลดไฟล์ได้
        
        Returns:
            Dict: การตั้งค่าเริ่มต้น
        """
        return {
            "trading": {
                "base_lot_size": 0.1,
                "max_triangles": 3,
                "max_grid_levels": 5,
                "min_arbitrage_threshold": 0.3,
                "max_spread": 0.5,
                "position_hold_time": 3600
            },
            "risk_management": {
                "position_size_multiplier": 1.5,
                "take_profit_percent": 1.0
            },
            "ai": {
                "learning_enabled": True,
                "rule_adaptation_frequency": "daily",
                "confidence_threshold": 0.7,
                "max_rules_per_category": 50,
                "performance_lookback_days": 30
            },
            "broker": {
                "default_broker": "MetaTrader5",
                "connection_timeout": 30,
                "retry_attempts": 3,
                "data_refresh_rate": 100
            },
            "gui": {
                "theme": "default",
                "chart_refresh_rate": 1000,
                "log_max_lines": 1000,
                "window_size": "1400x800"
            },
            "broker_config": {
                "MetaTrader5": {
                    "server": "YourBroker-Server",
                    "login": 0,
                    "password": "",
                    "timeout": 30000,
                    "portable": False
                },
                "OANDA": {
                    "account_id": "",
                    "access_token": "",
                    "environment": "practice",
                    "timeout": 30
                },
                "FXCM": {
                    "username": "",
                    "password": "",
                    "environment": "demo",
                    "timeout": 30
                }
            }
        }
    
    def setup_ui(self):
        """Setup the settings interface"""
        # Create main container
        main_container = ttk.Frame(self.settings_window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for different setting categories
        notebook = ttk.Notebook(main_container)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Trading settings tab
        self.create_trading_settings_tab(notebook)
        
        # Risk management tab
        self.create_risk_management_tab(notebook)
        
        # AI settings tab
        self.create_ai_settings_tab(notebook)
        
        # Broker settings tab
        self.create_broker_settings_tab(notebook)
        
        # GUI settings tab
        self.create_gui_settings_tab(notebook)
        
        # Rules settings tab
        self.create_rules_settings_tab(notebook)
        
        # Adaptive Params tab (ค่าที่ใช้จริง!)
        self.create_adaptive_params_tab(notebook)
        
        # Control buttons
        self.create_control_buttons(main_container)
        
    def create_trading_settings_tab(self, notebook):
        """Create trading settings tab"""
        trading_frame = ttk.Frame(notebook)
        notebook.add(trading_frame, text="Trading")
        
        # Create scrollable frame
        canvas = tk.Canvas(trading_frame, bg='#2b2b2b')
        scrollbar = ttk.Scrollbar(trading_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Trading parameters
        trading_params = [
            ("Base Lot Size", "trading.base_lot_size", "float", 0.01, 10.0),
            ("Max Triangles", "trading.max_triangles", "int", 1, 10),
            ("Max Grid Levels", "trading.max_grid_levels", "int", 1, 20),
            ("Min Arbitrage Threshold", "trading.min_arbitrage_threshold", "float", 0.01, 2.0),
            ("Max Spread", "trading.max_spread", "float", 0.01, 5.0),
            ("Position Hold Time (seconds)", "trading.position_hold_time", "int", 60, 86400)
        ]
        
        self.create_parameter_controls(scrollable_frame, trading_params)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def create_risk_management_tab(self, notebook):
        """Create risk management settings tab"""
        risk_frame = ttk.Frame(notebook)
        notebook.add(risk_frame, text="Risk Management")
        
        # Create scrollable frame
        canvas = tk.Canvas(risk_frame, bg='#2b2b2b')
        scrollbar = ttk.Scrollbar(risk_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Risk management parameters
        risk_params = [
            ("Position Size Multiplier", "risk_management.position_size_multiplier", "float", 0.1, 5.0),
            ("Take Profit %", "risk_management.take_profit_percent", "float", 0.1, 10.0)
        ]
        
        self.create_parameter_controls(scrollable_frame, risk_params)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def create_ai_settings_tab(self, notebook):
        """Create AI settings tab"""
        ai_frame = ttk.Frame(notebook)
        notebook.add(ai_frame, text="AI Engine")
        
        # AI parameters
        ai_params = [
            ("Learning Enabled", "ai.learning_enabled", "bool"),
            ("Rule Adaptation Frequency", "ai.rule_adaptation_frequency", "choice", ["daily", "weekly", "monthly"]),
            ("Confidence Threshold", "ai.confidence_threshold", "float", 0.1, 1.0),
            ("Max Rules Per Category", "ai.max_rules_per_category", "int", 10, 200),
            ("Performance Lookback Days", "ai.performance_lookback_days", "int", 7, 365)
        ]
        
        self.create_parameter_controls(ai_frame, ai_params)
        
    def create_broker_settings_tab(self, notebook):
        """Create broker settings tab"""
        broker_frame = ttk.Frame(notebook)
        notebook.add(broker_frame, text="Broker")
        
        # Broker selection
        ttk.Label(broker_frame, text="Default Broker:").pack(pady=5)
        self.broker_var = tk.StringVar(value=self.settings.get('broker', {}).get('default_broker', 'MetaTrader5'))
        broker_combo = ttk.Combobox(broker_frame, textvariable=self.broker_var,
                                  values=["MetaTrader5", "OANDA", "FXCM"])
        broker_combo.pack(pady=5)
        
        # Broker-specific settings
        self.broker_settings_frame = ttk.LabelFrame(broker_frame, text="Broker Configuration")
        self.broker_settings_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Update broker settings when selection changes
        broker_combo.bind('<<ComboboxSelected>>', self.update_broker_settings)
        self.update_broker_settings()
        
    def create_gui_settings_tab(self, notebook):
        """Create GUI settings tab"""
        gui_frame = ttk.Frame(notebook)
        notebook.add(gui_frame, text="GUI")
        
        # GUI parameters
        gui_params = [
            ("Theme", "gui.theme", "choice", ["default", "dark", "light"]),
            ("Chart Refresh Rate (ms)", "gui.chart_refresh_rate", "int", 100, 5000),
            ("Log Max Lines", "gui.log_max_lines", "int", 100, 10000),
            ("Window Size", "gui.window_size", "choice", ["800x600", "1200x800", "1400x800", "1600x900"])
        ]
        
        self.create_parameter_controls(gui_frame, gui_params)
        
    def create_rules_settings_tab(self, notebook):
        """Create rules settings tab"""
        rules_frame = ttk.Frame(notebook)
        notebook.add(rules_frame, text="Rules")
        
        # Rules display
        ttk.Label(rules_frame, text="AI Rules Configuration", font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Rules text area
        self.rules_text = tk.Text(rules_frame, height=20, bg='#1e1e1e', fg='#ffffff', font=('Consolas', 9))
        self.rules_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Load current rules
        self.load_rules_into_text()
        
        # Rules controls
        rules_controls = ttk.Frame(rules_frame)
        rules_controls.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(rules_controls, text="Load from File", 
                  command=self.load_rules_from_file).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(rules_controls, text="Save to File", 
                  command=self.save_rules_to_file).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(rules_controls, text="Reset to Default", 
                  command=self.reset_rules).pack(side=tk.LEFT, padx=5)
    
    def create_adaptive_params_tab(self, notebook):
        """สร้าง Adaptive Parameters tab (ค่าที่ใช้งานจริง)"""
        adaptive_frame = ttk.Frame(notebook)
        notebook.add(adaptive_frame, text="⚙️ Adaptive Params")
        
        # Create scrollable frame
        canvas = tk.Canvas(adaptive_frame, bg='#2b2b2b')
        scrollbar = ttk.Scrollbar(adaptive_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # === 1. Recovery Parameters (การแก้ไม้) ===
        self.create_section_header(scrollable_frame, "🔧 Recovery Parameters (การแก้ไม้)")
        recovery_params = [
            ("ขาดทุนขั้นต่ำ (%)", "adaptive_params.recovery_params.loss_thresholds.min_loss_percent", 
             "float", -0.02, 0.0, "เช่น -0.005 = ขาดทุน 0.5% ของ balance จึงแก้ไม้"),
            
            ("ระยะทาง (pips)", "adaptive_params.recovery_params.loss_thresholds.min_price_distance_pips", 
             "int", 5, 50, "เช่น 10 = ต้องห่าง 10 pips จึงแก้ไม้"),
            
            ("อายุไม้ขั้นต่ำ (วินาที)", "adaptive_params.recovery_params.timing.min_position_age_seconds", 
             "int", 30, 300, "เช่น 60 = รอ 60 วินาทีก่อนแก้ไม้"),
            
            ("ช่วงเช็ค (วินาที)", "adaptive_params.recovery_params.timing.cooldown_between_checks", 
             "int", 5, 60, "เช่น 10 = เช็คทุก 10 วินาที"),
            
            ("Correlation ขั้นต่ำ", "adaptive_params.recovery_params.correlation_thresholds.min_correlation", 
             "float", 0.3, 0.95, "เช่น 0.6 = ต้องมี correlation >= 60%")
        ]
        self.create_parameter_controls(scrollable_frame, recovery_params)
        
        # === 2. Chain Recovery (การแก้ไม้ต่อเนื่อง) ===
        self.create_section_header(scrollable_frame, "🔗 Chain Recovery (แก้ไม้ต่อเนื่อง)")
        chain_params = [
            ("เปิดใช้งาน", "adaptive_params.recovery_params.chain_recovery.enabled", 
             "bool", "เปิด = แก้ไม้ recovery ที่ติดลบต่อได้"),
            
            ("ความลึกสูงสุด", "adaptive_params.recovery_params.chain_recovery.max_chain_depth", 
             "int", 1, 5, "เช่น 2 = แก้ไม้ได้ลึก 2 ชั้น (Original → R1 → R2)"),
            
            ("ขาดทุนสำหรับ Chain (%)", "adaptive_params.recovery_params.chain_recovery.min_loss_percent_for_chain", 
             "float", -0.02, 0.0, "เช่น -0.006 = ขาดทุน 0.6% จึงแก้ไม้ chain")
        ]
        self.create_parameter_controls(scrollable_frame, chain_params)
        
        # === 3. Trailing Stop (ล็อคกำไร) ===
        self.create_section_header(scrollable_frame, "🔒 Trailing Stop (ล็อคกำไร)")
        trailing_params = [
            ("เปิดใช้งาน", "adaptive_params.arbitrage_params.closing.trailing_stop_enabled", 
             "bool", "เปิด = ล็อคกำไรเมื่อราคากลับ"),
            
            ("ระยะ Stop (USD)", "adaptive_params.arbitrage_params.closing.trailing_stop_distance", 
             "float", 5.0, 50.0, "เช่น 10 = ปิดเมื่อลดจาก peak $10"),
            
            ("กำไรขั้นต่ำ (USD)", "adaptive_params.arbitrage_params.closing.min_profit_base", 
             "float", 1.0, 50.0, "เช่น 5 = ต้องกำไร $5 @ $10K balance"),
            
            ("Balance ฐาน (USD)", "adaptive_params.arbitrage_params.closing.min_profit_base_balance", 
             "float", 5000.0, 100000.0, "เช่น 10000 = ฐาน $10K, ถ้า balance เพิ่ม → min profit เพิ่มตาม")
        ]
        self.create_parameter_controls(scrollable_frame, trailing_params)
        
        # === 4. Trend Analysis (วิเคราะห์เทรนด์) ===
        self.create_section_header(scrollable_frame, "📊 Trend Analysis (วิเคราะห์เทรนด์)")
        trend_params = [
            ("เปิดใช้งาน", "adaptive_params.recovery_params.trend_analysis.enabled", 
             "bool", "เปิด = วิเคราะห์ทิศทางตลาดก่อนแก้ไม้"),
            
            ("จำนวน Periods", "adaptive_params.recovery_params.trend_analysis.periods", 
             "int", 20, 200, "เช่น 50 = ดู MA 50 periods"),
            
            ("Confidence ขั้นต่ำ", "adaptive_params.recovery_params.trend_analysis.confidence_threshold", 
             "float", 0.1, 0.9, "เช่น 0.4 = ต้องมั่นใจ 40% จึงใช้ trend")
        ]
        self.create_parameter_controls(scrollable_frame, trend_params)
        
        # === 5. Position Sizing (ขนาดไม้) ===
        self.create_section_header(scrollable_frame, "💰 Position Sizing (ขนาดไม้)")
        sizing_params = [
            ("Lot Multiplier", "adaptive_params.position_sizing.account_tiers.medium.lot_multiplier", 
             "float", 0.5, 3.0, "เช่น 1.0 = ขนาดปกติ, 0.5 = ครึ่งหนึ่ง"),
            
            ("Base Lot Size", "adaptive_params.position_sizing.account_tiers.medium.base_lot_size", 
             "float", 0.01, 1.0, "เช่น 0.1 = ไม้ขนาด 0.1 lot"),
            
            ("Lot สูงสุด (Recovery)", "adaptive_params.recovery_params.dynamic_hedge.max_hedge_lot", 
             "float", 0.1, 5.0, "เช่น 3.0 = recovery ได้สูงสุด 3.0 lot"),
            
            ("Lot ต่ำสุด (Recovery)", "adaptive_params.recovery_params.dynamic_hedge.min_hedge_lot", 
             "float", 0.01, 1.0, "เช่น 0.1 = recovery ต่ำสุด 0.1 lot")
        ]
        self.create_parameter_controls(scrollable_frame, sizing_params)
        
        # === 6. Arbitrage Settings (การตั้งค่า Arbitrage) ===
        self.create_section_header(scrollable_frame, "⚡ Arbitrage Settings")
        arbitrage_params = [
            ("Threshold ขั้นต่ำ", "adaptive_params.arbitrage_params.detection.min_threshold", 
             "float", 0.00001, 0.01, "เช่น 0.0001 = ต้องมีโอกาส arbitrage >= 0.01%"),
            
            ("Triangle สูงสุด", "adaptive_params.arbitrage_params.triangles.max_active_triangles", 
             "int", 1, 10, "เช่น 4 = เปิดได้สูงสุด 4 groups พร้อมกัน"),
            
            ("กำไรขั้นต่ำปิด (USD)", "adaptive_params.arbitrage_params.closing.min_profit_to_close", 
             "float", 1.0, 50.0, "เช่น 5 = ปิดเมื่อกำไร >= $5 (ไม่ scale)")
        ]
        self.create_parameter_controls(scrollable_frame, arbitrage_params)
        
        # === 7. Multi-Armed Bandit (ML) ===
        self.create_section_header(scrollable_frame, "🤖 Multi-Armed Bandit (ML)")
        bandit_params = [
            ("เปิดใช้งาน", "adaptive_params.recovery_params.multi_armed_bandit.enabled", 
             "bool", "เปิด = ใช้ ML เรียนรู้เลือก pair ที่ดีที่สุด"),
            
            ("Exploration Rate", "adaptive_params.recovery_params.multi_armed_bandit.exploration_rate", 
             "float", 0.0, 1.0, "เช่น 0.2 = ทดลอง pair ใหม่ 20%"),
            
            ("Learning Rate", "adaptive_params.recovery_params.multi_armed_bandit.learning_rate", 
             "float", 0.0, 1.0, "เช่น 0.1 = เรียนรู้ช้าๆ แต่มั่นคง")
        ]
        self.create_parameter_controls(scrollable_frame, bandit_params)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_section_header(self, parent, title):
        """สร้าง section header"""
        header_frame = tk.Frame(parent, bg='#3b3b3b', height=30)
        header_frame.pack(fill='x', padx=5, pady=(15, 5))
        header_frame.pack_propagate(False)
        
        tk.Label(
            header_frame,
            text=title,
            font=('Arial', 11, 'bold'),
            bg='#3b3b3b',
            fg='#FFD700'
        ).pack(side='left', padx=10, pady=5)
        
    def create_parameter_controls(self, parent, parameters):
        """Create parameter controls for settings with Thai descriptions"""
        if not hasattr(self, 'parameter_vars'):
            self.parameter_vars = {}
        
        for i, param in enumerate(parameters):
            param_name = param[0]
            param_path = param[1]
            param_type = param[2]
            
            # Create frame for parameter
            param_frame = ttk.Frame(parent)
            param_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # Parameter label
            ttk.Label(param_frame, text=param_name + ":", width=25).pack(side=tk.LEFT, padx=5)
            
            # Get current value
            current_value = self.get_nested_value(self.settings, param_path)
            if current_value is None:
                current_value = 0.0 if param_type == "float" else 0 if param_type == "int" else False
            
            if param_type == "bool":
                # Boolean checkbox
                var = tk.BooleanVar(value=current_value)
                ttk.Checkbutton(param_frame, variable=var).pack(side=tk.LEFT, padx=5)
                
                # Description (if provided)
                if len(param) > 3:
                    description = param[3]
                    desc_label = tk.Label(
                        param_frame,
                        text=f"({description})",
                        font=('Arial', 8),
                        bg='#2b2b2b',
                        fg='#888888'
                    )
                    desc_label.pack(side=tk.LEFT, padx=5)
                
            elif param_type == "choice":
                # Choice combobox
                choices = param[3] if len(param) > 3 else []
                var = tk.StringVar(value=str(current_value))
                ttk.Combobox(param_frame, textvariable=var, values=choices, width=20).pack(side=tk.LEFT, padx=5)
                
            elif param_type == "int":
                # Integer entry
                var = tk.StringVar(value=str(current_value))
                entry = ttk.Entry(param_frame, textvariable=var, width=15)
                entry.pack(side=tk.LEFT, padx=5)
                
                # Add validation with range
                if len(param) > 4:
                    min_val, max_val = param[3], param[4]
                    entry.bind('<FocusOut>', lambda e, v=var, mn=min_val, mx=max_val: self.validate_int_range(v, mn, mx))
                else:
                    entry.bind('<FocusOut>', lambda e, v=var: self.validate_int(v))
                
                # Description (if provided)
                if len(param) > 5:
                    description = param[5]
                    desc_label = tk.Label(
                        param_frame,
                        text=description,
                        font=('Arial', 8),
                        bg='#2b2b2b',
                        fg='#888888',
                        wraplength=300,
                        justify='left'
                    )
                    desc_label.pack(side=tk.LEFT, padx=5)
                
            elif param_type == "float":
                # Float entry
                var = tk.StringVar(value=str(current_value))
                entry = ttk.Entry(param_frame, textvariable=var, width=15)
                entry.pack(side=tk.LEFT, padx=5)
                
                # Add validation with range
                if len(param) > 4:
                    min_val, max_val = param[3], param[4]
                    entry.bind('<FocusOut>', lambda e, v=var, mn=min_val, mx=max_val: self.validate_float_range(v, mn, mx))
                else:
                    entry.bind('<FocusOut>', lambda e, v=var: self.validate_float(v))
                
                # Description (if provided)
                if len(param) > 5:
                    description = param[5]
                    desc_label = tk.Label(
                        param_frame,
                        text=description,
                        font=('Arial', 8),
                        bg='#2b2b2b',
                        fg='#888888',
                        wraplength=300,
                        justify='left'
                    )
                    desc_label.pack(side=tk.LEFT, padx=5)
            
            # Store variable reference
            self.parameter_vars[param_path] = var
    
    def update_broker_settings(self, event=None):
        """Update broker-specific settings display"""
        try:
            # Clear existing widgets
            for widget in self.broker_settings_frame.winfo_children():
                widget.destroy()
            
            broker_type = self.broker_var.get()
            broker_config = self.settings.get('broker_config', {}).get(broker_type, {})
            
            # Create broker-specific controls
            row = 0
            for key, value in broker_config.items():
                ttk.Label(self.broker_settings_frame, text=key.replace('_', ' ').title() + ":").grid(
                    row=row, column=0, padx=5, pady=5, sticky="w")
                
                if isinstance(value, bool):
                    var = tk.BooleanVar(value=value)
                    ttk.Checkbutton(self.broker_settings_frame, variable=var).grid(
                        row=row, column=1, padx=5, pady=5, sticky="w")
                else:
                    var = tk.StringVar(value=str(value))
                    ttk.Entry(self.broker_settings_frame, textvariable=var, width=30).grid(
                        row=row, column=1, padx=5, pady=5, sticky="w")
                
                # Store variable reference
                self.parameter_vars[f"broker_config.{broker_type}.{key}"] = var
                row += 1
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update broker settings: {str(e)}")
    
    def create_control_buttons(self, parent):
        """Create control buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Save", 
                  command=self.save_settings).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Reset", 
                  command=self.reset_settings).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Cancel", 
                  command=self.cancel_settings).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Import", 
                  command=self.import_settings).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(button_frame, text="Export", 
                  command=self.export_settings).pack(side=tk.RIGHT, padx=5)
    
    def get_nested_value(self, data, path):
        """Get value from nested dictionary using dot notation"""
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    def set_nested_value(self, data, path, value):
        """Set value in nested dictionary using dot notation"""
        keys = path.split('.')
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
    
    def validate_int(self, var):
        """Validate integer input"""
        try:
            value = int(var.get())
            var.set(str(value))
        except ValueError:
            var.set("0")
    
    def validate_int_range(self, var, min_val, max_val):
        """Validate integer input with range"""
        try:
            value = int(var.get())
            value = max(min_val, min(max_val, value))
            var.set(str(value))
        except ValueError:
            var.set(str(min_val))
    
    def validate_float(self, var):
        """Validate float input"""
        try:
            value = float(var.get())
            var.set(str(value))
        except ValueError:
            var.set("0.0")
    
    def validate_float_range(self, var, min_val, max_val):
        """Validate float input with range"""
        try:
            value = float(var.get())
            value = max(min_val, min(max_val, value))
            var.set(f"{value:.6f}".rstrip('0').rstrip('.'))
        except ValueError:
            var.set(str(min_val))
    
    def load_rules_into_text(self):
        """Load rules into text area"""
        try:
            rules_json = json.dumps(self.settings.get('rules', {}), indent=2)
            self.rules_text.delete(1.0, tk.END)
            self.rules_text.insert(1.0, rules_json)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load rules: {str(e)}")
    
    def load_rules_from_file(self):
        """Load rules from file"""
        try:
            filename = filedialog.askopenfilename(
                title="Load Rules File",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                with open(filename, 'r') as f:
                    rules = json.load(f)
                
                self.settings['rules'] = rules
                self.load_rules_into_text()
                messagebox.showinfo("Success", "Rules loaded successfully")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load rules: {str(e)}")
    
    def save_rules_to_file(self):
        """Save rules to file"""
        try:
            filename = filedialog.asksaveasfilename(
                title="Save Rules File",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                rules_text = self.rules_text.get(1.0, tk.END).strip()
                rules = json.loads(rules_text)
                
                with open(filename, 'w') as f:
                    json.dump(rules, f, indent=2)
                
                self.settings['rules'] = rules
                messagebox.showinfo("Success", "Rules saved successfully")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save rules: {str(e)}")
    
    def reset_rules(self):
        """Reset rules to default"""
        try:
            if messagebox.askyesno("Confirm", "Reset rules to default? This will lose all custom rules."):
                # Load default rules
                with open('config/rules.json', 'r') as f:
                    default_rules = json.load(f)
                
                self.settings['rules'] = default_rules
                self.load_rules_into_text()
                messagebox.showinfo("Success", "Rules reset to default")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset rules: {str(e)}")
    
    def save_settings(self):
        """Save all settings"""
        try:
            # Update settings from UI
            for param_path, var in self.parameter_vars.items():
                value = var.get()
                
                # Convert value based on type
                if isinstance(value, bool):
                    # Already boolean
                    pass
                elif param_path.startswith('broker_config.'):
                    # Broker config values
                    if isinstance(value, str):
                        if value.lower() in ['true', 'false']:
                            value = value.lower() == 'true'
                        elif value.isdigit():
                            value = int(value)
                        elif value.replace('.', '').replace('-', '').isdigit():
                            value = float(value)
                elif param_path.startswith('adaptive_params.'):
                    # Adaptive params values
                    if isinstance(value, str):
                        # Check for boolean
                        if value.lower() in ['true', 'false', '1', '0']:
                            value = value.lower() in ['true', '1']
                        # Check for int (no decimal point and no negative sign after first char)
                        elif '.' not in value and value.lstrip('-').isdigit():
                            value = int(value)
                        # Check for float
                        elif value.replace('.', '').replace('-', '').isdigit():
                            value = float(value)
                elif param_path.endswith('.learning_enabled'):
                    if isinstance(value, str):
                        value = value.lower() == 'true'
                elif param_path.endswith(('.max_triangles', '.max_grid_levels', '.position_hold_time', 
                                        '.max_rules_per_category', '.performance_lookback_days')):
                    value = int(value) if isinstance(value, str) else value
                elif param_path.endswith(('.base_lot_size', '.min_arbitrage_threshold', '.max_spread',
                                        '.max_drawdown_percent', '.position_size_multiplier', 
                                        '.take_profit_percent', '.confidence_threshold')):
                    value = float(value) if isinstance(value, str) else value
                
                self.set_nested_value(self.settings, param_path, value)
            
            # Save to files
            self.save_settings_to_files()
            
            messagebox.showinfo("สำเร็จ", "บันทึกการตั้งค่าเรียบร้อยแล้ว!\n\n⚠️ กรุณา Restart ระบบเพื่อใช้งานค่าใหม่")
            self.settings_window.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
    
    def save_settings_to_files(self):
        """Save settings to configuration files"""
        try:
            # Save main settings
            main_settings = {k: v for k, v in self.settings.items() if k not in ['broker_config', 'rules', 'adaptive_params']}
            with open('config/settings.json', 'w', encoding='utf-8') as f:
                json.dump(main_settings, f, indent=2, ensure_ascii=False)
            
            # Save broker config
            with open('config/broker_config.json', 'w', encoding='utf-8') as f:
                json.dump(self.settings.get('broker_config', {}), f, indent=2, ensure_ascii=False)
            
            # Save rules (if exists)
            if self.settings.get('rules'):
                with open('config/rules.json', 'w', encoding='utf-8') as f:
                    json.dump(self.settings.get('rules', {}), f, indent=2, ensure_ascii=False)
            
            # Save adaptive params
            with open('config/adaptive_params.json', 'w', encoding='utf-8') as f:
                json.dump(self.settings.get('adaptive_params', {}), f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            raise Exception(f"Failed to save settings to files: {str(e)}")
    
    def reset_settings(self):
        """Reset settings to original values"""
        try:
            if messagebox.askyesno("Confirm", "Reset all settings to original values?"):
                self.settings = json.loads(json.dumps(self.original_settings))
                self.settings_window.destroy()
                SettingsWindow(self.parent)  # Reopen with reset settings
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset settings: {str(e)}")
    
    def cancel_settings(self):
        """Cancel settings changes"""
        self.settings_window.destroy()
    
    def import_settings(self):
        """Import settings from file"""
        try:
            filename = filedialog.askopenfilename(
                title="Import Settings",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                with open(filename, 'r') as f:
                    imported_settings = json.load(f)
                
                self.settings.update(imported_settings)
                messagebox.showinfo("Success", "Settings imported successfully")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import settings: {str(e)}")
    
    def export_settings(self):
        """Export settings to file"""
        try:
            filename = filedialog.asksaveasfilename(
                title="Export Settings",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                with open(filename, 'w') as f:
                    json.dump(self.settings, f, indent=2)
                
                messagebox.showinfo("Success", "Settings exported successfully")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export settings: {str(e)}")
    
    def show(self):
        """Show the settings window"""
        self.settings_window.deiconify()
        self.settings_window.lift()
