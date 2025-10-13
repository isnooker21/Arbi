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
        
        # Main content area - แบ่งเป็น 2 ส่วน
        self.create_main_content_area()
        
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
    
    def create_main_content_area(self):
        """สร้างพื้นที่หลัก - แต่ละ group แยกเต็มหน้า"""
        # Main content frame
        self.content_frame = tk.Frame(self.main_frame, bg='#1a1a1a')
        self.content_frame.pack(fill='both', expand=True)
        
        # Create groups view (default)
        self.create_groups_view()
        
        # Initialize group detail views (hidden by default)
        self.group_detail_views = {}
        self.current_view = 'groups'
    
    def create_groups_view(self):
        """สร้าง groups view - แสดงทุก group ในหน้าเดียว"""
        # Clear existing content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Groups container
        groups_container = tk.Frame(self.content_frame, bg='#1a1a1a')
        groups_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Create canvas for scrolling
        self.groups_canvas = tk.Canvas(
            groups_container,
            bg='#1a1a1a',
            highlightthickness=0
        )
        
        # Scrollbar
        groups_scrollbar = ttk.Scrollbar(groups_container, orient='vertical', command=self.groups_canvas.yview)
        self.groups_canvas.configure(yscrollcommand=groups_scrollbar.set)
        
        self.groups_canvas.pack(side='left', fill='both', expand=True)
        groups_scrollbar.pack(side='right', fill='y')
        
        # Groups frame inside canvas
        self.groups_frame = tk.Frame(self.groups_canvas, bg='#1a1a1a')
        self.canvas_frame = self.groups_canvas.create_window((0, 0), window=self.groups_frame, anchor='nw')
        
        # Bind events
        self.groups_frame.bind('<Configure>', lambda e: self.groups_canvas.configure(scrollregion=self.groups_canvas.bbox('all')))
        self.groups_canvas.bind_all('<MouseWheel>', lambda e: self.groups_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        # Create group cards
        self.create_full_size_group_cards()
    
    def create_full_size_group_cards(self):
        """สร้าง group cards ขนาดใหญ่เต็มหน้า"""
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
        
        # Create full-size cards (1 card per row)
        for i, config in enumerate(group_configs):
            self.create_single_full_size_group_card(config, i)
    
    def create_single_full_size_group_card(self, config, row):
        """สร้าง group card ขนาดใหญ่เต็มแถว"""
        # Main card frame
        card_frame = tk.Frame(
            self.groups_frame,
            bg='#2d2d2d',
            relief='raised',
            bd=2,
            height=200
        )
        card_frame.pack(fill='x', padx=20, pady=10)
        card_frame.pack_propagate(False)
        
        # Header
        header_frame = tk.Frame(card_frame, bg=config['color'], height=50)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        # Group name and magic
        name_label = tk.Label(
            header_frame,
            text=f"{config['name']} (Magic: {config['magic']})",
            font=('Arial', 14, 'bold'),
            bg=config['color'],
            fg='white'
        )
        name_label.pack(side='left', padx=20, pady=10)
        
        # Status indicator
        status_indicator = tk.Label(
            header_frame,
            text="🔴",
            font=('Arial', 18),
            bg=config['color'],
            fg='white'
        )
        status_indicator.pack(side='right', padx=20, pady=10)
        self.status_indicators[config['id']] = status_indicator
        
        # Content area
        content_frame = tk.Frame(card_frame, bg='#2d2d2d')
        content_frame.pack(fill='both', expand=True, padx=20, pady=15)
        
        # Left side - Basic info
        left_frame = tk.Frame(content_frame, bg='#2d2d2d', width=300)
        left_frame.pack(side='left', fill='y', padx=(0, 20))
        left_frame.pack_propagate(False)
        
        # Pairs info
        pairs_label = tk.Label(
            left_frame,
            text="📊 Currency Pairs:",
            font=('Arial', 11, 'bold'),
            bg='#2d2d2d',
            fg='#FFD700'
        )
        pairs_label.pack(anchor='w', pady=(0, 5))
        
        pairs_text = tk.Label(
            left_frame,
            text=f"{' • '.join(config['pairs'])}",
            font=('Arial', 12),
            bg='#2d2d2d',
            fg='white'
        )
        pairs_text.pack(anchor='w', pady=(0, 15))
        
        # P&L Section
        pnl_frame = tk.Frame(left_frame, bg='#2d2d2d')
        pnl_frame.pack(fill='x', pady=(0, 15))
        
        pnl_title = tk.Label(
            pnl_frame,
            text="💰 P&L Summary:",
            font=('Arial', 11, 'bold'),
            bg='#2d2d2d',
            fg='#FFD700'
        )
        pnl_title.pack(anchor='w', pady=(0, 5))
        
        # P&L values
        pnl_values = {
            'arb': tk.Label(pnl_frame, text="Arbitrage: $0.00", font=('Arial', 10), bg='#2d2d2d', fg='white'),
            'rec': tk.Label(pnl_frame, text="Recovery: $0.00", font=('Arial', 10), bg='#2d2d2d', fg='white'),
            'net': tk.Label(pnl_frame, text="Net: $0.00", font=('Arial', 11, 'bold'), bg='#2d2d2d', fg='#4CAF50')
        }
        
        for label in pnl_values.values():
            label.pack(anchor='w')
        
        if not hasattr(self, 'pnl_labels'):
            self.pnl_labels = {}
        self.pnl_labels[config['id']] = pnl_values
        
        # Status info
        status_info = tk.Label(
            left_frame,
            text="📈 Status: No Active Positions",
            font=('Arial', 10),
            bg='#2d2d2d',
            fg='#888888'
        )
        status_info.pack(anchor='w')
        
        # Right side - Quick actions and positions
        right_frame = tk.Frame(content_frame, bg='#2d2d2d')
        right_frame.pack(side='right', fill='both', expand=True)
        
        # Quick actions
        actions_label = tk.Label(
            right_frame,
            text="⚡ Quick Actions:",
            font=('Arial', 11, 'bold'),
            bg='#2d2d2d',
            fg='#FFD700'
        )
        actions_label.pack(anchor='w', pady=(0, 10))
        
        # Action buttons
        buttons_frame = tk.Frame(right_frame, bg='#2d2d2d')
        buttons_frame.pack(fill='x', pady=(0, 20))
        
        # View Details button
        view_details_btn = tk.Button(
            buttons_frame,
            text="🔍 View Details",
            command=lambda: self.show_group_details(config['id']),
            bg='#4CAF50',
            fg='white',
            font=('Arial', 10, 'bold'),
            padx=15,
            pady=8,
            relief='flat',
            cursor='hand2'
        )
        view_details_btn.pack(side='left', padx=(0, 10))
        
        # Close All Positions button
        close_all_btn = tk.Button(
            buttons_frame,
            text="⏹️ Close All",
            command=lambda: self.close_all_positions(config['id']),
            bg='#F44336',
            fg='white',
            font=('Arial', 10, 'bold'),
            padx=15,
            pady=8,
            relief='flat',
            cursor='hand2'
        )
        close_all_btn.pack(side='left', padx=(0, 10))
        
        # Quick positions overview
        positions_label = tk.Label(
            right_frame,
            text="🎯 Active Positions:",
            font=('Arial', 11, 'bold'),
            bg='#2d2d2d',
            fg='#FFD700'
        )
        positions_label.pack(anchor='w', pady=(0, 5))
        
        # Simple positions list
        positions_text = tk.Label(
            right_frame,
            text="No active positions",
            font=('Arial', 10),
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
    
    def create_detailed_view(self, parent):
        """สร้าง detailed view สำหรับแสดงไม้และการแก้ไม้"""
        # Header
        header_frame = tk.Frame(parent, bg='#2d2d2d', height=50)
        header_frame.pack(fill='x', pady=(0, 10))
        header_frame.pack_propagate(False)
        
        # Title
        title_label = tk.Label(
            header_frame,
            text="📊 Group Details",
            font=('Arial', 14, 'bold'),
            bg='#2d2d2d',
            fg='#FFD700'
        )
        title_label.pack(side='left', padx=15, pady=10)
        
        # Selected group info
        self.selected_group_label = tk.Label(
            header_frame,
            text="No Group Selected",
            font=('Arial', 12),
            bg='#2d2d2d',
            fg='white'
        )
        self.selected_group_label.pack(side='right', padx=15, pady=10)
        
        # Main content area
        content_frame = tk.Frame(parent, bg='#1a1a1a')
        content_frame.pack(fill='both', expand=True)
        
        # Create notebook for tabs
        from tkinter import ttk
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Configure notebook style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background='#2d2d2d')
        style.configure('TNotebook.Tab', background='#2d2d2d', foreground='white')
        style.map('TNotebook.Tab', background=[('selected', '#4CAF50')])
        
        # Tab 1: Active Positions
        self.positions_frame = tk.Frame(self.notebook, bg='#2d2d2d')
        self.notebook.add(self.positions_frame, text="🎯 Active Positions")
        self.create_positions_tab()
        
        # Tab 2: Recovery History
        self.recovery_frame = tk.Frame(self.notebook, bg='#2d2d2d')
        self.notebook.add(self.recovery_frame, text="🔄 Recovery History")
        self.create_recovery_tab()
        
        # Tab 3: Trading Log
        self.log_frame = tk.Frame(self.notebook, bg='#2d2d2d')
        self.notebook.add(self.log_frame, text="📝 Trading Log")
        self.create_log_tab()
        
        # Tab 4: Performance
        self.performance_frame = tk.Frame(self.notebook, bg='#2d2d2d')
        self.notebook.add(self.performance_frame, text="📈 Performance")
        self.create_performance_tab()
    
    def create_positions_tab(self):
        """สร้าง tab แสดง positions"""
        # Header
        header_frame = tk.Frame(self.positions_frame, bg='#3d3d3d', height=40)
        header_frame.pack(fill='x', padx=10, pady=10)
        header_frame.pack_propagate(False)
        
        tk.Label(
            header_frame,
            text="🎯 Active Positions",
            font=('Arial', 12, 'bold'),
            bg='#3d3d3d',
            fg='#FFD700'
        ).pack(side='left', padx=10, pady=8)
        
        # Positions list
        positions_container = tk.Frame(self.positions_frame, bg='#2d2d2d')
        positions_container.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Create treeview for positions
        columns = ('Symbol', 'Type', 'Volume', 'Open Price', 'Current P&L', 'Status')
        self.positions_tree = ttk.Treeview(positions_container, columns=columns, show='headings', height=15)
        
        # Configure columns
        for col in columns:
            self.positions_tree.heading(col, text=col)
            self.positions_tree.column(col, width=100, anchor='center')
        
        # Scrollbar
        positions_scrollbar = ttk.Scrollbar(positions_container, orient='vertical', command=self.positions_tree.yview)
        self.positions_tree.configure(yscrollcommand=positions_scrollbar.set)
        
        # Pack
        self.positions_tree.pack(side='left', fill='both', expand=True)
        positions_scrollbar.pack(side='right', fill='y')
        
        # Sample data
        sample_positions = [
            ('EURUSD', 'BUY', '0.50', '1.08520', '+$12.30', 'Active'),
            ('GBPUSD', 'BUY', '0.48', '1.26520', '+$8.75', 'Active'),
            ('EURGBP', 'SELL', '0.52', '0.85820', '-$5.55', 'Active')
        ]
        
        for pos in sample_positions:
            self.positions_tree.insert('', 'end', values=pos)
    
    def create_recovery_tab(self):
        """สร้าง tab แสดง recovery history"""
        # Header
        header_frame = tk.Frame(self.recovery_frame, bg='#3d3d3d', height=40)
        header_frame.pack(fill='x', padx=10, pady=10)
        header_frame.pack_propagate(False)
        
        tk.Label(
            header_frame,
            text="🔄 Recovery History",
            font=('Arial', 12, 'bold'),
            bg='#3d3d3d',
            fg='#FFD700'
        ).pack(side='left', padx=10, pady=8)
        
        # Recovery list
        recovery_container = tk.Frame(self.recovery_frame, bg='#2d2d2d')
        recovery_container.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Create treeview for recovery
        columns = ('Time', 'Original', 'Recovery', 'Correlation', 'Result', 'P&L')
        self.recovery_tree = ttk.Treeview(recovery_container, columns=columns, show='headings', height=15)
        
        # Configure columns
        for col in columns:
            self.recovery_tree.heading(col, text=col)
            self.recovery_tree.column(col, width=100, anchor='center')
        
        # Scrollbar
        recovery_scrollbar = ttk.Scrollbar(recovery_container, orient='vertical', command=self.recovery_tree.yview)
        self.recovery_tree.configure(yscrollcommand=recovery_scrollbar.set)
        
        # Pack
        self.recovery_tree.pack(side='left', fill='both', expand=True)
        recovery_scrollbar.pack(side='right', fill='y')
        
        # Sample data
        sample_recovery = [
            ('14:30:25', 'EURUSD', 'GBPUSD', '0.85', 'Success', '+$3.20'),
            ('13:45:12', 'GBPUSD', 'USDJPY', '0.78', 'Success', '+$1.85'),
            ('12:15:33', 'EURGBP', 'EURUSD', '0.92', 'Success', '+$2.45')
        ]
        
        for rec in sample_recovery:
            self.recovery_tree.insert('', 'end', values=rec)
    
    def create_log_tab(self):
        """สร้าง tab แสดง trading log"""
        # Header
        header_frame = tk.Frame(self.log_frame, bg='#3d3d3d', height=40)
        header_frame.pack(fill='x', padx=10, pady=10)
        header_frame.pack_propagate(False)
        
        tk.Label(
            header_frame,
            text="📝 Trading Log",
            font=('Arial', 12, 'bold'),
            bg='#3d3d3d',
            fg='#FFD700'
        ).pack(side='left', padx=10, pady=8)
        
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
            height=20
        )
        
        log_scrollbar = ttk.Scrollbar(log_container, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        # Pack
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')
        
        # Sample log
        sample_log = """2025-01-13 17:30:25 - Triangle 1: Checking arbitrage conditions for ('EURUSD', 'GBPUSD', 'EURGBP')
2025-01-13 17:30:25 - ('EURUSD', 'GBPUSD', 'EURGBP'): Calculating arbitrage direction...
2025-01-13 17:30:25 - ('EURUSD', 'GBPUSD', 'EURGBP'): Prices - EURUSD: 1.08500/1.08520, GBPUSD: 1.26500/1.26520, EURGBP: 0.85800/0.85820
2025-01-13 17:30:25 - ('EURUSD', 'GBPUSD', 'EURGBP'): Forward path = 0.45%, Reverse path = 0.38%, Cost = 0.12%
2025-01-13 17:30:25 - ('EURUSD', 'GBPUSD', 'EURGBP'): Net profits - Forward: 0.33%, Reverse: 0.26%, Min threshold: 0.30%
2025-01-13 17:30:25 - ✅ ('EURUSD', 'GBPUSD', 'EURGBP'): FORWARD path selected - Net profit: 0.33%
2025-01-13 17:30:25 - ✅ EURUSD_GBPUSD_EURGBP_1: Direction check passed - FORWARD path, profit: 0.3300%
2025-01-13 17:30:25 - 💰 ('EURUSD', 'GBPUSD', 'EURGBP'): Raw profit: 0.45%, Cost: 0.12%, Net: 0.33%
2025-01-13 17:30:25 - ✅ ('EURUSD', 'GBPUSD', 'EURGBP'): Profit check passed (0.33% >= 0.30%)
2025-01-13 17:30:25 - ✅ EURUSD_GBPUSD_EURGBP_1: Feasibility check passed
2025-01-13 17:30:25 - 📊 ('EURUSD', 'GBPUSD', 'EURGBP'): Spreads - EURUSD: 1.2, GBPUSD: 1.5, EURGBP: 1.8
2025-01-13 17:30:25 - ✅ ('EURUSD', 'GBPUSD', 'EURGBP'): All spreads acceptable (max: 1.8 <= 3.0)
2025-01-13 17:30:25 - ✅ ('EURUSD', 'GBPUSD', 'EURGBP'): Spread check passed
2025-01-13 17:30:25 - 💰 EURUSD_GBPUSD_EURGBP_1: Account balance: $10,000.00
2025-01-13 17:30:25 - ⚙️ EURUSD_GBPUSD_EURGBP_1: Risk per trade: 1.0%
2025-01-13 17:30:25 - 🚀 EURUSD_GBPUSD_EURGBP_1: All checks passed! Sending orders...
2025-01-13 17:30:25 - 🚀 Sending FORWARD arbitrage for EURUSD_GBPUSD_EURGBP_1: ['EURUSD', 'GBPUSD', 'EURGBP']
2025-01-13 17:30:25 - ✅ EURUSD BUY 0.50 lots - SUCCESS (Ticket: 12345)
2025-01-13 17:30:25 - ✅ GBPUSD BUY 0.48 lots - SUCCESS (Ticket: 12346)
2025-01-13 17:30:25 - ✅ EURGBP SELL 0.52 lots - SUCCESS (Ticket: 12347)
2025-01-13 17:30:25 - ✅ EURUSD_GBPUSD_EURGBP_1: All 3 orders placed successfully!
2025-01-13 17:30:25 - 🎉 EURUSD_GBPUSD_EURGBP_1: All orders placed successfully!"""
        
        self.log_text.insert('1.0', sample_log)
        self.log_text.config(state='disabled')
    
    def create_performance_tab(self):
        """สร้าง tab แสดง performance metrics"""
        # Header
        header_frame = tk.Frame(self.performance_frame, bg='#3d3d3d', height=40)
        header_frame.pack(fill='x', padx=10, pady=10)
        header_frame.pack_propagate(False)
        
        tk.Label(
            header_frame,
            text="📈 Performance Metrics",
            font=('Arial', 12, 'bold'),
            bg='#3d3d3d',
            fg='#FFD700'
        ).pack(side='left', padx=10, pady=8)
        
        # Performance metrics
        metrics_frame = tk.Frame(self.performance_frame, bg='#2d2d2d')
        metrics_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Create metrics grid
        metrics_data = [
            ("Total Trades", "15", "#4CAF50"),
            ("Winning Trades", "9", "#4CAF50"),
            ("Losing Trades", "6", "#F44336"),
            ("Win Rate", "60%", "#4CAF50"),
            ("Average Win", "$8.45", "#4CAF50"),
            ("Average Loss", "-$5.20", "#F44336"),
            ("Profit Factor", "2.43", "#4CAF50"),
            ("Max Drawdown", "$15.30", "#F44336"),
            ("Recovery Success", "85%", "#4CAF50"),
            ("Avg Recovery Time", "2.5 min", "#2196F3"),
            ("Best Trade", "$22.80", "#4CAF50"),
            ("Worst Trade", "-$12.50", "#F44336")
        ]
        
        for i, (metric, value, color) in enumerate(metrics_data):
            row = i // 3
            col = i % 3
            
            metric_frame = tk.Frame(metrics_frame, bg=color, width=150, height=80)
            metric_frame.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
            metric_frame.grid_propagate(False)
            
            tk.Label(
                metric_frame,
                text=metric,
                font=('Arial', 9, 'bold'),
                bg=color,
                fg='white'
            ).pack(pady=(5, 0))
            
            tk.Label(
                metric_frame,
                text=value,
                font=('Arial', 14, 'bold'),
                bg=color,
                fg='white'
            ).pack(expand=True)
        
        # Configure grid weights
        for i in range(4):  # 4 rows
            metrics_frame.grid_rowconfigure(i, weight=1)
        for i in range(3):  # 3 columns
            metrics_frame.grid_columnconfigure(i, weight=1)
    
    def create_modern_groups_grid(self, parent=None):
        """สร้าง groups grid แบบใหม่ - สวยและใช้งานง่าย"""
        if parent is None:
            parent = self.main_frame
            
        # Main container
        container_frame = tk.Frame(parent, bg='#1a1a1a')
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
            if hasattr(self, 'stats_cards'):
                self.update_stats_overview(groups_data)

            # Update group cards (only if in groups view)
            if hasattr(self, 'group_cards') and self.current_view == 'groups':
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
