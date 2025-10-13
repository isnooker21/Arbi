import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import threading
import time
from datetime import datetime

# Import theme
from .theme import TradingTheme

class MainWindow:
    def __init__(self, trading_system=None):
        self.root = tk.Tk()
        self.root.title("🎯 ArbiTrader - Colorful & Beautiful")
        self.root.geometry("1600x1000")
        self.root.configure(bg='#0a0a0a')
        self.root.resizable(True, True)
        
        # Add window styling
        self.root.attributes('-alpha', 0.98)
        
        # Add colorful border effect
        self.root.configure(highlightthickness=3, highlightbackground='#4ECDC4')
        
        # Center window
        self.center_window()
        
        # Initialize variables
        self.trading_system = trading_system
        self.current_mode = "normal"  # default mode
        self.mode_buttons = {}
        self.is_connected = False
        
        # Apply theme
        TradingTheme.apply_theme(self.root)
        
        # Setup UI
        self.setup_ui()
        
        # Load current mode and start updates
        self.load_current_mode()
        self.start_periodic_updates()
        
        print("✅ Professional Main Window initialized")
    
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_ui(self):
        """Setup the main UI"""
        # Main container
        self.main_frame = tk.Frame(self.root, bg='#0a0a0a')
        self.main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create sections
        self.create_header()
        self.create_mode_selection()
        self.create_status_display()
        self.create_action_buttons()
        self.create_footer()
    
    def create_header(self):
        """Create header section"""
        # Header frame
        header_frame = tk.Frame(self.main_frame, bg='#2d3748', relief='flat', bd=0)
        header_frame.pack(fill='x', pady=(0, 20))
        
        # Title section
        title_frame = tk.Frame(header_frame, bg='#2d3748')
        title_frame.pack(side='left', padx=20, pady=15)
        
        title_label = tk.Label(
            title_frame,
            text="🚀 ArbiTrader",
            font=('Segoe UI', 24, 'bold'),
            bg='#2d3748',
            fg='#ffffff'
        )
        title_label.pack(side='left')
        
        subtitle_label = tk.Label(
            title_frame,
            text="Colorful & Beautiful",
            font=('Segoe UI', 14, 'italic'),
            bg='#2d3748',
            fg='#a0aec0'
        )
        subtitle_label.pack(side='left', padx=(10, 0))
        
        # Connection section
        connection_frame = tk.Frame(header_frame, bg='#2d3748')
        connection_frame.pack(side='right', padx=20, pady=15)
        
        # Connection status
        self.connection_status_label = tk.Label(
            connection_frame,
            text="🔴 ไม่ได้เชื่อมต่อ",
            font=('Segoe UI', 12, 'bold'),
            bg='#2d3748',
            fg='#e53e3e'
        )
        self.connection_status_label.pack(side='right', padx=(0, 10))
        
        # Connect button
        self.connect_btn = tk.Button(
            connection_frame,
            text="🔌 เชื่อมต่อ",
            font=('Segoe UI', 12, 'bold'),
            bg='#38a169',
            fg='white',
            relief='flat',
            bd=0,
            padx=20,
            pady=8,
            command=self.toggle_connection
        )
        self.connect_btn.pack(side='right')
        
        # Status indicator
        status_label = tk.Label(
            connection_frame,
            text="🟢 Ready v3.0 Colorful",
            font=('Segoe UI', 10),
            bg='#2d3748',
            fg='#38a169'
        )
        status_label.pack(side='right', padx=(0, 15))
    
    def create_mode_selection(self):
        """Create mode selection section"""
        # Mode selection frame
        mode_frame = tk.Frame(self.main_frame, bg='#1a1a1a', relief='flat', bd=1)
        mode_frame.pack(fill='x', pady=(0, 20))
        
        # Title
        title_frame = tk.Frame(mode_frame, bg='#1a1a1a')
        title_frame.pack(fill='x', padx=20, pady=(15, 10))
        
        title_label = tk.Label(
            title_frame,
            text="⚙️ เลือกโหมดการเทรด",
            font=('Segoe UI', 16, 'bold'),
            bg='#1a1a1a',
            fg='#ffffff'
        )
        title_label.pack(side='left')
        
        # Mode buttons frame
        buttons_frame = tk.Frame(mode_frame, bg='#1a1a1a')
        buttons_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        # Mode configurations
        modes = [
            ("racing", "🔥 ซิ่ง", "(เสียงสูงสุด)", "#e53e3e"),
            ("fast", "⚡ ซิ่งกลาง", "(เสียงปานกลาง)", "#dd6b20"),
            ("normal", "⚖️ ปกติ", "(สมดุล)", "#38a169"),
            ("safe", "🛡️ เซฟ", "(ปลอดภัย)", "#3182ce"),
            ("custom", "🔧 Custom", "(ปรับแต่ง)", "#805ad5")
        ]
        
        for i, (mode, text, desc, color) in enumerate(modes):
            btn = tk.Button(
                buttons_frame,
                text=f"{text}\n{desc}",
                font=('Segoe UI', 11, 'bold'),
                bg=color,
                fg='white',
                relief='flat',
                bd=0,
                padx=20,
                pady=15,
                command=lambda m=mode: self.select_mode(m)
            )
            btn.pack(side='left', padx=(0, 10) if i < len(modes)-1 else 0, fill='x', expand=True)
            self.mode_buttons[mode] = btn
        
        # Custom settings button (initially hidden)
        self.custom_settings_btn = tk.Button(
            mode_frame,
            text="🔧 ปรับแต่ง Custom Settings",
            font=('Segoe UI', 10),
            bg='#805ad5',
            fg='white',
            relief='flat',
            bd=0,
            padx=15,
            pady=8,
            command=self.open_custom_settings,
            state='disabled'
        )
        # Don't pack initially - will be shown when Custom mode is selected
    
    def select_mode(self, mode):
        """Select trading mode"""
        try:
            print(f"✅ Selected mode: {mode}")
            
            # Update button states
            for m, btn in self.mode_buttons.items():
                if m == mode:
                    # Highlight selected mode
                    btn.config(relief='raised', bd=2)
                else:
                    # Reset other buttons
                    btn.config(relief='flat', bd=0)
            
            # Update current mode
            self.current_mode = mode
            
            # Show/hide custom settings button
            if mode == "custom":
                self.custom_settings_btn.pack(pady=(0, 15), padx=20)
                self.custom_settings_btn.config(state='normal')
            else:
                self.custom_settings_btn.pack_forget()
                self.custom_settings_btn.config(state='disabled')
            
            # Apply mode settings
            self.apply_mode_settings(mode)
            
        except Exception as e:
            print(f"❌ Error selecting mode: {e}")
    
    def apply_mode_settings(self, mode):
        """Apply settings for selected mode"""
        try:
            print(f"📋 Applying {self.get_mode_color(mode)} {mode}")
            
            # Mode configurations
            mode_configs = {
                "racing": {
                    "min_threshold": 0.00001,
                    "commission_rate": 0.00001,
                    "max_active_triangles": 5,
                    "trailing_stop_distance": 20.0,
                    "description": "เสียงสูงสุด ไม่ปิดล็อคอะไรเลย"
                },
                "fast": {
                    "min_threshold": 0.00003,
                    "commission_rate": 0.00003,
                    "max_active_triangles": 4,
                    "trailing_stop_distance": 25.0,
                    "description": "เสียงปานกลาง แก้ไม้น้อยกว่า"
                },
                "normal": {
                    "min_threshold": 0.00005,
                    "commission_rate": 0.00005,
                    "max_active_triangles": 3,
                    "trailing_stop_distance": 30.0,
                    "description": "ค่ากลางที่สุด สมดุลระหว่างกำไรและความเสี่ยง"
                },
                "safe": {
                    "min_threshold": 0.00008,
                    "commission_rate": 0.00008,
                    "max_active_triangles": 2,
                    "trailing_stop_distance": 40.0,
                    "description": "รันแบบปลอดภัย ความเสี่ยงต่ำสุด"
                },
                "custom": {
                    "min_threshold": 0.00005,
                    "commission_rate": 0.00005,
                    "max_active_triangles": 3,
                    "trailing_stop_distance": 30.0,
                    "description": "ปรับแต่งตามต้องการ"
                }
            }
            
            if mode in mode_configs:
                config = mode_configs[mode]
                print(f"📝 {config['description']}")
                
                # Save to config file (except custom mode)
                if mode != "custom":
                    self.save_mode_to_config(mode, config)
                    print(f"✅ Mode {mode} saved to config")
                
                # Update current mode label
                if hasattr(self, 'current_mode_label'):
                    self.current_mode_label.config(text=mode)
            
        except Exception as e:
            print(f"❌ Error applying mode settings: {e}")
    
    def get_mode_color(self, mode):
        """Get color for mode"""
        colors = {
            "racing": "🔥",
            "fast": "⚡", 
            "normal": "⚖️",
            "safe": "🛡️",
            "custom": "🔧"
        }
        return colors.get(mode, "⚖️")
    
    def save_mode_to_config(self, mode, config):
        """Save mode configuration to file"""
        try:
            config_file = "config/adaptive_params.json"
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}
            
            # Update nested values
            self.set_nested_value(data, "arbitrage.min_threshold", config["min_threshold"])
            self.set_nested_value(data, "arbitrage.commission_rate", config["commission_rate"])
            self.set_nested_value(data, "arbitrage.max_active_triangles", config["max_active_triangles"])
            self.set_nested_value(data, "risk.trailing_stop_distance", config["trailing_stop_distance"])
            
            # Save back to file
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"❌ Error saving mode config: {e}")
    
    def set_nested_value(self, data, path, value):
        """Set nested value in dictionary"""
        keys = path.split('.')
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
    
    def open_custom_settings(self):
        """Open custom settings window"""
        messagebox.showinfo("🔧 Custom Settings", "Custom settings window will be implemented here")
    
    def toggle_connection(self):
        """Toggle broker connection"""
        if self.is_connected:
            self.disconnect_from_broker()
        else:
            self.connect_to_broker()
    
    def connect_to_broker(self):
        """Connect to broker"""
        try:
            print("🔌 Attempting to connect to broker...")
            
            # Update UI to show connecting
            self.connect_btn.config(
                text="🔄 กำลังเชื่อมต่อ...",
                state='disabled',
                bg='#dd6b20'
            )
            self.connection_status_label.config(
                text="🟡 กำลังเชื่อมต่อ...",
                fg='#dd6b20'
            )
            self.root.update()
            
            # Connect using real trading system
            if self.trading_system and hasattr(self.trading_system, 'broker_api'):
                success = self.trading_system.broker_api.connect()
                if success:
                    self.is_connected = True
                    self.connect_btn.config(
                        text="🔌 ตัดการเชื่อมต่อ",
                        state='normal',
                        bg='#e53e3e'
                    )
                    self.connection_status_label.config(
                        text="🟢 เชื่อมต่อแล้ว",
                        fg='#38a169'
                    )
                    
                    # Enable trading buttons
                    if hasattr(self, 'start_btn'):
                        self.start_btn.config(state='normal')
                    
                    messagebox.showinfo(
                        "✅ เชื่อมต่อสำเร็จ",
                        "เชื่อมต่อกับ Broker สำเร็จแล้ว!\n\nพร้อมเริ่มเทรดได้เลย"
                    )
                    print("✅ Connected to broker successfully")
                else:
                    raise Exception("Failed to initialize broker connection")
            else:
                raise Exception("Trading system not available - cannot connect to broker")
                
        except Exception as e:
            print(f"❌ Failed to connect to broker: {e}")
            
            # Reset UI to disconnected state
            self.connect_btn.config(
                text="🔌 เชื่อมต่อ",
                state='normal',
                bg='#38a169'
            )
            self.connection_status_label.config(
                text="🔴 เชื่อมต่อล้มเหลว",
                fg='#e53e3e'
            )
            
            # Disable trading buttons
            if hasattr(self, 'start_btn'):
                self.start_btn.config(state='disabled')
            
            messagebox.showerror(
                "❌ เชื่อมต่อล้มเหลว",
                f"ไม่สามารถเชื่อมต่อกับ Broker ได้:\n\n{str(e)}\n\nกรุณาตรวจสอบการตั้งค่าและลองใหม่อีกครั้ง"
            )
    
    def disconnect_from_broker(self):
        """Disconnect from broker"""
        try:
            print("🔌 Disconnecting from broker...")
            
            # Update UI to show disconnecting
            self.connect_btn.config(
                text="🔄 กำลังตัดการเชื่อมต่อ...",
                state='disabled',
                bg='#dd6b20'
            )
            self.connection_status_label.config(
                text="🟡 กำลังตัดการเชื่อมต่อ...",
                fg='#dd6b20'
            )
            self.root.update()
            
            # Stop trading if active
            if hasattr(self, 'start_btn') and self.start_btn['state'] == 'disabled':
                self.stop_trading()
            
            # Disconnect from broker
            if self.trading_system and hasattr(self.trading_system, 'broker_api'):
                self.trading_system.broker_api.disconnect()
            
            # Update UI
            self.is_connected = False
            self.connect_btn.config(
                text="🔌 เชื่อมต่อ",
                state='normal',
                bg='#38a169'
            )
            self.connection_status_label.config(
                text="🔴 ไม่ได้เชื่อมต่อ",
                fg='#e53e3e'
            )
            
            # Disable trading buttons
            if hasattr(self, 'start_btn'):
                self.start_btn.config(state='disabled')
            
            print("✅ Disconnected from broker")
            
        except Exception as e:
            print(f"❌ Error disconnecting: {e}")
    
    def create_status_display(self):
        """Create status display section"""
        # Status frame
        status_frame = tk.Frame(self.main_frame, bg='#1a1a1a', relief='flat', bd=1)
        status_frame.pack(fill='x', pady=(0, 20))
        
        # Title
        title_frame = tk.Frame(status_frame, bg='#1a1a1a')
        title_frame.pack(fill='x', padx=20, pady=(15, 10))
        
        title_label = tk.Label(
            title_frame,
            text="📊 สถานะระบบ",
            font=('Segoe UI', 16, 'bold'),
            bg='#1a1a1a',
            fg='#ffffff'
        )
        title_label.pack(side='left')
        
        # Status content
        content_frame = tk.Frame(status_frame, bg='#1a1a1a')
        content_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        # Current mode
        mode_frame = tk.Frame(content_frame, bg='#1a1a1a')
        mode_frame.pack(fill='x', pady=(0, 8))
        
        tk.Label(
            mode_frame,
            text="• โหมดปัจจุบัน:",
            font=('Segoe UI', 12),
            bg='#1a1a1a',
            fg='#a0aec0'
        ).pack(side='left')
        
        self.current_mode_label = tk.Label(
            mode_frame,
            text="ปกติ",
            font=('Segoe UI', 12, 'bold'),
            bg='#1a1a1a',
            fg='#38a169'
        )
        self.current_mode_label.pack(side='left', padx=(5, 0))
        
        # Active groups
        groups_frame = tk.Frame(content_frame, bg='#1a1a1a')
        groups_frame.pack(fill='x', pady=(0, 8))
        
        tk.Label(
            groups_frame,
            text="กลุ่มที่ท่างาน:",
            font=('Segoe UI', 12),
            bg='#1a1a1a',
            fg='#a0aec0'
        ).pack(side='left')
        
        self.active_groups_label = tk.Label(
            groups_frame,
            text="0/0",
            font=('Segoe UI', 12, 'bold'),
            bg='#1a1a1a',
            fg='#ffffff'
        )
        self.active_groups_label.pack(side='left', padx=(5, 0))
        
        # Total P&L
        pnl_frame = tk.Frame(content_frame, bg='#1a1a1a')
        pnl_frame.pack(fill='x')
        
        tk.Label(
            pnl_frame,
            text="กำไร/ขาดทุนรวม:",
            font=('Segoe UI', 12),
            bg='#1a1a1a',
            fg='#a0aec0'
        ).pack(side='left')
        
        self.total_pnl_label = tk.Label(
            pnl_frame,
            text="$0.00",
            font=('Segoe UI', 12, 'bold'),
            bg='#1a1a1a',
            fg='#38a169'
        )
        self.total_pnl_label.pack(side='left', padx=(5, 0))
    
    def create_action_buttons(self):
        """Create action buttons section"""
        # Action frame
        action_frame = tk.Frame(self.main_frame, bg='#1a1a1a', relief='flat', bd=1)
        action_frame.pack(fill='x', pady=(0, 20))
        
        # Title
        title_frame = tk.Frame(action_frame, bg='#1a1a1a')
        title_frame.pack(fill='x', padx=20, pady=(15, 10))
        
        title_label = tk.Label(
            title_frame,
            text="🎮 การควบคุมระบบ",
            font=('Segoe UI', 16, 'bold'),
            bg='#1a1a1a',
            fg='#ffffff'
        )
        title_label.pack(side='left')
        
        # Buttons frame
        buttons_frame = tk.Frame(action_frame, bg='#1a1a1a')
        buttons_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        # Start button
        self.start_btn = tk.Button(
            buttons_frame,
            text="▶️ เริ่มเทรด",
            font=('Segoe UI', 12, 'bold'),
            bg='#38a169',
            fg='white',
            relief='flat',
            bd=0,
            padx=25,
            pady=12,
            command=self.start_trading,
            state='disabled'
        )
        self.start_btn.pack(side='left', padx=(0, 10))
        
        # Stop button
        self.stop_btn = tk.Button(
            buttons_frame,
            text="⏹️ หยุดเทรด",
            font=('Segoe UI', 12, 'bold'),
            bg='#dd6b20',
            fg='white',
            relief='flat',
            bd=0,
            padx=25,
            pady=12,
            command=self.stop_trading,
            state='disabled'
        )
        self.stop_btn.pack(side='left', padx=(0, 10))
        
        # Emergency close button
        emergency_btn = tk.Button(
            buttons_frame,
            text="🚨 ปิดทั้งหมด",
            font=('Segoe UI', 12, 'bold'),
            bg='#e53e3e',
            fg='white',
            relief='flat',
            bd=0,
            padx=25,
            pady=12,
            command=self.emergency_close
        )
        emergency_btn.pack(side='left')
    
    def start_trading(self):
        """Start trading"""
        try:
            # Check if connected to broker
            if not self.is_connected:
                messagebox.showwarning(
                    "⚠️ ยังไม่ได้เชื่อมต่อ",
                    "กรุณาเชื่อมต่อกับ Broker ก่อนเริ่มเทรด!\n\nกดปุ่ม 'เชื่อมต่อ' ในส่วนหัวของหน้าจอ"
                )
                return
            
            print("🚀 Starting trading")
            
            # Update button states
            self.start_btn.config(
                state='disabled',
                bg='#a0aec0',
                fg='white'
            )
            self.stop_btn.config(
                state='normal',
                bg='#e53e3e',
                fg='white'
            )
            
            # Start real trading system
            if self.trading_system and hasattr(self.trading_system, 'start'):
                success = self.trading_system.start()
                if success:
                    messagebox.showinfo(
                        "🚀 เริ่มเทรดสำเร็จ",
                        f"เริ่มเทรดในโหมด: {self.current_mode}\n\nระบบจะเริ่มทำงานทันที!"
                    )
                    print("✅ Trading started successfully")
                else:
                    raise Exception("Failed to start trading system")
            else:
                raise Exception("Trading system not available - cannot start trading")
                
        except Exception as e:
            print(f"❌ Error starting trading: {e}")
            
            # Reset button states
            self.start_btn.config(
                state='normal',
                bg='#38a169',
                fg='white'
            )
            self.stop_btn.config(
                state='disabled',
                bg='#a0aec0',
                fg='white'
            )
            
            messagebox.showerror(
                "❌ เริ่มเทรดล้มเหลว",
                f"ไม่สามารถเริ่มเทรดได้:\n\n{str(e)}"
            )
    
    def stop_trading(self):
        """Stop trading"""
        try:
            print("⏹️ Stopping trading")
            
            # Stop real trading system
            if self.trading_system and hasattr(self.trading_system, 'stop'):
                self.trading_system.stop()
            
            # Disable stop button, enable start button
            self.stop_btn.config(state='disabled')
            self.start_btn.config(state='normal')
            
            messagebox.showinfo(
                "⏹️ หยุดเทรด",
                "หยุดเทรดเรียบร้อยแล้ว!\n\nระบบจะหยุดการทำงานใหม่"
            )
            
        except Exception as e:
            print(f"❌ Error stopping trading: {e}")
            messagebox.showerror("❌ Error", f"ไม่สามารถหยุดเทรดได้: {str(e)}")
    
    def emergency_close(self):
        """Emergency close all positions"""
        try:
            if messagebox.askyesno(
                "🚨 ปิดทั้งหมด",
                "คุณแน่ใจหรือไม่ที่จะปิดออเดอร์ทั้งหมด?\n\nการกระทำนี้ไม่สามารถยกเลิกได้!"
            ):
                print("🚨 Emergency close all positions")
                
                # Call emergency stop on trading system
                if self.trading_system and hasattr(self.trading_system, 'emergency_stop'):
                    self.trading_system.emergency_stop()
                
                messagebox.showinfo(
                    "🚨 ปิดทั้งหมด",
                    "ปิดออเดอร์ทั้งหมดเรียบร้อยแล้ว!"
                )
                
        except Exception as e:
            print(f"❌ Error emergency close: {e}")
            messagebox.showerror("❌ Error", f"ไม่สามารถปิดออเดอร์ได้: {str(e)}")
    
    def load_current_mode(self):
        """Load current mode from config"""
        try:
            # Set default mode
            self.current_mode = "normal"
            self.apply_mode_settings(self.current_mode)
            print("✅ Loaded current mode: normal")
        except Exception as e:
            print(f"❌ Error loading current mode: {e}")
    
    def update_status_display(self):
        """Update status display with real data from broker"""
        try:
            # Get real data from trading system
            if self.trading_system and self.is_connected:
                # Get real active groups from trading system
                if hasattr(self.trading_system, 'arbitrage_detector'):
                    active_groups = self.trading_system.arbitrage_detector.active_groups
                    active_count = len([g for g in active_groups.values() if g.get('status') == 'active'])
                    total_count = len(active_groups)
                    
                    if hasattr(self, 'active_groups_label'):
                        self.active_groups_label.config(text=f"{active_count}/{total_count}")
                    
                    # Get real P&L from broker
                    total_pnl = 0.0
                    if hasattr(self.trading_system, 'broker_api'):
                        positions = self.trading_system.broker_api.get_all_positions()
                        if positions:
                            for position in positions:
                                if isinstance(position, dict) and 'profit' in position:
                                    total_pnl += float(position['profit'])
                                elif hasattr(position, 'profit'):
                                    total_pnl += float(position.profit)
                    
                    if hasattr(self, 'total_pnl_label'):
                        color = '#38a169' if total_pnl >= 0 else '#e53e3e'
                        self.total_pnl_label.config(
                            text=f"${total_pnl:.2f}",
                            fg=color
                        )
                    
                    print(f"📊 Real status updated: {active_count}/{total_count} groups, P&L: ${total_pnl:.2f}")
                else:
                    # Fallback to file data if trading system not fully available
                    self.update_status_from_file()
            else:
                # Not connected - show disconnected state
                if hasattr(self, 'active_groups_label'):
                    self.active_groups_label.config(text="0/0")
                if hasattr(self, 'total_pnl_label'):
                    self.total_pnl_label.config(text="$0.00", fg='#a0aec0')
                print("📊 Status: Disconnected - no real data available")
                
        except Exception as e:
            print(f"❌ Error updating real status: {e}")
            # Fallback to file data on error
            self.update_status_from_file()
    
    def update_status_from_file(self):
        """Update status from file data as fallback"""
        try:
            # Load from active_groups.json
            active_groups_file = "data/active_groups.json"
            if os.path.exists(active_groups_file):
                with open(active_groups_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    active_groups = data.get('active_groups', {})
                    
                    # Count active groups
                    active_count = 0
                    total_count = len(active_groups)
                    
                    for group_data in active_groups.values():
                        if isinstance(group_data, dict) and group_data.get('status') == 'active':
                            active_count += 1
                    
                    # Update labels
                    if hasattr(self, 'active_groups_label'):
                        self.active_groups_label.config(text=f"{active_count}/{total_count}")
                    
                    # Simple P&L simulation for display
                    total_pnl = 0.0
                    for group_data in active_groups.values():
                        if isinstance(group_data, dict):
                            positions = group_data.get('positions', [])
                            for position in positions:
                                if isinstance(position, dict):
                                    pnl = position.get('pnl', 0.0)
                                    total_pnl += float(pnl)
                    
                    if hasattr(self, 'total_pnl_label'):
                        color = '#38a169' if total_pnl >= 0 else '#e53e3e'
                        self.total_pnl_label.config(
                            text=f"${total_pnl:.2f}",
                            fg=color
                        )
                    
                    print(f"📊 File status updated: {active_count}/{total_count} groups, P&L: ${total_pnl:.2f}")
            else:
                print("📊 No active groups file found")
                
        except Exception as e:
            print(f"❌ Error updating status from file: {e}")
    
    def start_periodic_updates(self):
        """Start periodic status updates"""
        def update_loop():
            while True:
                try:
                    self.update_status_display()
                    time.sleep(5)  # Update every 5 seconds
                except Exception as e:
                    print(f"❌ Error in update loop: {e}")
                    time.sleep(5)
        
        # Start update thread
        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()
        print("✅ Periodic updates started")
    
    def create_footer(self):
        """Create footer section"""
        # Footer frame
        footer_frame = tk.Frame(self.main_frame, bg='#2d3748', relief='flat', bd=0)
        footer_frame.pack(fill='x', side='bottom')
        
        # Left side - Auto refresh controls
        left_frame = tk.Frame(footer_frame, bg='#2d3748')
        left_frame.pack(side='left', padx=20, pady=10)
        
        # Auto refresh checkbox
        self.auto_refresh_cb = tk.Checkbutton(
            left_frame,
            text="🔄 อัพเดทอัตโนมัติ",
            font=('Segoe UI', 10),
            bg='#2d3748',
            fg='#ffffff',
            selectcolor='#38a169',
            activebackground='#2d3748',
            activeforeground='#ffffff',
            command=self.toggle_auto_refresh
        )
        self.auto_refresh_cb.pack(side='left', padx=(0, 10))
        self.auto_refresh_cb.select()  # Default to selected
        
        # Manual refresh button
        self.refresh_btn = tk.Button(
            left_frame,
            text="🔄 รีเฟรช",
            font=('Segoe UI', 10),
            bg='#3182ce',
            fg='white',
            relief='flat',
            bd=0,
            padx=15,
            pady=5,
            command=self.manual_refresh
        )
        self.refresh_btn.pack(side='left')
        
        # Right side - Version info
        right_frame = tk.Frame(footer_frame, bg='#2d3748')
        right_frame.pack(side='right', padx=20, pady=10)
        
        self.version_label = tk.Label(
            right_frame,
            text="v3.0 Colorful • ArbiTrader Professional",
            font=('Segoe UI', 9),
            bg='#2d3748',
            fg='#a0aec0'
        )
        self.version_label.pack(side='right')
    
    def toggle_auto_refresh(self):
        """Toggle auto refresh"""
        try:
            if self.auto_refresh_cb.instate(['selected']):
                self.start_periodic_updates()
                print("✅ Auto refresh enabled")
            else:
                # Stop periodic updates by not scheduling next update
                print("⏸️ Auto refresh disabled")
        except Exception as e:
            print(f"❌ Error toggling auto refresh: {e}")
    
    def manual_refresh(self):
        """Manual refresh"""
        try:
            self.update_status_display()
            print("🔄 Manual refresh completed")
        except Exception as e:
            print(f"❌ Error in manual refresh: {e}")
    
    def run(self):
        """Run the main window"""
        print("🚀 Starting ArbiTrader Professional Main Window...")
        self.root.mainloop()