import json
import os
import re
from typing import List, Dict, Any, Set

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_PATH       = os.path.join(BASE_DIR, '../data/_talents.raw.json')
TAGS_PATH      = os.path.join(BASE_DIR, '../data/tags.json')
OVERRIDES_PATH = os.path.join(BASE_DIR, '../data/_tag_overrides.json')
OUT_PATH       = os.path.join(BASE_DIR, '../data/talents.json')

# 1. 所有的tag : [keywords] 全部用同一個dict 存放
# 2. 一個keyword 一個字節，兩個以上的字節就拆分
# 3. keyword 比對，可能的話全部使用 lowercase, 並移除因為大小寫不一樣而新增的keywords
KEYWORDS_DICT = {
    'claw':       {'claw'},
    'flint':      {'flint'},
    'fang':       {'fang'},
    'wildwolf':   {'wildwolf'},
    'savagehorn': {'savagehorn'},
    'outcast':    {'outcast'},
    
    # 'combat':     {'dmg', 'attack', 'speed', 'crit', 'damage', 'melee',   'resilience', 'dodg', 'hitstun', 'stamina', 'bleeding', 'critical', 'hit',  'atk', 'def', 'defen', 'hp', 'buff', 'enem', 'Shield','block',},
    'hunter':     {'hunt', 'bow', 'spear', 'arrow', 'gauntlets', 'whip', 'dual-blade', 'blade' 
                   'dmg', 'attack', 'speed', 'crit', 'damage', 'melee',   'resilience', 'dodg', 'hitstun', 'stamina', 'bleeding', 'critical', 'hit',  'atk', 'def', 'defen', 'hp', 'buff', 'enem', 'Shield','block',},
    'warrior':    {'warrior', 'fight', 'hammer', 'sword','blade', 'gauntlet', 'dual-blade',
                   'dmg', 'attack', 'speed', 'crit', 'damage', 'melee',   'resilience', 'dodg', 'hitstun', 'stamina', 'bleeding', 'critical', 'hit',  'atk', 'def', 'defen', 'hp', 'buff', 'enem', 'Shield','block', },
    'guard':   {'guard', 'sword','blade','shield','bow', 'spear',
                'dmg', 'attack', 'speed', 'crit', 'damage', 'melee',   'resilience', 'dodg', 'hitstun', 'stamina', 'bleeding', 'critical', 'hit',  'atk', 'def', 'defen', 'hp', 'buff', 'enem', 'Shield','block', },
    
    'craftman':   {'weapon', 'crafting', 'armor', 'quality', 'craftman', 'craftsman', 'cooking','alchemy',}, #匠人
    'porter':     {'durability', 'cost', 'repairing', 'porter', 'potting', 'weaving','leatherworking', 'wood','stone', 'cutting', 'kilning', }, #雜工
    'laborer':    {'logging', 'planting', 'harvested', 'crop', 'mine', 'mining', 'slaughter', 'farming','laborer', } #力工
}

def load_json(filepath: str) -> Any:
    """單一職責：讀取 JSON 檔案"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data: Any, filepath: str) -> None:
    """單一職責：寫入 JSON 檔案並可被覆蓋"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def to_snake_case(text: str) -> str:
    """單一職責：將字串轉轉為 snake_case (包含 lower)"""
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')

def tokenize_text(text: str) -> Set[str]:
    """單一職責：拆分文字成單字集合 (全部使用 lowercase)"""
    words = re.findall(r'[a-z0-9]+', text.lower())
    return set(words)

def build_tag_id_map(tags_data: List[Dict]) -> Dict[str, int]:
    """單一職責：建立 tag_key 到 tag_id 的映射總表"""
    return {t['key']: t['id'] for t in tags_data}

