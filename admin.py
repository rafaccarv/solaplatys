"""Blueprint do painel /admin: auth, CSRF, CRUD genérico, reordenação e configurações."""
import secrets, time
from functools import wraps
from flask import Blueprint, render_template, request, session, redirect, flash, abort, jsonify, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import services as sv
from db import q, ex, unique_slug
from config_admin import RES, SETTINGS, PRESETS
bp = Blueprint('adm', __name__, url_prefix='/admin')
_fails = {}

def csrf():
    if '_csrf' not in session: session['_csrf'] = secrets.token_hex(16)
    return session['_csrf']
@bp.before_request
def guard():
    if request.method == 'POST' and not secrets.compare_digest(request.form.get('_csrf') or request.headers.get('X-CSRF') or '', session.get('_csrf', 'x')): abort(400)
    if request.endpoint != 'adm.login' and not (session.get('uid') and q('select 1 from users where id=?', (session['uid'],), one=True)):
        session.clear(); return redirect(url_for('adm.login'))
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        ip = request.remote_addr; n, t = _fails.get(ip, (0, 0))
        if n >= 5 and time.time() - t < 300: flash('Muitas tentativas. Aguarde alguns minutos.', 'error')
        else:
            u = q('select * from users where email=?', (request.form.get('email', '').strip().lower(),), one=True)
            if u and check_password_hash(u['password_hash'], request.form.get('password', '')):
                _fails.pop(ip, None); session.clear(); session['uid'] = u['id']; csrf(); return redirect(url_for('adm.dashboard'))
            _fails[ip] = (n + 1, time.time()); flash('E-mail ou senha inválidos.', 'error')
    return render_template('admin/login.html')
@bp.route('/logout', methods=['POST'])
def logout(): session.clear(); return redirect('/')
@bp.route('/')
def dashboard():
    c = lambda s: q(s, one=True)[0]
    stats = dict(products=c('select count(*) from products'), categories=c('select count(*) from categories'), active=c('select count(*) from products where active=1'), featured=c('select count(*) from products where featured=1'))
    recent = q("select 'products' res,id,name,updated_at from products union all select 'categories',id,name,updated_at from categories order by updated_at desc limit 8")
    return render_template('admin/dashboard.html', stats=stats, recent=recent)

def _opts(o):
    if o == 'categories': return [(str(r['id']), r['name']) for r in q('select id,name from categories order by position')]
    if o == 'products': return [(str(r['id']), r['name']) for r in q('select id,name from products order by name')]
    return o
def _prep(fields, obj):
    out = []
    for f in fields:
        f = dict(f)
        if f['t'] in ('select', 'multi'):
            f['options'] = _opts(f['opts'])
            if f['t'] == 'select' and f['n'] == 'category_id': f['options'] = [('', '— Sem categoria —')] + f['options']
            if f['t'] == 'multi':
                sel = [str(i) for i in sv.ids(obj.get(f['n']))]; d = dict(f['options'])
                f['options'] = [(i, d[i]) for i in sel if i in d] + [o for o in f['options'] if o[0] not in sel]; f['sel'] = sel
        out.append(f)
    return out
def _cfg(res): return RES.get(res) or abort(404)

@bp.route('/<res>')
def listing(res):
    cfg = _cfg(res)
    rows = q(f'select * from {cfg["table"]} order by ' + ('position,id' if cfg['sortable'] else 'id desc'))
    return render_template('admin/list.html', res=res, cfg=cfg, rows=rows)
@bp.route('/<res>/new', methods=['GET', 'POST'])
@bp.route('/<res>/<int:id>', methods=['GET', 'POST'])
def edit(res, id=None):
    cfg = _cfg(res); row = q(f'select * from {cfg["table"]} where id=?', (id,), one=True) if id else None
    if id and not row: abort(404)
    if request.method == 'POST':
        rid = _save(res, cfg, id, row)
        if rid: return redirect(url_for('adm.edit', res=res, id=rid) if request.form.get('stay') else url_for('adm.listing', res=res))
    obj = dict(row) if row else dict(cfg['defaults'])
    if request.method == 'POST': obj.update(request.form.to_dict())
    extra = {}
    if res == 'products' and id: extra = dict(images=sv.gallery(id), tags=', '.join(t['name'] for t in sv.tags_of(id)))
    if res == 'categories' and id: extra = dict(cat_products=sv.list_products('p.category_id=?', (id,)))
    return render_template('admin/form.html', res=res, cfg=cfg, obj=obj, id=id, fields=_prep(cfg['fields'], obj), **extra)
