"""
從 talents.json 讀取所有 icon URI，批次下載備份。
圖片存放於 soulmask/images/（保留原始相對路徑結構）
執行方式：docker compose exec python python soulmask/scripts/download_icons.py
"""
import json
import os
import time
import urllib.request
import urllib.error

BASE_URL = 'https://saraserenity.net/soulmask/'
JSON_PATH = os.path.join(os.path.dirname(__file__), '../data/talents.json')
OUT_DIR   = os.path.join(os.path.dirname(__file__), '../images')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; icon-backup-script/1.0)',
}


def download(url: str, dest: str) -> bool:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            with open(dest, 'wb') as f:
                f.write(resp.read())
        return True
    except urllib.error.HTTPError as e:
        print(f'  [HTTP {e.code}] {url}')
        return False
    except Exception as e:
        print(f'  [ERROR] {url}: {e}')
        return False


def main():
    with open(JSON_PATH, encoding='utf-8') as f:
        talents = json.load(f)

    # 收集不重複的 icon URI
    icons = sorted({t['icon'] for t in talents if t.get('icon')})
    print(f'Found {len(icons)} unique icons, downloading...\n')

    ok = skip = fail = 0
    for icon in icons:
        dest = os.path.join(OUT_DIR, icon)
        if os.path.exists(dest):
            skip += 1
            continue
        url = BASE_URL + icon
        if download(url, dest):
            ok += 1
        else:
            fail += 1
        time.sleep(0.1)  # 稍微節流，避免打太快

    print(f'\nDone. downloaded={ok}, skipped={skip}, failed={fail}')


if __name__ == '__main__':
    main()
