# Silver Empire — vitrine de joias de prata (Flask + SQLite)

## Executar
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py                                          # http://127.0.0.1:5000
```
Admin: **/admin** — usuário inicial `admin@silverempire.com` / senha `silver12345` (**troque em Admin → Usuários**).
Para definir outro no primeiro start: `ADMIN_EMAIL=... ADMIN_PASSWORD=... python app.py`. Em produção use `PRODUCTION=1` (cookie Secure), HTTPS e `gunicorn app:app`.
O banco `data/silver.db` é criado e populado (10 produtos, 4 categorias, home montada) no primeiro start. Apague o arquivo para recomeçar.

## Estrutura
- `db.py` schema SQLite + seed · `services.py` consultas/regras/imagens · `public.py` site · `admin.py` painel · `config_admin.py` **definição dos formulários do admin**
- `templates/` (públicos) e `templates/admin/` · `static/css|js` · `static/uploads` (imagens otimizadas em WebP)

## Como customizar
- **Novo campo de produto**: adicione a coluna em `db.py` (e `alter table products add column ...` no banco existente) + uma linha `F(...)` em `config_admin.py` → já aparece no admin; exiba no template. Há também "Informações adicionais" (Chave: valor) sem precisar de código.
- **Novo tipo de seção da home**: adicione em `SEC_TYPES`, resolva dados em `services.home_blocks()` e um bloco em `templates/home.html`.
- **Novo filtro**: um `if` em `services.filter_products` + um campo em `templates/products.html`.
- **Botão "Tenho interesse"**: Admin → Configurações (link com `{name}` e `{sku}`; ex.: WhatsApp).

## Segurança implementada
Senhas com hash (PBKDF2/werkzeug), sessão HttpOnly/SameSite, CSRF em todos os POST, rotas `/admin` protegidas no backend, limite de tentativas de login, uploads validados (extensão + decodificação real com Pillow, reencodados em WebP, nome aleatório, SVG bloqueado), consultas parametrizadas, autoescape do Jinja.

## Preparado para o futuro (não implementado)
Carrinho, pedidos, clientes, cupons, frete, estoque, pagamentos: adicionar tabelas (`orders`, `customers`, ...) em `db.py`, um blueprint novo por domínio (`cart.py`, `checkout.py`) e um `services/payments/` por gateway. Produtos já têm SKU, preço, promoção e disponibilidade; `interest_url` pode virar checkout.
