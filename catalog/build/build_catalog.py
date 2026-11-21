#!/usr/bin/env python3
import csv, json, re, os, html, math, unicodedata
from pathlib import Path
from collections import defaultdict, OrderedDict

ROOT = Path(__file__).resolve().parents[3]  # damirco/
SITE = ROOT / 'site'
OUT = SITE / 'catalog'
DATA_OUT = OUT / 'data'
SITE_REPO_PREFIX = '/damirco-site/'  # GitHub Pages repo path prefix in published URLs

csv.field_size_limit(10**7)

def norm_text(s):
    s = (s or '').lower().replace('ё', 'е')
    s = re.sub(r'[^a-zа-я0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def clean_html(s):
    s = (s or '').strip()
    if not s:
        return ''
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.I)
    s = re.sub(r'</(p|div|li|h[1-6]|tr)>', '\n', s, flags=re.I)
    s = re.sub(r'<li[^>]*>', '- ', s, flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = html.unescape(s)
    s = s.replace('\xa0', ' ')
    s = re.sub(r'[ \t]+\n', '\n', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    s = re.sub(r'[ \t]{2,}', ' ', s)
    return s.strip()

def slugify(s, maxlen=80):
    s = (s or '').strip().lower().replace('ё', 'е')
    tr = {
        'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ж':'zh','з':'z','и':'i','й':'y',
        'к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u',
        'ф':'f','х':'h','ц':'ts','ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya'
    }
    out=[]
    for ch in s:
        if ch in tr: out.append(tr[ch])
        elif ch.isalnum(): out.append(ch)
        elif ch in ' -_/.,()': out.append('-')
    slug = re.sub(r'-+','-', ''.join(out)).strip('-')
    if not slug: slug = 'item'
    return slug[:maxlen].strip('-') or 'item'

def split_size_values(raw):
    # split on comma+space but keep decimal commas inside numbers like 4,0х110
    parts = [p.strip() for p in re.split(r',\s*', raw.strip()) if p.strip()]
    merged=[]
    i=0
    while i < len(parts):
        cur = parts[i]
        if i+1 < len(parts):
            nxt = parts[i+1]
            # decimal comma split: '4' + '0х110' or '5' + '5х160'
            if re.fullmatch(r'\d+', cur) and re.match(r'^\d+[xх×X]', nxt):
                merged.append(cur + ',' + nxt)
                i += 2
                continue
        merged.append(cur)
        i += 1
    return merged

def extract_specs(desc, text):
    blob = ((desc or '') + '\n' + (text or '')).strip()
    specs=[]
    for m in re.finditer(r'([^\n:]{2,40})\s*:\s*([^\n]+)', blob):
        label = m.group(1).strip()
        if not re.search(r'(размер|диаметр|длина|толщина|вес|материал|покрытие|бренд|тип|класс|кол-во|количество|объем|объём|цвет|назначение|основание|упаков)', label, re.I):
            continue
        raw = m.group(2).strip()
        values = split_size_values(raw)
        specs.append({'label': label, 'raw': raw, 'values': values})
    uniq=[]; seen=set()
    for s in specs:
        k=(s['label'].lower(), s['raw'])
        if k in seen: continue
        seen.add(k); uniq.append(s)
    return uniq, blob

def parse_brand(title, desc, category):
    blob = ' '.join([title or '', desc or '', category or ''])
    brands = ['HILTI','Hilti','MKT','Fasty','FASTY','Graf','GRAF','Sormat','SORMAT','Himtex','HIMTEX','Fixol','FIXOL','Daxmer','DAXMER','Tech-Krep','Tech Krep','Тех-Креп','Koelner','Rawlplug','RAWLPLUG','Fischer','FISCHER','Soudal','SOUDAL','Elematic','INDEX','Index','BIT','Bit','VME','VESF','VE','HSA','HST','HUS','HAS','HIT','HVU','HSC','HSL','RE','HY']
    for b in brands:
        if re.search(r'\b'+re.escape(b)+r'\b', blob, re.I):
            return b if b.isupper() or len(b)<=4 else b
    m = re.search(r'бренд\s+([A-Za-zА-Яа-я0-9\-]+)', blob, re.I)
    if m: return m.group(1)
    return ''

def load_json(p):
    try:
        with open(p, encoding='utf-8') as f: return json.load(f)
    except Exception:
        return None

def localize_photo_url(url):
    """Convert known hosted photo URLs to site-root-relative local paths when file exists in site/."""
    url = (url or '').strip()
    if not url:
        return ''
    if not re.match(r'^https?://', url, re.I):
        # already local/relative - normalize separators
        return url.lstrip('./')
    try:
        from urllib.parse import urlparse, unquote
        parsed = urlparse(url)
        path = unquote(parsed.path or '')
    except Exception:
        return url
    # map /damirco-site/<...> -> site/<...>
    rel = None
    if path.startswith(SITE_REPO_PREFIX):
        rel = path[len(SITE_REPO_PREFIX):].lstrip('/')
    else:
        # try to detect known photo dirs by basename if hosted elsewhere under same repo naming? unlikely
        rel = None
    if rel:
        local_path = SITE / rel
        if local_path.exists():
            return rel
        # fallback: if same basename exists in known dirs
        name = os.path.basename(rel)
        for d in ['catalog-photos', 'catalog-photos-texnoroom', 'catalog-photos-original-backup', 'yml-photos']:
            cand = SITE / d / name
            if cand.exists():
                return f'{d}/{name}'
    return url

def main():
    DATA_OUT.mkdir(parents=True, exist_ok=True)

    with open(ROOT/'catalog_data'/'tilda_импорт_2075_финал.csv', encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f, delimiter=';'))

    # optional supplemental Tilda CSVs (e.g. separately uploaded category exports)
    extra_files = [
        ROOT/'catalog_data'/'tilda_tarelchatye_daxmer_local.csv',
        ROOT/'catalog_data'/'tilda_tarelchatye_daxmer.csv',
    ]
    seen_extra = set()
    existing_ids = set()
    for r in rows:
        for k in ('External ID', 'SKU'):
            v = str(r.get(k) or '').strip()
            if v:
                existing_ids.add(v)
    for ep in extra_files:
        if not ep.exists():
            continue
        rp = str(ep.resolve())
        if rp in seen_extra:
            continue
        seen_extra.add(rp)
        # prefer *_local.csv over original
        if ep.name.endswith('_local.csv'):
            orig = ep.with_name(ep.name.replace('_local.csv', '.csv'))
            if orig.exists():
                seen_extra.add(str(orig.resolve()))
        if ep.name == 'tilda_tarelchatye_daxmer.csv' and (ROOT/'catalog_data'/'tilda_tarelchatye_daxmer_local.csv').exists():
            continue
        with open(ep, encoding='utf-8-sig', newline='') as f:
            extra_rows = list(csv.DictReader(f, delimiter=';'))
        for r in extra_rows:
            ids = [str(r.get(k) or '').strip() for k in ('External ID', 'SKU')]
            ids = [v for v in ids if v]
            if any(v in existing_ids for v in ids):
                continue
            rows.append(r)
            for v in ids:
                existing_ids.add(v)

    inv = load_json(ROOT/'scraper'/'inventory.json') or []
    raw = load_json(ROOT/'catalog_data'/'products_raw.json') or []
    live = load_json(ROOT/'feed'/'live_cache.json') or []

    def index_by(items, keys):
        idx = {}
        for it in items:
            if not isinstance(it, dict): continue
            for k in keys:
                v = str(it.get(k,'') or '').strip()
                if v and v not in idx:
                    idx[v]=it
        return idx

    inv_by_uid = index_by(inv, ['uid'])
    inv_by_ext = index_by(inv, ['externalid'])
    raw_by_uid = index_by(raw, ['uid'])
    raw_by_ext = index_by(raw, ['externalid'])
    live_by_uid = index_by(live, ['uid'])
    live_by_ext = index_by(live, ['externalid'])

    inv_by_norm = {norm_text(x.get('title','')):x for x in inv if norm_text(x.get('title',''))}
    raw_by_norm = {norm_text(x.get('title','')):x for x in raw if norm_text(x.get('title',''))}

    cat_counts = OrderedDict()
    for r in rows:
        c = (r.get('Category') or '').strip() or 'Без категории'
        cat_counts[c] = cat_counts.get(c,0)+1
    categories=[]
    for i,(name,count) in enumerate(cat_counts.items(),1):
        categories.append({'id': i, 'name': name, 'slug': slugify(name), 'count': count})

    cat_slug = {c['name']: c['slug'] for c in categories}

    products=[]
    used_slugs = defaultdict(int)
    for idx,r in enumerate(rows,1):
        sku = (r.get('SKU') or '').strip()
        ext = (r.get('External ID') or '').strip()
        title = (r.get('Title') or '').strip()
        category = (r.get('Category') or '').strip() or 'Без категории'
        desc = clean_html((r.get('Description') or '').strip())
        text = clean_html((r.get('Text') or '').strip())
        photo = (r.get('Photo') or '').strip()
        price = (r.get('Price') or '').strip()
        price_old = (r.get('Price Old') or '').strip()
        qty = (r.get('Quantity') or '').strip()

        specs, fulltext = extract_specs(desc, text)
        brand = parse_brand(title, desc, category)

        enrich = None
        for key in [ext, sku]:
            if not key: continue
            enrich = enrich or inv_by_uid.get(key) or inv_by_ext.get(key) or raw_by_uid.get(key) or raw_by_ext.get(key) or live_by_uid.get(key) or live_by_ext.get(key)
        if not enrich:
            nt = norm_text(title)
            enrich = inv_by_norm.get(nt) or raw_by_norm.get(nt)

        variants = []
        json_options = ''
        editions = []
        live_url = ''
        gallery = []
        characteristics = []
        if enrich:
            json_options = enrich.get('json_options') or ''
            editions = enrich.get('editions') or []
            live_url = enrich.get('url') or ''
            gallery = enrich.get('gallery') or []
            characteristics = enrich.get('characteristics') or enrich.get('Characteristics') or []
            if not photo:
                g = gallery[0] if isinstance(gallery,list) and gallery else None
                if isinstance(g, dict): photo = g.get('img') or g.get('url') or ''
                elif isinstance(g, str): photo = g
                if not photo and isinstance(editions,list) and editions:
                    photo = (editions[0] or {}).get('img') or ''

        if isinstance(editions, list) and editions:
            for e in editions:
                if not isinstance(e, dict): continue
                v = {
                    'sku': e.get('sku') or e.get('externalid') or '',
                    'price': e.get('price') or '',
                    'priceold': e.get('priceold') or '',
                    'quantity': e.get('quantity') or '',
                    'img': e.get('img') or '',
                }
                meta={'uid','externalid','sku','price','priceold','quantity','img','editions','gallery'}
                opts={k:val for k,val in e.items() if k not in meta and val not in ('',None,[])}
                if opts: v['options']=opts
                if v.get('price') or v.get('sku') or opts:
                    variants.append(v)

        if not variants:
            for sp in specs:
                vals=[v for v in sp['values'] if v and not re.match(r'^\(и ещё', v, re.I)]
                if len(vals) > 1 and re.search(r'размер|диаметр|длина|толщина', sp['label'], re.I):
                    for val in vals:
                        variants.append({'label': val, 'options': {sp['label']: val}})
                    break

        photo = localize_photo_url(photo)

        base_slug = slugify(title) or slugify(sku) or f'item-{idx}'
        used_slugs[base_slug]+=1
        pslug = base_slug if used_slugs[base_slug]==1 else f"{base_slug}-{used_slugs[base_slug]}"

        products.append({
            'id': idx,
            'sku': sku,
            'external_id': ext,
            'title': title,
            'category': category,
            'category_slug': cat_slug.get(category, slugify(category)),
            'brand': brand,
            'description': desc,
            'text': text,
            'photo': photo,
            'price': price,
            'price_old': price_old,
            'quantity': qty,
            'specs': specs,
            'variants': variants,
            'has_variants': len(variants)>1 or (len(variants)==1 and bool(variants[0].get('options'))),
            'url': live_url,
            'slug': pslug,
        })

    catalog = {
        'meta': {
            'total': len(products),
            'categories': categories,
            'source': 'tilda_импорт_2075_финал.csv + enrichments',
        },
        'categories': categories,
        'products': products,
    }

    with open(DATA_OUT/'catalog.json','w',encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False)

    search=[]
    for p in products:
        search.append({
            'i': p['id'], 't': p['title'], 'c': p['category'], 'cs': p['category_slug'],
            'b': p['brand'], 'p': p['price'], 's': p['slug'], 'ph': (p['photo'] or '')[:140],
        })
    with open(DATA_OUT/'search.json','w',encoding='utf-8') as f:
        json.dump(search, f, ensure_ascii=False)

    popular=[]
    for c in categories:
        items=[p for p in products if p['category']==c['name'] and p.get('photo') and p.get('price')]
        if not items:
            items=[p for p in products if p['category']==c['name']]
        popular.extend(items[:2])
    popular = popular[:24]
    with open(DATA_OUT/'popular.json','w',encoding='utf-8') as f:
        json.dump([{'i':p['id'],'t':p['title'],'c':p['category'],'cs':p['category_slug'],'b':p['brand'],'p':p['price'],'s':p['slug'],'ph':p['photo']} for p in popular], f, ensure_ascii=False)

    print('products', len(products), 'categories', len(categories))
    print('written', DATA_OUT)

if __name__ == '__main__':
    main()
