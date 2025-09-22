# คู่มือการใช้งานระบบเทรด Forex AI

## 🎯 ภาพรวมการใช้งาน

ระบบเทรด Forex AI นี้ถูกออกแบบมาให้ใช้งานง่ายและมีประสิทธิภาพ โดยมีฟีเจอร์หลักคือการตรวจจับ Triangular Arbitrage และการกู้คืนตำแหน่งด้วย Correlation Analysis

## 🚀 การเริ่มต้นใช้งาน

### 1. เปิดระบบ
```bash
# รันแบบ GUI (แนะนำ)
python main.py --gui

# รันแบบ Command Line
python main.py
```

### 2. เชื่อมต่อ Broker
1. ใส่ข้อมูลการเข้าสู่ระบบ Broker
2. เลือกประเภท Broker (MetaTrader5, OANDA, FXCM)
3. คลิก "Connect"
4. รอจนกว่าจะแสดงสถานะ "Connected"

### 3. เริ่มเทรด
1. ตรวจสอบการตั้งค่าความเสี่ยง
2. เปิดใช้งานระบบ Arbitrage และ/หรือ Correlation
3. คลิก "START TRADING"
4. ติดตามผลการเทรดในหน้าจอ

## 🖥️ หน้าจอหลัก (Main Window)

### Connection Panel
- **Broker**: เลือกประเภท Broker
- **Login**: หมายเลขบัญชี
- **Password**: รหัสผ่าน
- **Auto Login**: เข้าสู่ระบบอัตโนมัติ
- **Connect**: เชื่อมต่อกับ Broker

### Control Panel
- **Arbitrage System**: เปิด/ปิดระบบ Arbitrage
- **Correlation System**: เปิด/ปิดระบบ Correlation
- **START TRADING**: เริ่มเทรด
- **STOP TRADING**: หยุดเทรด
- **EMERGENCY STOP**: หยุดฉุกเฉิน

### AI Engine Status
- **AI Status**: สถานะ AI Engine
- **Active Rules**: จำนวนกฎเกณฑ์ที่ใช้งาน
- **Confidence**: ระดับความเชื่อมั่น
- **Last Decision**: การตัดสินใจล่าสุด

### Monitoring Panel
#### Positions Tab
แสดงตำแหน่งที่เปิดอยู่:
- **Symbol**: คู่เงิน
- **Type**: ประเภท (BUY/SELL)
- **Volume**: ขนาด
- **Price**: ราคา
- **PnL**: กำไร/ขาดทุน
- **Status**: สถานะ

#### Performance Tab
แสดงผลการดำเนินงาน:
- **Total PnL**: กำไร/ขาดทุนรวม
- **Win Rate**: อัตราชนะ
- **Total Trades**: จำนวนการเทรด
- **Active Triangles**: จำนวน Arbitrage ที่เปิดอยู่

## 📊 AI Dashboard

### เปิด AI Dashboard
1. คลิกปุ่ม "AI Dashboard" ในหน้าจอหลัก
2. หรือใช้เมนู "View" → "AI Dashboard"

### Rule Engine Tab
- **Rule Statistics**: สถิติกฎเกณฑ์
- **Rule Performance**: ประสิทธิภาพของกฎเกณฑ์
- **Refresh**: อัปเดตข้อมูล

### Learning Module Tab
- **Learning Statistics**: สถิติการเรียนรู้
- **Train Classifier**: ฝึกโมเดล AI
- **Identify Patterns**: หารูปแบบการเทรด
- **Optimize Rules**: ปรับปรุงกฎเกณฑ์

### Performance Tab
- **Performance Metrics**: ตัวชี้วัดประสิทธิภาพ
- **Performance Chart**: กราฟผลการดำเนินงาน
- **Drawdown Chart**: กราฟการขาดทุน

### Market Analysis Tab
- **Market Conditions**: สภาพตลาดปัจจุบัน
- **Volatility Chart**: กราฟความผันผวน
- **Correlation Matrix**: เมทริกซ์ความสัมพันธ์

## 📈 Charts Window

### เปิด Charts
1. คลิกปุ่ม "Charts" ในหน้าจอหลัก
2. หรือใช้เมนู "View" → "Charts"

### Price Charts Tab
- **Symbol**: เลือกคู่เงิน
- **Timeframe**: เลือก Timeframe
- **Start Updates**: เริ่มอัปเดต
- **Stop Updates**: หยุดอัปเดต

### Arbitrage Opportunities Tab
- **Arbitrage Over Time**: กราฟโอกาส Arbitrage
- **Arbitrage Distribution**: การกระจายของ Arbitrage

### Performance Tab
- **Cumulative PnL**: กราฟกำไร/ขาดทุนสะสม
- **Drawdown**: กราฟการขาดทุน

