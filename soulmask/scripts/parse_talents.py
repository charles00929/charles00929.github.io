"""
Step 1: 解析 soulmask/_data/*.html → data/talents.raw.json
執行方式：docker compose exec python python soulmask/scripts/parse_talents.py
"""
import re
import json
import os
from html.parser import HTMLParser

DATA_DIR = os.path.join(os.path.dirname(__file__), '../_data')
OUT_PATH = os.path.join(os.path.dirname(__file__), '../data/_talents.raw.json')

# slot 對應各 html 檔案
SLOT_MAP = {
    'normal.html':     'normal',
    'origin.html':     'origin',
    'experience.html': 'experience',
    'title.html':      'title',
    'tribe.html':      'tribe',   # slot 由偵測決定，形如 tribe.{key}
}

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
        if tag == 'table' and self._in_table:
            self._in_table = False
            self._pending_title = None
            return
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
            'game_ids':           [v for v in ids if v is not None],
            'name':               title_text,
            'description':        desc,
            'description_values': desc_values,
            'icon':               icon,
        })


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
                    existing = m['description_values'] or []
                    combined = existing + [v for v in row['description_values']
                                           if v not in existing]
                    m['description_values'] = combined or None
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


def classify_rows(rows: list[dict], default_slot: str) -> list[dict]:
    """為每個 row 設定 slot。"""
    result = []
    for row in rows:
        row = dict(row)
        row['slot'] = default_slot
        result.append(row)
    return result


def to_snake_case(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')


def main():
    all_talents = []
    for filename, slot in SLOT_MAP.items():
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            print(f'[SKIP] {filename} not found')
            continue
        rows    = parse_file(filepath)
        talents = classify_rows(rows, slot)
        all_talents.extend(talents)
        print(f'[OK] {filename}: {len(talents)} talents')

    for i, talent in enumerate(all_talents, 1):
        talent['talent_id'] = i
        talent['key'] = to_snake_case(talent['name'])

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_talents, f, ensure_ascii=False, indent=2)
    print(f'\nTotal: {len(all_talents)} talents → {OUT_PATH}')


if __name__ == '__main__':
    main()
