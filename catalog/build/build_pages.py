#!/usr/bin/env python3
import json, html, os, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # damirco/
SITE = ROOT / 'site'
DATA = SITE / 'catalog' / 'data'
OUT = SITE / 'catalog'

def esc(s):
    return html.escape('' if s is None else str(s), quote=True)

def fmt_price(p):
    p = ('' if p is None else str(p)).strip()
    if not p: return 'Цена по запросу'
    p = p.replace(' ', '').replace(',', '.')
    try:
        n = float(p)
        s = f"{n:,.2f}"  # 1,234.56
        s = s.replace(',', ' ').replace('.', ',')
        return s + ' ₽'
    except Exception:
        return ' '.join(str(p).split()) + ' ₽'

def resolve_photo_src(photo, site_root_prefix):
    """photo is external URL or site-root-relative path; return src usable from current page."""
    photo = (photo or '').strip()
    if not photo:
        return ''
    if _re.match(r'^https?://', photo, _re.I):
        return photo
    return site_root_prefix + photo.lstrip('/')

def layout(title, body, rel='', description='', extra_head='', back_href=None, hero_title='', hero_desc=''):
    # rel is relative prefix to /catalog/ root from this page, e.g. '' for /catalog/, '../' for category, '../../' for product
    css = rel + 'assets/catalog.css'
    js = rel + 'assets/catalog.js'
    site_root = rel + '../'
    logo = site_root + 'vendor/static.tildacdn.com/tild3836-3065-4361-b230-346163353065/photo.jpg'
    if not back_href:
        back_href = site_root + 'index.html#search-products'
    hero_html = ''
    if hero_title or hero_desc:
        hero_html = '<div class="header-info">'
        if hero_title:
            hero_html += f'<div class="header-title">{esc(hero_title)}</div>'
        if hero_desc:
            hero_html += f'<p>{esc(hero_desc)}</p>'
        hero_html += '</div>'
    nav = f'''
<header class="site-header"><div class="container inner">
  <a class="header-back" href="{esc(back_href)}" aria-label="Назад">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
  </a>
  <a class="brand-logo" href="{esc(site_root + 'index.html')}" aria-label="ДАМИР ГРУПП">
    <img src="{esc(logo)}" alt="ДАМИР ГРУПП">
  </a>
  {hero_html}
</div></header>'''
    desc_meta = f'<meta name="description" content="{esc(description)}" />' if description else ''
    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(title)}</title>
  {desc_meta}
  <link rel="stylesheet" href="{css}" />
  {extra_head}
