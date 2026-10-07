"""Silver Empire — vitrine + painel admin. Execute: python app.py"""
import os, secrets
from flask import Flask, render_template, session
import db, services as sv, admin, public
from config_admin import RES, FONTS

def create_app():
    app = Flask(__name__)
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)  # Render fica atrás de proxy HTTPS
    kf = os.path.join(db.BASE, 'data', 'secret.key')
    os.makedirs(os.path.dirname(kf), exist_ok=True)
    if not os.environ.get('SECRET_KEY') and not os.path.exists(kf): open(kf, 'w').write(secrets.token_hex(32))
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY') or open(kf).read(), MAX_CONTENT_LENGTH=40 * 1024 * 1024, SESSION_COOKIE_HTTPONLY=True,
                      SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=bool(os.environ.get('PRODUCTION')), SEND_FILE_MAX_AGE_DEFAULT=604800)
    os.makedirs(os.path.join(db.BASE, 'static', 'uploads'), exist_ok=True)
    db.init_db(os.environ.get('ADMIN_EMAIL', 'admin@silverempire.com'), os.environ.get('ADMIN_PASSWORD', 'silver12345'))
    app.teardown_appcontext(db.close_db)
    app.register_blueprint(public.bp); app.register_blueprint(admin.bp)
    app.jinja_env.globals.update(img=sv.img, money=sv.money, tags_of=sv.tags_of, extra_lines=sv.extra_lines, badge=sv.badge, csrf=admin.csrf, RES=RES, ids=sv.ids)
    @app.context_processor
    def ctx():
        S = sv.get_settings(); fam = '&family='.join(f.replace(' ', '+') + ':wght@300;400;500;600' for f in {S['font_heading'], S['font_body']})
        return dict(S=S, fonts_url=f'https://fonts.googleapis.com/css2?family={fam}&display=swap', nav_cats=db.q('select name,slug from categories where visible=1 order by position'), is_admin=bool(session.get('uid')))
    @app.after_request
    def sec(r):
        r.headers.update({'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'SAMEORIGIN', 'Referrer-Policy': 'same-origin'}); return r
    @app.errorhandler(404)
    def nf(e): return render_template('404.html'), 404
    return app

app = create_app()
if __name__ == '__main__':
    app.run(debug=bool(os.environ.get('DEBUG')), host='127.0.0.1', port=int(os.environ.get('PORT', 5000)))
