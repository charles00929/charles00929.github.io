"""
解析 soulmask/_data/*.html，將天賦資料寫入 SQLite。
執行方式：docker compose exec python python soulmask/scripts/parse_talents.py
"""
import re
import sqlite3
import json
import os
from html.parser import HTMLParser

DB_PATH = os.path.join(os.path.dirname(__file__), '../data/soulmask.db')
DATA_DIR = os.path.join(os.path.dirname(__file__), '../_data')

# slot 對應各 html 檔案
SLOT_MAP = {
    'normal.html':     'normal',
    'origin.html':     'origin',
    'experience.html': 'experience',
    'title.html':      'title',
    'tribe.html':      'tribe',   # slot 由偵測決定，形如 tribe.{key}
}

# tribe 天賦：從 title/description 推斷所屬 tribe tag key
# 包含 tribe.html 的敘述關鍵字，以及 normal.html 中的 [X Exclusive] 標記
TRIBE_KEYWORDS = {
    'claw':       ['Claw Tribe', 'the Claw', 'Claw Exclusive'],
    'flint':      ['Flint Tribe', 'the Flint', 'Flint Exclusive'],
    'fang':       ['Fang Tribe', 'the Fang', 'Fang Exclusive'],
    'wildwolf':   ['Wildwolf Tribe', 'Wildwolf people', 'Wildwolf Exclusive'],
    'savagehorn': ['Savagehorn Tribe', 'Savagehorn people', 'Savagehorn Exclusive'],
}
OUTCAST_KEYWORD = 'Outcast'


class TalentTableParser(HTMLParser):
    """從一個 <table class="data-table"> 中解析所有 talent row。"""

    def __init__(self):
        super().__init__()
        self.rows = []          # 最終結果
        self._in_table = False
        self._in_tr = False
        self._cells = []        # 目前 row 的 td 內容
        self._cur_cell = None   # 目前 td 的 tag type (ids/title/desc/icon)
        self._cur_text = ''
        self._cur_icon = ''
        self._pending_title = None  # rowspan title 跨列保留
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'table' and attrs.get('class') == 'data-table':
            self._in_table = True
        if not self._in_table:
            return
        if tag == 'tr':
            self._in_tr = True
            self._cells = []
        if tag == 'td' and self._in_tr:
            self._cur_cell = 'td'
            self._cur_text = ''
            self._cur_icon = ''
        if tag == 'div' and attrs.get('class') == 'title-data':
            self._cur_cell = 'title'
        if tag == 'img' and attrs.get('class') == 'hover-img':
            self._cur_icon = attrs.get('src', '')

    def handle_endtag(self, tag):
        if not self._in_table:
            return
        if tag == 'td' and self._cur_cell is not None:
            self._cells.append({
                'type': self._cur_cell,
                'text': self._cur_text.strip(),
                'icon': self._cur_icon,
            })
            self._cur_cell = None
        if tag == 'tr' and self._in_tr:
            self._in_tr = False
            self._process_row()

    def handle_data(self, data):
        if self._cur_cell is not None:
            self._cur_text += data

    def _process_row(self):
        cells = self._cells
        if len(cells) < 2:
            return

        # 收集 td 值
        tds = [c['text'] for c in cells]
        icon = next((c['icon'] for c in cells if c['icon']), '')
        title_cell = next((c for c in cells if c['type'] == 'title'), None)

        def to_int(v):
            v = v.strip()
            return int(v) if v.isdigit() else None

        # 正常 row：[lv1_id, lv2_id, lv3_id, title, desc, icon_td]
        # rowspan title row：title 有時與下一列共用（已在 title_data div 裡）
        if title_cell:
            title_text = title_cell['text']
            self._pending_title = title_text
        else:
            title_text = self._pending_title or ''

        # IDs：前三個 td（可能空白）
        ids = [to_int(tds[i]) if i < len(tds) else None for i in range(3)]
        if all(v is None for v in ids):
            return  # thead row 或空行

        # description：有 desc-data class 的 td 內容
        desc_cell = next((c for c in cells if c['type'] == 'td' and c['text']
                          and c not in cells[:3]), None)
        desc = desc_cell['text'] if desc_cell else ''

        # 解析 description 中的 [x,y,z] 數值
        values_match = re.search(r'\[([0-9,. ]+)\]', desc)
        desc_values = None
        if values_match:
            desc_values = [float(v.strip()) if '.' in v else int(v.strip())
                           for v in values_match.group(1).split(',')]
            # 把 desc 中的 [x,y,z] 換成 #
            desc = re.sub(r'\[[0-9,. ]+\]', '#', desc)

        self.rows.append({
            'game_ids': [v for v in ids if v is not None],
            'name': title_text,
            'description': desc,
            'description_values': json.dumps(desc_values) if desc_values else None,
            'icon': icon,
        })