</head>
<body>
{nav}
{body}
<footer class="footer"><div class="container">© ДАМИР ГРУПП. Каталог носит информационный характер. Уточняйте наличие и цены у менеджера: <a href="mailto:damirgrupp@mail.ru">damirgrupp@mail.ru</a>, +7 (495) 363-71-60.</div></footer>
<script src="{js}"></script>
</body>
</html>'''

def cat_sidebar(categories, active_slug, rel_to_catalog, interactive=False):
    items=[]
    for c in categories:
        href = rel_to_catalog + c['slug'] + '/'
        cls = ' class="active"' if c['slug']==active_slug else ''
        icon = rel_to_catalog + 'assets/icons/' + c['slug'] + '.png'
        data = f' data-cat="{esc(c["slug"])}"' if interactive else ''
        items.append(
            f'<li><a{cls}{data} href="{href}">'
            f'<span class="cat-icon"><img src="{esc(icon)}" alt="" loading="lazy"></span>'
            f'<span class="cat-name">{esc(c["name"])}</span>'
            f'<span class="cat-count">{c["count"]}</span>'
            f'</a></li>'
        )
    return '<aside class="panel"><h3>Разделы каталога</h3><ul class="cat-list">' + ''.join(items) + '</ul></aside>'

import re as _re

def re_search_size(label):
    return bool(_re.search(r'размер|диаметр|длина|толщина', label or '', _re.I))

def render_variants_block(p):
    variants = p.get('variants') or []
    specs = p.get('specs') or []
    parts = []
    # if structured variants with options table
    if variants:
        # collect option keys
        opt_keys = []
        for v in variants:
            opts = v.get('options') or {}
            for k in opts.keys():
                if k not in opt_keys: opt_keys.append(k)
        if opt_keys:
            # table
            headers = opt_keys + [h for h in ['sku','price','priceold','quantity'] if any(v.get(h) for v in variants)]
            head_html = ''.join(f'<th>{esc(h if h not in ("sku","price","priceold","quantity") else {"sku":"Артикул","price":"Цена","priceold":"Старая цена","quantity":"Наличие"}[h])}</th>' for h in headers)
            rows=[]
            for v in variants:
                opts = v.get('options') or {}
                cells=[]
                for h in headers:
                    if h in opts: val = opts.get(h,'')
                    else: val = v.get(h,'')
                    if h in ('price','priceold') and val: val = fmt_price(val)
                    cells.append(f'<td>{esc(val)}</td>')
                rows.append('<tr>'+''.join(cells)+'</tr>')
            parts.append('<div class="block"><h3>Размерный ряд / варианты</h3><div class="table-wrap"><table><thead><tr>'+head_html+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div></div>')
        else:
            # simple list
            lis=[]
            for v in variants:
                label = v.get('label') or v.get('sku') or ''
                price = fmt_price(v.get('price')) if v.get('price') else ''
                txt = label + ((' — '+price) if price and 'Цена' not in price else (' — '+price if price else ''))
                if not txt.strip(): continue
                lis.append(f'<li>{esc(txt)}</li>')
            if lis:
                parts.append('<div class="block"><h3>Размерный ряд / варианты</h3><ul class="size-list">'+''.join(lis)+'</ul></div>')
    # also show specs as characteristics if present and not redundant
    if specs:
        # render spec lists (can include size ranges)
        spec_html=[]
        for sp in specs:
            label = sp.get('label','')
            vals = sp.get('values') or []
            raw = sp.get('raw','')
            if len(vals) > 1:
                # if looks like a size range spec, render as size list
                if re_search_size(label):
                    lis = ''.join(f'<li>{esc(v)}</li>' for v in vals if v and not v.startswith('(и ещё'))
                    note = ''
                    for v in vals:
                        if v.startswith('(и ещё'): note = f'<div class="notice">{esc(v)}</div>'
                    spec_html.append(f'<div style="margin-top:10px"><strong>{esc(label)}:</strong><ul class="size-list">{lis}</ul>{note}</div>')
                else:
                    spec_html.append(f'<div style="margin-top:8px"><strong>{esc(label)}:</strong> {esc(", ".join(vals))}</div>')
            else:
                spec_html.append(f'<div style="margin-top:8px"><strong>{esc(label)}:</strong> {esc(raw)}</div>')
        if spec_html and not parts:
            parts.append('<div class="block"><h3>Характеристики и размеры</h3>' + ''.join(spec_html) + '</div>')
        elif spec_html:
            parts.append('<div class="block"><h3>Характеристики</h3>' + ''.join(spec_html) + '</div>')
    return ''.join(parts)

def main():
    with open(DATA/'catalog.json', encoding='utf-8') as f:
        catalog = json.load(f)
    categories = catalog['categories']
    products = catalog['products']

    # index page
    hero_desc = f"Полный ассортимент ДАМИР ГРУПП: {catalog['meta']['total']} позиций в {len(categories)} разделах. Описания, характеристики и размерные ряды."
    body = f'''
<div class="container section">
  <div class="layout">
    {cat_sidebar(categories, '', '', interactive=True)}
    <main>
      <div class="catalog-sticky">
        <div class="toolbar">
          <input id="catalog-search" class="search-input" type="search" placeholder="Поиск по всем товарам..." />
          <span id="catalog-meta" class="meta-line"></span>
        </div>
        <h2 id="catalog-sticky-title" class="catalog-sticky-title">Популярное из каталога</h2>
      </div>
      <section class="section" id="search-section" hidden>
        <div id="search-results" class="grid"></div>
      </section>
      <section class="section" id="popular-section">
        <div id="popular-root" class="popular-grid"></div>
      </section>
      <section class="section" id="category-section" hidden>
        <div id="category-root" class="grid"></div>
      </section>
    </main>
  </div>
