# 📐 สูตรคำนวณ Lot Size ในระบบ Arbi Trading
# Lot Size Calculation Formulas

## 🎯 ภาพรวม: ระบบคำนวณ Lot Size

ระบบของคุณมี **3 วิธี** ในการคำนวณ Lot Size:

```
1. Account Tier-Based Sizing
   → คำนวณตามระดับบัญชี (Starter, Standard, Premium, VIP)

2. Risk-Based Sizing
   → คำนวณตามเปอร์เซ็นต์ความเสี่ยง

3. Recovery Lot Sizing
   → คำนวณ lot สำหรับ recovery positions
```

---

## 💰 วิธีที่ 1: Account Tier-Based Sizing (แนะนำ!)

### หลักการ:
ระบบจะ **auto-detect** ระดับบัญชีจากยอดเงิน และปรับ risk ให้เหมาะสม

### Account Tiers:

```
┌─────────────────────────────────────────────────────────┐
│ Tier      │ Balance Range    │ Risk/Trade │ Max Triangles│
├───────────┼─────────────────┼────────────┼──────────────┤
│ STARTER   │ $1,000-$5,000   │   2.0%     │      2       │
│ STANDARD  │ $5,000-$25,000  │   1.5%     │      3       │
│ PREMIUM   │ $25,000-$100,000│   1.2%     │      4       │
│ VIP       │ $100,000+       │   1.0%     │      5       │
└─────────────────────────────────────────────────────────┘
```

### สูตรคำนวณ:

```
ขั้นตอนที่ 1: คำนวณ Risk Amount
Risk Amount = Balance × (Risk Percent / 100)

ขั้นตอนที่ 2: แบ่ง Risk ให้ 3 คู่เงินใน Triangle
Risk per Pair = Risk Amount / 3

ขั้นตอนที่ 3: คำนวณ Lot Size
Lot Size = (Risk per Pair / Pip Value) × 0.01
```

### ตัวอย่างการคำนวณ:

#### ตัวอย่างที่ 1: STANDARD Account ($10,000)

```
Balance = $10,000
Tier = STANDARD
Risk Percent = 1.5%

ขั้นที่ 1: คำนวณ Risk Amount
Risk Amount = $10,000 × (1.5 / 100)
Risk Amount = $10,000 × 0.015
Risk Amount = $150

ขั้นที่ 2: Risk per Pair (3 คู่เงินใน triangle)
Risk per Pair = $150 / 3
Risk per Pair = $50

ขั้นที่ 3: คำนวณ Lot Size
สมมติ: Pip Value = $10 per 0.01 lot (สำหรับ EURUSD)

Lot Size = ($50 / $10) × 0.01
Lot Size = 5 × 0.01
Lot Size = 0.05 lot

ผลลัพธ์: ใช้ 0.05 lot สำหรับแต่ละคู่เงิน
→ Triangle เปิด 3 คู่ = 0.05 + 0.05 + 0.05 = 0.15 lot รวม
```

#### ตัวอย่างที่ 2: PREMIUM Account ($50,000)

```
Balance = $50,000
Tier = PREMIUM
Risk Percent = 1.2%

ขั้นที่ 1: คำนวณ Risk Amount
Risk Amount = $50,000 × (1.2 / 100)
Risk Amount = $50,000 × 0.012
Risk Amount = $600

ขั้นที่ 2: Risk per Pair
Risk per Pair = $600 / 3
Risk per Pair = $200

ขั้นที่ 3: คำนวณ Lot Size
Pip Value = $10 per 0.01 lot

Lot Size = ($200 / $10) × 0.01
Lot Size = 20 × 0.01
Lot Size = 0.20 lot

ผลลัพธ์: ใช้ 0.20 lot สำหรับแต่ละคู่เงิน
→ Triangle เปิด 3 คู่ = 0.20 + 0.20 + 0.20 = 0.60 lot รวม
```

#### ตัวอย่างที่ 3: VIP Account ($200,000)

```
Balance = $200,000
Tier = VIP
Risk Percent = 1.0%

ขั้นที่ 1: คำนวณ Risk Amount
Risk Amount = $200,000 × (1.0 / 100)
Risk Amount = $200,000 × 0.01
Risk Amount = $2,000

ขั้นที่ 2: Risk per Pair
Risk per Pair = $2,000 / 3
Risk per Pair = $666.67

ขั้นที่ 3: คำนวณ Lot Size
Pip Value = $10 per 0.01 lot

Lot Size = ($666.67 / $10) × 0.01
Lot Size = 66.67 × 0.01
Lot Size = 0.67 lot

ผลลัพธ์: ใช้ 0.67 lot สำหรับแต่ละคู่เงิน
→ Triangle เปิด 3 คู่ = 0.67 + 0.67 + 0.67 = 2.01 lot รวม
```

