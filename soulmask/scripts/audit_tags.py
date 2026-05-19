import json
import os
import sys
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_PATH       = os.path.join(BASE_DIR, '../data/talents.raw.json')
TAGS_PATH      = os.path.join(BASE_DIR, '../data/tags.json')
OVERRIDES_PATH = os.path.join(BASE_DIR, '../data/_tag_overrides.json')

# 讓載入自定義 module 正常運作
sys.path.append(BASE_DIR)
from assign_tags import to_snake_case, compute_talent_tags

def load_json(filepath):
    if not os.path.exists(filepath): return []
    with open(filepath, 'r', encoding='utf-8') as f: return json.load(f)

def save_json(data, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def show_help(tags_data):
    print("\n=== 指令說明 ===")
    print("  +ID 或 ++ID : 高優先應該出現 (例如: +80 ++50)")
    print("  -ID 或 --ID : 高優先不該出現 (例如: -81 --52)")
    print("  rID         : 取消該 ID 的覆寫 (例如: r80)")
    print("  群組快捷鍵  : c 代表 51 52 53 (製造), b 代表 81 82 83 (戰鬥)")
    print("               用法搭配前綴如: +c, -b, ++c, rb")
    print("  輸入空白隔開可同時執行多個: +50 -81 ++82 +c -b")
    print("  q           : 退出並儲存這筆天賦")
    print("  h           : 顯示此說明與所有標籤")
    print("\n--- 所有可用標籤列表 ---")
    for t in sorted(tags_data, key=lambda x: x['id']):
        print(f"[{t['id']:>3}] {t['key']:<15} - {t.get('ch_name', '')}")
    print("-----------------------\n")

def edit_talent(t, tag_id_map, override, tags_data):
    talent_id = t['talent_id']
    name = t.get('name', '')
    desc = t.get('description', '')
    
    # 自動分析出的 Tags
    auto_tag_keys = compute_talent_tags(t)
    auto_tag_ids = [tag_id_map[k] for k in auto_tag_keys if k in tag_id_map]
    
    id_to_name = {tg['id']: f"#{tg['id']} {tg.get('en_name', tg['key'])}" for tg in tags_data}

    msg = ""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # 計算最終結果
        final_tags = set(auto_tag_ids)
        final_tags.update(override.get('tag_ids', []))
        for eid in override.get('exclude_tags', []):
            final_tags.discard(eid)
            
        print(f"\n{'='*50}")
        print(f"正在編輯天賦 ID: {talent_id} | \033[93m{name}\033[0m")
        print(f"描述: {desc}")
        print(f"{'-'*50}")
        print(f"1. 腳本建議 Tags  : {[id_to_name.get(tid, str(tid)) for tid in auto_tag_ids]}")
        print(f"2. 人工新增 Tags (+): \033[92m{[id_to_name.get(tid, str(tid)) for tid in override.get('tag_ids', [])]}\033[0m")
        print(f"3. 人工排除 Tags (-): \033[91m{[id_to_name.get(tid, str(tid)) for tid in override.get('exclude_tags', [])]}\033[0m")
        print(f"{'-'*50}")
        print(f"👉 最終呈現 Tags  : \033[96m{[id_to_name.get(tid, str(tid)) for tid in final_tags]}\033[0m")
        print(f"{'='*50}")
        
        if msg:
            print(msg, end="")
            msg = ""
        
        cmd = input("指令 (輸入 h 看說明, q 儲存) > ").strip()
        if not cmd: continue
        if cmd.lower() == 'q':
            break
        if cmd.lower() == 'h':
            show_help(tags_data)
            input("\n\033[93m請按 Enter 鍵繼續...\033[0m")
            continue
            
        parts = cmd.split()
        
        expanded_parts = []
        for token in parts:
            if token.endswith('c') and token[:-1] in ['+', '++', '-', '--', 'r']:
                prefix = token[:-1]
                expanded_parts.extend([f"{prefix}51", f"{prefix}52", f"{prefix}53"])
            elif token.endswith('b') and token[:-1] in ['+', '++', '-', '--', 'r']:
                prefix = token[:-1]
                expanded_parts.extend([f"{prefix}81", f"{prefix}82", f"{prefix}83"])
            else:
                expanded_parts.append(token)
        
        if 'tag_ids' not in override: override['tag_ids'] = []
        if 'exclude_tags' not in override: override['exclude_tags'] = []
            
        for token in expanded_parts:
            try:
                if token.startswith('++'):
                    tid = int(token[2:])
                    if tid not in override['tag_ids']: override['tag_ids'].append(tid)
                    if tid in override['exclude_tags']: override['exclude_tags'].remove(tid)
                elif token.startswith('--'):
                    tid = int(token[2:])
                    if tid not in override['exclude_tags']: override['exclude_tags'].append(tid)
                    if tid in override['tag_ids']: override['tag_ids'].remove(tid)
                elif token.startswith('+'):
                    tid = int(token[1:])
                    if tid not in override['tag_ids']: override['tag_ids'].append(tid)
                    if tid in override['exclude_tags']: override['exclude_tags'].remove(tid)
                elif token.startswith('-'):
                    tid = int(token[1:])
                    if tid not in override['exclude_tags']: override['exclude_tags'].append(tid)
                    if tid in override['tag_ids']: override['tag_ids'].remove(tid)
                elif token.startswith('r'):
                    tid = int(token[1:])
                    if tid in override['tag_ids']: override['tag_ids'].remove(tid)
                    if tid in override['exclude_tags']: override['exclude_tags'].remove(tid)
                else:
                    msg += f"\033[91m無法辨識的 token: {token}\033[0m\n"
            except ValueError:
                msg += f"\033[91m無法解析為數字的 token: {token}\033[0m\n"

def main():
    raw_talents = load_json(RAW_PATH)
    tags_data = load_json(TAGS_PATH)
    overrides = load_json(OVERRIDES_PATH)
    
    tag_id_map = {t['key']: t['id'] for t in tags_data}
    
    # dict: talent_key -> override object
    overrides_dict = {item['key']: item for item in overrides if 'key' in item}
    
    # 幫 raw_talents 加上 index 以利查詢
    for i, t in enumerate(raw_talents, start=1):
        t['talent_id'] = i

    while True:
        print("\n=== Soulmask 天賦標籤編輯神器 ===")
        val = input("輸入天賦 ID/名稱 或輸入 'u' 尋找無標籤天賦 (q 結束): ").strip()
        if val.lower() == 'q':
            break
        if not val:
            continue
            
        matches = []
        if val.lower() == 'u':
            # 尋找「最終沒有任何標籤」的天賦
            for mt in raw_talents:
                # 只有 normal 槽位才算
                if mt.get('slot') != 'normal':
                    continue
                    
                mt_key = to_snake_case(mt.get('name', ''))
                mt_auto_tags = compute_talent_tags(mt)
                mt_auto_ids = {tag_id_map[k] for k in mt_auto_tags if k in tag_id_map}
                
                # 加上 override 的影響
                if mt_key in overrides_dict:
                    mt_auto_ids.update(overrides_dict[mt_key].get('tag_ids', []))
                    for eid in overrides_dict[mt_key].get('exclude_tags', []):
                        mt_auto_ids.discard(eid)
                        
                # 如果最終結果連一個特定的職業/部落標籤都沒有 (扣除 slot 本身)
                classes_and_tribes = {t['id'] for t in tags_data if t.get('category') in ('class', 'tribe')}
                if not mt_auto_ids.intersection(classes_and_tribes):
                    matches.append(mt)
                    
            if not matches:
                print("\033[92m目前沒有找到任何無標籤的天賦！\033[0m")
                continue
            print(f"\033[93m找到 {len(matches)} 筆無標籤天賦\033[0m")
        elif val.isdigit():
            target_id = int(val)
            matches = [t for t in raw_talents if t['talent_id'] == target_id]
        else:
            matches = [t for t in raw_talents if val.lower() in t.get('name', '').lower()]
            
        if not matches:
            print("\033[91m找不到該天賦。\033[0m")
            continue
            
        target_talent = matches[0]
        if len(matches) > 1:
            print(f"找到 {len(matches)} 筆天賦：")
            for i, mt in enumerate(matches):
                print(f"  {i+1}: [{mt['talent_id']}] {mt['name']}")
            idx = input("請輸入對應的編號選擇 (直接按 Enter 取消): ").strip()
            if not idx.isdigit() or int(idx) < 1 or int(idx) > len(matches):
                continue
            target_talent = matches[int(idx)-1]
            
        # 準備編輯
        talent_key = to_snake_case(target_talent.get('name', ''))
        
        # 取得或初始化 override record
        if talent_key not in overrides_dict:
            overrides_dict[talent_key] = {
                "talent_id": target_talent['talent_id'],
                "key": talent_key,
                "tag_ids": [],
                "exclude_tags": []
            }
            
        edit_talent(target_talent, tag_id_map, overrides_dict[talent_key], tags_data)
        
        # 儲存
        # 清除掉空的覆寫陣列以保持乾淨
        if not overrides_dict[talent_key]['tag_ids'] and not overrides_dict[talent_key]['exclude_tags']:
            del overrides_dict[talent_key]
            
        save_json(list(overrides_dict.values()), OVERRIDES_PATH)
        print("\033[92m已自動寫入並儲存 _tag_overrides.json！\033[0m")

if __name__ == '__main__':
    main()
