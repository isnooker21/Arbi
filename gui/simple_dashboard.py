"""
Simple Trading Dashboard - หน้า GUI เรียบง่าย
============================================

Author: AI Trading System
Version: 3.0 - Simple & Beautiful
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SimpleDashboard:
    def __init__(self, parent, trading_system=None):
        self.parent = parent
        self.trading_system = trading_system
        self.current_mode = "normal"  # default mode
        
        # Create main window
        self.main_window = tk.Toplevel(parent)
        self.main_window.title("🚀 ArbiTrader - Professional Dashboard")
        self.main_window.geometry("950x700")
        self.main_window.configure(bg='#1e1e1e')
        self.main_window.resizable(True, True)
        
        # Add window styling
        self.main_window.attributes('-alpha', 0.95)
        
        # Add professional border effect
        self.main_window.configure(highlightthickness=2, highlightbackground='#2d3748')
        
        # Center window
        self.center_window()
        
        # Setup UI
        self.setup_ui()
        
        # Load current mode
        self.load_current_mode()
        
    def center_window(self):
        """Center window on screen"""
        self.main_window.update_idletasks()
        width = 950
        height = 700
        x = (self.main_window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.main_window.winfo_screenheight() // 2) - (height // 2)
        self.main_window.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_ui(self):
        """Setup the simple dashboard interface"""
        # Header
        self.create_header()
        
        # Mode Selection
        self.create_mode_selection()
        
        # Status Display
        self.create_status_display()
        
        # Action Buttons
        self.create_action_buttons()
        
        # Footer
        self.create_footer()
    
    def create_header(self):
        """Create professional header section"""
        # Main header frame with professional styling
        header_frame = tk.Frame(self.main_window, bg='#1e1e1e', height=100)
        header_frame.pack(fill='x', padx=20, pady=(20, 15))
        header_frame.pack_propagate(False)
        
        # Inner header with professional styling
        inner_header = tk.Frame(header_frame, bg='#2d3748', relief='flat', bd=1)
        inner_header.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Title with professional styling
        title_frame = tk.Frame(inner_header, bg='#2d3748')
        title_frame.pack(side='left', fill='y', padx=25, pady=15)
        
        title_label = tk.Label(
            title_frame,
            text="🚀 ArbiTrader",
            font=('Segoe UI', 28, 'bold'),
            bg='#2d3748',
            fg='#ffffff'
        )
        title_label.pack(side='left')
        
        subtitle_label = tk.Label(
            title_frame,
            text="Professional Dashboard",
            font=('Segoe UI', 12),
            bg='#2d3748',
            fg='#a0aec0'
        )
        subtitle_label.pack(side='left', padx=(20, 0), pady=(8, 0))
        
        # Status section with beautiful indicators
        status_frame = tk.Frame(inner_header, bg='#2a2a2a')
        status_frame.pack(side='right', fill='y', padx=25, pady=15)
        
        # Status indicator with colorful animation effect
        self.status_indicator = tk.Label(
            status_frame,
            text="🟢",
            font=('Segoe UI', 18),
            bg='#2a2a2a',
            fg='#00FF88'
        )
        self.status_indicator.pack(side='right', padx=(10, 0))
        
        status_text = tk.Label(
            status_frame,
            text="ONLINE",
            font=('Segoe UI', 15, 'bold'),
            bg='#2a2a2a',
            fg='#00FF88'
        )
        status_text.pack(side='right', padx=(0, 5))
        
        # Version info with colorful styling
        version_label = tk.Label(
            status_frame,
            text="v3.0 Colorful",
            font=('Segoe UI', 11, 'bold'),
            bg='#2a2a2a',
            fg='#FFD93D'
        )
        version_label.pack(side='right', padx=(0, 15), pady=(5, 0))
    
    def create_mode_selection(self):
        """Create colorful mode selection section"""
        # Main mode frame
        mode_frame = tk.Frame(self.main_window, bg='#1a1a1a')
        mode_frame.pack(fill='x', padx=20, pady=15)
        
        # Title with colorful styling
        title_frame = tk.Frame(mode_frame, bg='#1a1a1a')
        title_frame.pack(fill='x', pady=(0, 20))
        
        title_label = tk.Label(
            title_frame,
            text="⚙️ เลือกโหมดการเทรด",
            font=('Segoe UI', 20, 'bold'),
            bg='#1a1a1a',
            fg='#FF6B6B'
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            title_frame,
            text="เลือกโหมดที่เหมาะสมกับความเสี่ยงและเป้าหมายของคุณ",
            font=('Segoe UI', 12),
            bg='#1a1a1a',
            fg='#4ECDC4'
        )
        subtitle_label.pack(pady=(8, 0))
        
        # Mode buttons container with colorful background
        buttons_container = tk.Frame(mode_frame, bg='#2a2a2a', relief='raised', bd=3,
                                     highlightthickness=2, highlightbackground='#FF6B6B')
        buttons_container.pack(fill='x', padx=10, pady=10)
        
        buttons_frame = tk.Frame(buttons_container, bg='#2a2a2a')
        buttons_frame.pack(pady=25)
        
        # Mode buttons with beautiful styling
        self.mode_buttons = {}
        
        # Mode 1: ซิ่ง - Red gradient
        mode1_btn = tk.Button(
            buttons_frame,
            text="🔥 ซิ่ง\n(เสี่ยงสูงสุด)",
            font=('Segoe UI', 14, 'bold'),
            bg='#FF4757',
            fg='white',
            width=20,
            height=4,
            relief='raised',
            bd=5,
            cursor='hand2',
            command=lambda: self.select_mode('racing'),
            activebackground='#FF6B7A',
            activeforeground='white',
            highlightthickness=2,
            highlightbackground='#FF3838'
        )
        mode1_btn.grid(row=0, column=0, padx=12, pady=12)
        self.mode_buttons['racing'] = mode1_btn
        
        # Mode 2: ซิ่งกลาง - Orange gradient
        mode2_btn = tk.Button(
            buttons_frame,
            text="⚡ ซิ่งกลาง\n(เสี่ยงปานกลาง)",
            font=('Segoe UI', 14, 'bold'),
            bg='#FF9500',
            fg='white',
            width=20,
            height=4,
            relief='raised',
            bd=5,
            cursor='hand2',
            command=lambda: self.select_mode('fast'),
            activebackground='#FFB143',
            activeforeground='white',
            highlightthickness=2,
            highlightbackground='#FF8C00'
        )
        mode2_btn.grid(row=0, column=1, padx=12, pady=12)
        self.mode_buttons['fast'] = mode2_btn
        
        # Mode 3: ปกติ - Green gradient
        mode3_btn = tk.Button(
            buttons_frame,
            text="⚖️ ปกติ\n(สมดุล)",
            font=('Segoe UI', 14, 'bold'),
            bg='#2ED573',
            fg='white',
            width=20,
            height=4,
            relief='raised',
            bd=5,
            cursor='hand2',
            command=lambda: self.select_mode('normal'),
            activebackground='#7BED9F',
            activeforeground='white',
            highlightthickness=2,
            highlightbackground='#00D2D3'
        )
        mode3_btn.grid(row=0, column=2, padx=12, pady=12)
        self.mode_buttons['normal'] = mode3_btn
        
        # Mode 4: เซฟ - Blue gradient
        mode4_btn = tk.Button(
            buttons_frame,
            text="🛡️ เซฟ\n(ปลอดภัย)",
            font=('Segoe UI', 14, 'bold'),
            bg='#3742FA',
            fg='white',
            width=20,
            height=4,
            relief='raised',
            bd=5,
            cursor='hand2',
            command=lambda: self.select_mode('safe'),
            activebackground='#5352ED',
            activeforeground='white',
            highlightthickness=2,
            highlightbackground='#2F3542'
        )
        mode4_btn.grid(row=0, column=3, padx=12, pady=12)
        self.mode_buttons['safe'] = mode4_btn
    
    def create_status_display(self):
        """Create colorful status display section"""
        # Main status frame
        status_frame = tk.Frame(self.main_window, bg='#1a1a1a')
        status_frame.pack(fill='x', padx=20, pady=15)
        
        # Status container with colorful background
        status_container = tk.Frame(status_frame, bg='#2a2a2a', relief='raised', bd=3,
                                    highlightthickness=2, highlightbackground='#FFD93D')
        status_container.pack(fill='x', padx=10, pady=10)
        
        # Title with colorful styling
        title_label = tk.Label(
            status_container,
            text="📊 สถานะระบบ",
            font=('Segoe UI', 18, 'bold'),
            bg='#2a2a2a',
            fg='#FFD93D'
        )
        title_label.pack(pady=(25, 20))
        
        # Status info container with grid layout
        info_frame = tk.Frame(status_container, bg='#2a2a2a')
        info_frame.pack(pady=(0, 20))
        
        # Current mode with colorful styling
        mode_frame = tk.Frame(info_frame, bg='#3a3a3a', relief='raised', bd=2,
                              highlightthickness=1, highlightbackground='#FF6B6B')
        mode_frame.pack(fill='x', padx=20, pady=10)
        
        mode_title = tk.Label(
            mode_frame,
            text="🎯 โหมดปัจจุบัน",
            font=('Segoe UI', 13, 'bold'),
            bg='#3a3a3a',
            fg='#4ECDC4'
        )
        mode_title.pack(side='left', padx=18, pady=12)
        
        self.current_mode_label = tk.Label(
            mode_frame,
            text="⚖️ ปกติ",
            font=('Segoe UI', 14, 'bold'),
            bg='#3a3a3a',
            fg='#2ED573'
        )
        self.current_mode_label.pack(side='right', padx=18, pady=12)
        
        # Active groups with colorful styling
        groups_frame = tk.Frame(info_frame, bg='#3a3a3a', relief='raised', bd=2,
                                highlightthickness=1, highlightbackground='#3742FA')
        groups_frame.pack(fill='x', padx=20, pady=10)
        
        groups_title = tk.Label(
            groups_frame,
            text="🔄 กลุ่มที่ทำงาน",
            font=('Segoe UI', 13, 'bold'),
            bg='#3a3a3a',
            fg='#4ECDC4'
        )
        groups_title.pack(side='left', padx=18, pady=12)
        
        self.active_groups_label = tk.Label(
            groups_frame,
            text="0/6",
            font=('Segoe UI', 14, 'bold'),
            bg='#3a3a3a',
            fg='#3742FA'
        )
        self.active_groups_label.pack(side='right', padx=18, pady=12)
        
        # Total P&L with colorful styling
        pnl_frame = tk.Frame(info_frame, bg='#3a3a3a', relief='raised', bd=2,
                             highlightthickness=1, highlightbackground='#FFD93D')
        pnl_frame.pack(fill='x', padx=20, pady=10)
        
        pnl_title = tk.Label(
            pnl_frame,
            text="💰 กำไร/ขาดทุนรวม",
            font=('Segoe UI', 13, 'bold'),
            bg='#3a3a3a',
            fg='#4ECDC4'
        )
        pnl_title.pack(side='left', padx=18, pady=12)
        
        self.total_pnl_label = tk.Label(
            pnl_frame,
            text="$0.00",
            font=('Segoe UI', 14, 'bold'),
            bg='#3a3a3a',
            fg='#FFD93D'
        )
        self.total_pnl_label.pack(side='right', padx=18, pady=12)
    
    def create_action_buttons(self):
        """Create colorful action buttons section"""
        # Main action frame
        action_frame = tk.Frame(self.main_window, bg='#1a1a1a')
        action_frame.pack(fill='x', padx=20, pady=15)
        
        # Title with colorful styling
        title_label = tk.Label(
            action_frame,
            text="🎮 การควบคุมระบบ",
            font=('Segoe UI', 20, 'bold'),
            bg='#1a1a1a',
            fg='#FF6B6B'
        )
        title_label.pack(pady=(0, 25))
        
        # Buttons container with colorful background
        buttons_container = tk.Frame(action_frame, bg='#2a2a2a', relief='raised', bd=3,
                                     highlightthickness=2, highlightbackground='#4ECDC4')
        buttons_container.pack(fill='x', padx=10, pady=10)
        
        buttons_frame = tk.Frame(buttons_container, bg='#2a2a2a')
        buttons_frame.pack(pady=25)
        
        # Start button with colorful styling
        self.start_btn = tk.Button(
            buttons_frame,
            text="▶️ เริ่มเทรด",
            font=('Segoe UI', 15, 'bold'),
            bg='#2ED573',
            fg='white',
            width=16,
            height=3,
            relief='raised',
            bd=5,
            cursor='hand2',
            command=self.start_trading,
            activebackground='#7BED9F',
            activeforeground='white',
            highlightthickness=2,
            highlightbackground='#00D2D3'
        )
        self.start_btn.grid(row=0, column=0, padx=12, pady=12)
        
        # Stop button with colorful styling
        self.stop_btn = tk.Button(
            buttons_frame,
            text="⏹️ หยุดเทรด",
            font=('Segoe UI', 15, 'bold'),
            bg='#FF4757',
            fg='white',
            width=16,
            height=3,
            relief='raised',
            bd=5,
            cursor='hand2',
            command=self.stop_trading,
            state='disabled',
            activebackground='#FF6B7A',
            activeforeground='white',
            highlightthickness=2,
            highlightbackground='#FF3838'
        )
        self.stop_btn.grid(row=0, column=1, padx=12, pady=12)
        
        # Emergency close button with colorful styling
        self.emergency_btn = tk.Button(
            buttons_frame,
            text="🚨 ปิดทั้งหมด",
            font=('Segoe UI', 15, 'bold'),
            bg='#FF9500',
            fg='white',
            width=16,
            height=3,
            relief='raised',
            bd=5,
            cursor='hand2',
            command=self.emergency_close,
            activebackground='#FFB143',
            activeforeground='white',
            highlightthickness=2,
            highlightbackground='#FF8C00'
        )
        self.emergency_btn.grid(row=0, column=2, padx=12, pady=12)
    
    def create_footer(self):
        """Create colorful footer section"""
        # Main footer frame
        footer_frame = tk.Frame(self.main_window, bg='#1a1a1a', height=85)
        footer_frame.pack(side='bottom', fill='x', padx=20, pady=(15, 20))
        footer_frame.pack_propagate(False)
        
        # Footer container with colorful background
        footer_container = tk.Frame(footer_frame, bg='#2a2a2a', relief='raised', bd=3,
                                    highlightthickness=2, highlightbackground='#FFD93D')
        footer_container.pack(fill='both', expand=True, padx=8, pady=8)
        
        # Left side - Auto refresh
        left_frame = tk.Frame(footer_container, bg='#2a2a2a')
        left_frame.pack(side='left', fill='y', padx=25, pady=15)
        
        self.auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_cb = tk.Checkbutton(
            left_frame,
            text="🔄 Auto Refresh",
            variable=self.auto_refresh_var,
            bg='#2a2a2a',
            fg='#4ECDC4',
            selectcolor='#2ED573',
            activebackground='#2a2a2a',
            font=('Segoe UI', 13, 'bold'),
            command=self.toggle_auto_refresh
        )
        auto_refresh_cb.pack(side='left')
        
        # Right side - Refresh button and info
        right_frame = tk.Frame(footer_container, bg='#2a2a2a')
        right_frame.pack(side='right', fill='y', padx=25, pady=15)
        
        # Refresh button with colorful styling
        refresh_btn = tk.Button(
            right_frame,
            text="🔄 Refresh",
            font=('Segoe UI', 13, 'bold'),
            bg='#3742FA',
            fg='white',
            width=14,
            relief='raised',
            bd=4,
            cursor='hand2',
            command=self.refresh_status,
            activebackground='#5352ED',
            activeforeground='white',
            highlightthickness=2,
            highlightbackground='#2F3542'
        )
        refresh_btn.pack(side='right', padx=(15, 0))
        
        # Version info with colorful styling
        version_label = tk.Label(
            right_frame,
            text="v3.0 Colorful",
            font=('Segoe UI', 11, 'bold'),
            bg='#2a2a2a',
            fg='#FFD93D'
        )
        version_label.pack(side='right', padx=(0, 20))
    
    def select_mode(self, mode):
        """Select trading mode"""
        self.current_mode = mode
        
        # Reset all buttons
        for btn in self.mode_buttons.values():
            btn.config(relief='raised', bd=3)
        
        # Highlight selected mode
        self.mode_buttons[mode].config(relief='sunken', bd=5)
        
        # Update current mode label
        mode_names = {
            'racing': '🔥 ซิ่ง',
            'fast': '⚡ ซิ่งกลาง',
            'normal': '⚖️ ปกติ',
            'safe': '🛡️ เซฟ'
        }
        
        self.current_mode_label.config(
            text=f"โหมดปัจจุบัน: {mode_names[mode]}",
            fg=self.get_mode_color(mode)
        )
        
        # Apply mode settings
        self.apply_mode_settings(mode)
        
        print(f"✅ Selected mode: {mode}")
    
    def get_mode_color(self, mode):
        """Get color for mode"""
        colors = {
            'racing': '#FF4444',
            'fast': '#FF8800',
            'normal': '#4CAF50',
            'safe': '#2196F3'
        }
        return colors.get(mode, '#4CAF50')
    
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
                }
            }
            
            if mode in mode_configs:
                config = mode_configs[mode]
                print(f"📋 Applying {config['name']}")
                print(f"📝 {config['description']}")
                
                # Save mode to config file
                self.save_mode_to_config(mode, config)
                
                # Show confirmation
                messagebox.showinfo(
                    "✅ เปลี่ยนโหมดสำเร็จ",
                    f"เปลี่ยนเป็นโหมด: {config['name']}\n\n{config['description']}"
                )
                
        except Exception as e:
            print(f"❌ Error applying mode: {e}")
            messagebox.showerror("❌ Error", f"ไม่สามารถเปลี่ยนโหมดได้: {str(e)}")
    
    def save_mode_to_config(self, mode, config):
        """Save mode configuration to config file"""
        try:
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
    
    def load_current_mode(self):
        """Load current mode from config"""
        try:
            config_file_path = os.path.join('config', 'adaptive_params.json')
            if os.path.exists(config_file_path):
                with open(config_file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Try to detect current mode from config values
                threshold = config.get('arbitrage_params', {}).get('detection', {}).get('min_threshold', 0.00005)
                
                if threshold <= 0.00001:
                    self.select_mode('racing')
                elif threshold <= 0.00003:
                    self.select_mode('fast')
                elif threshold <= 0.00005:
                    self.select_mode('normal')
                else:
                    self.select_mode('safe')
                    
        except Exception as e:
            print(f"❌ Error loading current mode: {e}")
    
    def start_trading(self):
        """Start trading"""
        try:
            print(f"🚀 Starting trading in {self.current_mode} mode")
            
            # Enable stop button, disable start button
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            
            # Update status
            self.status_indicator.config(fg='#4CAF50')
            
            messagebox.showinfo(
                "🚀 เริ่มเทรด",
                f"เริ่มเทรดในโหมด: {self.get_mode_name()}\n\nระบบจะเริ่มทำงานทันที!"
            )
            
        except Exception as e:
            print(f"❌ Error starting trading: {e}")
            messagebox.showerror("❌ Error", f"ไม่สามารถเริ่มเทรดได้: {str(e)}")
    
    def stop_trading(self):
        """Stop trading"""
        try:
            print("⏹️ Stopping trading")
            
            # Disable stop button, enable start button
            self.stop_btn.config(state='disabled')
            self.start_btn.config(state='normal')
            
            # Update status
            self.status_indicator.config(fg='#F44336')
            
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
    
    def toggle_auto_refresh(self):
        """Toggle auto refresh"""
        if self.auto_refresh_var.get():
            print("🔄 Auto refresh enabled")
        else:
            print("🔄 Auto refresh disabled")
    
    def refresh_status(self):
        """Refresh status display"""
        try:
            print("🔄 Refreshing status...")
            
            # Update active groups (simulate)
            import random
            active_groups = random.randint(0, 6)
            self.active_groups_label.config(text=f"กลุ่มที่ทำงาน: {active_groups}/6")
            
            # Update total P&L (simulate)
            total_pnl = random.uniform(-100, 500)
            color = '#4CAF50' if total_pnl >= 0 else '#F44336'
            self.total_pnl_label.config(
                text=f"กำไร/ขาดทุนรวม: ${total_pnl:.2f}",
                fg=color
            )
            
            print("✅ Status refreshed")
            
        except Exception as e:
            print(f"❌ Error refreshing status: {e}")
    
    def get_mode_name(self):
        """Get current mode name"""
        mode_names = {
            'racing': '🔥 ซิ่ง',
            'fast': '⚡ ซิ่งกลาง',
            'normal': '⚖️ ปกติ',
            'safe': '🛡️ เซฟ'
        }
        return mode_names.get(self.current_mode, '⚖️ ปกติ')
    
    def show(self):
        """Show the dashboard"""
        self.main_window.deiconify()
        self.main_window.lift()
    
    def close(self):
        """Close the dashboard"""
        self.main_window.destroy()