</div>
<script>
document.addEventListener('DOMContentLoaded', function() {{
  var searchData = null;
  var popularData = null;
  var activeCat = '';
  var activeCatName = '';
  var popularSection = document.getElementById('popular-section');
  var categorySection = document.getElementById('category-section');
  var stickyTitle = document.getElementById('catalog-sticky-title');
  var categoryRoot = document.getElementById('category-root');
  var searchSection = document.getElementById('search-section');
  var searchResults = document.getElementById('search-results');
  var searchInput = document.getElementById('catalog-search');
  var searchMeta = document.getElementById('catalog-meta');
  var sidebarLinks = Array.prototype.slice.call(document.querySelectorAll('.cat-list a[data-cat]'));

  function norm(s) {{ return String(s||'').toLowerCase().replace(/ё/g,'е').replace(/[^a-zа-я0-9]+/g,' ').trim(); }}
  function loadSearch() {{
    if (searchData) return Promise.resolve(searchData);
    return DamirCatalog.loadJSON('data/search.json').then(function(items) {{ searchData = items || []; return searchData; }});
  }}
  function renderPopular() {{
    if (popularData) {{ DamirCatalog.renderGrid(popularData, '#popular-root', '', 9); return; }}
    DamirCatalog.loadJSON('data/popular.json').then(function(items) {{
      popularData = (items || []).slice(0, 9);
      DamirCatalog.renderGrid(popularData, '#popular-root', '', 9);
    }}).catch(function(){{}});
  }}
  function setActive(slug) {{
    sidebarLinks.forEach(function(a) {{ a.classList.toggle('active', a.getAttribute('data-cat') === slug); }});
  }}
  function updatePlaceholder() {{
    if (!searchInput) return;
    searchInput.placeholder = activeCat ? ('Поиск в разделе «' + activeCatName + '»...') : 'Поиск по всем товарам...';
  }}
  function setStickyTitle(text) {{
    if (stickyTitle) stickyTitle.textContent = text || '';
  }}
  function showCurrentView() {{
    searchSection.hidden = true;
    searchResults.innerHTML = '';
    if (activeCat) {{
      popularSection.hidden = true;
      categorySection.hidden = false;
      setStickyTitle(activeCatName || 'Раздел');
    }} else {{
      categorySection.hidden = true;
      popularSection.hidden = false;
      setStickyTitle('Популярное из каталога');
    }}
  }}
  function runSearch() {{
    var q = norm(searchInput ? searchInput.value : '');
    if (!q) {{
      if (searchMeta) searchMeta.textContent = '';
      showCurrentView();
      return;
    }}
    loadSearch().then(function(items) {{
      var list = items;
      if (activeCat) list = list.filter(function(x) {{ return x.cs === activeCat; }});
      var terms = q.split(' ').filter(Boolean);
      list = list.filter(function(x) {{
        var hay = norm((x.t||'') + ' ' + (x.b||'') + ' ' + (x.c||''));
        return terms.every(function(t) {{ return hay.indexOf(t) !== -1; }});
      }});
      popularSection.hidden = true;
      categorySection.hidden = true;
      searchSection.hidden = false;
      setStickyTitle(activeCat ? ('Результаты поиска: ' + activeCatName) : 'Результаты поиска');
      if (searchMeta) searchMeta.textContent = 'Найдено: ' + list.length;
      DamirCatalog.renderGrid(list, '#search-results', '', 60);
    }});
  }}
  function openCategory(slug, name) {{
    activeCat = slug;
    activeCatName = name || '';
    setActive(slug);
    updatePlaceholder();
    setStickyTitle(activeCatName || 'Раздел');
    categoryRoot.innerHTML = '<div class="empty">Загрузка...</div>';
    loadSearch().then(function(items) {{
      var list = items.filter(function(x) {{ return x.cs === slug; }});
      DamirCatalog.renderGrid(list, '#category-root', '', 500);
    }}).catch(function() {{ categoryRoot.innerHTML = '<div class="empty">Не удалось загрузить товары.</div>'; }});
    if (searchInput && norm(searchInput.value)) {{ runSearch(); }}
    else {{ showCurrentView(); }}
  }}
  function closeCategory() {{
    activeCat = '';
    activeCatName = '';
    setActive('');
    updatePlaceholder();
    categoryRoot.innerHTML = '';
    if (searchInput && norm(searchInput.value)) {{ runSearch(); }}
    else {{ showCurrentView(); }}
  }}

  sidebarLinks.forEach(function(a) {{
    a.addEventListener('click', function(e) {{
      e.preventDefault();
      var slug = a.getAttribute('data-cat') || '';
      var nameEl = a.querySelector('.cat-name');
      var name = nameEl ? nameEl.textContent : '';
      if (activeCat === slug) {{ closeCategory(); return; }}
      openCategory(slug, name);
    }});
  }});

  if (searchInput) searchInput.addEventListener('input', runSearch);
  renderPopular();
  updatePlaceholder();

  var params = new URLSearchParams(window.location.search || '');
  var openSlug = params.get('open');
  if (openSlug) {{
    var match = sidebarLinks.find(function(a) {{ return a.getAttribute('data-cat') === openSlug; }});
    if (match) {{
      var n = match.querySelector('.cat-name');
      openCategory(openSlug, n ? n.textContent : '');
      match.scrollIntoView({{block:'nearest'}});
    }}
  }}
}});
</script>'''
    (OUT/'index.html').write_text(layout('Каталог — ДАМИР ГРУПП', body, '', 'Каталог крепежа ДАМИР ГРУПП: все разделы, поиск, описания и размеры.', hero_title='Каталог продукции', hero_desc=hero_desc), encoding='utf-8')

    # category pages
    for c in categories:
        cdir = OUT / c['slug']
        cdir.mkdir(parents=True, exist_ok=True)
        items = [p for p in products if p['category_slug']==c['slug']]
        # render grid server-side for SEO/basic no-JS, and also enable search within
        cards=[]
        for p in items:
            href = '../p/' + p['slug'] + '/'
            img = resolve_photo_src(p.get('photo') or '', '../../')
            price = fmt_price(p.get('price'))
            img_html = f'<img loading="lazy" src="{esc(img)}" alt="{esc(p["title"])}">' if img else '<div class="ph">Нет фото</div>'
            brand = f'<div class="card-brand">{esc(p.get("brand",""))}</div>' if p.get('brand') else ''
            badge = '<span class="badge">Есть варианты</span>' if p.get('has_variants') else ''
            cards.append(f'''<article class="card"><a class="card-img" href="{href}">{img_html}</a><div class="card-body"><div class="card-cat">{esc(p["category"])}</div><div class="card-title"><a href="{href}">{esc(p["title"])}</a></div>{brand}<div class="price-row"><span class="price">{esc(price)}</span> {badge}</div></div></article>''')
        body = f'''
