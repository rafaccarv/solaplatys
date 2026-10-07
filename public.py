from flask import Blueprint, render_template, request, abort, jsonify, Response, redirect
import services as sv
from db import q
bp = Blueprint('pub', __name__)

def _facets():
    return dict(cats=q('select * from categories where visible=1 order by position'), tags=q('select distinct t.* from tags t join product_tags pt on pt.tag_id=t.id join products p on p.id=pt.product_id and p.active=1 order by t.name'))
def _listing(title, cat=None):
    a = request.args; rows = sv.filter_products(a, cat)
    tpl = '_grid.html' if request.headers.get('X-Requested-With') == 'fetch' else 'products.html'
    return render_template(tpl, products=rows, title=title, cat=cat, a=a, **_facets())

@bp.route('/')
def home(): return render_template('home.html', blocks=sv.home_blocks())
@bp.route('/categorias')
def categories():
    cats = [dict(c, products=sv.list_products('p.active=1 and p.category_id=?', (c['id'],), limit=4)) for c in q('select * from categories where visible=1 order by position,id')]
    return render_template('categories.html', cats=cats)
@bp.route('/categoria/<slug>')
def category(slug):
    c = q('select * from categories where slug=? and visible=1', (slug,), one=True) or abort(404)
    return _listing(c['name'], c)
@bp.route('/produtos')
def products(): return _listing('Produtos')
@bp.route('/novidades')
def news(): return redirect('/produtos?sort=recent')
@bp.route('/sobre')
def about(): return render_template('about.html')
@bp.route('/produto/<slug>')
def product(slug):
    p = q(sv.PSEL + 'where p.slug=? and p.active=1', (slug,), one=True) or abort(404)
    rel = sv.list_products('p.active=1 and p.id!=? and p.category_id is not distinct from ?', (p['id'], p['category_id']), limit=4)
    return render_template('product.html', p=p, images=sv.gallery(p['id']), tags=sv.tags_of(p['id']), related=rel)
@bp.route('/busca')
def busca():
    s = request.args.get('q', '').strip()
    return render_template('search.html', s=s, products=sv.search(s) if s else [])
@bp.route('/api/search')
def api_search():
    s = request.args.get('q', '').strip()
    if len(s) < 2: return jsonify([])
    return jsonify([dict(name=p['name'], url=f'/produto/{p["slug"]}', price=sv.money(p['sale_price'] or p['price']), cat=p['cat_name'] or '', img=sv.img(p['image'])) for p in sv.search(s, 6)])
@bp.route('/ph/<name>.svg')
def ph(name): return Response(sv.placeholder(name), mimetype='image/svg+xml', headers={'Cache-Control': 'public,max-age=604800'})
@bp.route('/sitemap.xml')
def sitemap():
    u = ['/', '/produtos', '/categorias', '/sobre'] + [f'/categoria/{c["slug"]}' for c in q('select slug from categories where visible=1')] + [f'/produto/{p["slug"]}' for p in q('select slug from products where active=1')]
    return Response('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{request.host_url.rstrip("/")}{x}</loc></url>' for x in u) + '</urlset>', mimetype='application/xml')
