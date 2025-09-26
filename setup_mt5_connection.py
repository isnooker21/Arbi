#!/usr/bin/env python3
"""
Script สำหรับตั้งค่าเชื่อมต่อ MT5
"""

import json
import os
import sys

def setup_mt5_connection():
    """ตั้งค่าเชื่อมต่อ MT5"""
    print("=" * 60)
    print("🔧 ตั้งค่าเชื่อมต่อ MetaTrader 5")
    print("=" * 60)
    
    # ตรวจสอบไฟล์ config
    config_file = "config/broker_config.json"
    if not os.path.exists(config_file):
        print(f"❌ ไม่พบไฟล์ {config_file}")
        return False
    
    # อ่าน config ปัจจุบัน
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ ไม่สามารถอ่านไฟล์ config: {e}")
        return False
    
    print("\n📋 ข้อมูลการเชื่อมต่อ MT5 ปัจจุบัน:")
    mt5_config = config.get('MetaTrader5', {})
    print(f"   Server: {mt5_config.get('server', 'Not set')}")
    print(f"   Login: {mt5_config.get('login', 'Not set')}")
    print(f"   Password: {'*' * len(str(mt5_config.get('password', ''))) if mt5_config.get('password') else 'Not set'}")
    
    print("\n🔧 กรุณาใส่ข้อมูลการเชื่อมต่อ MT5:")
    
    # รับข้อมูลจากผู้ใช้
    server = input("Server (เช่น: YourBroker-Server): ").strip()
    if not server:
        print("❌ ต้องใส่ Server")
        return False
    
    login = input("Login (Account Number): ").strip()
    if not login:
        print("❌ ต้องใส่ Login")
        return False
    
    try:
        login = int(login)
    except ValueError:
        print("❌ Login ต้องเป็นตัวเลข")
        return False
    
    password = input("Password: ").strip()
    if not password:
        print("❌ ต้องใส่ Password")
        return False
    
    # อัพเดท config
    config['MetaTrader5'] = {
        'server': server,
        'login': login,
        'password': password,
        'timeout': 30000,
        'portable': False
    }
    
    # บันทึก config
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"\n✅ บันทึกการตั้งค่าเรียบร้อยแล้วใน {config_file}")
    except Exception as e:
        print(f"❌ ไม่สามารถบันทึกไฟล์ config: {e}")
        return False
    
    # ทดสอบการเชื่อมต่อ
    print("\n🔍 ทดสอบการเชื่อมต่อ MT5...")
    try:
        import MetaTrader5 as mt5
        
        # Initialize MT5
        if not mt5.initialize():
            print("❌ ไม่สามารถ initialize MT5")
            return False
        
        # Login
        if mt5.login(login, password=password, server=server):
            account_info = mt5.account_info()
            if account_info:
                print("✅ เชื่อมต่อ MT5 สำเร็จ!")
                print(f"   Account: {account_info.login}")
                print(f"   Server: {account_info.server}")
                print(f"   Balance: {account_info.balance}")
                print(f"   Equity: {account_info.equity}")
                return True
            else:
                print("❌ Login สำเร็จแต่ไม่ได้รับข้อมูลบัญชี")
                return False
        else:
            error_code = mt5.last_error()
            print(f"❌ Login ไม่สำเร็จ - Error Code: {error_code}")
            return False
            
    except ImportError:
        print("❌ ไม่พบ MetaTrader5 package")
        print("   กรุณาติดตั้ง: pip install MetaTrader5")
        return False
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        return False
    finally:
        try:
            mt5.shutdown()
        except:
            pass

def main():
    """Main function"""
    if setup_mt5_connection():
        print("\n🎉 ตั้งค่าเชื่อมต่อ MT5 เรียบร้อยแล้ว!")
        print("   ตอนนี้สามารถรันระบบเทรดได้แล้ว")
    else:
        print("\n❌ ตั้งค่าเชื่อมต่อ MT5 ไม่สำเร็จ")
        print("   กรุณาตรวจสอบข้อมูลการเชื่อมต่อและลองใหม่")

if __name__ == "__main__":
    main()
