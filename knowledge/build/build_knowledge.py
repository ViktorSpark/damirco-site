#!/usr/bin/env python3
import sqlite3, re, html, shutil
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
    s = re.sub(r'^Главная\s*»\s*', '', s)
    s = re.sub(r'^([^»]{2,60}\s*»\s*){1,3}', '', s)  # strip remaining breadcrumbs
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def clean_size_range(s):
    s = (s or '').strip()
    if not s: return ''
    if not re.search(r'[0-9Øø]|\bот\b|\bдо\b|мм|[MМ]\s*\d', s, re.I): return ''
    if len(s) > 80: return ''
    return s

def img_name(image_path):
    if not image_path: return ''
    return Path(image_path).name

def rel_img(image_path, base_prefix):
    n = img_name(image_path)
    if not n: return ''
    return base_prefix + 'images/' + n

def page_shell(title, description, base, body, active=''):
    nav = f'''
<header class="wk-header">
  <div class="wk-header__inner">
    <a class="wk-brand" href="{base}index.html">
      <span class="wk-brand__logo"><img src="{base}assets/logo-damir.png" alt="Логотип ДАМИР ГРУПП"></span>
      <span class="wk-brand__text">
        <span class="wk-brand__title">База знаний</span>
        <span class="wk-brand__sub">Дамир Групп</span>
      </span>
    </a>
    <nav class="wk-nav" aria-label="Навигация базы знаний">
      <a href="{base}index.html" class="{'is-active' if active=='home' else ''}">Главная</a>
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
  <link rel="stylesheet" href="{base}assets/knowledge.css">
</head>
<body>
{nav}
<div class="wk-page">
  <main class="wk-main">
{body}
  </main>
</div>
<footer class="wk-footer">
  <div class="wk-footer__inner">
    <div>База знаний ДАМИР ГРУПП — справочные материалы о крепеже и стандартах.</div>
    <div><a href="../index.html">damirco.ru</a></div>
  </div>
</footer>
</body>
</html>'''

