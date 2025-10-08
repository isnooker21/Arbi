# 📊 Correlation System - Visual Diagrams
# ไดอะแกรมการหา Correlation ในระบบ Arbi Trading

## 🔄 ภาพรวม: Multi-Layer Correlation System

```mermaid
graph TB
    Start([ต้องการหา Correlation<br/>สำหรับ EURUSD]) --> CheckCache{มีใน Cache?}
    
    CheckCache -->|Yes ✅| ReturnCache[ใช้จาก Cache<br/>⚡ รวดเร็ว]
    ReturnCache --> End1([Return Correlations])
    
    CheckCache -->|No ❌| Layer1[🔍 Layer 1<br/>Historical Data Calculation]
    
    Layer1 --> GetHistorical[ดึงข้อมูล 30 วันย้อนหลัง<br/>EURUSD + All Pairs]
    GetHistorical --> CheckData1{มีข้อมูล<br/>เพียงพอ?<br/> >= 10 bars}
    
    CheckData1 -->|Yes ✅| CalcPearson[คำนวณ Pearson Correlation<br/>ρ = Cov X,Y / σX × σY]
    CalcPearson --> ValidReal{Valid?<br/>-1 <= ρ <= 1}
    
    ValidReal -->|Yes ✅| CacheL1[💾 Save to Cache]
    CacheL1 --> Success1([✅ Return Layer 1<br/>Accuracy: ⭐️⭐️⭐️⭐️⭐️])
    
    CheckData1 -->|No ❌| Layer2[📊 Layer 2<br/>Tick Data Calculation]
    ValidReal -->|No ❌| Layer2
    
    Layer2 --> GetTicks[ดึง Tick Data ล่าสุด<br/>จากทุกคู่เงิน]
    GetTicks --> CheckData2{มี Tick Data?<br/>Recent ticks}
    
    CheckData2 -->|Yes ✅| CalcTick[คำนวณจาก Tick Returns<br/>Short-term correlation]
    CalcTick --> ValidTick{Valid?}
    
    ValidTick -->|Yes ✅| CacheL2[💾 Save to Cache]
    CacheL2 --> Success2([✅ Return Layer 2<br/>Accuracy: ⭐️⭐️⭐️⭐️])
    
    CheckData2 -->|No ❌| Layer3[🧮 Layer 3<br/>Dynamic Calculation]
    ValidTick -->|No ❌| Layer3
    
    Layer3 --> AnalyzeStructure[วิเคราะห์โครงสร้างคู่เงิน<br/>EUR-USD vs GBP-USD]
    AnalyzeStructure --> ApplyRules[ใช้กฎ Currency Relationship<br/>• Same currency<br/>• Opposite currency<br/>• Major vs Safe Haven]
    
    ApplyRules --> EstimateCorr[Estimate Correlation<br/>จากกฎที่กำหนด]
    EstimateCorr --> CacheL3[💾 Save to Cache]
    CacheL3 --> Success3([✅ Return Layer 3<br/>Accuracy: ⭐️⭐️⭐️])
    
    EstimateCorr -->|Error| Layer4[📋 Layer 4<br/>Default Correlations]
    Layer4 --> GetDefault[ดึงค่า Default<br/>จากตารางที่กำหนดไว้]
    GetDefault --> Success4([✅ Return Layer 4<br/>Accuracy: ⭐️⭐️])
    
    style Start fill:#e1f5ff
    style Success1 fill:#c8e6c9
    style Success2 fill:#c8e6c9
    style Success3 fill:#fff9c4
    style Success4 fill:#ffccbc
    style Layer1 fill:#bbdefb
    style Layer2 fill:#c5cae9
    style Layer3 fill:#d1c4e9
    style Layer4 fill:#f8bbd0
```

---

## 📈 Layer 1: Historical Data Calculation (วิธีที่แม่นยำที่สุด)

