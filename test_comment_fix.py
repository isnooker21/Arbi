#!/usr/bin/env python3
"""
ทดสอบการแก้ไขปัญหา comment
"""

import sys
import os
import logging
import time

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading.broker_api import BrokerAPI

def test_comment_fix():
    """ทดสอบการแก้ไขปัญหา comment"""
    print("🧪 เริ่มทดสอบการแก้ไขปัญหา comment...")
    print("=" * 50)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    try:
        # สร้าง BrokerAPI
        broker_api = BrokerAPI("MetaTrader5")
        
        # เชื่อมต่อ
        print("📡 กำลังเชื่อมต่อ MT5...")
        if not broker_api.connect():
            print("❌ ไม่สามารถเชื่อมต่อ MT5 ได้")
            return False
        
        print("✅ เชื่อมต่อ MT5 สำเร็จ!")
        
        # ทดสอบการดึงข้อมูลคู่เงิน
        print(f"\n🔍 กำลังตรวจสอบคู่เงินที่ใช้ได้...")
        symbols = broker_api.get_available_pairs()
        if symbols:
            print(f"   พบคู่เงิน {len(symbols)} คู่")
            
            # ทดสอบการดึงราคา
            test_symbol = symbols[0] if symbols else "EURUSD"
            print(f"\n💰 กำลังทดสอบราคา {test_symbol}...")
            price = broker_api.get_current_price(test_symbol)
            if price:
                print(f"   ราคาปัจจุบัน: {price}")
            else:
                print(f"   ❌ ไม่สามารถดึงราคาได้")
                return False
        else:
            print("   ❌ ไม่พบคู่เงิน")
            return False
        
        # ทดสอบการส่งออเดอร์ด้วย comment ง่ายๆ
        print(f"\n📤 กำลังทดสอบการส่งออเดอร์ด้วย comment ง่ายๆ...")
        print("⚠️  หมายเหตุ: นี่เป็นการทดสอบจริง - จะส่งออเดอร์ขนาดเล็ก")
        
        # ใช้คู่เงินแรกที่พบ
        test_symbol = symbols[0] if symbols else "EURUSD"
        current_price = broker_api.get_current_price(test_symbol)
        
        if current_price:
            # ส่งออเดอร์ BUY ขนาด 0.01 lot
            print(f"   ส่งออเดอร์ BUY {test_symbol} 0.01 lot @ {current_price}")
            
            result = broker_api.place_order(
                symbol=test_symbol,
                order_type="BUY",
                volume=0.01,
                price=current_price,
                comment="Test"  # ใช้ comment ง่ายๆ
            )
            
            if result:
                print(f"   ✅ ออเดอร์ส่งสำเร็จ!")
                print(f"   Order ID: {result.get('order_id')}")
                print(f"   Deal ID: {result.get('deal')}")
                print(f"   Retcode: {result.get('retcode')}")
                
                # รอ 3 วินาทีแล้วปิดออเดอร์
                print(f"   ⏳ รอ 3 วินาทีแล้วจะปิดออเดอร์...")
                time.sleep(3)
                
                # ตรวจสอบตำแหน่งที่เปิดอยู่
                print(f"   🔍 ตรวจสอบตำแหน่งที่เปิดอยู่...")
                positions = broker_api.get_all_positions()
                if positions:
                    print(f"   พบตำแหน่ง {len(positions)} ตำแหน่ง")
                    for pos in positions:
                        print(f"   - {pos['symbol']} {pos['type']} {pos['volume']} lot (ID: {pos['ticket']})")
                        
                        # ปิดออเดอร์
                        print(f"   🔄 กำลังปิดตำแหน่ง {pos['ticket']}...")
                        if broker_api.close_order(pos['ticket']):
                            print(f"   ✅ ปิดตำแหน่ง {pos['ticket']} สำเร็จ!")
                        else:
                            print(f"   ❌ ปิดตำแหน่ง {pos['ticket']} ไม่สำเร็จ")
                else:
                    print(f"   ℹ️ ไม่พบตำแหน่งที่เปิดอยู่")
                
            else:
                print(f"   ❌ ส่งออเดอร์ไม่สำเร็จ")
                return False
        else:
            print(f"   ❌ ไม่สามารถดึงราคาได้")
            return False
        
        print(f"\n✅ การทดสอบเสร็จสิ้น!")
        return True
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        logger.error(f"Test error: {e}")
        return False
    
    finally:
        # ปิดการเชื่อมต่อ
        if 'broker_api' in locals():
            broker_api.disconnect()
            print("🔌 ปิดการเชื่อมต่อแล้ว")

if __name__ == "__main__":
    success = test_comment_fix()
    if success:
        print("\n🎉 การทดสอบสำเร็จ! ปัญหา comment แก้ไขแล้ว")
    else:
        print("\n💥 การทดสอบล้มเหลว! ยังมีปัญหา comment")
        sys.exit(1)