### Market Analysis Tab
- **Volatility by Symbol**: ความผันผวนตามคู่เงิน
- **Trend Distribution**: การกระจายของเทรนด์
- **Correlation Matrix**: เมทริกซ์ความสัมพันธ์
- **Market Sentiment**: ความรู้สึกของตลาด

## ⚙️ Settings Window

### เปิด Settings
1. คลิกปุ่ม "Settings" ในหน้าจอหลัก
2. หรือใช้เมนู "Tools" → "Settings"

### Trading Tab
- **Base Lot Size**: ขนาดตำแหน่งพื้นฐาน
- **Max Triangles**: จำนวน Arbitrage สูงสุด
- **Min Arbitrage Threshold**: ขีดจำกัด Arbitrage ต่ำสุด
- **Max Spread**: Spread สูงสุด
- **Position Hold Time**: เวลาถือตำแหน่ง

### Risk Management Tab
- **Max Daily Loss**: การขาดทุนรายวันสูงสุด
- **Max Drawdown %**: การขาดทุนสูงสุด (%)
- **Position Size Multiplier**: ตัวคูณขนาดตำแหน่ง
- **Stop Loss %**: Stop Loss (%)
- **Take Profit %**: Take Profit (%)

### AI Engine Tab
- **Learning Enabled**: เปิดใช้งานการเรียนรู้
- **Rule Adaptation Frequency**: ความถี่การปรับกฎเกณฑ์
- **Confidence Threshold**: ขีดจำกัดความเชื่อมั่น
- **Max Rules Per Category**: จำนวนกฎเกณฑ์สูงสุดต่อหมวด
- **Performance Lookback Days**: จำนวนวันย้อนหลัง

### Broker Tab
- **Default Broker**: Broker เริ่มต้น
- **Connection Timeout**: หมดเวลาการเชื่อมต่อ
- **Retry Attempts**: จำนวนครั้งลองใหม่
- **Data Refresh Rate**: อัตราการอัปเดตข้อมูล

### GUI Tab
- **Theme**: ธีม
- **Chart Refresh Rate**: อัตราการอัปเดตกราฟ
- **Log Max Lines**: จำนวนบรรทัด Log สูงสุด
- **Window Size**: ขนาดหน้าต่าง

### Rules Tab
- **Load from File**: โหลดกฎเกณฑ์จากไฟล์
- **Save to File**: บันทึกกฎเกณฑ์ลงไฟล์
- **Reset to Default**: รีเซ็ตเป็นค่าเริ่มต้น

## 🔧 การปรับแต่งระบบ

### 1. การปรับแต่งกฎเกณฑ์ AI

#### แก้ไขไฟล์ rules.json
```json
{
  "arbitrage_rules": [
    {
      "id": "AD-001",
      "name": "High Volatility Arbitrage",
      "category": "arbitrage_detection",
      "weight": 0.8,
      "confidence": 0.75,
      "conditions": [
        "volatility > 0.5",
        "arbitrage_percent > 0.3",
        "spread_acceptable == true"
      ],
      "actions": [
        "SET arbitrage_confidence = 0.75",
        "SET proceed_to_entry = true"
      ]
    }
  ]
}
```

#### ตัวอย่างกฎเกณฑ์
- **Asian Session**: ถ้าเป็นช่วง Asian Session และ Arbitrage > 0.2% → เปิดตำแหน่ง
- **High Volatility**: ถ้า Volatility สูงและ Spread ต่ำ → เพิ่มขนาดตำแหน่ง
- **Risk Management**: ถ้า Drawdown > 30% → หยุดเทรด

### 2. การปรับแต่งการตั้งค่า

#### การตั้งค่าความเสี่ยง
```json
{
  "risk_management": {
    "max_daily_loss": 1000,        // การขาดทุนรายวันสูงสุด
    "max_drawdown_percent": 30,    // การขาดทุนสูงสุด (%)
    "stop_loss_percent": 2.0,      // Stop Loss (%)
    "take_profit_percent": 1.0     // Take Profit (%)
  }
}
```

#### การตั้งค่าระบบเทรด
```json
{
  "trading": {
    "base_lot_size": 0.1,          // ขนาดตำแหน่งพื้นฐาน
    "max_triangles": 3,            // จำนวน Arbitrage สูงสุด
    "min_arbitrage_threshold": 0.3 // ขีดจำกัด Arbitrage ต่ำสุด
  }
}
```

### 3. การปรับแต่ง AI

#### เปิดใช้งานการเรียนรู้
```json
{
  "ai": {
    "learning_enabled": true,           // เปิดใช้งานการเรียนรู้
    "confidence_threshold": 0.7,        // ขีดจำกัดความเชื่อมั่น
    "rule_adaptation_frequency": "daily" // ความถี่การปรับกฎเกณฑ์
  }
}
```

## 📊 การติดตามผลการเทรด

