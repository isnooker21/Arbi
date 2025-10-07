#!/usr/bin/env python3
"""
Debug Config Script - ตรวจสอบ config paths และ values
"""

import sys
import os
import json
sys.path.append('.')

def debug_config():
    print("="*60)
    print("🔍 DEBUG CONFIG PATHS AND VALUES")
    print("="*60)
    
    try:
        from utils.config_helper import get_config_path, get_user_config_path, load_config, save_config
        
        # 1. ตรวจสอบ paths
        print("\n1. Config Paths:")
        config_path = get_config_path('adaptive_params.json')
        user_config_path = get_user_config_path('adaptive_params.json')
        
        print(f"   get_config_path(): {config_path}")
        print(f"   get_user_config_path(): {user_config_path}")
        print(f"   Same path: {config_path == user_config_path}")
        
        # 2. ตรวจสอบไฟล์
        print(f"\n2. File Existence:")
        print(f"   Config file exists: {os.path.exists(config_path)}")
        print(f"   User config file exists: {os.path.exists(user_config_path)}")
        
        # 3. ตรวจสอบ content ของไฟล์ทั้งสอง
        if os.path.exists(config_path):
            print(f"\n3. Config file content ({config_path}):")
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = json.load(f)
            
            lot_calc = config_content.get('position_sizing', {}).get('lot_calculation', {})
            print(f"   use_risk_based_sizing: {lot_calc.get('use_risk_based_sizing')}")
            print(f"   use_simple_mode: {lot_calc.get('use_simple_mode')}")
            print(f"   risk_per_trade_percent: {lot_calc.get('risk_per_trade_percent')}")
        
        if os.path.exists(user_config_path) and user_config_path != config_path:
            print(f"\n4. User config file content ({user_config_path}):")
            with open(user_config_path, 'r', encoding='utf-8') as f:
                user_content = json.load(f)
            
            lot_calc = user_content.get('position_sizing', {}).get('lot_calculation', {})
            print(f"   use_risk_based_sizing: {lot_calc.get('use_risk_based_sizing')}")
            print(f"   use_simple_mode: {lot_calc.get('use_simple_mode')}")
            print(f"   risk_per_trade_percent: {lot_calc.get('risk_per_trade_percent')}")
        
        # 4. ตรวจสอบ load_config function
        print(f"\n5. load_config() result:")
        loaded_config = load_config('adaptive_params.json')
        
        if loaded_config:
            lot_calc = loaded_config.get('position_sizing', {}).get('lot_calculation', {})
            print(f"   use_risk_based_sizing: {lot_calc.get('use_risk_based_sizing')}")
            print(f"   use_simple_mode: {lot_calc.get('use_simple_mode')}")
            print(f"   risk_per_trade_percent: {lot_calc.get('risk_per_trade_percent')}")
        else:
            print("   ❌ load_config() returned empty")
        
        # 5. แก้ไข config ถ้าจำเป็น
        print(f"\n6. Fixing config if needed:")
        if not loaded_config or loaded_config.get('position_sizing', {}).get('lot_calculation', {}).get('use_risk_based_sizing') != True:
            print("   Config needs fixing...")
            
            # โหลด config ใหม่
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            else:
                print("   ❌ Config file not found!")
                return
            
            # แก้ไขค่า
            config_data['position_sizing']['lot_calculation']['use_risk_based_sizing'] = True
            config_data['position_sizing']['lot_calculation']['use_simple_mode'] = False
            config_data['position_sizing']['lot_calculation']['risk_per_trade_percent'] = 1.5
            
            # บันทึก
            result = save_config('adaptive_params.json', config_data)
            print(f"   Save result: {result}")
            
            # ตรวจสอบอีกครั้ง
            print(f"\n7. Verifying fix:")
            reloaded = load_config('adaptive_params.json')
            if reloaded:
                lot_calc = reloaded.get('position_sizing', {}).get('lot_calculation', {})
                print(f"   use_risk_based_sizing: {lot_calc.get('use_risk_based_sizing')}")
                print(f"   use_simple_mode: {lot_calc.get('use_simple_mode')}")
                print(f"   risk_per_trade_percent: {lot_calc.get('risk_per_trade_percent')}")
                
                if lot_calc.get('use_risk_based_sizing') == True:
                    print("   ✅ Config fixed successfully!")
                else:
                    print("   ❌ Config still not fixed")
            else:
                print("   ❌ Cannot reload config")
        else:
            print("   ✅ Config is already correct")
        
        print("\n" + "="*60)
        print("📋 สรุป:")
        print("   หาก config ถูกต้องแล้ว แต่ test ยังได้ lot = 1.0")
        print("   แสดงว่าปัญหาอยู่ในฟังก์ชัน get_uniform_triangle_lots")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_config()
