"""
Group Dashboard - แสดงสถานะของแต่ละ Group (2 Columns Grid + Horizontal Scroll)
========================================================================================

Dashboard ที่แสดงสถานะของแต่ละ arbitrage group แยกตาม triangle
พร้อม P&L Breakdown, Trailing Stop Status, และ Min Profit Target
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, Canvas
from datetime import datetime
from .theme import TradingTheme

class GroupDashboard:
    def __init__(self, parent):
        self.parent = parent
        self.groups = {}
        self.setup_ui()
    
    def setup_ui(self):
        """สร้าง UI สำหรับ Group Dashboard - ปรับปรุงใหม่"""
        # Main container
        self.main_frame = tk.Frame(self.parent, bg='#1a1a1a')
        self.main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Header
        self.create_header()
        
        # Stats Overview Cards
        self.create_stats_overview()
        
        # Groups grid - ปรับปรุงใหม่
        self.create_modern_groups_grid()
        
        # Summary panel
        self.create_summary_panel()
    
    def create_header(self):
        """สร้าง header - ปรับปรุงใหม่"""
        header_frame = tk.Frame(self.main_frame, bg='#2d2d2d', height=60)
        header_frame.pack(fill='x', pady=(0, 15))
        header_frame.pack_propagate(False)
        
        # Title
        title_label = tk.Label(
            header_frame,
            text="📊 Trading Dashboard",
            font=('Arial', 18, 'bold'),
            bg='#2d2d2d',
            fg='#FFD700'
        )
        title_label.pack(side='left', padx=20, pady=15)
        
        # Right side controls
        controls_frame = tk.Frame(header_frame, bg='#2d2d2d')
        controls_frame.pack(side='right', padx=20, pady=15)
        
        # Refresh button
        refresh_btn = tk.Button(
            controls_frame,
            text="🔄 Refresh",
            command=self.refresh_groups,
            bg='#4CAF50',
            fg='white',
            font=('Arial', 10, 'bold'),
            padx=15,
            pady=8,
            relief='flat',
            cursor='hand2'
        )
        refresh_btn.pack(side='right', padx=5)
        
        # Auto-refresh toggle
        self.auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_btn = tk.Checkbutton(
            controls_frame,
            text="Auto Refresh",
            variable=self.auto_refresh_var,
            bg='#2d2d2d',
            fg='white',
            font=('Arial', 10),
            selectcolor='#4CAF50',
            activebackground='#2d2d2d'
        )
        auto_refresh_btn.pack(side='right', padx=10)
    
    def create_stats_overview(self):
        """สร้าง stats overview cards - ใหม่"""
        stats_frame = tk.Frame(self.main_frame, bg='#1a1a1a')
        stats_frame.pack(fill='x', pady=(0, 15))
        
        # Stats cards
        stats_data = [
            {"title": "Total P&L", "value": "$0.00", "color": "#4CAF50", "icon": "💰"},
            {"title": "Active Groups", "value": "0/6", "color": "#2196F3", "icon": "🔺"},
            {"title": "Today's Trades", "value": "0", "color": "#FF9800", "icon": "📈"},
            {"title": "Win Rate", "value": "0%", "color": "#9C27B0", "icon": "🎯"}
        ]
        
        self.stats_cards = {}
        for i, stat in enumerate(stats_data):
            card = tk.Frame(
                stats_frame,
                bg=stat['color'],
                relief='raised',
                bd=2,
                width=200,
                height=80
            )
            card.pack(side='left', padx=10, fill='y')
            card.pack_propagate(False)
            
            # Icon and title
            header_frame = tk.Frame(card, bg=stat['color'])
            header_frame.pack(fill='x', padx=10, pady=5)
            
            icon_label = tk.Label(
                header_frame,
                text=stat['icon'],
                font=('Arial', 14),
                bg=stat['color'],
                fg='white'
            )
            icon_label.pack(side='left')
            
            title_label = tk.Label(
                header_frame,
                text=stat['title'],
                font=('Arial', 10, 'bold'),
                bg=stat['color'],
                fg='white'
            )
            title_label.pack(side='right')
            
            # Value
            value_label = tk.Label(
                card,
                text=stat['value'],
                font=('Arial', 16, 'bold'),
                bg=stat['color'],
                fg='white'
            )
            value_label.pack(expand=True)
            
            self.stats_cards[stat['title']] = value_label
    
    def create_modern_groups_grid(self):
        """สร้าง groups grid แบบใหม่ - สวยและใช้งานง่าย"""
        # Main container
        container_frame = tk.Frame(self.main_frame, bg='#1a1a1a')
        container_frame.pack(fill='both', expand=True)
        
        # Create canvas for scrolling
        self.canvas = tk.Canvas(
            container_frame,
            bg='#1a1a1a',
            highlightthickness=0
        )
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(container_frame, orient='vertical', command=self.canvas.yview)
        scrollbar.pack(side='right', fill='y')
        
        self.canvas.pack(side='left', fill='both', expand=True)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Groups container
        self.groups_container = tk.Frame(self.canvas, bg='#1a1a1a')
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.groups_container, anchor='nw')
        
        # Bind events
        self.groups_container.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind_all('<MouseWheel>', lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        # Create group cards
        self.create_group_cards()
    
    def create_group_cards(self):
        """สร้าง group cards แบบใหม่ - สวยและใช้งานง่าย"""
        # Group configurations
        group_configs = [
            {
                'id': 'triangle_1',
                'name': 'Triangle 1',
                'pairs': ['EURUSD', 'GBPUSD', 'EURGBP'],
                'magic': 234001,
                'color': '#FF6B6B'
            },
            {
                'id': 'triangle_2',
                'name': 'Triangle 2',
                'pairs': ['USDJPY', 'EURUSD', 'EURJPY'],
                'magic': 234002,
                'color': '#4ECDC4'
            },
            {
                'id': 'triangle_3',
                'name': 'Triangle 3',
                'pairs': ['GBPUSD', 'USDJPY', 'GBPJPY'],
                'magic': 234003,
                'color': '#45B7D1'
            },
            {
                'id': 'triangle_4',
                'name': 'Triangle 4',
                'pairs': ['AUDUSD', 'USDCAD', 'AUDCAD'],
                'magic': 234004,
                'color': '#96CEB4'
            },
            {
                'id': 'triangle_5',
                'name': 'Triangle 5',
                'pairs': ['NZDUSD', 'USDCHF', 'NZDCHF'],
                'magic': 234005,
                'color': '#FFEAA7'
            },
            {
                'id': 'triangle_6',
                'name': 'Triangle 6',
                'pairs': ['EURCHF', 'USDCHF', 'EURUSD'],
                'magic': 234006,
                'color': '#DDA0DD'
            }
        ]
        
        self.group_cards = {}
        self.status_indicators = {}
        self.pnl_labels = {}
        
        # Create cards in 2 columns
        for i, config in enumerate(group_configs):
            row = i // 2
            col = i % 2
            
            self.create_single_group_card(config, row, col)
    
    def create_single_group_card(self, config, row, col):
        """สร้าง group card เดียว - ใหม่"""
        # Main card frame
        card_frame = tk.Frame(
            self.groups_container,
            bg='#2d2d2d',
            relief='raised',
            bd=2,
            width=350,
            height=280
        )
        card_frame.grid(row=row, column=col, padx=15, pady=10, sticky='nsew')
        card_frame.grid_propagate(False)
        
        # Configure grid weights
        self.groups_container.grid_rowconfigure(row, weight=1)
        self.groups_container.grid_columnconfigure(col, weight=1)
        
        # Header
        header_frame = tk.Frame(card_frame, bg=config['color'], height=50)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        # Group name and magic
        name_label = tk.Label(
            header_frame,
            text=f"{config['name']} (Magic: {config['magic']})",
            font=('Arial', 12, 'bold'),
            bg=config['color'],
            fg='white'
        )
        name_label.pack(side='left', padx=15, pady=10)
        
        # Status indicator
        status_indicator = tk.Label(
            header_frame,
            text="🔴",
            font=('Arial', 16),
            bg=config['color'],
            fg='white'
        )
        status_indicator.pack(side='right', padx=15, pady=10)
        self.status_indicators[config['id']] = status_indicator
        
        # Content area
        content_frame = tk.Frame(card_frame, bg='#2d2d2d')
        content_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Pairs info
        pairs_frame = tk.Frame(content_frame, bg='#2d2d2d')
        pairs_frame.pack(fill='x', pady=(0, 10))
        
        pairs_label = tk.Label(
            pairs_frame,
            text="📊 Pairs:",
            font=('Arial', 10, 'bold'),
            bg='#2d2d2d',
            fg='#FFD700'
        )
        pairs_label.pack(anchor='w')
        
        pairs_text = tk.Label(
            pairs_frame,
            text=f"{' • '.join(config['pairs'])}",
            font=('Arial', 10),
            bg='#2d2d2d',
            fg='white'
        )
        pairs_text.pack(anchor='w')
        
        # P&L Section
        pnl_frame = tk.Frame(content_frame, bg='#2d2d2d')
        pnl_frame.pack(fill='x', pady=(0, 10))
        
        pnl_title = tk.Label(
            pnl_frame,
            text="💰 P&L:",
            font=('Arial', 10, 'bold'),
            bg='#2d2d2d',
            fg='#FFD700'
        )
        pnl_title.pack(anchor='w')
        
        # P&L values
        pnl_values = {
            'arb': tk.Label(pnl_frame, text="Arbitrage: $0.00", font=('Arial', 9), bg='#2d2d2d', fg='white'),
            'rec': tk.Label(pnl_frame, text="Recovery: $0.00", font=('Arial', 9), bg='#2d2d2d', fg='white'),
            'net': tk.Label(pnl_frame, text="Net: $0.00", font=('Arial', 9, 'bold'), bg='#2d2d2d', fg='#4CAF50')
        }
        
        for label in pnl_values.values():
            label.pack(anchor='w')
        
        if not hasattr(self, 'pnl_labels'):
            self.pnl_labels = {}
        self.pnl_labels[config['id']] = pnl_values
        
        # Status section
        status_frame = tk.Frame(content_frame, bg='#2d2d2d')
        status_frame.pack(fill='x')
        
        status_title = tk.Label(
            status_frame,
            text="📈 Status:",
            font=('Arial', 10, 'bold'),
            bg='#2d2d2d',
            fg='#FFD700'
        )
        status_title.pack(anchor='w')
        
        status_info = tk.Label(
            status_frame,
            text="No Active Positions",
            font=('Arial', 9),
            bg='#2d2d2d',
            fg='#888888'
        )
        status_info.pack(anchor='w')
        
        self.group_cards[config['id']] = {
            'frame': card_frame,
            'status_info': status_info,
            'config': config
        }
    
    def update_group_dashboard(self, groups_data=None):
        """อัปเดต dashboard ทั้งหมด - ใหม่"""
        try:
            if groups_data is None:
                groups_data = {}
            
            # Update stats overview
            self.update_stats_overview(groups_data)
            
            # Update group cards
            for triangle_id in self.group_cards.keys():
                group_data = groups_data.get(triangle_id, {})
                self.update_single_group_card(triangle_id, group_data)
                
        except Exception as e:
            print(f"Error updating dashboard: {e}")
    
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
                
        except Exception as e:
            print(f"Error updating stats overview: {e}")
    
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
            positions = group_data.get('total_positions', 0)
            
            if status == 'active':
                status_text = f"Active - {positions} positions"
                card['status_info'].config(text=status_text, fg='#4CAF50')
            else:
                card['status_info'].config(text="No Active Positions", fg='#888888')
                
        except Exception as e:
            print(f"Error updating group card {triangle_id}: {e}")
    
    def refresh_groups(self):
        """รีเฟรชข้อมูล groups"""
        try:
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
            self.update_group_dashboard(sample_data)
            
        except Exception as e:
            print(f"Error refreshing groups: {e}")
    
    def create_groups_grid_horizontal(self):
        """สร้าง grid แบบ vertical scroll (3 columns × 2 rows = 6 groups)"""
        # Main container with vertical scrollbar
        container_frame = tk.Frame(self.main_frame, bg=TradingTheme.COLORS['secondary_bg'])
        container_frame.pack(fill='both', expand=True, padx=TradingTheme.SPACING['md'], pady=TradingTheme.SPACING['md'])
        
        # Create canvas for scrolling
        self.canvas = Canvas(
            container_frame,
            bg=TradingTheme.COLORS['secondary_bg'],
            highlightthickness=0
        )
        
        # Vertical scrollbar (เลื่อนขึ้นลง)
        v_scrollbar = ttk.Scrollbar(container_frame, orient='vertical', command=self.canvas.yview)
        v_scrollbar.pack(side='right', fill='y')
        
        self.canvas.pack(side='left', fill='both', expand=True)
        self.canvas.configure(yscrollcommand=v_scrollbar.set)
        
        # Create frame inside canvas
        self.groups_container = tk.Frame(self.canvas, bg=TradingTheme.COLORS['secondary_bg'])
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.groups_container, anchor='nw')
        
        # Bind canvas resize
        self.groups_container.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        
        # Bind mouse wheel for scrolling
        self.canvas.bind_all('<MouseWheel>', lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        # Triangle configurations
        self.triangle_configs = {
            'triangle_1': {
                'name': 'Triangle 1',
                'pairs': ['EURUSD', 'GBPUSD', 'EURGBP'],
                'magic': 234001,
                'color': '#FF6B6B'
            },
            'triangle_2': {
                'name': 'Triangle 2', 
                'pairs': ['USDJPY', 'EURUSD', 'EURJPY'],
                'magic': 234002,
                'color': '#4ECDC4'
            },
            'triangle_3': {
                'name': 'Triangle 3',
                'pairs': ['USDJPY', 'GBPUSD', 'GBPJPY'],
                'magic': 234003,
                'color': '#45B7D1'
            },
            'triangle_4': {
                'name': 'Triangle 4',
                'pairs': ['AUDUSD', 'EURUSD', 'EURAUD'],
                'magic': 234004,
                'color': '#96CEB4'
            },
            'triangle_5': {
                'name': 'Triangle 5',
                'pairs': ['USDCAD', 'EURUSD', 'EURCAD'],
                'magic': 234005,
                'color': '#FFEAA7'
            },
            'triangle_6': {
                'name': 'Triangle 6',
                'pairs': ['AUDUSD', 'GBPUSD', 'GBPAUD'],
                'magic': 234006,
                'color': '#DDA0DD'
            }
        }
        
        # Create group cards in 2×3 grid (2 rows, 3 columns) - Horizontal layout
        self.group_cards = {}
        for i, (triangle_id, config) in enumerate(self.triangle_configs.items()):
            # Calculate position: แนวนอนก่อน (row-first)
            # i=0→G1: col=0,row=0 | i=1→G2: col=1,row=0 | i=2→G3: col=2,row=0
            # i=3→G4: col=0,row=1 | i=4→G5: col=1,row=1 | i=5→G6: col=2,row=1
            col = i % 3   # 0,1,2,0,1,2 (horizontal first)
            row = i // 3  # 0,0,0,1,1,1 (then go to next row)
            
            card = self.create_enhanced_group_card(triangle_id, config)
            card.grid(row=row, column=col, padx=TradingTheme.SPACING['md'], 
                     pady=TradingTheme.SPACING['md'], sticky='nsew')
            
            self.group_cards[triangle_id] = card
        
        # Configure grid weights
        for i in range(2):  # 2 rows
            self.groups_container.grid_rowconfigure(i, weight=0)
        for i in range(3):  # 3 columns
            self.groups_container.grid_columnconfigure(i, weight=1, minsize=380)
    
    def create_enhanced_group_card(self, triangle_id, config):
        """สร้าง enhanced card พร้อม P&L Breakdown, Progress Bar, Trailing Stop"""
        # Main card frame
        card_frame = tk.Frame(
            self.groups_container,
            bg=TradingTheme.COLORS['primary_bg'],
            relief='raised',
            bd=2,
            width=380,
            height=400
        )
        card_frame.grid_propagate(False)
        
        # Header
        header_frame = tk.Frame(card_frame, bg=config['color'], height=40)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        # Group name
        name_label = tk.Label(
            header_frame,
            text=f"{config['name']} (G{triangle_id.split('_')[1]})",
            font=('Arial', 11, 'bold'),
            bg=config['color'],
            fg='white'
        )
        name_label.pack(side='left', padx=TradingTheme.SPACING['md'], pady=TradingTheme.SPACING['sm'])
        
        # Status indicator
        if not hasattr(self, 'status_indicators'):
            self.status_indicators = {}
        
        status_indicator = tk.Label(
            header_frame,
            text="🔴",
            font=('Arial', 14),
            bg=config['color']
        )
        status_indicator.pack(side='right', padx=TradingTheme.SPACING['md'])
        self.status_indicators[triangle_id] = status_indicator
        
        # Content area (scrollable)
        content_frame = tk.Frame(card_frame, bg=TradingTheme.COLORS['primary_bg'])
        content_frame.pack(fill='both', expand=True, padx=TradingTheme.SPACING['md'], pady=TradingTheme.SPACING['md'])
        
        # Magic & Pairs
        info_text = f"Magic: {config['magic']}\n{', '.join(config['pairs'])}"
        info_label = tk.Label(
            content_frame,
            text=info_text,
            font=('Arial', 9),
            bg=TradingTheme.COLORS['primary_bg'],
            fg=TradingTheme.COLORS['text_secondary'],
            justify='left'
        )
        info_label.pack(anchor='w', pady=(0, TradingTheme.SPACING['sm']))
        
        # Separator
        ttk.Separator(content_frame, orient='horizontal').pack(fill='x', pady=TradingTheme.SPACING['sm'])
        
        # 💰 P&L Breakdown Section
        pnl_frame = tk.Frame(content_frame, bg=TradingTheme.COLORS['primary_bg'])
        pnl_frame.pack(fill='x', pady=TradingTheme.SPACING['sm'])
        
        pnl_title = tk.Label(
            pnl_frame,
            text="💰 P&L Breakdown:",
            font=('Arial', 10, 'bold'),
            bg=TradingTheme.COLORS['primary_bg'],
            fg=TradingTheme.COLORS['text_primary']
        )
        pnl_title.pack(anchor='w')
        
        # Initialize labels
        if not hasattr(self, 'arb_pnl_labels'):
            self.arb_pnl_labels = {}
        if not hasattr(self, 'rec_pnl_labels'):
            self.rec_pnl_labels = {}
        if not hasattr(self, 'net_pnl_labels'):
            self.net_pnl_labels = {}
        
        # Arbitrage PnL
        arb_pnl_label = tk.Label(
            pnl_frame,
            text="  Arb (0): $0.00",
            font=('Consolas', 9),
            bg=TradingTheme.COLORS['primary_bg'],
            fg=TradingTheme.COLORS['text_primary']
        )
        arb_pnl_label.pack(anchor='w')
        self.arb_pnl_labels[triangle_id] = arb_pnl_label
        
        # Recovery PnL
        rec_pnl_label = tk.Label(
            pnl_frame,
            text="  Rec (0): $0.00",
            font=('Consolas', 9),
            bg=TradingTheme.COLORS['primary_bg'],
            fg=TradingTheme.COLORS['text_primary']
        )
        rec_pnl_label.pack(anchor='w')
        self.rec_pnl_labels[triangle_id] = rec_pnl_label
        
        # Net PnL
        net_pnl_label = tk.Label(
            pnl_frame,
            text="  Net: $0.00",
            font=('Consolas', 10, 'bold'),
            bg=TradingTheme.COLORS['primary_bg'],
            fg=TradingTheme.COLORS['text_primary']
        )
        net_pnl_label.pack(anchor='w', pady=(2, 0))
        self.net_pnl_labels[triangle_id] = net_pnl_label
        
        # Separator
        ttk.Separator(content_frame, orient='horizontal').pack(fill='x', pady=TradingTheme.SPACING['sm'])
        
        # 🎯 Profit Target Section
        target_frame = tk.Frame(content_frame, bg=TradingTheme.COLORS['primary_bg'])
        target_frame.pack(fill='x', pady=TradingTheme.SPACING['sm'])
        
        if not hasattr(self, 'target_labels'):
            self.target_labels = {}
        if not hasattr(self, 'progress_bars'):
            self.progress_bars = {}
        if not hasattr(self, 'progress_labels'):
            self.progress_labels = {}
        
        target_label = tk.Label(
            target_frame,
            text="🎯 Target: $5.00",
            font=('Arial', 9, 'bold'),
            bg=TradingTheme.COLORS['primary_bg'],
            fg=TradingTheme.COLORS['text_primary']
        )
        target_label.pack(anchor='w')
        self.target_labels[triangle_id] = target_label
        
        # Progress bar frame
        progress_frame = tk.Frame(target_frame, bg=TradingTheme.COLORS['secondary_bg'], height=20)
        progress_frame.pack(fill='x', pady=(2, 2))
        
        # Progress bar canvas
        progress_canvas = Canvas(
            progress_frame,
            bg=TradingTheme.COLORS['secondary_bg'],
            height=18,
            highlightthickness=0
        )
        progress_canvas.pack(fill='x')
        self.progress_bars[triangle_id] = progress_canvas
        
        # Progress text
        progress_label = tk.Label(
            target_frame,
            text="0% (Need $5.00)",
            font=('Arial', 8),
            bg=TradingTheme.COLORS['primary_bg'],
            fg=TradingTheme.COLORS['text_secondary']
        )
        progress_label.pack(anchor='w')
        self.progress_labels[triangle_id] = progress_label
        
        # Separator
        ttk.Separator(content_frame, orient='horizontal').pack(fill='x', pady=TradingTheme.SPACING['sm'])
        
        # 🔒 Trailing Stop Section
        trailing_frame = tk.Frame(content_frame, bg=TradingTheme.COLORS['primary_bg'])
        trailing_frame.pack(fill='x', pady=TradingTheme.SPACING['sm'])
        
        if not hasattr(self, 'trailing_status_labels'):
            self.trailing_status_labels = {}
        if not hasattr(self, 'trailing_detail_labels'):
            self.trailing_detail_labels = {}
        
        trailing_status = tk.Label(
            trailing_frame,
            text="🔓 Trailing: Inactive",
            font=('Arial', 9, 'bold'),
            bg=TradingTheme.COLORS['primary_bg'],
            fg=TradingTheme.COLORS['text_secondary']
        )
        trailing_status.pack(anchor='w')
        self.trailing_status_labels[triangle_id] = trailing_status
        
        trailing_detail = tk.Label(
            trailing_frame,
            text="(Waiting for profit)",
            font=('Arial', 8),
            bg=TradingTheme.COLORS['primary_bg'],
            fg=TradingTheme.COLORS['text_secondary']
        )
        trailing_detail.pack(anchor='w')
        self.trailing_detail_labels[triangle_id] = trailing_detail
        
        return card_frame
    
    def update_group_status(self, triangle_id, group_data):
        """อัปเดตสถานะของ group พร้อมข้อมูลเพิ่มเติม"""
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
                self.status_indicators[triangle_id].config(text="🟡")
        
        # Update P&L Breakdown
        arb_pnl = group_data.get('arbitrage_pnl', 0.0)
        rec_pnl = group_data.get('recovery_pnl', 0.0)
        arb_count = group_data.get('arbitrage_count', 0)
        rec_count = group_data.get('recovery_count', 0)
        
        if triangle_id in self.arb_pnl_labels:
            arb_color = TradingTheme.COLORS['success'] if arb_pnl > 0 else TradingTheme.COLORS['danger'] if arb_pnl < 0 else TradingTheme.COLORS['text_primary']
            self.arb_pnl_labels[triangle_id].config(
                text=f"  Arb ({arb_count}): ${arb_pnl:.2f}",
                fg=arb_color
            )
        
        if triangle_id in self.rec_pnl_labels:
            rec_color = TradingTheme.COLORS['success'] if rec_pnl > 0 else TradingTheme.COLORS['danger'] if rec_pnl < 0 else TradingTheme.COLORS['text_primary']
            self.rec_pnl_labels[triangle_id].config(
                text=f"  Rec ({rec_count}): ${rec_pnl:.2f}",
                fg=rec_color
            )
        
        if triangle_id in self.net_pnl_labels:
            net_color = TradingTheme.COLORS['success'] if net_pnl > 0 else TradingTheme.COLORS['danger'] if net_pnl < 0 else TradingTheme.COLORS['text_primary']
            self.net_pnl_labels[triangle_id].config(
                text=f"  Net: ${net_pnl:.2f}",
                fg=net_color
            )
        
        # Update Profit Target & Progress Bar
        min_profit = group_data.get('min_profit_target', 5.0)
        progress_pct = (net_pnl / min_profit * 100) if min_profit > 0 else 0
        progress_pct = max(0, min(100, progress_pct))
        
        if triangle_id in self.target_labels:
            self.target_labels[triangle_id].config(text=f"🎯 Target: ${min_profit:.2f}")
        
        if triangle_id in self.progress_bars:
            canvas = self.progress_bars[triangle_id]
            canvas.delete('all')
            width = canvas.winfo_width() if canvas.winfo_width() > 1 else 300
            fill_width = int(width * progress_pct / 100)
            
            # Background
            canvas.create_rectangle(0, 0, width, 18, fill=TradingTheme.COLORS['secondary_bg'], outline='')
            
            # Progress fill
            if progress_pct > 0:
                fill_color = TradingTheme.COLORS['success'] if progress_pct >= 100 else '#FFA500'
                canvas.create_rectangle(0, 0, fill_width, 18, fill=fill_color, outline='')
        
        if triangle_id in self.progress_labels:
            if net_pnl >= min_profit:
                self.progress_labels[triangle_id].config(
                    text=f"{progress_pct:.0f}% ✅ TARGET REACHED!",
                    fg=TradingTheme.COLORS['success']
                )
            elif net_pnl > 0:
                need_more = min_profit - net_pnl
                self.progress_labels[triangle_id].config(
                    text=f"{progress_pct:.0f}% (Need ${need_more:.2f})",
                    fg='#FFA500'
                )
            else:
                need_total = min_profit - net_pnl
                self.progress_labels[triangle_id].config(
                    text=f"0% (Need ${need_total:.2f})",
                    fg=TradingTheme.COLORS['text_secondary']
                )
        
        # Update Trailing Stop Status
        trailing_active = group_data.get('trailing_active', False)
        trailing_peak = group_data.get('trailing_peak', 0.0)
        trailing_stop = group_data.get('trailing_stop', 0.0)
        
        if triangle_id in self.trailing_status_labels:
            if trailing_active:
                distance_from_stop = net_pnl - trailing_stop
                if distance_from_stop <= 2.0:
                    status_text = "🔒 Trailing: ACTIVE 🚨"
                    status_color = TradingTheme.COLORS['danger']
                else:
                    status_text = "🔒 Trailing: ACTIVE 💎"
                    status_color = TradingTheme.COLORS['success']
                
                self.trailing_status_labels[triangle_id].config(
                    text=status_text,
                    fg=status_color
                )
                
                if triangle_id in self.trailing_detail_labels:
                    detail_text = f"Peak ${trailing_peak:.2f} | Stop ${trailing_stop:.2f}\nNow ${net_pnl:.2f}"
                    if distance_from_stop <= 2.0:
                        detail_text += f" (${distance_from_stop:.2f} away!)"
                    else:
                        detail_text += " (Safe)"
                    
                    self.trailing_detail_labels[triangle_id].config(
                        text=detail_text,
                        fg=status_color
                    )
            elif net_pnl > 0 and net_pnl >= min_profit * 0.8:
                self.trailing_status_labels[triangle_id].config(
                    text="⏳ Trailing: Near Target",
                    fg='#FFA500'
                )
                if triangle_id in self.trailing_detail_labels:
                    self.trailing_detail_labels[triangle_id].config(
                        text=f"(Need ${min_profit - net_pnl:.2f} more)",
                        fg='#FFA500'
                    )
            else:
                self.trailing_status_labels[triangle_id].config(
                    text="🔓 Trailing: Inactive",
                    fg=TradingTheme.COLORS['text_secondary']
                )
                if triangle_id in self.trailing_detail_labels:
                    self.trailing_detail_labels[triangle_id].config(
                        text="(Waiting for profit)",
                        fg=TradingTheme.COLORS['text_secondary']
                    )
    
    def update_summary(self, groups_data):
        """อัปเดต summary"""
        total_groups = len(groups_data)
        active_groups = sum(1 for g in groups_data.values() if g.get('status') == 'active')
        total_net_pnl = sum(g.get('net_pnl', 0.0) for g in groups_data.values())
        total_positions = sum(g.get('arbitrage_count', 0) for g in groups_data.values())
        total_recovery = sum(g.get('recovery_count', 0) for g in groups_data.values())
        
        self.total_groups_label.config(text=f"Total Groups: {total_groups}")
        self.active_groups_label.config(text=f"Active: {active_groups}")
        
        pnl_color = TradingTheme.COLORS['success'] if total_net_pnl > 0 else TradingTheme.COLORS['danger'] if total_net_pnl < 0 else TradingTheme.COLORS['text_primary']
        self.total_pnl_label.config(text=f"Total Net PnL: ${total_net_pnl:.2f}", fg=pnl_color)
        
        self.total_positions_label.config(text=f"Total Positions: {total_positions}")
        self.total_recovery_label.config(text=f"Total Recovery: {total_recovery}")
    
    def create_summary_panel(self):
        """สร้าง summary panel"""
        summary_frame = tk.Frame(self.main_frame, bg=TradingTheme.COLORS['secondary_bg'], height=60)
        summary_frame.pack(fill='x', padx=TradingTheme.SPACING['md'], pady=(TradingTheme.SPACING['md'], 0))
        summary_frame.pack_propagate(False)
        
        # Summary metrics
        metrics_frame = tk.Frame(summary_frame, bg=TradingTheme.COLORS['secondary_bg'])
        metrics_frame.pack(fill='both', expand=True, padx=TradingTheme.SPACING['md'], pady=TradingTheme.SPACING['md'])
        
        # Total groups
        self.total_groups_label = tk.Label(
            metrics_frame,
            text="Total Groups: 0",
            font=TradingTheme.FONTS['body'],
            bg=TradingTheme.COLORS['secondary_bg'],
            fg=TradingTheme.COLORS['text_primary']
        )
        self.total_groups_label.pack(side='left', padx=(0, TradingTheme.SPACING['lg']))
        
        # Active groups
        self.active_groups_label = tk.Label(
            metrics_frame,
            text="Active: 0",
            font=TradingTheme.FONTS['body'],
            bg=TradingTheme.COLORS['secondary_bg'],
            fg=TradingTheme.COLORS['success']
        )
        self.active_groups_label.pack(side='left', padx=(0, TradingTheme.SPACING['lg']))
        
        # Total PnL
        self.total_pnl_label = tk.Label(
            metrics_frame,
            text="Total Net PnL: $0.00",
            font=TradingTheme.FONTS['body'],
            bg=TradingTheme.COLORS['secondary_bg'],
            fg=TradingTheme.COLORS['text_primary']
        )
        self.total_pnl_label.pack(side='left', padx=(0, TradingTheme.SPACING['lg']))
        
        # Total positions
        self.total_positions_label = tk.Label(
            metrics_frame,
            text="Total Positions: 0",
            font=TradingTheme.FONTS['body'],
            bg=TradingTheme.COLORS['secondary_bg'],
            fg=TradingTheme.COLORS['text_primary']
        )
        self.total_positions_label.pack(side='left', padx=(0, TradingTheme.SPACING['lg']))
        
        # Total recovery
        self.total_recovery_label = tk.Label(
            metrics_frame,
            text="Total Recovery: 0",
            font=TradingTheme.FONTS['body'],
            bg=TradingTheme.COLORS['secondary_bg'],
            fg=TradingTheme.COLORS['text_primary']
        )
        self.total_recovery_label.pack(side='left')
    
    def refresh_groups(self):
        """รีเฟรชข้อมูล groups"""
        # Find the main window and call update_group_dashboard
        main_window = self.parent
        while hasattr(main_window, 'parent') and main_window.parent:
            main_window = main_window.parent
        
        if hasattr(main_window, 'update_group_dashboard'):
            main_window.update_group_dashboard()