### 1. ดูผลการเทรดแบบเรียลไทม์
- ตรวจสอบแท็บ "Positions" สำหรับตำแหน่งที่เปิดอยู่
- ดูแท็บ "Performance" สำหรับผลการดำเนินงาน
- ตรวจสอบ AI Dashboard สำหรับการตัดสินใจของ AI

### 2. ดูกราฟและสถิติ
- เปิด Charts Window เพื่อดูกราฟราคา
- ตรวจสอบกราฟ Arbitrage Opportunities
- ดูกราฟ Performance และ Drawdown

### 3. ดู Log Files
- ตรวจสอบไฟล์ในโฟลเดอร์ `logs/`
- ดู `trading_system_*.log` สำหรับ Log หลัก
- ดู `trades_*.log` สำหรับข้อมูลการเทรด
- ดู `arbitrage_*.log` สำหรับโอกาส Arbitrage

### 4. ดูรายงาน Performance
- เปิด AI Dashboard → Performance Tab
- ดูสถิติ Win Rate, Profit Factor, Sharpe Ratio
- ตรวจสอบ Maximum Drawdown

## 🚨 การจัดการความเสี่ยง

### 1. การตั้งค่า Stop Loss
- ตั้งค่า Stop Loss ตามเปอร์เซ็นต์ของราคา
- ใช้การคำนวณ ATR สำหรับ Stop Loss แบบไดนามิก
- ตั้งค่า Trailing Stop เพื่อรักษากำไร

### 2. การควบคุมขนาดตำแหน่ง
- ใช้การคำนวณ Position Size ตามความเสี่ยง
- ตั้งค่า Maximum Position Size
- ใช้การกระจายความเสี่ยงระหว่างคู่เงิน

### 3. การจัดการ Drawdown
- ตั้งค่า Maximum Drawdown Limit
- ใช้การหยุดเทรดเมื่อ Drawdown เกินขีดจำกัด
- ใช้การลดขนาดตำแหน่งเมื่อ Drawdown เพิ่มขึ้น

### 4. การใช้ Emergency Stop
- ใช้ปุ่ม "EMERGENCY STOP" เมื่อเกิดปัญหา
- ตั้งค่า Auto Emergency Stop เมื่อขาดทุนเกินขีดจำกัด
- ตรวจสอบสถานะระบบเป็นประจำ

## 🔍 การแก้ไขปัญหา

### 1. ระบบไม่เริ่มทำงาน
- ตรวจสอบการเชื่อมต่อ Broker
- ตรวจสอบการตั้งค่าใน `config/`
- ดู Log Files สำหรับข้อผิดพลาด

### 2. ไม่พบโอกาส Arbitrage
- ตรวจสอบการตั้งค่า Threshold
- ตรวจสอบข้อมูลราคา
- ปรับแต่งกฎเกณฑ์ AI

### 3. AI ไม่ตัดสินใจ
- ตรวจสอบ Confidence Threshold
- ตรวจสอบกฎเกณฑ์ที่ใช้งาน
- ดู AI Dashboard สำหรับข้อมูล

### 4. ระบบหยุดทำงาน
- ตรวจสอบการเชื่อมต่อ Broker
- ตรวจสอบ Log Files
- รีสตาร์ทระบบ

## 📈 การปรับปรุงประสิทธิภาพ

### 1. การปรับแต่ง AI
- เพิ่มกฎเกณฑ์ใหม่
- ปรับแต่ง Confidence Threshold
- เปิดใช้งาน Learning Module

### 2. การปรับแต่งข้อมูล
- เพิ่ม Timeframe ใหม่
- ปรับแต่งการคำนวณ Correlation
- เพิ่มการวิเคราะห์เทคนิคอล

### 3. การปรับแต่งความเสี่ยง
- ปรับขนาดตำแหน่งตามความเสี่ยง
- ตั้งค่า Stop Loss ที่เหมาะสม
- ควบคุม Maximum Drawdown

## 💡 เคล็ดลับการใช้งาน

### 1. การเริ่มต้น
- เริ่มด้วยบัญชี Demo
- ตั้งค่าความเสี่ยงต่ำ
- ทดสอบระบบก่อนใช้งานจริง

### 2. การติดตาม
- ตรวจสอบผลการเทรดเป็นประจำ
- ดู Log Files เพื่อหาปัญหา
- ปรับแต่งการตั้งค่าตามผลการดำเนินงาน

### 3. การปรับปรุง
- เรียนรู้จากข้อมูลการเทรด
- ปรับแต่งกฎเกณฑ์ AI
- เพิ่มฟีเจอร์ใหม่ตามต้องการ

---

**หมายเหตุ**: ระบบนี้ใช้สำหรับการศึกษาและทดสอบเท่านั้น การใช้งานจริงควรมีการทดสอบอย่างละเอียดและคำนึงถึงความเสี่ยง