---

## 📊 Pip Value คืออะไร?

### คำจำกัดความ:
**Pip Value** = มูลค่าของการเปลี่ยนแปลง 1 pip ในสกุลเงิน Account Currency

### สูตรคำนวณ Pip Value:

```
Pip Value = Contract Size × Pip Size

โดยที่:
  Contract Size = 100,000 × Lot Size
  Pip Size = 0.0001 (สำหรับคู่เงินทั่วไป)
           = 0.01   (สำหรับคู่เงิน JPY)
```

### ตัวอย่าง: EURUSD

```
Lot Size = 0.01 lot
Contract Size = 100,000 × 0.01 = 1,000
Pip Size = 0.0001

Pip Value = 1,000 × 0.0001 = $0.10 per pip

หมายความว่า:
- ถ้าเปิด 0.01 lot
- ราคาเคลื่อนไหว 1 pip
- กำไร/ขาดทุน = $0.10
```

### ตัวอย่าง: USDJPY

```
Lot Size = 0.01 lot
Contract Size = 100,000 × 0.01 = 1,000
Pip Size = 0.01 (JPY pairs ใช้ 0.01)

Pip Value = 1,000 × 0.01 = 10 JPY per pip

แปลงเป็น USD:
Pip Value (USD) = 10 / USDJPY Rate
ถ้า USDJPY = 150.00
Pip Value (USD) = 10 / 150 = $0.067 per pip
```

### ตาราง Pip Value สำหรับ 0.01 lot:

| คู่เงิน | Pip Size | Pip Value (USD) |
|---------|----------|-----------------|
| EURUSD  | 0.0001   | $1.00          |
| GBPUSD  | 0.0001   | $1.00          |
| AUDUSD  | 0.0001   | $1.00          |
| NZDUSD  | 0.0001   | $1.00          |
| USDCAD  | 0.0001   | ~$0.75         |
| USDCHF  | 0.0001   | ~$1.10         |
| USDJPY  | 0.01     | ~$0.67         |

---

## 🔧 วิธีที่ 2: Risk-Based Sizing

### หลักการ:
คำนวณ lot ตาม **เปอร์เซ็นต์ความเสี่ยงที่ยอมรับได้**

### สูตร:

```
Lot Size = (Balance × Risk% / 100) / Pip Value / 100

หรือ:

Lot Size = Risk Amount / (Pip Value × 100)

โดยที่:
  Risk Amount = Balance × Risk%
  Pip Value = มูลค่าของ 1 pip สำหรับ 1.0 lot
```

### ตัวอย่าง:

```
Balance = $10,000
Risk% = 2% (ยอมรับขาดทุนได้ $200 ต่อ trade)
Pip Value = $10 per 0.01 lot (EURUSD)

ขั้นที่ 1: คำนวณ Risk Amount
Risk Amount = $10,000 × 0.02 = $200

ขั้นที่ 2: คำนวณ Pip Value for 1.0 lot
Pip Value (1.0 lot) = $10 / 0.01 = $1,000 per pip

ขั้นที่ 3: คำนวณ Lot Size
Lot Size = $200 / $1,000 = 0.20 lot

ผลลัพธ์: เปิด 0.20 lot
```

---

## 🔄 วิธีที่ 3: Recovery Lot Sizing

### หลักการ:
คำนวณ lot สำหรับ **Recovery Position** โดยพิจารณา:
1. Correlation กับตำแหน่งเดิม
2. ขนาด lot ของตำแหน่งเดิม
3. ขนาดการขาดทุน

### สูตร Recovery Lot:

```
Recovery Lot = Original Lot × Hedge Ratio

โดยที่:
  Hedge Ratio = abs(Correlation) × Multiplier
  Multiplier = 1.0 - 1.5 (ปรับตามสถานการณ์)
```

### ตัวอย่างที่ 1: Strong Negative Correlation