```mermaid
sequenceDiagram
    participant User as System
    participant Engine as Adaptive Engine
    participant Broker as MT5 Broker
    participant Calc as Calculator
    
    User->>Engine: ต้องการ correlation สำหรับ EURUSD
    
    Engine->>Broker: get_historical_data('EURUSD', 'H1', 720)
    Broker-->>Engine: 720 bars (30 วัน × 24 ชม.)
    
    Note over Engine: กรอง Major/Minor pairs<br/>EUR, USD, GBP, JPY, CHF, AUD, CAD, NZD
    
    loop สำหรับแต่ละคู่เงิน (20 คู่)
        Engine->>Broker: get_historical_data(pair, 'H1', 720)
        Broker-->>Engine: Historical data
        
        Engine->>Calc: merge_by_timestamp(EURUSD, pair)
        Calc-->>Engine: Aligned data
        
        Engine->>Calc: calculate_returns(prices)
        Calc-->>Engine: Returns data
        
        Engine->>Calc: pearson_correlation(returns1, returns2)
        Calc-->>Engine: correlation = 0.85
        
        Note over Engine: EURUSD vs GBPUSD = 0.85 ✅
    end
    
    Engine->>Engine: Sort by |correlation|
    Engine->>Engine: Cache results
    Engine-->>User: {<br/>'USDCHF': -0.87,<br/>'GBPUSD': 0.85,<br/>'AUDCAD': -0.76<br/>}
```

---

## 🔬 การคำนวณ Correlation แบบละเอียด

```mermaid
graph LR
    subgraph "1. ดึงข้อมูลราคา"
        A1[EURUSD Prices<br/>1.1000, 1.1010, 1.1005, ...]
        A2[GBPUSD Prices<br/>1.2500, 1.2510, 1.2505, ...]
    end
    
    subgraph "2. Merge ตาม Timestamp"
        B1[Aligned Data<br/>timestamp | EUR | GBP<br/>10:00 | 1.1000 | 1.2500<br/>11:00 | 1.1010 | 1.2510<br/>12:00 | 1.1005 | 1.2505]
    end
    
    subgraph "3. คำนวณ Returns"
        C1[EUR Returns<br/>+0.09%, -0.05%, ...]
        C2[GBP Returns<br/>+0.08%, -0.04%, ...]
    end
    
    subgraph "4. คำนวณ Correlation"
        D1[Pearson ρ<br/>ρ = Cov/σ1·σ2]
        D2[Result<br/>ρ = 0.85]
    end
    
    A1 --> B1
    A2 --> B1
    B1 --> C1
    B1 --> C2
    C1 --> D1
    C2 --> D1
    D1 --> D2
    
    style D2 fill:#c8e6c9
```

### สูตรการคำนวณ:

```
Returns (ผลตอบแทน):
r[t] = (P[t] - P[t-1]) / P[t-1]

ตัวอย่าง:
Price[0] = 1.1000
Price[1] = 1.1010
Returns[1] = (1.1010 - 1.1000) / 1.1000 = 0.0009 = 0.09%

Pearson Correlation:
         Σ[(X - X̄)(Y - Ȳ)]
ρ = ─────────────────────────
    √[Σ(X - X̄)²] × √[Σ(Y - Ȳ)²]

หรือ:
    Cov(X,Y)
ρ = ─────────
     σ_X × σ_Y
```

---

## 🧮 Layer 3: Dynamic Correlation (การวิเคราะห์โครงสร้าง)

