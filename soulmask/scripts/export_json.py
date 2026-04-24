"""
從 SQLite 匯出 JSON 供前端使用。
產出：
  soulmask/data/talents.json       -- 所有天賦完整資料
  soulmask/data/talent_pools.json  -- 各池子 talent id 列表（巢狀分層結構）
執行方式：docker compose exec python python soulmask/scripts/export_json.py
"""
import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '../data/soulmask.db')
OUT_DIR = os.path.join(os.path.dirname(__file__), '../data')

# ─── 分層定義 ─────────────────────────────────────────────────────────────────
TRIBE_KEYS     = ['savagehorn', 'wildwolf', 'fang', 'claw', 'flint', 'outcast']
BATTLE_CLASSES = ['hunter', 'warrior', 'defender']
CRAFT_CLASSES  = ['craftman', 'handyman', 'laborer']


def export_talents(conn):
    rows = conn.execute('''
        SELECT id, slot, game_ids,
               name, description, description_values, icon
        FROM talents
        ORDER BY id
    ''').fetchall()

    talents = []
    for r in rows:
        talents.append({
            'id':                 r[0],
            'slot':               r[1],
            'game_ids':           json.loads(r[2]) if r[2] else [],
            'name':               r[3],
            'description':        r[4],
            'description_values': json.loads(r[5]) if r[5] else None,
            'icon':               r[6],
        })

    path = os.path.join(OUT_DIR, 'talents.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(talents, f, ensure_ascii=False, indent=2)
    print(f'[OK] talents.json: {len(talents)} records')
    return talents


# ─── DB 查詢工具（各做一件事）────────────────────────────────────────────────

def ids_by_slot(conn, slot: str) -> list[int]:
    """回傳指定 slot 的所有天賦 ID。"""
    return [r[0] for r in conn.execute(
        'SELECT id FROM talents WHERE slot=? ORDER BY id', (slot,)
    )]


def ids_with_tags(conn, slot: str, tags: list[str]) -> list[int]:
    """回傳同時擁有所有指定 tag 的天賦 ID（slot + ALL tags 全部符合）。"""
    if not tags:
        return ids_by_slot(conn, slot)
    ph = ','.join('?' * len(tags))
    sql = f'''
        SELECT t.id FROM talents t
        WHERE t.slot = ?
          AND (SELECT COUNT(DISTINCT tg.key)
               FROM talent_tags tt JOIN tags tg ON tg.id = tt.tag_id
               WHERE tt.talent_id = t.id AND tg.key IN ({ph})
              ) = {len(tags)}
        ORDER BY t.id
    '''
    return [r[0] for r in conn.execute(sql, [slot] + list(tags))]


def ungroup_ids(base: list[int], *subsets) -> list[int]:
    """從 base 中移除屬於任何子集的 ID，回傳本層 ungroup。"""
    taken = set()
    for s in subsets:
        taken.update(s)
    return [i for i in base if i not in taken]


# ─── Pool builders（各做一件事）──────────────────────────────────────────────

def build_experience_pool(conn) -> list[int]:
    """L1：experience 天賦，不細分。"""
    return ids_by_slot(conn, 'experience')


def build_tribe_pool(conn) -> dict:
    """L1：tribe 天賦，依部落分桶。{ ungroup:[], claw:[...], ... }"""
    pool = {'ungroup': []}
    for key in TRIBE_KEYS:
        pool[key] = ids_by_slot(conn, f'tribe.{key}')
    return pool


def build_l2_slot_pool(conn, slot: str, categories: list[str]) -> dict:
    """L2：origin / title 天賦，依職業群分桶。{ ungroup:[], battle:[], craft:[] }"""
    buckets = {cat: ids_with_tags(conn, slot, [cat]) for cat in categories}
    all_ids = ids_by_slot(conn, slot)
    return {'ungroup': ungroup_ids(all_ids, *buckets.values()), **buckets}


def build_normal_l4_bucket(conn, category: str, tribe: str, class_keys: list[str]) -> dict:
    """L4：單一部落內依具體職業分桶。{ ungroup:[], hunter:[], ... }"""
    class_buckets = {
        cls: ids_with_tags(conn, 'normal', [category, tribe, cls])
        for cls in class_keys
    }
    base = ids_with_tags(conn, 'normal', [category, tribe])
    return {'ungroup': ungroup_ids(base, *class_buckets.values()), **class_buckets}


def build_normal_l3_bucket(conn, category: str, class_keys: list[str]) -> dict:
    """L3：單一職業群內依部落分桶，各部落再展開 L4。{ ungroup:[], savagehorn:{...}, ... }"""
    tribe_pools = {
        tribe: build_normal_l4_bucket(conn, category, tribe, class_keys)
        for tribe in TRIBE_KEYS
        if tribe != 'outcast'
    }
    tribe_all_ids = [ids_with_tags(conn, 'normal', [category, tribe]) for tribe in tribe_pools]
    base = ids_with_tags(conn, 'normal', [category])
    return {'ungroup': ungroup_ids(base, *tribe_all_ids), **tribe_pools}


def build_normal_pool(conn) -> dict:
    """L1-L4：完整 normal pool。{ ungroup:[], battle:{...}, craft:{...} }"""
    battle_pool = build_normal_l3_bucket(conn, 'battle', BATTLE_CLASSES)
    craft_pool  = build_normal_l3_bucket(conn, 'craft',  CRAFT_CLASSES)
    all_ids     = ids_by_slot(conn, 'normal')
    cat_ids     = (ids_with_tags(conn, 'normal', ['battle'])
                   + ids_with_tags(conn, 'normal', ['craft']))
    return {
        'ungroup': ungroup_ids(all_ids, cat_ids),
        'battle':  battle_pool,
        'craft':   craft_pool,
    }


# ─── 統計輸出 ─────────────────────────────────────────────────────────────────

def _count_recursive(pool) -> int:
    if isinstance(pool, list):
        return len(pool)
    return sum(_count_recursive(v) for v in pool.values())


def _print_pool_stats(pools):
    tribe  = pools['tribe']
    origin = pools['origin']
    title  = pools['title']
    normal = pools['normal']

    print('[OK] talent_pools.json:')
    print(f'     experience: {len(pools["experience"])}')
    tribe_str = '  '.join(f'{k}={len(v)}' for k, v in tribe.items() if k != 'ungroup')
    print(f'     tribe:  {tribe_str}')
    print(f'     origin: ' + '  '.join(f'{k}={len(v)}' for k, v in origin.items()))
    print(f'     title:  ' + '  '.join(f'{k}={len(v)}' for k, v in title.items()))
    print(f'     normal: ungroup={len(normal["ungroup"])}  '
          f'battle(total={_count_recursive(normal["battle"])})  '
          f'craft(total={_count_recursive(normal["craft"])})')
    for cat in ('battle', 'craft'):
        bucket = normal[cat]
        tribes_str = '  '.join(
            f'{k}={_count_recursive(v)}' for k, v in bucket.items() if k != 'ungroup'
        )
        print(f'       {cat}.ungroup={len(bucket["ungroup"])}  {tribes_str}')


# ─── 匯出入口 ─────────────────────────────────────────────────────────────────

def export_talent_pools(conn):
    pools = {
        'experience': build_experience_pool(conn),
        'tribe':      build_tribe_pool(conn),
        'origin':     build_l2_slot_pool(conn, 'origin', ['battle', 'craft']),
        'title':      build_l2_slot_pool(conn, 'title',  ['battle', 'craft']),
        'normal':     build_normal_pool(conn),
    }
    path = os.path.join(OUT_DIR, 'talent_pools.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(pools, f, ensure_ascii=False, indent=2)
    _print_pool_stats(pools)


def main():
    conn = sqlite3.connect(DB_PATH)
    export_talents(conn)
    export_talent_pools(conn)
    conn.close()


if __name__ == '__main__':
    main()
