#!/usr/bin/env python3
import sqlite3, os, re, json, html, shutil, math
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[3]  # damirco/
WORKSPACE = Path(__file__).resolve().parents[4]  # Default Project
DB = WORKSPACE / 'mvp-agent-exchange' / 'data' / 'db' / 'catalog_2002.db'
OUT = ROOT / 'site' / 'knowledge'
ASSETS = OUT / 'assets'
IMG_SRC = WORKSPACE / 'mvp-agent-exchange' / 'data' / 'images'
IMG_DST = OUT / 'images'

def slugify(s, maxlen=80):
    s = (s or '').strip().lower().replace('ё', 'е')
    tr = {'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ж':'zh','з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'ts','ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya'}
    out=[]
    for ch in s:
        if ch in tr: out.append(tr[ch])
        elif ch.isalnum(): out.append(ch)
        elif ch in ' -_/.,()': out.append('-')
    slug = re.sub(r'-+','-', ''.join(out)).strip('-')
    return (slug[:maxlen].strip('-') or 'item')

def esc(s):
    return html.escape('' if s is None else str(s), quote=True)

def clean_desc(s):
    s = (s or '').strip()
    # remove breadcrumb prefix like "Главная » ..."
    s = re.sub(r'^Главная\s*»\s*', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def fmt_price(v):
    if v is None or v == '': return ''
    try:
        n=float(v)
        if n<=0: return ''
        return f"{n:,.2f}".replace(',',' ').replace('.',',') + ' ₽'
    except: return esc(v)

def img_name(image_path):
    if not image_path: return ''
    return Path(image_path).name


def rel_img(image_path, base_prefix):
    n = img_name(image_path)
    if not n: return ''
    return base_prefix + 'images/' + n

def page_shell(title, description, base, body, active=''):
    nav = f'''
<header class="kb-header">
  <div class="kb-header__inner">
    <a class="kb-brand" href="{base}index.html">
      <span class="kb-brand__logo">DG</span>
      <span class="kb-brand__text">
        <span class="kb-brand__title">База знаний</span>
        <span class="kb-brand__sub">ДАМИР ГРУПП</span>
      </span>
    </a>
    <nav class="kb-nav" aria-label="Навигация базы знаний">
      <a href="{base}index.html" class="{'is-active' if active=='home' else ''}">Категории</a>
      <a href="{base}gost-din-iso.html" class="{'is-active' if active=='gost' else ''}">ГОСТ / DIN / ISO</a>
      <a href="../index.html">На сайт</a>
    </nav>
  </div>
</header>'''
    return f'''<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{base}assets/knowledge.css">
</head>
<body>
{nav}
<main class="kb-main">
{body}
</main>
<footer class="kb-footer">
  <div class="kb-footer__inner">
    <div>База знаний ДАМИР ГРУПП · На основе открытых справочных данных о крепеже</div>
    <div><a href="../index.html">damirco.ru</a></div>
  </div>
</footer>
</body>
</html>'''

CSS = r'''
:root{--bg:#f4f7f5;--card:#fff;--text:#16202b;--muted:#5d6b78;--line:#dfe8e2;--green:#2f9d6a;--green2:#237a53;--green-soft:#e8f5ee;--radius:18px;--shadow:0 10px 30px rgba(22,32,43,.06)}
*{box-sizing:border-box} body{margin:0;font-family:Inter,system-ui,-apple-system,sans-serif;color:var(--text);background:linear-gradient(180deg,#eef5f1 0,#f7faf8 180px,#f4f7f5 100%);line-height:1.5}
a{color:var(--green2);text-decoration:none} a:hover{text-decoration:underline}
.kb-header{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.92);backdrop-filter:blur(10px);border-bottom:1px solid rgba(223,232,226,.8)}
.kb-header__inner,.kb-main,.kb-footer__inner{max-width:1240px;margin:0 auto;padding:0 20px}
.kb-header__inner{display:flex;align-items:center;justify-content:space-between;gap:20px;min-height:72px}
.kb-brand{display:flex;align-items:center;gap:12px;color:var(--text);text-decoration:none}
.kb-brand__logo{width:42px;height:42px;border-radius:12px;background:linear-gradient(135deg,var(--green),#57b987);color:#fff;display:grid;place-items:center;font-weight:800;font-size:15px;letter-spacing:.02em}
.kb-brand__text{display:flex;flex-direction:column;line-height:1.1}
.kb-brand__title{font-size:18px;font-weight:800} .kb-brand__sub{font-size:12px;color:var(--muted);font-weight:600;letter-spacing:.06em;text-transform:uppercase}
.kb-nav{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}
.kb-nav a{padding:10px 14px;border-radius:10px;color:#34424f;font-weight:600;font-size:14px;text-decoration:none}
.kb-nav a:hover{background:var(--green-soft);color:var(--green2)} .kb-nav a.is-active{background:var(--green-soft);color:var(--green2)}
.kb-main{padding:32px 20px 56px}
.kb-hero{padding:28px 0 24px} .kb-hero h1{margin:0 0 10px;font-size:clamp(30px,4.6vw,52px);line-height:1.05;letter-spacing:-.03em}
.kb-hero p{margin:0;color:var(--muted);max-width:820px;font-size:17px}
.kb-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:24px 0 32px}
.kb-stat{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px;box-shadow:var(--shadow)}
.kb-stat__v{font-size:28px;font-weight:800;color:var(--green2);line-height:1} .kb-stat__l{margin-top:6px;color:var(--muted);font-size:13px;font-weight:500}
.kb-search{margin:0 0 28px} .kb-search input{width:100%;padding:15px 18px;border:1px solid #cedbd3;border-radius:14px;font:inherit;font-size:16px;background:#fff;box-shadow:0 2px 8px rgba(22,32,43,.03)}
.kb-search input:focus{outline:2px solid rgba(47,157,106,.25);border-color:var(--green)}
.kb-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}
.kb-card{display:flex;flex-direction:column;background:var(--card);border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;box-shadow:var(--shadow);color:inherit;text-decoration:none;transition:transform .2s ease,box-shadow .2s ease,border-color .2s}
.kb-card:hover{transform:translateY(-3px);box-shadow:0 16px 36px rgba(22,32,43,.09);border-color:#bcd7c9;text-decoration:none}
.kb-card__img{aspect-ratio:4/3;background:#f0f4f2;display:flex;align-items:center;justify-content:center;overflow:hidden}
.kb-card__img img{width:100%;height:100%;object-fit:contain;padding:18px;background:#fff}
.kb-card__body{padding:18px} .kb-card__title{font-size:17px;font-weight:700;line-height:1.3;margin:0 0 8px;color:var(--text)}
.kb-card__meta{font-size:13px;color:var(--muted);display:flex;gap:10px;flex-wrap:wrap}
.kb-badge{display:inline-flex;align-items:center;padding:4px 10px;border-radius:999px;background:var(--green-soft);color:var(--green2);font-size:12px;font-weight:700}
.kb-breadcrumbs{font-size:14px;color:var(--muted);margin:0 0 18px;display:flex;gap:8px;flex-wrap:wrap} .kb-breadcrumbs a{color:var(--muted)}
.kb-section{margin-top:28px} .kb-section h2{font-size:24px;margin:0 0 14px;letter-spacing:-.02em}
.kb-detail{display:grid;grid-template-columns:minmax(0,420px) minmax(0,1fr);gap:28px;align-items:start}
.kb-detail__img{background:#fff;border:1px solid var(--line);border-radius:20px;padding:20px;box-shadow:var(--shadow)}
.kb-detail__img img{width:100%;height:auto;display:block;max-height:420px;object-fit:contain}
.kb-detail__body{background:#fff;border:1px solid var(--line);border-radius:20px;padding:28px;box-shadow:var(--shadow)}
.kb-detail__body h1{margin:0 0 12px;font-size:clamp(26px,3.4vw,40px);line-height:1.15;letter-spacing:-.02em}
.kb-props{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:18px 0}
.kb-prop{padding:12px 14px;background:#f7faf8;border-radius:12px;border:1px solid #e7eeea}
.kb-prop__k{font-size:12px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.04em}
.kb-prop__v{font-size:15px;font-weight:600;margin-top:3px;word-break:break-word}
.kb-desc{color:#33424f;font-size:15px;line-height:1.75;white-space:pre-line}
.kb-table-wrap{overflow:auto;background:#fff;border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow)}
table.kb-table{width:100%;border-collapse:collapse;font-size:14px;min-width:640px}
.kb-table th,.kb-table td{padding:12px 14px;text-align:left;border-bottom:1px solid #edf2ee;vertical-align:top}
.kb-table th{background:#f7faf8;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;font-weight:700;position:sticky;top:0}
.kb-table tr:last-child td{border-bottom:0}
.kb-empty{padding:28px;background:#fff;border:1px dashed #cfdcd4;border-radius:16px;color:var(--muted)}
.kb-footer{border-top:1px solid var(--line);padding:22px 0;color:var(--muted);font-size:14px}
.kb-footer__inner{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
@media (max-width:980px){.kb-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.kb-detail{grid-template-columns:1fr}.kb-stats{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:640px){.kb-header__inner{padding:14px 16px;flex-direction:column;align-items:stretch}.kb-nav{justify-content:flex-start}.kb-main,.kb-footer__inner{padding-left:16px;padding-right:16px}.kb-grid{grid-template-columns:1fr}.kb-props{grid-template-columns:1fr}.kb-stats{grid-template-columns:1fr 1fr}}
'''

def build():
    con = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute('SELECT * FROM categories ORDER BY name')
    categories = [dict(r) for r in cur.fetchall()]
    cur.execute('SELECT * FROM product_types ORDER BY category_id, name')
    types = [dict(r) for r in cur.fetchall()]
    cur.execute('SELECT * FROM products ORDER BY product_type_id, name')
    products = [dict(r) for r in cur.fetchall()]
    cur.execute('SELECT * FROM gost_din_iso ORDER BY din, name')
    gosts = [dict(r) for r in cur.fetchall()]

    # slugs
    cat_slug = {}
    used = set()
    for c in categories:
        s = slugify(c['name'])
        base=s; i=2
        while s in used: s=f"{base}-{i}"; i+=1
        used.add(s); cat_slug[c['id']] = s

    type_slug = {}
    usedt=set()
    for t in types:
        s = slugify(t['name'])
        base=s; i=2
        while s in usedt: s=f"{base}-{i}"; i+=1
        usedt.add(s); type_slug[t['id']] = s

    prods_by_type = defaultdict(list)
    for p in products: prods_by_type[p['product_type_id']].append(p)
    types_by_cat = defaultdict(list)
    for t in types: types_by_cat[t['category_id']].append(t)

    # assets
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS/'knowledge.css').write_text(CSS, encoding='utf-8')

    # copy images
    IMG_DST.mkdir(parents=True, exist_ok=True)
    if IMG_SRC.exists():
        for f in IMG_SRC.iterdir():
            if f.is_file():
                dst = IMG_DST / f.name
                if not dst.exists():
                    shutil.copy2(f, dst)

    # index
    stats = f'''
<section class="kb-hero">
  <h1>База знаний крепежа</h1>
  <p>Справочник по видам крепежа, стандартам и соответствиям ГОСТ / DIN / ISO. Собрано в статическом виде, чтобы быстро находить нужную информацию прямо на сайте.</p>
</section>
<div class="kb-stats">
  <div class="kb-stat"><div class="kb-stat__v">{len(categories)}</div><div class="kb-stat__l">категорий</div></div>
  <div class="kb-stat"><div class="kb-stat__v">{len(types)}</div><div class="kb-stat__l">типов изделий</div></div>
  <div class="kb-stat"><div class="kb-stat__v">{len(products)}</div><div class="kb-stat__l">размеров/вариантов</div></div>
  <div class="kb-stat"><div class="kb-stat__v">{len(gosts)}</div><div class="kb-stat__l">соответствий ГОСТ/DIN/ISO</div></div>
</div>
<div class="kb-search"><input id="kb-search" type="search" placeholder="Поиск по базе знаний: название, DIN, ГОСТ, ISO..." aria-label="Поиск по базе знаний"></div>
'''

    cat_cards=[]
    for c in categories:
        items = types_by_cat.get(c['id'], [])
        # pick first image
        img=''
        for t in items:
            if t.get('image_path'):
                img = rel_img(t['image_path'], '')
                break
        img_html = f'<img src="{esc(img)}" alt="{esc(c["name"])}" loading="lazy" decoding="async">' if img else '<div style="color:#8aa095;font-weight:600">Нет фото</div>'
        cat_cards.append(f'''
<a class="kb-card" href="categories/{esc(cat_slug[c['id']])}.html" data-search="{esc((c['name'] or '').lower())}">
  <div class="kb-card__img">{img_html}</div>
  <div class="kb-card__body">
    <h2 class="kb-card__title">{esc(c['name'])}</h2>
    <div class="kb-card__meta"><span class="kb-badge">{len(items)} поз.</span></div>
  </div>
</a>''')
    index_body = stats + '<section class="kb-section"><h2>Категории</h2><div class="kb-grid" id="kb-cats">' + ''.join(cat_cards) + '</div></section>'

    # add all-types search list
    type_items=[]
    for t in types:
        cslug = cat_slug.get(t['category_id'],'')
        cname = next((c['name'] for c in categories if c['id']==t['category_id']), '')
        search = ' '.join(filter(None,[t.get('name'), t.get('standard'), t.get('gost'), t.get('iso'), cname])).lower()
        img = rel_img(t.get('image_path'), '')
        img_html = f'<img src="{esc(img)}" alt="{esc(t["name"])}" loading="lazy" decoding="async">' if img else ''
        meta=[]
        if t.get('standard'): meta.append(esc(t['standard']))
        if t.get('gost'): meta.append(esc(t['gost']))
        if t.get('iso'): meta.append(esc(t['iso']))
        meta_html = ' · '.join(meta) if meta else esc(cname)
        type_items.append(f'''
<a class="kb-card kb-type-item" href="items/{esc(type_slug[t['id']])}.html" data-search="{esc(search)}" style="display:none">
  <div class="kb-card__img">{img_html or "<div style='color:#8aa095;font-weight:600'>Нет фото</div>"}</div>
  <div class="kb-card__body">
    <h3 class="kb-card__title">{esc(t['name'])}</h3>
    <div class="kb-card__meta">{meta_html}</div>
  </div>
</a>''')
    index_body += '<section class="kb-section" id="kb-types-section" style="display:none"><h2>Результаты поиска</h2><div class="kb-grid" id="kb-types">' + ''.join(type_items) + '</div><div id="kb-empty" class="kb-empty" style="display:none">Ничего не найдено. Попробуйте другой запрос.</div></section>'
    index_body += '''
<script>
(()=>{
  const q=document.getElementById('kb-search');
  const cats=[...document.querySelectorAll('#kb-cats .kb-card')];
  const types=[...document.querySelectorAll('.kb-type-item')];
  const typeSection=document.getElementById('kb-types-section');
  const empty=document.getElementById('kb-empty');
  const norm=s=> (s||'').toLower().replace(/ё/g,'е').trim();
  q.addEventListener('input',()=>{
    const v=norm(q.value);
    if(!v){
      cats.forEach(c=>c.style.display='');
      types.forEach(t=>t.style.display='none');
      typeSection.style.display='none';
      empty.style.display='none';
      return;
    }
    cats.forEach(c=>{ c.style.display = norm(c.dataset.search).includes(v) ? '' : 'none'; });
    let shown=0;
    types.forEach(t=>{ const ok=norm(t.dataset.search).includes(v); t.style.display=ok?'':'none'; if(ok) shown++; });
    typeSection.style.display='';
    empty.style.display=shown? 'none':'';
  });
})();
</script>
'''
    (OUT/'index.html').write_text(page_shell('База знаний крепежа — ДАМИР ГРУПП', 'Справочник по видам крепежа, стандартам ГОСТ, DIN, ISO.', '', index_body, 'home'), encoding='utf-8')

    # category pages
    for c in categories:
        items = types_by_cat.get(c['id'], [])
        cards=[]
        for t in items:
            img = rel_img(t.get('image_path'), '../')
            img_html = f'<img src="{esc(img)}" alt="{esc(t["name"])}" loading="lazy" decoding="async">' if img else '<div style="color:#8aa095;font-weight:600">Нет фото</div>'
            meta=[]
            if t.get('standard'): meta.append(esc(t['standard']))
            if t.get('gost'): meta.append(esc(t['gost']))
            if t.get('iso'): meta.append(esc(t['iso']))
            meta_html = ' · '.join(meta) if meta else '&nbsp;'
            cards.append(f'''
<a class="kb-card" href="../items/{esc(type_slug[t['id']])}.html">
  <div class="kb-card__img">{img_html}</div>
  <div class="kb-card__body">
    <h3 class="kb-card__title">{esc(t['name'])}</h3>
    <div class="kb-card__meta">{meta_html}</div>
  </div>
</a>''')
        body = f'''
<div class="kb-breadcrumbs"><a href="../index.html">База знаний</a> <span>/</span> <span>{esc(c['name'])}</span></div>
<section class="kb-hero"><h1>{esc(c['name'])}</h1><p>{len(items)} типов изделий в категории.</p></section>
<section class="kb-section"><div class="kb-grid">{''.join(cards) if cards else '<div class="kb-empty">В этой категории пока нет позиций.</div>'}</div></section>
'''
        (OUT/'categories'/f"{cat_slug[c['id']]}.html").write_text(page_shell(f"{c['name']} — База знаний", f"Категория {c['name']} в базе знаний крепежа.", '../', body, 'home'), encoding='utf-8')

    # item pages
    for t in types:
        c = next((x for x in categories if x['id']==t['category_id']), None)
        cname = c['name'] if c else t['category_id']
        cslug = cat_slug.get(t['category_id'],'')
        img = rel_img(t.get('image_path'), '../')
        img_html = f'<img src="{esc(img)}" alt="{esc(t["name"])}" loading="lazy" decoding="async">' if img else '<div style="color:#8aa095;font-weight:600;padding:40px">Нет фото</div>'
        props=[]
        for k,label in [('standard','Стандарт'),('gost','ГОСТ'),('iso','ISO'),('price_from_rub','Цена от')]:
            v=t.get(k)
            if k=='price_from_rub': v=fmt_price(v)
            if v: props.append(f'<div class="kb-prop"><div class="kb-prop__k">{label}</div><div class="kb-prop__v">{esc(v)}</div></div>')
        if t.get('size_range_text'): props.append(f'<div class="kb-prop"><div class="kb-prop__k">Размерный ряд</div><div class="kb-prop__v">{esc(t["size_range_text"])}</div></div>')
        props_html = '<div class="kb-props">' + ''.join(props) + '</div>' if props else ''
        desc = clean_desc(t.get('description'))
        desc_html = f'<div class="kb-desc">{esc(desc)}</div>' if desc else '<div class="kb-desc" style="color:#6b7785">Описание будет дополнено.</div>'

        pitems = prods_by_type.get(t['id'], [])
        table=''
        if pitems:
            rows=[]
            for p in pitems[:200]:
                rows.append(f"<tr><td>{esc(p.get('name') or '')}</td><td>{esc(p.get('size') or '')}</td><td>{esc(p.get('length_mm') or '')}</td><td>{esc(p.get('material') or '')}</td><td>{esc(p.get('coating') or '')}</td><td>{esc(fmt_price(p.get('price_rub')))}</td></tr>")
            table = f'''
<section class="kb-section">
  <h2>Варианты и размеры ({len(pitems)})</h2>
  <div class="kb-table-wrap"><table class="kb-table">
    <thead><tr><th>Наименование</th><th>Размер</th><th>Длина, мм</th><th>Материал</th><th>Покрытие</th><th>Цена</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table></div>
  {'<p style="color:#6b7785;font-size:13px;margin-top:10px">Показаны первые 200 вариантов.</p>' if len(pitems)>200 else ''}
</section>'''

        body = f'''
<div class="kb-breadcrumbs"><a href="../index.html">База знаний</a> <span>/</span> <a href="../categories/{esc(cslug)}.html">{esc(cname)}</a> <span>/</span> <span>{esc(t['name'])}</span></div>
<div class="kb-detail">
  <div class="kb-detail__img">{img_html}</div>
  <div class="kb-detail__body">
    <h1>{esc(t['name'])}</h1>
    {props_html}
    {desc_html}
  </div>
</div>
{table}
'''
        (OUT/'items'/f"{type_slug[t['id']]}.html").write_text(page_shell(f"{t['name']} — База знаний", clean_desc(t.get('description'))[:160], '../', body, 'home'), encoding='utf-8')

    # GOST/DIN/ISO page
    rows=[]
    for g in gosts:
        rows.append(f"<tr><td>{esc(g.get('din') or '')}</td><td>{esc(g.get('name') or '')}</td><td>{esc(g.get('gost') or '')}</td><td>{esc(g.get('iso') or '')}</td></tr>")
    gost_body = f'''
<div class="kb-breadcrumbs"><a href="index.html">База знаний</a> <span>/</span> <span>ГОСТ / DIN / ISO</span></div>
<section class="kb-hero"><h1>Соответствие ГОСТ / DIN / ISO</h1><p>Справочная таблица соответствий стандартов для крепежных изделий. {len(gosts)} записей.</p></section>
<div class="kb-search"><input id="gost-search" type="search" placeholder="Поиск: DIN, ГОСТ, ISO или название..." aria-label="Поиск по таблице соответствий"></div>
<div class="kb-table-wrap"><table class="kb-table" id="gost-table">
  <thead><tr><th>DIN</th><th>Наименование</th><th>ГОСТ</th><th>ISO</th></tr></thead>
  <tbody>{''.join(rows)}</tbody>
</table></div>
<script>
(()=>{{
  const q=document.getElementById('gost-search');
  const rows=[...document.querySelectorAll('#gost-table tbody tr')];
  const norm=s=>(s||'').toLowerCase().replace(/ё/g,'е');
  q.addEventListener('input',()=>{{ const v=norm(q.value.trim()); rows.forEach(r=>r.style.display=!v||norm(r.textContent).includes(v)?'':'none'); }});
}})();
</script>
'''
    (OUT/'gost-din-iso.html').write_text(page_shell('Соответствие ГОСТ / DIN / ISO — База знаний', 'Таблица соответствий стандартов ГОСТ, DIN, ISO для крепежа.', '', gost_body, 'gost'), encoding='utf-8')

    print(f'Generated knowledge base: {len(categories)} categories, {len(types)} types, {len(gosts)} gost rows')

if __name__ == '__main__':
    build()
