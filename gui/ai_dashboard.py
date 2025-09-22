"""
แดชบอร์ด AI สำหรับระบบเทรด
============================

ไฟล์นี้ทำหน้าที่:
- แสดงสถานะและประสิทธิภาพของ AI Engine
- แสดงข้อมูล Rule Engine และ Learning Module
- แสดงกราฟและสถิติการทำงานของ AI
- ควบคุมและปรับแต่งพารามิเตอร์ AI
- แสดงการวิเคราะห์ตลาดและรูปแบบ

Author: AI Trading System
Version: 1.0
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from datetime import datetime, timedelta
import json

class AIDashboard:
    """
    แดชบอร์ด AI หลัก
    
    แสดงข้อมูลและควบคุม AI Engine ผ่าน GUI
    รวมถึงการติดตามประสิทธิภาพและการวิเคราะห์
    """
    
    def __init__(self, parent, ai_engine, learning_module):
        """
        เริ่มต้นแดชบอร์ด AI
        
        Args:
            parent: หน้าต่างหลัก
            ai_engine: ระบบ AI Engine
            learning_module: ระบบการเรียนรู้
        """
        self.parent = parent
        self.ai_engine = ai_engine
        self.learning_module = learning_module
        
        # Create dashboard window
        self.dashboard_window = tk.Toplevel(parent)
        self.dashboard_window.title("AI Dashboard")
        self.dashboard_window.geometry("1200x800")
        self.dashboard_window.configure(bg='#2b2b2b')
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        """
        ตั้งค่าอินเทอร์เฟซแดชบอร์ด AI
        
        สร้างแท็บต่างๆ สำหรับแสดงข้อมูล AI:
        - Rule Engine
        - Learning Module
        - Performance
        - Market Analysis
        """
        # Create main container
        main_container = ttk.Frame(self.dashboard_window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_container)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Rule Engine tab
        self.create_rule_engine_tab(notebook)
        
        # Learning Module tab
        self.create_learning_tab(notebook)
        
        # Performance tab
        self.create_performance_tab(notebook)
        
        # Market Analysis tab
        self.create_market_analysis_tab(notebook)
        
    def create_rule_engine_tab(self, notebook):
        """
        สร้างแท็บติดตาม Rule Engine
        
        แสดงสถานะและประสิทธิภาพของกฎเกณฑ์ต่างๆ
        """
        rule_frame = ttk.Frame(notebook)
        notebook.add(rule_frame, text="Rule Engine")
        
        # Rule statistics
        stats_frame = ttk.LabelFrame(rule_frame, text="Rule Statistics")
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Rule count
        ttk.Label(stats_frame, text="Total Rules:").grid(row=0, column=0, padx=5, pady=5)
        self.total_rules_label = ttk.Label(stats_frame, text="0")
        self.total_rules_label.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(stats_frame, text="Fired Rules:").grid(row=0, column=2, padx=5, pady=5)
        self.fired_rules_label = ttk.Label(stats_frame, text="0")
        self.fired_rules_label.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(stats_frame, text="Total Fires:").grid(row=0, column=4, padx=5, pady=5)
        self.total_fires_label = ttk.Label(stats_frame, text="0")
        self.total_fires_label.grid(row=0, column=5, padx=5, pady=5)
        
        # Rule performance table
        performance_frame = ttk.LabelFrame(rule_frame, text="Rule Performance")
        performance_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create treeview for rule performance
        columns = ('Rule ID', 'Name', 'Category', 'Success Rate', 'Total PnL', 'Fires')
        self.rule_performance_tree = ttk.Treeview(performance_frame, columns=columns, show='headings')
        
        for col in columns:
            self.rule_performance_tree.heading(col, text=col)
            self.rule_performance_tree.column(col, width=120)
        
        self.rule_performance_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Refresh button
        ttk.Button(performance_frame, text="Refresh", 
                  command=self.refresh_rule_performance).pack(pady=5)
        
    def create_learning_tab(self, notebook):
        """
        สร้างแท็บ Learning Module
        
        แสดงข้อมูลการเรียนรู้และรูปแบบที่พบ
        """
        learning_frame = ttk.Frame(notebook)
        notebook.add(learning_frame, text="Learning Module")
        
        # Learning statistics
        stats_frame = ttk.LabelFrame(learning_frame, text="Learning Statistics")
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(stats_frame, text="Performance Records:").grid(row=0, column=0, padx=5, pady=5)
        self.performance_records_label = ttk.Label(stats_frame, text="0")
        self.performance_records_label.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(stats_frame, text="Arbitrage Opportunities:").grid(row=0, column=2, padx=5, pady=5)
        self.arbitrage_opportunities_label = ttk.Label(stats_frame, text="0")
        self.arbitrage_opportunities_label.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(stats_frame, text="Market Patterns:").grid(row=0, column=4, padx=5, pady=5)
        self.market_patterns_label = ttk.Label(stats_frame, text="0")
        self.market_patterns_label.grid(row=0, column=5, padx=5, pady=5)
        
        # Learning controls
        controls_frame = ttk.LabelFrame(learning_frame, text="Learning Controls")
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(controls_frame, text="Train Arbitrage Classifier", 
                  command=self.train_classifier).pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Button(controls_frame, text="Identify Patterns", 
                  command=self.identify_patterns).pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Button(controls_frame, text="Optimize Rules", 
                  command=self.optimize_rules).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Pattern display
        pattern_frame = ttk.LabelFrame(learning_frame, text="Identified Patterns")
        pattern_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.pattern_text = tk.Text(pattern_frame, height=15, bg='#1e1e1e', fg='#ffffff')
        self.pattern_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def create_performance_tab(self, notebook):
        """
        สร้างแท็บติดตามประสิทธิภาพ
        
        แสดงกราฟและสถิติการทำงานของ AI
        """
        performance_frame = ttk.Frame(notebook)
        notebook.add(performance_frame, text="Performance")
        
        # Performance metrics
        metrics_frame = ttk.LabelFrame(performance_frame, text="Performance Metrics")
        metrics_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create performance labels
        metrics = [
            ("Total Trades", "total_trades"),
            ("Winning Trades", "winning_trades"),
            ("Losing Trades", "losing_trades"),
            ("Win Rate", "win_rate"),
            ("Average Win", "average_win"),
            ("Average Loss", "average_loss"),
            ("Profit Factor", "profit_factor"),
            ("Max Drawdown", "max_drawdown")
        ]
        
        self.performance_labels = {}
        for i, (label_text, key) in enumerate(metrics):
            row = i // 4
            col = (i % 4) * 2
            
            ttk.Label(metrics_frame, text=f"{label_text}:").grid(row=row, column=col, padx=5, pady=5, sticky="w")
            self.performance_labels[key] = ttk.Label(metrics_frame, text="0")
            self.performance_labels[key].grid(row=row, column=col+1, padx=5, pady=5, sticky="w")
        
        # Performance chart
        chart_frame = ttk.LabelFrame(performance_frame, text="Performance Chart")
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create matplotlib figure
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initialize empty chart
        self.update_performance_chart()
        
    def create_market_analysis_tab(self, notebook):
        """
        สร้างแท็บการวิเคราะห์ตลาด
        
        แสดงการวิเคราะห์ตลาดและรูปแบบที่ AI ระบุ
        """
        analysis_frame = ttk.Frame(notebook)
        notebook.add(analysis_frame, text="Market Analysis")
        
        # Market conditions
        conditions_frame = ttk.LabelFrame(analysis_frame, text="Current Market Conditions")
        conditions_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.market_conditions_text = tk.Text(conditions_frame, height=8, bg='#1e1e1e', fg='#ffffff')
        self.market_conditions_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Market analysis chart
        chart_frame = ttk.LabelFrame(analysis_frame, text="Market Analysis Chart")
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create matplotlib figure for market analysis
        self.market_fig, self.market_ax = plt.subplots(figsize=(10, 6))
        self.market_canvas = FigureCanvasTkAgg(self.market_fig, chart_frame)
        self.market_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initialize empty chart
        self.update_market_analysis_chart()
        
    def refresh_rule_performance(self):
        """Refresh rule performance data"""
        try:
            if not self.ai_engine:
                return
            
            # Get rule statistics
            stats = self.ai_engine.get_rule_statistics()
            
            self.total_rules_label.config(text=str(stats.get('total_rules', 0)))
            self.fired_rules_label.config(text=str(stats.get('fired_rules', 0)))
            self.total_fires_label.config(text=str(stats.get('total_fires', 0)))
            
            # Get rule performance data
            performance_data = self.ai_engine.get_rule_performance()
            
            # Clear existing items
            for item in self.rule_performance_tree.get_children():
                self.rule_performance_tree.delete(item)
            
            # Add performance data
            for rule_id, data in performance_data.items():
                success_count = data.get('success_count', 0)
                failure_count = data.get('failure_count', 0)
                total_trades = success_count + failure_count
                success_rate = (success_count / total_trades * 100) if total_trades > 0 else 0
                total_pnl = data.get('total_pnl', 0)
                fires = data.get('success_count', 0) + data.get('failure_count', 0)
                
                self.rule_performance_tree.insert("", "end", values=(
                    rule_id,
                    f"Rule {rule_id}",
                    "Unknown",
                    f"{success_rate:.1f}%",
                    f"${total_pnl:.2f}",
                    str(fires)
                ))
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh rule performance: {str(e)}")
    
    def train_classifier(self):
        """Train arbitrage classifier"""
        try:
            if not self.learning_module:
                messagebox.showerror("Error", "Learning module not available")
                return
            
            result = self.learning_module.train_arbitrage_classifier(days=30)
            
            if 'error' in result:
                messagebox.showerror("Error", result['error'])
            else:
                messagebox.showinfo("Success", f"Classifier trained successfully!\n"
                                             f"Test Accuracy: {result.get('test_accuracy', 0):.2f}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to train classifier: {str(e)}")
    
    def identify_patterns(self):
        """Identify market patterns"""
        try:
            if not self.learning_module:
                messagebox.showerror("Error", "Learning module not available")
                return
            
            patterns = self.learning_module.identify_market_patterns(days=7)
            
            if 'error' in patterns:
                messagebox.showerror("Error", patterns['error'])
            else:
                # Display patterns
                self.pattern_text.delete(1.0, tk.END)
                
                if patterns.get('patterns'):
                    for i, pattern in enumerate(patterns['patterns']):
                        self.pattern_text.insert(tk.END, f"Pattern {i+1}:\n")
                        self.pattern_text.insert(tk.END, f"  Success Rate: {pattern.get('success_rate', 0):.2f}\n")
                        self.pattern_text.insert(tk.END, f"  Avg Arbitrage: {pattern.get('avg_arbitrage_percent', 0):.2f}%\n")
                        self.pattern_text.insert(tk.END, f"  Avg Volatility: {pattern.get('avg_volatility', 0):.2f}\n")
                        self.pattern_text.insert(tk.END, f"  Sample Size: {pattern.get('sample_size', 0)}\n")
                        self.pattern_text.insert(tk.END, f"  Characteristics: {pattern.get('characteristics', {})}\n\n")
                else:
                    self.pattern_text.insert(tk.END, "No patterns identified")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to identify patterns: {str(e)}")
    
    def optimize_rules(self):
        """Optimize rule parameters"""
        try:
            if not self.learning_module:
                messagebox.showerror("Error", "Learning module not available")
                return
            
            # Get list of rules to optimize
            if hasattr(self.ai_engine, 'rules'):
                rule_ids = [rule.get('id') for rule in self.ai_engine.rules if rule.get('id')]
            else:
                rule_ids = ['AD-001', 'AD-002', 'AD-003']  # Default rule IDs
            
            optimization_results = []
            
            for rule_id in rule_ids[:3]:  # Optimize first 3 rules
                result = self.learning_module.optimize_rule_parameters(rule_id, days=30)
                if 'error' not in result:
                    optimization_results.append(f"Rule {rule_id}: {result}")
            
            if optimization_results:
                messagebox.showinfo("Optimization Complete", 
                                  "Rule optimization completed:\n\n" + "\n".join(optimization_results))
            else:
                messagebox.showinfo("Optimization Complete", "No rules could be optimized")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to optimize rules: {str(e)}")
    
    def update_performance_chart(self):
        """Update performance chart"""
        try:
            self.ax.clear()
            
            # Generate sample performance data
            dates = [datetime.now() - timedelta(days=i) for i in range(30, 0, -1)]
            pnl_values = np.cumsum(np.random.normal(10, 50, 30))
            
            # Plot cumulative PnL
            self.ax.plot(dates, pnl_values, 'b-', linewidth=2, label='Cumulative PnL')
            self.ax.axhline(y=0, color='r', linestyle='--', alpha=0.5)
            
            self.ax.set_title('Cumulative PnL Over Time')
            self.ax.set_xlabel('Date')
            self.ax.set_ylabel('PnL ($)')
            self.ax.legend()
            self.ax.grid(True, alpha=0.3)
            
            # Format x-axis
            self.ax.tick_params(axis='x', rotation=45)
            
            self.canvas.draw()
            
        except Exception as e:
            print(f"Error updating performance chart: {e}")
    
    def update_market_analysis_chart(self):
        """Update market analysis chart"""
        try:
            self.market_ax.clear()
            
            # Generate sample market data
            symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD']
            volatilities = np.random.uniform(0.2, 1.5, len(symbols))
            trends = np.random.choice(['Bullish', 'Bearish', 'Sideways'], len(symbols))
            
            # Create bar chart
            colors = ['green' if t == 'Bullish' else 'red' if t == 'Bearish' else 'gray' for t in trends]
            bars = self.market_ax.bar(symbols, volatilities, color=colors, alpha=0.7)
            
            self.market_ax.set_title('Market Volatility by Symbol')
            self.market_ax.set_xlabel('Symbol')
            self.market_ax.set_ylabel('Volatility')
            self.market_ax.grid(True, alpha=0.3)
            
            # Add value labels on bars
            for bar, vol in zip(bars, volatilities):
                height = bar.get_height()
                self.market_ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                                  f'{vol:.2f}', ha='center', va='bottom')
            
            self.market_canvas.draw()
            
        except Exception as e:
            print(f"Error updating market analysis chart: {e}")
    
    def update_dashboard(self):
        """Update all dashboard data"""
        try:
            # Update learning statistics
            if self.learning_module:
                summary = self.learning_module.get_learning_summary()
                self.performance_records_label.config(text=str(summary.get('rule_performance_records', 0)))
                self.arbitrage_opportunities_label.config(text=str(summary.get('arbitrage_opportunities', 0)))
                self.market_patterns_label.config(text=str(summary.get('market_patterns', 0)))
            
            # Update performance metrics
            if hasattr(self.ai_engine, 'get_rule_performance'):
                performance_data = self.ai_engine.get_rule_performance()
                
                # Calculate overall performance
                total_trades = 0
                winning_trades = 0
                total_pnl = 0
                
                for rule_data in performance_data.values():
                    total_trades += rule_data.get('success_count', 0) + rule_data.get('failure_count', 0)
                    winning_trades += rule_data.get('success_count', 0)
                    total_pnl += rule_data.get('total_pnl', 0)
                
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                
                self.performance_labels['total_trades'].config(text=str(total_trades))
                self.performance_labels['winning_trades'].config(text=str(winning_trades))
                self.performance_labels['losing_trades'].config(text=str(total_trades - winning_trades))
                self.performance_labels['win_rate'].config(text=f"{win_rate:.1f}%")
                self.performance_labels['average_win'].config(text="$0.00")  # Placeholder
                self.performance_labels['average_loss'].config(text="$0.00")  # Placeholder
                self.performance_labels['profit_factor'].config(text="1.00")  # Placeholder
                self.performance_labels['max_drawdown'].config(text="$0.00")  # Placeholder
            
            # Update charts
            self.update_performance_chart()
            self.update_market_analysis_chart()
            
        except Exception as e:
            print(f"Error updating dashboard: {e}")
    
    def show(self):
        """Show the dashboard window"""
        self.dashboard_window.deiconify()
        self.dashboard_window.lift()
        self.update_dashboard()
