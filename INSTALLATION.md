# คู่มือการติดตั้งระบบเทรด Forex AI

## 📋 ข้อกำหนดระบบ

### ระบบปฏิบัติการ
- **Windows 10/11** (แนะนำสำหรับ MetaTrader5)
- **macOS 10.14+** (สำหรับ OANDA/FXCM)
- **Linux Ubuntu 18.04+** (สำหรับ OANDA/FXCM)

### ข้อกำหนดฮาร์ดแวร์
- **CPU**: Intel i5 หรือ AMD Ryzen 5 ขึ้นไป
- **RAM**: อย่างน้อย 4GB (แนะนำ 8GB)
- **Storage**: พื้นที่ว่าง 2GB
- **Network**: การเชื่อมต่ออินเทอร์เน็ตที่เสถียร

### ข้อกำหนดซอฟต์แวร์
- **Python 3.9+** (แนะนำ 3.10)
- **MetaTrader5** (ถ้าใช้ MT5)
- **Git** (สำหรับ Clone โปรเจค)

## 🚀 ขั้นตอนการติดตั้ง

### 1. ติดตั้ง Python

#### Windows
1. ดาวน์โหลด Python จาก [python.org](https://www.python.org/downloads/)
2. เลือกเวอร์ชัน 3.9 หรือใหม่กว่า
3. ติดตั้งโดยเลือก "Add Python to PATH"
4. ตรวจสอบการติดตั้ง:
```cmd
python --version
pip --version
```

#### macOS
```bash
# ใช้ Homebrew
brew install python@3.10

# หรือดาวน์โหลดจาก python.org
```

#### Linux (Ubuntu)
```bash
sudo apt update
sudo apt install python3.10 python3.10-pip python3.10-venv
```

### 2. ติดตั้ง MetaTrader5 (ถ้าใช้)

#### Windows
1. ดาวน์โหลด MetaTrader5 จากเว็บไซต์ Broker ของคุณ
2. ติดตั้งและเข้าสู่ระบบ
3. เปิด Terminal และติดตั้ง Python API:
```cmd
pip install MetaTrader5
```

#### macOS/Linux
- MetaTrader5 ไม่รองรับ macOS/Linux
- ใช้ OANDA หรือ FXCM แทน

### 3. Clone โปรเจค

```bash
# Clone โปรเจค
git clone <repository-url>
cd Arbi

# หรือดาวน์โหลด ZIP และแตกไฟล์
```

### 4. สร้าง Virtual Environment (แนะนำ)

```bash
# สร้าง Virtual Environment
python -m venv venv

# เปิดใช้งาน (Windows)
venv\Scripts\activate

# เปิดใช้งาน (macOS/Linux)
source venv/bin/activate
```

### 5. ติดตั้ง Dependencies

```bash
# ติดตั้งแพ็คเกจทั้งหมด
pip install -r requirements.txt

# หรือติดตั้งทีละแพ็คเกจ
pip install MetaTrader5
pip install pandas
pip install numpy
pip install scikit-learn
pip install matplotlib
pip install tkinter
```

### 6. ตั้งค่า Broker

#### MetaTrader5
1. เปิดไฟล์ `config/broker_config.json`
2. แก้ไขข้อมูลการเชื่อมต่อ:
```json
{
  "MetaTrader5": {
    "server": "YourBroker-Server",
    "login": 123456,
    "password": "your_password",
    "timeout": 30000,
    "portable": false
  }
}
```

#### OANDA
1. สมัครบัญชี OANDA
2. รับ API Token
3. แก้ไขไฟล์ `config/broker_config.json`:
```json
{
  "OANDA": {
    "account_id": "your_account_id",
    "access_token": "your_access_token",
    "environment": "practice",
    "timeout": 30
  }
}
```

#### FXCM
1. สมัครบัญชี FXCM
2. รับ API Credentials
3. แก้ไขไฟล์ `config/broker_config.json`:
```json
{
  "FXCM": {
    "username": "your_username",
    "password": "your_password",
    "environment": "demo",
    "timeout": 30
  }
}
```

### 7. ตั้งค่าระบบ

1. เปิดไฟล์ `config/settings.json`
2. ปรับแต่งพารามิเตอร์ตามต้องการ:

```json
{
  "trading": {
    "base_lot_size": 0.1,
    "max_triangles": 3,
    "min_arbitrage_threshold": 0.3
  },
  "risk_management": {
    "max_daily_loss": 1000,
    "max_drawdown_percent": 30,
    "stop_loss_percent": 2.0
  },
  "ai": {
    "learning_enabled": true,
    "confidence_threshold": 0.7
  }
}
```

### 8. ทดสอบการติดตั้ง

```bash
# ทดสอบการรันระบบ
python main.py --gui

# หรือรันแบบ Command Line
python main.py
```

## 🔧 การแก้ไขปัญหา

### ปัญหาที่พบบ่อย

#### 1. Python ไม่พบ
```bash
# ตรวจสอบ Python
python --version

# ถ้าไม่พบ ให้เพิ่ม Python ไปยัง PATH
```

#### 2. MetaTrader5 ไม่สามารถเชื่อมต่อได้
- ตรวจสอบว่า MetaTrader5 เปิดอยู่
- ตรวจสอบข้อมูลการเข้าสู่ระบบ
- ตรวจสอบการตั้งค่า Server

#### 3. Dependencies ติดตั้งไม่ได้
```bash
# อัปเดต pip
python -m pip install --upgrade pip

# ติดตั้งใหม่
pip install --force-reinstall -r requirements.txt
```

#### 4. GUI ไม่แสดง
- ตรวจสอบการติดตั้ง tkinter
- ตรวจสอบการตั้งค่า Display (Linux)

#### 5. ฐานข้อมูลไม่สร้าง
```bash
# สร้างโฟลเดอร์ data
mkdir data
mkdir logs

# ตรวจสอบสิทธิ์การเขียนไฟล์
```

### การแก้ไขปัญหาเฉพาะระบบ

#### Windows
```cmd
# ติดตั้ง Visual C++ Redistributable
# ดาวน์โหลดจาก Microsoft

# ตรวจสอบ Windows Defender
# เพิ่ม Exception สำหรับโฟลเดอร์โปรเจค
```

#### macOS
```bash
# ติดตั้ง Xcode Command Line Tools
xcode-select --install

# ตั้งค่า Python Path
export PATH="/usr/local/bin:$PATH"
```

#### Linux
```bash
# ติดตั้ง Dependencies
sudo apt install python3-tk
sudo apt install python3-dev
sudo apt install build-essential

# ตั้งค่า Display (ถ้าใช้ SSH)
export DISPLAY=:0
```

## 📁 โครงสร้างไฟล์หลังการติดตั้ง

```
Arbi/
├── main.py                    # ไฟล์หลัก
├── requirements.txt           # รายการ Dependencies
├── README.md                 # คู่มือการใช้งาน
├── INSTALLATION.md           # คู่มือการติดตั้ง
├── config/                   # ไฟล์การตั้งค่า
│   ├── rules.json
│   ├── settings.json
│   └── broker_config.json
├── trading/                  # ระบบเทรด
├── ai/                      # ระบบ AI
├── gui/                     # หน้าจอผู้ใช้
├── data/                    # ข้อมูลและฐานข้อมูล
├── utils/                   # เครื่องมือช่วย
├── logs/                    # ไฟล์ Log (สร้างอัตโนมัติ)
└── venv/                    # Virtual Environment (ถ้าใช้)
```

## 🧪 การทดสอบระบบ

### 1. ทดสอบการเชื่อมต่อ Broker
```python
# สร้างไฟล์ test_connection.py
from trading.broker_api import BrokerAPI

broker = BrokerAPI("MetaTrader5")
success = broker.connect(login=123456, password="your_password")
print(f"Connection: {'Success' if success else 'Failed'}")
```

### 2. ทดสอบการคำนวณ Arbitrage
```python
# สร้างไฟล์ test_arbitrage.py
from utils.calculations import TradingCalculations

calc = TradingCalculations()
arbitrage = calc.calculate_arbitrage_percentage(1.1000, 110.00, 121.50)
print(f"Arbitrage: {arbitrage:.4f}%")
```

### 3. ทดสอบ GUI
```bash
# รัน GUI
python main.py --gui

# ตรวจสอบว่าหน้าจอแสดงขึ้นมา
```

## 📊 การตรวจสอบประสิทธิภาพ

### 1. ตรวจสอบการใช้ Memory
```python
import psutil
import os

process = psutil.Process(os.getpid())
memory_usage = process.memory_info().rss / 1024 / 1024
print(f"Memory Usage: {memory_usage:.2f} MB")
```

### 2. ตรวจสอบการเชื่อมต่อ Network
```python
import socket

def test_connection(host, port):
    try:
        socket.create_connection((host, port), timeout=5)
        return True
    except:
        return False

# ทดสอบการเชื่อมต่อ Broker
print(f"MT5 Connection: {test_connection('localhost', 8080)}")
```

## 🔄 การอัปเดตระบบ

### 1. อัปเดตโค้ด
```bash
# Pull การเปลี่ยนแปลงล่าสุด
git pull origin main

# ติดตั้ง Dependencies ใหม่
pip install -r requirements.txt
```

### 2. อัปเดตการตั้งค่า
- ตรวจสอบไฟล์ `config/settings.json`
- เปรียบเทียบกับเวอร์ชันเก่า
- ปรับแต่งตามต้องการ

### 3. อัปเดตฐานข้อมูล
```python
# รัน Migration Script (ถ้ามี)
python migrate_database.py
```

## 🗑️ การถอนการติดตั้ง

### 1. หยุดระบบ
- ปิด GUI
- หยุดการเทรด
- ปิดการเชื่อมต่อ Broker

### 2. ลบไฟล์
```bash
# ลบ Virtual Environment
rm -rf venv

# ลบ Log Files
rm -rf logs

# ลบฐานข้อมูล (ระวัง!)
rm -rf data
```

### 3. ลบ Dependencies
```bash
# ถอนการติดตั้งแพ็คเกจ
pip uninstall -r requirements.txt -y
```

## 📞 การขอความช่วยเหลือ

### 1. ตรวจสอบ Log Files
- ดูไฟล์ในโฟลเดอร์ `logs/`
- หาข้อผิดพลาดใน `errors_*.log`

### 2. ตรวจสอบการตั้งค่า
- ตรวจสอบไฟล์ใน `config/`
- เปรียบเทียบกับตัวอย่าง

### 3. ทดสอบทีละส่วน
- ทดสอบการเชื่อมต่อ Broker
- ทดสอบการคำนวณ
- ทดสอบ GUI

### 4. รีสตาร์ทระบบ
```bash
# รีสตาร์ท Python
python main.py --gui

# รีสตาร์ท MetaTrader5
# ปิดและเปิดใหม่
```

---

**หมายเหตุ**: หากพบปัญหาที่ไม่สามารถแก้ไขได้ ให้ตรวจสอบ Log Files และสร้าง Issue ใน Repository
