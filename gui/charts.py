import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import threading
import time

class RealTimeCharts:
    def __init__(self, parent, broker_api):
        self.parent = parent
        self.broker_api = broker_api
        self.is_running = False
        self.update_thread = None
        
        # Create charts window
        self.charts_window = tk.Toplevel(parent)
        self.charts_window.title("Real-time Charts")
        self.charts_window.geometry("1400x800")
        self.charts_window.configure(bg='#2b2b2b')
        
        # Chart data
        self.price_data = {}
        self.arbitrage_data = {}
        self.performance_data = []
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the charts interface"""
        # Create main container
        main_container = ttk.Frame(self.charts_window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create control panel
        self.create_control_panel(main_container)
        
        # Create notebook for different chart types
        notebook = ttk.Notebook(main_container)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Price charts tab
        self.create_price_charts_tab(notebook)
        
        # Arbitrage opportunities tab
        self.create_arbitrage_charts_tab(notebook)
        
        # Performance charts tab
        self.create_performance_charts_tab(notebook)
        
        # Market analysis tab
        self.create_market_analysis_tab(notebook)
        
    def create_control_panel(self, parent):
        """Create control panel for charts"""
        control_frame = ttk.LabelFrame(parent, text="Chart Controls")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Symbol selection
        ttk.Label(control_frame, text="Symbol:").pack(side=tk.LEFT, padx=5, pady=5)
        self.symbol_var = tk.StringVar(value="EURUSD")
        symbol_combo = ttk.Combobox(control_frame, textvariable=self.symbol_var, 
                                  values=["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"], 
                                  width=10)
        symbol_combo.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Timeframe selection
        ttk.Label(control_frame, text="Timeframe:").pack(side=tk.LEFT, padx=5, pady=5)
        self.timeframe_var = tk.StringVar(value="M1")
        timeframe_combo = ttk.Combobox(control_frame, textvariable=self.timeframe_var,
                                     values=["M1", "M5", "M15", "M30", "H1"], width=5)
        timeframe_combo.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Update controls
        ttk.Button(control_frame, text="Start Updates", 
                  command=self.start_updates).pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Button(control_frame, text="Stop Updates", 
                  command=self.stop_updates).pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Button(control_frame, text="Clear Data", 
                  command=self.clear_data).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Status label
        self.status_label = ttk.Label(control_frame, text="Stopped")
        self.status_label.pack(side=tk.RIGHT, padx=5, pady=5)
        
    def create_price_charts_tab(self, notebook):
        """Create price charts tab"""
        price_frame = ttk.Frame(notebook)
        notebook.add(price_frame, text="Price Charts")
        
        # Create matplotlib figure
        self.price_fig, (self.price_ax1, self.price_ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Configure subplots
        self.price_ax1.set_title('Price Chart')
        self.price_ax1.set_ylabel('Price')
        self.price_ax1.grid(True, alpha=0.3)
        
        self.price_ax2.set_title('Volume')
        self.price_ax2.set_xlabel('Time')
        self.price_ax2.set_ylabel('Volume')
        self.price_ax2.grid(True, alpha=0.3)
        
        # Create canvas
        self.price_canvas = FigureCanvasTkAgg(self.price_fig, price_frame)
        self.price_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_arbitrage_charts_tab(self, notebook):
        """Create arbitrage opportunities charts tab"""
        arbitrage_frame = ttk.Frame(notebook)
        notebook.add(arbitrage_frame, text="Arbitrage Opportunities")
        
        # Create matplotlib figure
        self.arbitrage_fig, (self.arbitrage_ax1, self.arbitrage_ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Configure subplots
        self.arbitrage_ax1.set_title('Arbitrage Opportunities Over Time')
        self.arbitrage_ax1.set_ylabel('Arbitrage %')
        self.arbitrage_ax1.grid(True, alpha=0.3)
        
        self.arbitrage_ax2.set_title('Arbitrage Distribution')
        self.arbitrage_ax2.set_xlabel('Arbitrage %')
        self.arbitrage_ax2.set_ylabel('Frequency')
        self.arbitrage_ax2.grid(True, alpha=0.3)
        
        # Create canvas
        self.arbitrage_canvas = FigureCanvasTkAgg(self.arbitrage_fig, arbitrage_frame)
        self.arbitrage_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_performance_charts_tab(self, notebook):
        """Create performance charts tab"""
        performance_frame = ttk.Frame(notebook)
        notebook.add(performance_frame, text="Performance")
        
        # Create matplotlib figure
        self.performance_fig, (self.performance_ax1, self.performance_ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Configure subplots
        self.performance_ax1.set_title('Cumulative PnL')
        self.performance_ax1.set_ylabel('PnL ($)')
        self.performance_ax1.grid(True, alpha=0.3)
        
        self.performance_ax2.set_title('Drawdown')
        self.performance_ax2.set_xlabel('Time')
        self.performance_ax2.set_ylabel('Drawdown ($)')
        self.performance_ax2.grid(True, alpha=0.3)
        
        # Create canvas
        self.performance_canvas = FigureCanvasTkAgg(self.performance_fig, performance_frame)
        self.performance_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_market_analysis_tab(self, notebook):
        """Create market analysis charts tab"""
        analysis_frame = ttk.Frame(notebook)
        notebook.add(analysis_frame, text="Market Analysis")
        
        # Create matplotlib figure
        self.analysis_fig, ((self.analysis_ax1, self.analysis_ax2), 
                           (self.analysis_ax3, self.analysis_ax4)) = plt.subplots(2, 2, figsize=(12, 8))
        
        # Configure subplots
        self.analysis_ax1.set_title('Volatility by Symbol')
        self.analysis_ax1.set_ylabel('Volatility')
        
        self.analysis_ax2.set_title('Trend Distribution')
        self.analysis_ax2.set_ylabel('Count')
        
        self.analysis_ax3.set_title('Correlation Matrix')
        
        self.analysis_ax4.set_title('Market Sentiment')
        self.analysis_ax4.set_ylabel('Sentiment Score')
        
        # Create canvas
        self.analysis_canvas = FigureCanvasTkAgg(self.analysis_fig, analysis_frame)
        self.analysis_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def start_updates(self):
        """Start real-time chart updates"""
        if self.is_running:
            return
        
        self.is_running = True
        self.status_label.config(text="Running")
        
        # Start update thread
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        
    def stop_updates(self):
        """Stop real-time chart updates"""
        self.is_running = False
        self.status_label.config(text="Stopped")
        
    def clear_data(self):
        """Clear all chart data"""
        self.price_data.clear()
        self.arbitrage_data.clear()
        self.performance_data.clear()
        
        # Clear all charts
        self.update_price_charts()
        self.update_arbitrage_charts()
        self.update_performance_charts()
        self.update_market_analysis_charts()
        
    def _update_loop(self):
        """Main update loop for charts"""
        while self.is_running:
            try:
                # Update all charts
                self.update_price_charts()
                self.update_arbitrage_charts()
                self.update_performance_charts()
                self.update_market_analysis_charts()
                
                # Sleep for 1 second
                time.sleep(1)
                
            except Exception as e:
                print(f"Chart update error: {e}")
                time.sleep(5)
    
    def update_price_charts(self):
        """Update price charts"""
        try:
            symbol = self.symbol_var.get()
            timeframe = self.timeframe_var.get()
            
            # Get historical data
            data = self.broker_api.get_historical_data(symbol, timeframe, 100)
            
            if data is None or len(data) < 10:
                return
            
            # Clear previous plots
            self.price_ax1.clear()
            self.price_ax2.clear()
            
            # Plot price data
            self.price_ax1.plot(data.index, data['close'], 'b-', linewidth=1, label='Close')
            self.price_ax1.plot(data.index, data['high'], 'g-', alpha=0.3, linewidth=0.5, label='High')
            self.price_ax1.plot(data.index, data['low'], 'r-', alpha=0.3, linewidth=0.5, label='Low')
            
            # Add moving averages
            if len(data) >= 20:
                sma_20 = data['close'].rolling(20).mean()
                self.price_ax1.plot(data.index, sma_20, 'orange', linewidth=1, label='SMA 20')
            
            self.price_ax1.set_title(f'{symbol} - {timeframe} Price Chart')
            self.price_ax1.set_ylabel('Price')
            self.price_ax1.legend()
            self.price_ax1.grid(True, alpha=0.3)
            
            # Plot volume if available
            if 'volume' in data.columns:
                self.price_ax2.bar(data.index, data['volume'], alpha=0.7, color='blue')
                self.price_ax2.set_title('Volume')
                self.price_ax2.set_ylabel('Volume')
            else:
                self.price_ax2.text(0.5, 0.5, 'Volume data not available', 
                                  ha='center', va='center', transform=self.price_ax2.transAxes)
            
            self.price_ax2.set_xlabel('Time')
            self.price_ax2.grid(True, alpha=0.3)
            
            # Format x-axis
            self.price_ax1.tick_params(axis='x', rotation=45)
            self.price_ax2.tick_params(axis='x', rotation=45)
            
            self.price_canvas.draw()
            
        except Exception as e:
            print(f"Error updating price charts: {e}")
    
    def update_arbitrage_charts(self):
        """Update arbitrage opportunity charts"""
        try:
            # Generate sample arbitrage data
            if not self.arbitrage_data:
                # Initialize with sample data
                times = [datetime.now() - timedelta(minutes=i) for i in range(60, 0, -1)]
                arbitrage_values = np.random.normal(0.1, 0.2, 60)
                self.arbitrage_data = {'times': times, 'values': arbitrage_values.tolist()}
            else:
                # Add new data point
                new_time = datetime.now()
                new_value = np.random.normal(0.1, 0.2)
                self.arbitrage_data['times'].append(new_time)
                self.arbitrage_data['values'].append(new_value)
                
                # Keep only last 100 points
                if len(self.arbitrage_data['times']) > 100:
                    self.arbitrage_data['times'] = self.arbitrage_data['times'][-100:]
                    self.arbitrage_data['values'] = self.arbitrage_data['values'][-100:]
            
            # Clear previous plots
            self.arbitrage_ax1.clear()
            self.arbitrage_ax2.clear()
            
            # Plot arbitrage opportunities over time
            self.arbitrage_ax1.plot(self.arbitrage_data['times'], self.arbitrage_data['values'], 
                                  'b-', linewidth=1, alpha=0.7)
            self.arbitrage_ax1.axhline(y=0, color='r', linestyle='--', alpha=0.5)
            self.arbitrage_ax1.axhline(y=0.3, color='g', linestyle='--', alpha=0.5, label='Threshold')
            
            self.arbitrage_ax1.set_title('Arbitrage Opportunities Over Time')
            self.arbitrage_ax1.set_ylabel('Arbitrage %')
            self.arbitrage_ax1.legend()
            self.arbitrage_ax1.grid(True, alpha=0.3)
            
            # Plot arbitrage distribution
            values = np.array(self.arbitrage_data['values'])
            self.arbitrage_ax2.hist(values, bins=20, alpha=0.7, color='blue', edgecolor='black')
            self.arbitrage_ax2.axvline(x=0, color='r', linestyle='--', alpha=0.5)
            self.arbitrage_ax2.axvline(x=0.3, color='g', linestyle='--', alpha=0.5, label='Threshold')
            
            self.arbitrage_ax2.set_title('Arbitrage Distribution')
            self.arbitrage_ax2.set_xlabel('Arbitrage %')
            self.arbitrage_ax2.set_ylabel('Frequency')
            self.arbitrage_ax2.legend()
            self.arbitrage_ax2.grid(True, alpha=0.3)
            
            # Format x-axis
            self.arbitrage_ax1.tick_params(axis='x', rotation=45)
            
            self.arbitrage_canvas.draw()
            
        except Exception as e:
            print(f"Error updating arbitrage charts: {e}")
    
    def update_performance_charts(self):
        """Update performance charts"""
        try:
            # Generate sample performance data
            if not self.performance_data:
                # Initialize with sample data
                times = [datetime.now() - timedelta(hours=i) for i in range(24, 0, -1)]
                pnl_values = np.cumsum(np.random.normal(10, 50, 24))
                self.performance_data = {'times': times, 'pnl': pnl_values.tolist()}
            else:
                # Add new data point
                new_time = datetime.now()
                new_pnl = self.performance_data['pnl'][-1] + np.random.normal(10, 50)
                self.performance_data['times'].append(new_time)
                self.performance_data['pnl'].append(new_pnl)
                
                # Keep only last 100 points
                if len(self.performance_data['times']) > 100:
                    self.performance_data['times'] = self.performance_data['times'][-100:]
                    self.performance_data['pnl'] = self.performance_data['pnl'][-100:]
            
            # Clear previous plots
            self.performance_ax1.clear()
            self.performance_ax2.clear()
            
            # Plot cumulative PnL
            pnl_array = np.array(self.performance_data['pnl'])
            self.performance_ax1.plot(self.performance_data['times'], pnl_array, 
                                    'b-', linewidth=2, label='Cumulative PnL')
            self.performance_ax1.axhline(y=0, color='r', linestyle='--', alpha=0.5)
            
            self.performance_ax1.set_title('Cumulative PnL')
            self.performance_ax1.set_ylabel('PnL ($)')
            self.performance_ax1.legend()
            self.performance_ax1.grid(True, alpha=0.3)
            
            # Plot drawdown
            running_max = np.maximum.accumulate(pnl_array)
            drawdown = running_max - pnl_array
            self.performance_ax2.fill_between(self.performance_data['times'], drawdown, 0, 
                                            alpha=0.3, color='red', label='Drawdown')
            self.performance_ax2.plot(self.performance_data['times'], drawdown, 'r-', linewidth=1)
            
            self.performance_ax2.set_title('Drawdown')
            self.performance_ax2.set_xlabel('Time')
            self.performance_ax2.set_ylabel('Drawdown ($)')
            self.performance_ax2.legend()
            self.performance_ax2.grid(True, alpha=0.3)
            
            # Format x-axis
            self.performance_ax1.tick_params(axis='x', rotation=45)
            self.performance_ax2.tick_params(axis='x', rotation=45)
            
            self.performance_canvas.draw()
            
        except Exception as e:
            print(f"Error updating performance charts: {e}")
    
    def update_market_analysis_charts(self):
        """Update market analysis charts"""
        try:
            # Clear previous plots
            self.analysis_ax1.clear()
            self.analysis_ax2.clear()
            self.analysis_ax3.clear()
            self.analysis_ax4.clear()
            
            # Generate sample data
            symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD']
            volatilities = np.random.uniform(0.2, 1.5, len(symbols))
            trends = np.random.choice(['Bullish', 'Bearish', 'Sideways'], len(symbols))
            
            # Volatility by symbol
            colors = ['green' if t == 'Bullish' else 'red' if t == 'Bearish' else 'gray' for t in trends]
            bars = self.analysis_ax1.bar(symbols, volatilities, color=colors, alpha=0.7)
            self.analysis_ax1.set_title('Volatility by Symbol')
            self.analysis_ax1.set_ylabel('Volatility')
            self.analysis_ax1.tick_params(axis='x', rotation=45)
            
            # Add value labels
            for bar, vol in zip(bars, volatilities):
                height = bar.get_height()
                self.analysis_ax1.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                                     f'{vol:.2f}', ha='center', va='bottom')
            
            # Trend distribution
            trend_counts = {'Bullish': trends.tolist().count('Bullish'),
                          'Bearish': trends.tolist().count('Bearish'),
                          'Sideways': trends.tolist().count('Sideways')}
            
            self.analysis_ax2.bar(trend_counts.keys(), trend_counts.values(), 
                                color=['green', 'red', 'gray'], alpha=0.7)
            self.analysis_ax2.set_title('Trend Distribution')
            self.analysis_ax2.set_ylabel('Count')
            
            # Correlation matrix (simplified)
            correlation_data = np.random.uniform(-1, 1, (len(symbols), len(symbols)))
            np.fill_diagonal(correlation_data, 1)
            
            im = self.analysis_ax3.imshow(correlation_data, cmap='coolwarm', vmin=-1, vmax=1)
            self.analysis_ax3.set_xticks(range(len(symbols)))
            self.analysis_ax3.set_yticks(range(len(symbols)))
            self.analysis_ax3.set_xticklabels(symbols, rotation=45)
            self.analysis_ax3.set_yticklabels(symbols)
            self.analysis_ax3.set_title('Correlation Matrix')
            
            # Add colorbar
            self.analysis_fig.colorbar(im, ax=self.analysis_ax3, shrink=0.8)
            
            # Market sentiment over time
            times = [datetime.now() - timedelta(hours=i) for i in range(12, 0, -1)]
            sentiment_scores = np.random.uniform(-1, 1, 12)
            
            self.analysis_ax4.plot(times, sentiment_scores, 'b-', linewidth=2, marker='o')
            self.analysis_ax4.axhline(y=0, color='r', linestyle='--', alpha=0.5)
            self.analysis_ax4.fill_between(times, sentiment_scores, 0, 
                                         where=(np.array(sentiment_scores) >= 0), 
                                         alpha=0.3, color='green', label='Positive')
            self.analysis_ax4.fill_between(times, sentiment_scores, 0, 
                                         where=(np.array(sentiment_scores) < 0), 
                                         alpha=0.3, color='red', label='Negative')
            
            self.analysis_ax4.set_title('Market Sentiment Over Time')
            self.analysis_ax4.set_ylabel('Sentiment Score')
            self.analysis_ax4.set_xlabel('Time')
            self.analysis_ax4.legend()
            self.analysis_ax4.tick_params(axis='x', rotation=45)
            self.analysis_ax4.grid(True, alpha=0.3)
            
            self.analysis_canvas.draw()
            
        except Exception as e:
            print(f"Error updating market analysis charts: {e}")
    
    def show(self):
        """Show the charts window"""
        self.charts_window.deiconify()
        self.charts_window.lift()
    
    def close(self):
        """Close the charts window"""
        self.stop_updates()
        self.charts_window.destroy()
