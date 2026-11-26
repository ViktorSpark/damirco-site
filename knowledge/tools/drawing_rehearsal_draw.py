#!/usr/bin/env python3
import json, math
from pathlib import Path
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / 'knowledge' / 'tools' / 'drawing-rehearsal' / 'processed'
CORR = ROOT / 'knowledge' / 'tools' / 'drawing-rehearsal' / 'corrections.json'

COLORS = {
    'Головка':'#e53935','Подголовник':'#fb8c00','Гладкая часть':'#43a047',
    'Резьбовая часть':'#1e88e5','Фаска (сбег)':'#8e24aa'
}

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

def width_profile(mask):
    h,w = mask.shape
    ys,xs = np.where(mask)
    if len(xs)==0: return 0,w-1,np.zeros(w)
    x0,x1=int(xs.min()), int(xs.max())
    prof=np.zeros(w,dtype=np.float32)
    for x in range(x0,x1+1):
        col=np.where(mask[:,x])[0]
        if len(col): prof[x]=col.max()-col.min()+1
    # smooth
    k=9
    kernel=np.ones(k)/k
    sm=np.convolve(prof, kernel, mode='same')
    return x0,x1,sm

def seg_color(name):
    return COLORS.get(name,'#666')

def avg_width(prof, x1,x2):
    x1=max(0,int(x1)); x2=min(len(prof),int(x2))
    if x2<=x1: x2=x1+1
    v=prof[x1:x2]
    v=v[v>0]
    return float(np.median(v)) if len(v) else 20.0