<div class="container">
  <div class="breadcrumbs"><a href="../index.html">Каталог</a> / <span>{esc(c["name"])}</span></div>
  <div class="layout">
    {cat_sidebar(categories, c['slug'], '../')}
    <main>
      <div class="catalog-sticky">
        <h1 class="catalog-sticky-title">{esc(c["name"])}</h1>
        <div class="toolbar"><input id="catalog-search" class="search-input" type="search" placeholder="Поиск в разделе «{esc(c["name"])}»..." /><span id="catalog-meta" class="meta-line">Товаров: {len(items)}</span></div>
      </div>
      <div id="catalog-results" class="grid">{''.join(cards)}</div>
    </main>
  </div>
</div>
<script>document.addEventListener('DOMContentLoaded',function(){{ DamirCatalog.initSearch({{base:'../', input:'#catalog-search', results:'#catalog-results', meta:'#catalog-meta', category:{json.dumps(c['name'], ensure_ascii=False)}, limit:500}}); }});</script>'''
        (cdir/'index.html').write_text(layout(f'{c["name"]} — Каталог ДАМИР ГРУПП', body, '../', f'{c["name"]} — {len(items)} товаров в каталоге ДАМИР ГРУПП.', back_href=f'../index.html?open={esc(c["slug"])}', hero_title='Каталог продукции'), encoding='utf-8')

    # product pages
    pdir = OUT / 'p'
    pdir.mkdir(parents=True, exist_ok=True)
    for p in products:
        d = pdir / p['slug']
        d.mkdir(parents=True, exist_ok=True)
        img = resolve_photo_src(p.get('photo') or '', '../../../')
        img_html = f'<img src="{esc(img)}" alt="{esc(p["title"])}">' if img else '<div class="ph" style="padding:40px;color:#9ca3af">Нет фото</div>'
        brand = p.get('brand') or ''
        kv = []
        kv.append(('Раздел', f'<a href="../../{esc(p["category_slug"])}/">{esc(p["category"])}</a>'))
        if brand: kv.append(('Бренд', esc(brand)))
        if p.get('sku'): kv.append(('Артикул (SKU)', esc(p['sku'])))
        if p.get('external_id') and p.get('external_id')!=p.get('sku'): kv.append(('Внешний ID', esc(p['external_id'])))
        price = p.get('price') or ''
        price_old = p.get('price_old') or ''
        price_main = f'<span class="product-price-main">{esc(fmt_price(price))}</span>' if price else '<span class="product-price-main" style="color:#6b7280;font-size:20px;">Цена по запросу</span>'
        price_html = price_main + (f' <span class="price-old">{esc(fmt_price(price_old))}</span>' if price_old else '')
        kv.append(('Цена', price_html))
        if p.get('quantity'): kv.append(('Наличие', esc(p['quantity'])))
        if p.get('url'): kv.append(('Страница на сайте', f'<a href="{esc(p["url"])}" target="_blank" rel="noopener">Открыть</a>'))
        kv_html = ''.join(f'<div>{k}</div><div>{v}</div>' for k,v in kv)

        desc = (p.get('description') or '').strip()
        text = (p.get('text') or '').strip()
        # avoid duplicate identical blocks
        desc_block = ''
        main_desc = desc or text
        if desc and text and desc.strip() != text.strip():
            main_desc = desc + '\n\n' + text
        elif desc:
            main_desc = desc
        else:
            main_desc = text
        if main_desc:
            desc_block = f'<div class="block"><h3>Описание</h3><div class="desc">{esc(main_desc)}</div></div>'

        variants_block = render_variants_block(p)

        # related/popular within category
        body = f'''