def load_overrides(filepath: str) -> Dict[str, Dict[str, List[int]]]:
    """單一職責：讀取已轉換至新結構的覆寫設定 (_tag_overrides.json)，現在支援 merge 與 exclude_tags"""
    if not os.path.exists(filepath):
        return {}
        
    data = load_json(filepath)
    return { 
        item['key']: {
            'tag_ids': item.get('tag_ids', []),
            'exclude_tags': item.get('exclude_tags', [])
        } 
        for item in data if 'key' in item 
    }

def extract_matched_tags(text_tokens: Set[str]) -> List[str]:
    """單一職責：比對文字 tokens 與各類別的 keywords (一個 method 只做一件事)"""
    matched = []
    for tag_key, keywords in KEYWORDS_DICT.items():
        # 若集合交集不為空，表示有命中 Keyword
        if keywords & text_tokens:
            matched.append(tag_key)
    return matched

def apply_hierarchical_rules(matched_tags: List[str], slot: str) -> List[str]:
    """單一職責：處理特殊的標籤分層與槽位規則"""
    tribe_pool = {'claw', 'flint', 'fang', 'wildwolf', 'savagehorn', 'outcast'}
    specific_pool = {'hunter', 'warrior', 'guard', 'craftman', 'porter', 'laborer'}
    
    detected_tribes = [t for t in matched_tags if t in tribe_pool]
    detected_specific = next((t for t in matched_tags if t in specific_pool), None)

    # 原先的邏輯: 依照 slot 與階層決定最終的 tag_keys
    tag_keys = []

    if detected_tribes:
        tag_keys.extend(detected_tribes)
        if slot in ('normal', 'origin', 'title') and detected_specific:
            tag_keys.append(detected_specific)
    elif slot in ('title', 'origin', 'normal'):
        if detected_specific:
            tag_keys.append(detected_specific)
    else:
        tag_keys.append('general')
        
    if 'exclusive' in matched_tags:
        tag_keys.append('exclusive')
        
    return tag_keys

def compute_talent_tags(talent: Dict) -> List[str]:
    """單一職責：統整出天賦對應的 tag_keys 列表"""
    name = talent.get('name', '')
    desc = talent.get('description', '') or ''
    slot = talent.get('slot', '')
    
    target_text = f"{name} {desc}"
    text_tokens = tokenize_text(target_text)
    matched_tags = extract_matched_tags(text_tokens)
    
    # 塞上對應的 slot tag
    if slot:
        matched_tags.append(slot)
        
    return matched_tags

def process_talents() -> None:
    """主流程：負責協調讀取、處理映射與產出結構好的結果"""
    tags_data = load_json(TAGS_PATH)
    tag_id_map = build_tag_id_map(tags_data)
    overrides_map = load_overrides(OVERRIDES_PATH)
    raw_talents = load_json(RAW_PATH)
    
    results = []
    for i, t in enumerate(raw_talents, start=1):
        name = t.get('name', '')
        talent_key = to_snake_case(name)
        
        # 1. 自動透過關鍵字辨識與規則分層 (基礎 tags)
        tag_keys = compute_talent_tags(t)
        base_tag_ids = [tag_id_map[k] for k in tag_keys if k in tag_id_map]
        final_tag_ids = set(base_tag_ids)
        # final_tag_ids = set(tag_keys)
        
        # 2. 合併 (Merge) 與 排除 (Exclude)
        if talent_key in overrides_map:
            override_rules = overrides_map[talent_key]
            final_tag_ids.update(override_rules['tag_ids'])
            
            for eid in override_rules['exclude_tags']:
                final_tag_ids.discard(eid)
                
        final_tag_ids = list(final_tag_ids)
            
        t_copy = t.copy()
        t_copy["talent_id"] = i
        t_copy["key"] = talent_key
        t_copy["tag_ids"] = final_tag_ids
        
        results.append(t_copy)
        
    save_json(results, OUT_PATH)
    print(f"[OK] 成功產生 {len(results)} 筆天賦，輸出至 {OUT_PATH}")

if __name__ == '__main__':
    process_talents()