def _save(res, cfg, id, row):
    v = {}
    for f in cfg['fields']:
        n, t = f['n'], f['t']
        if t == 'image':
            try: new = sv.save_image(request.files.get(n))
            except ValueError as e: flash(str(e), 'error'); return None
            v[n] = new or ('' if request.form.get(n + '_remove') else request.form.get(n + '_cur', ''))
        elif t == 'check': v[n] = 1 if request.form.get(n) else 0
        elif t == 'multi': v[n] = ','.join(request.form.getlist(n))
        elif t == 'number':
            s = request.form.get(n, '').strip().replace(',', '.')
            try: v[n] = float(s) if s else None
            except ValueError: flash(f'Valor inválido em "{f["l"]}".', 'error'); return None
            if f['n'] == 'limit_n' and v[n]: v[n] = int(v[n])
        elif t == 'password':
            s = request.form.get(n, '')
            if s and len(s) < 8 or (not s and not id): flash('A senha deve ter ao menos 8 caracteres.', 'error'); return None
            if s: v['password_hash'] = generate_password_hash(s)
        else: v[n] = request.form.get(n, '').strip()
        if f.get('req') and not v.get(n): flash(f'Preencha "{f["l"]}".', 'error'); return None
    v.pop('password', None)
    if v.get('category_id') == '': v['category_id'] = None
    if res == 'users':
        v['email'] = v['email'].lower()
        if q('select 1 from users where email=? and id!=?', (v['email'], id or 0), one=True): flash('E-mail já cadastrado.', 'error'); return None
    if 'slug' in v or res in ('categories', 'products'): v['slug'] = unique_slug(cfg['table'], v.get('slug') or v.get('name'), id)
    if res in ('products', 'categories'): v['updated_at'] = __import__('datetime').datetime.utcnow().isoformat(sep=' ', timespec='seconds')
    if id: ex(f'update {cfg["table"]} set ' + ','.join(f'{k}=?' for k in v) + ' where id=?', (*v.values(), id)); rid = id
    else:
        if cfg['sortable'] or res == 'products': v['position'] = q(f'select coalesce(max(position),0)+1 from {cfg["table"]}', one=True)[0]
        rid = ex(f'insert into {cfg["table"]}({",".join(v)}) values({",".join("?"*len(v))})', tuple(v.values()))
    if res == 'products': _product_extras(rid)
    flash(f'{cfg["one"]} salvo(a) com sucesso.', 'success'); return rid
def _product_extras(pid):
    sv.set_tags(pid, request.form.get('tags', ''))
    keep = request.form.getlist('img_id'); dele = set(request.form.getlist('img_del'))
    for pos, i in enumerate(keep):
        if i in dele: ex('delete from product_images where id=? and product_id=?', (i, pid))
        else: ex('update product_images set position=? where id=? and product_id=?', (pos, i, pid))
    base = q('select coalesce(max(position),-1)+1 from product_images where product_id=?', (pid,), one=True)[0]
    for k, f in enumerate(request.files.getlist('gallery')):
        try:
            p = sv.save_image(f)
            if p: ex('insert into product_images(product_id,path,position) values(?,?,?)', (pid, p, base + k))
        except ValueError as e: flash(str(e), 'error')
@bp.route('/<res>/<int:id>/delete', methods=['POST'])
def delete(res, id):
    cfg = _cfg(res)
    if res == 'users' and (id == session['uid'] or q('select count(*) from users', one=True)[0] < 2): flash('Não é possível excluir este usuário.', 'error'); return redirect(url_for('adm.listing', res=res))
    if res == 'categories':
        n = q('select count(*) from products where category_id=?', (id,), one=True)[0]
        if n: flash(f'{n} produto(s) desta categoria ficaram sem categoria.', 'info')
    ex(f'delete from {cfg["table"]} where id=?', (id,)); flash(f'{cfg["one"]} excluído(a).', 'success')
    return redirect(url_for('adm.listing', res=res))
@bp.route('/reorder/<res>', methods=['POST'])
def reorder(res):
    if res not in ('categories', 'products', 'home_sections', 'banners'): abort(404)
    for pos, i in enumerate((request.get_json(silent=True) or {}).get('ids', [])): ex(f'update {RES[res]["table"]} set position=? where id=?', (pos, int(i)))
    return jsonify(ok=True)
@bp.route('/toggle/<res>/<int:id>/<field>', methods=['POST'])
def toggle(res, id, field):
    if field not in ('visible', 'active', 'featured') or res not in RES: abort(404)
    ex(f'update {RES[res]["table"]} set {field}=1-{field} where id=?', (id,)); return jsonify(ok=True)
@bp.route('/config/<group>', methods=['GET', 'POST'])
def config(group):
    title, fields = SETTINGS.get(group) or abort(404)
    if request.method == 'POST':
        for f in fields:
            n = f['n']
            if f['t'] == 'image':
                try: new = sv.save_image(request.files.get(n))
                except ValueError as e: flash(str(e), 'error'); return redirect(request.url)
                sv.set_setting(n, new or ('' if request.form.get(n + '_remove') else request.form.get(n + '_cur', '')))
            else: sv.set_setting(n, request.form.get(n, '').strip())
        flash('Configurações publicadas.', 'success'); return redirect(request.url)
    S = sv.get_settings()
    return render_template('admin/form.html', res=None, cfg=dict(title=title), obj=dict(S), id=None, fields=_prep(fields, S), group=group, presets=PRESETS)
