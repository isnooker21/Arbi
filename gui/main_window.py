"""
Simple Main Window - หน้า GUI หลักที่เรียบง่าย
=============================================

Author: AI Trading System
Version: 3.0 - Simple & Beautiful
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .theme import TradingTheme
from .simple_dashboard import SimpleDashboard

class MainWindow:
    def __init__(self, trading_system=None):
        self.root = tk.Tk()
        self.root.title("🎯 ArbiTrader - Colorful & Beautiful")
        self.root.geometry("1300x850")
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
        self.simple_dashboard = None
        
        # Apply theme
        TradingTheme.apply_theme(self.root)
        
        # Setup UI
        self.setup_ui()
        
        # Load current mode and start updates
        self.load_current_mode()
        self.start_periodic_updates()
        
        print("✅ Professional Main Window initialized")
    
    def center_window(self):
        """Center window on screen"""
        self.root.update_idletasks()
        width = 1300
        height = 850
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_ui(self):
        """Setup integrated UI layout"""
        # Main container
        self.main_frame = tk.Frame(self.root, bg='#1e1e1e')
        self.main_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Initialize variables
        self.current_mode = "normal"  # default mode
        self.mode_buttons = {}
        self.is_connected = False
        self.trading_system = trading_system
        
        # Header
        self.create_header()
        
        # Mode selection (integrated)
        self.create_mode_selection()
        
        # Status display (integrated)
        self.create_status_display()
        
        # Action buttons (integrated)
        self.create_action_buttons()
        
        # Footer
        self.create_footer()
    
    def create_header(self):
        """Create beautiful header section"""
        # Main header frame with gradient effect
        header_frame = tk.Frame(self.main_frame, bg='#1a1a1a', height=100)
        header_frame.pack(fill='x', pady=(0, 25))
        header_frame.pack_propagate(False)
        
        # Inner header with gradient simulation
        inner_header = tk.Frame(header_frame, bg='#2a2a2a', relief='raised', bd=2)
        inner_header.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title with beautiful styling
        title_frame = tk.Frame(inner_header, bg='#2a2a2a')
        title_frame.pack(side='left', fill='y', padx=30, pady=20)
        
        title_label = tk.Label(
            title_frame,
            text="🚀 ArbiTrader",
            font=('Segoe UI', 36, 'bold'),
            bg='#2a2a2a',
            fg='#FF6B6B'
        )
        title_label.pack(side='left')
        
        subtitle_label = tk.Label(
            title_frame,
            text="Colorful & Beautiful",
            font=('Segoe UI', 16, 'italic'),
            bg='#2a2a2a',
            fg='#4ECDC4'
        )
        subtitle_label.pack(side='left', padx=(25, 0), pady=(12, 0))
        
        # Right side info
        info_frame = tk.Frame(inner_header, bg='#2a2a2a')
        info_frame.pack(side='right', fill='y', padx=30, pady=20)
        
        # Version
        version_label = tk.Label(
            info_frame,
            text="v3.0 Colorful",
            font=('Segoe UI', 13, 'bold'),
            bg='#2a2a2a',
            fg='#FFD93D'
        )
        version_label.pack(side='right', padx=(0, 15))
        
        # Status
        status_label = tk.Label(
            info_frame,
            text="🟢 Ready",
            font=('Segoe UI', 13, 'bold'),
            bg='#2a2a2a',
            fg='#00FF88'
        )
        status_label.pack(side='right', padx=(0, 20))
        
        # Connection section
        connection_frame = tk.Frame(inner_header, bg='#2a2a2a')
        connection_frame.pack(side='right', fill='y', padx=25, pady=15)
        
        # Connection status
        self.connection_status_label = tk.Label(
            connection_frame,
            text="🔴 ไม่ได้เชื่อมต่อ",
            font=('Segoe UI', 11, 'bold'),
            bg='#2a2a2a',
            fg='#e53e3e'
        )
        self.connection_status_label.pack(side='right', padx=(0, 15))
        
        # Connect button
        self.connect_btn = tk.Button(
            connection_frame,
            text="🔌 เชื่อมต่อ",
            font=('Segoe UI', 10, 'bold'),
            bg='#38a169',
            fg='white',
            width=10,
            height=1,
            relief='flat',
            bd=1,
            cursor='hand2',
            command=self.toggle_connection,
            activebackground='#68d391',
            activeforeground='white'
        )
        self.connect_btn.pack(side='right', padx=(0, 10))
    
    def create_mode_selection(self):
        """Create mode selection section"""
        # Main mode frame
        mode_frame = tk.Frame(self.main_frame, bg='#1e1e1e')
        mode_frame.pack(fill='x', pady=15)
        
        # Title with professional styling
        title_label = tk.Label(
            mode_frame,
            text="⚙️ เลือกโหมดการเทรด",
            font=('Segoe UI', 18, 'bold'),
            bg='#1e1e1e',
            fg='#ffffff'
        )
        title_label.pack(pady=(0, 15))
        
        # Mode buttons container with professional background
        buttons_container = tk.Frame(mode_frame, bg='#2d3748', relief='flat', bd=1)
        buttons_container.pack(fill='x', padx=10, pady=10)
        
        buttons_frame = tk.Frame(buttons_container, bg='#2d3748')
        buttons_frame.pack(pady=20)
        
        # Mode buttons with professional styling
        self.mode_buttons = {}
        
        # Mode 1: ซิ่ง
        mode1_btn = tk.Button(
            buttons_frame,
            text="🔥 ซิ่ง\n(เสี่ยงสูงสุด)",
            font=('Segoe UI', 11, 'bold'),
            bg='#e53e3e',
            fg='white',
            width=16,
            height=3,
            relief='flat',
            bd=2,
            cursor='hand2',
            command=lambda: self.select_mode('racing'),
            activebackground='#fc8181',
            activeforeground='white'
        )
        mode1_btn.grid(row=0, column=0, padx=8, pady=8)
        self.mode_buttons['racing'] = mode1_btn
        
        # Mode 2: ซิ่งกลาง
        mode2_btn = tk.Button(
            buttons_frame,
            text="⚡ ซิ่งกลาง\n(เสี่ยงปานกลาง)",
            font=('Segoe UI', 11, 'bold'),
            bg='#dd6b20',
            fg='white',
            width=16,
            height=3,
            relief='flat',
            bd=2,
            cursor='hand2',
            command=lambda: self.select_mode('fast'),
            activebackground='#f6ad55',
            activeforeground='white'
        )
        mode2_btn.grid(row=0, column=1, padx=8, pady=8)
        self.mode_buttons['fast'] = mode2_btn
        
        # Mode 3: ปกติ
        mode3_btn = tk.Button(
            buttons_frame,
            text="⚖️ ปกติ\n(สมดุล)",
            font=('Segoe UI', 11, 'bold'),
            bg='#38a169',
            fg='white',
            width=16,
            height=3,
            relief='flat',
            bd=2,
            cursor='hand2',
            command=lambda: self.select_mode('normal'),
            activebackground='#68d391',
            activeforeground='white'
        )
        mode3_btn.grid(row=0, column=2, padx=8, pady=8)
        self.mode_buttons['normal'] = mode3_btn
        
        # Mode 4: เซฟ
        mode4_btn = tk.Button(
            buttons_frame,
            text="🛡️ เซฟ\n(ปลอดภัย)",
            font=('Segoe UI', 11, 'bold'),
            bg='#3182ce',
            fg='white',
            width=16,
            height=3,
            relief='flat',
            bd=2,
            cursor='hand2',
            command=lambda: self.select_mode('safe'),
            activebackground='#63b3ed',
            activeforeground='white'
        )
        mode4_btn.grid(row=0, column=3, padx=8, pady=8)
        self.mode_buttons['safe'] = mode4_btn
        
        # Mode 5: Custom
        mode5_btn = tk.Button(
            buttons_frame,
            text="🔧 Custom\n(ปรับแต่ง)",
            font=('Segoe UI', 11, 'bold'),
            bg='#805ad5',
            fg='white',
            width=16,
            height=3,
            relief='flat',
            bd=2,
            cursor='hand2',
            command=lambda: self.select_mode('custom'),
            activebackground='#b794f6',
            activeforeground='white'
        )
        mode5_btn.grid(row=0, column=4, padx=8, pady=8)
        self.mode_buttons['custom'] = mode5_btn
        
        # Custom settings button (only visible when custom mode is selected)
        self.custom_settings_btn = tk.Button(
            buttons_container,
            text="⚙️ ปรับแต่ง Custom Settings",
            font=('Segoe UI', 10, 'bold'),
            bg='#4a5568',
            fg='white',
            width=25,
            height=2,
            relief='flat',
            bd=1,
            cursor='hand2',
            command=self.open_custom_settings,
            state='disabled'
        )
        # Don't pack yet - will be shown when custom mode is selected
    
    def select_mode(self, mode):
        """Select trading mode"""
        self.current_mode = mode
        
        # Reset all buttons
        for btn in self.mode_buttons.values():
            btn.config(relief='flat', bd=2)
        
        # Highlight selected mode
        self.mode_buttons[mode].config(relief='raised', bd=3)
        
        # Update custom settings button visibility
        if mode == 'custom':
            self.custom_settings_btn.pack(pady=(10, 20))
            self.custom_settings_btn.config(state='normal')
        else:
            self.custom_settings_btn.pack_forget()
            self.custom_settings_btn.config(state='disabled')
        
        # Apply mode settings
        self.apply_mode_settings(mode)
        
        print(f"✅ Selected mode: {mode}")
    
    def apply_mode_settings(self, mode):
        """Apply settings for selected mode"""
        try:
            # Mode configurations
            mode_configs = {
                'racing': {
                    'name': '🔥 ซิ่ง (เสี่ยงสูงสุด)',
                    'description': 'ออกไม้และแก้ไม้ไวที่สุด แบบเสี่ยง ไม่ปิดล็อคอะไรเลย',
                    'arbitrage_params.detection.min_threshold': 0.00001,
                    'arbitrage_params.detection.spread_tolerance': 2.0,
                    'arbitrage_params.execution.commission_rate': 0.00001,
                    'arbitrage_params.execution.max_slippage': 0.002,
                    'arbitrage_params.triangles.balance_tolerance_percent': 50.0,
                    'arbitrage_params.triangles.max_active_triangles': 6,
                    'arbitrage_params.closing.trailing_stop_enabled': False,
                    'arbitrage_params.closing.lock_profit_percentage': 0.0,
                    'recovery_params.loss_thresholds.min_loss_percent': -20.0,
                    'recovery_params.chain_recovery.max_chain_depth': 5,
                    'position_sizing.lot_calculation.risk_per_trade_percent': 5.0
                },
                'fast': {
                    'name': '⚡ ซิ่งกลาง (เสี่ยงปานกลาง)',
                    'description': 'ออกไม้ซิ่งแต่ไม่มากเท่าโหมดแรกและแก้ไม้น้อยกว่า',
                    'arbitrage_params.detection.min_threshold': 0.00003,
                    'arbitrage_params.detection.spread_tolerance': 1.5,
                    'arbitrage_params.execution.commission_rate': 0.00003,
                    'arbitrage_params.execution.max_slippage': 0.001,
                    'arbitrage_params.triangles.balance_tolerance_percent': 35.0,
                    'arbitrage_params.triangles.max_active_triangles': 4,
                    'arbitrage_params.closing.trailing_stop_enabled': True,
                    'arbitrage_params.closing.lock_profit_percentage': 0.3,
                    'recovery_params.loss_thresholds.min_loss_percent': -10.0,
                    'recovery_params.chain_recovery.max_chain_depth': 3,
                    'position_sizing.lot_calculation.risk_per_trade_percent': 3.0
                },
                'normal': {
                    'name': '⚖️ ปกติ (สมดุล)',
                    'description': 'ค่ากลางที่สุด สมดุลระหว่างกำไรและความเสี่ยง',
                    'arbitrage_params.detection.min_threshold': 0.00005,
                    'arbitrage_params.detection.spread_tolerance': 1.0,
                    'arbitrage_params.execution.commission_rate': 0.00005,
                    'arbitrage_params.execution.max_slippage': 0.0008,
                    'arbitrage_params.triangles.balance_tolerance_percent': 25.0,
                    'arbitrage_params.triangles.max_active_triangles': 3,
                    'arbitrage_params.closing.trailing_stop_enabled': True,
                    'arbitrage_params.closing.lock_profit_percentage': 0.5,
                    'recovery_params.loss_thresholds.min_loss_percent': -5.0,
                    'recovery_params.chain_recovery.max_chain_depth': 2,
                    'position_sizing.lot_calculation.risk_per_trade_percent': 2.0
                },
                'safe': {
                    'name': '🛡️ เซฟ (ปลอดภัย)',
                    'description': 'แบบปลอดภัย เสี่ยงต่ำ กำไรมั่นคง',
                    'arbitrage_params.detection.min_threshold': 0.0001,
                    'arbitrage_params.detection.spread_tolerance': 0.5,
                    'arbitrage_params.execution.commission_rate': 0.0001,
                    'arbitrage_params.execution.max_slippage': 0.0005,
                    'arbitrage_params.triangles.balance_tolerance_percent': 15.0,
                    'arbitrage_params.triangles.max_active_triangles': 2,
                    'arbitrage_params.closing.trailing_stop_enabled': True,
                    'arbitrage_params.closing.lock_profit_percentage': 0.7,
                    'recovery_params.loss_thresholds.min_loss_percent': -2.0,
                    'recovery_params.chain_recovery.max_chain_depth': 1,
                    'position_sizing.lot_calculation.risk_per_trade_percent': 1.0
                },
                'custom': {
                    'name': '🔧 Custom (ปรับแต่ง)',
                    'description': 'โหมดปรับแต่งตามต้องการ ต้องตั้งค่าด้วยตนเอง',
                    'arbitrage_params.detection.min_threshold': 0.00005,
                    'arbitrage_params.detection.spread_tolerance': 1.0,
                    'arbitrage_params.execution.commission_rate': 0.00005,
                    'arbitrage_params.execution.max_slippage': 0.0008,
                    'arbitrage_params.triangles.balance_tolerance_percent': 25.0,
                    'arbitrage_params.triangles.max_active_triangles': 3,
                    'arbitrage_params.closing.trailing_stop_enabled': True,
                    'arbitrage_params.closing.lock_profit_percentage': 0.5,
                    'recovery_params.loss_thresholds.min_loss_percent': -5.0,
                    'recovery_params.chain_recovery.max_chain_depth': 2,
                    'position_sizing.lot_calculation.risk_per_trade_percent': 2.0
                }
            }
            
            if mode in mode_configs:
                config = mode_configs[mode]
                print(f"📋 Applying {config['name']}")
                print(f"📝 {config['description']}")
                
                # Save mode to config file (except for custom)
                if mode != 'custom':
                    self.save_mode_to_config(mode, config)
                
                # Update status display
                if hasattr(self, 'current_mode_label'):
                    mode_names = {
                        'racing': '🔥 ซิ่ง',
                        'fast': '⚡ ซิ่งกลาง',
                        'normal': '⚖️ ปกติ',
                        'safe': '🛡️ เซฟ',
                        'custom': '🔧 Custom'
                    }
                    self.current_mode_label.config(
                        text=f"{mode_names[mode]}",
                        fg=self.get_mode_color(mode)
                    )
                
        except Exception as e:
            print(f"❌ Error applying mode: {e}")
    
    def get_mode_color(self, mode):
        """Get color for mode"""
        colors = {
            'racing': '#e53e3e',
            'fast': '#dd6b20',
            'normal': '#38a169',
            'safe': '#3182ce',
            'custom': '#805ad5'
        }
        return colors.get(mode, '#38a169')
    
    def save_mode_to_config(self, mode, config):
        """Save mode configuration to config file"""
        try:
            import os
            import json
            config_file_path = os.path.join('config', 'adaptive_params.json')
            
            # Load current config
            if os.path.exists(config_file_path):
                with open(config_file_path, 'r', encoding='utf-8') as f:
                    current_config = json.load(f)
            else:
                current_config = {}
            
            # Update with mode settings
            for key, value in config.items():
                if key not in ['name', 'description']:
                    self.set_nested_value(current_config, key, value)
            
            # Save back to file
            with open(config_file_path, 'w', encoding='utf-8') as f:
                json.dump(current_config, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Mode {mode} saved to config")
            
        except Exception as e:
            print(f"❌ Error saving mode config: {e}")
    
    def set_nested_value(self, data, path, value):
        """Set value in nested dictionary using dot notation"""
        keys = path.split('.')
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
    
    def open_custom_settings(self):
        """Open custom settings window"""
        try:
            messagebox.showinfo(
                "🔧 Custom Settings",
                "Custom Settings จะเปิดในหน้าต่างใหม่\n\nคุณสามารถปรับแต่งค่าต่างๆ ได้ตามต้องการ"
            )
            print("🔧 Opening Custom Settings...")
        except Exception as e:
            print(f"❌ Error opening custom settings: {e}")
            messagebox.showerror("❌ Error", f"ไม่สามารถเปิด Custom Settings ได้: {str(e)}")
    
    def toggle_connection(self):
        """Toggle broker connection"""
        try:
            if not self.is_connected:
                self.connect_to_broker()
            else:
                self.disconnect_from_broker()
        except Exception as e:
            print(f"❌ Error toggling connection: {e}")
            messagebox.showerror("❌ Error", f"ไม่สามารถเปลี่ยนสถานะการเชื่อมต่อได้: {str(e)}")
    
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
            
            # Try to connect using trading system
            if self.trading_system and hasattr(self.trading_system, 'broker_api'):
                success = self.trading_system.broker_api.initialize()
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
                # Simulate connection for testing
                import time
                time.sleep(1)  # Simulate connection delay
                
                self.is_connected = True
                self.connect_btn.config(
                    text="🔌 ตัดการเชื่อมต่อ",
                    state='normal',
                    bg='#e53e3e'
                )
                self.connection_status_label.config(
                    text="🟢 เชื่อมต่อแล้ว (Demo)",
                    fg='#38a169'
                )
                
                # Enable trading buttons
                if hasattr(self, 'start_btn'):
                    self.start_btn.config(state='normal')
                
                messagebox.showinfo(
                    "✅ เชื่อมต่อสำเร็จ (Demo)",
                    "เชื่อมต่อกับ Broker สำเร็จแล้ว! (Demo Mode)\n\nพร้อมเริ่มเทรดได้เลย"
                )
                print("✅ Connected to broker successfully (Demo Mode)")
                
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
            
            # Try to disconnect using trading system
            if self.trading_system and hasattr(self.trading_system, 'broker_api'):
                self.trading_system.broker_api.shutdown()
            
            # Simulate disconnection delay
            import time
            time.sleep(0.5)
            
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
            
            messagebox.showinfo(
                "✅ ตัดการเชื่อมต่อสำเร็จ",
                "ตัดการเชื่อมต่อกับ Broker เรียบร้อยแล้ว"
            )
            print("✅ Disconnected from broker successfully")
            
        except Exception as e:
            print(f"❌ Error disconnecting from broker: {e}")
            messagebox.showerror("❌ Error", f"ไม่สามารถตัดการเชื่อมต่อได้: {str(e)}")
    
    def create_status_display(self):
        """Create status display section"""
        # Main status frame
        status_frame = tk.Frame(self.main_frame, bg='#1e1e1e')
        status_frame.pack(fill='x', pady=15)
        
        # Status container with professional background
        status_container = tk.Frame(status_frame, bg='#2d3748', relief='flat', bd=1)
        status_container.pack(fill='x', padx=10, pady=10)
        
        # Title with professional styling
        title_label = tk.Label(
            status_container,
            text="📊 สถานะระบบ",
            font=('Segoe UI', 16, 'bold'),
            bg='#2d3748',
            fg='#ffffff'
        )
        title_label.pack(pady=(15, 10))
        
        # Status info container with grid layout
        info_frame = tk.Frame(status_container, bg='#2d3748')
        info_frame.pack(pady=(0, 15))
        
        # Current mode with professional styling
        mode_frame = tk.Frame(info_frame, bg='#4a5568', relief='flat', bd=1)
        mode_frame.pack(fill='x', padx=15, pady=5)
        
        mode_title = tk.Label(
            mode_frame,
            text="🎯 โหมดปัจจุบัน:",
            font=('Segoe UI', 11, 'bold'),
            bg='#4a5568',
            fg='#a0aec0'
        )
        mode_title.pack(side='left', padx=15, pady=8)
        
        self.current_mode_label = tk.Label(
            mode_frame,
            text="⚖️ ปกติ",
            font=('Segoe UI', 12, 'bold'),
            bg='#4a5568',
            fg='#38a169'
        )
        self.current_mode_label.pack(side='right', padx=15, pady=8)
        
        # Active groups with professional styling
        groups_frame = tk.Frame(info_frame, bg='#4a5568', relief='flat', bd=1)
        groups_frame.pack(fill='x', padx=15, pady=5)
        
        groups_title = tk.Label(
            groups_frame,
            text="🔄 กลุ่มที่ทำงาน:",
            font=('Segoe UI', 11, 'bold'),
            bg='#4a5568',
            fg='#a0aec0'
        )
        groups_title.pack(side='left', padx=15, pady=8)
        
        self.active_groups_label = tk.Label(
            groups_frame,
            text="0/6",
            font=('Segoe UI', 12, 'bold'),
            bg='#4a5568',
            fg='#3182ce'
        )
        self.active_groups_label.pack(side='right', padx=15, pady=8)
        
        # Total P&L with professional styling
        pnl_frame = tk.Frame(info_frame, bg='#4a5568', relief='flat', bd=1)
        pnl_frame.pack(fill='x', padx=15, pady=5)
        
        pnl_title = tk.Label(
            pnl_frame,
            text="💰 กำไร/ขาดทุนรวม:",
            font=('Segoe UI', 11, 'bold'),
            bg='#4a5568',
            fg='#a0aec0'
        )
        pnl_title.pack(side='left', padx=15, pady=8)
        
        self.total_pnl_label = tk.Label(
            pnl_frame,
            text="$0.00",
            font=('Segoe UI', 12, 'bold'),
            bg='#4a5568',
            fg='#38a169'
        )
        self.total_pnl_label.pack(side='right', padx=15, pady=8)
    
    def create_action_buttons(self):
        """Create action buttons section"""
        # Main action frame
        action_frame = tk.Frame(self.main_frame, bg='#1e1e1e')
        action_frame.pack(fill='x', pady=15)
        
        # Title with professional styling
        title_label = tk.Label(
            action_frame,
            text="🎮 การควบคุมระบบ",
            font=('Segoe UI', 18, 'bold'),
            bg='#1e1e1e',
            fg='#ffffff'
        )
        title_label.pack(pady=(0, 15))
        
        # Buttons container with professional background
        buttons_container = tk.Frame(action_frame, bg='#2d3748', relief='flat', bd=1)
        buttons_container.pack(fill='x', padx=10, pady=10)
        
        buttons_frame = tk.Frame(buttons_container, bg='#2d3748')
        buttons_frame.pack(pady=20)
        
        # Start button with professional styling (disabled by default)
        self.start_btn = tk.Button(
            buttons_frame,
            text="▶️ เริ่มเทรด",
            font=('Segoe UI', 12, 'bold'),
            bg='#4a5568',
            fg='#a0aec0',
            width=15,
            height=2,
            relief='flat',
            bd=2,
            cursor='hand2',
            command=self.start_trading,
            state='disabled',
            activebackground='#68d391',
            activeforeground='white'
        )
        self.start_btn.grid(row=0, column=0, padx=10, pady=8)
        
        # Stop button with professional styling
        self.stop_btn = tk.Button(
            buttons_frame,
            text="⏹️ หยุดเทรด",
            font=('Segoe UI', 12, 'bold'),
            bg='#e53e3e',
            fg='white',
            width=15,
            height=2,
            relief='flat',
            bd=2,
            cursor='hand2',
            command=self.stop_trading,
            state='disabled',
            activebackground='#fc8181',
            activeforeground='white'
        )
        self.stop_btn.grid(row=0, column=1, padx=10, pady=8)
        
        # Emergency close button with professional styling
        self.emergency_btn = tk.Button(
            buttons_frame,
            text="🚨 ปิดทั้งหมด",
            font=('Segoe UI', 12, 'bold'),
            bg='#dd6b20',
            fg='white',
            width=15,
            height=2,
            relief='flat',
            bd=2,
            cursor='hand2',
            command=self.emergency_close,
            activebackground='#f6ad55',
            activeforeground='white'
        )
        self.emergency_btn.grid(row=0, column=2, padx=10, pady=8)
    
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
            
            print(f"🚀 Starting trading in {self.current_mode} mode")
            
            # Update button states
            self.start_btn.config(
                state='disabled',
                bg='#4a5568',
                fg='#a0aec0'
            )
            self.stop_btn.config(
                state='normal',
                bg='#e53e3e',
                fg='white'
            )
            
            # Start actual trading if trading system is available
            if self.trading_system and hasattr(self.trading_system, 'start_trading'):
                success = self.trading_system.start_trading()
                if success:
                    messagebox.showinfo(
                        "🚀 เริ่มเทรดสำเร็จ",
                        f"เริ่มเทรดในโหมด: {self.current_mode}\n\nระบบจะเริ่มทำงานทันที!"
                    )
                    print("✅ Trading started successfully")
                else:
                    raise Exception("Failed to start trading system")
            else:
                # Simulate trading start
                messagebox.showinfo(
                    "🚀 เริ่มเทรด (Demo)",
                    f"เริ่มเทรดในโหมด: {self.current_mode}\n\nระบบจะเริ่มทำงานทันที! (Demo Mode)"
                )
                print("✅ Trading started successfully (Demo Mode)")
            
        except Exception as e:
            print(f"❌ Error starting trading: {e}")
            
            # Reset button states on error
            self.start_btn.config(
                state='normal',
                bg='#38a169',
                fg='white'
            )
            self.stop_btn.config(
                state='disabled',
                bg='#4a5568',
                fg='#a0aec0'
            )
            
            messagebox.showerror("❌ Error", f"ไม่สามารถเริ่มเทรดได้: {str(e)}")
    
    def stop_trading(self):
        """Stop trading"""
        try:
            print("⏹️ Stopping trading")
            
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
                
                messagebox.showinfo(
                    "🚨 ปิดทั้งหมด",
                    "ปิดออเดอร์ทั้งหมดเรียบร้อยแล้ว!"
                )
                
        except Exception as e:
            print(f"❌ Error emergency close: {e}")
            messagebox.showerror("❌ Error", f"ไม่สามารถปิดออเดอร์ได้: {str(e)}")
    
    def load_current_mode(self):
        """Load current mode from saved settings"""
        try:
            # Default to normal mode
            self.current_mode = "normal"
            
            # Apply normal mode settings
            self.apply_mode_settings('normal')
            
            # Highlight normal button
            if hasattr(self, 'mode_buttons') and 'normal' in self.mode_buttons:
                self.select_mode('normal')
            
            print("✅ Loaded current mode: normal")
            
        except Exception as e:
            print(f"❌ Error loading current mode: {e}")
    
    def update_status_display(self):
        """Update status display with real data"""
        try:
            # Load active groups data
            import os
            import json
            
            active_groups_file = os.path.join('data', 'active_groups.json')
            if os.path.exists(active_groups_file):
                with open(active_groups_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Get the actual groups data from the correct structure
                if isinstance(data, dict) and 'active_groups' in data:
                    active_groups = data['active_groups']
                else:
                    active_groups = data
                
                # Ensure active_groups is a dictionary
                if not isinstance(active_groups, dict):
                    print("❌ active_groups is not a dictionary")
                    return
                
                # Update active groups count
                active_count = len([g for g in active_groups.values() if isinstance(g, dict) and g.get('status') == 'active'])
                total_count = len(active_groups)
                
                if hasattr(self, 'active_groups_label'):
                    self.active_groups_label.config(text=f"{active_count}/{total_count}")
                
                # Calculate total P&L (simulated)
                total_pnl = 0.0
                for g in active_groups.values():
                    if isinstance(g, dict):
                        pnl_value = g.get('net_pnl', 0)
                        if isinstance(pnl_value, (int, float)):
                            total_pnl += float(pnl_value)
                
                if hasattr(self, 'total_pnl_label'):
                    color = '#38a169' if total_pnl >= 0 else '#e53e3e'
                    self.total_pnl_label.config(
                        text=f"${total_pnl:.2f}",
                        fg=color
                    )
                
                print(f"📊 Status updated: {active_count}/{total_count} groups, P&L: ${total_pnl:.2f}")
            
        except Exception as e:
            print(f"❌ Error updating status: {e}")
            import traceback
            traceback.print_exc()
    
    def start_periodic_updates(self):
        """Start periodic updates for status display"""
        try:
            self.update_status_display()
            # Update every 5 seconds
            self.root.after(5000, self.start_periodic_updates)
        except Exception as e:
            print(f"❌ Error in periodic updates: {e}")
    
    def create_footer(self):
        """Create professional footer section"""
        # Main footer frame
        footer_frame = tk.Frame(self.main_frame, bg='#1e1e1e', height=60)
        footer_frame.pack(fill='x', side='bottom', pady=(20, 0))
        footer_frame.pack_propagate(False)
        
        # Footer container with professional background
        footer_container = tk.Frame(footer_frame, bg='#2d3748', relief='flat', bd=1)
        footer_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Left side - Auto refresh
        left_frame = tk.Frame(footer_container, bg='#2d3748')
        left_frame.pack(side='left', fill='y', padx=15, pady=10)
        
        self.auto_refresh_cb = tk.Checkbutton(
            left_frame,
            text="🔄 อัพเดทอัตโนมัติ",
            font=('Segoe UI', 10),
            bg='#2d3748',
            fg='#a0aec0',
            selectcolor='#2d3748',
            activebackground='#2d3748',
            activeforeground='#a0aec0',
            command=self.toggle_auto_refresh
        )
        self.auto_refresh_cb.pack(side='left')
        self.auto_refresh_cb.select()  # Default enabled
        
        # Center - Refresh button
        center_frame = tk.Frame(footer_container, bg='#2d3748')
        center_frame.pack(side='left', fill='y', padx=20, pady=10)
        
        self.refresh_btn = tk.Button(
            center_frame,
            text="🔄 รีเฟรช",
            font=('Segoe UI', 10, 'bold'),
            bg='#4a5568',
            fg='white',
            width=12,
            height=1,
            relief='flat',
            bd=1,
            cursor='hand2',
            command=self.manual_refresh,
            activebackground='#2d3748',
            activeforeground='white'
        )
        self.refresh_btn.pack()
        
        # Right side - Version info
        right_frame = tk.Frame(footer_container, bg='#2d3748')
        right_frame.pack(side='right', fill='y', padx=15, pady=10)
        
        self.version_label = tk.Label(
            right_frame,
            text="v3.0 Professional",
            font=('Segoe UI', 10, 'bold'),
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
    
    def open_dashboard(self):
        """Open simple dashboard"""
        try:
            if not hasattr(self, 'simple_dashboard') or self.simple_dashboard is None:
                from .simple_dashboard import SimpleDashboard
                self.simple_dashboard = SimpleDashboard(self.root, self.trading_system)
            else:
                self.simple_dashboard.main_window.lift()
                self.simple_dashboard.main_window.focus_force()
            
            print("✅ Dashboard opened")
            
        except Exception as e:
            print(f"❌ Error opening dashboard: {e}")
            import tkinter.messagebox as messagebox
            messagebox.showerror("❌ Error", f"ไม่สามารถเปิด Dashboard ได้: {str(e)}")
    
    def create_status_section(self):
        """Create beautiful status section"""
        # Main status frame
        status_frame = tk.Frame(self.main_frame, bg='#1a1a1a')
        status_frame.pack(fill='x', pady=(0, 25))
        
        # Status container with beautiful background
        status_container = tk.Frame(status_frame, bg='#2a2a2a', relief='raised', bd=2)
        status_container.pack(fill='x', padx=25, pady=15)
        
        # Title with beautiful styling
        title_label = tk.Label(
            status_container,
            text="📊 สถานะระบบ",
            font=('Segoe UI', 18, 'bold'),
            bg='#2a2a2a',
            fg='#FFD700'
        )
        title_label.pack(pady=(20, 15))
        
        # Status info container with beautiful layout
        info_frame = tk.Frame(status_container, bg='#2a2a2a')
        info_frame.pack(pady=(0, 20))
        
        # System status with beautiful styling
        system_frame = tk.Frame(info_frame, bg='#3a3a3a', relief='raised', bd=1)
        system_frame.pack(fill='x', padx=20, pady=8)
        
        system_title = tk.Label(
            system_frame,
            text="🖥️ ระบบ",
            font=('Segoe UI', 12, 'bold'),
            bg='#3a3a3a',
            fg='#CCCCCC'
        )
        system_title.pack(side='left', padx=15, pady=10)
        
        self.system_status_label = tk.Label(
            system_frame,
            text="🟢 พร้อมใช้งาน",
            font=('Segoe UI', 13, 'bold'),
            bg='#3a3a3a',
            fg='#4CAF50'
        )
        self.system_status_label.pack(side='right', padx=15, pady=10)
        
        # Connection status with beautiful styling
        connection_frame = tk.Frame(info_frame, bg='#3a3a3a', relief='raised', bd=1)
        connection_frame.pack(fill='x', padx=20, pady=8)
        
        connection_title = tk.Label(
            connection_frame,
            text="🔌 การเชื่อมต่อ",
            font=('Segoe UI', 12, 'bold'),
            bg='#3a3a3a',
            fg='#CCCCCC'
        )
        connection_title.pack(side='left', padx=15, pady=10)
        
        self.connection_status_label = tk.Label(
            connection_frame,
            text="🔴 ยังไม่ได้เชื่อมต่อ",
            font=('Segoe UI', 13, 'bold'),
            bg='#3a3a3a',
            fg='#F44336'
        )
        self.connection_status_label.pack(side='right', padx=15, pady=10)
        
        # Trading status with beautiful styling
        trading_frame = tk.Frame(info_frame, bg='#3a3a3a', relief='raised', bd=1)
        trading_frame.pack(fill='x', padx=20, pady=8)
        
        trading_title = tk.Label(
            trading_frame,
            text="📈 การเทรด",
            font=('Segoe UI', 12, 'bold'),
            bg='#3a3a3a',
            fg='#CCCCCC'
        )
        trading_title.pack(side='left', padx=15, pady=10)
        
        self.trading_status_label = tk.Label(
            trading_frame,
            text="⏹️ ยังไม่ได้เริ่มเทรด",
            font=('Segoe UI', 13, 'bold'),
            bg='#3a3a3a',
            fg='#FF9800'
        )
        self.trading_status_label.pack(side='right', padx=15, pady=10)
    
    def run(self):
        """Run the main window"""
        print("🚀 Starting ArbiTrader Professional Main Window...")
        self.root.mainloop()
    
    def close(self):
        """Close the main window"""
        if hasattr(self, 'simple_dashboard') and self.simple_dashboard:
            self.simple_dashboard.close()
        self.root.destroy()