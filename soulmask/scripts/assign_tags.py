"""
Step 2: 為天賦分配 tags → data/talents.json

輸入：
  data/talents.raw.json     -- Step 1 輸出
  data/tags.json            -- tag 定義（key 為識別依據）
  data/tag_overrides.json   -- 手動覆寫（{ "天賦名稱": ["tag_key", ...] }）

執行方式：docker compose exec python python soulmask/scripts/assign_tags.py
"""
import json
import os
import sys

RAW_PATH       = os.path.join(os.path.dirname(__file__), '../data/talents.raw.json')
TAGS_PATH      = os.path.join(os.path.dirname(__file__), '../data/tags.json')
OVERRIDES_PATH = os.path.join(os.path.dirname(__file__), '../data/tag_overrides.json')
OUT_PATH       = os.path.join(os.path.dirname(__file__), '../data/talents.json')

# ── 關鍵字表 ───────────────────────────────────────────────────────────────────

TRIBE_KEYWORDS = {
    'claw':       ['Claw Tribe', 'the Claw', 'Claw Exclusive'],
    'flint':      ['Flint Tribe', 'the Flint', 'Flint Exclusive'],
    'fang':       ['Fang Tribe', 'the Fang', 'Fang Exclusive'],
    'wildwolf':   ['Wildwolf Tribe', 'Wildwolf people', 'Wildwolf Exclusive'],
    'savagehorn': ['Savagehorn Tribe', 'Savagehorn people', 'Savagehorn Exclusive'],
}

CLASS_KEYWORDS = {
    'battle': [
        'DMG', 'Attack Speed', 'Crit', 'Damage', 'damage', 'melee', 'bow', 'lance',
        'axe', 'sword', 'Resilience', 'Dodge', 'Hitstun', 'Stamina',
        'Bleeding', 'critical hit', 'gauntlet', 'shield', 'spear', 'Attack', 'ATK', 'DEF', 
        'Defense', 'defense','attack', 'HP','hit','Hit', 'buff', 'arrow', 'enem'
        
    ],
    'craft': [
        'crafting', 'potting', 'logging', 'farming', 'weaving',
        'leatherworking', 'wood planing', 'stone cutting', 'kilning',
        'mining', 'slaughter', 'cooking', 'proficiency growth rate',
        'alchemy', 'weapon crafting', 'armor crafting',
    ],
}

SPECIFIC_CLASS_KEYWORDS = {
    # battle sub-classes
    'hunter':   ['bow', 'Bow', 'lance', 'Lance', 'Arrow', 'crossbow'],
    'warrior':  ['axe', 'Axe', 'sword', 'Sword', 'gauntlet', 'Gauntlet', 'spear', 'Spear'],
    'defender': ['Shield', 'shield', 'Block', 'Hitstun', 'dodging', 'Dodging', 'defending against'],
    # craft sub-classes
    'craftman': ['weapon crafting', 'armor crafting', 'high-quality armor', 'high-quality weapon',
                 'crafting armor', 'crafting weapon', 'crafting any'],
    'porter': ['durability cost', 'repairing'],
    'laborer':  ['Logging', 'logging', 'Planting', 'planting', 'harvested crop',
                 'Mine Regen', 'mining', 'slaughter'],
}

# ── 驗證 ───────────────────────────────────────────────────────────────────────

def validate_overrides(overrides: dict, valid_keys: set) -> None:
    """驗證 tag_overrides.json 所有 tag key 都存在於 tags.json，有錯則 exit。
    _ 開頭的 key 視為文件欄位，略過不驗證。"""
    errors = []
    for talent_name, keys in overrides.items():
        if talent_name.startswith('_'):
            continue
        if not isinstance(keys, list):
            errors.append(f'  [{talent_name}]: 值必須是 list，得到 {type(keys).__name__}')
            continue
        for key in keys:
            if key not in valid_keys:
                errors.append(f'  [{talent_name}]: 未知 tag key "{key}"')
    if errors:
        print('[ERROR] tag_overrides.json 驗證失敗：')
        for e in errors:
            print(e)
        print(f'\n有效的 tag keys：{sorted(valid_keys)}')
        sys.exit(1)

# ── Tag 偵測 ───────────────────────────────────────────────────────────────────

def detect_tribe_tags(name: str, desc: str) -> list[str]:
    text = name + ' ' + desc
    return [key for key, keywords in TRIBE_KEYWORDS.items()
            if any(kw in text for kw in keywords)]


def detect_class_tag(name: str, desc: str) -> str:
    text = name + ' ' + desc
    for key, keywords in CLASS_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return key
    return 'general'


def detect_specific_class_tag(name: str, desc: str) -> str | None:
    text = name + ' ' + desc
    for key, keywords in SPECIFIC_CLASS_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return key
    return None


def compute_tags(talent: dict) -> list[str]:
    name  = talent.get('name', '')
    desc  = talent.get('description', '') or ''
    slot  = talent['slot']

    tribe_tags = detect_tribe_tags(name, desc)
    class_tag  = detect_class_tag(name, desc) if slot in ('normal', 'title', 'origin') else 'general'

    if tribe_tags:
        tag_keys = list(tribe_tags)
        if class_tag != 'general':
            tag_keys.append(class_tag)
        if slot == 'normal':
            specific = detect_specific_class_tag(name, desc)
            if specific:
                tag_keys.append(specific)
    elif slot in ('title', 'origin', 'normal'):
        # fix: 沒有 tribe tag 時仍保留 class_tag（原本 normal slot 會錯誤落入 general）
        tag_keys = [class_tag]
    else:
        tag_keys = ['general']

    return tag_keys

# ── 主流程 ─────────────────────────────────────────────────────────────────────

def main():
    with open(TAGS_PATH, encoding='utf-8') as f:
        tags_data = json.load(f)
    valid_keys = {t['key'] for t in tags_data}

    overrides: dict = {}
    if os.path.exists(OVERRIDES_PATH):
        with open(OVERRIDES_PATH, encoding='utf-8') as f:
            overrides = json.load(f)
        validate_overrides(overrides, valid_keys)
    else:
        print(f'[INFO] {OVERRIDES_PATH} 不存在，略過手動覆寫')

    with open(RAW_PATH, encoding='utf-8') as f:
        raw: list[dict] = json.load(f)

    talents = []
    warn_count = 0
    for i, t in enumerate(raw, start=1):
        name = t.get('name', '')
        # _ 開頭的 key 是文件欄位，不做 lookup
        if name in overrides and not name.startswith('_'):
            tags = list(overrides[name])
        else:
            tags = compute_tags(t)

        unknown = [k for k in tags if k not in valid_keys]
        if unknown:
            print(f'  [WARN] "{name}": 偵測到未知 tag {unknown}，已略過')
            warn_count += 1
        tags = [k for k in tags if k in valid_keys]

        talents.append({
            'id':                 i,
            'slot':               t['slot'],
            'game_ids':           t['game_ids'],
            'name':               name,
            'description':        t.get('description'),
            'description_values': t.get('description_values'),
            'icon':               t.get('icon'),
            'tags':               tags,
        })

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(talents, f, ensure_ascii=False, indent=2)

    print(f'[OK] {len(talents)} talents → {OUT_PATH}')
    if warn_count:
        print(f'     {warn_count} 筆有未知 tag 警告，請確認 tags.json 或 tag_overrides.json')


if __name__ == '__main__':
    main()
