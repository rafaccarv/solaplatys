"""Regras de negócio e consultas reutilizáveis (loja pública)."""
import os, io, secrets, re, math, urllib.request
from datetime import datetime, timedelta
from db import q, ex, slugify, unique_slug, DEFAULT_SETTINGS
from PIL import Image, ImageOps
_cache = {}
SUPA_URL = os.environ.get('SUPABASE_URL', '').rstrip('/'); SUPA_KEY = os.environ.get('SUPABASE_SERVICE_KEY', ''); BUCKET = os.environ.get('SUPABASE_BUCKET', 'uploads')
def get_settings():
    if 'v' not in _cache:
        _cache['v'] = {**DEFAULT_SETTINGS, **{r['key']: r['value'] for r in q('select * from settings')}}
    return _cache['v']
def set_setting(k, v):
    ex('insert into settings values(?,?) on conflict(key) do update set value=excluded.value', (k, v)); _cache.clear()

def money(v): return '' if v is None else 'R$ ' + f'{v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
def img(p, w=None):
    if not p: return '/ph/ring1.svg'
    if p.startswith('ph:'): return f'/ph/{p[3:]}.svg'
    return f'{SUPA_URL}/storage/v1/object/public/{BUCKET}/{p}' if SUPA_URL else f'/static/uploads/{p}'
def ids(s): return [int(x) for x in (s or '').split(',') if x.strip().isdigit()]
def extra_lines(t): return [tuple(x.split(':', 1)) for x in (t or '').splitlines() if ':' in x]
def badge(p):
    if p['sale_price']: return 'Oferta'
    if p['badge']: return p['badge']
    if p['featured']: return 'Destaque'
    try:
        if datetime.utcnow() - datetime.fromisoformat(p['created_at']) < timedelta(days=30): return 'Novo'
    except Exception: pass
    return ''
def tags_of(pid): return q('select t.* from tags t join product_tags pt on pt.tag_id=t.id where pt.product_id=? order by t.name', (pid,))
def gallery(pid): return q('select * from product_images where product_id=? order by position,id', (pid,))
def set_tags(pid, csv):
    ex('delete from product_tags where product_id=?', (pid,))
    for n in {t.strip().lower() for t in csv.split(',') if t.strip()}:
        ex('insert or ignore into tags(name,slug) values(?,?)', (n, slugify(n)))
        ex('insert or ignore into product_tags select ?,id from tags where name=?', (pid, n))

PSEL = ("select p.*, c.name cat_name, c.slug cat_slug, (select path from product_images where product_id=p.id order by position,id limit 1) image "
        "from products p left join categories c on c.id=p.category_id ")
ORDERS = {'recent': 'p.created_at desc, p.id desc', 'price_asc': 'coalesce(p.sale_price,p.price) asc', 'price_desc': 'coalesce(p.sale_price,p.price) desc',
          'name': 'lower(p.name)', 'featured': 'p.featured desc, p.position, p.id desc', 'default': 'p.position, p.id'}
def list_products(where='p.active=1', args=(), order='default', limit=None):
    return q(PSEL + f'where {where} order by {ORDERS.get(order, ORDERS["default"])}' + (f' limit {int(limit)}' if limit else ''), args)
def by_ids(idl, table='products'):
    if table == 'categories':
        rows = {r['id']: r for r in q('select * from categories where visible=1')}
    else:
        rows = {r['id']: r for r in list_products()}
    return [rows[i] for i in idl if i in rows]
def filter_products(a, cat=None):
    w, args = ['p.active=1'], []
    if cat: w.append('p.category_id=?'); args.append(cat['id'])
    elif a.get('category'): w.append('c.slug=?'); args.append(a['category'])
    if a.get('min'): w.append('coalesce(p.sale_price,p.price)>=?'); args.append(float(a['min']))
    if a.get('max'): w.append('coalesce(p.sale_price,p.price)<=?'); args.append(float(a['max']))
    if a.get('tag'): w.append('exists(select 1 from product_tags pt join tags t on t.id=pt.tag_id where pt.product_id=p.id and t.slug=?)'); args.append(a['tag'])
    if a.get('avail'): w.append('p.availability=?'); args.append(a['avail'])
    return list_products(' and '.join(w), args, a.get('sort', 'default'))
def _num(v):
    try: float(v); return v
    except (TypeError, ValueError): return ''
def search(s, limit=60):
    l = f'%{s}%'
    return q(PSEL + 'where p.active=1 and (p.name ilike ? or p.sku ilike ? or c.name ilike ? or exists(select 1 from product_tags pt join tags t on t.id=pt.tag_id where pt.product_id=p.id and t.name ilike ?)) order by p.featured desc, p.name limit ?', (l, l, l, l, limit))
