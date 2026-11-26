#!/usr/bin/env python3
import json, os, re, math
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from PIL import Image, ImageOps
import numpy as np
from drawing_rehearsal_draw import generate_for_item

ROOT = Path(__file__).resolve().parents[2]  # site/
ITEMS_HTML = ROOT / 'knowledge' / 'items'
OUT = ROOT / 'knowledge' / 'tools' / 'drawing-rehearsal'
OUT.mkdir(parents=True, exist_ok=True)
CORR = OUT / 'corrections.json'


def get_image_path(slug):
    html=(ITEMS_HTML/f'{slug}.html').read_text(encoding='utf-8',errors='ignore')
    m=re.search(r'<div class="wk-infobox__img"><img src="([^"]+)"', html)
    if not m: return None, html
    src=m.group(1)
    if src.startswith('../'):
        p=(ITEMS_HTML/src).resolve()
    else:
        p=(ROOT/'knowledge'/src).resolve()
    return p, html

def get_title(html, slug):
    m=re.search(r'<h1 class="wk-title">(.*?)</h1>', html, re.S)
    return re.sub('<[^>]+>','',m.group(1)).strip() if m else slug

def load_mask(img):
    g = img.convert('L')
    a = np.array(g, dtype=np.float32)
    if img.mode in ('RGBA','LA'):
        alpha = np.array(img.split()[-1], dtype=np.float32)
        bg = alpha > 10
    else:
        bg = np.zeros_like(a, dtype=bool)
    thr = np.percentile(a, 60)
    thr = min(max(thr, 80), 245)
    mask = (a < thr) | bg
    mask[:2,:]=False; mask[-2:,:]=False; mask[:,:2]=False; mask[:,-2:]=False
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
    if angle > 90: angle -= 180
    if angle < -90: angle += 180
    return angle

def rotate_image(img, angle):
    return img.rotate(angle, expand=True, resample=Image.BICUBIC, fillcolor=(255,255,255))

def crop_to_mask(img, mask, pad=12):
    ys,xs = np.where(mask)
    if len(xs)==0: return img, mask, (0,0)
    x0=max(0,int(xs.min())-pad); x1=min(mask.shape[1],int(xs.max())+pad+1)
    y0=max(0,int(ys.min())-pad); y1=min(mask.shape[0],int(ys.max())+pad+1)
    return img.crop((x0,y0,x1,y1)), mask[y0:y1,x0:x1], (x0,y0)

