"""
建立 SQLite 資料庫 schema 並填入已知 enum 資料。
執行方式：docker compose exec python python soulmask/scripts/setup_db.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '../data/soulmask.db')


def setup():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.executescript('''
        CREATE TABLE IF NOT EXISTS talents (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            slot        TEXT NOT NULL,  -- normal | origin | experience | title | tribe.{key}
            game_ids    TEXT NOT NULL DEFAULT '[]',  -- JSON int array (merged across levels)
            name        TEXT NOT NULL,
            description TEXT,
            description_values TEXT,    -- JSON array, fill in # slots by level
            icon        TEXT            -- image uri
        );

        CREATE TABLE IF NOT EXISTS tags (
            id       INTEGER PRIMARY KEY,
            category TEXT NOT NULL,     -- tribe | class | general
            key      TEXT NOT NULL UNIQUE,
            en_name  TEXT NOT NULL,
            ch_name  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tribe_enum (
            id      INTEGER PRIMARY KEY,
            key     TEXT NOT NULL UNIQUE,
            en_name TEXT NOT NULL,
            ch_name TEXT NOT NULL,
            tag_ids TEXT NOT NULL DEFAULT '[]'  -- JSON int array
        );

        CREATE TABLE IF NOT EXISTS class_enum (
            id       INTEGER PRIMARY KEY,
            key      TEXT NOT NULL UNIQUE,
            en_name  TEXT NOT NULL,
            ch_name  TEXT NOT NULL,
            category TEXT NOT NULL,     -- battle | craft
            tag_ids  TEXT NOT NULL DEFAULT '[]'  -- JSON int array
        );

        CREATE TABLE IF NOT EXISTS talent_tags (
            talent_id INTEGER NOT NULL REFERENCES talents(id),
            tag_id    INTEGER NOT NULL REFERENCES tags(id),
            PRIMARY KEY (talent_id, tag_id)
        );
    ''')

    # ── Tags ──────────────────────────────────────────────────────────────────
    tags = [
        # tribe tags
        (1,  'tribe',   'savagehorn', 'Savagehorn', '蠻角'),
        (2,  'tribe',   'wildwolf',   'Wildwolf',   '野狼'),
        (3,  'tribe',   'fang',       'Fang',       '毒牙'),
        (4,  'tribe',   'claw',       'Claw',       '利爪'),
        (5,  'tribe',   'flint',      'Flint',      '火石'),
        # class tags
        (6,  'class',   'battle',     'Battle',     '戰鬥'),
        (7,  'class',   'hunter',     'Hunter',     '獵手'),
        (8,  'class',   'warrior',    'Warrior',    '戰士'),
        (9,  'class',   'defender',   'Defender',   '衛士'),
        (10, 'class',   'craft',      'Craft',      '工藝'),
        (11, 'class',   'laborer',      'Laborer',      '力工'),
        (12, 'class',   'handyman',      'Handyman',      '雜工'),
        (13, 'class',   'craftman',      'Craftman',      '匠人'),
        # general (untagged talents available to all)
        (14, 'general', 'general',    'General',    '通用'),
    ]
    c.executemany('INSERT OR IGNORE INTO tags VALUES (?,?,?,?,?)', tags)

    # ── Tribe enum ────────────────────────────────────────────────────────────
    tribes = [
        (1, 'savagehorn', 'Savagehorn', '蠻角', '[1]'),
        (2, 'wildwolf',   'Wildwolf',   '野狼', '[2]'),
        (3, 'fang',       'Fang',       '毒牙', '[3]'),
        (4, 'claw',       'Claw',       '利爪', '[4]'),
        (5, 'flint',      'Flint',      '火石', '[5]'),
    ]
    c.executemany('INSERT OR IGNORE INTO tribe_enum VALUES (?,?,?,?,?)', tribes)

    # ── Class enum ────────────────────────────────────────────────────────────
    # battle classes: tag_ids = [battle(6), specific_class_tag]
    # craft classes:  tag_ids = [craft(7)]  (sub-class tags TBD)
    classes = [
        (1,  'defender_low',   'Defender (Low)',   '衛士(低)', 'battle', '[6,9]'),
        (2,  'defender_mid',   'Defender (Mid)',   '衛士(中)', 'battle', '[6,9]'),
        (3,  'defender_high',  'Defender (High)',  '衛士(高)', 'battle', '[6,9]'),
        (4,  'hunter_low',     'Hunter (Low)',     '獵手(低)', 'battle', '[6,7]'),
        (5,  'hunter_mid',     'Hunter (Mid)',     '獵手(中)', 'battle', '[6,7]'),
        (6,  'hunter_high',    'Hunter (High)',    '獵手(高)', 'battle', '[6,7]'),
        (7,  'warrior_low',    'Warrior (Low)',    '戰士(低)', 'battle', '[6,8]'),
        (8,  'warrior_mid',    'Warrior (Mid)',    '戰士(中)', 'battle', '[6,8]'),
        (9,  'warrior_high',   'Warrior (High)',   '戰士(高)', 'battle', '[6,8]'),
        (10, 'craftman_low',    'Craftman (Low)',    '匠人(低)', 'craft',  '[10,13]'),
        (11, 'craftman_mid',    'Craftman (Mid)',    '匠人(中)', 'craft',  '[10,13]'),
        (12, 'craftman_high',   'Craftman (High)',   '匠人(高)', 'craft',  '[10,13]'),
        (13, 'handyman_low',   'Handyman (Low)',   '雜工(低)', 'craft',  '[10,12]'),
        (14, 'handyman_mid',   'Handyman (Mid)',   '雜工(中)', 'craft',  '[10,12]'),
        (15, 'handyman_high',  'Handyman (High)',  '雜工(高)', 'craft',  '[10,12]'),
        (16, 'laborer_low',    'Laborer (Low)',    '力工(低)', 'craft',  '[10,11]'),
        (17, 'laborer_mid',    'Laborer (Mid)',    '力工(中)', 'craft',  '[10,11]'),
        (18, 'laborer_high',   'Laborer (High)',   '力工(高)', 'craft',  '[10,11]'),
    ]
    c.executemany('INSERT OR IGNORE INTO class_enum VALUES (?,?,?,?,?,?)', classes)

    conn.commit()
    conn.close()
    print(f"DB setup complete: {DB_PATH}")


if __name__ == '__main__':
    setup()
