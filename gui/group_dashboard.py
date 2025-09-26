"""
Group Dashboard - แสดงสถานะของแต่ละ Group
==========================================

Dashboard ที่แสดงสถานะของแต่ละ arbitrage group แยกตาม triangle
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
from .theme import TradingTheme

class GroupDashboard:
    def __init__(self, parent):
        self.parent = parent
        self.groups = {}
        self.setup_ui()
    
    def setup_ui(self):
        """สร้าง UI สำหรับ Group Dashboard"""
        # Main container
        self.main_frame = tk.Frame(self.parent, bg=TradingTheme.COLORS['secondary_bg'])
        self.main_frame.pack(fill='both', expand=True)
        
        # Header
        self.create_header()
        
        # Positions status panel (แสดงแทน groups grid)
        self.create_positions_status_panel()
    
    def create_header(self):
        """สร้าง header"""
        header_frame = tk.Frame(self.main_frame, bg=TradingTheme.COLORS['secondary_bg'])
        header_frame.pack(fill='x', padx=TradingTheme.SPACING['md'], pady=TradingTheme.SPACING['md'])
        
        # Title
        title_label = tk.Label(
            header_frame,
            text="📊 Positions Status Dashboard",
            font=TradingTheme.FONTS['title'],
            bg=TradingTheme.COLORS['secondary_bg'],
            fg=TradingTheme.COLORS['text_primary']
        )
        title_label.pack(side='left')
        
        # Refresh button
        self.refresh_btn = TradingTheme.create_button_style(
            header_frame, "🔄 Refresh", self.refresh_groups, "secondary"
        )
        self.refresh_btn.pack(side='right')
    
    def create_groups_grid(self):
        """สร้าง grid สำหรับแสดงแต่ละ group"""
        # Container for groups
        self.groups_container = tk.Frame(self.main_frame, bg=TradingTheme.COLORS['secondary_bg'])
        self.groups_container.pack(fill='both', expand=True, padx=TradingTheme.SPACING['md'])
        
        # Create 6 group cards (2 rows x 3 columns)
        self.group_cards = {}
        
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
        
        # Create group cards
        for i, (triangle_id, config) in enumerate(self.triangle_configs.items()):
            row = i // 3
            col = i % 3
            
            card = self.create_group_card(triangle_id, config)
            card.grid(row=row, column=col, padx=TradingTheme.SPACING['sm'], 
                     pady=TradingTheme.SPACING['sm'], sticky='nsew')
            
            self.group_cards[triangle_id] = card
        
        # Configure grid weights
        for i in range(2):
            self.groups_container.grid_rowconfigure(i, weight=1)
        for i in range(3):
            self.groups_container.grid_columnconfigure(i, weight=1)
    
    def create_group_card(self, triangle_id, config):
        """สร้าง card สำหรับแต่ละ group"""
        # Main card frame
        card_frame = tk.Frame(
            self.groups_container,
            bg=TradingTheme.COLORS['primary_bg'],
            relief='raised',
            bd=1
        )
        
        # Header
        header_frame = tk.Frame(card_frame, bg=config['color'], height=40)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        # Group name
        name_label = tk.Label(
            header_frame,
            text=config['name'],
            font=TradingTheme.FONTS['title'],
            bg=config['color'],
            fg='white'
        )
        name_label.pack(side='left', padx=TradingTheme.SPACING['md'], pady=TradingTheme.SPACING['sm'])
        
        # Status indicator
        if not hasattr(self, 'status_indicators'):
            self.status_indicators = {}
        
        status_frame = tk.Frame(header_frame, bg=config['color'])
        status_frame.pack(side='right', padx=TradingTheme.SPACING['md'], pady=TradingTheme.SPACING['sm'])
        
        status_indicator = tk.Label(
            status_frame,
            text="●",
            font=('Arial', 12),
            bg=config['color'],
            fg='#FFD700'  # Gold for active
        )
        status_indicator.pack()
        self.status_indicators[triangle_id] = status_indicator
        
        # Content area
        content_frame = tk.Frame(card_frame, bg=TradingTheme.COLORS['primary_bg'])
        content_frame.pack(fill='both', expand=True, padx=TradingTheme.SPACING['md'], pady=TradingTheme.SPACING['md'])
        
        # Magic number
        magic_label = tk.Label(
            content_frame,
            text=f"Magic: {config['magic']}",
            font=TradingTheme.FONTS['body'],
            bg=TradingTheme.COLORS['primary_bg'],
            fg=TradingTheme.COLORS['text_secondary']
        )
        magic_label.pack(anchor='w')
        
        # Pairs
        pairs_label = tk.Label(
            content_frame,
            text=f"Pairs: {', '.join(config['pairs'])}",
            font=TradingTheme.FONTS['body'],
            bg=TradingTheme.COLORS['primary_bg'],
            fg=TradingTheme.COLORS['text_secondary']
        )
        pairs_label.pack(anchor='w', pady=(TradingTheme.SPACING['xs'], 0))
        
        # Group ID
        if not hasattr(self, 'group_id_labels'):
            self.group_id_labels = {}
        group_id_label = tk.Label(
            content_frame,
            text="Group: None",
            font=TradingTheme.FONTS['body'],
            bg=TradingTheme.COLORS['primary_bg'],
            fg=TradingTheme.COLORS['text_primary']
        )
        group_id_label.pack(anchor='w', pady=(TradingTheme.SPACING['sm'], 0))
        self.group_id_labels[triangle_id] = group_id_label
        
        # PnL
        if not hasattr(self, 'pnl_labels'):
            self.pnl_labels = {}
        pnl_label = tk.Label(
            content_frame,
            text="PnL: $0.00",
            font=TradingTheme.FONTS['body'],
            bg=TradingTheme.COLORS['primary_bg'],
            fg=TradingTheme.COLORS['text_primary']
        )
        pnl_label.pack(anchor='w', pady=(TradingTheme.SPACING['xs'], 0))
        self.pnl_labels[triangle_id] = pnl_label
        
        # Positions count
        if not hasattr(self, 'positions_labels'):
            self.positions_labels = {}
        positions_label = tk.Label(
            content_frame,
            text="Positions: 0",
            font=TradingTheme.FONTS['body'],
            bg=TradingTheme.COLORS['primary_bg'],
            fg=TradingTheme.COLORS['text_primary']
        )
        positions_label.pack(anchor='w', pady=(TradingTheme.SPACING['xs'], 0))
        self.positions_labels[triangle_id] = positions_label
        
        # Recovery positions count
        if not hasattr(self, 'recovery_labels'):
            self.recovery_labels = {}
        recovery_label = tk.Label(
            content_frame,
            text="Recovery: 0",
            font=TradingTheme.FONTS['body'],
            bg=TradingTheme.COLORS['primary_bg'],
            fg=TradingTheme.COLORS['text_primary']
        )
        recovery_label.pack(anchor='w', pady=(TradingTheme.SPACING['xs'], 0))
        self.recovery_labels[triangle_id] = recovery_label
        
        # Last update
        if not hasattr(self, 'last_update_labels'):
            self.last_update_labels = {}
        last_update_label = tk.Label(
            content_frame,
            text="Last: Never",
            font=TradingTheme.FONTS['small'],
            bg=TradingTheme.COLORS['primary_bg'],
            fg=TradingTheme.COLORS['text_secondary']
        )
        last_update_label.pack(anchor='w', pady=(TradingTheme.SPACING['sm'], 0))
        self.last_update_labels[triangle_id] = last_update_label
        
        return card_frame
    
    def create_summary_panel(self):
        """สร้าง summary panel"""
        summary_frame = tk.Frame(self.main_frame, bg=TradingTheme.COLORS['secondary_bg'], height=80)
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
            text="Total PnL: $0.00",
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
    
    def update_group_status(self, triangle_id, group_data):
        """อัปเดตสถานะของ group"""
        if triangle_id not in self.group_cards:
            return
        
        # Update status indicator
        if triangle_id in self.status_indicators:
            if group_data.get('status') == 'active':
                self.status_indicators[triangle_id].config(fg='#00FF00')  # Green
            else:
                self.status_indicators[triangle_id].config(fg='#FFD700')  # Gold
        
        # Update group ID
        if triangle_id in self.group_id_labels:
            group_id = group_data.get('group_id', 'None')
            self.group_id_labels[triangle_id].config(text=f"Group: {group_id}")
        
        # Update PnL
        if triangle_id in self.pnl_labels:
            pnl = group_data.get('total_pnl', 0.0)
            pnl_color = TradingTheme.COLORS['success'] if pnl > 0 else TradingTheme.COLORS['danger'] if pnl < 0 else TradingTheme.COLORS['text_primary']
            self.pnl_labels[triangle_id].config(text=f"PnL: ${pnl:.2f}", fg=pnl_color)
        
        # Update positions count
        if triangle_id in self.positions_labels:
            positions_count = len(group_data.get('positions', []))
            self.positions_labels[triangle_id].config(text=f"Positions: {positions_count}")
        
        # Update recovery count
        if triangle_id in self.recovery_labels:
            recovery_count = len(group_data.get('recovery_chain', []))
            self.recovery_labels[triangle_id].config(text=f"Recovery: {recovery_count}")
        
        # Update last update time
        if triangle_id in self.last_update_labels:
            last_update = datetime.now().strftime("%H:%M:%S")
            self.last_update_labels[triangle_id].config(text=f"Last: {last_update}")
    
    def update_summary(self, groups_data):
        """อัปเดต summary"""
        total_groups = len(groups_data)
        active_groups = sum(1 for g in groups_data.values() if g.get('status') == 'active')
        total_pnl = sum(g.get('total_pnl', 0.0) for g in groups_data.values())
        total_positions = sum(len(g.get('positions', [])) for g in groups_data.values())
        total_recovery = sum(len(g.get('recovery_chain', [])) for g in groups_data.values())
        
        self.total_groups_label.config(text=f"Total Groups: {total_groups}")
        self.active_groups_label.config(text=f"Active: {active_groups}")
        
        pnl_color = TradingTheme.COLORS['success'] if total_pnl > 0 else TradingTheme.COLORS['danger'] if total_pnl < 0 else TradingTheme.COLORS['text_primary']
        self.total_pnl_label.config(text=f"Total PnL: ${total_pnl:.2f}", fg=pnl_color)
        
        self.total_positions_label.config(text=f"Total Positions: {total_positions}")
        self.total_recovery_label.config(text=f"Total Recovery: {total_recovery}")
    
    def refresh_groups(self):
        """รีเฟรชข้อมูล groups"""
        # Find the main window and call update_group_dashboard
        main_window = self.parent
        while hasattr(main_window, 'parent') and main_window.parent:
            main_window = main_window.parent
        
        if hasattr(main_window, 'update_group_dashboard'):
            main_window.update_group_dashboard()
    
    def create_positions_status_panel(self):
        """สร้าง panel แสดงสถานะไม้แบบละเอียด"""
        # Main positions status frame
        self.positions_status_frame = tk.Frame(
            self.main_frame, 
            bg=TradingTheme.COLORS['secondary_bg'],
            relief='raised',
            bd=1
        )
        self.positions_status_frame.pack(fill='both', expand=True, padx=TradingTheme.SPACING['md'], pady=TradingTheme.SPACING['md'])
        
        # Title
        title_label = tk.Label(
            self.positions_status_frame,
            text="📊 POSITIONS STATUS",
            font=TradingTheme.FONTS['subheader'],
            bg=TradingTheme.COLORS['secondary_bg'],
            fg=TradingTheme.COLORS['text_primary']
        )
        title_label.pack(anchor='w', padx=TradingTheme.SPACING['md'], pady=(TradingTheme.SPACING['md'], TradingTheme.SPACING['sm']))
        
        # Create scrollable text widget for positions status
        self.positions_text = scrolledtext.ScrolledText(
            self.positions_status_frame,
            height=25,
            font=('Consolas', 9),
            bg=TradingTheme.COLORS['primary_bg'],
            fg=TradingTheme.COLORS['text_primary'],
            insertbackground=TradingTheme.COLORS['text_primary'],
            selectbackground=TradingTheme.COLORS['accent_bg'],
            state='disabled',
            wrap='none'
        )
        self.positions_text.pack(fill='both', expand=True, padx=TradingTheme.SPACING['md'], pady=TradingTheme.SPACING['sm'])
    
    def update_positions_status(self, positions_data):
        """อัปเดตสถานะไม้แบบละเอียด"""
        if not hasattr(self, 'positions_text'):
            return
        
        # Clear existing content
        self.positions_text.config(state='normal')
        self.positions_text.delete(1.0, tk.END)
        
        try:
            # Format positions data
            status_text = self.format_positions_status(positions_data)
            self.positions_text.insert(tk.END, status_text)
            
        except Exception as e:
            self.positions_text.insert(tk.END, f"❌ Error updating positions status: {e}")
        
        # Disable editing
        self.positions_text.config(state='disabled')
    
    def format_positions_status(self, positions_data):
        """จัดรูปแบบข้อมูลสถานะไม้แบ่งตาม Group"""
        output = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        output.append(f"🕐 Last Update: {timestamp}\n")
        output.append("=" * 100 + "\n")
        
        # แบ่งตาม Group
        groups_data = positions_data.get('groups', {})
        
        for group_id in sorted(groups_data.keys()):
            group_data = groups_data[group_id]
            group_name = group_id.replace('group_triangle_', 'G').replace('_', ' ')
            
            output.append(f"\n📊 {group_name.upper()} STATUS:\n")
            output.append("-" * 80 + "\n")
            
            # Profit Arbitrage Positions
            profit_arbitrage = group_data.get('profit_arbitrage', [])
            if profit_arbitrage:
                output.append("🟢 PROFIT ARBITRAGE POSITIONS:\n")
                for i, pos in enumerate(profit_arbitrage, 1):
                    symbol = pos.get('symbol', 'Unknown')
                    order_id = pos.get('order_id', 'N/A')
                    pnl = pos.get('pnl', 0)
                    risk = pos.get('risk_percent', 0)
                    distance = pos.get('price_distance', 0)
                    
                    output.append(f"     {i}. {symbol:<8} (Order: {order_id}) - ✅ HEDGED | PnL: ${pnl:>8.2f}\n")
                    output.append(f"         Risk: {risk:>6.2f}% (info only)\n")
                    output.append(f"         Distance: {distance:>6.1f} pips (≥10) ✅\n")
            else:
                output.append("🟢 PROFIT ARBITRAGE POSITIONS: None\n")
            
            output.append("\n")
            
            # Losing Arbitrage Positions
            losing_arbitrage = group_data.get('losing_arbitrage', [])
            if losing_arbitrage:
                output.append("🔴 LOSING ARBITRAGE POSITIONS:\n")
                for i, pos in enumerate(losing_arbitrage, 1):
                    symbol = pos.get('symbol', 'Unknown')
                    order_id = pos.get('order_id', 'N/A')
                    pnl = pos.get('pnl', 0)
                    risk = pos.get('risk_percent', 0)
                    distance = pos.get('price_distance', 0)
                    is_hedged = pos.get('is_hedged', False)
                    
                    hedged_status = "✅ HEDGED" if is_hedged else "❌ NOT HEDGED"
                    distance_status = "✅" if distance >= 10 else "❌"
                    
                    output.append(f"     {i}. {symbol:<8} (Order: {order_id}) - {hedged_status} | PnL: ${pnl:>8.2f}\n")
                    output.append(f"         Risk: {risk:>6.2f}% (info only)\n")
                    output.append(f"         Distance: {distance:>6.1f} pips (≥10) {distance_status}\n")
            else:
                output.append("🔴 LOSING ARBITRAGE POSITIONS: None\n")
            
            output.append("\n")
            
            # Profit Correlation Positions
            profit_correlation = group_data.get('profit_correlation', [])
            if profit_correlation:
                output.append("🟢 PROFIT CORRELATION POSITIONS:\n")
                for i, pos in enumerate(profit_correlation, 1):
                    symbol = pos.get('symbol', 'Unknown')
                    order_id = pos.get('order_id', 'N/A')
                    pnl = pos.get('pnl', 0)
                    output.append(f"     {i}. {symbol:<8} (Order: {order_id}) - PnL: ${pnl:>8.2f}\n")
            else:
                output.append("🟢 PROFIT CORRELATION POSITIONS: None\n")
            
            output.append("\n")
            
            # Losing Correlation Positions
            losing_correlation = group_data.get('losing_correlation', [])
            if losing_correlation:
                output.append("🔴 LOSING CORRELATION POSITIONS:\n")
                for i, pos in enumerate(losing_correlation, 1):
                    symbol = pos.get('symbol', 'Unknown')
                    order_id = pos.get('order_id', 'N/A')
                    pnl = pos.get('pnl', 0)
                    output.append(f"     {i}. {symbol:<8} (Order: {order_id}) - PnL: ${pnl:>8.2f}\n")
            else:
                output.append("🔴 LOSING CORRELATION POSITIONS: None\n")
            
            output.append("\n")
            
            # Existing Correlation Positions
            existing_correlation = group_data.get('existing_correlation', [])
            if existing_correlation:
                output.append("🔄 EXISTING CORRELATION POSITIONS:\n")
                for i, pos in enumerate(existing_correlation, 1):
                    symbol = pos.get('symbol', 'Unknown')
                    order_id = pos.get('order_id', 'N/A')
                    pnl = pos.get('pnl', 0)
                    output.append(f"     {i}. {symbol:<8} (Order: {order_id}) - PnL: ${pnl:>8.2f}\n")
            else:
                output.append("🔄 EXISTING CORRELATION POSITIONS: None\n")
            
            output.append("\n" + "=" * 100 + "\n")
        
        return ''.join(output)
