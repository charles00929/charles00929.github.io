import json
import os
from typing import List, Dict, Any, Set

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TALENTS_PATH = os.path.join(BASE_DIR, '../data/talents.json')
RAW_PATH     = os.path.join(BASE_DIR, '../data/_talents.raw.json')
TAGS_PATH    = os.path.join(BASE_DIR, '../data/tags.json')
OUT_PATH     = os.path.join(BASE_DIR, '../data/talent_pools.json')

CLASS_MAPPING = {
    'hunter': 'combat',
    'warrior': 'combat',
    'guard': 'combat',
    'craftman': 'craft',
    'porter': 'craft',
    'laborer': 'craft'
}

SLOTS = ['tribe', 'origin', 'experience', 'title', 'exclusive', 'normal']

def load_json(filepath: str) -> Any:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data: Any, filepath: str) -> None:
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def build_talent_pools() -> None:
    # Load all dependencies
    talents_data = load_json(TALENTS_PATH)
    raw_data = load_json(RAW_PATH)
    tags_data = load_json(TAGS_PATH)
    tribes = [t for t in tags_data if t.get('category') == 'tribe']
    
    # 建立 tag_id 對應的 string key 以利比對
    tag_id_to_key = {t['id']: t['key'] for t in tags_data}
    
    # 將 slot 補回去 (透過 raw_data，index 就是 talent_id - 1)
    for t in talents_data:
        idx = t['talent_id'] - 1
        if 0 <= idx < len(raw_data):
            t['slot'] = raw_data[idx].get('slot')
        else:
            t['slot'] = None

    TRIBE_TAGS = {'savagehorn', 'wildwolf', 'fang', 'claw', 'flint', 'outcast'}
    CATEGORY_TAGS = {'combat', 'craft', 'battle'} # battle is legacy, combat is new
    SPECIFIC_CLASS_TAGS = {'hunter', 'warrior', 'guard', 'craftman', 'porter', 'laborer', 'defender'}

    result = []
    
    for tribe in tribes:
        tribe_key = tribe['key']
        tribe_data = {
            "id": tribe["id"],
            "key": tribe["key"],
            "en_name": tribe["en_name"],
            "ch_name": tribe["ch_name"],
            "classes": {}
        }
        
        for cls_name, major_class in CLASS_MAPPING.items():
            pool_data = {slot: [] for slot in SLOTS}
            
            for t in talents_data:
                # 取得該 talent 所有的 tag keys
                tag_keys = {tag_id_to_key.get(tid, "") for tid in t['tag_ids']}
                
                # 如果沒有任何有效標籤，代表它不應該出現在任何池子中 (被手動排除了所有 tags)
                if not tag_keys or (not tag_keys.intersection(TRIBE_TAGS | CATEGORY_TAGS | SPECIFIC_CLASS_TAGS) and 'general' not in tag_keys):
                    continue
                
                # Check tribe
                talent_tribes = tag_keys & TRIBE_TAGS
                if talent_tribes and tribe_key not in talent_tribes:
                    continue
                    
                # Check category
                talent_categories = tag_keys & CATEGORY_TAGS
                if talent_categories and major_class not in talent_categories:
                    continue
                    
                # Check specific class
                target_specific_tag = cls_name
                talent_specifics = tag_keys & SPECIFIC_CLASS_TAGS
                
                # Handling mapping alias for guard/defender internally
                if target_specific_tag == 'guard' and 'defender' in talent_specifics:
                    pass # Valid
                elif talent_specifics and target_specific_tag not in talent_specifics:
                    continue
                
                # Valid talent! Append to proper slot
                slot = t.get('slot')
                if slot in pool_data:
                    pool_data[slot].append(t['talent_id'])
                    
            tribe_data["classes"][cls_name] = pool_data
            
        result.append(tribe_data)
        
    save_json(result, OUT_PATH)
    print(f"[OK] 已經成功轉換資料並存檔至: {OUT_PATH}")

if __name__ == '__main__':
    build_talent_pools()