```mermaid
graph TB
    Start([EURUSD vs ???]) --> Split[แยกสกุลเงิน]
    
    Split --> Base[EURUSD<br/>EUR + USD]
    Split --> Target{คู่เงินที่ต้องการเทียบ}
    
    Target --> T1[GBPUSD<br/>GBP + USD]
    Target --> T2[USDCHF<br/>USD + CHF]
    Target --> T3[EURJPY<br/>EUR + JPY]
    Target --> T4[AUDUSD<br/>AUD + USD]
    
    T1 --> Rule1{กฎที่ 1:<br/>Same Currency?}
    T2 --> Rule2{กฎที่ 2:<br/>Opposite Currency?}
    T3 --> Rule3{กฎที่ 3:<br/>Related Currency?}
    T4 --> Rule4{กฎที่ 4:<br/>Major vs Safe Haven?}
    
    Rule1 -->|Yes<br/>USD = USD| R1[Correlation = +0.75<br/>✅ Positive High]
    Rule2 -->|Yes<br/>USD ตรงข้าม| R2[Correlation = -0.75<br/>✅ Negative High]
    Rule3 -->|Yes<br/>มี EUR| R3[Correlation = +0.60<br/>✅ Positive Medium]
    Rule4 -->|Yes<br/>AUD Major| R4[Correlation = +0.60<br/>✅ Positive Medium]
    
    R1 --> Summary[สรุปผล:<br/>EURUSD vs GBPUSD = +0.75]
    R2 --> Summary2[สรุปผล:<br/>EURUSD vs USDCHF = -0.75]
    R3 --> Summary3[สรุปผล:<br/>EURUSD vs EURJPY = +0.60]
    R4 --> Summary4[สรุปผล:<br/>EURUSD vs AUDUSD = +0.60]
    
    style R1 fill:#c8e6c9
    style R2 fill:#c8e6c9
    style R3 fill:#fff9c4
    style R4 fill:#fff9c4
```

### กฎการวิเคราะห์:

```mermaid
graph LR
    subgraph "Positive Correlation"
        P1[Same Currency<br/>EURUSD vs GBPUSD<br/>ทั้งสองมี USD]
        P2[Same Base<br/>EURUSD vs EURJPY<br/>ทั้งสองมี EUR]
        P3[Major Pairs<br/>EURUSD vs GBPUSD<br/>ทั้งสองเป็น Major]
    end
    
    subgraph "Negative Correlation"
        N1[Opposite Position<br/>EURUSD vs USDCHF<br/>USD คนละด้าน]
        N2[Major vs Safe Haven<br/>AUDUSD vs USDJPY<br/>Risk On vs Risk Off]
        N3[Inverse Pairs<br/>EURUSD vs USDEUR<br/>คู่กลับ]
    end
    
    style P1 fill:#c8e6c9
    style P2 fill:#c8e6c9
    style P3 fill:#c8e6c9
    style N1 fill:#ffccbc
    style N2 fill:#ffccbc
    style N3 fill:#ffccbc
```

---

## 🎯 การใช้ Correlation ใน Recovery Process

```mermaid
graph TB
    Start([Position ติดลบ<br/>EURUSD BUY 0.10<br/>Loss: -$50]) --> GetCorr[หา Correlation Pairs]
    
    GetCorr --> Layer[ใช้ Multi-Layer System<br/>หา correlation]
    
    Layer --> Results[ผลลัพธ์:<br/>USDCHF: -0.87<br/>GBPUSD: +0.82<br/>AUDCAD: -0.76<br/>USDJPY: -0.73]
    
    Results --> Filter{Filter & Rank}
    
    Filter --> F1[1. Correlation >= 0.70 ✅]
    Filter --> F2[2. ไม่ซ้ำ Active Groups ✅]
    Filter --> F3[3. Spread ต่ำ ✅]
    
    F1 --> Rank[Ranking:<br/>1. USDCHF: -0.87 ⭐️⭐️⭐️⭐️⭐️<br/>2. GBPUSD: +0.82 ⭐️⭐️⭐️⭐️<br/>3. AUDCAD: -0.76 ⭐️⭐️⭐️]
    F2 --> Rank
    F3 --> Rank
    
    Rank --> Select[เลือก: USDCHF<br/>Negative correlation สูงสุด]
    
    Select --> CalcRatio[คำนวณ Hedge Ratio<br/>ratio = abs-0.87 × 1.2<br/>= 1.044]
    
    CalcRatio --> CalcVol[คำนวณ Volume<br/>vol = 0.10 × 1.044<br/>= 0.104 lot]
    
    CalcVol --> Direction{กำหนด Direction<br/>Negative Correlation}
    
    Direction --> Dir[EURUSD: BUY ติดลบ<br/>→ USDCHF: BUY<br/>ทิศทางเดียวกัน]
    
    Dir --> Execute[Execute Recovery<br/>USDCHF BUY 0.104<br/>Comment: RECOVERY_EURUSD_G1]
    
    Execute --> Monitor[Monitor Recovery]
    
    Monitor --> Check{Combined<br/>Profit > 0?}
    
    Check -->|No| Wait[รอต่อ<br/>EURUSD: -$35<br/>USDCHF: +$30<br/>Total: -$5]
    Wait --> Monitor
    
    Check -->|Yes| Success[ปิด Recovery!<br/>EURUSD: -$30<br/>USDCHF: +$40<br/>Total: +$10 ✅]
    
    style Start fill:#ffccbc
    style Select fill:#bbdefb
    style Execute fill:#c5cae9
    style Success fill:#c8e6c9
```

