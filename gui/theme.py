"""
Modern Trading GUI Theme
=======================

Professional dark theme for trading applications
Inspired by MetaTrader 5, TradingView, and modern trading platforms
"""

import tkinter as tk
from tkinter import ttk

class TradingTheme:
    """Modern trading application theme"""
    
    # Color Palette - Dark Trading Theme
    COLORS = {
        # Background Colors
        'primary_bg': '#1a1a1a',        # Main background
        'secondary_bg': '#2d2d2d',      # Card/panel background  
        'accent_bg': '#404040',         # Input/button background
        'hover_bg': '#505050',          # Hover effects
        'selected_bg': '#0066cc',       # Selected items
        
        # Text Colors
        'text_primary': '#ffffff',      # Primary text
        'text_secondary': '#b3b3b3',    # Secondary text
        'text_muted': '#808080',        # Muted text
        'text_disabled': '#555555',     # Disabled text
        
        # Status Colors
        'success': '#4CAF50',           # Green for profits/positive
        'success_dark': '#2E7D32',      # Dark green
        'danger': '#f44336',            # Red for losses/negative
        'danger_dark': '#C62828',       # Dark red
        'warning': '#ff9800',           # Orange for warnings
        'warning_dark': '#F57C00',      # Dark orange
        'info': '#2196f3',              # Blue for info
        'info_dark': '#1976D2',         # Dark blue
        
        # Trading Colors
        'buy_color': '#00c851',         # Buy orders/positions
        'buy_color_dark': '#00a041',    # Dark buy color
        'sell_color': '#ff4444',        # Sell orders/positions
        'sell_color_dark': '#cc0000',   # Dark sell color
        'neutral_color': '#757575',     # Neutral/closed positions
        
        # UI Elements
        'border': '#555555',            # Border color
        'border_light': '#666666',      # Light border
        'border_dark': '#333333',       # Dark border
        'shadow': '#000000',            # Shadow color
        'highlight': '#0066cc',         # Highlight color
        
        # Chart Colors
        'chart_bg': '#1e1e1e',         # Chart background
        'chart_grid': '#333333',       # Chart grid lines
        'chart_candle_up': '#4CAF50',   # Up candles
        'chart_candle_down': '#f44336', # Down candles
        'chart_line': '#2196f3',        # Line charts
    }
    
    # Typography
    FONTS = {
        'header': ('Segoe UI', 16, 'bold'),
        'subheader': ('Segoe UI', 14, 'bold'), 
        'title': ('Segoe UI', 12, 'bold'),
        'body': ('Segoe UI', 10),
        'small': ('Segoe UI', 9),
        'tiny': ('Segoe UI', 8),
        'monospace': ('Consolas', 10),  # For prices/numbers
        'monospace_bold': ('Consolas', 10, 'bold'),
        'large_numbers': ('Consolas', 14, 'bold'),  # For PnL displays
        'huge_numbers': ('Consolas', 18, 'bold'),   # For main stats
    }
    
    # Spacing
    SPACING = {
        'xs': 4,    # Extra small
        'sm': 8,    # Small
        'md': 12,   # Medium
        'lg': 16,   # Large
        'xl': 20,   # Extra large
        'xxl': 24,  # Extra extra large
    }
    
    # Border Radius (for rounded corners)
    RADIUS = {
        'sm': 4,
        'md': 6,
        'lg': 8,
        'xl': 12,
    }
    
    @classmethod
    def apply_theme(cls, root):
        """Apply theme to root window"""
        root.configure(bg=cls.COLORS['primary_bg'])
        
        # Configure ttk styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure Treeview
        style.configure("Treeview",
                       background=cls.COLORS['secondary_bg'],
                       foreground=cls.COLORS['text_primary'],
                       fieldbackground=cls.COLORS['secondary_bg'],
                       borderwidth=0,
                       font=cls.FONTS['body'])
        
        style.configure("Treeview.Heading",
                       background=cls.COLORS['accent_bg'],
                       foreground=cls.COLORS['text_primary'],
                       font=cls.FONTS['title'],
                       relief='flat')
        
        style.map("Treeview.Heading",
                 background=[('active', cls.COLORS['hover_bg'])])
        
        # Configure Notebook (tabs)
        style.configure("TNotebook",
                       background=cls.COLORS['primary_bg'],
                       borderwidth=0)
        
        style.configure("TNotebook.Tab",
                       background=cls.COLORS['secondary_bg'],
                       foreground=cls.COLORS['text_primary'],
                       font=cls.FONTS['body'],
                       padding=[cls.SPACING['md'], cls.SPACING['sm']])
        
        style.map("TNotebook.Tab",
                 background=[('selected', cls.COLORS['accent_bg']),
                           ('active', cls.COLORS['hover_bg'])])
        
        # Configure Scrollbar
        style.configure("Vertical.TScrollbar",
                       background=cls.COLORS['accent_bg'],
                       troughcolor=cls.COLORS['secondary_bg'],
                       borderwidth=0,
                       arrowcolor=cls.COLORS['text_primary'],
                       darkcolor=cls.COLORS['accent_bg'],
                       lightcolor=cls.COLORS['accent_bg'])
        
        style.configure("Horizontal.TScrollbar",
                       background=cls.COLORS['accent_bg'],
                       troughcolor=cls.COLORS['secondary_bg'],
                       borderwidth=0,
                       arrowcolor=cls.COLORS['text_primary'],
                       darkcolor=cls.COLORS['accent_bg'],
                       lightcolor=cls.COLORS['accent_bg'])
    
    @classmethod
    def create_button_style(cls, parent, text, command, style_type="primary", **kwargs):
        """Create modern button with hover effects"""
        styles = {
            'primary': {
                'bg': cls.COLORS['info'],
                'fg': cls.COLORS['text_primary'],
                'activebackground': cls.COLORS['info_dark']
            },
            'success': {
                'bg': cls.COLORS['success'],
                'fg': cls.COLORS['text_primary'],
                'activebackground': cls.COLORS['success_dark']
            },
            'danger': {
                'bg': cls.COLORS['danger'],
                'fg': cls.COLORS['text_primary'],
                'activebackground': cls.COLORS['danger_dark']
            },
            'warning': {
                'bg': cls.COLORS['warning'],
                'fg': cls.COLORS['text_primary'],
                'activebackground': cls.COLORS['warning_dark']
            },
            'secondary': {
                'bg': cls.COLORS['accent_bg'],
                'fg': cls.COLORS['text_primary'],
                'activebackground': cls.COLORS['hover_bg']
            }
        }
        
        style = styles.get(style_type, styles['primary'])
        
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=cls.FONTS['body'],
            bg=style['bg'],
            fg=style['fg'],
            bd=0,
            padx=cls.SPACING['lg'],
            pady=cls.SPACING['sm'],
            relief='flat',
            cursor='hand2',
            activebackground=style['activebackground'],
            **kwargs
        )
        
        # Add hover effects
        def on_enter(e):
            btn['bg'] = cls.COLORS['hover_bg']
        def on_leave(e):
            btn['bg'] = style['bg']
            
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)
        
        return btn
    
    @classmethod
    def create_info_card(cls, parent, title, value, change=None, icon="", width=200, height=100):
        """Create modern info card"""
        frame = tk.Frame(
            parent, 
            bg=cls.COLORS['secondary_bg'], 
            relief='flat', 
            bd=1,
            width=width,
            height=height
        )
        frame.pack_propagate(False)
        
        # Title with icon
        title_frame = tk.Frame(frame, bg=cls.COLORS['secondary_bg'])
        title_frame.pack(fill='x', padx=cls.SPACING['md'], pady=(cls.SPACING['md'], 0))
        
        title_label = tk.Label(
            title_frame,
            text=f"{icon} {title}",
            font=cls.FONTS['small'],
            bg=cls.COLORS['secondary_bg'],
            fg=cls.COLORS['text_secondary']
        )
        title_label.pack(anchor='w')
        
        # Value
        value_label = tk.Label(
            frame,
            text=value,
            font=cls.FONTS['large_numbers'],
            bg=cls.COLORS['secondary_bg'],
            fg=cls.COLORS['text_primary']
        )
        value_label.pack(pady=cls.SPACING['sm'])
        
        # Change indicator
        if change is not None:
            change_color = cls.COLORS['success'] if change > 0 else cls.COLORS['danger']
            change_text = f"{'↗' if change > 0 else '↘'} {abs(change):.2f}%"
            
            change_label = tk.Label(
                frame,
                text=change_text,
                font=cls.FONTS['small'],
                bg=cls.COLORS['secondary_bg'],
                fg=change_color
            )
            change_label.pack(pady=(0, cls.SPACING['md']))
        
        return frame, value_label
    
    @classmethod
    def create_status_indicator(cls, parent, title, status="disconnected"):
        """Create status indicator with icon and color"""
        frame = tk.Frame(parent, bg=cls.COLORS['secondary_bg'])
        
        # Status colors and icons
        status_config = {
            'connected': {'color': cls.COLORS['success'], 'icon': '🟢'},
            'connecting': {'color': cls.COLORS['warning'], 'icon': '🟡'},
            'disconnected': {'color': cls.COLORS['danger'], 'icon': '🔴'},
            'error': {'color': cls.COLORS['danger'], 'icon': '⚠️'},
            'active': {'color': cls.COLORS['success'], 'icon': '⚡'},
            'inactive': {'color': cls.COLORS['text_muted'], 'icon': '⚫'},
        }
        
        config = status_config.get(status, status_config['disconnected'])
        
        indicator_label = tk.Label(
            frame,
            text=f"{config['icon']} {title}",
            font=cls.FONTS['body'],
            bg=cls.COLORS['secondary_bg'],
            fg=config['color']
        )
        indicator_label.pack(pady=cls.SPACING['sm'])
        
        return frame, indicator_label
    
    @classmethod
    def create_professional_table(cls, parent, columns, height=8):
        """Create professional data table"""
        # Create frame for table and scrollbar
        table_frame = tk.Frame(parent, bg=cls.COLORS['primary_bg'])
        
        # Create treeview
        tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=height)
        
        # Configure columns
        column_widths = {
            'Symbol': 80, 'Type': 60, 'Volume': 80, 'Price': 100, 
            'PnL': 100, 'Status': 80, 'Time': 120, 'Action': 80
        }
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=column_widths.get(col, 100), anchor='center')
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack table and scrollbar
        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        return table_frame, tree, scrollbar
    
    @classmethod
    def create_section_header(cls, parent, title, subtitle=""):
        """Create section header"""
        header_frame = tk.Frame(parent, bg=cls.COLORS['primary_bg'])
        
        title_label = tk.Label(
            header_frame,
            text=title,
            font=cls.FONTS['subheader'],
            bg=cls.COLORS['primary_bg'],
            fg=cls.COLORS['text_primary']
        )
        title_label.pack(anchor='w')
        
        if subtitle:
            subtitle_label = tk.Label(
                header_frame,
                text=subtitle,
                font=cls.FONTS['small'],
                bg=cls.COLORS['primary_bg'],
                fg=cls.COLORS['text_secondary']
            )
            subtitle_label.pack(anchor='w')
        
        return header_frame
    
    @classmethod
    def format_currency(cls, value, show_sign=True):
        """Format currency value with proper color"""
        if value is None:
            return "$0.00"
        
        formatted = f"${abs(value):,.2f}"
        if show_sign and value != 0:
            formatted = f"{'+' if value > 0 else '-'}{formatted}"
        
        return formatted
    
    @classmethod
    def format_percentage(cls, value, show_sign=True):
        """Format percentage value"""
        if value is None:
            return "0.00%"
        
        formatted = f"{abs(value):.2f}%"
        if show_sign and value != 0:
            formatted = f"{'+' if value > 0 else '-'}{formatted}"
        
        return formatted
    
    @classmethod
    def get_pnl_color(cls, value):
        """Get color for PnL value"""
        if value is None or value == 0:
            return cls.COLORS['text_primary']
        return cls.COLORS['success'] if value > 0 else cls.COLORS['danger']
    
    @classmethod
    def get_position_type_color(cls, position_type):
        """Get color for position type"""
        if position_type.upper() == 'BUY':
            return cls.COLORS['buy_color']
        elif position_type.upper() == 'SELL':
            return cls.COLORS['sell_color']
        else:
            return cls.COLORS['neutral_color']
