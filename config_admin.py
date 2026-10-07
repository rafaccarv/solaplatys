"""Definição declarativa dos recursos do admin. Para adicionar um campo novo: (1) coluna no schema (db.py) e (2) uma linha F(...) aqui."""
def F(n, l, t='text', **k): return dict(n=n, l=l, t=t, **k)
AVAIL = [('disponivel', 'Disponível'), ('sob_encomenda', 'Sob encomenda'), ('indisponivel', 'Indisponível')]
SEC_TYPES = [('hero', 'Hero principal'), ('banner', 'Banner / carrossel'), ('categories', 'Categorias'), ('featured', 'Produtos em destaque'),
             ('new', 'Produtos mais recentes'), ('collection', 'Coleção (produtos escolhidos)'), ('promo', 'Banner promocional'), ('text', 'Texto institucional'), ('gallery', 'Galeria de imagens')]
SEO = dict(grp='SEO')
RES = {
 'products': dict(table='products', title='Produtos', one='Produto', sortable=False, cols=['name', 'sku', 'price'], defaults=dict(active=1), fields=[
    F('name', 'Nome', req=1), F('sku', 'Código / SKU'), F('price', 'Preço (R$)', 'number'), F('sale_price', 'Preço promocional (R$)', 'number'),
    F('category_id', 'Categoria', 'select', opts='categories'), F('subcategory', 'Subcategoria'),
    F('short_desc', 'Descrição curta', 'textarea'), F('description', 'Descrição completa', 'textarea'),
    F('material', 'Material'), F('weight', 'Peso'), F('size', 'Tamanho'), F('availability', 'Disponibilidade', 'select', opts=AVAIL),
    F('badge', 'Selo personalizado (ex.: Novo, Edição limitada)'), F('featured', 'Produto em destaque', 'check'), F('active', 'Ativo', 'check'),
    F('extra', 'Informações adicionais (uma por linha: Chave: valor)', 'textarea'), F('custom_text', 'Texto personalizado', 'textarea'),
    F('slug', 'Slug / URL', **SEO), F('meta_title', 'Meta title', **SEO), F('meta_description', 'Meta description', 'textarea', **SEO), F('og_image', 'Imagem de compartilhamento (Open Graph)', 'image', **SEO)]),
 'categories': dict(table='categories', title='Categorias', one='Categoria', sortable=True, cols=['name', 'slug'], defaults=dict(visible=1), fields=[
    F('name', 'Nome', req=1), F('slug', 'Slug / URL'), F('description', 'Descrição', 'textarea'), F('image', 'Imagem / capa', 'image'),
    F('featured_image', 'Imagem de destaque', 'image'), F('visible', 'Visível no site', 'check'),
    F('meta_title', 'Meta title', **SEO), F('meta_description', 'Meta description', 'textarea', **SEO)]),
 'home_sections': dict(table='home_sections', title='Página inicial', one='Seção', sortable=True, cols=['type', 'title'], defaults=dict(visible=1, limit_n=4, zone='gallery'), fields=[
    F('type', 'Tipo de seção', 'select', opts=SEC_TYPES, req=1), F('title', 'Título'), F('subtitle', 'Subtítulo'),
    F('body', 'Texto', 'textarea', show=['text']), F('image', 'Imagem', 'image', show=['hero', 'promo']),
    F('button_text', 'Texto do botão', show=['hero', 'promo', 'featured', 'new', 'collection', 'categories']), F('button_link', 'Link do botão', show=['hero', 'promo', 'featured', 'new', 'collection', 'categories']),
    F('bg_color', 'Cor de fundo', 'color'), F('text_color', 'Cor do texto', 'color'),
    F('cat_ids', 'Categorias exibidas (arraste para ordenar; vazio = todas)', 'multi', opts='categories', show=['categories']),
    F('prod_ids', 'Produtos exibidos (arraste para ordenar)', 'multi', opts='products', show=['collection', 'featured', 'new']),
    F('zone', 'Zona de banners', show=['banner', 'gallery']), F('limit_n', 'Quantidade de itens', 'number', show=['featured', 'new', 'collection']),
    F('visible', 'Visível', 'check')]),
 'banners': dict(table='banners', title='Banners', one='Banner', sortable=True, cols=['title', 'zone'], defaults=dict(active=1, zone='gallery'), fields=[
    F('title', 'Título'), F('subtitle', 'Subtítulo'), F('image', 'Imagem', 'image'), F('link', 'Link'), F('zone', 'Zona (agrupa banners; usada nas seções)'), F('active', 'Ativo', 'check')]),
 'users': dict(table='users', title='Usuários', one='Usuário', sortable=False, cols=['email', 'created_at'], defaults={}, fields=[
    F('email', 'E-mail', req=1), F('password', 'Senha (mín. 8 caracteres; vazio = manter)', 'password')]),
}
FONTS = ['Cormorant Garamond', 'Playfair Display', 'Cinzel', 'Inter', 'Montserrat', 'Jost', 'Manrope']
opts = lambda l: [(x, x) for x in l]
YN = [('1', 'Sim'), ('0', 'Não')]
SETTINGS = {
 'general': ('Configurações', [F('store_name', 'Nome da loja'), F('tagline', 'Slogan'), F('footer_text', 'Texto do rodapé', 'textarea'),
    F('interest_label', 'Texto do botão de interesse'), F('interest_url', 'Link do botão (use {name} e {sku}; ex.: https://wa.me/5519999999999?text=...)'), F('about_text', 'Texto "Sobre"', 'textarea')]),
 'appearance': ('Aparência', [F('logo', 'Logo', 'image'), F('favicon', 'Favicon', 'image'),
    F('color_primary', 'Cor principal', 'color', var='--primary'), F('color_accent', 'Cor secundária (prata)', 'color', var='--accent'), F('color_bg', 'Cor de fundo', 'color', var='--bg'),
    F('color_text', 'Cor do texto', 'color', var='--text'), F('color_muted', 'Cor de texto suave', 'color', var='--muted'),
    F('font_heading', 'Fonte dos títulos', 'select', opts=opts(FONTS)), F('font_body', 'Fonte do texto', 'select', opts=opts(FONTS)),
    F('base_size', 'Tamanho base do texto (px)', 'number', var='--fs'), F('btn_style', 'Estilo dos botões', 'select', opts=[('solid', 'Sólido'), ('outline', 'Contorno')]),
    F('radius', 'Border radius (px)', 'number', var='--radius'), F('shadow', 'Sombras', 'select', opts=[('none', 'Nenhuma'), ('soft', 'Suave'), ('strong', 'Marcante')]),
    F('header_sticky', 'Header fixo', 'select', opts=YN), F('header_style', 'Header', 'select', opts=[('light', 'Claro'), ('dark', 'Escuro')]),
    F('footer_style', 'Footer', 'select', opts=[('dark', 'Escuro'), ('light', 'Claro')])]),
 'seo': ('SEO', [F('site_title', 'Título padrão do site'), F('site_description', 'Descrição padrão', 'textarea'), F('og_image', 'Imagem de compartilhamento padrão', 'image')]),
}
PRESETS = {'Prata clássica': dict(color_primary='#0e0e10', color_accent='#a9adb4', color_bg='#fafafa', color_text='#1a1a1c', color_muted='#6b6e75'),
           'Grafite': dict(color_primary='#2b2d31', color_accent='#c5c8ce', color_bg='#f3f3f4', color_text='#232427', color_muted='#70737a'),
           'Noite': dict(color_primary='#f2f2f3', color_accent='#9a9ea6', color_bg='#0f0f11', color_text='#ececee', color_muted='#8b8e95'),
           'Branco puro': dict(color_primary='#111111', color_accent='#b8bbc0', color_bg='#ffffff', color_text='#111111', color_muted='#777777')}
