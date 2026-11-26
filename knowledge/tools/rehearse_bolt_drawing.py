#!/usr/bin/env python3
import json, math, os, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'knowledge' / 'tools' / 'drawing-rehearsal'
OUT.mkdir(parents=True, exist_ok=True)

ITEMS = [
    ('flange','art-10105-bolt-s-flantsem'),
    ('tbolt','art-88928-bolt-s-t-obraznoy-golovkoy-dlya-profilya'),
    ('hex','art-88933-bolt-so-stopornym-burtom'),
    ('elevator','din-15237-bolt-noriynyy'),
    ('swing','din-444-bolt-otkidnoy'),
    ('anchor','din-529-bolty-ankernye'),
    ('eye','din-580-rym-bolt'),
    ('carriage','din-603-bolt-mebelnyy-s-polukrugloy-golovkoy'),
    ('countersunk','din-604-bolt-s-potaynoy-golovkoy-i-usom'),
    ('fitting','din-609-bolt-prizonnyy'),
    ('flange','art-88912-bolt-s-flantsem-s-nasechkami'),
    ('tbolt','art-88940-bolt-halfen-dlya-profilya'),
    ('hex','din-22424-bolt-s-trehgrannoy-golovkoy-i-burtikom'),
    ('swing','gost-3033-79-bolty-otkidnye'),
    ('anchor','gost-24379-1-2012-bolty-fundamentnye'),
    ('carriage','din-607-bolt-mebelnyy-s-usom'),
    ('countersunk','din-605-bolt-s-potaynoy-golovkoy-i-kvadratnym-podgolovkom'),
    ('fitting','din-610-bolt-prizonnyy'),
    ('flange','art-88913-bolt-shestigrannyy-s-flantsem'),
    ('tbolt','art-88950-bolt-halfen-dlya-profilya'),
]

def get_image_path(slug):
    html=(ROOT/'knowledge/items'/f'{slug}.html').read_text(encoding='utf-8',errors='ignore')
    m=re.search(r'<div class="wk-infobox__img"><img src="([^"]+)"', html)
    if not m: return None
    src=m.group(1)
    if src.startswith('../'):
        return (ROOT/'knowledge/items'/src).resolve()
    return (ROOT/'knowledge'/src).resolve()

def load_mask(img):
    g = img.convert('L')
    a = np.array(g, dtype=np.float32)
    # also use alpha if present
    if img.mode in ('RGBA','LA'):
        alpha = np.array(img.split()[-1], dtype=np.float32)
        bg = alpha > 10
    else:
        bg = np.zeros_like(a, dtype=bool)
    # threshold: object darker than background or non-white
    # adaptive: Otsu-like simple
    thr = np.percentile(a, 60)
    thr = min(max(thr, 80), 245)
    mask = (a < thr) | bg
    # remove border artifacts
    mask[:2,:]=False; mask[-2:,:]=False; mask[:,:2]=False; mask[:,-2:]=False
    return mask

def largest_component(mask):
    # simple BFS/labeling via numpy - avoid scipy; implement small component labeling
    h,w = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    best = None; best_n=0
    ys,xs = np.where(mask)
    # if too many pixels, sample by scanning; use connected components by iterative grow on bounding regions
    # fallback: use all mask pixels as one component for simplicity
    if len(ys)==0: return mask
    return mask

def pca_angle(mask):
    ys,xs = np.where(mask)
    if len(xs) < 50: return 0.0
    x = xs.astype(np.float64); y = ys.astype(np.float64)
    x -= x.mean(); y -= y.mean()
    cov = np.cov(np.stack([x,y]))
    vals, vecs = np.linalg.eigh(cov)
    v = vecs[:, np.argmax(vals)]
    angle = math.degrees(math.atan2(v[1], v[0]))
    # normalize to [-90,90]
    if angle > 90: angle -= 180
    if angle < -90: angle += 180
    return angle

def rotate_image(img, angle):
    # rotate around center, expand
    return img.rotate(angle, expand=True, resample=Image.BICUBIC, fillcolor=(255,255,255))

def crop_to_mask(img, mask, pad=10):
    ys,xs = np.where(mask)
    if len(xs)==0: return img, mask
    x0=max(0,xs.min()-pad); x1=min(mask.shape[1],xs.max()+pad+1)
    y0=max(0,ys.min()-pad); y1=min(mask.shape[0],ys.max()+pad+1)
    return img.crop((x0,y0,x1,y1)), mask[y0:y1,x0:x1]

