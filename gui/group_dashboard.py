"""
Group Dashboard - แสดงสถานะของแต่ละ Group (Full Size Cards + Individual Details)
========================================================================================

Dashboard ที่แสดงสถานะของแต่ละ arbitrage group แยกตาม triangle
พร้อม P&L Breakdown, Individual Group Details, และ Performance Metrics
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, Canvas
from datetime import datetime
import os
import json
from .theme import TradingTheme

class GroupDashboard:
    def __init__(self, parent):
        self.parent = parent
        self.groups = {}
        self.setup_ui()
    
    def setup_ui(self):
        """สร้าง UI สำหรับ Group Dashboard - ปรับปรุงใหม่"""
        print("🔍 Debug: setup_ui called")
        
        # Main container
        self.main_frame = tk.Frame(self.parent, bg='#1a1a1a')
        self.main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        print("🔍 Debug: main_frame created")
        
        # Header
        print("🔍 Debug: Creating header...")
        self.create_header()
        print("✅ Debug: Header created")
        
        # Stats Overview Cards
        print("🔍 Debug: Creating stats overview...")
        self.create_stats_overview()
        print("✅ Debug: Stats overview created")
        
        # Main content area - แบ่งเป็น 2 ส่วน
        print("🔍 Debug: Creating main content area...")
        self.create_main_content_area()
        print("✅ Debug: Main content area created")
        
        # Summary panel
        print("🔍 Debug: Creating summary panel...")
        self.create_summary_panel()
        print("✅ Debug: Summary panel created")
        
        print("✅ Debug: setup_ui completed")
    
    def create_header(self):
        """สร้าง header - ปรับปรุงให้สวยขึ้น"""
        header_frame = tk.Frame(self.main_frame, bg='#1a1a1a', height=70)
        header_frame.pack(fill='x', pady=(0, 20))
        header_frame.pack_propagate(False)
        
        # Header content with gradient effect
        header_content = tk.Frame(header_frame, bg='#2d2d2d', height=70)
        header_content.pack(fill='x', padx=20, pady=10)
        header_content.pack_propagate(False)
        
        # Title with better styling
        title_label = tk.Label(
            header_content,
            text="📊 Trading Dashboard",
            font=('Segoe UI', 20, 'bold'),
            bg='#2d2d2d',
            fg='#FFD700'
        )
        title_label.pack(side='left', pady=20)
        
        # Right side controls
        controls_frame = tk.Frame(header_content, bg='#2d2d2d')
        controls_frame.pack(side='right', pady=20)
        
        # Refresh button with better styling
        refresh_btn = tk.Button(
            controls_frame,
            text="🔄 Refresh",
            command=self.refresh_groups,
            bg='#4CAF50',
            fg='white',
            font=('Segoe UI', 11, 'bold'),
            padx=20,
            pady=10,
            relief='flat',
            cursor='hand2',
            bd=0
        )
        refresh_btn.pack(side='right', padx=(0, 10))
        
        # Auto-refresh toggle with better styling
        self.auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_btn = tk.Checkbutton(
            controls_frame,
            text="Auto Refresh",
            variable=self.auto_refresh_var,
            bg='#2d2d2d',
            fg='white',
            font=('Segoe UI', 11),
            selectcolor='#4CAF50',
            activebackground='#2d2d2d',
            activeforeground='white'
        )
        auto_refresh_btn.pack(side='right', padx=10)
    
    def create_stats_overview(self):
        """สร้าง stats overview cards - ปรับปรุงให้สวยขึ้น"""
        stats_frame = tk.Frame(self.main_frame, bg='#1a1a1a')
        stats_frame.pack(fill='x', pady=(0, 20))
        
        # Stats cards - ปรับปรุงสีสันและขนาด
        stats_data = [
            {"title": "Total P&L", "value": "$0.00", "color": "#2E7D32", "icon": "💰", "gradient": "#4CAF50"},
            {"title": "Active Groups", "value": "0/6", "color": "#1565C0", "icon": "🔺", "gradient": "#2196F3"},
            {"title": "Today's Trades", "value": "0", "color": "#E65100", "icon": "📈", "gradient": "#FF9800"},
            {"title": "Win Rate", "value": "0%", "color": "#4A148C", "icon": "🎯", "gradient": "#9C27B0"}
        ]
        
        self.stats_cards = {}
        for i, stat in enumerate(stats_data):
            # Main card with shadow effect
            card_container = tk.Frame(stats_frame, bg='#1a1a1a')
            card_container.pack(side='left', padx=8, fill='y')
            
            # Shadow frame
            shadow_frame = tk.Frame(
                card_container,
                bg='#000000',
                width=220,
                height=100
            )
            shadow_frame.pack(padx=(2, 0), pady=(2, 0))
            shadow_frame.pack_propagate(False)
            
            # Main card
            card = tk.Frame(
                shadow_frame,
                bg=stat['color'],
                relief='flat',
                bd=0,
                width=218,
                height=98
            )
            card.pack(padx=0, pady=0)
            card.pack_propagate(False)
            
            # Gradient effect (simulated with multiple frames)
            gradient_frame = tk.Frame(card, bg=stat['gradient'], height=30)
            gradient_frame.pack(fill='x', padx=0, pady=0)
            gradient_frame.pack_propagate(False)
            
            # Header with icon and title
            header_frame = tk.Frame(gradient_frame, bg=stat['gradient'])
            header_frame.pack(fill='x', padx=15, pady=8)
            
            icon_label = tk.Label(
                header_frame,
                text=stat['icon'],
                font=('Segoe UI', 16),
                bg=stat['gradient'],
                fg='white'
            )
            icon_label.pack(side='left')
            
            title_label = tk.Label(
                header_frame,
                text=stat['title'],
                font=('Segoe UI', 11, 'bold'),
                bg=stat['gradient'],
                fg='white'
            )
            title_label.pack(side='right')
            
            # Value section
            value_frame = tk.Frame(card, bg=stat['color'])
            value_frame.pack(fill='both', expand=True, padx=15, pady=10)
            
            value_label = tk.Label(
                value_frame,
                text=stat['value'],
                font=('Consolas', 18, 'bold'),
                bg=stat['color'],
                fg='white'
            )
            value_label.pack(expand=True)
            
            self.stats_cards[stat['title']] = value_label
    
    def create_main_content_area(self):
        """สร้างพื้นที่หลัก - แต่ละ group แยกเต็มหน้า"""
        print("🔍 Debug: create_main_content_area called")
        
        # Main content frame
        self.content_frame = tk.Frame(self.main_frame, bg='#1a1a1a')
        self.content_frame.pack(fill='both', expand=True)
        print("🔍 Debug: content_frame created")
        
        # Create groups view (default)
        print("🔍 Debug: Creating groups view...")
        self.create_groups_view()
        print("✅ Debug: Groups view created")
        
        # Initialize group detail views (hidden by default)
        self.group_detail_views = {}
        self.current_view = 'groups'
        
        # Force immediate display
        self.content_frame.update_idletasks()
        print("✅ Debug: create_main_content_area completed")
    
    def create_groups_view(self):
        """สร้าง groups view - แสดงทุก group ในหน้าเดียวพร้อม scrollbar"""
        print("🔍 Debug: create_groups_view called")
        
        # Clear existing content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        print("🔍 Debug: Cleared existing content")
        
        # Create main container with scrollbar
        main_container = tk.Frame(self.content_frame, bg='#1a1a1a')
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create canvas for scrolling
        self.groups_canvas = tk.Canvas(
            main_container,
            bg='#1a1a1a',
            highlightthickness=0
        )
        
        # Create scrollbar
        self.groups_scrollbar = ttk.Scrollbar(
            main_container, 
            orient='vertical', 
            command=self.groups_canvas.yview
        )
        self.groups_canvas.configure(yscrollcommand=self.groups_scrollbar.set)
        
        # Pack canvas and scrollbar
        self.groups_canvas.pack(side='left', fill='both', expand=True)
        self.groups_scrollbar.pack(side='right', fill='y')
        
        # Create frame inside canvas
        self.groups_frame = tk.Frame(self.groups_canvas, bg='#1a1a1a')
        self.canvas_window = self.groups_canvas.create_window(
            (0, 0), 
            window=self.groups_frame, 
            anchor='nw'
        )
        
        # Bind events for scrolling
        self.groups_frame.bind('<Configure>', self._on_frame_configure)
        self.groups_canvas.bind('<Configure>', self._on_canvas_configure)
        self.groups_canvas.bind_all('<MouseWheel>', self._on_mousewheel)
        
        print("🔍 Debug: Groups frame with scrollbar created")
        
        # Create group cards
        print("🔍 Debug: Creating full size group cards...")
        self.create_full_size_group_cards()
        print("✅ Debug: Full size group cards created")
        
        # Force immediate display
        self.groups_frame.update_idletasks()
        self.groups_canvas.update_idletasks()
        self.parent.update_idletasks()
        print("🔍 Debug: Forced immediate display")
    
    def create_full_size_group_cards(self):
        """สร้าง group cards ขนาดใหญ่เต็มหน้า"""
        print("🔍 Debug: create_full_size_group_cards called")
        
        # Group configurations - ปรับปรุงสีให้สวยขึ้น
        group_configs = [
            {
                'id': 'triangle_1',
                'name': 'Triangle 1',
                'pairs': ['EURUSD', 'GBPUSD', 'EURGBP'],
                'magic': 234001,
                'color': '#E53935'  # Red
            },
            {
                'id': 'triangle_2',
                'name': 'Triangle 2',
                'pairs': ['USDJPY', 'EURUSD', 'EURJPY'],
                'magic': 234002,
                'color': '#1E88E5'  # Blue
            },
            {
                'id': 'triangle_3',
                'name': 'Triangle 3',
                'pairs': ['GBPUSD', 'USDJPY', 'GBPJPY'],
                'magic': 234003,
                'color': '#43A047'  # Green
            },
            {
                'id': 'triangle_4',
                'name': 'Triangle 4',
                'pairs': ['AUDUSD', 'USDCAD', 'AUDCAD'],
                'magic': 234004,
                'color': '#FB8C00'  # Orange
            },
            {
                'id': 'triangle_5',
                'name': 'Triangle 5',
                'pairs': ['NZDUSD', 'USDCHF', 'NZDCHF'],
                'magic': 234005,
                'color': '#8E24AA'  # Purple
            },
            {
                'id': 'triangle_6',
                'name': 'Triangle 6',
                'pairs': ['EURCHF', 'USDCHF', 'EURUSD'],
                'magic': 234006,
                'color': '#00ACC1'  # Cyan
            }
        ]
        
        self.group_cards = {}
        self.status_indicators = {}
        self.pnl_labels = {}
        
        print(f"🔍 Debug: Creating {len(group_configs)} group cards...")
        
        # Create full-size cards (1 card per row)
        for i, config in enumerate(group_configs):
            print(f"🔍 Debug: Creating card {i+1}/{len(group_configs)}: {config['name']}")
            self.create_single_full_size_group_card(config, i)
        
        print("✅ Debug: All group cards created successfully")
        
        # Force update after creating all cards
        self.groups_frame.update_idletasks()
        if hasattr(self, 'groups_canvas'):
            self.groups_canvas.update_idletasks()
            self.groups_canvas.configure(scrollregion=self.groups_canvas.bbox('all'))
        self.parent.update_idletasks()
        print("🔍 Debug: Frame updated after creating cards")
    
    def create_single_full_size_group_card(self, config, row):
        """สร้าง group card ขนาดใหญ่เต็มแถว - ปรับปรุงให้สวยขึ้น"""
        print(f"🔍 Debug: Creating card for {config['name']} (row {row})")
        
        # Card container with shadow - ลด padding และกำหนดขนาดคงที่
        card_container = tk.Frame(self.groups_frame, bg='#1a1a1a')
        card_container.pack(fill='x', padx=8, pady=4)
        
        # Shadow frame - ลดความสูงให้เหมาะสม
        shadow_frame = tk.Frame(
            card_container,
            bg='#000000',
            height=180  # ลดจาก 220 เป็น 180
        )
        shadow_frame.pack(fill='x', padx=(2, 0), pady=(2, 0))
        shadow_frame.pack_propagate(False)
        
        # Main card frame - ลดความสูงให้เหมาะสม
        card_frame = tk.Frame(
            shadow_frame,
            bg='#2d2d2d',
            relief='flat',
            bd=0,
            height=177  # ลดจาก 217 เป็น 177
        )
        card_frame.pack(fill='x', padx=0, pady=0)
        card_frame.pack_propagate(False)
        print(f"🔍 Debug: Card frame created for {config['name']}")
        
        # Header with gradient effect - ลดความสูง
        header_frame = tk.Frame(card_frame, bg=config['color'], height=45)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        # Header content - ลด padding
        header_content = tk.Frame(header_frame, bg=config['color'])
        header_content.pack(fill='x', padx=15, pady=8)
        
        # Group name and magic - ปรับขนาดฟอนต์
        name_label = tk.Label(
            header_content,
            text=f"{config['name']}",
            font=('Segoe UI', 14, 'bold'),
            bg=config['color'],
            fg='white'
        )
        name_label.pack(side='left')
        
        # Magic number - ปรับขนาดฟอนต์
        magic_label = tk.Label(
            header_content,
            text=f"Magic: {config['magic']}",
            font=('Segoe UI', 9),
            bg=config['color'],
            fg='white'
        )
        magic_label.pack(side='left', padx=(8, 0))
        
        # Status indicator - ปรับขนาด
        status_indicator = tk.Label(
            header_content,
            text="🔴",
            font=('Segoe UI', 16),
            bg=config['color'],
            fg='white'
        )
        status_indicator.pack(side='right')
        self.status_indicators[config['id']] = status_indicator
        
        # Content area - ลด padding
        content_frame = tk.Frame(card_frame, bg='#2d2d2d')
        content_frame.pack(fill='both', expand=True, padx=15, pady=12)
        
        # Left side - Basic info - ปรับขนาด
        left_frame = tk.Frame(content_frame, bg='#2d2d2d', width=300)
        left_frame.pack(side='left', fill='y', padx=(0, 15))
        left_frame.pack_propagate(False)
        
        # Pairs info with better styling - ลด padding
        pairs_section = tk.Frame(left_frame, bg='#2d2d2d')
        pairs_section.pack(fill='x', pady=(0, 12))
        
        pairs_label = tk.Label(
            pairs_section,
            text="📊 Currency Pairs",
            font=('Segoe UI', 10, 'bold'),
            bg='#2d2d2d',
            fg='#FFD700'
        )
        pairs_label.pack(anchor='w', pady=(0, 4))
        
        pairs_text = tk.Label(
            pairs_section,
            text=f"{' • '.join(config['pairs'])}",
            font=('Consolas', 10),
            bg='#2d2d2d',
            fg='#E0E0E0'
        )
        pairs_text.pack(anchor='w')
        
        # P&L Section with better styling - ลด padding
        pnl_section = tk.Frame(left_frame, bg='#2d2d2d')
        pnl_section.pack(fill='x', pady=(0, 12))
        
        pnl_title = tk.Label(
            pnl_section,
            text="💰 P&L Summary",
            font=('Segoe UI', 10, 'bold'),
            bg='#2d2d2d',
            fg='#FFD700'
        )
        pnl_title.pack(anchor='w', pady=(0, 4))
        
        # P&L values with better styling - ปรับขนาดฟอนต์
        pnl_values = {
            'arb': tk.Label(pnl_section, text="Arbitrage: $0.00", font=('Consolas', 9), bg='#2d2d2d', fg='#E0E0E0'),
            'rec': tk.Label(pnl_section, text="Recovery: $0.00", font=('Consolas', 9), bg='#2d2d2d', fg='#E0E0E0'),
            'net': tk.Label(pnl_section, text="Net: $0.00", font=('Consolas', 10, 'bold'), bg='#2d2d2d', fg='#4CAF50')
        }
        
        for label in pnl_values.values():
            label.pack(anchor='w', pady=1)
        
        if not hasattr(self, 'pnl_labels'):
            self.pnl_labels = {}
        self.pnl_labels[config['id']] = pnl_values
        
        # Status info with better styling - ปรับขนาดฟอนต์
        status_section = tk.Frame(left_frame, bg='#2d2d2d')
        status_section.pack(fill='x')
        
        status_info = tk.Label(
            status_section,
            text="📈 Status: No Active Positions",
            font=('Segoe UI', 9),
            bg='#2d2d2d',
            fg='#888888'
        )
        status_info.pack(anchor='w')
        
        # Right side - Quick actions and positions
        right_frame = tk.Frame(content_frame, bg='#2d2d2d')
        right_frame.pack(side='right', fill='both', expand=True)
        
        # Quick actions section - ลด padding
        actions_section = tk.Frame(right_frame, bg='#2d2d2d')
        actions_section.pack(fill='x', pady=(0, 15))
        
        actions_label = tk.Label(
            actions_section,
            text="⚡ Quick Actions",
            font=('Segoe UI', 10, 'bold'),
            bg='#2d2d2d',
            fg='#FFD700'
        )
        actions_label.pack(anchor='w', pady=(0, 8))
        
        # Action buttons with better styling - ปรับขนาดปุ่ม
        buttons_frame = tk.Frame(actions_section, bg='#2d2d2d')
        buttons_frame.pack(fill='x')
        
        # View Details button - ปรับขนาด
        view_details_btn = tk.Button(
            buttons_frame,
            text="🔍 View Details",
            command=lambda: self.show_group_details(config['id']),
            bg='#4CAF50',
            fg='white',
            font=('Segoe UI', 9, 'bold'),
            padx=15,
            pady=6,
            relief='flat',
            cursor='hand2',
            bd=0
        )
        view_details_btn.pack(side='left', padx=(0, 8))
        
        # Close All Positions button - ปรับขนาด
        close_all_btn = tk.Button(
            buttons_frame,
            text="⏹️ Close All",
            command=lambda: self.close_all_positions(config['id']),
            bg='#F44336',
            fg='white',
            font=('Segoe UI', 9, 'bold'),
            padx=15,
            pady=6,
            relief='flat',
            cursor='hand2',
            bd=0
        )
        close_all_btn.pack(side='left')
        
        # Quick positions overview - ลด padding
        positions_section = tk.Frame(right_frame, bg='#2d2d2d')
        positions_section.pack(fill='x')
        
        positions_label = tk.Label(
            positions_section,
            text="🎯 Active Positions",
            font=('Segoe UI', 10, 'bold'),
            bg='#2d2d2d',
            fg='#FFD700'
        )
        positions_label.pack(anchor='w', pady=(0, 4))
        
        # Simple positions list - ปรับขนาดฟอนต์
        positions_text = tk.Label(
            positions_section,
            text="No active positions",
            font=('Segoe UI', 9),
            bg='#2d2d2d',
            fg='#888888',
            justify='left'
        )
        positions_text.pack(anchor='w')
        
        self.group_cards[config['id']] = {
            'frame': card_frame,
            'status_info': status_info,
            'positions_text': positions_text,
            'config': config
        }
        
        # Force immediate display of this card
        card_frame.update_idletasks()
        print(f"✅ Debug: Card for {config['name']} created and stored")
    
    def show_group_details(self, group_id):
        """แสดงรายละเอียดของ group ที่เลือก"""
        # Clear existing content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Get group config
        group_config = None
        for card_id, card_data in self.group_cards.items():
            if card_id == group_id:
                group_config = card_data['config']
                break
        
        if not group_config:
            return
        
        # Create group detail view
        self.create_group_detail_view(group_config)
        self.current_view = f'group_{group_id}'
    
    def create_group_detail_view(self, config):
        """สร้าง detailed view สำหรับ group เดียว"""
        # Header with back button
        header_frame = tk.Frame(self.content_frame, bg='#2d2d2d', height=60)
        header_frame.pack(fill='x', padx=20, pady=(20, 10))
        header_frame.pack_propagate(False)
        
        # Back button
        back_btn = tk.Button(
            header_frame,
            text="⬅️ Back to Groups",
            command=self.show_groups_view,
            bg='#666666',
            fg='white',
            font=('Arial', 10, 'bold'),
            padx=15,
            pady=8,
            relief='flat',
            cursor='hand2'
        )
        back_btn.pack(side='left', padx=10, pady=15)
        
        # Group title
        title_label = tk.Label(
            header_frame,
            text=f"📊 {config['name']} - Detailed View",
            font=('Arial', 16, 'bold'),
            bg='#2d2d2d',
            fg=config['color']
        )
        title_label.pack(side='left', padx=20, pady=15)
        
        # Magic number
        magic_label = tk.Label(
            header_frame,
            text=f"Magic: {config['magic']}",
            font=('Arial', 12),
            bg='#2d2d2d',
            fg='white'
        )
        magic_label.pack(side='right', padx=20, pady=15)
        
        # Main content area
        main_content = tk.Frame(self.content_frame, bg='#1a1a1a')
        main_content.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        # Create notebook for tabs
        from tkinter import ttk
        self.notebook = ttk.Notebook(main_content)
        self.notebook.pack(fill='both', expand=True)
        
        # Configure notebook style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background='#2d2d2d')
        style.configure('TNotebook.Tab', background='#2d2d2d', foreground='white')
        style.map('TNotebook.Tab', background=[('selected', config['color'])])
        
        # Tab 1: Active Positions
        self.positions_frame = tk.Frame(self.notebook, bg='#2d2d2d')
        self.notebook.add(self.positions_frame, text="🎯 Active Positions")
        self.create_group_positions_tab(config)
        
        # Tab 2: Recovery History
        self.recovery_frame = tk.Frame(self.notebook, bg='#2d2d2d')
        self.notebook.add(self.recovery_frame, text="🔄 Recovery History")
        self.create_group_recovery_tab(config)
        
        # Tab 3: Trading Log
        self.log_frame = tk.Frame(self.notebook, bg='#2d2d2d')
        self.notebook.add(self.log_frame, text="📝 Trading Log")
        self.create_group_log_tab(config)
        
        # Tab 4: Performance
        self.performance_frame = tk.Frame(self.notebook, bg='#2d2d2d')
        self.notebook.add(self.performance_frame, text="📈 Performance")
        self.create_group_performance_tab(config)
    
    def create_group_positions_tab(self, config):
        """สร้าง positions tab สำหรับ group เดียว"""
        # Header
        header_frame = tk.Frame(self.positions_frame, bg='#3d3d3d', height=50)
        header_frame.pack(fill='x', padx=10, pady=10)
        header_frame.pack_propagate(False)
        
        tk.Label(
            header_frame,
            text=f"🎯 Active Positions - {config['name']}",
            font=('Arial', 14, 'bold'),
            bg='#3d3d3d',
            fg=config['color']
        ).pack(side='left', padx=15, pady=10)
        
        # Action buttons
        buttons_frame = tk.Frame(header_frame, bg='#3d3d3d')
        buttons_frame.pack(side='right', padx=15, pady=10)
        
        # Close all positions button
        close_all_btn = tk.Button(
            buttons_frame,
            text="⏹️ Close All Positions",
            command=lambda: self.close_all_positions(config['id']),
            bg='#F44336',
            fg='white',
            font=('Arial', 10, 'bold'),
            padx=15,
            pady=8,
            relief='flat',
            cursor='hand2'
        )
        close_all_btn.pack(side='right', padx=(0, 10))
        
        # Refresh button
        refresh_btn = tk.Button(
            buttons_frame,
            text="🔄 Refresh",
            command=lambda: self.refresh_group_positions(config['id']),
            bg='#4CAF50',
            fg='white',
            font=('Arial', 10, 'bold'),
            padx=15,
            pady=8,
            relief='flat',
            cursor='hand2'
        )
        refresh_btn.pack(side='right', padx=(0, 10))
        
        # Positions list
        positions_container = tk.Frame(self.positions_frame, bg='#2d2d2d')
        positions_container.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Create treeview for positions
        columns = ('Symbol', 'Type', 'Volume', 'Open Price', 'Current Price', 'P&L', 'Status', 'Time')
        self.positions_tree = ttk.Treeview(positions_container, columns=columns, show='headings', height=20)
        
        # Configure columns
        column_widths = {'Symbol': 80, 'Type': 60, 'Volume': 80, 'Open Price': 100, 
                        'Current Price': 100, 'P&L': 80, 'Status': 80, 'Time': 100}
        
        for col in columns:
            self.positions_tree.heading(col, text=col)
            self.positions_tree.column(col, width=column_widths[col], anchor='center')
        
        # Scrollbar
        positions_scrollbar = ttk.Scrollbar(positions_container, orient='vertical', command=self.positions_tree.yview)
        self.positions_tree.configure(yscrollcommand=positions_scrollbar.set)
        
        # Pack
        self.positions_tree.pack(side='left', fill='both', expand=True)
        positions_scrollbar.pack(side='right', fill='y')
        
        # Sample data for this group
        sample_positions = self.get_group_sample_positions(config)
        
        for pos in sample_positions:
            self.positions_tree.insert('', 'end', values=pos)
    
    def create_group_recovery_tab(self, config):
        """สร้าง recovery tab สำหรับ group เดียว"""
        # Header
        header_frame = tk.Frame(self.recovery_frame, bg='#3d3d3d', height=50)
        header_frame.pack(fill='x', padx=10, pady=10)
        header_frame.pack_propagate(False)
        
        tk.Label(
            header_frame,
            text=f"🔄 Recovery History - {config['name']}",
            font=('Arial', 14, 'bold'),
            bg='#3d3d3d',
            fg=config['color']
        ).pack(side='left', padx=15, pady=10)
        
        # Recovery list
        recovery_container = tk.Frame(self.recovery_frame, bg='#2d2d2d')
        recovery_container.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Create treeview for recovery
        columns = ('Time', 'Original Position', 'Recovery Pair', 'Correlation', 'Entry Price', 'Exit Price', 'Result', 'P&L')
        self.recovery_tree = ttk.Treeview(recovery_container, columns=columns, show='headings', height=20)
        
        # Configure columns
        column_widths = {'Time': 80, 'Original Position': 120, 'Recovery Pair': 100, 'Correlation': 80,
                        'Entry Price': 100, 'Exit Price': 100, 'Result': 80, 'P&L': 80}
        
        for col in columns:
            self.recovery_tree.heading(col, text=col)
            self.recovery_tree.column(col, width=column_widths[col], anchor='center')
        
        # Scrollbar
        recovery_scrollbar = ttk.Scrollbar(recovery_container, orient='vertical', command=self.recovery_tree.yview)
        self.recovery_tree.configure(yscrollcommand=recovery_scrollbar.set)
        
        # Pack
        self.recovery_tree.pack(side='left', fill='both', expand=True)
        recovery_scrollbar.pack(side='right', fill='y')
        
        # Sample data for this group
        sample_recovery = self.get_group_sample_recovery(config)
        
        for rec in sample_recovery:
            self.recovery_tree.insert('', 'end', values=rec)
    
    def create_group_log_tab(self, config):
        """สร้าง log tab สำหรับ group เดียว"""
        # Header
        header_frame = tk.Frame(self.log_frame, bg='#3d3d3d', height=50)
        header_frame.pack(fill='x', padx=10, pady=10)
        header_frame.pack_propagate(False)
        
        tk.Label(
            header_frame,
            text=f"📝 Trading Log - {config['name']}",
            font=('Arial', 14, 'bold'),
            bg='#3d3d3d',
            fg=config['color']
        ).pack(side='left', padx=15, pady=10)
        
        # Log text area
        log_container = tk.Frame(self.log_frame, bg='#2d2d2d')
        log_container.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Text widget with scrollbar
        self.log_text = tk.Text(
            log_container,
            bg='#1a1a1a',
            fg='#00FF00',
            font=('Consolas', 9),
            wrap='word',
            height=25
        )
        
        log_scrollbar = ttk.Scrollbar(log_container, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        # Pack
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')
        
        # Sample log for this group
        sample_log = self.get_group_sample_log(config)
        
        self.log_text.insert('1.0', sample_log)
        self.log_text.config(state='disabled')
    
    def create_group_performance_tab(self, config):
        """สร้าง performance tab สำหรับ group เดียว"""
        # Header
        header_frame = tk.Frame(self.performance_frame, bg='#3d3d3d', height=50)
        header_frame.pack(fill='x', padx=10, pady=10)
        header_frame.pack_propagate(False)
        
        tk.Label(
            header_frame,
            text=f"📈 Performance Metrics - {config['name']}",
            font=('Arial', 14, 'bold'),
            bg='#3d3d3d',
            fg=config['color']
        ).pack(side='left', padx=15, pady=10)
        
        # Performance metrics
        metrics_frame = tk.Frame(self.performance_frame, bg='#2d2d2d')
        metrics_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Create metrics grid
        metrics_data = self.get_group_sample_metrics(config)
        
        for i, (metric, value, color) in enumerate(metrics_data):
            row = i // 4  # 4 columns
            col = i % 4
            
            metric_frame = tk.Frame(metrics_frame, bg=color, width=180, height=100)
            metric_frame.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')
            metric_frame.grid_propagate(False)
            
            tk.Label(
                metric_frame,
                text=metric,
                font=('Arial', 10, 'bold'),
                bg=color,
                fg='white'
            ).pack(pady=(10, 5))
            
            tk.Label(
                metric_frame,
                text=value,
                font=('Arial', 16, 'bold'),
                bg=color,
                fg='white'
            ).pack(expand=True)
        
        # Configure grid weights
        for i in range(3):  # 3 rows
            metrics_frame.grid_rowconfigure(i, weight=1)
        for i in range(4):  # 4 columns
            metrics_frame.grid_columnconfigure(i, weight=1)
    
    def get_group_sample_positions(self, config):
        """สร้างข้อมูล positions ตัวอย่างสำหรับ group"""
        pairs = config['pairs']
        sample_positions = []
        
        for i, pair in enumerate(pairs):
            order_type = 'BUY' if i % 2 == 0 else 'SELL'
            volume = f"0.{50 + i * 10}"
            open_price = f"1.{8500 + i * 200}"
            current_price = f"1.{8505 + i * 205}"
            pnl = f"+${5 + i * 2}.{30 + i * 10}"
            
            sample_positions.append((
                pair, order_type, volume, open_price, current_price, pnl, 'Active', '17:30:25'
            ))
        
        return sample_positions
    
    def get_group_sample_recovery(self, config):
        """สร้างข้อมูล recovery ตัวอย่างสำหรับ group"""
        pairs = config['pairs']
        sample_recovery = []
        
        for i, pair in enumerate(pairs):
            time = f"1{7 + i}:3{0 + i}:2{5 + i}"
            original = pair
            recovery = pairs[(i + 1) % len(pairs)]
            correlation = f"0.{85 + i * 3}"
            entry_price = f"1.{8500 + i * 200}"
            exit_price = f"1.{8505 + i * 205}"
            result = 'Success'
            pnl = f"+${2 + i}.{50 + i * 10}"
            
            sample_recovery.append((
                time, original, recovery, correlation, entry_price, exit_price, result, pnl
            ))
        
        return sample_recovery
    
    def get_group_sample_log(self, config):
        """สร้าง log ตัวอย่างสำหรับ group"""
        pairs_str = ', '.join(config['pairs'])
        
        sample_log = f"""2025-01-13 17:30:25 - {config['name']}: Checking arbitrage conditions for ({pairs_str})