def detect_tribe_tags(name: str, desc: str) -> list[str]:
    """從 name/desc 推斷 tribe tag keys，回傳 list。
    Outcast 天賦不屬於任何 tribe，slot 由呼叫端另行設定為 origin。"""
    text = name + ' ' + desc
    matched = []
    for key, keywords in TRIBE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            matched.append(key)
    return matched


# 職業類別偵測關鍵字：用於 title/origin slot 判斷是戰鬥專屬、工藝專屬、還是通用
CLASS_KEYWORDS = {
    'battle': [
        'DMG', 'Attack Speed', 'Crit', 'Damage', 'melee', 'bow', 'lance',
        'axe', 'sword', 'Resilience', 'Dodge', 'Hitstun', 'Stamina',
        'Bleeding', 'critical hit', 'gauntlet', 'shield', 'spear',
    ],
    'craft': [
        'crafting', 'potting', 'logging', 'farming', 'weaving',
        'leatherworking', 'wood planing', 'stone cutting', 'kilning',
        'mining', 'slaughter', 'cooking', 'proficiency growth rate',
        'alchemy', 'weapon crafting', 'armor crafting',
    ],
}


# L4 具體職業偵測關鍵字：僅用於 normal slot 中已有 tribe tag 的天賦
SPECIFIC_CLASS_KEYWORDS = {
    # battle sub-classes
    'hunter':   ['bow', 'Bow', 'lance', 'Lance', 'Arrow', 'crossbow'],
    'warrior':  ['axe', 'Axe', 'sword', 'Sword', 'gauntlet', 'Gauntlet', 'spear', 'Spear'],
    'defender': ['Shield', 'shield', 'Block', 'Hitstun', 'dodging', 'Dodging', 'defending against'],
    # craft sub-classes
    'craftman': ['weapon crafting', 'armor crafting', 'high-quality armor', 'high-quality weapon',
                 'crafting armor', 'crafting weapon', 'crafting any'],
    'handyman': ['durability cost', 'repairing'],
    'laborer':  ['Logging', 'logging', 'Planting', 'planting', 'harvested crop',
                 'Mine Regen', 'mining', 'slaughter'],
}


def detect_class_tag(name: str, desc: str) -> str:
    """從 name/desc 推斷職業類別 tag key：'battle'、'craft' 或 'general'。"""
    text = name + ' ' + desc
    for key, keywords in CLASS_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return key
    return 'general'


def detect_specific_class_tag(name: str, desc: str) -> str | None:
    """從 name/desc 推斷最精細的 L4 職業 tag（hunter/warrior/defender/craftman/handyman/laborer）。
    僅在 normal slot 且已有 tribe tag 的天賦上使用。"""
    text = name + ' ' + desc
    for key, keywords in SPECIFIC_CLASS_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return key
    return None


def merge_duplicates(rows: list[dict]) -> list[dict]:
    """合併同名的 level-split rows（合計 game_ids ≤ 3）。
    若合計超過 3，視為不同天賦，各自獨立保留。"""
    result: list[dict] = []
    pending: dict[str, int] = {}  # name -> index in result（尚未滿 3 ids）

    for row in rows:
        key = row['name']
        if key in pending:
            m = result[pending[key]]
            if len(m['game_ids']) + len(row['game_ids']) <= 3:
                # 同一天賦的 level-split，合併
                m['game_ids'] = m['game_ids'] + [g for g in row['game_ids']
                                                  if g not in m['game_ids']]
                if row['description_values'] is not None:
                    existing = json.loads(m['description_values']) if m['description_values'] else []
                    new_vals = json.loads(row['description_values'])
                    combined = existing + [v for v in new_vals if v not in existing]
                    m['description_values'] = json.dumps(combined) if combined else None
                if not m['description'] and row['description']:
                    m['description'] = row['description']
                if not m['icon'] and row['icon']:
                    m['icon'] = row['icon']
                if len(m['game_ids']) >= 3:
                    del pending[key]
            else:
                # 超過 3 ids → 不同天賦，新增獨立 entry
                result.append(dict(row))
                if len(row['game_ids']) < 3:
                    pending[key] = len(result) - 1
        else:
            result.append(dict(row))
            if len(row['game_ids']) < 3:
                pending[key] = len(result) - 1

    return result


