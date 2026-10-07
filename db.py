"""Camada de banco (SQLite) + schema + dados iniciais."""
import os, re, unicodedata
import psycopg2, psycopg2.extras, psycopg2.pool
from flask import g
BASE = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get('DATABASE_URL', '')

SCHEMA = """
create table if not exists users(id serial primary key, email text unique not null, password_hash text not null, created_at text default to_char(now() at time zone 'utc','YYYY-MM-DD HH24:MI:SS'));
create table if not exists categories(id serial primary key, name text not null, slug text unique not null, description text default '', image text default '', featured_image text default '', position integer default 0, visible integer default 1, meta_title text default '', meta_description text default '', updated_at text default to_char(now() at time zone 'utc','YYYY-MM-DD HH24:MI:SS'));
create table if not exists products(id serial primary key, name text not null, slug text unique not null, sku text default '', price double precision, sale_price double precision, short_desc text default '', description text default '', category_id integer references categories(id) on delete set null, subcategory text default '', material text default '', weight text default '', size text default '', availability text default 'disponivel', badge text default '', featured integer default 0, active integer default 1, extra text default '', custom_text text default '', meta_title text default '', meta_description text default '', og_image text default '', position integer default 0, created_at text default to_char(now() at time zone 'utc','YYYY-MM-DD HH24:MI:SS'), updated_at text default to_char(now() at time zone 'utc','YYYY-MM-DD HH24:MI:SS'));
create table if not exists product_images(id serial primary key, product_id integer not null references products(id) on delete cascade, path text not null, position integer default 0);
create table if not exists tags(id serial primary key, name text unique not null, slug text unique not null);
create table if not exists product_tags(product_id integer references products(id) on delete cascade, tag_id integer references tags(id) on delete cascade, primary key(product_id, tag_id));
create table if not exists home_sections(id serial primary key, type text not null, title text default '', subtitle text default '', body text default '', image text default '', button_text text default '', button_link text default '', bg_color text default '', text_color text default '', cat_ids text default '', prod_ids text default '', zone text default 'gallery', limit_n integer default 4, position integer default 0, visible integer default 1);
create table if not exists banners(id serial primary key, title text default '', subtitle text default '', image text default '', link text default '', zone text default 'gallery', active integer default 1, position integer default 0);
create table if not exists settings(key text primary key, value text default '');
"""

_pool = None
def _connect():
    """Conexão do pool (Supabase/PostgreSQL). Autocommit: cada comando é confirmado na hora."""
    global _pool
    if _pool is None:
        if not DATABASE_URL: raise RuntimeError('Defina a variável de ambiente DATABASE_URL (string de conexão do Supabase).')
        _pool = psycopg2.pool.ThreadedConnectionPool(1, 8, DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor, sslmode='require', keepalives=1, keepalives_idle=30)
    c = _pool.getconn()
    try: c.autocommit = True; c.cursor().execute('select 1')
    except Exception:
        _pool.putconn(c, close=True); c = _pool.getconn(); c.autocommit = True
    return c

_NOID = ('into product_tags', 'into settings')
def _exec(cur, sql, args=()):
    """Traduz o SQL escrito no estilo SQLite (?, insert or ignore, lastrowid) para PostgreSQL."""
    s = sql.replace('?', '%s')
    if 'insert or ignore' in s: s = s.replace('insert or ignore', 'insert') + ' on conflict do nothing'
    low = s.lower().lstrip()
    ret = low.startswith('insert') and 'on conflict' not in low and not any(t in low for t in _NOID)
    cur.execute(s + (' returning id' if ret else ''), args)
    return cur.fetchone()[0] if ret else None

def get_db():
    if 'db' not in g: g.db = _connect()
    return g.db

def close_db(e=None):
    d = g.pop('db', None)
    if d: _pool.putconn(d)

def q(sql, args=(), one=False):
    cur = get_db().cursor(); _exec(cur, sql, args); r = cur.fetchall(); cur.close()
    return (r[0] if r else None) if one else r

def ex(sql, args=()):
    cur = get_db().cursor(); n = _exec(cur, sql, args); cur.close(); return n

class _Res:
    def __init__(s, cur, n): s.cur, s.lastrowid = cur, n
    def fetchone(s): return s.cur.fetchone()
class _Shim:
    """Conexão exclusiva para init_db (transação única + lock para evitar seed duplicado)."""
    def __init__(s):
        s.conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor, sslmode='require'); s.cur = s.conn.cursor(); s.cur.execute('select pg_advisory_xact_lock(42)')
    def executescript(s, sql): s.cur.execute(sql)
    def execute(s, sql, args=()): return _Res(s.cur, _exec(s.cur, sql, args))
    def commit(s): s.conn.commit()
    def close(s): s.conn.close()

