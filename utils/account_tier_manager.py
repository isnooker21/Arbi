"""
ระบบจัดการ Account Tier อัตโนมัติ

ไฟล์นี้ทำหน้าที่:
- ตรวจจับระดับบัญชีตามยอดเงินอัตโนมัติ
- ปรับการตั้งค่าตาม Account Tier
- จัดการ Risk Management ตามระดับบัญชี
- รองรับลูกค้าหลายประเภท
"""

import json
import logging
from typing import Dict, Optional, Tuple
import os

class AccountTierManager:
    """จัดการ Account Tier และการตั้งค่าตามยอดเงิน"""
    
    def __init__(self, config_file: str = "config/adaptive_params.json"):
        self.logger = logging.getLogger(__name__)
        self.config_file = config_file
        self.account_tiers = self._load_account_tiers()
        
    def _load_account_tiers(self) -> Dict:
        """โหลดการตั้งค่า Account Tiers จาก config"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config.get('position_sizing', {}).get('account_tiers', {})
        except UnicodeDecodeError as e:
            self.logger.error(f"Unicode decode error in config file: {e}")
            # Try with different encodings
            for encoding in ['cp1252', 'latin-1', 'iso-8859-1']:
                try:
                    with open(self.config_file, 'r', encoding=encoding) as f:
                        config = json.load(f)
                    self.logger.info(f"Successfully loaded config with {encoding} encoding")
                    return config.get('position_sizing', {}).get('account_tiers', {})
                except:
                    continue
            self.logger.error("Failed to load config with any encoding, using defaults")
            return self._get_default_tiers()
        except Exception as e:
            self.logger.error(f"Error loading account tiers: {e}")
            return self._get_default_tiers()
    
    def _get_default_tiers(self) -> Dict:
        """Default account tiers หากไม่สามารถโหลด config ได้"""
        return {
            "starter": {
                "min_balance": 1000,
                "max_balance": 5000,
                "risk_per_trade_percent": 2.0,
                "max_triangles": 2,
                "description": "Starter account"
            },
            "standard": {
                "min_balance": 5000,
                "max_balance": 25000,
                "risk_per_trade_percent": 1.5,
                "max_triangles": 3,
                "description": "Standard account"
            },
            "premium": {
                "min_balance": 25000,
                "max_balance": 100000,
                "risk_per_trade_percent": 1.2,
                "max_triangles": 4,
                "description": "Premium account"
            },
            "vip": {
                "min_balance": 100000,
                "max_balance": 999999999,
                "risk_per_trade_percent": 1.0,
                "max_triangles": 5,
                "description": "VIP account"
            }
        }
    
    def detect_account_tier(self, balance: float) -> Tuple[str, Dict]:
        """
        ตรวจจับ Account Tier ตามยอดเงิน
        
        Args:
            balance: ยอดเงินในบัญชี
            
        Returns:
            Tuple[str, Dict]: (tier_name, tier_config)
        """
        try:
            for tier_name, tier_config in self.account_tiers.items():
                min_balance = tier_config.get('min_balance', 0)
                max_balance = tier_config.get('max_balance', float('inf'))
                
                if min_balance <= balance <= max_balance:
                    self.logger.info(f"🎯 Account Tier Detected: {tier_name.upper()}")
                    self.logger.info(f"   Balance: ${balance:,.2f}")
                    self.logger.info(f"   Risk: {tier_config.get('risk_per_trade_percent', 1.5)}%")
                    self.logger.info(f"   Max Triangles: {tier_config.get('max_triangles', 3)}")
                    return tier_name, tier_config
            
            # หากไม่พบ tier ที่เหมาะสม ใช้ starter
            self.logger.warning(f"Balance ${balance:,.2f} not in any tier range - using STARTER")
            return "starter", self.account_tiers.get("starter", {})
            
        except Exception as e:
            self.logger.error(f"Error detecting account tier: {e}")
            return "starter", self._get_default_tiers().get("starter", {})
    
    def get_tier_config(self, tier_name: str) -> Dict:
        """ดึงการตั้งค่าของ tier ที่ระบุ"""
        return self.account_tiers.get(tier_name, {})
    
    def calculate_lot_size_for_tier(self, balance: float, pip_value: float, tier_name: str = None) -> float:
        """
        คำนวณ lot size ตาม tier
        
        Args:
            balance: ยอดเงินในบัญชี
            pip_value: pip value per 0.01 lot
            tier_name: ชื่อ tier (ถ้าไม่ระบุจะ auto-detect)
            
        Returns:
            float: lot size ที่คำนวณได้
        """
        try:
            if not tier_name:
                tier_name, _ = self.detect_account_tier(balance)
            
            tier_config = self.get_tier_config(tier_name)
            risk_percent = tier_config.get('risk_per_trade_percent', 1.5)
            
            # คำนวณ lot size ตาม Risk-Based Sizing
            risk_amount = balance * (risk_percent / 100.0)
            risk_per_pair = risk_amount / 3.0  # แบ่งเป็น 3 คู่ใน triangle
            
            if pip_value > 0:
                lot_size = (risk_per_pair / pip_value) * 0.01
            else:
                lot_size = 0.01
            
            # จำกัดขนาด lot ตาม tier
            max_position_size = tier_config.get('max_position_size', 1.0)
            lot_size = min(lot_size, max_position_size)
            
            self.logger.info(f"💰 Lot Calculation for {tier_name.upper()}:")
            self.logger.info(f"   Balance: ${balance:,.2f}")
            self.logger.info(f"   Risk: {risk_percent}% (${risk_amount:,.2f})")
            self.logger.info(f"   Risk per Pair: ${risk_per_pair:,.2f}")
            self.logger.info(f"   Calculated Lot: {lot_size:.4f}")
            
            return max(0.01, lot_size)  # ขั้นต่ำ 0.01 lot
            
        except Exception as e:
            self.logger.error(f"Error calculating lot size for tier: {e}")
            return 0.01
    
    def get_max_triangles(self, balance: float, tier_name: str = None) -> int:
        """ดึงจำนวน triangle สูงสุดตาม tier"""
        try:
            if not tier_name:
                tier_name, _ = self.detect_account_tier(balance)
            
            tier_config = self.get_tier_config(tier_name)
            max_triangles = tier_config.get('max_triangles', 3)
            
            self.logger.info(f"🔺 Max Triangles for {tier_name.upper()}: {max_triangles}")
            return max_triangles
            
        except Exception as e:
            self.logger.error(f"Error getting max triangles: {e}")
            return 3
    
    def get_tier_summary(self, balance: float) -> Dict:
        """สรุปข้อมูล tier สำหรับบัญชี"""
        try:
            tier_name, tier_config = self.detect_account_tier(balance)
            
            summary = {
                'tier_name': tier_name,
                'balance': balance,
                'risk_per_trade_percent': tier_config.get('risk_per_trade_percent', 1.5),
                'max_triangles': tier_config.get('max_triangles', 3),
                'max_position_size': tier_config.get('max_position_size', 1.0),
                'description': tier_config.get('description', ''),
                'risk_amount': balance * (tier_config.get('risk_per_trade_percent', 1.5) / 100.0),
                'risk_per_pair': (balance * (tier_config.get('risk_per_trade_percent', 1.5) / 100.0)) / 3.0
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting tier summary: {e}")
            return {}
    
    def print_tier_info(self, balance: float):
        """แสดงข้อมูล tier แบบสวยงาม"""
        try:
            summary = self.get_tier_summary(balance)
            
            print("\n" + "="*60)
            print(f"🎯 ACCOUNT TIER DETECTION")
            print("="*60)
            print(f"💰 Balance: ${summary.get('balance', 0):,.2f}")
            print(f"🏆 Tier: {summary.get('tier_name', 'UNKNOWN').upper()}")
            print(f"📊 Risk per Trade: {summary.get('risk_per_trade_percent', 1.5)}%")
            print(f"💵 Risk Amount: ${summary.get('risk_amount', 0):,.2f}")
            print(f"🎯 Risk per Pair: ${summary.get('risk_per_pair', 0):,.2f}")
            print(f"🔺 Max Triangles: {summary.get('max_triangles', 3)}")
            print(f"📏 Max Position Size: {summary.get('max_position_size', 1.0)} lot")
            print(f"📝 Description: {summary.get('description', '')}")
            print("="*60)
            
        except Exception as e:
            self.logger.error(f"Error printing tier info: {e}")

# ฟังก์ชันสำหรับทดสอบ
def test_account_tiers():
    """ทดสอบระบบ Account Tier"""
    manager = AccountTierManager()
    
    test_balances = [1000, 5000, 15000, 50000, 100000, 250000]
    
    print("🧪 TESTING ACCOUNT TIER DETECTION")
    print("="*80)
    
    for balance in test_balances:
        manager.print_tier_info(balance)
        print()

if __name__ == "__main__":
    test_account_tiers()