def parse_file(filepath: str) -> list[dict]:
    """純粹解析 HTML 固定結構，擷取天賦原始資料並合併 level-split。"""
    with open(filepath, encoding='utf-8') as f:
        html = f.read()
    parser = TalentTableParser()
    parser.feed(html)
    return merge_duplicates(parser.rows)


def classify_rows(rows: list[dict], default_slot: str, is_tribe: bool) -> list[dict]:
    """為每個 row 設定 slot 與 tribe_tags。"""
    result = []
    for row in rows:
        row = dict(row)
        if is_tribe:
            is_outcast = OUTCAST_KEYWORD in (row['name'] or '')
            if is_outcast:
                row['slot'] = 'tribe.outcast'
                row['tribe_tags'] = []
            else:
                tribes = detect_tribe_tags(row['name'], row['description'] or '')
                row['slot'] = ('tribe.' + tribes[0]) if tribes else 'tribe.unknown'
                row['tribe_tags'] = tribes
                if not tribes:
                    print(f'  [WARN] tribe talent with no tribe tag: {row["name"]}')
        else:
            row['slot'] = default_slot
            row['tribe_tags'] = detect_tribe_tags(row['name'], row['description'] or '')
        result.append(row)
    return result


def get_tag_id(conn, key: str) -> int | None:
    row = conn.execute('SELECT id FROM tags WHERE key=?', (key,)).fetchone()
    return row[0] if row else None


def insert_talents(conn, talents: list[dict]) -> list[int]:
    c = conn.cursor()
    ids = []
    for t in talents:
        c.execute('''
            INSERT INTO talents
                (slot, game_ids, name, description, description_values, icon)
            VALUES (?,?,?,?,?,?)
        ''', (
            t['slot'], json.dumps(t['game_ids']),
            t['name'], t['description'], t['description_values'], t['icon'],
        ))
        ids.append(c.lastrowid)
    conn.commit()
    return ids


def assign_talent_tags(conn, talents: list[dict], talent_ids: list[int]):
    """根據已解析的 tribe_tags / slot / description 關鍵字比對，寫入 talent_tags。"""
    c = conn.cursor()
    for t, talent_id in zip(talents, talent_ids):
        tribe_tags = t['tribe_tags']
        slot       = t['slot']

        if slot in ('normal', 'title', 'origin'):
            class_tag = detect_class_tag(t['name'], t.get('description') or '')
        else:
            class_tag = 'general'

        if tribe_tags:
            tag_keys = list(tribe_tags)
            if class_tag != 'general':
                tag_keys.append(class_tag)
            if slot == 'normal':
                specific_cls = detect_specific_class_tag(t['name'], t.get('description') or '')
                if specific_cls:
                    tag_keys.append(specific_cls)
        elif slot in ('title', 'origin'):
            tag_keys = [class_tag]
        else:
            tag_keys = ['general']

        for key in tag_keys:
            tag_id = get_tag_id(conn, key)
            if tag_id:
                c.execute('INSERT OR IGNORE INTO talent_tags VALUES (?,?)',
                          (talent_id, tag_id))
    conn.commit()


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('DELETE FROM talent_tags')
    conn.execute('DELETE FROM talents')
    conn.commit()

    total = 0
    for filename, slot in SLOT_MAP.items():
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            print(f'[SKIP] {filename} not found')
            continue
        is_tribe = filename == 'tribe.html'
        rows       = parse_file(filepath)
        talents    = classify_rows(rows, slot, is_tribe)
        talent_ids = insert_talents(conn, talents)
        assign_talent_tags(conn, talents, talent_ids)
        print(f'[OK] {filename}: {len(talents)} talents (slot={slot})')
        total += len(talents)

    print(f'\nTotal: {total} talents inserted.')
    conn.close()


if __name__ == '__main__':
    main()
