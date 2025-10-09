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
import logging

class TradingCalculations:
    """Utility class for trading calculations"""
    
    @staticmethod
    def calculate_arbitrage_percentage(pair1_price: float, pair2_price: float, 
                                     pair3_price: float, spread1: float = 0, 
                                     spread2: float = 0, spread3: float = 0,
                                     commission_rate: float = 0.0001, 
                                     slippage_percent: float = 0.05,
                                     minimum_threshold: float = 0.1) -> float:
        """
        คำนวณเปอร์เซ็นต์ Arbitrage แบบสามเหลี่ยมรวมต้นทุนการเทรดจริง
        
        Parameters:
        - pair1_price, pair2_price, pair3_price: ราคาคู่เงิน
        - spread1, spread2, spread3: Spread ของแต่ละคู่เงิน (pips)
        - commission_rate: อัตราค่าคอมมิชชั่น (0.0001 = 0.01%)
        - slippage_percent: เปอร์เซ็นต์ Slippage (0.05 = 0.05%)
        - minimum_threshold: ขั้นต่ำที่ต้องทำกำไร (0.1 = 0.1%)
        
        Returns:
        - Net arbitrage percentage หลังจากหักต้นทุนแล้ว
        """
        try:
            # ตรวจสอบข้อมูลพื้นฐานด้วย DataValidator
            if not DataValidator.validate_arbitrage_data(pair1_price, pair2_price, pair3_price):
                return 0.0
            
            # คำนวณราคาทางทฤษฎี
            theoretical_price = pair1_price * pair2_price
            
            if theoretical_price == 0:
                return 0.0
            
            # คำนวณ theoretical arbitrage
            theoretical_arbitrage = (pair3_price - theoretical_price) / theoretical_price * 100
            
            # คำนวณต้นทุนรวม
            # 1. Spread cost (แปลงจาก pips เป็นเปอร์เซ็นต์)
            spread_cost = ((spread1 + spread2 + spread3) / pair3_price) * 100
            
            # 2. Commission cost (3 legs)
            commission_cost = commission_rate * 3 * 100
            
            # 3. Slippage cost
            slippage_cost = slippage_percent
            
            # ต้นทุนรวม
            total_cost = spread_cost + commission_cost + slippage_cost
            
            # Arbitrage ที่แท้จริง = theoretical - ต้นทุน
            net_arbitrage = theoretical_arbitrage - total_cost
            
            # Return เฉพาะเมื่อ net_arbitrage > minimum_threshold
            return net_arbitrage if net_arbitrage > minimum_threshold else 0.0
            
        except Exception as e:
            # Log error for debugging
            import logging
            logging.getLogger(__name__).error(f"Error calculating arbitrage: {e}")
            return 0.0
    
    @staticmethod
    def calculate_correlation(prices1: List[float], prices2: List[float]) -> float:
        """Calculate correlation between two price series"""
        try:
            # ตรวจสอบข้อมูลด้วย DataValidator
            if not DataValidator.validate_correlation_data(prices1, prices2):
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
    
    # ฟังก์ชันนี้ถูกลบออกแล้ว - ใช้ calculate_lot_from_balance แทน
    
    @staticmethod
    def calculate_pip_value(symbol: str, lot_size: float = 0.01, broker_api=None, account_currency: str = "USD") -> float:
        """คำนวณ pip value ที่แม่นยำตามสูตรที่ถูกต้อง"""
        try:
            # ตัด suffix (.m, .raw, .pro) ออก
            clean_symbol = symbol.upper().split('.')[0]
            
            # ตรวจสอบ input parameters
            if lot_size <= 0:
                logging.getLogger(__name__).warning(f"Invalid lot size: {lot_size}, using 0.01")
                lot_size = 0.01
            
            if len(clean_symbol) != 6:
                return 10.0  # fallback
            
            base_currency = clean_symbol[:3]
            quote_currency = clean_symbol[3:]
            
            # Contract size
            contract_size = 100000 * lot_size
            
            # Determine pip size
            pip_size = 0.01 if quote_currency == 'JPY' else 0.0001
            
            # Case 1: Quote currency is USD (EURUSD, GBPUSD, etc.)
            if quote_currency == 'USD':
                pip_value = contract_size * pip_size
                logging.getLogger(__name__).debug(f"USD Quote: {clean_symbol} = {contract_size} × {pip_size} = {pip_value:.2f}")
                
            # Case 2: JPY pairs (USDJPY, EURJPY, etc.)
            elif quote_currency == 'JPY':
                usd_jpy_rate = TradingCalculations.get_exchange_rate('USDJPY', broker_api)
                pip_value = (contract_size * pip_size) / usd_jpy_rate
                logging.getLogger(__name__).debug(f"JPY Pair: {clean_symbol} = ({contract_size} × {pip_size}) / {usd_jpy_rate:.2f} = {pip_value:.2f}")
                
            # Case 3: USD base pairs (USDCHF, USDCAD, etc.)
            elif base_currency == 'USD':
                usd_xxx_rate = TradingCalculations.get_exchange_rate(clean_symbol, broker_api)
                pip_value = (contract_size * pip_size) / usd_xxx_rate
                logging.getLogger(__name__).debug(f"USD Base: {clean_symbol} = ({contract_size} × {pip_size}) / {usd_xxx_rate:.2f} = {pip_value:.2f}")
                
            # Case 4: Cross pairs (EURGBP, EURAUD, etc.)
            else:
                quote_to_usd_rate = TradingCalculations.get_quote_to_usd_rate(quote_currency, broker_api)
                pip_value = (contract_size * pip_size) * quote_to_usd_rate
                logging.getLogger(__name__).debug(f"Cross Pair: {clean_symbol} = {contract_size} × {pip_size} × {quote_to_usd_rate:.4f} = {pip_value:.2f}")
            
            return pip_value
            
        except Exception as e:
            logging.getLogger(__name__).error(f"❌ Error calculating pip value for {symbol}: {e}")
            # ⚠️ ใช้ fallback สำหรับ major pairs เท่านั้น
            # สำหรับ USD pairs: 1 lot = $10/pip
            if 'USD' in symbol.upper():
                pip_value_1lot = 10.0
                return pip_value_1lot * lot_size
            else:
                # Cross pairs: ประมาณ $13/pip for 1 lot
                pip_value_1lot = 13.0
                return pip_value_1lot * lot_size
    
    
    @staticmethod
    def get_exchange_rate(symbol: str, broker_api) -> float:
        """ดึงอัตราแลกเปลี่ยนจาก broker - บังคับให้ใช้จาก MT5 เท่านั้น"""
        try:
            if broker_api and hasattr(broker_api, 'get_current_price'):
                price_data = broker_api.get_current_price(symbol)
                if price_data and isinstance(price_data, (int, float)) and price_data > 0:
                    return float(price_data)
                else:
                    logging.getLogger(__name__).error(f"❌ Cannot get price for {symbol} from MT5")
                    return 0.0  # ส่งกลับ 0 เพื่อให้เห็นว่ามีปัญหา
            else:
                logging.getLogger(__name__).error(f"❌ No broker_api available for {symbol}")
                return 0.0
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Error getting exchange rate for {symbol}: {e}")
            return 1.0
    
    @staticmethod
    def get_quote_to_usd_rate(currency: str, broker_api) -> float:
        """ได้อัตราแลกเปลี่ยนจาก quote currency เป็น USD"""
        try:
            if currency == 'USD':
                return 1.0
            elif currency == 'EUR':
                return TradingCalculations.get_exchange_rate('EURUSD', broker_api)
            elif currency == 'GBP':  
                return TradingCalculations.get_exchange_rate('GBPUSD', broker_api)
            elif currency == 'AUD':
                return TradingCalculations.get_exchange_rate('AUDUSD', broker_api)
            elif currency == 'CAD':
                usd_cad = TradingCalculations.get_exchange_rate('USDCAD', broker_api)
                return 1.0 / usd_cad
            elif currency == 'CHF':
                usd_chf = TradingCalculations.get_exchange_rate('USDCHF', broker_api)
                return 1.0 / usd_chf
            elif currency == 'NZD':
                return TradingCalculations.get_exchange_rate('NZDUSD', broker_api)
            else:
                return 1.0  # fallback
                
        except Exception as e:
            logging.getLogger(__name__).error(f"Error getting quote to USD rate for {currency}: {e}")
            return 1.0
    
    @staticmethod
    def calculate_lot_from_balance(balance: float, pip_value: float, risk_percent: float = 1.0, max_loss_pips: float = 100) -> float:
        """
        Calculate lot size based on account balance using Proper Risk Management
        
        Args:
            balance: Account balance in USD
            pip_value: Pip value per 1.0 lot (e.g., $10 for EURUSD)
            risk_percent: Risk percentage (e.g., 1.0 means 1% risk if move 100 pips)
            max_loss_pips: Maximum pips to move before hitting risk limit (default 100 pips)
            
        Returns:
            float: Calculated lot size
        """
        try:
            if balance <= 0 or risk_percent <= 0 or pip_value <= 0 or max_loss_pips <= 0:
                return 0.01  # Minimum lot size
            
            # 🎯 สูตร Risk Management ที่ถูกต้อง
            # Risk Amount = Balance × (Risk% ÷ 100)
            # Lot Size = Risk Amount ÷ (Pip Value × Max Loss Pips)
            
            # ตัวอย่าง:
            # Balance = $10,000, Risk = 1%, Max Loss = 100 pips, Pip Value = $10
            # Risk Amount = $10,000 × (1 ÷ 100) = $100
            # Lot Size = $100 ÷ ($10 × 100) = $100 ÷ $1,000 = 0.1 lot
            
            # คำนวณ Risk Amount (ยอดเงินที่ยอมเสี่ยงได้)
            risk_amount = balance * (risk_percent / 100.0)
            
            # คำนวณ Pip Value สำหรับ max_loss_pips
            pip_value_for_risk = pip_value * max_loss_pips
            
            # คำนวณ Lot Size
            calculated_lot = risk_amount / pip_value_for_risk
            
            # Round to valid lot size
            final_lot = TradingCalculations.round_to_valid_lot_size(calculated_lot)
            
            # จำกัดขนาด lot (min 0.01 เท่านั้น ไม่จำกัด max)
            final_lot = max(0.01, final_lot)
            
            # Debug log
            logging.getLogger(__name__).info(f"💰 Proper Risk Management Lot Calculation:")
            logging.getLogger(__name__).info(f"   Balance=${balance:.2f}")
            logging.getLogger(__name__).info(f"   Risk={risk_percent}% => Risk Amount=${risk_amount:.2f}")
            logging.getLogger(__name__).info(f"   Max Loss Pips={max_loss_pips}")
            logging.getLogger(__name__).info(f"   Pip Value=${pip_value:.2f}/lot")
            logging.getLogger(__name__).info(f"   Risk Pip Value=${pip_value_for_risk:.2f} ({max_loss_pips} pips)")
            logging.getLogger(__name__).info(f"   Calculated Lot={calculated_lot:.4f}")
            logging.getLogger(__name__).info(f"   Final Lot={final_lot:.4f}")
            logging.getLogger(__name__).info(f"   ✅ If move {max_loss_pips} pips → Loss = ${final_lot * pip_value * max_loss_pips:.2f} ({risk_percent}% of balance)")
            
            return final_lot
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Error calculating proper risk lot from balance: {e}")
            return 0.01  # Minimum lot size
    
    @staticmethod
    def round_to_valid_lot_size(calculated_lot: float, min_lot: float = 0.01, lot_step: float = 0.01) -> float:
        """Round calculated lot size to valid broker lot size"""
        try:
            if calculated_lot <= 0:
                return min_lot
            
            # Round to nearest lot step
            rounded_lot = round(calculated_lot / lot_step) * lot_step
            
            # Ensure minimum lot size (broker requirement)
            if rounded_lot < min_lot:
                rounded_lot = min_lot
                logging.getLogger(__name__).info(f"📊 Lot size adjusted to minimum: {calculated_lot:.4f} → {rounded_lot:.2f}")
            
            # ไม่จำกัด maximum lot size (ให้คำนวณตาม risk จริงๆ)
            # max_lot = 5.0
            # if rounded_lot > max_lot:
            #     rounded_lot = max_lot
            #     logging.getLogger(__name__).warning(f"📊 Lot size capped at maximum: {rounded_lot:.2f}")
            
            return rounded_lot
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Error rounding lot size: {e}")
            return min_lot
    
    @staticmethod
    def get_uniform_triangle_lots(triangle_symbols: List[str], balance: float, target_pip_value: float = 10.0, broker_api=None, use_simple_mode: bool = False, use_risk_based_sizing: bool = False, risk_per_trade_percent: float = None) -> Dict[str, float]:
        """คำนวณ lot sizes ให้ pip value เท่ากัน + scale ตาม balance (ใช้ค่าจาก config)"""
        try:
            if not triangle_symbols or len(triangle_symbols) != 3:
                return {}
            
            if balance <= 0:
                return {}
            
            # ⭐ ตรวจสอบว่ามี risk_per_trade_percent หรือไม่
            if risk_per_trade_percent is None:
                logging.getLogger(__name__).error("❌ risk_per_trade_percent is required - must be set in GUI Settings")
                return {}
            
            # ใช้ค่าที่ส่งมาแทนการโหลดจาก config (เพื่อความแน่นอน)
            use_risk_based = use_risk_based_sizing  # ใช้ค่าที่ส่งมา
            
            # ===== โหมดที่ 1: Risk-Based Sizing (ง่ายที่สุด - แนะนำ!) =====
            if use_risk_based:
                # คำนวณ lot size จาก risk โดยตรง (ใช้ Risk ทั้งหมด ไม่แบ่ง 3 คู่)
                # Risk Amount = Balance × Risk%
                # Lot = Risk Amount / (Max Loss Pips × Pip Value)
                
                # ⭐ บันทึก log เพียงครั้งเดียว
                logging.getLogger(__name__).info(f"💰 Lot Calc: Balance=${balance:,.2f}, Risk={risk_per_trade_percent}%")
                
                risk_amount = balance * (risk_per_trade_percent / 100.0)
                
                # ใช้ Max Loss Pips = 100 (จาก GUI) แทน Stop Loss
                max_loss_pips = 100.0  # ใช้ค่าจาก GUI
                
                lot_sizes = {}
                
                for symbol in triangle_symbols:
                    # 🎯 สูตร Risk Management ที่ถูกต้อง
                    # Lot Size = Risk Amount ÷ (Pip Value × Max Loss Pips)
                    pip_value_per_1lot = TradingCalculations.calculate_pip_value(symbol, 1.0, broker_api)
                    max_loss_pips = 100  # Default 100 pips risk
                    
                    if pip_value_per_1lot > 0:
                        # คำนวณ pip value สำหรับ max_loss_pips
                        pip_value_for_risk = pip_value_per_1lot * max_loss_pips
                        
                        # คำนวณ lot size (ใช้ Risk ทั้งหมด ไม่แบ่ง 3 คู่)
                        lot_size = risk_amount / pip_value_for_risk
                        
                        # Round to valid lot size
                        lot_size = TradingCalculations.round_to_valid_lot_size(lot_size)
                        
                        # จำกัดขนาด lot (min 0.01 เท่านั้น ไม่จำกัด max)
                        lot_size = max(0.01, lot_size)
                        
                    else:
                        lot_size = 0.01  # Minimum fallback
                        logging.getLogger(__name__).warning(f"⚠️ {symbol}: Cannot calculate pip value, using minimum lot")
                    
                    lot_sizes[symbol] = lot_size
                
                return lot_sizes
            
            # ===== ใช้ Risk-Based Mode เท่านั้น =====
            # คำนวณ lot size จาก risk โดยตรง
            risk_amount = balance * (risk_per_trade_percent / 100.0)
            max_loss_pips = 100.0
            
            lot_sizes = {}
            
            for symbol in triangle_symbols:
                pip_value_per_1lot = TradingCalculations.calculate_pip_value(symbol, 1.0, broker_api)
                
                if pip_value_per_1lot > 0:
                    pip_value_for_risk = pip_value_per_1lot * max_loss_pips
                    lot_size = risk_amount / pip_value_for_risk
                    lot_size = TradingCalculations.round_to_valid_lot_size(lot_size)
                    lot_size = max(0.01, lot_size)
                else:
                    lot_size = 0.01
                
                lot_sizes[symbol] = lot_size
            
            return lot_sizes
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Error calculating uniform triangle lots: {e}")
            return {}
    
    # ฟังก์ชันนี้ถูกลบออกแล้ว - ใช้ get_uniform_triangle_lots แทน
    
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