---

## 📊 ตัวอย่างการคำนวณจริง

### ตัวอย่างที่ 1: Positive Correlation

```mermaid
graph LR
    subgraph "EURUSD Prices"
        E1[1.1000]
        E2[1.1010]
        E3[1.1020]
        E4[1.1015]
        E5[1.1025]
    end
    
    subgraph "GBPUSD Prices"
        G1[1.2500]
        G2[1.2512]
        G3[1.2525]
        G4[1.2518]
        G5[1.2530]
    end
    
    subgraph "EUR Returns"
        ER1[+0.09%]
        ER2[+0.09%]
        ER3[-0.05%]
        ER4[+0.10%]
    end
    
    subgraph "GBP Returns"
        GR1[+0.10%]
        GR2[+0.10%]
        GR3[-0.06%]
        GR4[+0.10%]
    end
    
    E1 --> E2 --> E3 --> E4 --> E5
    G1 --> G2 --> G3 --> G4 --> G5
    
    E1 -.-> ER1
    E2 -.-> ER2
    E3 -.-> ER3
    E4 -.-> ER4
    
    G1 -.-> GR1
    G2 -.-> GR2
    G3 -.-> GR3
    G4 -.-> GR4
    
    ER1 --> Corr[Correlation<br/>Calculation]
    GR1 --> Corr
    ER2 --> Corr
    GR2 --> Corr
    ER3 --> Corr
    GR3 --> Corr
    ER4 --> Corr
    GR4 --> Corr
    
    Corr --> Result[ρ = +0.98<br/>✅ Strong Positive<br/>เคลื่อนไหวไปด้วยกัน]
    
    style Result fill:#c8e6c9
```

### ตัวอย่างที่ 2: Negative Correlation

```mermaid
graph LR
    subgraph "EURUSD Prices"
        E1[1.1000]
        E2[1.1010]
        E3[1.1020]
        E4[1.1015]
        E5[1.1025]
    end
    
    subgraph "USDCHF Prices"
        U1[0.9000]
        U2[0.8992]
        U3[0.8984]
        U4[0.8988]
        U5[0.8980]
    end
    
    subgraph "EUR Returns"
        ER1[+0.09%]
        ER2[+0.09%]
        ER3[-0.05%]
        ER4[+0.10%]
    end
    
    subgraph "USD Returns"
        UR1[-0.09%]
        UR2[-0.09%]
        UR3[+0.04%]
        UR4[-0.09%]
    end
    
    E1 --> E2 --> E3 --> E4 --> E5
    U1 --> U2 --> U3 --> U4 --> U5
    
    E1 -.-> ER1
    E2 -.-> ER2
    E3 -.-> ER3
    E4 -.-> ER4
    
    U1 -.-> UR1
    U2 -.-> UR2
    U3 -.-> UR3
    U4 -.-> UR4
    
    ER1 --> Corr[Correlation<br/>Calculation]
    UR1 --> Corr
    ER2 --> Corr
    UR2 --> Corr
    ER3 --> Corr
    UR3 --> Corr
    ER4 --> Corr
    UR4 --> Corr
    
    Corr --> Result[ρ = -0.95<br/>✅ Strong Negative<br/>เคลื่อนไหวตรงข้าม]
    
    style Result fill:#ffccbc
```

