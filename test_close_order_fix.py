#!/usr/bin/env python3
"""
ทดสอบการแก้ไขปัญหาการปิดออเดอร์
"""

print("🔧 การแก้ไขปัญหาการปิดออเดอร์")
print("=" * 50)

print("\n✅ ปัญหาที่พบ:")
print("   - Error 10030: Unsupported filling mode")
print("   - การปิดออเดอร์ใช้ filling type ที่ไม่ถูกต้อง")

print("\n🔧 การแก้ไขที่ทำ:")
print("   1. ปรับปรุงฟังก์ชัน close_order() ให้ใช้ filling type ที่เหมาะสม")
print("   2. เพิ่มการตรวจสอบ symbol_info ก่อนปิดออเดอร์")
print("   3. ใช้ฟังก์ชัน _get_filling_type() สำหรับการปิดออเดอร์")
print("   4. เพิ่มการจัดการ error ที่ดีขึ้น")

print("\n📝 การเปลี่ยนแปลงหลัก:")
print("   - เปลี่ยนจาก ORDER_FILLING_IOC เป็น filling type ที่เหมาะสม")
print("   - เพิ่มการตรวจสอบ filling_mode ของ symbol")
print("   - เพิ่ม error message สำหรับ error code 10030")

print("\n🧪 วิธีทดสอบ:")
print("   1. เปิด MT5 และ login")
print("   2. รัน: python test_order_sending.py")
print("   3. ตรวจสอบว่าการปิดออเดอร์สำเร็จ")

print("\n⚠️  หมายเหตุ:")
print("   - ต้องติดตั้ง MetaTrader5: pip install MetaTrader5")
print("   - ต้องเปิด MT5 และ login ก่อนทดสอบ")
print("   - การทดสอบจะส่งออเดอร์จริงขนาด 0.01 lot")

print("\n✅ การแก้ไขเสร็จสิ้น!")
print("   ระบบควรสามารถปิดออเดอร์ได้แล้ว")