class DataValidator:
    """คลาสสำหรับตรวจสอบความถูกต้องของข้อมูลก่อนใช้งาน"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def validate_price_data(prices: List[float], symbol: str = "Unknown") -> bool:
        """
        ตรวจสอบความถูกต้องของข้อมูลราคา
        
        Parameters:
        - prices: รายการราคา
        - symbol: ชื่อสัญลักษณ์ (สำหรับ log)
        
        Returns:
        - True ถ้าข้อมูลถูกต้อง, False ถ้าไม่ถูกต้อง
        """
        try:
            if not prices or len(prices) == 0:
                raise ValueError(f"Empty price data for {symbol}")
            
            # ตรวจสอบราคาที่ไม่ถูกต้อง (<= 0)
            if any(p <= 0 for p in prices):
                raise ValueError(f"Invalid price (<= 0) for {symbol}")
            
            # ตรวจสอบการเปลี่ยนแปลงราคาที่ไม่สมเหตุสมผล (> 10% ในหนึ่ง tick)
            for i in range(1, len(prices)):
                if prices[i-1] > 0:  # ตรวจสอบหารด้วยศูนย์
                    change_percent = abs(prices[i] - prices[i-1]) / prices[i-1] * 100
                    if change_percent > 10:
                        raise ValueError(f"Unrealistic price change {change_percent:.2f}% for {symbol}")
            
            return True
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Price validation failed for {symbol}: {e}")
            return False
    
    @staticmethod
    def validate_correlation_data(data1: List[float], data2: List[float]) -> bool:
        """
        ตรวจสอบความถูกต้องของข้อมูลสำหรับการคำนวณ correlation
        
        Parameters:
        - data1, data2: ข้อมูลสองชุดสำหรับคำนวณ correlation
        
        Returns:
        - True ถ้าข้อมูลถูกต้อง, False ถ้าไม่ถูกต้อง
        """
        try:
            if len(data1) != len(data2):
                raise ValueError("Correlation data length mismatch")
            
            if len(data1) < 10:
                raise ValueError("Insufficient data for correlation (min 10 points)")
            
            # ตรวจสอบข้อมูลที่ว่างเปล่า
            if not data1 or not data2:
                raise ValueError("Empty correlation data")
            
            # ตรวจสอบข้อมูลที่ไม่มีค่า (NaN)
            if any(math.isnan(x) for x in data1) or any(math.isnan(x) for x in data2):
                raise ValueError("NaN values found in correlation data")
            
            # ตรวจสอบข้อมูลที่ไม่มีค่า (infinity)
            if any(math.isinf(x) for x in data1) or any(math.isinf(x) for x in data2):
                raise ValueError("Infinite values found in correlation data")
            
            return True
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Correlation data validation failed: {e}")
            return False
    
    @staticmethod
    def validate_arbitrage_data(pair1_price: float, pair2_price: float, 
                               pair3_price: float) -> bool:
        """
        ตรวจสอบความถูกต้องของข้อมูลสำหรับการคำนวณ arbitrage
        
        Parameters:
        - pair1_price, pair2_price, pair3_price: ราคาคู่เงินทั้งสาม
        
        Returns:
        - True ถ้าข้อมูลถูกต้อง, False ถ้าไม่ถูกต้อง
        """
        try:
            # ตรวจสอบราคาที่ไม่ถูกต้อง
            if pair1_price <= 0 or pair2_price <= 0 or pair3_price <= 0:
                raise ValueError("Invalid price data (<= 0)")
            
            # ตรวจสอบราคาที่ไม่มีค่า
            if (math.isnan(pair1_price) or math.isnan(pair2_price) or 
                math.isnan(pair3_price)):
                raise ValueError("NaN values in price data")
            
            # ตรวจสอบราคาที่ไม่มีค่า (infinity)
            if (math.isinf(pair1_price) or math.isinf(pair2_price) or 
                math.isinf(pair3_price)):
                raise ValueError("Infinite values in price data")
            
            # ตรวจสอบราคาที่ไม่สมเหตุสมผล (มากเกินไปหรือน้อยเกินไป)
            if (pair1_price > 1000 or pair2_price > 1000 or pair3_price > 1000 or
                pair1_price < 0.0001 or pair2_price < 0.0001 or pair3_price < 0.0001):
                raise ValueError("Unrealistic price values")
            
            return True
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Arbitrage data validation failed: {e}")
            return False
    
    @staticmethod
    def validate_trading_parameters(volume: float, stop_loss: float, 
                                  take_profit: float, symbol: str = "Unknown") -> bool:
        """
        ตรวจสอบพารามิเตอร์การเทรด
        
        Parameters:
        - volume: ขนาดตำแหน่ง
        - stop_loss: ระดับ stop loss
        - take_profit: ระดับ take profit
        - symbol: ชื่อสัญลักษณ์
        
        Returns:
        - True ถ้าพารามิเตอร์ถูกต้อง, False ถ้าไม่ถูกต้อง
        """
        try:
            # ตรวจสอบ volume
            if volume <= 0 or volume > 100:
                raise ValueError(f"Invalid volume {volume} for {symbol}")
            
            # ตรวจสอบ stop loss
            if stop_loss <= 0:
                raise ValueError(f"Invalid stop loss {stop_loss} for {symbol}")
            
            # ตรวจสอบ take profit
            if take_profit <= 0:
                raise ValueError(f"Invalid take profit {take_profit} for {symbol}")
            
            # ตรวจสอบ stop loss และ take profit ที่สมเหตุสมผล
            if stop_loss > 1000:  # มากกว่า 1000 pips
                raise ValueError(f"Stop loss too large {stop_loss} for {symbol}")
            
            if take_profit > 1000:  # มากกว่า 1000 pips
                raise ValueError(f"Take profit too large {take_profit} for {symbol}")
            
            return True
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Trading parameters validation failed for {symbol}: {e}")
            return False
