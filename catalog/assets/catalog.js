(function(){
  function qs(sel, root){ return (root||document).querySelector(sel); }
  function qsa(sel, root){ return Array.prototype.slice.call((root||document).querySelectorAll(sel)); }
  function esc(s){ return String(s==null?'':s).replace(/[&<>"']/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c])); }
  function fmtPrice(p){
    if(p==null||p==='') return '';
    var s = String(p).replace(/\s+/g,'').replace(',', '.').trim();
    var n = Number(s);
    if(!isFinite(n)) return String(p).trim() + ' ₽';
    var parts = n.toFixed(2).split('.');
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    return parts[0] + ',' + parts[1] + ' ₽';
  }
  function norm(s){ return String(s||'').toLowerCase().replace(/ё/g,'е').replace(/[^a-zа-я0-9]+/g,' ').trim(); }

  async function loadJSON(url){
    const r = await fetch(url, {cache:'no-cache'});
    if(!r.ok) throw new Error('HTTP '+r.status);
    return r.json();
  }

  function resolvePhotoSrc(photo, base){
    photo = String(photo || '').trim();
    if(!photo) return '';
    if(/^https?:\/\//i.test(photo)) return photo;
    var siteRootPrefix = '../' + (base || ''); // base is relative to catalog root; catalog root is one level below site root
    return siteRootPrefix + photo.replace(/^\/+/, '');
  }

  function cardHTML(p, base){
    base = base || '';
    const href = base + 'p/' + encodeURIComponent(p.s || p.slug) + '/';
    const img = resolvePhotoSrc(p.ph || p.photo || '', base);
    const price = p.p || p.price || '';
    return '<article class="card">'+
      '<a class="card-img" href="'+esc(href)+'">'+(img?'<img loading="lazy" src="'+esc(img)+'" alt="'+esc(p.t||p.title)+'">':'<div class="ph">Нет фото</div>')+'</a>'+
      '<div class="card-body">'+
        '<div class="card-cat">'+esc(p.c||p.category||'')+'</div>'+
        '<div class="card-title"><a href="'+esc(href)+'">'+esc(p.t||p.title)+'</a></div>'+
        (p.b||p.brand?'<div class="card-brand">'+esc(p.b||p.brand)+'</div>':'')+
        '<div class="price-row">'+(price?'<span class="price">'+esc(fmtPrice(price))+'</span>':'<span class="price" style="color:#6b7280;font-weight:500">Цена по запросу</span>')+'</div>'+
      '</div>'+
    '</article>';
  }

  function renderGrid(items, root, base, limit){
    const el = typeof root==='string'?qs(root):root; if(!el) return;
    const list = (limit?items.slice(0,limit):items);
    if(!list.length){ el.innerHTML = '<div class="empty">Ничего не найдено</div>'; return; }
    el.innerHTML = list.map(p=>cardHTML(p, base)).join('');
  }

  async function initSearch(opts){
    opts = opts||{};
    const input = qs(opts.input||'#catalog-search');
    const results = qs(opts.results||'#catalog-results');
    const meta = qs(opts.meta||'#catalog-meta');
    if(!input || !results) return;
    const base = opts.base || '';
    let index = [];
    try { index = await loadJSON(opts.dataUrl || (base + 'data/search.json')); } catch(e){ results.innerHTML='<div class="empty">Не удалось загрузить каталог</div>'; return; }
    const category = opts.category || '';
    const baseList = category ? index.filter(x=>x.c===category || x.cs===category) : index;
    function run(){
      const q = norm(input.value);
      let list = baseList;
      if(q){
        const terms = q.split(' ').filter(Boolean);
        list = baseList.filter(x=>{
          const hay = norm((x.t||'')+' '+(x.b||'')+' '+(x.c||''));
          return terms.every(t=>hay.indexOf(t)!==-1);
        });
      }
      renderGrid(list, results, base, opts.limit || 60);
      if(meta) meta.textContent = 'Найдено: ' + list.length + (q? ' по запросу «'+input.value+'»':'' );
    }
    input.addEventListener('input', run);
    run();
    return {index, run};
  }

  async function initPopular(opts){
    opts=opts||{};
    const root = qs(opts.root||'#popular-root'); if(!root) return;
    const base = opts.base || '';
    try{
      const items = await loadJSON(opts.dataUrl || (base + 'data/popular.json'));
      renderGrid(items, root, base, opts.limit || 12);
    }catch(e){ root.innerHTML='<div class="empty">Не удалось загрузить популярные товары</div>'; }
  }

  function initStickyCompact(){
    const sticky = qs('.layout > main .catalog-sticky');
    if(!sticky) return;
    let lastY = window.scrollY || 0;
    function onScroll(){
      const y = window.scrollY || 0;
      const desktop = window.innerWidth >= 901;
      if(!desktop){ sticky.classList.remove('is-compact'); lastY = y; return; }
      if(y > 140 && y >= lastY) sticky.classList.add('is-compact');
      else if(y < 80) sticky.classList.remove('is-compact');
      lastY = y;
    }
    window.addEventListener('scroll', onScroll, {passive:true});
    window.addEventListener('resize', onScroll);
    onScroll();
  }

  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initStickyCompact);
  else initStickyCompact();

  window.DamirCatalog = { initSearch, initPopular, renderGrid, loadJSON, esc };
})();