CSS = r'''
:root{
  --bg:#f6f6f6;--paper:#ffffff;--text:#202122;--muted:#54595d;--line:#a2a9b1;--line-soft:#c8ccd1;--line-bg:#eaecf0;
  --link:#0645ad;--link-visited:#0b0080;--head:#000;--max:1180px;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI','Liberation Sans',sans-serif}
a{color:var(--link);text-decoration:none}
a:hover{text-decoration:underline}
a:visited{color:var(--link-visited)}
img{max-width:100%;height:auto}
.wk-header{background:#fff;border-bottom:1px solid var(--line-soft)}
.wk-header__inner,.wk-footer__inner{max-width:var(--max);margin:0 auto;padding:0 16px}
.wk-header__inner{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:64px}
.wk-brand{display:flex;align-items:center;gap:12px;color:inherit;text-decoration:none}
.wk-brand:hover{text-decoration:none}
.wk-brand__logo{width:46px;height:46px;border-radius:50%;overflow:hidden;border:1px solid var(--line-soft);background:#fff;flex:0 0 46px}
.wk-brand__logo img{width:100%;height:100%;object-fit:cover;display:block}
.wk-brand__text{display:flex;flex-direction:column;line-height:1.2}
.wk-brand__title{font-family:'Linux Libertine','Georgia','Times',serif;font-size:28px;color:#000;letter-spacing:.01em}
.wk-brand__sub{font-size:12px;color:var(--muted)}
.wk-nav{display:flex;gap:4px;flex-wrap:wrap}
.wk-nav a{padding:8px 10px;color:#202122;border-radius:2px;font-size:14px}
.wk-nav a:hover{background:var(--line-bg);text-decoration:none;color:#202122}
.wk-nav a.is-active{background:var(--line-bg);box-shadow:inset 0 -2px 0 #36c;color:#202122}
.wk-page{max-width:var(--max);margin:0 auto;padding:16px}
.wk-main{background:var(--paper);border:1px solid var(--line-soft);padding:24px 28px 32px;min-height:70vh}
.wk-breadcrumbs{font-size:13px;color:var(--muted);margin-bottom:12px}
.wk-breadcrumbs a{color:var(--link)}
.wk-breadcrumbs span.sep{margin:0 4px;color:#72777d}
h1.wk-title{font-family:'Linux Libertine','Georgia','Times',serif;font-size:32px;line-height:1.3;font-weight:400;margin:0;padding-bottom:4px;border-bottom:1px solid var(--line);color:var(--head)}
.wk-lead{margin:14px 0 18px;font-size:14px;max-width:980px}
.wk-notice{background:#f8f9fa;border:1px solid var(--line-soft);padding:10px 12px;font-size:13px;color:#202122;margin:0 0 18px}
.wk-search{margin:0 0 20px}
.wk-search input{width:100%;max-width:520px;padding:8px 10px;border:1px solid var(--line);font:inherit;background:#fff}
.wk-search input:focus{outline:2px solid #36c;border-color:#36c}
.wk-cols{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:0 28px}
.wk-section{margin:24px 0 0}
.wk-section h2{font-family:'Linux Libertine','Georgia','Times',serif;font-size:24px;font-weight:400;line-height:1.3;margin:0 0 8px;padding-bottom:2px;border-bottom:1px solid var(--line);overflow:hidden}
.wk-cat-group{break-inside:avoid;margin:0 0 18px}
.wk-cat-group h3{font-family:'Linux Libertine','Georgia','Times',serif;font-size:20px;font-weight:400;margin:0 0 6px;padding-bottom:2px;border-bottom:1px solid var(--line-soft)}
.wk-cat-group h3 a{color:#202122}
.wk-cat-group h3 a:hover{color:var(--link)}
.wk-list{margin:0;padding-left:20px}
.wk-list li{margin:2px 0}
.wk-muted{color:var(--muted);font-size:13px}
.wk-article{overflow:hidden}
.wk-infobox{float:right;clear:right;width:290px;margin:4px 0 16px 20px;background:#f8f9fa;border:1px solid var(--line-soft);font-size:13px;line-height:1.5}
.wk-infobox__title{padding:8px 10px;text-align:center;font-weight:700;background:#eaecf0;border-bottom:1px solid var(--line-soft)}
.wk-infobox__img{padding:10px;background:#fff;border-bottom:1px solid var(--line-soft);text-align:center}
.wk-infobox__img img{max-height:220px;object-fit:contain}
.wk-infobox table{width:100%;border-collapse:collapse}
.wk-infobox th,.wk-infobox td{padding:6px 8px;vertical-align:top;border-top:1px solid #eaecf0;text-align:left}
.wk-infobox th{width:42%;color:#202122;font-weight:600;background:#f8f9fa}
.wk-article p{margin:0 0 12px}
.wk-article .wk-lead{margin-top:14px}
.wk-table-wrap{overflow:auto;margin:12px 0}
table.wikitable{border-collapse:collapse;background:#f8f9fa;border:1px solid var(--line-soft);font-size:13px;width:100%}
table.wikitable th,table.wikitable td{border:1px solid var(--line-soft);padding:6px 8px;vertical-align:top;text-align:left}
table.wikitable th{background:#eaecf0;font-weight:600;text-align:center}
table.wikitable tr:hover td{background:#eef3f8}
.wk-empty{color:var(--muted);font-style:italic}
.wk-footer{padding:14px 0 24px;font-size:12px;color:var(--muted)}
.wk-footer__inner{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
.wk-footer a{color:var(--link)}
@media (max-width:980px){.wk-cols{grid-template-columns:repeat(2,minmax(0,1fr))}.wk-infobox{width:260px}}
@media (max-width:720px){
  .wk-header__inner{flex-direction:column;align-items:flex-start;padding:10px 16px}
  .wk-main{padding:18px 16px 24px}
  .wk-cols{grid-template-columns:1fr}
  .wk-infobox{float:none;width:auto;margin:14px 0}
  h1.wk-title{font-size:28px}
}
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

    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS/'knowledge.css').write_text(CSS, encoding='utf-8')

    # ensure logo exists in assets (user-provided copy may already be there)
    logo_src = ROOT / 'catalog_data' / 'logo_damir.png'
    logo_dst = ASSETS / 'logo-damir.png'
    if logo_src.exists() and not logo_dst.exists():
        shutil.copy2(logo_src, logo_dst)

    IMG_DST.mkdir(parents=True, exist_ok=True)
    if IMG_SRC.exists():
        for f in IMG_SRC.iterdir():
            if f.is_file():
                dst = IMG_DST / f.name
                if not dst.exists():
                    shutil.copy2(f, dst)

    # index
    cat_groups = []
    for c in categories:
        items = types_by_cat.get(c['id'], [])
        lis = []
        for t in items:
            lis.append(f'<li><a href="items/{esc(type_slug[t["id"]])}.html">{esc(t["name"])}</a></li>')
        cat_groups.append(f'''