---

## 🔄 Complete Recovery Flow with Correlation

```mermaid
sequenceDiagram
    participant PM as Position Manager
    participant CM as Correlation Manager
    participant AE as Adaptive Engine
    participant Broker as MT5
    
    Note over PM: ตรวจพบ EURUSD ติดลบ<br/>Volume: 0.10, Loss: -$50
    
    PM->>CM: initiate_recovery(EURUSD)
    
    CM->>AE: get_correlations('EURUSD')
    
    Note over AE: Multi-Layer Calculation
    
    rect rgb(200, 230, 201)
        Note over AE: Layer 1: Historical Data
        AE->>Broker: get_historical_data('EURUSD', 'H1', 720)
        Broker-->>AE: 720 bars
        
        loop 20 pairs
            AE->>Broker: get_historical_data(pair)
            Broker-->>AE: Historical data
            AE->>AE: calculate_correlation()
        end
        
        AE-->>CM: {'USDCHF': -0.87, 'GBPUSD': 0.82, ...}
    end
    
    CM->>CM: filter_and_rank_pairs()
    Note over CM: 1. USDCHF: -0.87 ⭐️⭐️⭐️⭐️⭐️<br/>2. AUDCAD: -0.76 ⭐️⭐️⭐️
    
    CM->>CM: calculate_hedge_ratio(-0.87)
    Note over CM: ratio = 0.87 × 1.2 = 1.044
    
    CM->>CM: calculate_recovery_volume()
    Note over CM: volume = 0.10 × 1.044 = 0.104
    
    CM->>CM: determine_direction(-0.87, 'BUY')
    Note over CM: Negative corr → Same direction<br/>Direction = BUY
    
    CM->>Broker: place_order('USDCHF', 'BUY', 0.104)
    Broker-->>CM: Order placed ✅
    
    Note over CM: Monitor Recovery
    
    loop Every 30 seconds
        CM->>Broker: get_position_pnl('EURUSD')
        Broker-->>CM: -$35
        
        CM->>Broker: get_position_pnl('USDCHF')
        Broker-->>CM: +$40
        
        CM->>CM: check_combined_profit()
        Note over CM: Total: -$35 + $40 = +$5 ✅
    end
    
    CM->>Broker: close_position('USDCHF')
    Broker-->>CM: Closed ✅
    
    CM->>PM: recovery_completed(+$5)
    Note over PM: Recovery Success!
```

---

## 📈 Correlation Matrix Visualization

```mermaid
graph TB
    subgraph "EURUSD Correlations"
        EUR[EURUSD<br/>Base Pair]
        
        EUR -->|+0.85| GBP[GBPUSD<br/>Strong Positive]
        EUR -->|-0.87| CHF[USDCHF<br/>Strong Negative]
        EUR -->|+0.78| AUD[AUDUSD<br/>Positive]
        EUR -->|-0.76| AUDCAD[AUDCAD<br/>Negative]
        EUR -->|-0.73| JPY[USDJPY<br/>Negative]
        EUR -->|+0.65| NZD[NZDUSD<br/>Moderate Positive]
        EUR -->|-0.70| CAD[USDCAD<br/>Negative]
    end
    
    subgraph "Recovery Ranking"
        R1[1st Choice<br/>USDCHF: -0.87<br/>⭐️⭐️⭐️⭐️⭐️]
        R2[2nd Choice<br/>GBPUSD: +0.85<br/>⭐️⭐️⭐️⭐️⭐️]
        R3[3rd Choice<br/>AUDUSD: +0.78<br/>⭐️⭐️⭐️⭐️]
        R4[4th Choice<br/>AUDCAD: -0.76<br/>⭐️⭐️⭐️⭐️]
    end
    
    CHF -.-> R1
    GBP -.-> R2
    AUD -.-> R3
    AUDCAD -.-> R4
    
    style EUR fill:#e1f5ff
    style CHF fill:#ffccbc
    style GBP fill:#c8e6c9
    style R1 fill:#ffccbc
    style R2 fill:#c8e6c9
```

