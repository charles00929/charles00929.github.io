'use strict';
const { createApp } = Vue;

// ─── Helper ───────────────────────────────────────────────────────────────────
function iconSrc(icon) {
  return icon ? icon : '';
}
function talentTip(t) {
  if (!t) return {};
  // description_values 填入 # 佔位
  let desc = t.description || '';
  if (t.description_values?.length) {
    const vals = t.description_values.map(v => `<b>${v}</b>`);
    let i = 0;
    desc = desc.replace(/#/g, () => vals[i++] ?? '#');
  }
  return { 'data-tip-name': t.name, 'data-tip-desc': desc };
}

// ─── Component: TalentSelect ──────────────────────────────────────────────────
// 用途：選擇單一天賦，顯示 icon + name，支援搜尋
const TalentSelect = {
  name: 'TalentSelect',
  props: {
    modelValue:  { default: null },
    options:     { type: Array,   default: () => [] },
    placeholder: { type: String,  default: '請選擇天賦' },
    nullable:    { type: Boolean, default: true },
  },
  emits: ['update:modelValue'],
  data() { return { search: '', open: false }; },
  mounted() {
    this._close = (e) => { if (!this.$el.contains(e.target)) this.open = false; };
    document.addEventListener('click', this._close);
  },
  beforeUnmount() {
    document.removeEventListener('click', this._close);
  },
  computed: {
    selected() { return this.options.find(o => o.id === this.modelValue) || null; },
    filtered() {
      const q = this.search.trim().toLowerCase();
      return q ? this.options.filter(o => o.name.toLowerCase().includes(q)) : this.options;
    },
  },
  methods: {
    pick(id) { this.$emit('update:modelValue', id); this.open = false; this.search = ''; },
    iconSrc,
    talentTip,
  },
  template: `
<div class="position-relative">
  <button type="button"
    class="btn btn-outline-secondary w-100 text-start d-flex align-items-center gap-2 py-1"
    @click.stop="open = !open">
    <template v-if="selected">
          <img :src="iconSrc(selected.icon)"
               v-bind="talentTip(selected)"
               class="talent-icon-sm rounded-1 flex-shrink-0"
               @error="$event.target.style.opacity='.3'">
      <span class="flex-grow-1 text-truncate small">{{ selected.name }}</span>
    </template>
    <span v-else class="text-muted small flex-grow-1">{{ placeholder }}</span>
    <span class="ms-auto text-muted" style="font-size:.65rem">▼</span>
  </button>
  <div v-show="open" class="talent-dropdown-menu">
    <div class="p-1 border-bottom">
      <input v-model="search" type="text" class="form-control form-control-sm"
             placeholder="搜尋..." @click.stop>
    </div>
    <ul class="list-unstyled mb-0 overflow-auto" style="max-height:220px">
      <li v-if="nullable">
        <button type="button" class="dropdown-item text-muted small py-1"
                @click.stop="pick(null)">— 無 —</button>
      </li>
      <li v-for="opt in filtered" :key="opt.id">
        <button type="button"
          class="dropdown-item d-flex align-items-center gap-2 py-1"
          :class="{'active': opt.id === modelValue}"
          @click.stop="pick(opt.id)">
          <img :src="iconSrc(opt.icon)"
               v-bind="talentTip(opt)"
               class="talent-icon-sm rounded-1 flex-shrink-0"
               @error="$event.target.style.opacity='.3'">
          <span class="small text-truncate">{{ opt.name }}</span>
        </button>
      </li>
      <li v-if="!filtered.length" class="p-2 text-muted text-center small">無符合結果</li>
    </ul>
  </div>
</div>`,
};

// ─── Component: CharacterSelect ───────────────────────────────────────────────
// 用途：選擇角色，顯示 name + 所有天賦 icon（傳承機制用）
const CharacterSelect = {
  name: 'CharacterSelect',
  props: {
    modelValue:  { default: null },
    characters:  { type: Array,  default: () => [] },
    talentsMap:  { type: Object, default: () => ({}) },
    placeholder: { type: String, default: '請選擇角色' },
  },
  emits: ['update:modelValue'],
  data() { return { open: false }; },
  mounted() {
    this._close = (e) => { if (!this.$el.contains(e.target)) this.open = false; };
    document.addEventListener('click', this._close);
  },
  beforeUnmount() {
    document.removeEventListener('click', this._close);
  },
  computed: {
    selected() { return this.characters.find(c => c.id === this.modelValue) || null; },
  },
  methods: {
    pick(id) { this.$emit('update:modelValue', id); this.open = false; },
    iconSrc,
    talentTip,
    talentIcons(char) {
      return [
        char.tribe_talent_id,
        char.origin_talent_id,
        char.experience_talent_id,
        char.title_talent_id,
        ...char.talent_ids,
      ].filter(id => id != null).map(id => this.talentsMap[id]).filter(Boolean);
    },
  },
  template: `
<div class="position-relative">
  <button type="button"
    class="btn btn-outline-secondary w-100 text-start py-1"
    @click.stop="open = !open">
    <span v-if="selected" class="small">
      {{ selected.name }} <span class="text-muted">(#{{ selected.id }})</span>
    </span>
    <span v-else class="text-muted small">{{ placeholder }}</span>
  </button>
  <div v-show="open" class="talent-dropdown-menu">
    <ul class="list-unstyled mb-0 overflow-auto" style="max-height:300px">
      <li v-if="!characters.length">
        <span class="dropdown-item text-muted small">無可選角色</span>
      </li>
      <li v-for="char in characters" :key="char.id">
        <button type="button"
          class="dropdown-item py-2"
          :class="{'active': char.id === modelValue}"
          @click.stop="pick(char.id)">
          <div class="small fw-semibold">
            {{ char.name }} <span class="text-muted fw-normal">(#{{ char.id }})</span>
          </div>
          <div class="d-flex gap-1 flex-wrap mt-1">
            <img v-for="t in talentIcons(char)" :key="t.id"
                 :src="iconSrc(t.icon)"
                 v-bind="talentTip(t)"
                 width="20" height="20" class="rounded-1"
                 @error="$event.target.style.opacity='.3'">
          </div>
        </button>
      </li>
    </ul>
  </div>
</div>`,
};

// ─── Component: CharacterCard ─────────────────────────────────────────────────
const CharacterCard = {
  name: 'CharacterCard',
  props: {
    char:       { type: Object, required: true },
    talentsMap: { type: Object, default: () => ({}) },
    tribes:     { type: Array,  default: () => [] },
    classes:    { type: Array,  default: () => [] },
  },
  emits: ['edit', 'delete', 'inherit'],
  computed: {
    tribeName() {
      const t = this.tribes.find(t => t.id === this.char.tribe_id);
      return t ? t.ch_name : '—';
    },
    className() {
      const c = this.classes.find(c => c.id === this.char.class_id);
      return c ? c.ch_name : '—';
    },
    displayTalents() {
      return [
        this.char.tribe_talent_id,
        this.char.origin_talent_id,
        this.char.experience_talent_id,
        this.char.title_talent_id,
        ...this.char.talent_ids,
      ].filter(id => id != null).map(id => this.talentsMap[id]).filter(Boolean);
    },
  },
  methods: { iconSrc, talentTip },
  template: `
<div class="card h-100 shadow-sm">
  <div class="card-body p-2">
    <div class="d-flex justify-content-between align-items-start mb-1">
      <div class="small fw-bold text-truncate">
        {{ char.name }} <span class="text-muted fw-normal">(#{{ char.id }})</span>
      </div>
      <div class="dropdown flex-shrink-0 ms-1">
        <button class="btn btn-sm btn-link p-0 lh-1 text-muted" data-bs-toggle="dropdown">⋮</button>
        <ul class="dropdown-menu dropdown-menu-end">
          <li><button class="dropdown-item small" @click="$emit('edit', char)">✏️ 編輯</button></li>
          <li><button class="dropdown-item small" @click="$emit('inherit', char)">🔗 傳承</button></li>
          <li><hr class="dropdown-divider my-1"></li>
          <li><button class="dropdown-item small text-danger" @click="$emit('delete', char.id)">🗑 刪除</button></li>
        </ul>
      </div>
    </div>
    <div class="text-muted small mb-2">{{ tribeName }} — {{ className }}</div>
    <div class="d-flex flex-wrap gap-1">
      <img v-for="t in displayTalents" :key="t.id"
           :src="iconSrc(t.icon)"
           v-bind="talentTip(t)"
           class="talent-icon rounded-1 border"
           @error="$event.target.style.opacity='.3'">
      <span v-if="!displayTalents.length" class="text-muted small fst-italic">無天賦</span>
    </div>
  </div>
</div>`,
};

// ─── Main App ─────────────────────────────────────────────────────────────────
createApp({
  components: { TalentSelect, CharacterSelect, CharacterCard },

  data() {
    return {
      loading: true,
      talents: [],
      talentsMap: {},
      pools: {},
      tribes: [],
      classes: [],
      characters: [],
      nextId: 1,

      // 手動生成／編輯
      manualForm: {
        id: null, name: '', tribe_id: null, class_id: null,
        origin_talent_id: null, experience_talent_id: null, title_talent_id: null,
        talent_ids: [],
      },

      // 傳承
      inheritForm: { master_id: null, student_id: null },
      inheritResult: null,
      inheritError: '',

      // 分享
      shareString: '',
      importString: '',

      _modals: {},
    };
  },

  computed: {
    originTalents() {
      const cls = this.classes.find(c => c.id === this.manualForm?.class_id);
      return this.buildSlotPool('origin', cls);
    },
    experienceTalents() { return this.talents.filter(t => t.slot === 'experience'); },
    titleTalents() {
      const cls = this.classes.find(c => c.id === this.manualForm?.class_id);
      return this.buildSlotPool('title', cls);
    },
    normalTalents()     { return this.talents.filter(t => t.slot === 'normal'); },

    // Manual modal 用：部落天賦選項（依選取的部落過濾）
    manualTribeOptions() {
      const tribeKey = this.tribes.find(t => t.id === this.manualForm?.tribe_id)?.key;
      if (!tribeKey) return [];
      return this.pools.tribe?.[tribeKey] || [];
    },

    // Manual modal 用：一般天賦選項
    manualNormalOptions() {
      return this.talents.filter(t => t.slot === 'normal');
    },


    // 傳承：徒弟必須天賦未滿 6 且不能是師父
    eligibleStudents() {
      return this.characters.filter(c =>
        c.id !== this.inheritForm.master_id && c.talent_ids.length < 6
      );
    },
  },

  watch: {
    'inheritForm.master_id'()  { this.inheritResult = null; this.inheritError = ''; },
    'inheritForm.student_id'() { this.inheritResult = null; this.inheritError = ''; },
  },

  async mounted() {
    await this.loadData();
    this.loadCharacters();
    this.$nextTick(() => {
      ['Manual', 'Inherit', 'Share'].forEach(name => {
        const el = document.getElementById('modal' + name);
        if (el) this._modals[name] = new bootstrap.Modal(el);
      });
    });
  },

  methods: {
    // ── 資料載入 ──────────────────────────────────────────────────────────────
    async loadData() {
      this.loading = true;
      try {
        const [talents, pools, tribes, classes] = await Promise.all([
          fetch('data/talents.json').then(r => r.json()),
          fetch('data/talent_pools.json').then(r => r.json()),
          fetch('data/tribes.json').then(r => r.json()),
          fetch('data/classes.json').then(r => r.json()),
        ]);
        this.talents    = talents;
        this.talentsMap = Object.fromEntries(talents.map(t => [t.id, t]));
        this.pools      = pools;
        this.tribes     = tribes;
        this.classes    = classes;
      } catch (e) {
        console.error('Failed to load data', e);
      }
      this.loading = false;
    },

    loadCharacters() {
      try {
        const raw = localStorage.getItem('soulmask_chars');
        if (!raw) return;
        const data = JSON.parse(LZString.decompressFromUTF16(raw));
        this.characters = data.characters || [];
        this.nextId     = data.nextId || (this.characters.length + 1);
      } catch (e) {
        console.error('Failed to load characters', e);
      }
    },

    saveCharacters() {
      const data = JSON.stringify({ characters: this.characters, nextId: this.nextId });
      localStorage.setItem('soulmask_chars', LZString.compressToUTF16(data));
    },

    // ── 自然生成 ──────────────────────────────────────────────────────────────
    autoGenerate() {
      if (this.loading) return;

      // 1. 選部落
      const tribe = this.pickRandom(this.tribes);
      // 2. 選職業
      const cls   = this.pickRandom(this.classes);

      const used = new Set();

      // 3. 選 origin（依部落決定池子，Outcast 部落用專屬池）
      const origin_talent_id     = this.pickTalents(this.buildOriginPool(tribe?.key, cls), 1, used)[0] ?? null;

      // 4. 選稱號（依職業類別過濾）
      const title_talent_id      = this.pickTalents(this.buildTitlePool(cls), 1, used)[0] ?? null;

      // 5. 選部落天賦（剛好 1 筆）
      const tribe_talent_id      = this.pickTalents(this.pools.tribe?.[tribe?.key] || [], 1, used)[0] ?? null;

      // 6. 選一般天賦（1~5 筆，只從 normal 池）
      const count      = Math.floor(Math.random() * 5) + 1;
      const talent_ids = this.pickTalents(this.buildNormalPool(tribe?.id, cls?.id), count, used);

      // experience 天賦獨立選取（目前只有 1 筆）
      const experience_talent_id = this.pickTalents(this.pools.experience || [], 1, used)[0] ?? null;

      const char = {
        id:                   this.nextId++,
        name:                 (tribe?.ch_name ?? '') + (cls?.ch_name ?? '族人'),
        tribe_id:             tribe?.id ?? null,
        class_id:             cls?.id   ?? null,
        origin_talent_id,
        experience_talent_id,
        title_talent_id,
        tribe_talent_id,
        talent_ids,
      };
      if (this.characters.length >= 100) this.characters.shift();
      this.characters.push(char);
      this.saveCharacters();
    },

    // 回傳 slot 的天賦物件陣列（給 ManualForm 選項用），依職業群過濾
    buildSlotPool(slot, cls) {
      const bucket  = this.pools[slot] || {};
      const general = bucket.ungroup || [];
      if (!cls) return general;
      const catPool = bucket[cls.category] || [];
      const seen = new Set(catPool.map(t => t.id));
      return [...catPool, ...general.filter(t => !seen.has(t.id))];
    },

    // 回傳自然生成用的 origin 候選 ID 陣列
    buildOriginPool(tribeKey, cls) {
      const bucket  = this.pools.origin || {};
      const general = bucket.ungroup || [];
      if (!cls) return general;
      return [...new Set([...(bucket[cls.category] || []), ...general])];
    },

    // 回傳自然生成用的 title 候選 ID 陣列
    buildTitlePool(cls) {
      const bucket  = this.pools.title || {};
      const general = bucket.ungroup || [];
      if (!cls) return general;
      return [...new Set([...(bucket[cls.category] || []), ...general])];
    },

    // 回傳一般天賦候選 ID 陣列（L1→L4 巢狀聯集）
    // 支援新格式：craft 無部落層，直接為 class bucket
    buildNormalPool(tribe_id, class_id) {
      const n     = this.pools.normal || {};
      const tribe = tribe_id ? this.tribes.find(t => t.id === tribe_id)  : null;
      const cls   = class_id ? this.classes.find(c => c.id === class_id) : null;
      const ids   = new Set();
      const add   = arr => (arr || []).forEach(id => ids.add(id));

      add(n.ungroup);  // L1 ungroup（無 category tag）

      const cats = cls ? [cls.category] : ['battle', 'craft'];
      cats.forEach(cat => {
        const catBucket = n[cat];
        if (!catBucket) return;
        if (Array.isArray(catBucket)) { add(catBucket); return; }

        add(catBucket.ungroup);  // L2 ungroup（category 通用）

        const tribeKey    = tribe?.key;
        const tribeBucket = tribeKey ? catBucket[tribeKey] : null;

        if (tribeBucket != null) {
          // 有部落層（battle）
          if (Array.isArray(tribeBucket)) {
            add(tribeBucket);
          } else {
            add(tribeBucket.ungroup);  // L3 ungroup
            if (cls) {
              add(tribeBucket[cls.key]);  // L4 specific class
            } else {
              Object.entries(tribeBucket)
                .filter(([k]) => k !== 'ungroup')
                .forEach(([, v]) => add(Array.isArray(v) ? v : []));
            }
          }
        } else {
          // 無部落層（craft），class bucket 直接在 catBucket 下
          if (cls) {
            add(catBucket[cls.key]);
          } else if (!tribeKey) {
            // 無部落篩選：展開所有 sub-bucket
            Object.entries(catBucket)
              .filter(([k]) => k !== 'ungroup')
              .forEach(([, v]) => {
                if (Array.isArray(v)) add(v);
                else { add(v.ungroup); Object.entries(v).filter(([k]) => k !== 'ungroup').forEach(([, a]) => add(a)); }
              });
          }
          // else: 有部落篩選但此 category 無部落層，僅 L2 ungroup 已加入
        }
      });

      return [...ids];
    },

    pickRandom(arr) {
      return arr.length ? arr[Math.floor(Math.random() * arr.length)] : null;
    },

    // pool: talent 物件或 id 陣列；amount: 取幾個；used: Set（以 id 過濾並更新）
    pickTalents(pool, amount, used = null) {
      const getId = item => (typeof item === 'object' && item !== null) ? item.id : item;
      const avail  = used ? pool.filter(item => !used.has(getId(item))) : [...pool];
      const picked = avail.sort(() => Math.random() - 0.5).slice(0, amount);
      const ids    = picked.map(getId);
      if (used) ids.forEach(id => used.add(id));
      return ids;
    },


    // ── 手動生成 / 編輯 ───────────────────────────────────────────────────────
    openManual(char) {
      this.manualForm = char
        ? { ...char, talent_ids: [...char.talent_ids] }
        : {
            id: null, name: '', tribe_id: null, class_id: null,
            origin_talent_id: null, experience_talent_id: null, title_talent_id: null,
            tribe_talent_id: null,
            talent_ids: [],
          };
      this._modals.Manual?.show();
    },

    updateTalentSlot(i, id) {
      const arr = Array.from({ length: 6 }, (_, j) => this.manualForm.talent_ids[j] ?? null);
      arr[i] = id;
      // 移除尾端空白並壓縮
      let last = -1;
      for (let j = 5; j >= 0; j--) { if (arr[j] != null) { last = j; break; } }
      this.manualForm.talent_ids = arr.slice(0, last + 1).filter(x => x != null);
    },

    saveManual() {
      const f    = this.manualForm;
      const char = {
        id:                   f.id ?? this.nextId++,
        name:                 f.name.trim() || '族人',
        tribe_id:             f.tribe_id,
        class_id:             f.class_id,
        origin_talent_id:     f.origin_talent_id,
        experience_talent_id: f.experience_talent_id,
        title_talent_id:      f.title_talent_id,
        tribe_talent_id:      f.tribe_talent_id,
        talent_ids:           f.talent_ids.filter(x => x != null).slice(0, 6),
      };
      if (f.id != null) {
        const idx = this.characters.findIndex(c => c.id === f.id);
        if (idx >= 0) this.characters.splice(idx, 1, char);
      } else {
        if (this.characters.length >= 100) this.characters.shift();
        this.characters.push(char);
      }
      this.saveCharacters();
      this._modals.Manual?.hide();
    },

    // ── 刪除 ──────────────────────────────────────────────────────────────────
    deleteChar(id) {
      this.characters = this.characters.filter(c => c.id !== id);
      this.saveCharacters();
    },

    // ── 傳承 ──────────────────────────────────────────────────────────────────
    openInherit(char) {
      this.inheritForm   = { master_id: char?.id ?? null, student_id: null };
      this.inheritResult = null;
      this.inheritError  = '';
      this._modals.Inherit?.show();
    },

    rollInherit() {
      this.inheritResult = null;
      this.inheritError  = '';
      const master  = this.characters.find(c => c.id === this.inheritForm.master_id);
      const student = this.characters.find(c => c.id === this.inheritForm.student_id);
      if (!master || !student)            { this.inheritError = '請選擇師父與徒弟。'; return; }
      if (student.talent_ids.length >= 6) { this.inheritError = '徒弟已有 6 個天賦，無法再傳承。'; return; }
      if (!master.talent_ids.length)      { this.inheritError = '師父沒有一般天賦可傳授。'; return; }
      // 徒弟的有效天賦池（依部落與職業條件）
      const studentPool  = new Set(this.buildNormalPool(student.tribe_id, student.class_id));
      // 排除徒弟已擁有 或 不符合徒弟條件的天賦
      const studentOwned = new Set(student.talent_ids);
      const available    = master.talent_ids.filter(id => studentPool.has(id) && !studentOwned.has(id));
      if (!available.length) { this.inheritError = '師父沒有符合徒弟部落/職業條件的可傳授天賦。'; return; }
      const pickedId     = this.pickRandom(available);
      this.inheritResult = this.talentsMap[pickedId] || null;
    },

    confirmInherit() {
      if (!this.inheritResult) return;
      const student = this.characters.find(c => c.id === this.inheritForm.student_id);
      if (!student || student.talent_ids.length >= 6) return;
      // 防止重複寫入
      if (student.talent_ids.includes(this.inheritResult.id)) return;
      student.talent_ids.push(this.inheritResult.id);
      this.saveCharacters();
      this._modals.Inherit?.hide();
    },

    // ── 儲存/分享 ─────────────────────────────────────────────────────────────
    openShare() {
      const data       = JSON.stringify({ characters: this.characters, nextId: this.nextId });
      this.shareString = LZString.compressToBase64(data);
      this.importString = '';
      this._modals.Share?.show();
    },

    copyShare() {
      navigator.clipboard.writeText(this.shareString)
        .then(() => alert('已複製到剪貼板！'))
        .catch(() => alert('複製失敗，請手動選取複製。'));
    },

    importChars() {
      try {
        const raw  = LZString.decompressFromBase64(this.importString.trim());
        const data = JSON.parse(raw);
        if (!Array.isArray(data.characters)) throw new Error('格式不合法');
        this.characters = data.characters;
        this.nextId     = data.nextId || (data.characters.length + 1);
        this.saveCharacters();
        this._modals.Share?.hide();
      } catch (e) {
        alert('匯入失敗：' + e.message);
      }
    },

    iconSrc,
    talentTip,
  },
}).mount('#app');