```
Original Position:
  Symbol: EURUSD
  Lot: 0.10
  Loss: -$50

Recovery Pair: USDCHF
Correlation: -0.87 (Negative สูง)

คำนวณ:
Hedge Ratio = abs(-0.87) × 1.2
Hedge Ratio = 0.87 × 1.2
Hedge Ratio = 1.044

Recovery Lot = 0.10 × 1.044
Recovery Lot = 0.104 lot

ผลลัพธ์: เปิด USDCHF 0.104 lot
```

### ตัวอย่างที่ 2: Moderate Correlation

```
Original Position:
  Symbol: EURUSD
  Lot: 0.10
  Loss: -$50

Recovery Pair: USDJPY
Correlation: -0.73 (Negative ปานกลาง)

คำนวณ:
Hedge Ratio = abs(-0.73) × 1.2
Hedge Ratio = 0.73 × 1.2
Hedge Ratio = 0.876

Recovery Lot = 0.10 × 0.876
Recovery Lot = 0.088 lot

ผลลัพธ์: เปิด USDJPY 0.088 lot
```

### สูตร Recovery Lot แบบ Dynamic (ใช้ Pip Value จริง):

```
Recovery Lot = (Target Recovery PnL / Hedge Pip Value) / 100

โดยที่:
  Target Recovery PnL = Original Loss × Recovery Target%
  Recovery Target% = 75-85% (ปรับตาม correlation)
  Hedge Pip Value = Pip Value ของคู่เงิน recovery
```

### ตัวอย่าง Dynamic Recovery:

```
Original Loss = -$50
Correlation = -0.87
Recovery Target = 75% + (0.87 × 10%) = 83.7%

ขั้นที่ 1: คำนวณ Target Recovery
Target Recovery = $50 × 0.837 = $41.85

ขั้นที่ 2: คำนวณ Recovery Lot
Hedge Pip Value = $10 per 0.01 lot (USDCHF)
Pip Value (1.0 lot) = $10 / 0.01 = $1,000

Recovery Lot = $41.85 / $1,000
Recovery Lot = 0.042 lot

ปรับขึ้นเล็กน้อย: 0.042 × 1.2 = 0.05 lot

ผลลัพธ์: เปิด USDCHF 0.05 lot
```

---

## 📈 ตารางสรุป Lot Size ตาม Balance

### สำหรับ Triangle Arbitrage (Risk per Pair):

| Balance | Tier | Risk% | Risk Amount | Risk/Pair | Lot Size (ประมาณ) |
|---------|------|-------|-------------|-----------|-------------------|
| $1,000  | Starter   | 2.0% | $20   | $6.67  | 0.007 lot |
| $5,000  | Standard  | 1.5% | $75   | $25    | 0.025 lot |
| $10,000 | Standard  | 1.5% | $150  | $50    | 0.05 lot  |
| $25,000 | Premium   | 1.2% | $300  | $100   | 0.10 lot  |
| $50,000 | Premium   | 1.2% | $600  | $200   | 0.20 lot  |
| $100,000| VIP       | 1.0% | $1,000| $333   | 0.33 lot  |
| $200,000| VIP       | 1.0% | $2,000| $667   | 0.67 lot  |

*หมายเหตุ: สมมติ Pip Value = $10 per 0.01 lot (EURUSD)*

---

## 🎯 การคำนวณแบบ Step-by-Step

### สถานการณ์จริง: Balance $15,000

