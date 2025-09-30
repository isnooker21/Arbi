"""
หน้าต่างตั้งค่าระบบเทรด - Adaptive Parameters
===============================================

Author: AI Trading System
Version: 2.0 - Simplified & Beautiful
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from typing import Dict, Any

class SettingsWindow:
    def __init__(self, parent):
        self.parent = parent
        self.settings = {}
        self.original_settings = {}
        self.parameter_vars = {}
        
        # Create settings window
        self.settings_window = tk.Toplevel(parent)
        self.settings_window.title("⚙️ การตั้งค่าระบบ - Adaptive Parameters")
        self.settings_window.geometry("1200x800")
        self.settings_window.configure(bg='#1e1e1e')
        
        # Load settings
        self.load_settings()
        
        # Setup UI
        self.setup_ui()
        
    def load_settings(self):
        """Load adaptive_params.json"""
        try:
            with open('config/adaptive_params.json', 'r', encoding='utf-8') as f:
                self.settings = json.load(f)
            
            # Store original settings for comparison
            self.original_settings = json.loads(json.dumps(self.settings))
            
        except Exception as e:
            messagebox.showerror("Error", f"ไม่สามารถโหลดไฟล์ได้: {str(e)}")
            self.settings = {}
            self.original_settings = {}
    
    def setup_ui(self):
        """Setup the settings interface"""
        # Header
        header_frame = tk.Frame(self.settings_window, bg='#2d2d2d', height=60)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        tk.Label(
            header_frame,
            text="⚙️ การตั้งค่าระบบ Adaptive Parameters",
            font=('Arial', 16, 'bold'),
            bg='#2d2d2d',
            fg='#FFD700'
        ).pack(side='left', padx=20, pady=15)
        
        # Control buttons in header
        btn_frame = tk.Frame(header_frame, bg='#2d2d2d')
        btn_frame.pack(side='right', padx=20, pady=15)
        
        tk.Button(
            btn_frame,
            text="💾 บันทึก",
            command=self.save_settings,
            bg='#4CAF50',
            fg='white',
            font=('Arial', 11, 'bold'),
            padx=20,
            pady=8,
            relief='flat',
            cursor='hand2'
        ).pack(side='left', padx=5)
        
        tk.Button(
            btn_frame,
            text="🔄 Reset",
            command=self.reset_settings,
            bg='#FF9800',
            fg='white',
            font=('Arial', 11, 'bold'),
            padx=20,
            pady=8,
            relief='flat',
            cursor='hand2'
        ).pack(side='left', padx=5)
        
        tk.Button(
            btn_frame,
            text="❌ ยกเลิก",
            command=self.cancel_settings,
            bg='#666666',
            fg='white',
            font=('Arial', 11, 'bold'),
            padx=20,
            pady=8,
            relief='flat',
            cursor='hand2'
        ).pack(side='left', padx=5)
        
        # Main content area with scrollbar
        main_container = tk.Frame(self.settings_window, bg='#1e1e1e')
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Create canvas for scrolling
        canvas = tk.Canvas(main_container, bg='#1e1e1e', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#1e1e1e')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # === Create 2-column layout ===
        left_column = tk.Frame(scrollable_frame, bg='#1e1e1e')
        left_column.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        right_column = tk.Frame(scrollable_frame, bg='#1e1e1e')
        right_column.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        # === LEFT COLUMN ===
        
        # 1. Recovery Parameters
        self.create_section(left_column, "🔧 Recovery Parameters (การแก้ไม้)", [
            ("ขาดทุนขั้นต่ำ (%)", "recovery_params.loss_thresholds.min_loss_percent", 
             "float", -0.02, 0.0, "เช่น -0.005 = ขาดทุน 0.5% ของ balance จึงแก้ไม้"),
            ("ระยะทางขั้นต่ำ (pips)", "recovery_params.loss_thresholds.min_price_distance_pips", 
             "int", 5, 50, "เช่น 10 = ราคาต้องห่าง 10 pips จากจุดเปิดไม้"),
            ("อายุไม้ขั้นต่ำ (วินาที)", "recovery_params.timing.min_position_age_seconds", 
             "int", 30, 300, "เช่น 60 = รอให้ไม้อายุครบ 60 วินาที"),
            ("ช่วงเช็คระบบ (วินาที)", "recovery_params.timing.cooldown_between_checks", 
             "int", 5, 60, "เช่น 10 = ระบบเช็คทุก 10 วินาที"),
            ("Correlation ขั้นต่ำ", "recovery_params.correlation_thresholds.min_correlation", 
             "float", 0.3, 0.95, "เช่น 0.6 = คู่เงินต้องมี correlation >= 60%")
        ])
        
        # 2. Chain Recovery
        self.create_section(left_column, "🔗 Chain Recovery (แก้ไม้ต่อเนื่อง)", [
            ("เปิดใช้งาน", "recovery_params.chain_recovery.enabled", 
             "bool", "เปิด = ถ้าไม้ recovery ติดลบจะแก้ไม้ต่อให้อีก"),
            ("ความลึกสูงสุด", "recovery_params.chain_recovery.max_chain_depth", 
             "int", 1, 5, "เช่น 2 = แก้ไม้ได้ลึก 2 ชั้น"),
            ("ขาดทุนสำหรับ Chain (%)", "recovery_params.chain_recovery.min_loss_percent_for_chain", 
             "float", -0.02, 0.0, "เช่น -0.006 = ไม้ recovery ขาดทุน 0.6%")
        ])
        
        # 3. Trailing Stop
        self.create_section(left_column, "🔒 Trailing Stop (ล็อคกำไร)", [
            ("เปิดใช้งาน", "arbitrage_params.closing.trailing_stop_enabled", 
             "bool", "เปิด = ล็อคกำไรอัตโนมัติเมื่อราคากลับ"),
            ("ระยะ Stop (USD)", "arbitrage_params.closing.trailing_stop_distance", 
             "float", 5.0, 50.0, "เช่น 10 = ถ้ากำไรลดจาก peak $10 ก็ปิด"),
            ("กำไรขั้นต่ำ (USD)", "arbitrage_params.closing.min_profit_base", 
             "float", 1.0, 50.0, "เช่น 5 = ต้องกำไร $5 ถึงเริ่ม trailing"),
            ("Balance ฐาน (USD)", "arbitrage_params.closing.min_profit_base_balance", 
             "float", 5000.0, 100000.0, "เช่น 10000 = ฐาน $10K")
        ])
        
        # 4. Trend Analysis
        self.create_section(left_column, "📊 Trend Analysis (วิเคราะห์เทรนด์)", [
            ("เปิดใช้งาน", "recovery_params.trend_analysis.enabled", 
             "bool", "เปิด = วิเคราะห์ทิศทางตลาดก่อนแก้ไม้"),
            ("จำนวน MA Periods", "recovery_params.trend_analysis.periods", 
             "int", 20, 200, "เช่น 50 = ใช้ Moving Average 50 periods"),
            ("Confidence ขั้นต่ำ", "recovery_params.trend_analysis.confidence_threshold", 
             "float", 0.1, 0.9, "เช่น 0.4 = ต้องมั่นใจ 40%")
        ])
        
        # === RIGHT COLUMN ===
        
        # 5. Position Sizing
        self.create_section(right_column, "💰 Position Sizing (ขนาดไม้)", [
            ("Lot Multiplier", "position_sizing.account_tiers.medium.lot_multiplier", 
             "float", 0.5, 3.0, "เช่น 1.0 = ขนาดปกติ, 0.5 = ลดครึ่ง"),
            ("Base Lot Size", "position_sizing.account_tiers.medium.base_lot_size", 
             "float", 0.01, 1.0, "เช่น 0.1 = เปิดไม้ 0.1 lot"),
            ("Lot สูงสุด (Recovery)", "recovery_params.dynamic_hedge.max_hedge_lot", 
             "float", 0.1, 5.0, "เช่น 3.0 = recovery สูงสุด 3.0 lot"),
            ("Lot ต่ำสุด (Recovery)", "recovery_params.dynamic_hedge.min_hedge_lot", 
             "float", 0.01, 1.0, "เช่น 0.1 = recovery ต่ำสุด 0.1 lot")
        ])
        
        # 6. Arbitrage Settings
        self.create_section(right_column, "⚡ Arbitrage Settings", [
            ("Threshold ขั้นต่ำ", "arbitrage_params.detection.min_threshold", 
             "float", 0.00001, 0.01, "เช่น 0.0001 = ต้องมีส่วนต่าง >= 0.01%"),
            ("Triangle สูงสุด", "arbitrage_params.triangles.max_active_triangles", 
             "int", 1, 10, "เช่น 4 = เปิดได้สูงสุด 4 groups"),
            ("Spread Tolerance", "arbitrage_params.detection.spread_tolerance", 
             "float", 0.1, 2.0, "เช่น 0.5 = ยอมรับ spread 0.5 pips")
        ])
        
        # 7. Multi-Armed Bandit
        self.create_section(right_column, "🤖 Multi-Armed Bandit (ML)", [
            ("เปิดใช้งาน ML", "recovery_params.multi_armed_bandit.enabled", 
             "bool", "เปิด = ระบบเรียนรู้เลือก pair อัตโนมัติ"),
            ("Exploration Rate", "recovery_params.multi_armed_bandit.exploration_rate", 
             "float", 0.0, 1.0, "เช่น 0.2 = ทดลอง pair ใหม่ 20%"),
            ("Learning Rate", "recovery_params.multi_armed_bandit.learning_rate", 
             "float", 0.0, 1.0, "เช่น 0.1 = เรียนรู้ช้าๆ แต่มั่นคง")
        ])
        
        # 8. Advanced Settings
        self.create_section(right_column, "🎯 Advanced Settings", [
            ("Max Position Size", "position_sizing.account_tiers.medium.max_position_size", 
             "float", 1.0, 20.0, "เช่น 5.0 = เปิดได้สูงสุด 5.0 lot"),
            ("Risk per Trade (%)", "position_sizing.risk_management.risk_per_trade", 
             "float", 0.001, 0.05, "เช่น 0.015 = เสี่ยง 1.5% ต่อไม้"),
            ("Max Groups", "position_sizing.risk_management.max_concurrent_groups", 
             "int", 1, 10, "เช่น 4 = เปิดได้สูงสุด 4 groups")
        ])
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_section(self, parent, title, parameters):
        """สร้าง section พร้อม parameters"""
        section_frame = tk.Frame(parent, bg='#2d2d2d', relief='raised', bd=2)
        section_frame.pack(fill='x', pady=(0, 20))
        
        # Section header
        header_frame = tk.Frame(section_frame, bg='#3d3d3d', height=45)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        tk.Label(
            header_frame,
            text=title,
            font=('Arial', 12, 'bold'),
            bg='#3d3d3d',
            fg='#FFD700'
        ).pack(side='left', padx=15, pady=10)
        
        # Parameters container
        params_container = tk.Frame(section_frame, bg='#2d2d2d')
        params_container.pack(fill='x', padx=15, pady=15)
        
        # Create parameters
        for param in parameters:
            self.create_parameter_row(params_container, param)
    
    def create_parameter_row(self, parent, param):
        """สร้างแถวสำหรับแต่ละ parameter"""
        param_name = param[0]
        param_path = param[1]
        param_type = param[2]
        
        # Main row frame
        row_frame = tk.Frame(parent, bg='#2d2d2d')
        row_frame.pack(fill='x', pady=8)
        
        # Label frame (left side)
        label_frame = tk.Frame(row_frame, bg='#2d2d2d', width=300)
        label_frame.pack(side='left', fill='y')
        label_frame.pack_propagate(False)
        
        tk.Label(
            label_frame,
            text=param_name,
            font=('Arial', 10, 'bold'),
            bg='#2d2d2d',
            fg='#FFFFFF',
            anchor='w'
        ).pack(side='left', padx=(0, 10))
        
        # Input frame (middle)
        input_frame = tk.Frame(row_frame, bg='#2d2d2d', width=150)
        input_frame.pack(side='left')
        input_frame.pack_propagate(False)
        
        # Get current value
        current_value = self.get_nested_value(self.settings, param_path)
        if current_value is None:
            current_value = 0.0 if param_type == "float" else 0 if param_type == "int" else False
        
        if param_type == "bool":
            # Boolean checkbox with custom style
            var = tk.BooleanVar(value=current_value)
            cb = tk.Checkbutton(
                input_frame,
                variable=var,
                bg='#2d2d2d',
                fg='#FFFFFF',
                selectcolor='#4CAF50',
                activebackground='#2d2d2d',
                font=('Arial', 10)
            )
            cb.pack(side='left', padx=5)
            
            # Status label
            status_label = tk.Label(
                input_frame,
                text="✅ เปิด" if current_value else "❌ ปิด",
                font=('Arial', 9, 'bold'),
                bg='#2d2d2d',
                fg='#4CAF50' if current_value else '#FF5252'
            )
            status_label.pack(side='left', padx=5)
            
            # Update status when checkbox changes
            def update_status(*args):
                is_enabled = var.get()
                status_label.config(
                    text="✅ เปิด" if is_enabled else "❌ ปิด",
                    fg='#4CAF50' if is_enabled else '#FF5252'
                )
            var.trace('w', update_status)
            
        elif param_type == "int" or param_type == "float":
            # Number entry with custom style
            var = tk.StringVar(value=str(current_value))
            entry = tk.Entry(
                input_frame,
                textvariable=var,
                width=15,
                font=('Consolas', 10),
                bg='#3d3d3d',
                fg='#FFFFFF',
                insertbackground='#FFFFFF',
                relief='flat',
                bd=5
            )
            entry.pack(side='left', padx=5)
            
            # Add validation with range
            if len(param) > 4:
                min_val, max_val = param[3], param[4]
                if param_type == "int":
                    entry.bind('<FocusOut>', lambda e, v=var, mn=min_val, mx=max_val: self.validate_int_range(v, mn, mx))
                else:
                    entry.bind('<FocusOut>', lambda e, v=var, mn=min_val, mx=max_val: self.validate_float_range(v, mn, mx))
            
            # Range label
            if len(param) > 4:
                range_label = tk.Label(
                    input_frame,
                    text=f"({param[3]} ถึง {param[4]})",
                    font=('Arial', 8),
                    bg='#2d2d2d',
                    fg='#888888'
                )
                range_label.pack(side='left', padx=5)
        
        # Description frame (right side)
        if len(param) > 5:
            description = param[5]
            desc_label = tk.Label(
                row_frame,
                text=description,
                font=('Arial', 9),
                bg='#2d2d2d',
                fg='#AAAAAA',
                wraplength=400,
                justify='left'
            )
            desc_label.pack(side='left', padx=15, fill='x', expand=True)
        
        # Store variable reference
        self.parameter_vars[param_path] = var
    
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
    
    def validate_int_range(self, var, min_val, max_val):
        """Validate integer input with range"""
        try:
            value = int(var.get())
            value = max(min_val, min(max_val, value))
            var.set(str(value))
        except ValueError:
            var.set(str(min_val))
    
    def validate_float_range(self, var, min_val, max_val):
        """Validate float input with range"""
        try:
            value = float(var.get())
            value = max(min_val, min(max_val, value))
            if abs(value) < 0.01:
                var.set(f"{value:.6f}".rstrip('0').rstrip('.'))
            else:
                var.set(f"{value:.4f}".rstrip('0').rstrip('.'))
        except ValueError:
            var.set(str(min_val))
    
    def save_settings(self):
        """Save all settings to adaptive_params.json"""
        try:
            # Update settings from UI
            for param_path, var in self.parameter_vars.items():
                value = var.get()
                
                # Convert value based on type
                if isinstance(value, bool):
                    pass
                elif isinstance(value, str):
                    if value.lower() in ['true', 'false', '1', '0']:
                        value = value.lower() in ['true', '1']
                    elif '.' not in value and value.lstrip('-').isdigit():
                        value = int(value)
                    elif value.replace('.', '', 1).replace('-', '', 1).isdigit():
                        value = float(value)
                
                self.set_nested_value(self.settings, param_path, value)
            
            # Save to file
            with open('config/adaptive_params.json', 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo(
                "✅ สำเร็จ", 
                "บันทึกการตั้งค่าเรียบร้อยแล้ว!\n\n⚠️ กรุณา Restart ระบบเพื่อใช้งานค่าใหม่"
            )
            self.settings_window.destroy()
            
        except Exception as e:
            messagebox.showerror("❌ Error", f"ไม่สามารถบันทึกได้: {str(e)}")
    
    def reset_settings(self):
        """Reset settings to original values"""
        try:
            if messagebox.askyesno("⚠️ ยืนยัน", "Reset ค่าทั้งหมดกลับเป็นค่าเดิม?"):
                self.settings = json.loads(json.dumps(self.original_settings))
                self.settings_window.destroy()
                SettingsWindow(self.parent)
                
        except Exception as e:
            messagebox.showerror("Error", f"ไม่สามารถ reset ได้: {str(e)}")
    
    def cancel_settings(self):
        """Cancel settings changes"""
        if self.settings != self.original_settings:
            if messagebox.askyesno("⚠️ ยืนยัน", "มีการเปลี่ยนแปลงที่ยังไม่ได้บันทึก\n\nต้องการปิดหน้าต่างโดยไม่บันทึกใช่หรือไม่?"):
                self.settings_window.destroy()
        else:
            self.settings_window.destroy()
    
    def show(self):
        """Show the settings window"""
        self.settings_window.deiconify()
        self.settings_window.lift()