def home_blocks():
    out = []
    for s in q('select * from home_sections where visible=1 order by position,id'):
        s = dict(s); t = s['type']
        if t == 'categories':
            s['items'] = by_ids(ids(s['cat_ids']), 'categories') or q('select * from categories where visible=1 order by position,id')
        elif t in ('featured', 'new', 'collection'):
            lim = s['limit_n'] or 4
            s['items'] = by_ids(ids(s['prod_ids']))[:lim] or list_products('p.active=1' + (' and p.featured=1' if t == 'featured' else ''), order='featured' if t == 'featured' else 'recent', limit=lim)
        elif t in ('banner', 'gallery'):
            s['items'] = q('select * from banners where active=1 and zone=? order by position,id', (s['zone'] or 'gallery',))
        out.append(s)
    return out

def save_image(f, maxw=1600):
    """Valida (extensão + decodificação real), corrige rotação, redimensiona e converte para WebP com nome aleatório."""
    if not f or not f.filename: return None
    if f.filename.rsplit('.', 1)[-1].lower() not in {'jpg', 'jpeg', 'png', 'webp', 'gif'}: raise ValueError('Formato de imagem não permitido.')
    from db import BASE
    try:
        Image.open(f.stream).verify(); f.stream.seek(0)
        im = ImageOps.exif_transpose(Image.open(f.stream)); im.thumbnail((maxw, maxw))
    except Exception: raise ValueError('Arquivo de imagem inválido.')
    name = secrets.token_hex(8) + '.webp'
    buf = io.BytesIO(); im.convert('RGBA' if im.mode in ('RGBA', 'LA', 'P') else 'RGB').save(buf, 'WEBP', quality=82); data = buf.getvalue()
    if SUPA_URL and SUPA_KEY:  # Supabase Storage (o disco do Render é temporário)
        req = urllib.request.Request(f'{SUPA_URL}/storage/v1/object/{BUCKET}/{name}', data=data, method='POST', headers={'Authorization': f'Bearer {SUPA_KEY}', 'apikey': SUPA_KEY, 'Content-Type': 'image/webp', 'cache-control': 'max-age=31536000'})
        try: urllib.request.urlopen(req, timeout=30)
        except Exception: raise ValueError('Falha ao enviar a imagem para o armazenamento.')
    else:
        open(os.path.join(BASE, 'static', 'uploads', name), 'wb').write(data)
    return name

def placeholder(name):
    """SVG de joia estilizado (placeholder elegante, sem dependência externa)."""
    kind = re.match(r'[a-z]+', name).group(); n = int(''.join(c for c in name if c.isdigit()) or 1); alt = name.endswith('b')
    dark = kind in ('hero', 'banner'); a, b = ('#151517', '#34363a') if dark else ('#f5f5f6', '#d9dbdf')
    st = 'url(#s)'; sw = 26 + n * 4
    if kind == 'ring': body = f'<circle cx="400" cy="560" r="170" fill="none" stroke="{st}" stroke-width="{sw}"/><circle cx="400" cy="560" r="{170-sw/2}" fill="none" stroke="#0002" stroke-width="2"/><path d="M400 330 l{40+n*6} 40 l-{40+n*6} 50 l-{40+n*6} -50z" fill="#fff" stroke="{st}" stroke-width="10"/>'
    elif kind == 'necklace': body = f'<path d="M140 220 Q400 {720+n*40} 660 220" fill="none" stroke="{st}" stroke-width="9"/><path d="M400 {560+n*20} l34 50 l-34 60 l-34 -60z" fill="#fff" stroke="{st}" stroke-width="12"/>'
    elif kind == 'bracelet': body = f'<ellipse cx="400" cy="520" rx="230" ry="{110+n*20}" fill="none" stroke="{st}" stroke-width="{34+n*6}"/><ellipse cx="400" cy="520" rx="230" ry="{110+n*20}" fill="none" stroke="#fff8" stroke-width="3" stroke-dasharray="2 26"/>'
    else:
        links = ''.join(f'<ellipse cx="{130+i*45}" cy="{500+math.sin(i/2.2)*120*(1 if kind!="hero" else .6)}" rx="{30+n*3}" ry="{20+n*2}" fill="none" stroke="{st}" stroke-width="{12+n*2}" transform="rotate({(i%2)*90} {130+i*45} {500+math.sin(i/2.2)*120})"/>' for i in range(14)); body = links
    o = '.5' if alt else '1'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 1000"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>'
            f'<linearGradient id="s" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff"/><stop offset=".45" stop-color="#8f949c"/><stop offset=".7" stop-color="#e9eaec"/><stop offset="1" stop-color="#6d7178"/></linearGradient></defs>'
            f'<rect width="800" height="1000" fill="url(#g)"/><g opacity="{o}" transform="{"rotate(-8 400 500)" if alt else ""}">{body}</g></svg>')