```
┌──────────────────────────────────────────┐
│ STEP 1: Detect Account Tier             │
└──────────────────────────────────────────┘

Balance = $15,000
→ อยู่ในช่วง $5,000-$25,000
→ Tier = STANDARD
→ Risk% = 1.5%
→ Max Triangles = 3

┌──────────────────────────────────────────┐
│ STEP 2: Calculate Risk Amount           │
└──────────────────────────────────────────┘

Risk Amount = Balance × (Risk% / 100)
Risk Amount = $15,000 × 0.015
Risk Amount = $225

┌──────────────────────────────────────────┐
│ STEP 3: Calculate Risk per Pair         │
└──────────────────────────────────────────┘

Triangle มี 3 คู่เงิน:
  - EURUSD
  - GBPUSD
  - EURGBP

Risk per Pair = $225 / 3 = $75

┌──────────────────────────────────────────┐
│ STEP 4: Calculate Pip Value             │
└──────────────────────────────────────────┘

EURUSD (Quote = USD):
  Pip Value (0.01 lot) = $1.00
  Pip Value (1.0 lot) = $100

GBPUSD (Quote = USD):
  Pip Value (0.01 lot) = $1.00
  Pip Value (1.0 lot) = $100

EURGBP (Quote = GBP):
  Current GBP/USD = 1.25
  Pip Value (0.01 lot) = $1.25
  Pip Value (1.0 lot) = $125

┌──────────────────────────────────────────┐
│ STEP 5: Calculate Lot Size              │
└──────────────────────────────────────────┘

EURUSD:
  Lot Size = (Risk / Pip Value) × 0.01
  Lot Size = ($75 / $100) × 0.01
  Lot Size = 0.75 × 0.01
  Lot Size = 0.0075 lot
  → ปัดเป็น 0.01 lot (ขั้นต่ำ)

GBPUSD:
  Lot Size = ($75 / $100) × 0.01
  Lot Size = 0.01 lot

EURGBP:
  Lot Size = ($75 / $125) × 0.01
  Lot Size = 0.60 × 0.01
  Lot Size = 0.006 lot
  → ปัดเป็น 0.01 lot (ขั้นต่ำ)

┌──────────────────────────────────────────┐
│ FINAL RESULT                             │
└──────────────────────────────────────────┘

Triangle Orders:
  1. EURUSD: 0.01 lot
  2. GBPUSD: 0.01 lot
  3. EURGBP: 0.01 lot

Total Exposure: 0.03 lot
Total Risk: ~$225 (1.5% of balance)
```

---

## ⚙️ Code Implementation

### โค้ดในระบบ (Python):

```python
# ไฟล์: utils/account_tier_manager.py

def calculate_lot_size_for_tier(self, balance, pip_value, tier_name=None):
    """
    คำนวณ lot size ตาม tier
    
    Args:
        balance: ยอดเงินในบัญชี
        pip_value: pip value per 0.01 lot
        tier_name: ชื่อ tier (ถ้าไม่ระบุจะ auto-detect)
    
    Returns:
        float: lot size ที่คำนวณได้
    """
    # Auto-detect tier ถ้าไม่ระบุ
    if not tier_name:
        tier_name, _ = self.detect_account_tier(balance)
    
    # ดึง config ของ tier
    tier_config = self.get_tier_config(tier_name)
    risk_percent = tier_config.get('risk_per_trade_percent', 1.5)
    
    # คำนวณ lot size ตาม Risk-Based Sizing
    risk_amount = balance * (risk_percent / 100.0)
    risk_per_pair = risk_amount / 3.0  # แบ่งเป็น 3 คู่
    
    if pip_value > 0:
        lot_size = (risk_per_pair / pip_value) * 0.01
    else:
        lot_size = 0.01
    
    # จำกัดขนาด lot ตาม tier
    max_position_size = tier_config.get('max_position_size', 1.0)
    lot_size = min(lot_size, max_position_size)
    
    return max(0.01, lot_size)  # ขั้นต่ำ 0.01 lot
```

### ฟังก์ชันคำนวณ Pip Value:

```python
# ไฟล์: utils/calculations.py

def calculate_pip_value(symbol, lot_size=0.01, broker_api=None):
    """คำนวณ pip value ที่แม่นยำ"""
    # แยกสกุลเงิน
    base_currency = symbol[:3]
    quote_currency = symbol[3:6]
    
    # Contract size
    contract_size = 100000 * lot_size
    
    # Pip size
    if quote_currency == 'JPY':
        pip_size = 0.01
    else:
        pip_size = 0.0001
    
    # Case 1: Quote currency is USD
    if quote_currency == 'USD':
        pip_value = contract_size * pip_size
        return pip_value
    
    # Case 2: JPY pairs
    elif quote_currency == 'JPY':
        # Get USD/JPY rate
        usd_jpy_rate = get_exchange_rate('USDJPY', broker_api)
        pip_value = (contract_size * pip_size) / usd_jpy_rate
        return pip_value
    
    # Case 3: Other quote currencies
    else:
        # Get quote/USD rate
        quote_usd_rate = get_exchange_rate(f'{quote_currency}USD', broker_api)
        pip_value = contract_size * pip_size * quote_usd_rate
        return pip_value
```

---

## 🎓 สรุปสูตรทั้งหมด

### 1. Account Tier-Based Lot Size:

```
Lot Size = (Balance × Risk% / 100 / 3) / Pip Value × 0.01

ตัวอย่าง:
Balance = $10,000
Risk% = 1.5%
Pip Value = $10 per 0.01 lot

Lot Size = ($10,000 × 0.015 / 3) / $10 × 0.01
Lot Size = ($150 / 3) / $10 × 0.01
Lot Size = $50 / $10 × 0.01
Lot Size = 5 × 0.01
Lot Size = 0.05 lot ✅
```

