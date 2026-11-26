#!/usr/bin/env python3
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # site/
MANIFEST = ROOT / 'knowledge' / 'tools' / 'bolts_manifest.json'
OUT = ROOT / 'knowledge' / 'images' / 'drawings' / 'items'
OUT.mkdir(parents=True, exist_ok=True)

def family_for(item):
    n = (item['name'] or '').lower()
    std = (item.get('standard') or '').lower()
    if 'рым' in n or 'eye' in n:
        return 'eye'
    if any(x in n for x in ['t-образ', 'т-образ', 'half', 'паз', 'молотков', 'din 186', 'din 261']):
        # DIN 186 is T-slot, but some entries are ambiguous; check name first
        if 't-образ' in n or 'т-образ' in n or 'паз' in n or 'half' in n or 'din 261' in n or 'din 186 болт с т' in n:
            return 'tbolt'
    if 'фланц' in n:
        return 'flange'
    if 'мебель' in n or 'полукруглой головкой' in n or 'din 603' in n or 'din 607' in n and 'ус' in n:
        return 'carriage'
    if 'потайн' in n or 'din 605' in n or 'din 604' in n or 'din 608' in n or 'лемеш' in n:
        return 'countersunk'
    if 'анкер' in n or 'фундамент' in n or 'din 529' in n or '24379' in n:
        return 'anchor'
    if 'нори' in n or 'din 15237' in n:
        return 'elevator'
    if 'призон' in n or 'din 609' in n or 'din 610' in n or 'din 7968' in n:
        return 'fitting'
    if 'откид' in n or 'din 444' in n or '3033' in n:
        return 'eye' if 'кольц' in n else 'swing'
    return 'hex'