<div class="wk-cat-group" data-search="{esc((c['name'] or '').lower())}">
  <h3><a href="categories/{esc(cat_slug[c['id']])}.html">{esc(c['name'])}</a> <span class="wk-muted">({len(items)})</span></h3>
  <ul class="wk-list">{''.join(lis) if lis else '<li class="wk-empty">Нет статей</li>'}</ul>
</div>''')

    index_body = f'''
<h1 class="wk-title">База знаний крепежа</h1>
<div class="wk-lead">
  <p>Справочная энциклопедия по видам крепежа, стандартам и соответствиям ГОСТ / DIN / ISO. Материалы собраны в виде статических статей — без цен, артикулов и коммерческих данных, чтобы быстро ориентироваться в типах изделий и нормативных обозначениях.</p>
</div>
<div class="wk-notice">В базе знаний: <strong>{len(categories)}</strong> категорий, <strong>{len(types)}</strong> статей о типах изделий, <strong>{len(gosts)}</strong> записей соответствий ГОСТ / DIN / ISO.</div>
<div class="wk-search"><input id="wk-search" type="search" placeholder="Найти статью или стандарт..." aria-label="Поиск по базе знаний"></div>
<section class="wk-section" id="wk-cats-section">
  <h2>Категории и статьи</h2>
  <div class="wk-cols" id="wk-cats">{''.join(cat_groups)}</div>
</section>
<section class="wk-section" id="wk-results-section" style="display:none">
  <h2>Результаты поиска</h2>
  <ul class="wk-list" id="wk-results"></ul>
  <div id="wk-empty" class="wk-empty" style="display:none">Ничего не найдено.</div>
</section>
<script>
(()=>{{
  const q=document.getElementById('wk-search');
  const cats=[...document.querySelectorAll('.wk-cat-group')];
  const sec=document.getElementById('wk-results-section');
  const res=document.getElementById('wk-results');
  const empty=document.getElementById('wk-empty');
  const norm=s=>(s||'').toLowerCase().replace(/ё/g,'е').trim();
  const items=[...document.querySelectorAll('.wk-cat-group li a')].map(a=>({{t:a.textContent,href:a.getAttribute('href'),n:norm(a.textContent)}}));
  q.addEventListener('input',()=>{{
    const v=norm(q.value);
    if(!v){{cats.forEach(c=>c.style.display=''); sec.style.display='none'; res.innerHTML=''; empty.style.display='none'; return;}}
    cats.forEach(c=>{{c.style.display=norm(c.dataset.search).includes(v)?'':'none';}});
    const m=items.filter(i=>i.n.includes(v)).slice(0,80);
    res.innerHTML=m.map(i=>`<li><a href="${{i.href}}">${{i.t}}</a></li>`).join('');
    sec.style.display='';
    empty.style.display=m.length?'none':'';
  }});
}})();
</script>
'''
    (OUT/'index.html').write_text(page_shell('База знаний крепежа — ДАМИР ГРУПП', 'Справочная энциклопедия по видам крепежа, стандартам ГОСТ, DIN, ISO.', '', index_body, 'home'), encoding='utf-8')

    # category pages
    for c in categories:
        items = types_by_cat.get(c['id'], [])
        lis=[]
        for t in items:
            meta=[]
            if t.get('standard'): meta.append(esc(t['standard']))
            if t.get('gost'): meta.append(esc(t['gost']))
            if t.get('iso'): meta.append(esc(t['iso']))
            meta_s = f' <span class="wk-muted">— {" · ".join(meta)}</span>' if meta else ''
            lis.append(f'<li><a href="../items/{esc(type_slug[t["id"]])}.html">{esc(t["name"])}</a>{meta_s}</li>')
        body = f'''
<div class="wk-breadcrumbs"><a href="../index.html">База знаний</a><span class="sep">›</span><span>{esc(c['name'])}</span></div>
<h1 class="wk-title">{esc(c['name'])}</h1>
<div class="wk-lead"><p>Категория справочной базы знаний. В разделе собрано {len(items)} статей о типах изделий, стандартах и применении.</p></div>
<section class="wk-section">
  <h2>Статьи в категории</h2>
  {'<ul class="wk-list">' + ''.join(lis) + '</ul>' if lis else '<div class="wk-empty">В этой категории пока нет статей.</div>'}
