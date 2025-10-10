#!/bin/bash
echo "🚀 VPS Update Script"
echo "==================="

# 1. ตรวจสอบ branch ปัจจุบัน
echo "📋 Current branch:"
git branch

# 2. เปลี่ยนไป isnooker21 branch
echo "🔄 Switching to isnooker21 branch..."
git checkout isnooker21

# 3. Pull code ใหม่
echo "📥 Pulling latest code..."
git pull origin isnooker21

# 4. ตรวจสอบ config
echo "📊 Checking config..."
echo "risk_per_trade_percent:"
grep -A1 -B1 "risk_per_trade_percent" config/adaptive_params.json

# 5. ลบ cache
echo "🗑️ Cleaning cache..."
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# 6. หยุดระบบเก่า
echo "🛑 Stopping old system..."
pkill -f python 2>/dev/null || true
pkill -f main.py 2>/dev/null || true

# 7. เริ่มระบบใหม่
echo "🚀 Starting new system..."
python3 main.py &

echo "✅ VPS Update Complete!"
echo "========================"
