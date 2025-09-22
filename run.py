#!/usr/bin/env python3
"""
สคริปต์สำหรับรันระบบเทรด Forex AI
รองรับการรันแบบ GUI และ Command Line

การใช้งาน:
    python run.py                    # รันแบบ GUI
    python run.py --gui             # รันแบบ GUI
    python run.py --cli             # รันแบบ Command Line
    python run.py --test            # รันแบบทดสอบ
    python run.py --help            # แสดงความช่วยเหลือ
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# เพิ่ม path ของโปรเจค
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """ตั้งค่าระบบ Logging"""
    # สร้างโฟลเดอร์ logs
    os.makedirs("logs", exist_ok=True)
    
    # ตั้งค่า logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f"logs/run_{datetime.now().strftime('%Y%m%d')}.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def run_gui():
    """รันระบบแบบ GUI"""
    try:
        print("🚀 กำลังเริ่มระบบเทรด Forex AI แบบ GUI...")
        
        # ใช้ main.py แทน
        from main import main
        main()
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการรัน GUI: {e}")
        sys.exit(1)

def run_cli():
    """รันระบบแบบ Command Line"""
    try:
        print("🚀 กำลังเริ่มระบบเทรด Forex AI แบบ Command Line...")
        
        # ใช้ main.py แทน
        import sys
        sys.argv = ['main.py', '--cli']
        from main import main
        main()
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการรัน CLI: {e}")
        sys.exit(1)

def run_auto_setup():
    """รัน Auto Setup"""
    try:
        print("🔧 กำลังทำ Auto Setup...")
        
        # ใช้ main.py แทน
        import sys
        sys.argv = ['main.py', '--cli']  # ใช้ CLI mode เพื่อทำ auto setup
        from main import main
        main()
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดใน Auto Setup: {e}")
        sys.exit(1)

def run_test():
    """รันระบบแบบทดสอบ"""
    try:
        print("🧪 กำลังทดสอบระบบเทรด Forex AI...")
        
        # ทดสอบการ import modules
        print("📦 ทดสอบการ import modules...")
        
        try:
            from trading.broker_api import BrokerAPI
            print("   ✓ BrokerAPI")
        except Exception as e:
            print(f"   ✗ BrokerAPI: {e}")
        
        try:
            from trading.arbitrage_detector import TriangleArbitrageDetector
            print("   ✓ TriangleArbitrageDetector")
        except Exception as e:
            print(f"   ✗ TriangleArbitrageDetector: {e}")
        
        try:
            from ai.rule_engine import RuleEngine
            print("   ✓ RuleEngine")
        except Exception as e:
            print(f"   ✗ RuleEngine: {e}")
        
        try:
            from gui.main_window import MainWindow
            print("   ✓ MainWindow")
        except Exception as e:
            print(f"   ✗ MainWindow: {e}")
        
        # ทดสอบการคำนวณ
        print("\n🧮 ทดสอบการคำนวณ...")
        
        try:
            from utils.calculations import TradingCalculations
            calc = TradingCalculations()
            
            # ทดสอบการคำนวณ Arbitrage
            arbitrage = calc.calculate_arbitrage_percentage(1.1000, 110.00, 121.50)
            print(f"   ✓ Arbitrage Calculation: {arbitrage:.4f}%")
            
            # ทดสอบการคำนวณ Correlation
            prices1 = [1.1000, 1.1010, 1.1020, 1.1030, 1.1040]
            prices2 = [110.00, 110.10, 110.20, 110.30, 110.40]
            correlation = calc.calculate_correlation(prices1, prices2)
            print(f"   ✓ Correlation Calculation: {correlation:.4f}")
            
        except Exception as e:
            print(f"   ✗ Calculations: {e}")
        
        # ทดสอบการตั้งค่า
        print("\n⚙️ ทดสอบการตั้งค่า...")
        
        try:
            import json
            
            # ตรวจสอบไฟล์การตั้งค่า
            with open('config/settings.json', 'r') as f:
                settings = json.load(f)
            print("   ✓ Settings file")
            
            with open('config/rules.json', 'r') as f:
                rules = json.load(f)
            print("   ✓ Rules file")
            
            with open('config/broker_config.json', 'r') as f:
                broker_config = json.load(f)
            print("   ✓ Broker config file")
            
        except Exception as e:
            print(f"   ✗ Configuration: {e}")
        
        # ทดสอบการสร้างโฟลเดอร์
        print("\n📁 ทดสอบการสร้างโฟลเดอร์...")
        
        try:
            os.makedirs("data", exist_ok=True)
            os.makedirs("logs", exist_ok=True)
            print("   ✓ Data and logs directories")
        except Exception as e:
            print(f"   ✗ Directories: {e}")
        
        print("\n✅ การทดสอบเสร็จสิ้น")
        print("📝 หากมีข้อผิดพลาด ให้ตรวจสอบการติดตั้ง Dependencies")
        print("📝 ใช้ pip install -r requirements.txt เพื่อติดตั้งแพ็คเกจ")
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการทดสอบ: {e}")
        sys.exit(1)

def show_help():
    """แสดงความช่วยเหลือ"""
    print("""