<div class="container">
  <div class="breadcrumbs"><a href="../../index.html">Каталог</a> / <a href="../../{esc(p["category_slug"])}/">{esc(p["category"])}</a> / <span>{esc(p["title"])}</span></div>
  <div class="product-page">
    <div class="product-gallery"><div class="main-img">{img_html}</div></div>
    <div class="product-info">
      <h1>{esc(p["title"])}</h1>
      {('<div class="card-brand">'+esc(brand)+'</div>') if brand else ''}
      <div class="kv">{kv_html}</div>
      <div style="margin-top:14px"><a class="btn" href="mailto:damirgrupp@mail.ru?subject={html.escape('Запрос по товару: '+p['title'], quote=True)}">Запросить предложение</a></div>
      <div class="notice">Для заказа и уточнения актуальной цены/наличия отправьте запрос на почту или позвоните +7 (495) 363-71-60.</div>
    </div>
  </div>
  {desc_block}
  {variants_block}
  <div class="section">
    <h2>Другие товары раздела</h2>
    <div class="rel-carousel-wrap">
      <button type="button" class="rel-car-arrow rel-car-prev" id="rel-prev" aria-label="Прокрутить влево"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg></button>
      <div id="related-root" class="rel-carousel" aria-label="Другие товары раздела"></div>
      <button type="button" class="rel-car-arrow rel-car-next" id="rel-next" aria-label="Прокрутить вправо"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg></button>
    </div>
  </div>