---

## 🎯 Decision Matrix: เลือก Recovery Pair

```mermaid
graph TB
    Start([มี Correlation Pairs<br/>10 คู่]) --> Filter1{Correlation<br/>>= 0.70?}
    
    Filter1 -->|Yes ✅| Pass1[6 คู่ผ่าน]
    Filter1 -->|No ❌| Reject1[4 คู่ตก]
    
    Pass1 --> Filter2{ไม่ซ้ำกับ<br/>Active Groups?}
    
    Filter2 -->|Yes ✅| Pass2[4 คู่ผ่าน]
    Filter2 -->|No ❌| Reject2[2 คู่ตก]
    
    Pass2 --> Filter3{Spread<br/>ต่ำพอ?}
    
    Filter3 -->|Yes ✅| Pass3[3 คู่ผ่าน]
    Filter3 -->|No ❌| Reject3[1 คู่ตก]
    
    Pass3 --> Rank[Ranking:<br/>1. USDCHF: -0.87<br/>2. AUDCAD: -0.76<br/>3. GBPUSD: +0.82]
    
    Rank --> Prefer{Prefer<br/>Negative Corr?}
    
    Prefer -->|Yes| Select1[เลือก: USDCHF<br/>Negative correlation สูงสุด<br/>⭐️⭐️⭐️⭐️⭐️]
    Prefer -->|No| Select2[เลือก: GBPUSD<br/>Positive correlation สูง<br/>⭐️⭐️⭐️⭐️]
    
    Select1 --> Execute[Execute Recovery]
    Select2 --> Execute
    
    style Select1 fill:#c8e6c9
    style Execute fill:#bbdefb
```

---

## 📊 Performance Comparison

```mermaid
graph TB
    subgraph "Scenario: EURUSD Loss -$50"
        S1[Original Position<br/>EURUSD BUY 0.10<br/>Loss: -$50]
    end
    
    subgraph "Option 1: Strong Negative Correlation"
        O1A[Recovery: USDCHF<br/>Correlation: -0.87<br/>Volume: 0.104]
        O1B[Result after 30 min<br/>EURUSD: -$35<br/>USDCHF: +$40<br/>Total: +$5 ✅]
    end
    
    subgraph "Option 2: Moderate Negative Correlation"
        O2A[Recovery: USDJPY<br/>Correlation: -0.73<br/>Volume: 0.088]
        O2B[Result after 30 min<br/>EURUSD: -$35<br/>USDJPY: +$30<br/>Total: -$5 ⚠️]
    end
    
    subgraph "Option 3: Positive Correlation"
        O3A[Recovery: GBPUSD<br/>Correlation: +0.82<br/>Volume: 0.098]
        O3B[Result after 30 min<br/>EURUSD: -$35<br/>GBPUSD: -$20<br/>Total: -$55 ❌]
    end
    
    S1 --> O1A
    S1 --> O2A
    S1 --> O3A
    
    O1A --> O1B
    O2A --> O2B
    O3A --> O3B
    
    O1B --> Best[Best Choice!<br/>เร็วที่สุด]
    O2B --> OK[OK<br/>ต้องรอต่อ]
    O3B --> Worst[Worst<br/>แย่ลง!]
    
    style O1B fill:#c8e6c9
    style O2B fill:#fff9c4
    style O3B fill:#ffccbc
    style Best fill:#c8e6c9
```

---

## 🔍 Correlation Quality Indicators