🎯 ระบบเทรด Forex AI - คู่มือการใช้งาน

การใช้งาน:
    python run.py                    # รันแบบ GUI (แนะนำ)
    python run.py --gui             # รันแบบ GUI
    python run.py --auto-setup      # ทำ Auto Setup (แนะนำสำหรับผู้ใช้ใหม่)
    python run.py --cli             # รันแบบ Command Line
    python run.py --test            # รันแบบทดสอบ
    python run.py --help            # แสดงความช่วยเหลือนี้

ฟีเจอร์หลัก:
    🔍 Triangular Arbitrage Detection
    🔗 Correlation Recovery System
    🤖 AI Rule Engine
    📊 Real-time Charts
    ⚙️ Risk Management
    📈 Performance Tracking

การตั้งค่า:
    1. ตั้งค่า Broker ใน config/broker_config.json
    2. ตั้งค่าระบบใน config/settings.json
    3. ปรับแต่งกฎเกณฑ์ AI ใน config/rules.json

การแก้ไขปัญหา:
    - ตรวจสอบ Log Files ในโฟลเดอร์ logs/
    - ใช้ --test เพื่อทดสอบระบบ
    - ตรวจสอบการติดตั้ง Dependencies

📚 เอกสารเพิ่มเติม:
    - README.md: ภาพรวมระบบ
    - INSTALLATION.md: คู่มือการติดตั้ง
    - USER_GUIDE.md: คู่มือการใช้งาน
""")

def main():
    """ฟังก์ชันหลัก"""
    # ตั้งค่า logging
    logger = setup_logging()
    
    # สร้าง argument parser
    parser = argparse.ArgumentParser(
        description="ระบบเทรด Forex AI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--gui', 
        action='store_true', 
        help='รันแบบ GUI (ค่าเริ่มต้น)'
    )
    
    parser.add_argument(
        '--cli', 
        action='store_true', 
        help='รันแบบ Command Line'
    )
    
    parser.add_argument(
        '--test', 
        action='store_true', 
        help='รันแบบทดสอบ'
    )
    
    parser.add_argument(
        '--auto-setup', 
        action='store_true', 
        help='ทำ Auto Setup ระบบ (แนะนำสำหรับผู้ใช้ใหม่)'
    )
    
    parser.add_argument(
        '--help', 
        action='store_true', 
        help='แสดงความช่วยเหลือ'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # แสดงข้อความต้อนรับ
    print("=" * 60)
    print("🎯 ระบบเทรด Forex AI")
    print("   Triangular Arbitrage & Correlation Recovery")
    print("   พร้อม AI Engine และ GUI")
    print("=" * 60)
    
    # ตรวจสอบ arguments
    if args.help:
        show_help()
    elif args.auto_setup:
        run_auto_setup()
    elif args.test:
        run_test()
    elif args.cli:
        run_cli()
    else:
        # ค่าเริ่มต้นคือ GUI
        run_gui()

if __name__ == "__main__":
    main()
