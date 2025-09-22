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
        self.settings_window.title("System Settings")
        self.settings_window.geometry("800x600")
        self.settings_window.configure(bg='#2b2b2b')
        
        # Load settings
        self.load_settings()
        
        # Setup UI
        self.setup_ui()
        
    def load_settings(self):
        """Load settings from configuration files"""
        try:
            # Load main settings
            with open('config/settings.json', 'r') as f:
                self.settings = json.load(f)
            
            # Load broker config
            with open('config/broker_config.json', 'r') as f:
                broker_config = json.load(f)
                self.settings['broker_config'] = broker_config
            
            # Load rules
            with open('config/rules.json', 'r') as f:
                rules = json.load(f)
                self.settings['rules'] = rules
            
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
                "max_daily_loss": 1000,
                "max_drawdown_percent": 30,
                "position_size_multiplier": 1.5,
                "stop_loss_percent": 2.0,
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
            ("Max Daily Loss ($)", "risk_management.max_daily_loss", "float", 100, 10000),
            ("Max Drawdown %", "risk_management.max_drawdown_percent", "float", 5, 100),
            ("Position Size Multiplier", "risk_management.position_size_multiplier", "float", 0.1, 5.0),
            ("Stop Loss %", "risk_management.stop_loss_percent", "float", 0.1, 10.0),
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
        
    def create_parameter_controls(self, parent, parameters):
        """Create parameter controls for settings"""
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
            
            if param_type == "bool":
                # Boolean checkbox
                var = tk.BooleanVar(value=current_value)
                ttk.Checkbutton(param_frame, variable=var).pack(side=tk.LEFT, padx=5)
                
            elif param_type == "choice":
                # Choice combobox
                choices = param[3] if len(param) > 3 else []
                var = tk.StringVar(value=str(current_value))
                ttk.Combobox(param_frame, textvariable=var, values=choices, width=20).pack(side=tk.LEFT, padx=5)
                
            elif param_type == "int":
                # Integer entry
                var = tk.StringVar(value=str(current_value))
                entry = ttk.Entry(param_frame, textvariable=var, width=20)
                entry.pack(side=tk.LEFT, padx=5)
                
                # Add validation
                entry.bind('<FocusOut>', lambda e, v=var: self.validate_int(v))
                
            elif param_type == "float":
                # Float entry
                var = tk.StringVar(value=str(current_value))
                entry = ttk.Entry(param_frame, textvariable=var, width=20)
                entry.pack(side=tk.LEFT, padx=5)
                
                # Add validation
                entry.bind('<FocusOut>', lambda e, v=var: self.validate_float(v))
            
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
    
    def validate_float(self, var):
        """Validate float input"""
        try:
            value = float(var.get())
            var.set(str(value))
        except ValueError:
            var.set("0.0")
    
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
                if param_path.startswith('broker_config.'):
                    # Broker config values
                    if value.lower() in ['true', 'false']:
                        value = value.lower() == 'true'
                    elif value.isdigit():
                        value = int(value)
                    elif value.replace('.', '').isdigit():
                        value = float(value)
                elif param_path.endswith('.learning_enabled'):
                    value = value.lower() == 'true'
                elif param_path.endswith(('.max_triangles', '.max_grid_levels', '.position_hold_time', 
                                        '.max_daily_loss', '.max_rules_per_category', '.performance_lookback_days')):
                    value = int(value)
                elif param_path.endswith(('.base_lot_size', '.min_arbitrage_threshold', '.max_spread',
                                        '.max_drawdown_percent', '.position_size_multiplier', 
                                        '.stop_loss_percent', '.take_profit_percent', '.confidence_threshold')):
                    value = float(value)
                
                self.set_nested_value(self.settings, param_path, value)
            
            # Save to files
            self.save_settings_to_files()
            
            messagebox.showinfo("Success", "Settings saved successfully")
            self.settings_window.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
    
    def save_settings_to_files(self):
        """Save settings to configuration files"""
        try:
            # Save main settings
            main_settings = {k: v for k, v in self.settings.items() if k not in ['broker_config', 'rules']}
            with open('config/settings.json', 'w') as f:
                json.dump(main_settings, f, indent=2)
            
            # Save broker config
            with open('config/broker_config.json', 'w') as f:
                json.dump(self.settings.get('broker_config', {}), f, indent=2)
            
            # Save rules
            with open('config/rules.json', 'w') as f:
                json.dump(self.settings.get('rules', {}), f, indent=2)
                
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