### 2. Risk-Based Lot Size:

```
Lot Size = (Balance × Risk% / 100) / Pip Value (1.0 lot)

ตัวอย่าง:
Balance = $10,000
Risk% = 2%
Pip Value (1.0 lot) = $1,000 per pip

Lot Size = ($10,000 × 0.02) / $1,000
Lot Size = $200 / $1,000
Lot Size = 0.20 lot ✅
```

### 3. Recovery Lot Size:

```
Recovery Lot = Original Lot × abs(Correlation) × Multiplier

ตัวอย่าง:
Original Lot = 0.10
Correlation = -0.87
Multiplier = 1.2

Recovery Lot = 0.10 × 0.87 × 1.2
Recovery Lot = 0.104 lot ✅
```

---

## 📊 Visual Summary

```mermaid
graph TB
    Start([ต้องการคำนวณ Lot Size]) --> Method{เลือกวิธี}
    
    Method -->|แนะนำ| Tier[Account Tier-Based]
    Method --> Risk[Risk-Based]
    Method --> Recovery[Recovery Sizing]
    
    Tier --> T1[Detect Tier จาก Balance]
    T1 --> T2[Risk% ตาม Tier]
    T2 --> T3[Risk Amount = Balance × Risk%]
    T3 --> T4[Risk/Pair = Amount / 3]
    T4 --> T5[Lot = Risk/Pair / PipValue × 0.01]
    T5 --> Result1([Lot Size ✅])
    
    Risk --> R1[กำหนด Risk%]
    R1 --> R2[Risk Amount = Balance × Risk%]
    R2 --> R3[Lot = Risk / PipValue1.0]
    R3 --> Result2([Lot Size ✅])
    
    Recovery --> Rec1[Original Lot]
    Rec1 --> Rec2[Correlation Value]
    Rec2 --> Rec3[Hedge Ratio = |ρ| × Multiplier]
    Rec3 --> Rec4[Recovery Lot = Original × Ratio]
    Rec4 --> Result3([Recovery Lot ✅])
    
    style Tier fill:#c8e6c9
    style Result1 fill:#c8e6c9
    style Result2 fill:#bbdefb
    style Result3 fill:#fff9c4
```

---

## ⚠️ ข้อควรระวัง

### 1. Lot Size ขั้นต่ำ
```
❌ Lot Size < 0.01 → ไม่สามารถเปิดได้
✅ Lot Size >= 0.01 → OK

ระบบจะปรับเป็น 0.01 อัตโนมัติถ้าคำนวณได้น้อยกว่า
```

### 2. Lot Size สูงสุด
```
แต่ละ Tier มีขีดจำกัด:
- Starter: 0.50 lot
- Standard: 1.00 lot
- Premium: 2.00 lot
- VIP: 5.00 lot
```

### 3. Pip Value ของคู่เงิน JPY
```
⚠️ คู่เงิน JPY ใช้ pip size = 0.01 (ไม่ใช่ 0.0001)
→ Pip Value จะต่างจากคู่เงินอื่น
```

### 4. Balance เปลี่ยน → Tier เปลี่ยน
```
ถ้า Balance เพิ่มขึ้นหรือลดลง:
→ Tier อาจเปลี่ยน
→ Risk% เปลี่ยน
→ Lot Size เปลี่ยน
```

---

## 📚 เอกสารอ้างอิง

**โค้ดที่เกี่ยวข้อง:**
- [utils/account_tier_manager.py](./utils/account_tier_manager.py) - Tier Management
- [utils/calculations.py](./utils/calculations.py) - Pip Value Calculation
- [trading/arbitrage_detector.py](./trading/arbitrage_detector.py) - Arbitrage Lot Sizing
- [trading/correlation_manager.py](./trading/correlation_manager.py) - Recovery Lot Sizing

**เอกสารอื่นๆ:**
- [CORRELATION_GUIDE.md](./CORRELATION_GUIDE.md) - Correlation Calculation
- [PEARSON_CORRELATION_EXPLAINED.md](./PEARSON_CORRELATION_EXPLAINED.md) - Pearson Correlation

---

**สร้างโดย:** Arbi Trading System  
**วันที่:** 8 ตุลาคม 2025
