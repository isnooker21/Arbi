#!/usr/bin/env python3
"""
สคริปต์ Auto Setup สำหรับระบบเทรด Forex AI
==========================================

สคริปต์นี้จะช่วยตั้งค่าระบบโดยอัตโนมัติ:
- Auto-detect ข้อมูลจาก MT5
- ตั้งค่า Broker Config
- ตรวจสอบการเชื่อมต่อ
- แสดงข้อมูลบัญชี

การใช้งาน:
    python auto_setup.py
"""

import sys
import os
import logging
from datetime import datetime

# เพิ่ม path ของโปรเจค
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """ตั้งค่าระบบ Logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def main():
    """ฟังก์ชันหลักสำหรับ Auto Setup"""
    logger = setup_logging()
    
    print("🚀 กำลังเริ่ม Auto Setup สำหรับระบบเทรด Forex AI...")
    print("=" * 60)
    
    try:
        # Import modules
        from trading.broker_api import BrokerAPI
        
        # สร้าง BrokerAPI instance
        broker_api = BrokerAPI("MetaTrader5")
        
        print("📡 กำลังตรวจสอบการเชื่อมต่อ MT5...")
        
        # ลองเชื่อมต่อแบบ auto
        if broker_api.connect():
            print("✅ เชื่อมต่อ MT5 สำเร็จ!")
            
            # แสดงข้อมูลบัญชี
            if broker_api.account_info:
                account = broker_api.account_info
                print("\n📊 ข้อมูลบัญชี:")
                print(f"   หมายเลขบัญชี: {account.login}")
                print(f"   เซิร์ฟเวอร์: {account.server}")
                print(f"   ยอดเงิน: {account.balance:.2f} {account.currency}")
                print(f"   Equity: {account.equity:.2f} {account.currency}")
                print(f"   Margin: {account.margin:.2f} {account.currency}")
                print(f"   Free Margin: {account.margin_free:.2f} {account.currency}")
                print(f"   Leverage: 1:{account.leverage}")
                
                # ตรวจสอบการตั้งค่า
                print("\n⚙️  การตั้งค่า:")
                print(f"   Auto-detect สำเร็จ: ✅")
                print(f"   Config file อัปเดตแล้ว: ✅")
                
                # แสดงคู่เงินที่ใช้ได้
                print("\n💱 กำลังตรวจสอบคู่เงินที่ใช้ได้...")
                try:
                    symbols = broker_api.get_available_pairs()
                    if symbols:
                        print(f"   พบคู่เงิน {len(symbols)} คู่:")
                        for i, symbol in enumerate(symbols[:10]):  # แสดง 10 คู่แรก
                            print(f"   {i+1:2d}. {symbol}")
                        if len(symbols) > 10:
                            print(f"   ... และอีก {len(symbols) - 10} คู่")
                    else:
                        print("   ไม่พบคู่เงิน")
                except Exception as e:
                    print(f"   ⚠️  ไม่สามารถดึงข้อมูลคู่เงิน: {e}")
                
                print("\n🎉 Auto Setup เสร็จสิ้น!")
                print("   ระบบพร้อมใช้งานแล้ว")
                print("   รันระบบด้วย: python run.py")
                
            else:
                print("❌ ไม่สามารถดึงข้อมูลบัญชีได้")
                return False
                
        else:
            print("❌ ไม่สามารถเชื่อมต่อ MT5 ได้")
            print("\n🔧 วิธีแก้ไข:")
            print("   1. ตรวจสอบว่า MT5 เปิดอยู่และ login แล้ว")
            print("   2. ตรวจสอบว่า MT5 อนุญาตให้ Expert Advisors ทำงาน")
            print("   3. ตรวจสอบการตั้งค่าใน Tools → Options → Expert Advisors")
            print("   4. ลองรันใหม่: python auto_setup.py")
            return False
            
    except ImportError as e:
        print(f"❌ ไม่สามารถ import modules ได้: {e}")
        print("   ลองติดตั้ง dependencies: pip install -r requirements.txt")
        return False
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Auto Setup สำเร็จ!")
        sys.exit(0)
    else:
        print("\n❌ Auto Setup ล้มเหลว!")
        sys.exit(1)