def slugify(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-') or 'item'

def unique_slug(table, base, ignore=None):
    base = slugify(base); s, i = base, 2
    while q(f'select id from {table} where slug=? and id!=?', (s, ignore or 0), one=True):
        s = f'{base}-{i}'; i += 1
    return s

DEFAULT_SETTINGS = dict(
    store_name='Silver Empire', tagline='Joias de prata com presença, elegância e exclusividade.', logo='', favicon='',
    color_primary='#0e0e10', color_accent='#a9adb4', color_bg='#fafafa', color_text='#1a1a1c', color_muted='#6b6e75',
    font_heading='Cormorant Garamond', font_body='Inter', base_size='16', btn_style='solid', radius='2', shadow='soft',
    header_sticky='1', header_style='light', footer_style='dark', footer_text='© Silver Empire. Todos os direitos reservados.',
    interest_label='Tenho interesse', interest_url='https://wa.me/?text=Tenho%20interesse%20em%20{name}%20({sku})',
    about_text='A Silver Empire nasce da paixão pela prata como matéria de presença. Cada peça é desenhada para atravessar o tempo: linhas limpas, acabamento impecável e um brilho discreto que fala por si.',
    site_title='Silver Empire — Joias de prata', site_description='Joias de prata com presença, elegância e exclusividade.', og_image='')

def init_db(email, password):
    from werkzeug.security import generate_password_hash
    c = _Shim(); c.executescript(SCHEMA)
    if c.execute('select count(*) from users').fetchone()[0]:
        c.commit(); c.close(); return
    c.execute('insert into users(email,password_hash) values(?,?)', (email, generate_password_hash(password)))
    for k, v in DEFAULT_SETTINGS.items(): c.execute('insert into settings values(?,?)', (k, v))
    cats = [('Anéis', 'ring1', 'Presença em cada gesto.'), ('Colares', 'necklace1', 'Delicadeza que ilumina.'),
            ('Correntes', 'chain1', 'Elos de alto impacto.'), ('Pulseiras', 'bracelet1', 'Prata que abraça.')]
    for i, (n, img, d) in enumerate(cats):
        c.execute('insert into categories(name,slug,description,image,featured_image,position) values(?,?,?,?,?,?)', (n, slugify(n), d, 'ph:' + img, 'ph:' + img, i))
    P = [('Anel Imperial', 1, 489, None, 'ring1', 1, 'Anel de prata 925 com gema central lapidada.', 'aro 14–26', '8 g'),
         ('Anel Crown', 1, 359, 299, 'ring2', 0, 'Coroa minimalista em relevo polido.', 'aro 12–24', '6 g'),
         ('Anel Meridian', 1, 329, None, 'ring3', 0, 'Aro largo escovado, acabamento acetinado.', 'aro 14–26', '7 g'),
         ('Colar Élite', 2, 690, None, 'necklace1', 1, 'Colar com pingente solitário e fecho seguro.', '45 cm', '12 g'),
         ('Colar Aurora', 2, 540, None, 'necklace2', 0, 'Fio delicado com pingente em gota.', '42 cm', '9 g'),
         ('Corrente Sovereign', 3, 780, None, 'chain1', 1, 'Elos grossos polidos, presença marcante.', '55 cm', '38 g'),
         ('Corrente Empire', 3, 890, None, 'chain2', 1, 'Malha cubana de prata maciça.', '60 cm', '52 g'),
         ('Corrente Fina Argent', 3, 320, 279, 'chain3', 0, 'Corrente veneziana fina para uso diário.', '45 cm', '5 g'),
         ('Pulseira Argent', 4, 520, None, 'bracelet1', 1, 'Pulseira rígida com acabamento espelhado.', '18 cm', '22 g'),
         ('Pulseira Lumière', 4, 430, 379, 'bracelet2', 0, 'Elos articulados com brilho suave.', '19 cm', '18 g')]
    for i, (n, cat, pr, sp, img, ft, d, sz, w) in enumerate(P):
        cur = c.execute('insert into products(name,slug,sku,price,sale_price,short_desc,description,category_id,material,weight,size,featured,extra,position) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (n, slugify(n), f'SE-{100+i}', pr, sp, d, d + ' Peça em prata 925 com banho de ródio, entregue em embalagem premium.', cat, 'Prata 925', w, sz, ft, 'Acabamento: Ródio\nGarantia: 1 ano', i))
        for j, im in enumerate([img, img + 'b']): c.execute('insert into product_images(product_id,path,position) values(?,?,?)', (cur.lastrowid, 'ph:' + im, j))
        for t in ['prata 925', 'unissex' if i % 2 else 'feminino']:
            c.execute('insert or ignore into tags(name,slug) values(?,?)', (t, slugify(t)))
            c.execute('insert into product_tags select ?,id from tags where name=?', (cur.lastrowid, t))
    S = [('hero', 'Prata com presença', 'Joias desenhadas para quem entende de exclusividade.', 'ph:hero1', 'Ver coleção', '/produtos', '', '', '', ''),
         ('categories', 'Categorias', 'Explore por estilo', '', '', '', '', '', '', ''),
         ('featured', 'Em destaque', 'Nossas peças mais desejadas', '', 'Ver todos', '/produtos?sort=featured', '', '', '', ''),
         ('promo', 'Coleção Sovereign', 'Elos robustos, acabamento espelhado.', 'ph:banner1', 'Descobrir', '/categoria/correntes', '', '', '', ''),
         ('text', 'O império da prata', 'Feita para durar', '', '', '', '', '', '', ''),
         ('new', 'Novidades', 'Chegaram agora', '', 'Ver novidades', '/produtos?sort=recent', '', '', '', '')]
    for i, s in enumerate(S):
        c.execute('insert into home_sections(type,title,subtitle,image,button_text,button_link,position,body) values(?,?,?,?,?,?,?,?)', s[:6] + (i, DEFAULT_SETTINGS['about_text'] if s[0] == 'text' else ''))
    c.commit(); c.close()
