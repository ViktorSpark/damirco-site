(() => {
  const PIN = '3456';
  const pathKey = 'wk-edit:' + location.pathname;
  const $ = (s, r=document) => r.querySelector(s);
  const $$ = (s, r=document) => [...r.querySelectorAll(s)];
  const page = $('.wk-main');
  if (!page) return;

  const state = { on: false, saved: load() };

  function load() {
    try { return JSON.parse(localStorage.getItem(pathKey) || '{}'); } catch { return {}; }
  }
  function persist() { localStorage.setItem(pathKey, JSON.stringify(state.saved)); }
  function uid() { return 'fn' + Math.random().toString(36).slice(2, 9); }

  function ensureScaffold() {
    if ($('.wk-edit-bar')) return;
    const bar = document.createElement('div');
    bar.className = 'wk-edit-bar';
    bar.innerHTML = `
      <div class="wk-edit-bar__inner">
        <div class="wk-edit-bar__status">Режим редактирования</div>
        <button class="wk-btn wk-btn--primary" data-act="save">Сохранить</button>
        <button class="wk-btn" data-act="export">Экспорт JSON</button>
        <button class="wk-btn" data-act="import">Импорт JSON</button>
        <button class="wk-btn wk-btn--danger" data-act="reset">Сбросить</button>
        <button class="wk-btn" data-act="exit">Выйти</button>
      </div>`;
    document.body.prepend(bar);

    const pin = document.createElement('div');
    pin.className = 'wk-pin-modal';
    pin.innerHTML = `
      <div class="wk-pin-dialog">
        <h2>Режим редактирования</h2>
        <p>Введите PIN-код из 4 цифр для входа в режим редактирования.</p>
        <input inputmode="numeric" maxlength="4" pattern="[0-9]*" placeholder="••••" aria-label="PIN-код">
        <div class="wk-pin-error"></div>
        <div class="wk-row">
          <button class="wk-btn" data-act="pin-cancel">Отмена</button>
          <button class="wk-btn wk-btn--primary" data-act="pin-ok">Войти</button>
        </div>
      </div>`;
    document.body.appendChild(pin);

    const formula = document.createElement('div');
    formula.className = 'wk-formula-modal';
    formula.innerHTML = `
      <div class="wk-formula-dialog">
        <h2 style="margin:0 0 8px;font:400 24px/1.3 'Linux Libertine','Georgia','Times',serif">Формула</h2>
        <p style="margin:0 0 10px;color:#54595d;font-size:14px">Введите LaTeX. Пример: <code>E = mc^2</code> или <code>\\frac{a}{b}</code>.</p>
        <textarea placeholder="LaTeX формулы"></textarea>
        <div class="wk-formula-preview"></div>
        <div class="wk-row">
          <button class="wk-btn" data-act="formula-cancel">Отмена</button>
          <button class="wk-btn wk-btn--primary" data-act="formula-insert">Вставить</button>
        </div>
      </div>`;
    document.body.appendChild(formula);

    const nav = $('.wk-nav');
    if (nav && !$('.wk-edit-toggle', nav)) {
      const a = document.createElement('a');
      a.href = '#';
      a.className = 'wk-edit-toggle';
      a.textContent = 'Редактировать';
      a.addEventListener('click', (e) => { e.preventDefault(); openPin(); });
      nav.appendChild(a);
    }

    bar.addEventListener('click', onBarClick);
    pin.addEventListener('click', (e) => { if (e.target === pin) closePin(); });
    pin.querySelector('[data-act="pin-cancel"]').addEventListener('click', closePin);
    pin.querySelector('[data-act="pin-ok"]').addEventListener('click', submitPin);
    pin.querySelector('input').addEventListener('keydown', (e) => { if (e.key === 'Enter') submitPin(); });
    formula.addEventListener('click', (e) => { if (e.target === formula) closeFormula(); });
    formula.querySelector('[data-act="formula-cancel"]').addEventListener('click', closeFormula);
    formula.querySelector('[data-act="formula-insert"]').addEventListener('click', insertFormula);
    formula.querySelector('textarea').addEventListener('input', renderFormulaPreview);
  }

  function openPin() { ensureScaffold(); $('.wk-pin-modal').classList.add('is-open'); const i=$('.wk-pin-modal input'); i.value=''; $('.wk-pin-error').textContent=''; i.focus(); }
  function closePin() { $('.wk-pin-modal')?.classList.remove('is-open'); }
  function submitPin() {
    const v = $('.wk-pin-modal input').value.trim();
    if (v === PIN) { closePin(); enableEdit(); }
    else $('.wk-pin-error').textContent = 'Неверный PIN-код.';
  }

  function enableEdit() {
    ensureScaffold();
    state.on = true;
    document.body.classList.add('wk-editing');
    $('.wk-edit-bar').classList.add('is-on');
    setupEditable();
  }
  function disableEdit() {
    state.on = false;
    document.body.classList.remove('wk-editing');
    $('.wk-edit-bar')?.classList.remove('is-on');
    teardownEditable();
  }

  function onBarClick(e) {
    const act = e.target?.dataset?.act;
    if (act === 'save') save();
    if (act === 'export') exportJson();
    if (act === 'import') importJson();
    if (act === 'reset') resetEdits();
    if (act === 'exit') disableEdit();
  }

  function setupEditable() {
    const title = $('.wk-title');
    if (title && !title.dataset.bound) {
      title.dataset.bound = '1';
      title.contentEditable = 'true';
      title.classList.add('wk-editable');
      title.dataset.edit = 'title';
    }

    const lead = $('.wk-lead');
    if (lead && !lead.dataset.bound) {
      lead.dataset.bound = '1';
      if (!$('.wk-editor-toolbar', lead.parentElement)) {
        const tb = buildToolbar();
        lead.parentElement.insertBefore(tb, lead);
      }
      lead.contentEditable = 'true';
      lead.classList.add('wk-editable');
      lead.dataset.edit = 'desc';
    }

    setupPhotos();
    setupTable();
    ensureSources();
  }

  function teardownEditable() {
    $$('.wk-editable').forEach(el => el.contentEditable = 'false');
    $$('.wk-editor-toolbar').forEach(el => el.remove());
    $$('.wk-edit-actions').forEach(el => el.remove());
  }

  function buildToolbar() {
    const tb = document.createElement('div');
    tb.className = 'wk-editor-toolbar';
    tb.innerHTML = `
      <select data-cmd="fontSize">
        <option value="">Размер</option>
        <option value="2">Малый</option>
        <option value="3">Обычный</option>
        <option value="4">Крупный</option>
        <option value="5">Очень крупный</option>
      </select>
      <button type="button" data-cmd="bold"><b>Ж</b></button>
      <button type="button" data-cmd="italic"><i>К</i></button>
      <button type="button" data-cmd="underline"><u>Ч</u></button>
      <button type="button" data-cmd="insertUnorderedList">• Список</button>
      <button type="button" data-cmd="createLink">Ссылка</button>
      <button type="button" data-cmd="footnote">Сноска</button>
      <button type="button" data-cmd="formula">Формула</button>
      <button type="button" data-cmd="removeFormat">Очистить</button>`;
    tb.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-cmd]');
      if (!btn) return;
      const cmd = btn.dataset.cmd;
      const desc = $('.wk-lead[contenteditable="true"]');
      if (desc) desc.focus();
      if (cmd === 'bold' || cmd === 'italic' || cmd === 'underline' || cmd === 'insertUnorderedList' || cmd === 'removeFormat') document.execCommand(cmd, false, null);
      if (cmd === 'createLink') {
        const url = prompt('Введите URL ссылки:', 'https://');
        if (url) document.execCommand('createLink', false, url);
      }
      if (cmd === 'footnote') insertFootnote();
      if (cmd === 'formula') openFormula();
    });
    tb.querySelector('select[data-cmd="fontSize"]').addEventListener('change', (e) => {
      const v = e.target.value;
      const desc = $('.wk-lead[contenteditable="true"]');
      if (desc) desc.focus();
      if (v) document.execCommand('fontSize', false, v);
      e.target.value = '';
    });
    return tb;
  }

  function insertFootnote() {
    const sel = window.getSelection();
    if (!sel || !sel.rangeCount) return;
    const desc = $('.wk-lead');
    if (!desc || !desc.contains(sel.anchorNode)) desc?.focus();
    const n = nextFootnoteNum();
    const id = 'ref-' + n + '-' + uid();
    const ref = document.createElement('sup');
    ref.className = 'wk-footnote-ref';
    ref.innerHTML = `<a href="#cite-${n}" id="${id}">[${n}]</a>`;
    const range = sel.getRangeAt(0);
    range.collapse(false);
    range.insertNode(ref);
    range.setStartAfter(ref);
    range.collapse(true);
    sel.removeAllRanges();
    sel.addRange(range);
    ensureSources(n);
    syncSourcesFromRefs();
  }

  function nextFootnoteNum() {
    const nums = $$('.wk-footnote-ref a').map(a => parseInt(a.textContent.replace(/\D/g,''),10)).filter(Boolean);
    return nums.length ? Math.max(...nums) + 1 : 1;
  }

  function ensureSources(forceNum) {
    let sec = $('#wk-sources');
    if (!sec) {
      sec = document.createElement('section');
      sec.className = 'wk-section';
      sec.id = 'wk-sources';
      sec.innerHTML = `<h2>Ссылки на источники</h2><ol class="wk-source-list" data-edit="sources"></ol>`;
      page.appendChild(sec);
    }
    const list = $('.wk-source-list', sec);
    const placeholder = list.querySelector('.wk-empty');
    if (forceNum && placeholder) placeholder.remove();
    if (forceNum) {
      while (list.querySelectorAll('li:not(.wk-empty)').length < forceNum) {
        const n = list.querySelectorAll('li:not(.wk-empty)').length + 1;
        const li = document.createElement('li');
        li.id = 'cite-' + n;
        li.innerHTML = `<a href="https://" target="_blank" rel="noopener">https://</a>`;
        list.appendChild(li);
      }
    }
    if (state.on) makeSourcesEditable();
    return sec;
  }

  function syncSourcesFromRefs() {
    const refs = $$('.wk-footnote-ref a');
    const max = refs.reduce((m,a)=>Math.max(m, parseInt(a.textContent.replace(/\D/g,''),10)||0), 0);
    if (max) ensureSources(max);
  }

  function makeSourcesEditable() {
    const list = $('.wk-source-list');
    if (!list) return;
    list.querySelectorAll('li').forEach((li, i) => {
      if (!li.id) li.id = 'cite-' + (i+1);
      const a = li.querySelector('a');
      if (a && !li.querySelector('input')) {
        const url = a.getAttribute('href') || 'https://';
        const inp = document.createElement('input');
        inp.type = 'url';
        inp.value = url;
        inp.placeholder = 'https://источник...';
        inp.style.cssText = 'width:100%;padding:6px;border:1px solid #a2a9b1;font:13px sans-serif';
        inp.addEventListener('input', () => { a.href = inp.value; a.textContent = inp.value; });
        a.textContent = url;
        li.appendChild(inp);
      }
    });
  }

  function setupPhotos() {
    let sec = $('#wk-photos');
    if (!sec) {
      sec = document.createElement('section');
      sec.className = 'wk-section';
      sec.id = 'wk-photos';
      sec.innerHTML = `<h2>Фотографии</h2><div class="wk-photo-grid" data-edit="photos"></div><div class="wk-edit-actions"><input type="file" accept="image/*" multiple class="wk-photo-input" style="display:none"><button type="button" class="wk-btn" data-act="add-photo">Добавить фото</button></div>`;
      const sources = $('#wk-sources');
      (sources ? page.insertBefore(sec, sources) : page.appendChild(sec));
    }
    const actions = $('.wk-edit-actions', sec);
    if (actions && !actions.dataset.bound) {
      actions.dataset.bound = '1';
      actions.querySelector('[data-act="add-photo"]').addEventListener('click', () => $('.wk-photo-input', sec).click());
      $('.wk-photo-input', sec).addEventListener('change', onAddPhotos);
    }
    renderPhotos();
  }

  function onAddPhotos(e) {
    const files = [...(e.target.files || [])];
    files.forEach(file => {
      const reader = new FileReader();
      reader.onload = () => {
        state.saved.photos = state.saved.photos || [];
        state.saved.photos.push({ src: reader.result, caption: '' });
        renderPhotos(); persist();
      };
      reader.readAsDataURL(file);
    });
    e.target.value = '';
  }

  function renderPhotos() {
    const grid = $('.wk-photo-grid');
    if (!grid) return;
    const photos = state.saved.photos || [];
    grid.innerHTML = photos.map((p, i) => `
      <figure class="wk-photo-card">
        <img src="${p.src}" alt="${escapeHtml(p.caption || 'Фото')}">
        ${state.on ? `<input type="text" value="${escapeHtml(p.caption||'')}" placeholder="Подпись к фото" data-photo-cap="${i}">` : (p.caption ? `<figcaption style="font-size:13px;color:#54595d;margin-top:6px">${escapeHtml(p.caption)}</figcaption>` : '')}
        ${state.on ? `<button type="button" class="wk-btn wk-btn--danger" data-photo-del="${i}">Удалить</button>` : ''}
      </figure>`).join('');
    if (state.on) {
      grid.querySelectorAll('[data-photo-cap]').forEach(inp => inp.addEventListener('input', (e) => { state.saved.photos[+e.target.dataset.photoCap].caption = e.target.value; persist(); }));
      grid.querySelectorAll('[data-photo-del]').forEach(btn => btn.addEventListener('click', (e) => { state.saved.photos.splice(+e.target.dataset.photoDel,1); renderPhotos(); persist(); }));
    }
  }

  function setupTable() {
    const table = $('.wikitable');
    if (!table) return;
    table.classList.add('wk-table-edit');
    if (state.on) {
      table.querySelectorAll('td').forEach(td => td.contentEditable = 'true');
      let wrap = table.closest('.wk-table-wrap');
      let sec = table.closest('.wk-section');
      if (sec && !$('.wk-edit-actions', sec)) {
        const actions = document.createElement('div');
        actions.className = 'wk-edit-actions';
        actions.innerHTML = `<button type="button" class="wk-btn" data-act="add-row">Добавить строку</button><button type="button" class="wk-btn wk-btn--danger" data-act="del-row">Удалить последнюю строку</button>`;
        actions.querySelector('[data-act="add-row"]').addEventListener('click', addRow);
        actions.querySelector('[data-act="del-row"]').addEventListener('click', delRow);
        sec.appendChild(actions);
      }
    } else {
      table.querySelectorAll('td').forEach(td => td.contentEditable = 'false');
    }
  }

  function addRow() {
    const table = $('.wikitable');
    if (!table) return;
    const tbody = table.tBodies[0] || table;
    const cols = table.tHead?.rows?.[0]?.cells?.length || tbody.rows?.[0]?.cells?.length || 5;
    const tr = document.createElement('tr');
    for (let i=0;i<cols;i++){ const td=document.createElement('td'); td.contentEditable='true'; td.textContent=''; tr.appendChild(td); }
    tbody.appendChild(tr);
  }
  function delRow() {
    const table = $('.wikitable');
    const tbody = table?.tBodies?.[0];
    if (tbody && tbody.rows.length) tbody.deleteRow(tbody.rows.length-1);
  }

  function openFormula() {
    ensureScaffold();
    const m = $('.wk-formula-modal');
    m.classList.add('is-open');
    m.querySelector('textarea').value = '';
    m.querySelector('.wk-formula-preview').innerHTML = '<span style="color:#54595d">Предпросмотр формулы</span>';
    m.querySelector('textarea').focus();
  }
  function closeFormula() { $('.wk-formula-modal')?.classList.remove('is-open'); }
  function renderFormulaPreview() {
    const latex = $('.wk-formula-modal textarea').value;
    const prev = $('.wk-formula-modal .wk-formula-preview');
    prev.textContent = latex ? '$$' + latex + '$$' : 'Предпросмотр формулы';
    if (window.katex) { try { window.katex.render(latex, prev, {throwOnError:false, displayMode:true}); } catch(e){ prev.textContent = latex; } }
  }
  function insertFormula() {
    const latex = $('.wk-formula-modal textarea').value.trim();
    if (!latex) return;
    const desc = $('.wk-lead[contenteditable="true"]');
    if (desc) desc.focus();
    const span = document.createElement('span');
    span.className = 'wk-math';
    span.dataset.latex = latex;
    span.textContent = '$$' + latex + '$$';
    const sel = window.getSelection();
    if (sel && sel.rangeCount) { const r=sel.getRangeAt(0); r.collapse(false); r.insertNode(span); r.setStartAfter(span); r.collapse(true); sel.removeAllRanges(); sel.addRange(r); }
    else desc?.appendChild(span);
    closeFormula();
    renderMath();
  }

  function escapeHtml(s){ return (s||'').replace(/[&<>"']/g, c=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c])); }

  function collectSources() {
    const lis = $$('.wk-source-list li');
    return lis.map((li, i) => {
      const inp = li.querySelector('input');
      const a = li.querySelector('a');
      const url = (inp ? inp.value : a?.getAttribute('href')) || '';
      return { id: li.id || ('cite-' + (i+1)), url };
    }).filter(s => s.url && s.url !== 'https://');
  }

  function save() {
    const title = $('.wk-title');
    const desc = $('.wk-lead');
    const table = $('.wikitable');
    state.saved.title = title ? title.innerText.trim() : state.saved.title;
    state.saved.desc = desc ? desc.innerHTML : state.saved.desc;
    state.saved.sources = collectSources();
    if (table) {
      const head = table.tHead ? table.tHead.innerHTML : '';
      const body = table.tBodies[0] ? table.tBodies[0].innerHTML : '';
      state.saved.table = { head, body };
    }
    persist();
    renderPhotos();
    const status = $('.wk-edit-bar__status');
    if (status) { status.textContent = 'Сохранено локально'; setTimeout(()=>status.textContent='Режим редактирования', 1800); }
  }

  function applySaved() {
    const s = state.saved || {};
    if (s.title) { const t=$('.wk-title'); if (t) t.textContent = s.title; document.title = s.title + ' — База знаний'; }
    if (s.desc) { const d=$('.wk-lead'); if (d) d.innerHTML = s.desc; }
    if (s.table) {
      const table = $('.wikitable');
      if (table) {
        if (s.table.head && table.tHead) table.tHead.innerHTML = s.table.head;
        if (s.table.body && table.tBodies[0]) table.tBodies[0].innerHTML = s.table.body;
      }
    }
    if (s.sources && s.sources.length) {
      const sec = ensureSources();
      const list = $('.wk-source-list', sec);
      list.innerHTML = s.sources.map((src, i) => `<li id="${escapeHtml(src.id || 'cite-'+(i+1))}"><a href="${escapeHtml(src.url)}" target="_blank" rel="noopener">${escapeHtml(src.url)}</a></li>`).join('');
    }
    renderPhotos();
    syncSourcesFromRefs();
    renderMath();
  }

  function exportJson() {
    save();
    const blob = new Blob([JSON.stringify({ path: location.pathname, saved: state.saved }, null, 2)], {type:'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'knowledge-edit.json';
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function importJson() {
    const inp = document.createElement('input');
    inp.type = 'file'; inp.accept = 'application/json';
    inp.onchange = () => {
      const f = inp.files?.[0]; if (!f) return;
      const r = new FileReader();
      r.onload = () => {
        try {
          const data = JSON.parse(r.result);
          state.saved = data.saved || data;
          persist(); applySaved(); if (state.on) { setupEditable(); makeSourcesEditable(); }
        } catch(e) { alert('Не удалось прочитать JSON.'); }
      };
      r.readAsText(f);
    };
    inp.click();
  }

  function resetEdits() {
    if (!confirm('Сбросить локальные изменения для этой страницы?')) return;
    localStorage.removeItem(pathKey);
    location.reload();
  }

  function renderMath() {
    const nodes = $$('.wk-math');
    if (!nodes.length) return;
    if (window.katex) {
      nodes.forEach(n => { try { window.katex.render(n.dataset.latex || n.textContent, n, {throwOnError:false, displayMode:true}); } catch(e){} });
      return;
    }
    if (window.__wkKatexLoading) return;
    window.__wkKatexLoading = true;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css';
    document.head.appendChild(link);
    const s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js';
    s.onload = () => { window.__wkKatexLoading = false; renderMath(); };
    document.head.appendChild(s);
  }

  ensureScaffold();
  applySaved();
})();