def make_svg(slug, title, family, segments, img_w, img_h, mask, prof):
    # coordinate system same as processed image
    W,H = img_w,img_h
    pad_top, pad_bottom, pad_left, pad_right = 95, 110, 90, 90
    VW,VH = W+pad_left+pad_right, H+pad_top+pad_bottom
    ox,oy = pad_left,pad_top  # origin for image coords
    # axis y center from mask
    ys,xs=np.where(mask)
    if len(ys):
        cy = (ys.min()+ys.max())/2
        x_min,x_max = int(xs.min()), int(xs.max())
    else:
        cy=H/2; x_min,x_max=0,W-1

    def X(x): return ox+x
    def Y(y): return oy+y

    # build clean contour by segment widths
    # for each segment get representative half-width
    segs = sorted([dict(s) for s in segments], key=lambda s:s['x1'])
    # clamp segments to image
    for s in segs:
        s['x1']=max(0,min(W-1,int(s['x1'])))
        s['x2']=max(s['x1']+1,min(W,int(s['x2'])))
    # derive widths: prefer corrected segment height, fallback to profile
    for s in segs:
        if 'y1' in s and 'y2' in s and s['y2']>s['y1']:
            s['w']=float(s['y2']-s['y1'])
        else:
            s['w']=avg_width(prof,s['x1'],s['x2'])
        s['cy']=cy

    # build top/bottom profile points
    top=[]; bot=[]
    hex_dividers=[]  # vertical divider lines for hex head profile
    for i,s in enumerate(segs):
        hw=s['w']/2
        is_chamfer = 'Фаска' in s['name'] or 'сбег' in s['name'].lower()
        is_head = 'Головка' in s['name']
        is_nut = s['name'] == 'Гайка'
        if is_chamfer:
            hw0=s['w']/2
            hw1=max(2, hw0*0.35)
            top.append((s['x1'], cy-hw0)); top.append((s['x2'], cy-hw1))
            bot.append((s['x1'], cy+hw0)); bot.append((s['x2'], cy+hw1))
        elif is_nut or (is_head and (s.get('head_type')=='hex' or s.get('head_round') or s.get('head_countersunk'))):
            x1,x2=s['x1'],s['x2']
            # determine right side height (countersunk tapers to next block)
            hw_r = hw
            if s.get('head_countersunk') and i+1 < len(segs):
                hw_r = segs[i+1]['w']/2
            # left boundary: rounded or straight
            if s.get('head_round'):
                # single circle, center on symmetry axis far right,
                # passes through right top/bottom corners and left boundary axis point
                dx = max(1.0, float(x2-x1))
                Rr = dx/2 + (hw_r*hw_r)/(2*dx)
                Cx = x1 + Rr
                steps=20
                # top arc: from axis point (x1,cy) to right-top corner (x2,cy-hw_r)
                for k in range(steps+1):
                    py = cy - hw_r * k/steps
                    val = max(0.0, Rr*Rr - (py-cy)*(py-cy))
                    px = Cx - math.sqrt(val)
                    top.append((px,py))
                # bottom arc: from axis point (x1,cy) to right-bottom corner
                for k in range(steps+1):
                    py = cy + hw_r * k/steps
                    val = max(0.0, Rr*Rr - (py-cy)*(py-cy))
                    px = Cx - math.sqrt(val)
                    bot.append((px,py))
            else:
                top.append((x1, cy-hw)); top.append((x2, cy-hw_r))
                bot.append((x1, cy+hw)); bot.append((x2, cy+hw_r))
            # hex horizontal dividers
            if is_nut or s.get('head_type')=='hex':
                side_h = (hw*2) * 0.25
                y_top_div = cy-hw + side_h
                y_bot_div = cy+hw - side_h
                hex_dividers.append(('h', y_top_div, x1, x2))
                hex_dividers.append(('h', y_bot_div, x1, x2))
        else:
            top.append((s['x1'], cy-hw)); top.append((s['x2'], cy-hw))
            bot.append((s['x1'], cy+hw)); bot.append((s['x2'], cy+hw))
    # make contour path
    if not top:
        contour=''
    else:
        pts = top + list(reversed(bot))
        contour = 'M ' + ' L '.join(f'{X(x):.1f},{Y(y):.1f}' for x,y in pts) + ' Z'

    # thread hatching and GOST 2.311-68 inner diameter lines
    hatch_parts=[]
    thread_inner=[]
    for s in segs:
        if 'Резьб' in s['name']:
            x1,x2=s['x1'],s['x2']; hw=s['w']/2
            y1,y2=cy-hw, cy+hw
            # clip path id
            hid=f'hatch_{slug[:20].replace("-","_")}'
            lines=[]
            step=8
            for xx in range(int(x1)-int(hw), int(x2)+int(hw), step):
                # 70 degrees
                dx=(y2-y1)/math.tan(math.radians(70))
                lines.append(f'<line x1="{X(xx):.1f}" y1="{Y(y2):.1f}" x2="{X(xx+dx):.1f}" y2="{Y(y1):.1f}" />')
            hatch_parts.append(f'<g clip-path="url(#{hid})" stroke="#6b7280" stroke-width="0.8">{"".join(lines)}</g>')
            hatch_parts.append(f'<defs><clipPath id="{hid}"><rect x="{X(x1)}" y="{Y(y1)}" width="{x2-x1}" height="{y2-y1}"/></clipPath></defs>')
            # GOST 2.311-68: thin solid line along thread roots, ~9px from crest line
            inset = 9
            if hw > inset+2:
                thread_inner.append(f'<line x1="{X(x1):.1f}" y1="{Y(y1+inset):.1f}" x2="{X(x2):.1f}" y2="{Y(y1+inset):.1f}" stroke="#374151" stroke-width="1"/>')
                thread_inner.append(f'<line x1="{X(x1):.1f}" y1="{Y(y2-inset):.1f}" x2="{X(x2):.1f}" y2="{Y(y2-inset):.1f}" stroke="#374151" stroke-width="1"/>')

    # segment color overlays on drawing
    overlays=[]
    for s in segs:
        col=seg_color(s['name'])
        hw=s['w']/2
        overlays.append(f'<rect x="{X(s["x1"])}" y="{Y(cy-hw)}" width="{max(1,s["x2"]-s["x1"])}" height="{hw*2}" fill="{col}" fill-opacity="0.08" stroke="{col}" stroke-opacity="0.45" stroke-width="1.5"/>')

    # centerline
    cl = f'<line x1="{X(x_min-15)}" y1="{Y(cy)}" x2="{X(x_max+15)}" y2="{Y(cy)}" stroke="#2563eb" stroke-width="1" stroke-dasharray="12,6,2,6"/>'

    # vertical callouts up with names (lowered to avoid title overlap)
    callups=[]
    for i,segm in enumerate(segs):
        col=seg_color(segm['name'])
        mx=X((segm['x1']+segm['x2'])/2)
        topy=Y(cy-segm['w']/2)
        ly=oy-10 - (i%2)*16
        ly=max(52, ly)  # keep below title
        callups.append(f'<line x1="{mx:.1f}" y1="{topy:.1f}" x2="{mx:.1f}" y2="{ly+12:.1f}" stroke="{col}" stroke-width="1"/>')
        callups.append(f'<text x="{mx:.1f}" y="{ly:.1f}" text-anchor="middle" font-size="11" fill="{col}" font-family="Arial">{segm["name"]}</text>')

    # down callouts for letter size designation per segment - dimension style
    letters=[]
    base_y = oy+H+30
    for i,segm in enumerate(segs):
        col=seg_color(segm['name'])
        bx1,bx2 = X(segm['x1']), X(segm['x2'])
        boty = Y(cy+segm['w']/2)
        ly = base_y + (i%3)*18
        lname=f'l{i+1}'
        # extension lines
        letters.append(f'<line x1="{bx1:.1f}" y1="{boty+4:.1f}" x2="{bx1:.1f}" y2="{ly+5:.1f}" stroke="{col}" stroke-width="0.9"/>')
        letters.append(f'<line x1="{bx2:.1f}" y1="{boty+4:.1f}" x2="{bx2:.1f}" y2="{ly+5:.1f}" stroke="{col}" stroke-width="0.9"/>')
        # dimension arrow
        letters.append(f'<line x1="{bx1:.1f}" y1="{ly:.1f}" x2="{bx2:.1f}" y2="{ly:.1f}" stroke="{col}" stroke-width="1" marker-start="url(#arrc_{i})" marker-end="url(#arrc_{i})"/>')
        letters.append(f'<text x="{(bx1+bx2)/2:.1f}" y="{ly-3:.1f}" text-anchor="middle" font-size="11" fill="{col}" font-family="Arial">{lname}</text>')

    # total length l
    total_l = f'''<g stroke="#111" stroke-width="1" font-family="Arial" font-size="13" fill="#111">
      <line x1="{X(x_min)}" y1="{Y(cy+max(s['w']/2 for s in segs)+10)}" x2="{X(x_min)}" y2="{oy+H+70}"/>
      <line x1="{X(x_max)}" y1="{Y(cy+max(s['w']/2 for s in segs)+10)}" x2="{X(x_max)}" y2="{oy+H+70}"/>
      <line x1="{X(x_min)}" y1="{oy+H+65}" x2="{X(x_max)}" y2="{oy+H+65}" marker-start="url(#arr)" marker-end="url(#arr)"/>
      <text x="{X((x_min+x_max)/2)}" y="{oy+H+60}" text-anchor="middle">l</text>
    </g>'''

    # left horizontal diameter callout at head side
    head_segs=[s for s in segs if 'Головка' in s['name'] or 'Подголовник' in s['name']]
    ref_head = head_segs[0] if head_segs else segs[0]
    hw_h = ref_head['w']/2
    hx = X(ref_head['x1'] + (ref_head['x2']-ref_head['x1'])*0.3)
    left_dim = f'''<g stroke="#374151" stroke-width="1" font-family="Arial" font-size="12" fill="#111">
      <line x1="{X(x_min)-5}" y1="{Y(cy-hw_h)}" x2="{ox-20}" y2="{Y(cy-hw_h)}"/>
      <line x1="{X(x_min)-5}" y1="{Y(cy+hw_h)}" x2="{ox-20}" y2="{Y(cy+hw_h)}"/>
      <line x1="{ox-15}" y1="{Y(cy-hw_h)}" x2="{ox-15}" y2="{Y(cy+hw_h)}" marker-start="url(#arr)" marker-end="url(#arr)"/>
      <text x="{ox-22}" y="{Y(cy)+4}" text-anchor="end">D</text>
    </g>'''

    # right horizontal diameter callout at thread side
    thread_segs=[s for s in segs if 'Резьб' in s['name']]
    ref_thr = thread_segs[-1] if thread_segs else segs[-1]
    hw_t = ref_thr['w']/2
    right_dim = f'''<g stroke="#374151" stroke-width="1" font-family="Arial" font-size="12" fill="#111">
      <line x1="{X(x_max)+5}" y1="{Y(cy-hw_t)}" x2="{ox+W+20}" y2="{Y(cy-hw_t)}"/>
      <line x1="{X(x_max)+5}" y1="{Y(cy+hw_t)}" x2="{ox+W+20}" y2="{Y(cy+hw_t)}"/>
      <line x1="{ox+W+15}" y1="{Y(cy-hw_t)}" x2="{ox+W+15}" y2="{Y(cy+hw_t)}" marker-start="url(#arr)" marker-end="url(#arr)"/>
      <text x="{ox+W+22}" y="{Y(cy)+4}" text-anchor="start">d</text>
    </g>'''

    arr_defs=['<marker id="arr" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto-start-reverse"><path d="M0,0 L8,4 L0,8 z" fill="#555"/></marker>']
    for i,segm in enumerate(segs):
        col=seg_color(segm['name'])
        arr_defs.append(f'<marker id="arrc_{i}" markerWidth="7" markerHeight="7" refX="3.5" refY="3.5" orient="auto-start-reverse"><path d="M0,0 L7,3.5 L0,7 z" fill="{col}"/></marker>')
    defs = '<defs>' + ''.join(arr_defs) + '</defs>'

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VW} {VH}" width="{VW}" height="{VH}" font-family="Arial,sans-serif">
  {defs}
  <rect width="{VW}" height="{VH}" fill="#fff"/>
  <text x="{VW/2}" y="24" text-anchor="middle" font-size="14" fill="#222">{title}</text>
  <text x="{VW/2}" y="40" text-anchor="middle" font-size="11" fill="#666">{slug} · {family}</text>
  {''.join(hatch_parts)}
  <path d="{contour}" fill="#f8fafc" stroke="#111827" stroke-width="2.4"/>
  <g class="thread-inner">{''.join(thread_inner)}</g>
  <g class="hex-dividers" stroke="#111827" stroke-width="2">{''.join(
    f'<line x1="{X(d[2]):.1f}" y1="{Y(d[1]):.1f}" x2="{X(d[3]):.1f}" y2="{Y(d[1]):.1f}"/>' if d[0]=='h'
    else f'<line x1="{X(d[0]):.1f}" y1="{Y(d[1]):.1f}" x2="{X(d[0]):.1f}" y2="{Y(d[2]):.1f}"/>'
    for d in hex_dividers)}</g>
  {''.join(overlays)}
  <g class="seg-separators" stroke="#111827" stroke-width="2.2">{''.join((lambda segm: (
    (lambda hw_l,hw_r,is_round_head: 
      ('' if is_round_head else f'<line x1="{X(segm["x1"]):.1f}" y1="{Y(cy-hw_l):.1f}" x2="{X(segm["x1"]):.1f}" y2="{Y(cy+hw_l):.1f}"/>') +
      f'<line x1="{X(segm["x2"]):.1f}" y1="{Y(cy-hw_r):.1f}" x2="{X(segm["x2"]):.1f}" y2="{Y(cy+hw_r):.1f}"/>'
    )(
      (segm['w']/2),
      (max(2, segm['w']/2*0.35) if ('Фаска' in segm['name'] or 'сбег' in segm['name'].lower()) else (segs[segs.index(segm)+1]['w']/2 if (segm.get('head_countersunk') and 'Головка' in segm['name'] and segs.index(segm)+1 < len(segs)) else segm['w']/2)),
      (bool(segm.get('head_round')) and 'Головка' in segm['name'])
    )
  ))(segm) for segm in segs)}</g>
  {cl}
  {''.join(callups)}
  {''.join(letters)}
  {total_l}
  {left_dim}
  {right_dim}
</svg>'''
    return svg

def generate_for_item(slug, family, title, segments):
    p = PROC / f'{slug}.png'
    if not p.exists():
        return None, 'no processed image'
    img = Image.open(p).convert('RGB')
    mask = load_mask(img)
    x0,x1,prof = width_profile(mask)
    svg = make_svg(slug, title, family, segments, img.size[0], img.size[1], mask, prof)
    return svg, None