</section>
'''
        (OUT/'categories'/f"{cat_slug[c['id']]}.html").write_text(page_shell(f"{c['name']} — База знаний", f"Статьи категории {c['name']} в базе знаний.", '../', body, 'home'), encoding='utf-8')

    # item pages
    for t in types:
        c = next((x for x in categories if x['id']==t['category_id']), None)
        cname = c['name'] if c else t['category_id']
        cslug = cat_slug.get(t['category_id'],'')
        img = rel_img(t.get('image_path'), '../')
        img_html = f'<div class="wk-infobox__img"><img src="{esc(img)}" alt="{esc(t["name"])}" loading="lazy" decoding="async"></div>' if img else ''
        info_rows=[]
        for k,label in [('standard','Стандарт'),('gost','ГОСТ'),('iso','ISO'),('size_range_text','Размерный ряд')]:
            v=t.get(k)
            if k == 'size_range_text':
                v = clean_size_range(v)
            if v: info_rows.append(f'<tr><th>{label}</th><td>{esc(v)}</td></tr>')
        info_rows.append(f'<tr><th>Категория</th><td><a href="../categories/{esc(cslug)}.html">{esc(cname)}</a></td></tr>')
        infobox = f'''
<aside class="wk-infobox">
  <div class="wk-infobox__title">{esc(t['name'])}</div>
  {img_html}
  <table><tbody>{''.join(info_rows)}</tbody></table>
</aside>'''

        desc = clean_desc(t.get('description'))
        if desc:
            # split into paragraphs by sentence-ish chunks for readability
            paras = [p.strip() for p in re.split(r'\n+|(?<=\.)\s{2,}', desc) if p.strip()]
            if not paras: paras = [desc]
            desc_html = ''.join(f'<p>{esc(p)}</p>' for p in paras)
        else:
            desc_html = '<p class="wk-empty">Описание будет дополнено.</p>'

        pitems = prods_by_type.get(t['id'], [])
        table=''
        if pitems:
            rows=[]
            for p in pitems[:200]:
                rows.append(f"<tr><td>{esc(p.get('name') or '')}</td><td>{esc(p.get('size') or '')}</td><td>{esc(p.get('length_mm') or '')}</td><td>{esc(p.get('material') or '')}</td><td>{esc(p.get('coating') or '')}</td></tr>")
            more = f'<p class="wk-muted">Показаны первые 200 вариантов из {len(pitems)}.</p>' if len(pitems)>200 else ''
            table = f'''
<section class="wk-section">
  <h2>Размеры и варианты</h2>
  <div class="wk-table-wrap"><table class="wikitable">
    <thead><tr><th>Наименование</th><th>Размер</th><th>Длина, мм</th><th>Материал</th><th>Покрытие</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table></div>
  {more}
</section>'''

        body = f'''
<div class="wk-breadcrumbs"><a href="../index.html">База знаний</a><span class="sep">›</span><a href="../categories/{esc(cslug)}.html">{esc(cname)}</a><span class="sep">›</span><span>{esc(t['name'])}</span></div>
<h1 class="wk-title">{esc(t['name'])}</h1>
<div class="wk-article">
  {infobox}
  <div class="wk-lead">{desc_html}</div>
</div>
{table}
'''
        (OUT/'items'/f"{type_slug[t['id']]}.html").write_text(page_shell(f"{t['name']} — База знаний", clean_desc(t.get('description'))[:160], '../', body, 'home'), encoding='utf-8')

    # GOST/DIN/ISO page
    rows=[]
    for g in gosts:
        rows.append(f"<tr><td>{esc(g.get('din') or '')}</td><td>{esc(g.get('name') or '')}</td><td>{esc(g.get('gost') or '')}</td><td>{esc(g.get('iso') or '')}</td></tr>")
    gost_body = f'''
<div class="wk-breadcrumbs"><a href="index.html">База знаний</a><span class="sep">›</span><span>ГОСТ / DIN / ISO</span></div>
<h1 class="wk-title">Соответствие ГОСТ / DIN / ISO</h1>
<div class="wk-lead"><p>Справочная таблица соответствий стандартов для крепёжных изделий. Используйте поиск для фильтрации по обозначению стандарта или названию.</p></div>
<div class="wk-notice">Всего записей: <strong>{len(gosts)}</strong>.</div>
<div class="wk-search"><input id="gost-search" type="search" placeholder="Поиск: DIN, ГОСТ, ISO или название..." aria-label="Поиск по таблице соответствий"></div>
<div class="wk-table-wrap"><table class="wikitable" id="gost-table">
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
