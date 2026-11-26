#!/usr/bin/env python3
import json, os, re, base64, mimetypes
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # site/
KB_ITEMS = ROOT / 'knowledge' / 'items'
KB_DRAWINGS = ROOT / 'knowledge' / 'images' / 'drawings' / 'items'
KB_DRAWINGS.mkdir(parents=True, exist_ok=True)

def slug_from_item(path: Path):
    return path.stem

def read_article(path: Path):
    html = path.read_text(encoding='utf-8', errors='ignore')
    m = re.search(r'<h1 class="wk-title">(.*?)</h1>', html, re.S)
    title = re.sub('<[^>]+>', '', m.group(1)).strip() if m else path.stem
    # original infobox image
    mimg = re.search(r'<div class="wk-infobox__img"><img src="([^"]+)"', html)
    img = mimg.group(1) if mimg else ''
    # current figure
    mfig = re.search(r'<figure class="wk-figure">.*?<img src="([^"]+)".*?<figcaption>(.*?)</figcaption>.*?</figure>', html, re.S)
    fig_img = mfig.group(1) if mfig else ''
    fig_cap = re.sub('<[^>]+>', '', mfig.group(2)).strip() if mfig else ''
    custom = (KB_DRAWINGS / f'{path.stem}.png').exists()
    return {
        'slug': path.stem,
        'title': title,
        'file': str(path.relative_to(ROOT)),
        'infobox_img': img,
        'figure_img': fig_img,
        'figure_caption': fig_cap,
        'has_custom_drawing': custom,
        'custom_drawing': f'../images/drawings/items/{path.stem}.png' if custom else '',
    }

def list_articles():
    items = []
    for p in sorted(KB_ITEMS.glob('*.html'), key=lambda x: x.name.lower()):
        a = read_article(p)
        # only articles with an infobox/original image are useful
        if a['infobox_img']:
            items.append(a)
    return items

def save_drawing(slug, data_url, caption=None):
    p = KB_ITEMS / f'{slug}.html'
    if not p.exists():
        return {'ok': False, 'error': 'Article not found'}
    m = re.match(r'^data:image/(png|jpeg);base64,(.+)$', data_url, re.S)
    if not m:
        return {'ok': False, 'error': 'Invalid image data'}
    ext = 'png' if m.group(1) == 'png' else 'jpg'
    raw = base64.b64decode(m.group(2))
    out = KB_DRAWINGS / f'{slug}.png'
    out.write_bytes(raw)
    # update article figure
    html = p.read_text(encoding='utf-8', errors='ignore')
    fig_src = f'../images/drawings/items/{slug}.png'
    cap = caption or f'Чертёж: {read_article(p)["title"]}'
    fig_html = f'''  <figure class="wk-figure">
    <img src="{fig_src}" alt="{cap}" loading="lazy" decoding="async">
    <figcaption>{cap}</figcaption>
  </figure>'''
    if re.search(r'<figure class="wk-figure">.*?</figure>', html, re.S):
        html = re.sub(r'<figure class="wk-figure">.*?</figure>', fig_html, html, count=1, flags=re.S)
    else:
        # insert after lead
        html = re.sub(r'(<div class="wk-lead">.*?</div>)', r'\1\n' + fig_html, html, count=1, flags=re.S)
    p.write_text(html, encoding='utf-8')
    return {'ok': True, 'file': str(out.relative_to(ROOT)), 'article': f'/knowledge/items/{slug}.html', 'figure_src': fig_src}

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == '/api/articles':
            return self._json(200, {'ok': True, 'articles': list_articles()})
        if u.path == '/api/article':
            qs = parse_qs(u.query)
            slug = (qs.get('slug') or [''])[0]
            p = KB_ITEMS / f'{slug}.html'
            if not slug or not p.exists():
                return self._json(404, {'ok': False, 'error': 'Not found'})
            return self._json(200, {'ok': True, 'article': read_article(p)})
        return super().do_GET()

    def do_POST(self):
        u = urlparse(self.path)
        length = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(length) if length else b''
        if u.path == '/api/save-drawing':
            try:
                payload = json.loads(body.decode('utf-8'))
            except Exception as e:
                return self._json(400, {'ok': False, 'error': str(e)})
            slug = payload.get('slug', '')
            data_url = payload.get('image', '')
            caption = payload.get('caption')
            res = save_drawing(slug, data_url, caption)
            return self._json(200 if res.get('ok') else 400, res)
        return self._json(404, {'ok': False, 'error': 'Not found'})

    def log_message(self, fmt, *args):
        print(fmt % args)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8090'))
    srv = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'Drawing editor server: http://127.0.0.1:{port}/knowledge/tools/drawing-editor.html')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