def ensure_head_left(img, mask):
    ys,xs = np.where(mask)
    if len(xs)==0: return img, mask, False
    x0,x1 = xs.min(), xs.max()
    mid = (x0+x1)/2
    col = mask.sum(axis=0).astype(np.float32)
    col = col[x0:x1+1]
    if len(col)<10: return img, mask, False
    n=len(col)
    left_w = col[:max(1,n//3)].mean()
    right_w = col[-max(1,n//3):].mean()
    flipped=False
    if right_w > left_w * 1.15:
        img = ImageOps.mirror(img)
        mask = mask[:, ::-1].copy()
        flipped=True
    return img, mask, flipped

def width_profile(mask):
    ys,xs = np.where(mask)
    if len(xs)==0: return None
    x0,x1=int(xs.min()), int(xs.max())
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
    k=min(15, max(3, n//20*2+1))
    kernel = np.ones(k)/k
    sm = np.convolve(prof, kernel, mode='same')
    maxw = sm.max() if sm.max()>0 else 1
    left_region = sm[:max(5,int(n*0.45))]
    peak_i = int(np.argmax(left_region))
    head_end = peak_i
    for i in range(peak_i, len(left_region)):
        if sm[i] < left_region[peak_i]*0.75:
            head_end = i
            break
    head_end = max(head_end, int(n*0.08))
    head_end = min(head_end, int(n*0.35))

    chamfer_start = n-1
    for i in range(n-1, int(n*0.6), -1):
        if sm[i] < 0.5*maxw: chamfer_start = i
        else: break
    chamfer_start = max(chamfer_start, int(n*0.85))

    underhead_end = min(head_end + max(3,int(n*0.06)), chamfer_start-2)
    if family in ('hex','flange','carriage','fitting','swing'):
        thread_start = int(n*0.55)
    elif family in ('countersunk','elevator'):
        thread_start = int(n*0.45)
    elif family in ('tbolt','anchor'):
        thread_start = int(n*0.35)
    else:
        thread_start = int(n*0.5)
    thread_start = max(thread_start, underhead_end+2)
    thread_start = min(thread_start, chamfer_start-2)

    ys,xs = np.where(mask)
    y0,y1 = int(ys.min()), int(ys.max())
    def seg(name, a,b, color):
        a=max(0,min(n-1,int(a))); b=max(0,min(n,int(b)))
        if b<=a: b=a+1
        return {'name':name,'x1':int(x0+a),'x2':int(x0+b),'y1':y0,'y2':y1+1,'color':color}
    segs=[]
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

def analyze(slug, family):
    src, html = get_image_path(slug)
    title = get_title(html, slug)
    if not src or not src.exists():
        return {'slug':slug,'family':family,'title':title,'error':'image not found'}
    img = Image.open(src).convert('RGB')
    mask = load_mask(img)
    angle = pca_angle(mask)
    rotated = rotate_image(img, angle)
    mask_r = load_mask(rotated)
    rotated, mask_r, crop_off = crop_to_mask(rotated, mask_r, pad=12)
    rotated, mask_r, flipped = ensure_head_left(rotated, mask_r)
    segs = segment_elements(mask_r, family)
    # save processed image for UI
    rel = f'drawing-rehearsal/processed/{slug}.png'
    outp = OUT/'processed'/f'{slug}.png'
    outp.parent.mkdir(parents=True, exist_ok=True)
    rotated.save(outp,'PNG')
    # stage 0 auto suggestion
    warn=[]
    lname = title.lower()
    if family in ('eye','swing') or 'рым' in lname or 'крюк' in lname or 'кольц' in lname or 'откид' in lname:
        warn.append('other_elements')
    # multiple objects heuristic: count wide separated components in mask - rough
    col = mask_r.sum(axis=0)
    nz = col>0
    if nz.any():
        # gaps in middle
        idx = np.where(nz)[0]
        gaps = np.where(np.diff(idx)>max(10,int((idx[-1]-idx[0])*0.08)))[0]
        if len(gaps)>0: warn.append('multiple_objects')
    return {
        'slug':slug,'family':family,'title':title,
        'image':f'/knowledge/tools/{rel}',
        'orig_image': '/' + str(src.relative_to(ROOT)).replace('\\','/'),
        'width':rotated.size[0],'height':rotated.size[1],
        'angle':round(angle,2),'flipped':flipped,
        'segments':segs,
        'stage0_warnings':warn,
    }

def load_corrections():
    if CORR.exists():
        try: return json.loads(CORR.read_text(encoding='utf-8'))
        except Exception: return {}
    return {}

def save_corrections(data):
    CORR.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


MANIFEST = ROOT / 'knowledge' / 'tools' / 'bolts_drawing_manifest.json'

def load_items():
    corrs = load_corrections()
    m = json.loads(MANIFEST.read_text(encoding='utf-8'))
    items=[]
    for x in m:
        slug=x['slug']
        c=corrs.get(slug,{})
        if c.get('status')=='rejected':
            continue
        items.append((x.get('family','hex'), slug))
    return items

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == '/api/rehearsal/items':
            corrs = load_corrections()
            items=[]
            for fam,slug in load_items():
                a=analyze(slug,fam)
                c=corrs.get(slug,{})
                a['correction']=c
                items.append(a)
            return self._json(200, {'ok':True,'items':items})
        if u.path == '/api/rehearsal/item':
            qs=parse_qs(u.query)
            slug=(qs.get('slug') or [''])[0]
            all_items=load_items()
            fam=next((f for f,s in all_items if s==slug), 'hex')
            a=analyze(slug,fam)
            corrs=load_corrections()
            a['correction']=corrs.get(slug,{})
            return self._json(200, {'ok':True,'item':a})
        if u.path == '/api/rehearsal/drawings':
            corrs = load_corrections()
            items=[]
            for fam,slug in load_items():
                c=corrs.get(slug,{})
                if c.get('status')!='ok':
                    continue
                # analyze for image size and title, but use saved segments
                a=analyze(slug,fam)
                segs=c.get('segments') or a.get('segments') or []
                svg,err = generate_for_item(slug,fam,a.get('title',slug),segs)
                items.append({
                    'slug':slug,'family':fam,'title':a.get('title',slug),
                    'image':a.get('image'),
                    'width':a.get('width'),'height':a.get('height'),
                    'segments':segs,'svg':svg,'error':err
                })
            return self._json(200, {'ok':True,'items':items})
        return super().do_GET()

    def do_POST(self):
        u=urlparse(self.path)
        length=int(self.headers.get('Content-Length','0'))
        body=self.rfile.read(length) if length else b''
        if u.path == '/api/rehearsal/save':
            try:
                payload=json.loads(body.decode('utf-8'))
            except Exception as e:
                return self._json(400, {'ok':False,'error':str(e)})
            slug=payload.get('slug')
            if not slug: return self._json(400, {'ok':False,'error':'no slug'})
            corrs=load_corrections()
            corrs[slug]={
                'status': payload.get('status','ok'), # ok / rejected
                'reject_reason': payload.get('reject_reason',''),
                'segments': payload.get('segments',[]),
                'notes': payload.get('notes',''),
            }
            save_corrections(corrs)
            return self._json(200, {'ok':True})
        return self._json(404, {'ok':False,'error':'not found'})

    def log_message(self, fmt, *args):
        print(fmt % args)

if __name__ == '__main__':
    port=int(os.environ.get('PORT','8091'))
    srv=ThreadingHTTPServer(('127.0.0.1',port), Handler)
    print(f'Rehearsal server: http://127.0.0.1:{port}/knowledge/tools/drawing-rehearsal.html')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
