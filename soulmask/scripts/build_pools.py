"""
Step 3: 從 talents.json 建立 talent_pools.json

輸入：data/talents.json
執行方式：docker compose exec python python soulmask/scripts/build_pools.py
"""
from functools import reduce
import json
import os

TALENTS_PATH = os.path.join(os.path.dirname(__file__), '../data/talents.json')
OUT_PATH     = os.path.join(os.path.dirname(__file__), '../data/talent_pools.json')

CLASS_GROUPS   = ['battle', 'craft']
CLASS_KEYS     = ['hunter', 'warrior', 'defender', 'craftman', 'porter', 'laborer']
TRIBE_KEYS     = ['savagehorn', 'wildwolf', 'fang', 'claw', 'flint', 'outcast']

# 每個 slot 的分流層次設定（由外到內）
# tribe 天賦只有部落 tag，跳過 CLASS_GROUPS 那一層
SLOT_SPLITS = {
    'experience': [],
    'origin':     [CLASS_GROUPS],
    'title':      [CLASS_GROUPS],
    'tribe':      [TRIBE_KEYS],
    'normal':     [CLASS_GROUPS, TRIBE_KEYS, CLASS_KEYS],
}

# ── 通用分流 ──────────────────────────────────────────────────────────────────

def split_by_tags (talents: list[dict], split_tags: list[str]):
    """遞迴分流 talents，依序按照 split_tags 定義的 tag key 切分成多層 pool。"""

    # 遞迴結束點：沒有更多 tag 可分 → 回傳原 list
    if not split_tags:
        return list(talents)
    # 遞迴結束點：沒有可分的 talents → 回傳空 list
    if not talents:
        return []
    
    # 用 unpack 取第一層 keys，remaining 不含第一層（避免 pop 原地修改）
    keys, *remaining = split_tags
    pools = {}
    left = talents
    for key in keys:
        # 先從原 talent list 挑出符合 tag key items 成 subset，再丟進下一層分流
        # 剩下的 talents 等下一個迴圈再處理一次
        pick, left = reduce(lambda acc, t: 
            (acc[0] + [t], acc[1]) if key in t['tags'] else (acc[0], acc[1] + [t]), 
            left, 
            ([], []))
        
        # 遞迴分流 subset，並把結果放回 pools
        pools[key] = split_by_tags(pick, remaining)
        
        # 移除空的 pool
        if(pools[key] == []):
            del pools[key]
    
    # 迴圈後剩下的 talents 就是 ungroup
    pools['ungroup'] = left

    return pools

# ── 統計 ───────────────────────────────────────────────────────────────────────

def _count(pool) -> int:
    if isinstance(pool, list):
        return len(pool)
    return sum(_count(v) for v in pool.values())


def _print_stats(pools: dict) -> None:
    def _print_node(key: str, node, indent: int) -> None:
        prefix = '  ' * indent
        if isinstance(node, list):
            print(f'{prefix}{key}: {len(node)}')
        else:
            print(f'{prefix}{key}: total={_count(node)}')
            for k, v in node.items():
                _print_node(k, v, indent + 1)

    print('[OK] talent_pools.json:')
    for slot, pool in pools.items():
        _print_node(slot, pool, indent=1)

# ── 入口 ───────────────────────────────────────────────────────────────────────

def main():
    # ── Pool builders ──────────────────────────────────────────────────────────────
    #
    # 分流設計：
    #   Step 0  slot     — raw data 解析時已依 slot 拆分，無需再處理
    #   Step 1  category — 依職業群（battle / craft）分桶
    #   Step 2  tribe    — 依部落（savagehorn / wildwolf / ...）分桶
    #   Step 3  class    — 依職業細類（hunter / warrior / craftman / ...）分桶
    with open(TALENTS_PATH, encoding='utf-8') as f:
        talents = json.load(f)

    pools = {}
    # 先按 slot 分組
    for type in ('experience', 'origin', 'title', 'tribe', 'normal'):
        pools[type] = split_by_tags(
            [t for t in talents if t['slot'] == type],
            SLOT_SPLITS[type]
        )

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(pools, f, ensure_ascii=False, indent=2)
    _print_stats(pools)

if __name__ == '__main__':
    main()
