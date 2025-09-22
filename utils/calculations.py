"""
ระบบคำนวณทางการเทรดและเทคนิคอลอินดิเคเตอร์

ไฟล์นี้ทำหน้าที่:
- คำนวณ Triangular Arbitrage Percentage
- คำนวณ Correlation ระหว่างคู่เงิน
- คำนวณ Technical Indicators (RSI, MACD, Bollinger Bands)
- คำนวณ Risk Management (Position Size, Drawdown)
- คำนวณ Performance Metrics (Sharpe Ratio, Win Rate)

ฟีเจอร์หลัก:
- Arbitrage Calculations: คำนวณโอกาส Arbitrage
- Technical Analysis: วิเคราะห์เทคนิคอล
- Risk Calculations: คำนวณความเสี่ยง
- Performance Metrics: คำนวณผลการดำเนินงาน
- Statistical Analysis: วิเคราะห์ทางสถิติ
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import math

class TradingCalculations:
    """Utility class for trading calculations"""
    
    @staticmethod
    def calculate_arbitrage_percentage(pair1_price: float, pair2_price: float, 
                                     pair3_price: float) -> float:
        """Calculate triangular arbitrage percentage"""
        try:
            if pair1_price <= 0 or pair2_price <= 0 or pair3_price <= 0:
                return 0.0
            
            # Calculate theoretical price
            theoretical_price = pair1_price * pair2_price
            
            # Calculate arbitrage percentage
            arbitrage_percent = (pair3_price - theoretical_price) / theoretical_price * 100
            
            return arbitrage_percent
            
        except Exception:
            return 0.0
    
    @staticmethod
    def calculate_correlation(prices1: List[float], prices2: List[float]) -> float:
        """Calculate correlation between two price series"""
        try:
            if len(prices1) != len(prices2) or len(prices1) < 2:
                return 0.0
            
            # Convert to numpy arrays
            arr1 = np.array(prices1)
            arr2 = np.array(prices2)
            
            # Calculate returns
            returns1 = np.diff(arr1) / arr1[:-1]
            returns2 = np.diff(arr2) / arr2[:-1]
            
            # Calculate correlation
            correlation = np.corrcoef(returns1, returns2)[0, 1]
            
            return correlation if not np.isnan(correlation) else 0.0
            
        except Exception:
            return 0.0
    
    @staticmethod
    def calculate_volatility(prices: List[float], period: int = 20) -> float:
        """Calculate volatility (standard deviation of returns)"""
        try:
            if len(prices) < 2:
                return 0.0
            
            # Convert to numpy array
            arr = np.array(prices)
            
            # Calculate returns
            returns = np.diff(arr) / arr[:-1]
            
            # Calculate rolling volatility if period is specified
            if period > 0 and len(returns) >= period:
                returns = returns[-period:]
            
            # Calculate standard deviation
            volatility = np.std(returns) * 100  # Return as percentage
            
            return volatility
            
        except Exception:
            return 0.0
    
    @staticmethod
    def calculate_moving_average(prices: List[float], period: int) -> List[float]:
        """Calculate simple moving average"""
        try:
            if len(prices) < period:
                return []
            
            # Convert to pandas Series for easy calculation
            series = pd.Series(prices)
            ma = series.rolling(window=period).mean()
            
            return ma.tolist()
            
        except Exception:
            return []
    
    @staticmethod
    def calculate_exponential_moving_average(prices: List[float], period: int) -> List[float]:
        """Calculate exponential moving average"""
        try:
            if len(prices) < period:
                return []
            
            # Convert to pandas Series
            series = pd.Series(prices)
            ema = series.ewm(span=period).mean()
            
            return ema.tolist()
            
        except Exception:
            return []
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
        """Calculate Relative Strength Index"""
        try:
            if len(prices) < period + 1:
                return []
            
            # Convert to pandas Series
            series = pd.Series(prices)
            
            # Calculate price changes
            delta = series.diff()
            
            # Separate gains and losses
            gains = delta.where(delta > 0, 0)
            losses = -delta.where(delta < 0, 0)
            
            # Calculate average gains and losses
            avg_gains = gains.rolling(window=period).mean()
            avg_losses = losses.rolling(window=period).mean()
            
            # Calculate RSI
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.tolist()
            
        except Exception:
            return []
    
    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20, 
                                std_dev: float = 2.0) -> Tuple[List[float], List[float], List[float]]:
        """Calculate Bollinger Bands"""
        try:
            if len(prices) < period:
                return [], [], []
            
            # Convert to pandas Series
            series = pd.Series(prices)
            
            # Calculate moving average
            ma = series.rolling(window=period).mean()
            
            # Calculate standard deviation
            std = series.rolling(window=period).std()
            
            # Calculate bands
            upper_band = ma + (std * std_dev)
            lower_band = ma - (std * std_dev)
            
            return upper_band.tolist(), ma.tolist(), lower_band.tolist()
            
        except Exception:
            return [], [], []
    
    @staticmethod
    def calculate_macd(prices: List[float], fast_period: int = 12, 
                      slow_period: int = 26, signal_period: int = 9) -> Tuple[List[float], List[float], List[float]]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        try:
            if len(prices) < slow_period:
                return [], [], []
            
            # Convert to pandas Series
            series = pd.Series(prices)
            
            # Calculate EMAs
            ema_fast = series.ewm(span=fast_period).mean()
            ema_slow = series.ewm(span=slow_period).mean()
            
            # Calculate MACD line
            macd_line = ema_fast - ema_slow
            
            # Calculate signal line
            signal_line = macd_line.ewm(span=signal_period).mean()
            
            # Calculate histogram
            histogram = macd_line - signal_line
            
            return macd_line.tolist(), signal_line.tolist(), histogram.tolist()
            
        except Exception:
            return [], [], []
    
    @staticmethod
    def calculate_atr(high_prices: List[float], low_prices: List[float], 
                     close_prices: List[float], period: int = 14) -> List[float]:
        """Calculate Average True Range"""
        try:
            if len(high_prices) != len(low_prices) or len(high_prices) != len(close_prices):
                return []
            
            if len(high_prices) < period + 1:
                return []
            
            # Convert to pandas DataFrames
            df = pd.DataFrame({
                'high': high_prices,
                'low': low_prices,
                'close': close_prices
            })
            
            # Calculate True Range
            df['prev_close'] = df['close'].shift(1)
            df['tr1'] = df['high'] - df['low']
            df['tr2'] = abs(df['high'] - df['prev_close'])
            df['tr3'] = abs(df['low'] - df['prev_close'])
            
            df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
            
            # Calculate ATR
            atr = df['true_range'].rolling(window=period).mean()
            
            return atr.tolist()
            
        except Exception:
            return []
    
    @staticmethod
    def calculate_support_resistance(prices: List[float], window: int = 5) -> Tuple[List[float], List[float]]:
        """Calculate support and resistance levels"""
        try:
            if len(prices) < window * 2:
                return [], []
            
            # Convert to pandas Series
            series = pd.Series(prices)
            
            # Find local maxima and minima
            local_maxima = series.rolling(window=window, center=True).max() == series
            local_minima = series.rolling(window=window, center=True).min() == series
            
            # Extract support and resistance levels
            resistance_levels = series[local_maxima].tolist()
            support_levels = series[local_minima].tolist()
            
            return support_levels, resistance_levels
            
        except Exception:
            return [], []
    
    @staticmethod
    def calculate_fibonacci_retracement(high_price: float, low_price: float) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels"""
        try:
            if high_price <= low_price:
                return {}
            
            diff = high_price - low_price
            
            fib_levels = {
                '0%': high_price,
                '23.6%': high_price - (diff * 0.236),
                '38.2%': high_price - (diff * 0.382),
                '50%': high_price - (diff * 0.5),
                '61.8%': high_price - (diff * 0.618),
                '78.6%': high_price - (diff * 0.786),
                '100%': low_price
            }
            
            return fib_levels
            
        except Exception:
            return {}
    
    @staticmethod
    def calculate_pivot_points(high: float, low: float, close: float) -> Dict[str, float]:
        """Calculate pivot points"""
        try:
            if high <= 0 or low <= 0 or close <= 0:
                return {}
            
            # Calculate pivot point
            pivot = (high + low + close) / 3
            
            # Calculate support and resistance levels
            r1 = 2 * pivot - low
            r2 = pivot + (high - low)
            r3 = high + 2 * (pivot - low)
            
            s1 = 2 * pivot - high
            s2 = pivot - (high - low)
            s3 = low - 2 * (high - pivot)
            
            return {
                'pivot': pivot,
                'r1': r1,
                'r2': r2,
                'r3': r3,
                's1': s1,
                's2': s2,
                's3': s3
            }
            
        except Exception:
            return {}
    
    @staticmethod
    def calculate_position_size(account_balance: float, risk_percent: float, 
                              stop_loss_pips: float, pip_value: float) -> float:
        """Calculate position size based on risk management"""
        try:
            if account_balance <= 0 or risk_percent <= 0 or stop_loss_pips <= 0 or pip_value <= 0:
                return 0.0
            
            # Calculate risk amount
            risk_amount = account_balance * (risk_percent / 100)
            
            # Calculate position size
            position_size = risk_amount / (stop_loss_pips * pip_value)
            
            return position_size
            
        except Exception:
            return 0.0
    
    @staticmethod
    def calculate_pip_value(symbol: str, lot_size: float, account_currency: str = "USD") -> float:
        """Calculate pip value for a given symbol and lot size"""
        try:
            # This is a simplified calculation
            # In practice, you'd need to consider the actual currency pairs and exchange rates
            
            # Major pairs pip values (simplified)
            pip_values = {
                'EURUSD': 10.0,
                'GBPUSD': 10.0,
                'USDJPY': 9.09,
                'AUDUSD': 10.0,
                'USDCAD': 7.5,
                'NZDUSD': 10.0,
                'USDCHF': 9.09
            }
            
            base_pip_value = pip_values.get(symbol, 10.0)
            return base_pip_value * lot_size
            
        except Exception:
            return 0.0
    
    @staticmethod
    def calculate_drawdown(equity_curve: List[float]) -> Tuple[float, float, float]:
        """Calculate drawdown statistics"""
        try:
            if not equity_curve:
                return 0.0, 0.0, 0.0
            
            # Convert to numpy array
            equity = np.array(equity_curve)
            
            # Calculate running maximum
            running_max = np.maximum.accumulate(equity)
            
            # Calculate drawdown
            drawdown = running_max - equity
            
            # Calculate maximum drawdown
            max_drawdown = np.max(drawdown)
            
            # Calculate current drawdown
            current_drawdown = drawdown[-1] if len(drawdown) > 0 else 0.0
            
            # Calculate maximum drawdown percentage
            max_drawdown_percent = (max_drawdown / running_max[np.argmax(drawdown)]) * 100 if np.argmax(drawdown) > 0 else 0.0
            
            return max_drawdown, current_drawdown, max_drawdown_percent
            
        except Exception:
            return 0.0, 0.0, 0.0
    
    @staticmethod
    def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio"""
        try:
            if len(returns) < 2:
                return 0.0
            
            # Convert to numpy array
            returns_array = np.array(returns)
            
            # Calculate excess returns
            excess_returns = returns_array - risk_free_rate
            
            # Calculate Sharpe ratio
            if np.std(excess_returns) == 0:
                return 0.0
            
            sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns)
            
            return sharpe_ratio
            
        except Exception:
            return 0.0
    
    @staticmethod
    def calculate_sortino_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
        """Calculate Sortino ratio"""
        try:
            if len(returns) < 2:
                return 0.0
            
            # Convert to numpy array
            returns_array = np.array(returns)
            
            # Calculate excess returns
            excess_returns = returns_array - risk_free_rate
            
            # Calculate downside deviation (only negative returns)
            downside_returns = excess_returns[excess_returns < 0]
            
            if len(downside_returns) == 0 or np.std(downside_returns) == 0:
                return 0.0
            
            # Calculate Sortino ratio
            sortino_ratio = np.mean(excess_returns) / np.std(downside_returns)
            
            return sortino_ratio
            
        except Exception:
            return 0.0
    
    @staticmethod
    def calculate_profit_factor(gross_profit: float, gross_loss: float) -> float:
        """Calculate profit factor"""
        try:
            if gross_loss == 0:
                return float('inf') if gross_profit > 0 else 0.0
            
            return abs(gross_profit / gross_loss)
            
        except Exception:
            return 0.0
    
    @staticmethod
    def calculate_win_rate(winning_trades: int, total_trades: int) -> float:
        """Calculate win rate percentage"""
        try:
            if total_trades == 0:
                return 0.0
            
            return (winning_trades / total_trades) * 100
            
        except Exception:
            return 0.0
    
    @staticmethod
    def calculate_average_win_loss(winning_trades: List[float], losing_trades: List[float]) -> Tuple[float, float]:
        """Calculate average win and loss"""
        try:
            avg_win = np.mean(winning_trades) if winning_trades else 0.0
            avg_loss = np.mean(losing_trades) if losing_trades else 0.0
            
            return avg_win, avg_loss
            
        except Exception:
            return 0.0, 0.0
    
    @staticmethod
    def calculate_max_consecutive_wins_losses(trades: List[float]) -> Tuple[int, int]:
        """Calculate maximum consecutive wins and losses"""
        try:
            if not trades:
                return 0, 0
            
            max_wins = 0
            max_losses = 0
            current_wins = 0
            current_losses = 0
            
            for trade in trades:
                if trade > 0:
                    current_wins += 1
                    current_losses = 0
                    max_wins = max(max_wins, current_wins)
                elif trade < 0:
                    current_losses += 1
                    current_wins = 0
                    max_losses = max(max_losses, current_losses)
                else:
                    current_wins = 0
                    current_losses = 0
            
            return max_wins, max_losses
            
        except Exception:
            return 0, 0