```mermaid
graph LR
    subgraph "Excellent"
        E1[|ρ| >= 0.85<br/>⭐️⭐️⭐️⭐️⭐️]
        E2[EURUSD vs USDCHF<br/>ρ = -0.87]
        E3[ใช้ได้ทันที!]
    end
    
    subgraph "Good"
        G1[|ρ| 0.75-0.84<br/>⭐️⭐️⭐️⭐️]
        G2[EURUSD vs GBPUSD<br/>ρ = +0.82]
        G3[ใช้ได้ดี]
    end
    
    subgraph "Fair"
        F1[|ρ| 0.70-0.74<br/>⭐️⭐️⭐️]
        F2[EURUSD vs USDJPY<br/>ρ = -0.73]
        F3[ใช้ได้ แต่ระมัดระวัง]
    end
    
    subgraph "Poor"
        P1[|ρ| < 0.70<br/>⭐️⭐️]
        P2[EURUSD vs AUDNZD<br/>ρ = +0.65]
        P3[ไม่แนะนำ]
    end
    
    E1 --> E2 --> E3
    G1 --> G2 --> G3
    F1 --> F2 --> F3
    P1 --> P2 --> P3
    
    style E3 fill:#c8e6c9
    style G3 fill:#c8e6c9
    style F3 fill:#fff9c4
    style P3 fill:#ffccbc
```

---

## 📋 Summary: ทำไมต้องใช้หลาย Layer?

```mermaid
graph TB
    Q[ทำไมต้องใช้หลาย Layer?]
    
    Q --> A1[Layer 1: Historical<br/>✅ แม่นยำที่สุด<br/>❌ ต้องการข้อมูลเยอะ]
    Q --> A2[Layer 2: Tick Data<br/>✅ Real-time<br/>❌ ข้อมูลน้อย]
    Q --> A3[Layer 3: Dynamic<br/>✅ เร็วที่สุด<br/>❌ Estimation]
    Q --> A4[Layer 4: Default<br/>✅ เสมอมี<br/>❌ อาจไม่แม่นยำ]
    
    A1 --> Benefit[ข้อดี:<br/>• Reliability ✅<br/>• Flexibility ✅<br/>• Always Available ✅]
    A2 --> Benefit
    A3 --> Benefit
    A4 --> Benefit
    
    Benefit --> Result[ระบบทำงานได้เสมอ<br/>ไม่ว่าสถานการณ์ไหน!]
    
    style Result fill:#c8e6c9
```

---

## 🎓 Key Takeaways

```mermaid
mindmap
    root((Correlation<br/>System))
        Multi-Layer
            Layer 1: Historical
                Most Accurate
                720 bars data
                Pearson Correlation
            Layer 2: Tick
                Real-time
                Recent data
                Quick calculation
            Layer 3: Dynamic
                Structure analysis
                Currency rules
                Fast estimation
            Layer 4: Default
                Fallback values
                Always available
                Pre-defined
        
        Calculation
            Returns based
                Percentage change
                Price differences
            Correlation coefficient
                Cov X,Y / σX·σY
                Range: -1 to +1
            
        Application
            Recovery pairs
                High correlation
                Opposite direction
            Hedge ratio
                Volume calculation
                Risk management
            
        Quality
            Excellent: >= 0.85
            Good: 0.75-0.84
            Fair: 0.70-0.74
            Poor: < 0.70
```

---

## 📖 อ้างอิง

**เอกสารเพิ่มเติม:**
- [CORRELATION_GUIDE.md](./CORRELATION_GUIDE.md) - คู่มือการหา Correlation แบบละเอียด
- [utils/calculations.py](./utils/calculations.py) - โค้ดคำนวณ Correlation
- [trading/adaptive_engine.py](./trading/adaptive_engine.py) - Adaptive Engine Implementation
- [trading/correlation_manager.py](./trading/correlation_manager.py) - Correlation Manager Implementation

---

**สร้างโดย:** Arbi Trading System  
**วันที่:** 8 ตุลาคม 2025  
**เวอร์ชัน:** 2.0 (Adaptive Engine)
