#!/usr/bin/env python3
"""
Test Script สำหรับทดสอบ Risk-Based Lot Calculation
รันบน VPS เพื่อตรวจสอบว่าทำงานถูกต้องหรือไม่
"""

import sys
import os
sys.path.append('.')

def test_risk_calculation():
    print("="*60)
    print("🧪 TESTING RISK-BASED LOT CALCULATION")
    print("="*60)
    
    try:
        # 1. ตรวจสอบ config
        from utils.config_helper import load_config
        config = load_config('adaptive_params.json')
        
        lot_calc = config.get('position_sizing', {}).get('lot_calculation', {})
        print("\n1. Config Values:")
        print(f"   use_risk_based_sizing: {lot_calc.get('use_risk_based_sizing')}")
        print(f"   use_simple_mode: {lot_calc.get('use_simple_mode')}")
        print(f"   risk_per_trade_percent: {lot_calc.get('risk_per_trade_percent')}")
        
        # 2. ทดสอบการคำนวณด้วย manual calculation
        balance = 87995.12
        risk_percent = lot_calc.get('risk_per_trade_percent', 1.5)
        
        print(f"\n2. Manual Calculation:")
        print(f"   Balance: ${balance:,.2f}")
        print(f"   Risk: {risk_percent}%")
        
        risk_amount = balance * (risk_percent / 100.0)
        risk_per_pair = risk_amount / 3.0
        
        print(f"   Risk Amount: ${risk_amount:,.2f}")
        print(f"   Risk per Pair: ${risk_per_pair:,.2f}")
        
        # คำนวณ lot size (สมมติ EURUSD, pip value = $1 per 0.01 lot)
        pip_value_per_001 = 1.0
        stop_loss_pips = 50.0
        
        expected_lot = (risk_per_pair / (stop_loss_pips * pip_value_per_001)) * 0.01
        print(f"   Expected Lot Size: {expected_lot:.4f}")
        
        # 3. ทดสอบฟังก์ชันจริง (ถ้าไม่มี numpy error)
        print(f"\n3. Testing get_uniform_triangle_lots function:")
        try:
            from utils.calculations import TradingCalculations
            
            # สร้าง mock broker
            class MockBroker:
                def get_symbol_info(self, symbol):
                    return {
                        'digits': 5,
                        'point': 0.00001,
                        'contract_size': 100000
                    }
                def get_account_info(self):
                    return {'balance': balance}
            
            mock_broker = MockBroker()
            symbols = ["EURUSD", "GBPUSD", "EURGBP"]
            
            lots = TradingCalculations.get_uniform_triangle_lots(
                triangle_symbols=symbols,
                balance=balance,
                target_pip_value=5.0,
                broker_api=mock_broker,
                use_simple_mode=False,
                use_risk_based_sizing=True,
                risk_per_trade_percent=risk_percent
            )
            
            print(f"   Function Result: {lots}")
            
            if lots:
                avg_lot = sum(lots.values()) / len(lots)
                print(f"   Average Lot: {avg_lot:.4f}")
                
                if abs(avg_lot - expected_lot) < 0.01:
                    print("   ✅ Function result matches expected calculation")
                else:
                    print(f"   ❌ Function result differs from expected")
                    print(f"      Expected: {expected_lot:.4f}")
                    print(f"      Got: {avg_lot:.4f}")
            else:
                print("   ❌ Function returned empty result")
                
        except Exception as e:
            print(f"   ❌ Function test failed: {e}")
        
        # 4. ตรวจสอบว่า arbitrage_detector เรียกใช้ถูกต้องหรือไม่
        print(f"\n4. Checking arbitrage_detector code:")
        try:
            with open('trading/arbitrage_detector.py', 'r', encoding='utf-8') as f:
                arb_content = f.read()
            
            if 'use_risk_based_sizing=use_risk_based_sizing' in arb_content:
                print("   ✅ arbitrage_detector passes use_risk_based_sizing")
            else:
                print("   ❌ arbitrage_detector does NOT pass use_risk_based_sizing")
                
            if 'risk_per_trade_percent=risk_per_trade_percent' in arb_content:
                print("   ✅ arbitrage_detector passes risk_per_trade_percent")
            else:
                print("   ❌ arbitrage_detector does NOT pass risk_per_trade_percent")
                
        except Exception as e:
            print(f"   ❌ Cannot check arbitrage_detector: {e}")
        
        print("\n" + "="*60)
        print("📋 สรุป:")
        print(f"   - Balance: ${balance:,.2f}")
        print(f"   - Risk: {risk_percent}%")
        print(f"   - Expected Lot: {expected_lot:.4f}")
        print(f"   - Current Lot: 1.0 (จากภาพ)")
        print(f"   - Difference: {1.0/expected_lot:.1f}x too large")
        print("="*60)
        
        if expected_lot < 0.5:
            print("\n🎯 หากได้ lot = 1.0 แทน {:.4f}:".format(expected_lot))
            print("   ระบบยังไม่ใช้ risk-based calculation")
            print("   อาจเป็นเพราะ:")
            print("   1. ยังไม่ได้ restart ระบบ")
            print("   2. มี hardcoded lot size ที่อื่น")
            print("   3. risk-based logic มี bug")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_risk_calculation()