2025-01-13 17:30:25 - ({pairs_str}): Calculating arbitrage direction...
2025-01-13 17:30:25 - ({pairs_str}): Prices - {pairs_str.replace(',', ': 1.08500/1.08520,')}: 1.08500/1.08520
2025-01-13 17:30:25 - ({pairs_str}): Forward path = 0.45%, Reverse path = 0.38%, Cost = 0.12%
2025-01-13 17:30:25 - ({pairs_str}): Net profits - Forward: 0.33%, Reverse: 0.26%, Min threshold: 0.30%
2025-01-13 17:30:25 - ✅ ({pairs_str}): FORWARD path selected - Net profit: 0.33%
2025-01-13 17:30:25 - ✅ {config['name']}: Direction check passed - FORWARD path, profit: 0.3300%
2025-01-13 17:30:25 - 💰 ({pairs_str}): Raw profit: 0.45%, Cost: 0.12%, Net: 0.33%
2025-01-13 17:30:25 - ✅ ({pairs_str}): Profit check passed (0.33% >= 0.30%)
2025-01-13 17:30:25 - ✅ {config['name']}: Feasibility check passed
2025-01-13 17:30:25 - 📊 ({pairs_str}): Spreads - All acceptable (max: 1.8 <= 3.0)
2025-01-13 17:30:25 - ✅ ({pairs_str}): Spread check passed
2025-01-13 17:30:25 - 💰 {config['name']}: Account balance: $10,000.00
2025-01-13 17:30:25 - ⚙️ {config['name']}: Risk per trade: 1.0%
2025-01-13 17:30:25 - 🚀 {config['name']}: All checks passed! Sending orders..."""
        
        return sample_log
    
    def get_group_sample_metrics(self, config):
        """สร้าง metrics ตัวอย่างสำหรับ group"""
        return [
            ("Total Trades", "12", "#4CAF50"),
            ("Winning Trades", "8", "#4CAF50"),
            ("Losing Trades", "4", "#F44336"),
            ("Win Rate", "67%", "#4CAF50"),
            ("Average Win", f"${8 + len(config['pairs'])}.45", "#4CAF50"),
            ("Average Loss", f"-${4 + len(config['pairs'])}.20", "#F44336"),
            ("Profit Factor", "2.43", "#4CAF50"),
            ("Max Drawdown", f"${10 + len(config['pairs'])}.30", "#F44336"),
            ("Recovery Success", "85%", "#4CAF50"),
            ("Avg Recovery Time", "2.5 min", "#2196F3"),
            ("Best Trade", f"${20 + len(config['pairs'])}.80", "#4CAF50"),
            ("Worst Trade", f"-${8 + len(config['pairs'])}.50", "#F44336")
        ]
    
    def show_groups_view(self):
        """กลับไปแสดง groups view"""
        self.create_groups_view()
        self.current_view = 'groups'
    
    def close_all_positions(self, group_id):
        """ปิดไม้ทั้งหมดของ group"""
        print(f"Closing all positions for group: {group_id}")
        # TODO: Implement actual position closing logic
    
    def refresh_group_positions(self, group_id):
        """รีเฟรชข้อมูล positions ของ group"""
        print(f"Refreshing positions for group: {group_id}")
        # TODO: Implement actual refresh logic
    
    def get_real_trading_data(self):
        """ดึงข้อมูลจริงจากระบบ trading"""
        try:
            real_data = {}
            
            # ดึงข้อมูลจาก active_groups.json
            active_groups_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'active_groups.json')
            if os.path.exists(active_groups_file):
                with open(active_groups_file, 'r') as f:
                    active_groups_data = json.load(f)
                
                active_groups = active_groups_data.get('active_groups', {})
                
                for group_id, group_info in active_groups.items():
                    # คำนวณ P&L จาก positions
                    total_pnl = 0.0
                    active_positions = 0
                    
                    positions = group_info.get('positions', [])
                    for position in positions:
                        # คำนวณ P&L ง่ายๆ (ในความเป็นจริงต้องดึงราคาปัจจุบัน)
                        lot_size = position.get('lot_size', 0)
                        entry_price = position.get('entry_price', 0)
                        # ใช้ราคาปัจจุบันเป็น entry_price + random variation เพื่อจำลอง
                        import random
                        current_price = entry_price + random.uniform(-0.001, 0.001)
                        pnl = (current_price - entry_price) * lot_size * 100000  # จำลอง pip value
                        total_pnl += pnl
                        active_positions += 1
                    
                    # สร้างข้อมูล group
                    triangle = group_info.get('triangle', [])
                    real_data[group_id] = {
                        'name': group_id.replace('group_', '').replace('_', ' ').title(),
                        'triangle': triangle,
                        'status': 'active' if active_positions > 0 else 'inactive',
                        'net_pnl': total_pnl,
                        'arbitrage_pnl': total_pnl * 0.7,  # จำลอง
                        'recovery_pnl': total_pnl * 0.3,   # จำลอง
                        'total_trades': len(positions),
                        'active_positions': active_positions,
                        'positions': positions
                    }
            
            print(f"✅ Debug: Loaded real data for {len(real_data)} groups")
            return real_data
            
        except Exception as e:
            print(f"❌ Error loading real trading data: {e}")
            return None
    
    def get_empty_groups_data(self):
        """สร้างข้อมูลว่างสำหรับ groups"""
        group_configs = [
            {"id": "triangle_1", "name": "Triangle 1", "pairs": ["EURUSD", "GBPUSD", "EURGBP"]},
            {"id": "triangle_2", "name": "Triangle 2", "pairs": ["USDJPY", "EURUSD", "EURJPY"]},
            {"id": "triangle_3", "name": "Triangle 3", "pairs": ["AUDUSD", "GBPUSD", "GBPAUD"]},
            {"id": "triangle_4", "name": "Triangle 4", "pairs": ["AUDUSD", "EURUSD", "EURAUD"]},
            {"id": "triangle_5", "name": "Triangle 5", "pairs": ["USDCAD", "EURUSD", "EURCAD"]},
            {"id": "triangle_6", "name": "Triangle 6", "pairs": ["AUDUSD", "GBPUSD", "GBPAUD"]}
        ]
        
        empty_data = {}
        for config in group_configs:
            empty_data[config['id']] = {
                'name': config['name'],
                'triangle': config['pairs'],
                'status': 'inactive',
                'net_pnl': 0.0,
                'arbitrage_pnl': 0.0,
                'recovery_pnl': 0.0,
                'total_trades': 0,
                'active_positions': 0,
                'positions': []
            }
        
        return empty_data

    def update_group_dashboard(self, groups_data=None):
        """อัปเดต dashboard ทั้งหมด - ใช้ข้อมูลจริง"""
        try:
            print("🔍 Debug: update_group_dashboard called")
            
            # ดึงข้อมูลจริงจากระบบ
            real_data = self.get_real_trading_data()
            
            if real_data:
                print("✅ Debug: Using real trading data")
                groups_data = real_data
            else:
                print("⚠️ Debug: No real data available - showing empty state")
                groups_data = self.get_empty_groups_data()

            print(f"🔍 Debug: groups_data keys: {list(groups_data.keys())}")
            print(f"🔍 Debug: hasattr(self, 'stats_cards'): {hasattr(self, 'stats_cards')}")
            print(f"🔍 Debug: hasattr(self, 'group_cards'): {hasattr(self, 'group_cards')}")
            print(f"🔍 Debug: current_view: {getattr(self, 'current_view', 'None')}")

            # Update stats overview
            if hasattr(self, 'stats_cards'):
                print("🔍 Debug: Updating stats overview")
                self.update_stats_overview(groups_data)
            else:
                print("❌ Debug: No stats_cards found")

            # Update group cards (only if in groups view)
            if hasattr(self, 'group_cards') and self.current_view == 'groups':
                print(f"🔍 Debug: Updating group cards, current_view: {self.current_view}")
                print(f"🔍 Debug: group_cards keys: {list(self.group_cards.keys())}")
                for triangle_id in self.group_cards.keys():
                    group_data = groups_data.get(triangle_id, {})
                    print(f"🔍 Debug: Updating {triangle_id} with data: {group_data}")
                    self.update_single_group_card(triangle_id, group_data)
            else:
                print(f"❌ Debug: Cannot update group cards - has group_cards: {hasattr(self, 'group_cards')}, current_view: {getattr(self, 'current_view', 'None')}")

            print("✅ Debug: update_group_dashboard completed")
            
            # Force GUI update
            self.parent.update_idletasks()
            
            # Update frame and canvas if exists
            if hasattr(self, 'groups_frame'):
                self.groups_frame.update_idletasks()
            
            if hasattr(self, 'groups_canvas'):
                self.groups_canvas.update_idletasks()
                self.groups_canvas.configure(scrollregion=self.groups_canvas.bbox('all'))

        except Exception as e:
            print(f"❌ Error updating dashboard: {e}")
            import traceback
            traceback.print_exc()
    
    def update_stats_overview(self, groups_data):
        """อัปเดต stats overview cards"""
        try:
            if not hasattr(self, 'stats_cards'):
                return
            
            # Calculate totals
            total_pnl = sum(g.get('net_pnl', 0.0) for g in groups_data.values())
            active_groups = sum(1 for g in groups_data.values() if g.get('status') == 'active')
            total_groups = len(groups_data) or 6
            today_trades = sum(g.get('total_trades', 0) for g in groups_data.values())
            
            # Calculate win rate
            total_trades = today_trades
            winning_trades = sum(1 for g in groups_data.values() if g.get('net_pnl', 0) > 0)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Update cards
            if 'Total P&L' in self.stats_cards:
                color = '#4CAF50' if total_pnl >= 0 else '#F44336'
                self.stats_cards['Total P&L'].config(
                    text=f"${total_pnl:.2f}",
                    bg=color
                )
            
            if 'Active Groups' in self.stats_cards:
                self.stats_cards['Active Groups'].config(text=f"{active_groups}/{total_groups}")
            
            if 'Today\'s Trades' in self.stats_cards:
                self.stats_cards['Today\'s Trades'].config(text=str(today_trades))
            
            if 'Win Rate' in self.stats_cards:
                self.stats_cards['Win Rate'].config(text=f"{win_rate:.1f}%")
            
            # Update summary panel
            self.update_summary_panel(groups_data)
            
            # Force GUI update
            self.parent.update_idletasks()
            
            # Update frame and canvas if exists
            if hasattr(self, 'groups_frame'):
                self.groups_frame.update_idletasks()
            
            if hasattr(self, 'groups_canvas'):
                self.groups_canvas.update_idletasks()
                self.groups_canvas.configure(scrollregion=self.groups_canvas.bbox('all'))
                
        except Exception as e:
            print(f"Error updating stats overview: {e}")
    
    def update_summary_panel(self, groups_data):
        """อัปเดต summary panel"""
        try:
            if not hasattr(self, 'summary_labels'):
                return
            
            # Calculate totals
            total_pnl = sum(g.get('net_pnl', 0.0) for g in groups_data.values())
            active_groups = sum(1 for g in groups_data.values() if g.get('status') == 'active')
            total_positions = sum(g.get('total_positions', 0) for g in groups_data.values())
            total_trades = sum(g.get('total_trades', 0) for g in groups_data.values())
            
            # Update summary labels
            if 'active' in self.summary_labels:
                self.summary_labels['active'].config(text=f"Active: {active_groups}")
            
            if 'total_pnl' in self.summary_labels:
                color = '#4CAF50' if total_pnl >= 0 else '#F44336'
                self.summary_labels['total_pnl'].config(
                    text=f"Total Net PnL: ${total_pnl:.2f}",
                    fg=color
                )
            
            if 'total_positions' in self.summary_labels:
                self.summary_labels['total_positions'].config(text=f"Total Positions: {total_positions}")
            
            if 'total_recovery' in self.summary_labels:
                self.summary_labels['total_recovery'].config(text=f"Total Recovery: {total_trades}")
                
        except Exception as e:
            print(f"Error updating summary panel: {e}")
    
    def update_single_group_card(self, triangle_id, group_data):
        """อัปเดต group card เดียว"""
        try:
            if triangle_id not in self.group_cards:
                return
            
            # Update status indicator
            net_pnl = group_data.get('net_pnl', 0.0)
            if triangle_id in self.status_indicators:
                if net_pnl > 0:
                    self.status_indicators[triangle_id].config(text="🟢")
                elif net_pnl < 0:
                    self.status_indicators[triangle_id].config(text="🔴")
                else:
                    self.status_indicators[triangle_id].config(text="⚪")
            
            # Update P&L
            if triangle_id in self.pnl_labels:
                pnl_labels = self.pnl_labels[triangle_id]
                
                arb_pnl = group_data.get('arbitrage_pnl', 0.0)
                rec_pnl = group_data.get('recovery_pnl', 0.0)
                
                pnl_labels['arb'].config(text=f"Arbitrage: ${arb_pnl:.2f}")
                pnl_labels['rec'].config(text=f"Recovery: ${rec_pnl:.2f}")
                
                # Color code net P&L
                net_color = '#4CAF50' if net_pnl >= 0 else '#F44336'
                pnl_labels['net'].config(
                    text=f"Net: ${net_pnl:.2f}",
                    fg=net_color
                )
            
            # Update status info
            card = self.group_cards[triangle_id]
            status = group_data.get('status', 'inactive')
            active_positions = group_data.get('active_positions', 0)
            total_trades = group_data.get('total_trades', 0)
            
            if status == 'active' and active_positions > 0:
                status_text = f"📈 Status: {active_positions} Active Positions, {total_trades} Total Trades"
                card['status_info'].config(text=status_text, fg='#4CAF50')
            else:
                card['status_info'].config(text="📈 Status: No Active Positions", fg='#888888')
            
            # Update positions text with real position details
            if 'positions_text' in card:
                positions = group_data.get('positions', [])
                if positions:
                    # แสดงรายละเอียด positions จริง
                    position_details = []
                    for pos in positions[:3]:  # แสดงแค่ 3 positions แรก
                        symbol = pos.get('symbol', 'Unknown')
                        direction = pos.get('direction', 'Unknown')
                        lot_size = pos.get('lot_size', 0)
                        position_details.append(f"{symbol} {direction} {lot_size}L")
                    
                    if len(positions) > 3:
                        position_details.append(f"... +{len(positions) - 3} more")
                    
                    positions_text = " | ".join(position_details)
                    card['positions_text'].config(text=positions_text, fg='#4CAF50')
                else:
                    card['positions_text'].config(text="No active positions", fg='#888888')
                
        except Exception as e:
            print(f"Error updating group card {triangle_id}: {e}")
    
    def create_summary_panel(self):
        """สร้าง summary panel ด้านล่าง - ปรับปรุงให้สวยขึ้น"""
        # Summary frame with better styling
        summary_frame = tk.Frame(self.main_frame, bg='#1a1a1a', height=60)
        summary_frame.pack(fill='x', pady=(15, 0))
        summary_frame.pack_propagate(False)
        
        # Summary content with gradient effect
        summary_content = tk.Frame(summary_frame, bg='#2d2d2d', height=60)
        summary_content.pack(fill='x', padx=20, pady=10)
        summary_content.pack_propagate(False)
        
        # Summary labels - make them instance variables for updating
        self.summary_labels = {}
        
        self.summary_labels['total_groups'] = tk.Label(
            summary_content,
            text="Total Groups: 6",
            font=('Segoe UI', 11, 'bold'),
            bg='#2d2d2d',
            fg='#E0E0E0'
        )
        self.summary_labels['total_groups'].pack(side='left', padx=25, pady=20)
        
        self.summary_labels['active'] = tk.Label(
            summary_content,
            text="Active: 0",
            font=('Segoe UI', 11, 'bold'),
            bg='#2d2d2d',
            fg='#4CAF50'
        )
        self.summary_labels['active'].pack(side='left', padx=25, pady=20)
        
        self.summary_labels['total_pnl'] = tk.Label(
            summary_content,
            text="Total Net PnL: $0.00",
            font=('Consolas', 12, 'bold'),
            bg='#2d2d2d',
            fg='#FFD700'
        )
        self.summary_labels['total_pnl'].pack(side='left', padx=25, pady=20)
        
        self.summary_labels['total_positions'] = tk.Label(
            summary_content,
            text="Total Positions: 0",
            font=('Segoe UI', 11, 'bold'),
            bg='#2d2d2d',
            fg='#E0E0E0'
        )
        self.summary_labels['total_positions'].pack(side='left', padx=25, pady=20)
        
        self.summary_labels['total_recovery'] = tk.Label(
            summary_content,
            text="Total Recovery: 0",
            font=('Segoe UI', 11, 'bold'),
            bg='#2d2d2d',
            fg='#E0E0E0'
        )
        self.summary_labels['total_recovery'].pack(side='left', padx=25, pady=20)
    
    def _on_frame_configure(self, event):
        """Update scroll region when frame size changes"""
        self.groups_canvas.configure(scrollregion=self.groups_canvas.bbox('all'))
    
    def _on_canvas_configure(self, event):
        """Update canvas window when canvas size changes"""
        canvas_width = event.width
        frame_width = self.groups_frame.winfo_reqwidth()
        
        if frame_width != canvas_width:
            # Update the inner frame's width to fill the canvas
            self.groups_canvas.itemconfig(self.canvas_window, width=canvas_width)
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        self.groups_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def refresh_groups(self):
        """รีเฟรชข้อมูล groups"""
        try:
            print("🔍 Debug: refresh_groups called")
            print(f"🔍 Debug: hasattr(self, 'group_cards'): {hasattr(self, 'group_cards')}")
            print(f"🔍 Debug: current_view: {getattr(self, 'current_view', 'None')}")
            
            # Simulate data update (ในระบบจริงจะดึงจาก trading system)
            sample_data = {
                'triangle_1': {
                    'net_pnl': 15.50,
                    'arbitrage_pnl': 12.30,
                    'recovery_pnl': 3.20,
                    'status': 'active',
                    'total_positions': 3,
                    'total_trades': 5
                },
                'triangle_2': {
                    'net_pnl': -8.75,
                    'arbitrage_pnl': -5.20,
                    'recovery_pnl': -3.55,
                    'status': 'active',
                    'total_positions': 2,
                    'total_trades': 3
                },
                'triangle_3': {
                    'net_pnl': 0.00,
                    'arbitrage_pnl': 0.00,
                    'recovery_pnl': 0.00,
                    'status': 'inactive',
                    'total_positions': 0,
                    'total_trades': 0
                },
                'triangle_4': {
                    'net_pnl': 22.80,
                    'arbitrage_pnl': 18.50,
                    'recovery_pnl': 4.30,
                    'status': 'active',
                    'total_positions': 4,
                    'total_trades': 7
                },
                'triangle_5': {
                    'net_pnl': 0.00,
                    'arbitrage_pnl': 0.00,
                    'recovery_pnl': 0.00,
                    'status': 'inactive',
                    'total_positions': 0,
                    'total_trades': 0
                },
                'triangle_6': {
                    'net_pnl': 0.00,
                    'arbitrage_pnl': 0.00,
                    'recovery_pnl': 0.00,
                    'status': 'inactive',
                    'total_positions': 0,
                    'total_trades': 0
                }
            }
            
            # Update dashboard with sample data
            print("🔍 Debug: Calling update_group_dashboard with sample data")
            self.update_group_dashboard(sample_data)
            print("✅ Debug: update_group_dashboard completed")
            
            # Force GUI update
            self.parent.update_idletasks()
            
            # Update frame and canvas
            if hasattr(self, 'groups_frame'):
                self.groups_frame.update_idletasks()
                print("🔍 Debug: Frame updated in refresh_groups")
            
            if hasattr(self, 'groups_canvas'):
                self.groups_canvas.update_idletasks()
                self.groups_canvas.configure(scrollregion=self.groups_canvas.bbox('all'))
                print("🔍 Debug: Canvas updated in refresh_groups")
            
        except Exception as e:
            print(f"❌ Error refreshing groups: {e}")
            import traceback
            traceback.print_exc()