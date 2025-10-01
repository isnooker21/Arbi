"""
Symbol Mapper - จับคู่ชื่อคู่เงินกับนามสกุลจริงของ Broker
================================================================

ฟีเจอร์:
- สแกนคู่เงินจาก Broker อัตโนมัติ
- จับคู่ชื่อมาตรฐาน (EURUSD) กับชื่อจริง (EURUSDm, EURUSD.a, etc.)
- บันทึก/โหลด mapping จาก JSON
- Validate คู่เงินที่ต้องการ
- รองรับ suffix ต่างๆ: m, .a, _sb, ., etc.
"""

import json
import os
import logging
from typing import Dict, List, Optional, Set

class SymbolMapper:
    """จัดการ mapping ระหว่างชื่อ standard กับชื่อจริงของ broker"""
    
    def __init__(self, mapping_file: str = "data/symbol_mapping.json"):
        self.mapping_file = mapping_file
        self.symbol_map: Dict[str, str] = {}  # {'EURUSD': 'EURUSDm'}
        self.reverse_map: Dict[str, str] = {}  # {'EURUSDm': 'EURUSD'}
        self.available_symbols: Set[str] = set()
        self.logger = logging.getLogger(__name__)
        
        # โหลด mapping ที่บันทึกไว้ (ถ้ามี)
        self.load_mapping()
    
    def scan_and_map(self, broker_symbols: List[str], required_pairs: List[str]) -> Dict[str, Optional[str]]:
        """
        สแกนและจับคู่ symbol จาก broker
        
        Args:
            broker_symbols: รายการ symbol จาก broker
            required_pairs: รายการคู่เงินที่ต้องการ (standard names)
        
        Returns:
            Dict ของ mapping: {'EURUSD': 'EURUSDm', 'GBPUSD': None, ...}
        """
        self.logger.info(f"🔍 Scanning {len(broker_symbols)} broker symbols...")
        self.available_symbols = set(broker_symbols)
        
        mapping_result = {}
        
        for base_pair in required_pairs:
            matched_symbol = self._find_matching_symbol(base_pair, broker_symbols)
            mapping_result[base_pair] = matched_symbol
            
            if matched_symbol:
                self.symbol_map[base_pair] = matched_symbol
                self.reverse_map[matched_symbol] = base_pair
                self.logger.info(f"   {base_pair:8s} → {matched_symbol:15s} ✅")
            else:
                self.logger.warning(f"   {base_pair:8s} → NOT FOUND ❌")
        
        # บันทึก mapping
        if self.symbol_map:
            self.save_mapping()
            self.logger.info(f"✅ Mapped {len(self.symbol_map)}/{len(required_pairs)} required pairs")
        
        return mapping_result
    
    def _find_matching_symbol(self, base_pair: str, broker_symbols: List[str]) -> Optional[str]:
        """
        หา symbol ที่ตรงกับ base_pair จากรายการ broker
        
        รองรับ suffix: m, .a, _sb, ., .m, .pro, etc.
        """
        base_upper = base_pair.upper()
        
        # 1. หาแบบตรงทุกตัว
        if base_upper in broker_symbols:
            return base_upper
        
        # 2. หาแบบมี suffix
        for symbol in broker_symbols:
            # ลบ suffix ออกแล้วเทียบ
            clean_symbol = symbol.upper()
            
            # ลองลบ suffix ต่างๆ
            possible_suffixes = ['M', '.A', '_SB', '.', '.M', '.PRO', '_M', '_A', 'M.', 'A.']
            
            for suffix in possible_suffixes:
                if clean_symbol.endswith(suffix):
                    without_suffix = clean_symbol[:-len(suffix)]
                    if without_suffix == base_upper:
                        return symbol
            
            # ลองตรวจสอบว่า symbol เริ่มต้นด้วย base_pair หรือไม่
            if clean_symbol.startswith(base_upper):
                # เช็คว่าส่วนที่เหลือเป็น suffix ที่รู้จักไหม
                remaining = clean_symbol[len(base_upper):]
                if remaining in possible_suffixes or len(remaining) <= 3:
                    return symbol
        
        return None
    
    def get_real_symbol(self, base_symbol: str) -> str:
        """
        แปลง base symbol เป็น real symbol ของ broker
        
        Args:
            base_symbol: ชื่อมาตรฐาน เช่น 'EURUSD'
        
        Returns:
            ชื่อจริงของ broker เช่น 'EURUSDm' หรือ base_symbol ถ้าไม่มี mapping
        """
        return self.symbol_map.get(base_symbol.upper(), base_symbol)
    
    def get_base_symbol(self, real_symbol: str) -> str:
        """
        แปลง real symbol เป็น base symbol
        
        Args:
            real_symbol: ชื่อจริงจาก broker เช่น 'EURUSDm'
        
        Returns:
            ชื่อมาตรฐาน เช่น 'EURUSD' หรือ real_symbol ถ้าไม่มี mapping
        """
        return self.reverse_map.get(real_symbol, real_symbol)
    
    def validate_required_pairs(self, required_pairs: List[str]) -> Dict[str, bool]:
        """
        ตรวจสอบว่าคู่เงินที่ต้องการมีครบไหม
        
        Returns:
            Dict: {'EURUSD': True, 'GBPUSD': False, ...}
        """
        validation = {}
        
        for pair in required_pairs:
            validation[pair] = pair in self.symbol_map and self.symbol_map[pair] is not None
        
        return validation
    
    def get_missing_pairs(self, required_pairs: List[str]) -> List[str]:
        """คืนรายการคู่เงินที่หายไป"""
        return [pair for pair in required_pairs if pair not in self.symbol_map or self.symbol_map[pair] is None]
    
    def save_mapping(self) -> bool:
        """บันทึก mapping ลง JSON file"""
        try:
            os.makedirs(os.path.dirname(self.mapping_file), exist_ok=True)
            
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.symbol_map, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"💾 Saved symbol mapping to {self.mapping_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error saving symbol mapping: {e}")
            return False
    
    def load_mapping(self) -> bool:
        """โหลด mapping จาก JSON file"""
        try:
            if not os.path.exists(self.mapping_file):
                self.logger.debug(f"No existing mapping file at {self.mapping_file}")
                return False
            
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                self.symbol_map = json.load(f)
            
            # สร้าง reverse map
            self.reverse_map = {v: k for k, v in self.symbol_map.items()}
            
            self.logger.info(f"📂 Loaded {len(self.symbol_map)} symbol mappings from {self.mapping_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error loading symbol mapping: {e}")
            return False
    
    def clear_mapping(self):
        """ล้าง mapping ทั้งหมด"""
        self.symbol_map.clear()
        self.reverse_map.clear()
        self.available_symbols.clear()
        self.logger.info("🗑️ Cleared all symbol mappings")
    
    def get_mapping_summary(self) -> str:
        """สร้างสรุปของ mapping สำหรับแสดงผล"""
        if not self.symbol_map:
            return "No symbol mappings available"
        
        lines = ["Symbol Mapping Summary:", "=" * 50]
        for base, real in sorted(self.symbol_map.items()):
            lines.append(f"  {base:8s} → {real}")
        lines.append("=" * 50)
        lines.append(f"Total: {len(self.symbol_map)} pairs mapped")
        
        return "\n".join(lines)
    
    def is_mapped(self, base_symbol: str) -> bool:
        """เช็คว่า symbol นี้ถูก map แล้วหรือไม่"""
        return base_symbol.upper() in self.symbol_map
    
    def get_all_mapped_pairs(self) -> List[str]:
        """คืนรายการคู่เงินทั้งหมดที่ map แล้ว (base names)"""
        return list(self.symbol_map.keys())
    
    def get_all_real_symbols(self) -> List[str]:
        """คืนรายการ symbol จริงทั้งหมด (broker names)"""
        return list(self.symbol_map.values())

