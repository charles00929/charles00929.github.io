# 執行順序
1. 建立開發環境，必須模擬掛在 GitHub 的靜態頁服務
2. 實作資料整理腳本，產出 `*.json` 供前端 fetch 載入；若 GitHub Pages 有 CORS 問題，備用方案改產出帶有 `const {tablename} = [];` 的 js 檔，以 `<script src>` 載入
3. 生成模擬器介面（Vue + Bootstrap）
4. 完成模擬生成角色，並使用 lz-string 存取角色清單（LocalStorage）
5. 完成「傳承」機制功能
6. 綜合測試

# 目標
首先，我想要放在個人github的某個分頁，意味著可能最後結果會是HTML+JS+CSS。這個靜態頁會提供一個簡易模擬器，需要模擬遊戲生成角色的隨機天賦，需要特別注意種族與職業的專屬天賦；第二項功能是，模擬遊戲中後天配置天賦的機制，這裡就不細說。資料的部分，就我剛剛提供的連結算是很完整，只需要抓下來整理成 JSON檔，圖片考慮直接引用連結，但我很想也順手把圖片備份留下。

# 技術棧
 - 前端: 
   - vue CDN
   - bootstrap CDN
   - lz string CDN
 - 後端: (資料處理腳本，不是伺服器)
   - python 
   - sqlite

# 開發環境
1個nginx模擬 github 服務靜態頁面，1個 python 執行環境處理資料整理，docker compose 整合。

# 功能
## 模擬器
一個簡易模擬器，模擬遊戲生成角色時隨機賦予的天賦，而天賦會因為`種族`、`職業`、`類型`而有不同的`天賦池`。
遊戲中的角色可以擁有1個`部落天賦`，1個`經驗天賦`，1個`title天賦`，和6個一般天賦。除了一般天賦外，其餘的天賦在角色生成時就不能改變。當然，模擬器通通都調整。
模擬器提供：自然生成(仿遊戲)，與手動生成。
一般天賦獲得或遺忘是有`順序性`的。獲得時1->2->3->...，遺忘時 6->5->4...。
模擬器可以保留生成的角色(100個)。
模擬器可以模擬遊戲中`傳承`機制，`師父`傳授`徒弟`時，會隨機從`師父`擁有的一般天賦中挑選一個賦予`徒弟`。若徒弟已經滿6個，則不能被傳授。

## 資料處理
用簡易的方式將目標網頁的資料(https://saraserenity.net/soulmask/natural_gift.php)整理成專案內的資料結構，並且以`*.json`提供給模擬器使用。
目前已經將需要的HTML資料表，手動拆解並放在 `soulmask/_data/*`。

# 開發
## 模擬器
模擬器使用vue+bootstrap的CDN開發，資料用lcoalstorage儲存。
角色生成時，關聯tags, tags個別從天賦資料中撈出成一個池子，再將多池子聯集，最後成該角色的天賦池。
沒有被tag到的天賦也會成一個池子，被聯集到所有角色中。
### 角色資料結構
```JSON
{
  "id": 87,
  "name": "族人",
  "tribe_id": 5, //nullable
  "class_id": 12, //nullable
  "origin_talent_id": 61, //nullable
  "experience_talent_id": 53, //nullable
  "title_talent_id": 103, //nullable
  "talent_ids": [55,66,77,88,99,110]

}
```
ID 全部關聯來自後端生成的 *.json  
### 天賦池組合邏輯
Python 預處理階段產出 `talent_pools.json`，結構如下：
```json
{
  "origin":     [1, 2, 3],
  "experience": [10, 11],
  "title":      [20, 21],
  "normal": {
    "general":    [30, 31, 32],
    "savagehorn": [50, 51],
    "wildwolf":   [60, 61],
    "battle":     [70, 71],
    "craft":      [80, 81]
  }
}
```
前端角色生成時直接組合對應 key 的池子：
```js
pool = [
  ...talentPools.normal.general,
  ...talentPools.normal[tribe_key],
  ...talentPools.normal[class_key],
]
// Set 去重後隨機撈
```
角色資料結構本身不存 tag_ids，改由 enum 端維護 mapping，前端只需查 `tribe_enum` / `class_enum` 取得 `key`。

### UI 
清單以1列3欄使用 Bootstrap `card` 元件排列角色卡片。
卡片三行資訊：
- 第一行：`名稱 (ID)`
- 第二行：`部落全名 - 職業全名`（nullable 顯示為 `-`）
- 第三行：依序顯示天賦 icon，順序為 `部落天賦`、`經驗天賦`、`稱號天賦`、`一般天賦(最多6個)`



## 資料處理
預計會需要`sqlite`建立資料結構，以及整理過的資料。這份sqlite 只會在`爬資料`的時候使用，最後會透過python程式轉換成json提供給前端模擬器，而json 的結構也會貼近sqlite定義的結構，會有數個json files。
結構分以下幾張表：
 * talents: 所有天賦資料
 * tribes: 部落名稱 enum
 * class: 角色職業 enum
   * 兩大類 (工藝, 戰鬥)
     * 工藝：匠人、雜工、力工
     * 戰鬥：衛士、獵手、戰士
   * 每個職業都有分高、中、低，三階
 * tags: 定義天賦所在的池子
 * talent_tags: 實際關聯天賦會出現在那些池子的多對多資料
  
```
talents
------------
id:int
talent_ids:json -- id in game, there are 3 level per one telent.
name:string
description:string 
description_values:json -- fill in description slots(#) by level
icon:str -- image uri 
```

```
tribe_enum
------------
id:int
key:string
en_name:string
ch_name:string
tag_ids:json -- 關聯的 tag id 列表，用於組合天賦池
```

```
class_enum
------------
id:int
key:string
en_name:string
ch_name:string
tag_ids:json -- 關聯的 tag id 列表，用於組合天賦池
```

```
tags
------------
id:int
category:string -- tribe | class | general
en_name:string
ch_name:string
```
```
talent_tags
------------
talent_id:int
tag_id:int
```
