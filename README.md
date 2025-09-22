# ระบบเทรด Forex AI - Triangular Arbitrage & Correlation Recovery

## 🎯 ภาพรวม

ระบบเทรดอัตโนมัติที่ใช้ AI ในการตรวจจับและทำกำไรจากโอกาส Triangular Arbitrage และการกู้คืนตำแหน่งด้วย Correlation Analysis

## 🚀 ฟีเจอร์หลัก

- **Triangular Arbitrage Detection**: ตรวจจับโอกาส Arbitrage แบบสามเหลี่ยม
- **Correlation Recovery**: ระบบกู้คืนตำแหน่งด้วยความสัมพันธ์ระหว่างคู่เงิน
- **AI Rule Engine**: ระบบ AI ที่ใช้กฎเกณฑ์และ Machine Learning
- **Real-time GUI**: หน้าจอควบคุมแบบเรียลไทม์
- **Risk Management**: ระบบจัดการความเสี่ยงที่ครบถ้วน

## 📦 การติดตั้ง

```bash
# Clone repository
git clone <repository-url>
cd Arbi

# ติดตั้ง dependencies
pip install -r requirements.txt

# รันระบบ
python run.py --gui
```

## 📁 โครงสร้างโปรเจค

```
Arbi/
├── main.py                    # ไฟล์หลัก
├── run.py                     # สคริปต์รัน
├── requirements.txt           # Dependencies
├── config/                    # การตั้งค่า
├── trading/                   # ระบบเทรด
├── ai/                       # AI Engine
├── gui/                      # หน้าจอผู้ใช้
├── data/                     # ข้อมูล
└── utils/                    # เครื่องมือช่วย
```

## 🎮 การใช้งาน

1. ตั้งค่า Broker ใน `config/broker_config.json`
2. รันระบบ: `python run.py --gui`
3. เชื่อมต่อ Broker
4. เริ่มเทรด

## 📚 เอกสาร

- [คู่มือการติดตั้ง](INSTALLATION.md)
- [คู่มือการใช้งาน](USER_GUIDE.md)

## ⚠️ คำเตือน

ระบบนี้ใช้สำหรับการศึกษาและทดสอบเท่านั้น การเทรดมีความเสี่ยงสูง

## 📄 License

MIT License