def ensure_head_left(img, mask):
    h,w = mask.shape
    # split into left and right thirds of bbox width
    ys,xs = np.where(mask)
    if len(xs)==0: return img, mask
    x0,x1 = xs.min(), xs.max()
    mid = (x0+x1)/2
    left = mask[:, :int(mid)]
    right = mask[:, int(mid):]
    # width profile: count pixels per column
    col = mask.sum(axis=0).astype(np.float32)
    # consider object bbox only
    col = col[x0:x1+1]
    if len(col)<10: return img, mask
    n=len(col)
    left_w = col[:max(1,n//3)].mean()
    right_w = col[-max(1,n//3):].mean()
    if right_w > left_w * 1.15:
        img = ImageOps.mirror(img)
        mask = mask[:, ::-1].copy()
    return img, mask

def width_profile(mask):
    ys,xs = np.where(mask)
    if len(xs)==0: return None
    x0,x1=xs.min(), xs.max()
    prof=[]
    for x in range(x0,x1+1):
        col = np.where(mask[:,x])[0]
        if len(col)==0: prof.append(0)
        else: prof.append(int(col.max()-col.min()+1))
    return x0,x1,np.array(prof,dtype=np.float32)

def segment_elements(mask, family):
    wp = width_profile(mask)
    if wp is None: return []
    x0,x1,prof = wp
    n=len(prof)
    if n<20: return []
    # smooth
    k=min(15, max(3, n//20*2+1))
    kernel = np.ones(k)/k
    sm = np.convolve(prof, kernel, mode='same')
    maxw = sm.max() if sm.max()>0 else 1
    # head: from left where width > 0.65*maxw
    head_end = 0
    for i in range(n):
        if sm[i] > 0.65*maxw: head_end=i
        if i>n*0.45: break
    # refine head end: first significant drop after peak in first 40%
    left_region = sm[:max(5,int(n*0.45))]
    peak_i = int(np.argmax(left_region))
    head_end = peak_i
    for i in range(peak_i, len(left_region)):
        if sm[i] < left_region[peak_i]*0.75:
            head_end = i
            break
    head_end = max(head_end, int(n*0.08))
    head_end = min(head_end, int(n*0.35))

    # chamfer: right end taper
    chamfer_start = n-1
    for i in range(n-1, int(n*0.6), -1):
        if sm[i] < 0.5*maxw:
            chamfer_start = i
        else:
            break
    chamfer_start = max(chamfer_start, int(n*0.85))

    # underhead: small region after head
    underhead_end = min(head_end + max(3,int(n*0.06)), chamfer_start-2)

    # thread vs smooth: heuristic - threaded part usually right 45-70% or rougher; use family
    if family in ('hex','flange','carriage','fitting','swing'):
        # often partial thread
        thread_start = int(n*0.55)
    elif family in ('countersunk','elevator'):
        thread_start = int(n*0.45)
    elif family in ('tbolt','anchor'):
        thread_start = int(n*0.35)
    else:
        thread_start = int(n*0.5)
    thread_start = max(thread_start, underhead_end+2)
    thread_start = min(thread_start, chamfer_start-2)

    # build segments within bbox y
    ys,xs = np.where(mask)
    y0,y1 = int(ys.min()), int(ys.max())
    def seg(name, a,b, color):
        a=max(0,min(n-1,a)); b=max(0,min(n,b))
        if b<=a: b=a+1
        xa=int(x0+a); xb=int(x0+b)
        return {'name':name,'box':[xa,y0,xb,y1+1],'color':color}
    segs = []
    segs.append(seg('Головка', 0, head_end, '#e53935'))
    if underhead_end > head_end+1:
        segs.append(seg('Подголовник', head_end, underhead_end, '#fb8c00'))
    if thread_start > underhead_end+2:
        segs.append(seg('Гладкая часть', underhead_end, thread_start, '#43a047'))
    if chamfer_start > thread_start+1:
        segs.append(seg('Резьбовая часть', thread_start, chamfer_start, '#1e88e5'))
    if n > chamfer_start+1:
        segs.append(seg('Фаска (сбег)', chamfer_start, n, '#8e24aa'))
    return segs

def annotate(img, mask, segs, title):
    # draw on RGBA overlay
    base = img.convert('RGBA')
    draw = ImageDraw.Draw(base)
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 16)
        font_s = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 13)
    except Exception:
        font = font_s = ImageFont.load_default()
    # dim background slightly
    overlay = Image.new('RGBA', base.size, (255,255,255,0))
    od = ImageDraw.Draw(overlay)
    for s in segs:
        x0,y0,x1,y1=s['box']
        color=s['color']
        # rectangle
        od.rectangle([x0,y0,x1,y1], outline=color, width=3)
        # label background
        label=s['name']
        bbox = od.textbbox((0,0), label, font=font_s)
        tw,th=bbox[2]-bbox[0], bbox[3]-bbox[1]
        lx=x0+2; ly=max(0,y0-th-6)
        od.rectangle([lx-2,ly-2,lx+tw+4,ly+th+2], fill=color)
        od.text((lx,ly), label, fill='white', font=font_s)
    base = Image.alpha_composite(base, overlay)
    # title bar
    draw = ImageDraw.Draw(base)
    draw.rectangle([0,0,base.size[0],28], fill=(40,40,40,220))
    draw.text((8,5), title[:120], fill='white', font=font_s)
    return base.convert('RGB')

def process_one(family, slug):
    src = get_image_path(slug)
    if not src or not Path(src).exists():
        return {'slug':slug,'error':'no image'}
    img = Image.open(src).convert('RGB')
    orig_size = img.size
    # stage 1
    mask = load_mask(img)
    angle = pca_angle(mask)
    # rotate to horizontal
    rotated = rotate_image(img, angle)
    mask_r = load_mask(rotated)
    rotated, mask_r = crop_to_mask(rotated, mask_r, pad=12)
    rotated, mask_r = ensure_head_left(rotated, mask_r)
    # stage 2
    segs = segment_elements(mask_r, family)
    title = f'{slug} [{family}] angle={angle:.1f}°'
    ann = annotate(rotated, mask_r, segs, title)
    out_name = f'{slug}.png'
    ann.save(OUT/out_name, 'PNG')
    # also save a panel: original | annotated
    orig = Image.open(src).convert('RGB')
    # resize to same height
    h = 360
    def rh(im):
        w=int(im.size[0]*h/im.size[1])
        return im.resize((max(1,w),h), Image.LANCZOS)
    o2=rh(orig); a2=rh(ann)
    panel = Image.new('RGB', (o2.size[0]+a2.size[0]+10, h+30), 'white')
    panel.paste(o2,(0,30))
    panel.paste(a2,(o2.size[0]+10,30))
    pd = ImageDraw.Draw(panel)
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 14)
    except Exception:
        font = ImageFont.load_default()
    pd.text((5,6), 'Исходник', fill='#333', font=font)
    pd.text((o2.size[0]+15,6), 'Этап 1+2: ориентация + элементы', fill='#333', font=font)
    panel_name = f'{slug}_panel.png'
    panel.save(OUT/panel_name, 'PNG')
    return {'slug':slug,'family':family,'angle':angle,'segs':[s['name'] for s in segs],'file':out_name,'panel':panel_name,'orig':str(src)}

def main():
    results=[]
    for fam,slug in ITEMS:
        try:
            r=process_one(fam,slug)
            results.append(r)
            print('ok', slug, r.get('segs'))
        except Exception as e:
            print('err', slug, e)
            results.append({'slug':slug,'error':str(e)})
    # html report
    rows=[]
    for r in results:
        if 'panel' in r:
            rows.append(f'''<div class="card"><h3>{r['slug']} <small>[{r['family']}] угол {r['angle']:.1f}°</small></h3>
<div class="segs">{" ".join(f"<span>{s}</span>" for s in r.get('segs',[]))}</div>
<img src="{r['panel']}" alt="{r['slug']}" loading="lazy"></div>''')
        else:
            rows.append(f'<div class="card"><h3>{r["slug"]}</h3><p>Ошибка: {r.get("error")}</p></div>')
    html=f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Репетиция: ориентация и элементы болтов</title>
<style>body{{font-family:system-ui,sans-serif;margin:20px;background:#f5f5f5;color:#222}} .card{{background:#fff;border:1px solid #ddd;border-radius:10px;padding:14px;margin:14px 0}} img{{max-width:100%;height:auto;border:1px solid #eee}} h3{{margin:0 0 8px;font-size:16px}} small{{color:#666;font-weight:normal}} .segs span{{display:inline-block;background:#eef;padding:2px 8px;border-radius:10px;margin:2px 4px 6px 0;font-size:12px}}</style>
</head><body>
<h1>Репетиция разметки болтов (20 шт.)</h1>
<p>Этап 1: авто-поворот по PCA, выравнивание длинной оси горизонтально, головка слева. Этап 2: эвристическое выделение конструктивных элементов по профилю ширины.</p>
{''.join(rows)}
</body></html>'''
    (OUT/'index.html').write_text(html,encoding='utf-8')
    (OUT/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print('report', OUT/'index.html')

if __name__=='__main__':
    main()