</div>
<script>
document.addEventListener('DOMContentLoaded', function(){{
  function esc(s){{return String(s==null?'':s).replace(/[&<>"']/g,function(c){{return {{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c];}});}}
  function fmtPrice(p){{
    p=(p==null?'':String(p)).replace(/\\s+/g,'').replace(',', '.').trim();
    if(!p) return 'Цена по запросу';
    var n=Number(p); if(!isFinite(n)) return String(p)+' ₽';
    var parts=n.toFixed(2).split('.'); parts[0]=parts[0].replace(/\\B(?=(\\d{{3}})+(?!\\d))/g,' ');
    return parts[0]+','+parts[1]+' ₽';
  }}
  function photoSrc(ph){{ ph=String(ph||'').trim(); if(!ph) return ''; if(/^https?:\\/\\//i.test(ph)) return ph; return '../../' + ph.replace(/^\\/+/, ''); }}
  function card(p){{
    var href='../../p/'+encodeURIComponent(p.s||p.slug||'')+'/';
    var img=photoSrc(p.ph||p.photo||'');
    var imgHtml=img?'<img src="'+esc(img)+'" alt="'+esc(p.t||p.title||'')+'" loading="lazy">':'<div class="rel-ph">Нет фото</div>';
    return '<article class="rel-card">'
      +'<a class="rel-img" href="'+href+'">'+imgHtml+'</a>'
      +'<div class="rel-body">'
      +'<div class="rel-cat">'+esc(p.c||p.category||'')+'</div>'
      +'<a class="rel-title" href="'+href+'" title="'+esc(p.t||p.title||'')+'">'+esc(p.t||p.title||'')+'</a>'
      +'<div class="rel-price">'+esc(fmtPrice(p.p||p.price))+'</div>'
      +'</div></article>';
  }}
  function setupCarousel(track, prev, next){{
    function step(){{ return Math.max(track.clientWidth*0.8, 240); }}
    function update(){{
      var max=track.scrollWidth-track.clientWidth-4;
      prev.disabled = track.scrollLeft <= 4;
      next.disabled = track.scrollLeft >= max;
    }}
    if(!track.dataset.carouselInit){{
      prev.addEventListener('click', function(){{ track.scrollBy({{left:-step(),behavior:'smooth'}}); }});
      next.addEventListener('click', function(){{ track.scrollBy({{left:step(),behavior:'smooth'}}); }});
      track.addEventListener('scroll', function(){{ window.requestAnimationFrame(update); }});
      window.addEventListener('resize', update);
      track.dataset.carouselInit='1';
    }}
    setTimeout(update, 60);
  }}
  var track=document.getElementById('related-root');
  var prev=document.getElementById('rel-prev');
  var next=document.getElementById('rel-next');
  if(track && prev && next) setupCarousel(track,prev,next);
  DamirCatalog.loadJSON('../../data/search.json').then(function(items){{
    var rel = items.filter(function(x){{ return x.cs === {json.dumps(p['category_slug'], ensure_ascii=False)} && x.i !== {p['id']}; }}).slice(0,12);
    if(track) track.innerHTML = rel.map(card).join('');
    if(track && prev && next) setupCarousel(track,prev,next);
  }}).catch(function(){{}});
}});
</script>'''
        title = f'{p["title"]} — {p["category"]} — ДАМИР ГРУПП'
        desc_meta = (p.get('description') or p.get('text') or '')[:180].replace('\n',' ')
        (d/'index.html').write_text(layout(title, body, '../../', desc_meta, back_href=f'../../index.html?open={esc(p["category_slug"])}', hero_title='Каталог продукции'), encoding='utf-8')

    print('generated catalog pages: index,', len(categories), 'categories,', len(products), 'products')

if __name__ == '__main__':
    main()