def svg_wrap(inner, title, subtitle=''):
    sub = f'<text x="400" y="205" text-anchor="middle" font-size="12" fill="#556"> {subtitle}</text>' if subtitle else ''
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 230" font-family="Arial, sans-serif">
  <rect width="800" height="230" fill="#ffffff"/>
  <defs>
    <marker id="ah" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#555"/></marker>
    <marker id="ahb" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto-start-reverse"><path d="M0,0 L8,4 L0,8 Z" fill="#555"/></marker>
  </defs>
  <style>
    .s{{stroke:#1f2937;stroke-width:2;fill:none}}
    .f{{fill:#f6f7f9;stroke:#1f2937;stroke-width:2}}
    .th{{stroke:#4b5563;stroke-width:1}}
    .dim{{stroke:#6b7280;stroke-width:1;fill:#374151;font-size:13px}}
  </style>
  {inner}
  <text x="400" y="190" text-anchor="middle" font-size="13" fill="#374151">{title}</text>
  {sub}
</svg>'''

def dim_h(x1,x2,y,label,ey1=None,ey2=None):
    ey1 = y-25 if ey1 is None else ey1
    ey2 = y-25 if ey2 is None else ey2
    return f'''<g class="dim">
  <line x1="{x1}" y1="{ey1}" x2="{x1}" y2="{y}"/><line x1="{x2}" y1="{ey2}" x2="{x2}" y2="{y}"/>
  <line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" marker-start="url(#ahb)" marker-end="url(#ah)"/>
  <text x="{(x1+x2)/2}" y="{y-5}" text-anchor="middle" stroke="none">{label}</text>
</g>'''

def dim_v(x,y1,y2,label,ex1=None,ex2=None):
    ex1 = x+25 if ex1 is None else ex1
    ex2 = x+25 if ex2 is None else ex2
    return f'''<g class="dim">
  <line x1="{ex1}" y1="{y1}" x2="{x}" y2="{y1}"/><line x1="{ex2}" y1="{y2}" x2="{x}" y2="{y2}"/>
  <line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" marker-start="url(#ahb)" marker-end="url(#ah)"/>
  <text x="{x+8}" y="{(y1+y2)/2+4}" text-anchor="start" stroke="none">{label}</text>
</g>'''

def hex_template(item):
    inner = f'''
  <g class="f"><polygon points="120,70 140,55 190,55 210,70 210,110 190,125 140,125 120,110"/></g>
  <g class="s"><line x1="140" y1="55" x2="140" y2="125"/><line x1="190" y1="55" x2="190" y2="125"/></g>
  <rect class="f" x="210" y="78" width="170" height="24"/>
  <rect class="f" x="380" y="78" width="260" height="24"/>
  <g class="th">{"".join(f'<line x1="{x}" y1="78" x2="{x+8}" y2="102"/>' for x in range(385,635,14))}</g>
  <path class="s" d="M640,78 L660,90 L640,102"/>
  <line class="s" stroke-dasharray="10,6,2,6" x1="90" y1="90" x2="680" y2="90"/>
  {dim_h(120,210,45,'s',55,55)}
  {dim_h(210,640,150,'l',102,102)}
  {dim_h(380,640,165,'b',102,102)}
  {dim_v(680,78,102,'d',662,662)}
  {dim_v(95,55,125,'k',118,118)}
'''
    return svg_wrap(inner, f"Схема: {item['name']}", "s — размер под ключ, k — высота головки, d — диаметр, l — длина, b — длина резьбы")

def flange_template(item):
    inner = f'''
  <polygon class="f" points="120,72 140,58 190,58 210,72 210,92 190,92 140,92 120,92"/>
  <ellipse class="f" cx="165" cy="100" rx="55" ry="10"/>
  <rect class="f" x="150" y="92" width="30" height="8"/>
  <rect class="f" x="210" y="82" width="160" height="20"/>
  <rect class="f" x="370" y="82" width="260" height="20"/>
  <g class="th">{"".join(f'<line x1="{x}" y1="82" x2="{x+8}" y2="102"/>' for x in range(375,625,14))}</g>
  <path class="s" d="M630,82 L650,92 L630,102"/>
  <line class="s" stroke-dasharray="10,6,2,6" x1="95" y1="92" x2="670" y2="92"/>
  {dim_h(110,220,45,'df',100,100)}
  {dim_h(210,630,150,'l',102,102)}
  {dim_v(665,82,102,'d',652,652)}
  {dim_v(95,58,92,'k',118,118)}
'''
    return svg_wrap(inner, f"Схема: {item['name']}", "df — диаметр фланца, k — высота головки, d — диаметр, l — длина")

def carriage_template(item):
    inner = f'''
  <path class="f" d="M120,95 Q165,45 210,95 L210,105 L120,105 Z"/>
  <rect class="f" x="152" y="105" width="26" height="12"/>
  <rect class="f" x="210" y="84" width="150" height="22"/>
  <rect class="f" x="360" y="84" width="270" height="22"/>
  <g class="th">{"".join(f'<line x1="{x}" y1="84" x2="{x+8}" y2="106"/>' for x in range(365,625,14))}</g>
  <path class="s" d="M630,84 L650,95 L630,106"/>
  <line class="s" stroke-dasharray="10,6,2,6" x1="100" y1="95" x2="670" y2="95"/>
  {dim_h(120,210,45,'dk',95,95)}
  {dim_h(210,630,150,'l',106,106)}
  {dim_v(665,84,106,'d',652,652)}
  {dim_v(100,65,105,'k',118,118)}
'''
    return svg_wrap(inner, f"Схема: {item['name']}", "dk — диаметр головки, квадратный подголовок предотвращает проворачивание, d — диаметр, l — длина")

def countersunk_template(item):
    inner = f'''
  <path class="f" d="M120,95 L210,70 L210,120 Z"/>
  <rect class="f" x="210" y="84" width="150" height="22"/>
  <rect class="f" x="360" y="84" width="270" height="22"/>
  <g class="th">{"".join(f'<line x1="{x}" y1="84" x2="{x+8}" y2="106"/>' for x in range(365,625,14))}</g>
  <path class="s" d="M630,84 L650,95 L630,106"/>
  <line class="s" stroke-dasharray="10,6,2,6" x1="100" y1="95" x2="670" y2="95"/>
  {dim_h(120,210,50,'k',95,70)}
  {dim_h(210,630,150,'l',106,106)}
  {dim_v(665,84,106,'d',652,652)}
'''
    return svg_wrap(inner, f"Схема: {item['name']}", "Потайная головка/подголовок; d — диаметр, l — длина, k — размер головки")

def eye_template(item):
    inner = f'''
  <circle class="f" cx="140" cy="95" r="35"/>
  <circle cx="140" cy="95" r="20" fill="#fff" stroke="#1f2937" stroke-width="2"/>
  <rect class="f" x="175" y="85" width="160" height="20"/>
  <rect class="f" x="335" y="85" width="290" height="20"/>
  <g class="th">{"".join(f'<line x1="{x}" y1="85" x2="{x+8}" y2="105"/>' for x in range(340,620,14))}</g>
  <path class="s" d="M625,85 L645,95 L625,105"/>
  <line class="s" stroke-dasharray="10,6,2,6" x1="100" y1="95" x2="665" y2="95"/>
  {dim_h(105,175,45,'d2',60,60)}
  {dim_h(175,625,150,'l',105,105)}
  {dim_v(660,85,105,'d',647,647)}
'''
    return svg_wrap(inner, f"Схема: {item['name']}", "d2 — внутренний диаметр кольца, d — диаметр резьбы, l — длина")

def tbolt_template(item):
    inner = f'''
  <rect class="f" x="110" y="70" width="90" height="30"/>
  <rect class="f" x="140" y="70" width="30" height="30" fill="#eef0f3"/>
  <rect x="95" y="58" width="120" height="10" fill="none" stroke="#9ca3af" stroke-dasharray="4,3"/>
  <rect x="95" y="102" width="120" height="10" fill="none" stroke="#9ca3af" stroke-dasharray="4,3"/>
  <rect class="f" x="200" y="83" width="150" height="20"/>
  <rect class="f" x="350" y="83" width="270" height="20"/>
  <g class="th">{"".join(f'<line x1="{x}" y1="83" x2="{x+8}" y2="103"/>' for x in range(355,615,14))}</g>
  <path class="s" d="M620,83 L640,93 L620,103"/>
  {dim_h(110,200,45,'a',70,70)}
  {dim_h(200,620,150,'l',103,103)}
  {dim_v(655,83,103,'d',642,642)}
'''
    return svg_wrap(inner, f"Схема: {item['name']}", "a — ширина головки, головка фиксируется в Т-пазу поворотом, d — диаметр, l — длина")

def anchor_template(item):
    inner = f'''
  <rect class="f" x="120" y="70" width="70" height="18"/>
  <rect class="f" x="146" y="88" width="18" height="12"/>
  <path class="f" d="M140,100 L170,100 L178,150 L132,150 Z"/>
  <rect class="f" x="145" y="150" width="20" height="120"/>
  <g class="th">{"".join(f'<line x1="145" y1="{y}" x2="165" y2="{y+8}"/>' for y in range(155,265,12))}</g>
  <path class="s" d="M145,270 L155,285 L165,270"/>
  <line class="s" stroke-dasharray="10,6,2,6" x1="155" y1="60" x2="155" y2="290"/>
  {dim_h(120,190,55,'s',70,70)}
  {dim_v(200,100,270,'l',170,165)}
  {dim_v(220,150,270,'b',165,165)}
'''
    return svg_wrap(inner, f"Схема: {item['name']}", "Фундаментный/анкерный тип: s — размер под ключ, l — длина, b — резьбовая часть")

def elevator_template(item):
    inner = f'''
  <path class="f" d="M120,95 L210,75 L210,115 Z"/>
  <rect class="f" x="210" y="86" width="150" height="18"/>
  <rect class="f" x="360" y="86" width="250" height="18"/>
  <g class="th">{"".join(f'<line x1="{x}" y1="86" x2="{x+7}" y2="104"/>' for x in range(365,605,13))}</g>
  <path class="s" d="M610,86 L630,95 L610,104"/>
  <rect x="225" y="104" width="16" height="8" fill="#e5e7eb" stroke="#374151"/>
  {dim_h(120,210,55,'dk',95,75)}
  {dim_h(210,610,150,'l',104,104)}
  {dim_v(645,86,104,'d',632,632)}
'''
    return svg_wrap(inner, f"Схема: {item['name']}", "Норийный/транспортёрный болт: увеличенная потайная головка, d — диаметр, l — длина")

def fitting_template(item):
    inner = f'''
  <rect class="f" x="120" y="72" width="70" height="28"/>
  <rect class="f" x="190" y="80" width="230" height="20" fill="#f9fafb"/>
  <rect class="f" x="420" y="80" width="170" height="20"/>
  <g class="th">{"".join(f'<line x1="{x}" y1="80" x2="{x+8}" y2="100"/>' for x in range(425,585,14))}</g>
  <path class="s" d="M590,80 L610,90 L590,100"/>
  <line class="s" stroke-dasharray="10,6,2,6" x1="100" y1="90" x2="630" y2="90"/>
  {dim_h(190,420,55,'ds',80,80)}
  {dim_h(420,590,150,'b',100,100)}
  {dim_h(120,590,165,'l',100,100)}
  {dim_v(625,80,100,'d',612,612)}
'''
    return svg_wrap(inner, f"Схема: {item['name']}", "Призонный/посадочный болт: ds — гладкая посадочная часть, b — резьба, l — длина")

def swing_template(item):
    inner = f'''
  <circle class="f" cx="140" cy="92" r="28"/>
  <circle cx="140" cy="92" r="14" fill="#fff" stroke="#1f2937" stroke-width="2"/>
  <rect class="f" x="168" y="84" width="140" height="16"/>
  <rect class="f" x="308" y="84" width="250" height="16"/>
  <g class="th">{"".join(f'<line x1="{x}" y1="84" x2="{x+7}" y2="100"/>' for x in range(313,553,13))}</g>
  <path class="s" d="M558,84 L578,92 L558,100"/>
  {dim_h(112,168,50,'d2',64,64)}
  {dim_h(168,558,145,'l',100,100)}
  {dim_v(590,84,100,'d',580,580)}
'''
    return svg_wrap(inner, f"Схема: {item['name']}", "Откидной/петлевый тип: d2 — размер петли/кольца, d — диаметр, l — длина")

TEMPLATES = {
    'hex': hex_template,
    'flange': flange_template,
    'carriage': carriage_template,
    'countersunk': countersunk_template,
    'eye': eye_template,
    'tbolt': tbolt_template,
    'anchor': anchor_template,
    'elevator': elevator_template,
    'fitting': fitting_template,
    'swing': swing_template,
}

def main():
    items = json.loads(MANIFEST.read_text(encoding='utf-8'))
    out_manifest = []
    for item in items:
        fam = family_for(item)
        fn = TEMPLATES[fam]
        svg = fn(item)
        path = OUT / f"{item['slug']}.svg"
        path.write_text(svg, encoding='utf-8')
        out_manifest.append({**item, 'family': fam, 'drawing': f'images/drawings/items/{item["slug"]}.svg', 'source': 'generated-template'})
    (ROOT/'knowledge/tools/bolts_drawing_manifest.json').write_text(json.dumps(out_manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'generated {len(out_manifest)} drawings')
    from collections import Counter
    print(Counter(x['family'] for x in out_manifest))

if __name__ == '__main__':
    main()
