#!/usr/bin/env python3
"""DramaPick v2 builder: 4-language static site, remote covers,
hook-driven show pages, FAQ + JSON-LD, hreflang, one sitemap."""
import json, os, re, html, shutil

BASE = os.path.dirname(os.path.abspath(__file__))
DOMAIN = 'https://drama.jinbufenzi.com'
LANGS = ['en', 'es', 'pt', 'id']
PREFIX = {'en': '', 'es': 'es/', 'pt': 'pt/', 'id': 'id/'}
HTMLL = {'en': 'en', 'es': 'es', 'pt': 'pt', 'id': 'id'}

def load(name):
    with open(os.path.join(BASE, name), encoding='utf-8') as f:
        return json.load(f)

SHOWS = load('shows-final.json')
UI = load('ui_i18n.json')
META = load('meta_i18n.json')
FB = load('faq_beats_i18n.json')
HK = {l: load('hooks_%s.json' % l) for l in LANGS}
PLAT_NAME = {'dramabox': 'DramaBox', 'reelshort': 'ReelShort',
             'netshort': 'NetShort', 'sagabox': 'SAGABOX',
             'stardusttv': 'StardustTV', 'topshort': 'TopShort'}
TROPE_OF = {'Billionaire Romance': 'billionaire',
            'Werewolf Romance': 'werewolf',
            'Revenge & Comeback': 'revenge',
            'Secret Identity': 'secret-identity',
            'Contract Marriage': 'contract-marriage',
            'Fantasy & Powers': 'fantasy',
            'Mafia & Danger': 'mafia',
            'Rebirth & Second Chance': 'rebirth'}
TROPES = list(META['tropes'].keys())

def esc(s):
    return html.escape(s, quote=True)

def tropes_of(show):
    out = []
    for g in show['genres']:
        t = TROPE_OF.get(g)
        if t and t not in out:
            out.append(t)
    return out

def hook_of(lang, show):
    e = HK[lang][show['slug']]
    return e if isinstance(e, str) else e['h']

def setup_of(lang, show):
    if lang == 'en':
        return show['premise']
    return HK[lang][show['slug']]['s']

def beats_of(lang, show):
    out = []
    for g in show['genres']:
        for b in FB['beats'][lang].get(g, []):
            if b not in out:
                out.append(b)
        if len(out) >= 4:
            break
    return out[:4]

def rel_shows(show, n=4):
    scored = []
    for s in SHOWS:
        if s['slug'] == show['slug']:
            continue
        score = len(set(s['genres']) & set(show['genres']))
        if s['source'] == show['source']:
            score += 1
        scored.append((score, s))
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:n]]

CSS = """
:root{--bg:#0d0d12;--card:#17171f;--ink:#f2f0ea;--dim:#a7a5ad;--acc:#ff4d6d;--acc2:#ffb347}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font-family:system-ui,-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;line-height:1.55}
a{color:var(--acc2);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:1060px;margin:0 auto;padding:0 16px}
header{border-bottom:1px solid #26262f;padding:14px 0}
header .wrap{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.logo{font-weight:800;font-size:22px;color:var(--ink)}.logo span{color:var(--acc)}
nav.langs a{color:var(--dim);margin-left:10px;font-size:14px}
nav.langs a.on{color:var(--ink);font-weight:700}
.hero{padding:34px 0 8px}.hero h1{font-size:32px;line-height:1.2;margin:0 0 10px}
.hero p{color:var(--dim);max-width:640px}
h2{font-size:21px;margin:30px 0 12px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px}
.card{background:var(--card);border-radius:12px;overflow:hidden}
.card img{width:100%;aspect-ratio:3/4;object-fit:cover;display:block}
.card .t{padding:9px 10px;font-size:14px;font-weight:600;color:var(--ink)}
.card .p{padding:0 10px 10px;font-size:12px;color:var(--dim)}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
.chip{background:#22222c;border-radius:999px;padding:5px 12px;font-size:13px;color:var(--ink)}
.btn{display:inline-block;background:var(--acc);color:#fff;font-weight:700;
padding:13px 26px;border-radius:10px;font-size:17px}
.btn:hover{background:#ff3357;text-decoration:none}
.hookline{font-size:20px;font-weight:700;line-height:1.35;margin:12px 0}
.showhead{display:flex;gap:20px;flex-wrap:wrap;margin-top:18px}
.showhead img{width:230px;border-radius:14px;aspect-ratio:3/4;object-fit:cover}
.showhead .info{flex:1;min-width:260px}
ul.beats{padding-left:20px}ul.beats li{margin:6px 0}
.faq{background:var(--card);border-radius:12px;padding:6px 18px;margin:10px 0}
.faq h3{font-size:16px;margin:14px 0 4px}.faq p{color:var(--dim);margin:0 0 14px}
.disc{color:var(--dim);font-size:13px;margin:22px 0}
footer{border-top:1px solid #26262f;margin-top:40px;padding:20px 0;color:var(--dim);font-size:14px}
footer a{color:var(--dim);margin-right:14px}
.sticky{position:fixed;left:0;right:0;bottom:0;background:rgba(13,13,18,.94);
border-top:1px solid #2c2c38;padding:10px 16px;display:none;z-index:50}
.sticky a{display:block;text-align:center;background:var(--acc);color:#fff;
font-weight:700;padding:12px;border-radius:10px;font-size:16px}
@media(max-width:640px){.sticky{display:block}body{padding-bottom:64px}
.hero h1{font-size:26px}.showhead img{width:160px}}
"""

def alts(path_no_prefix):
    out = []
    for l in LANGS:
        out.append((l, DOMAIN + '/' + PREFIX[l] + path_no_prefix))
    return out

def page(lang, path, title, desc, body, ld=None, og_img=None):
    ui = UI[lang]
    canon = DOMAIN + '/' + PREFIX[lang] + path
    links = ''.join(
        '<link rel="alternate" hreflang="%s" href="%s">' % (l, u)
        for l, u in alts(path))
    links += '<link rel="alternate" hreflang="x-default" href="%s">' % (
        DOMAIN + '/' + path)
    og = ''
    if og_img:
        og = ('<meta property="og:image" content="%s">' % esc(og_img))
    ldtag = ''
    if ld:
        ldtag = ('<script type="application/ld+json">%s</script>'
                 % json.dumps(ld, ensure_ascii=False))
    langnav = ''.join(
        '<a href="%s" class="%s">%s</a>' % (
            DOMAIN + '/' + PREFIX[l] + path,
            'on' if l == lang else '', UI[l]['lang_name'])
        for l in LANGS)
    head = ('<!DOCTYPE html><html lang="%s"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>%s</title><meta name="description" content="%s">'
            '<link rel="canonical" href="%s">%s'
            '<meta property="og:title" content="%s">'
            '<meta property="og:description" content="%s">'
            '<meta property="og:type" content="website">%s%s'
            '<style>%s</style></head>'
            % (HTMLL[lang], esc(title), esc(desc), canon, links,
               esc(title), esc(desc), og, ldtag, CSS))
    header = ('<header><div class="wrap"><a class="logo" href="%s">'
              'Drama<span>Pick</span></a><nav class="langs">%s</nav>'
              '</div></header>'
              % (DOMAIN + '/' + PREFIX[lang], langnav))
    footer = ('<footer><div class="wrap"><a href="%sabout/">%s</a>'
              '<a href="%sprivacy/">%s</a><div>%s</div></div></footer>'
              % (DOMAIN + '/' + PREFIX[lang], ui['about'],
                 DOMAIN + '/' + PREFIX[lang], ui['privacy'],
                 esc(ui['tagline'])))
    return head + '<body>' + header + '<main class="wrap">' + body + \
        '</main>' + footer + '</body></html>'

def card(lang, show):
    ui = UI[lang]
    href = '%s/%sshows/%s/' % (DOMAIN, PREFIX[lang], show['slug'])
    return ('<div class="card"><a href="%s"><img src="%s" alt="%s" '
            'loading="lazy" referrerpolicy="no-referrer">'
            '<div class="t">%s</div><div class="p">%s · %s</div>'
            '</a></div>'
            % (href, esc(show['cover_url']), esc(show['name']),
               esc(show['name']), esc(PLAT_NAME[show['source']]),
               esc(' · '.join(show['genres'][:2]))))

def grid(lang, shows):
    return '<div class="grid">' + ''.join(card(lang, s) for s in shows) \
        + '</div>'

def home_body(lang):
    ui = UI[lang]
    p = PREFIX[lang]
    out = ['<section class="hero"><h1>%s</h1><p>%s</p></section>'
           % (esc(ui['home_h1']), esc(ui['home_sub']))]
    out.append('<h2>%s</h2>' % esc(ui['featured']))
    out.append(grid(lang, SHOWS[:6]))
    tchips = ''.join(
        '<a class="chip" href="%s/%stropes/%s/">%s</a>'
        % (DOMAIN, p, t, esc(META['tropes'][t][lang][0]))
        for t in TROPES)
    out.append('<h2>%s</h2><div class="chips">%s</div>'
               % (esc(ui['by_trope']), tchips))
    for src in PLAT_NAME:
        ss = [s for s in SHOWS if s['source'] == src]
        if not ss:
            continue
        out.append('<h2><a href="%s/%splatforms/%s/">%s</a></h2>'
                   '<p>%s</p>' % (DOMAIN, p, src,
                                  esc(PLAT_NAME[src]),
                                  esc(META['platforms'][lang][src])))
        out.append(grid(lang, ss))
    return ''.join(out)

def watch_btn(lang, show, label=None):
    ui = UI[lang]
    return ('<a class="btn" href="%s" rel="sponsored noopener" '
            'target="_blank">%s</a>'
            % (esc(show['drama_url']), esc(label or ui['watch'])))

def show_body(lang, show):
    ui = UI[lang]
    p = PREFIX[lang]
    plat = PLAT_NAME[show['source']]
    hook = hook_of(lang, show)
    out = []
    crumbs = ('<p><a href="%s/%s">%s</a> / '
              '<a href="%s/%splatforms/%s/">%s</a></p>'
              % (DOMAIN, p, esc(ui['home']), DOMAIN, p, show['source'],
                 esc(plat)))
    out.append(crumbs)
    out.append('<div class="showhead"><img src="%s" alt="%s" '
               'referrerpolicy="no-referrer"><div class="info">'
               '<h1 style="margin:0">%s</h1>'
               '<p class="hookline">%s</p>%s'
               '<p style="color:var(--dim)">%s</p></div></div>'
               % (esc(show['cover_url']), esc(show['name']),
                  esc(show['name']), esc(hook),
                  watch_btn(lang, show,
                            '%s — %s' % (ui['watch'], ui['free_first'])),
                  esc(ui['disclosure'])))
    chips = ['<a class="chip" href="%s/%splatforms/%s/">%s: %s</a>'
             % (DOMAIN, p, show['source'], esc(ui['platform']),
                esc(plat))]
    for t in tropes_of(show):
        chips.append('<a class="chip" href="%s/%stropes/%s/">%s</a>'
                     % (DOMAIN, p, t, esc(META['tropes'][t][lang][0])))
    out.append('<div class="chips">%s</div>' % ''.join(chips))
    out.append('<h2>%s</h2><p>%s</p>'
               % (esc(ui['the_setup']), esc(setup_of(lang, show))))
    bl = ''.join('<li>%s</li>' % esc(b) for b in beats_of(lang, show))
    out.append('<h2>%s</h2><ul class="beats"><li>%s</li>%s</ul>'
               % (esc(ui['why_stick']), esc(hook), bl))
    out.append(watch_btn(lang, show))
    fq = []
    for q, a in FB['faq'][lang]:
        fq.append('<div class="faq"><h3>%s</h3><p>%s</p></div>'
                  % (esc(q.format(name=show['name'], platform=plat)),
                     esc(a.format(name=show['name'], platform=plat,
                                  hook=hook))))
    out.append('<h2>%s</h2>%s' % (esc(ui['faq']), ''.join(fq)))
    out.append('<h2>%s</h2>%s'
               % (esc(ui['more_like']), grid(lang, rel_shows(show))))
    out.append('<div class="sticky"><a href="%s" rel="sponsored noopener" '
               'target="_blank">%s · %s</a></div>'
               % (esc(show['drama_url']), esc(ui['sticky']),
                  esc(show['name'])))
    return ''.join(out)

def show_ld(lang, show):
    plat = PLAT_NAME[show['source']]
    base = DOMAIN + '/' + PREFIX[lang]
    tv = {'@type': 'TVSeries', 'name': show['name'],
          'description': setup_of(lang, show),
          'genre': show['genres'], 'image': show['cover_url']}
    fq = {'@type': 'FAQPage', 'mainEntity': [
        {'@type': 'Question', 'name': q.format(name=show['name'],
                                               platform=plat),
         'acceptedAnswer': {'@type': 'Answer',
                            'text': a.format(name=show['name'],
                                             platform=plat,
                                             hook=hook_of(lang, show))}}
        for q, a in FB['faq'][lang]]}
    bc = {'@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': UI[lang]['home'],
         'item': base},
        {'@type': 'ListItem', 'position': 2, 'name': plat,
         'item': base + 'platforms/%s/' % show['source']},
        {'@type': 'ListItem', 'position': 3, 'name': show['name'],
         'item': base + 'shows/%s/' % show['slug']}]}
    return [dict({'@context': 'https://schema.org'}, **tv),
            dict({'@context': 'https://schema.org'}, **fq),
            dict({'@context': 'https://schema.org'}, **bc)]

ABOUT = {
 'en': ('About DramaPick',
        'DramaPick is a small editorial guide to vertical short dramas. '
        'We track the most talked-about series on DramaBox, ReelShort, '
        'NetShort, SAGABOX, StardustTV and TopShort, write up the setup '
        'and the hook without spoiling endings, and link you straight to '
        'the official app page. Show data and artwork come from the '
        'DramaCPS affiliate program materials. When you watch through '
        'our links we may earn a commission from the platform, at no '
        'extra cost to you.'),
 'es': ('Acerca de DramaPick',
        'DramaPick es una pequeña guía editorial de dramas cortos '
        'verticales. Seguimos las series más comentadas de DramaBox, '
        'ReelShort, NetShort, SAGABOX, StardustTV y TopShort, contamos '
        'la trama y el gancho sin revelar finales, y te enlazamos '
        'directo a la app oficial. Los datos y las imágenes provienen '
        'de los materiales del programa de afiliados de DramaCPS. '
        'Cuando ves a través de nuestros enlaces, podemos ganar una '
        'comisión de la plataforma, sin costo extra para ti.'),
 'pt': ('Sobre o DramaPick',
        'O DramaPick é um pequeno guia editorial de dramas curtos '
        'verticais. Acompanhamos as séries mais comentadas de '
        'DramaBox, ReelShort, NetShort, SAGABOX, StardustTV e '
        'TopShort, contamos a trama e o gancho sem revelar finais e '
        'te ligamos direto ao app oficial. Os dados e as imagens vêm '
        'dos materiais do programa de afiliados da DramaCPS. Quando '
        'você assiste pelos nossos links, podemos ganhar uma comissão '
        'da plataforma, sem custo extra para você.'),
 'id': ('Tentang DramaPick',
        'DramaPick adalah panduan editorial kecil untuk drama pendek '
        'vertikal. Kami mengikuti serial paling ramai dibicarakan di '
        'DramaBox, ReelShort, NetShort, SAGABOX, StardustTV, dan '
        'TopShort, menuliskan sinopsis dan daya tariknya tanpa '
        'membocorkan akhir, dan menautkan Anda langsung ke aplikasi '
        'resmi. Data dan gambar berasal dari materi program afiliasi '
        'DramaCPS. Saat Anda menonton melalui tautan kami, kami dapat '
        'menerima komisi dari platform, tanpa biaya tambahan untuk '
        'Anda.')}
PRIV = {
 'en': ('Privacy Policy',
        'DramaPick is a static guide: we run no accounts, no comments '
        'and no sign-ups, and we do not collect personal data on this '
        'site. Links labeled as watch buttons lead to third-party apps '
        '(DramaBox, ReelShort and others) through affiliate partner '
        'links; those apps have their own privacy policies and handle '
        'any account or payment data themselves. Basic, anonymous '
        'server logs (IP address, browser type, pages visited) may be '
        'kept briefly by our hosting and CDN providers for security '
        'and traffic measurement.'),
 'es': ('Política de privacidad',
        'DramaPick es una guía estática: no tenemos cuentas, '
        'comentarios ni registros, y no recopilamos datos personales '
        'en este sitio. Los botones de ver llevan a apps de terceros '
        '(DramaBox, ReelShort y otras) mediante enlaces de afiliado; '
        'esas apps tienen sus propias políticas de privacidad y '
        'gestionan cualquier dato de cuenta o pago. Nuestros '
        'proveedores de alojamiento y CDN pueden conservar brevemente '
        'registros anónimos del servidor (IP, navegador, páginas '
        'visitadas) por seguridad y medición de tráfico.'),
 'pt': ('Política de privacidade',
        'O DramaPick é um guia estático: não temos contas, comentários '
        'nem cadastros, e não coletamos dados pessoais neste site. Os '
        'botões de assistir levam a apps de terceiros (DramaBox, '
        'ReelShort e outros) por links de afiliado; esses apps têm '
        'suas próprias políticas de privacidade e cuidam de qualquer '
        'dado de conta ou pagamento. Nossos provedores de hospedagem '
        'e CDN podem manter por pouco tempo registros anônimos do '
        'servidor (IP, navegador, páginas visitadas) para segurança e '
        'medição de tráfego.'),
 'id': ('Kebijakan Privasi',
        'DramaPick adalah panduan statis: kami tidak menyediakan '
        'akun, komentar, atau pendaftaran, dan kami tidak '
        'mengumpulkan data pribadi di situs ini. Tombol tonton '
        'mengarah ke aplikasi pihak ketiga (DramaBox, ReelShort, dan '
        'lainnya) melalui tautan afiliasi; aplikasi-aplikasi tersebut '
        'memiliki kebijakan privasi sendiri dan menangani data akun '
        'atau pembayaran secara mandiri. Log server anonim dasar '
        '(alamat IP, jenis browser, halaman yang dikunjungi) dapat '
        'disimpan sebentar oleh penyedia hosting dan CDN kami untuk '
        'keamanan dan pengukuran lalu lintas.')}

def simple_body(title, text):
    return '<h1>%s</h1><p>%s</p>' % (esc(title), esc(text))

def platform_body(lang, src):
    ui = UI[lang]
    ss = [s for s in SHOWS if s['source'] == src]
    ld = {'@context': 'https://schema.org', '@type': 'ItemList',
          'itemListElement': [
              {'@type': 'ListItem', 'position': i + 1,
               'url': '%s/%sshows/%s/' % (DOMAIN, PREFIX[lang], s['slug']),
               'name': s['name']} for i, s in enumerate(ss)]}
    body = ('<h1>%s</h1><p>%s</p>%s'
            % (esc(ui['title_platform'].format(
                platform=PLAT_NAME[src])),
               esc(META['platforms'][lang][src]), grid(lang, ss)))
    return body, ld

def trope_body(lang, t):
    ui = UI[lang]
    name, desc = META['tropes'][t][lang]
    ss = [s for s in SHOWS if t in tropes_of(s)]
    ld = {'@context': 'https://schema.org', '@type': 'ItemList',
          'itemListElement': [
              {'@type': 'ListItem', 'position': i + 1,
               'url': '%s/%sshows/%s/' % (DOMAIN, PREFIX[lang], s['slug']),
               'name': s['name']} for i, s in enumerate(ss)]}
    body = '<h1>%s</h1><p>%s</p>%s' % (
        esc(ui['title_trope'].format(trope=name)), esc(desc),
        grid(lang, ss))
    return body, ld

def write(rel, content):
    path = os.path.join(BASE, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return rel.replace(os.sep, '/')

def main():
    for d in ('shows', 'platforms', 'tropes', 'about', 'privacy',
              'es', 'pt', 'id', 'img'):
        p = os.path.join(BASE, d)
        if os.path.isdir(p):
            shutil.rmtree(p)
    urls = []
    for lang in LANGS:
        ui = UI[lang]
        p = PREFIX[lang]
        write(p + 'index.html', page(
            lang, '', 'DramaPick — %s' % ui['home_h1'],
            ui['meta_desc_home'], home_body(lang)))
        urls.append(p)
        for s in SHOWS:
            plat = PLAT_NAME[s['source']]
            title = ui['title_watch'].format(name=s['name'],
                                             platform=plat)
            desc = '%s %s' % (hook_of(lang, s), ui['free_first'])
            write(p + 'shows/%s/index.html' % s['slug'], page(
                lang, 'shows/%s/' % s['slug'], title, desc[:300],
                show_body(lang, s), ld=show_ld(lang, s),
                og_img=s['cover_url']))
            urls.append(p + 'shows/%s/' % s['slug'])
        for src in PLAT_NAME:
            body, ld = platform_body(lang, src)
            write(p + 'platforms/%s/index.html' % src, page(
                lang, 'platforms/%s/' % src,
                ui['title_platform'].format(platform=PLAT_NAME[src]),
                META['platforms'][lang][src], body, ld=ld))
            urls.append(p + 'platforms/%s/' % src)
        for t in TROPES:
            body, ld = trope_body(lang, t)
            name = META['tropes'][t][lang][0]
            write(p + 'tropes/%s/index.html' % t, page(
                lang, 'tropes/%s/' % t,
                ui['title_trope'].format(trope=name),
                META['tropes'][t][lang][1], body, ld=ld))
            urls.append(p + 'tropes/%s/' % t)
        at, ax = ABOUT[lang]
        write(p + 'about/index.html', page(lang, 'about/', at, ax,
                                           simple_body(at, ax)))
        urls.append(p + 'about/')
        pt_, px = PRIV[lang]
        write(p + 'privacy/index.html', page(lang, 'privacy/', pt_, px,
                                             simple_body(pt_, px)))
        urls.append(p + 'privacy/')
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
          'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for u in urls:
        bare = re.sub(r'^(es|pt|id)/', '', u)
        sm.append('<url><loc>%s/%s</loc>' % (DOMAIN, u))
        for l in LANGS:
            sm.append('<xhtml:link rel="alternate" hreflang="%s" '
                      'href="%s/%s%s"/>' % (l, DOMAIN, PREFIX[l], bare))
        sm.append('<xhtml:link rel="alternate" hreflang="x-default" '
                  'href="%s/%s"/></url>' % (DOMAIN, bare))
    sm.append('</urlset>')
    write('sitemap.xml', '\n'.join(sm))
    write('robots.txt', 'User-agent: *\nAllow: /\n'
          'Sitemap: %s/sitemap.xml\n' % DOMAIN)
    llms = ['# DramaPick', '',
            'DramaPick is an editorial guide to vertical short dramas '
            'on DramaBox, ReelShort, NetShort, SAGABOX, StardustTV and '
            'TopShort. Each show page gives a spoiler-free setup, the '
            'hook, and an official affiliate watch link. The site is '
            'published in English, Spanish, Portuguese and Indonesian.',
            '', '## Platforms']
    for src, name in PLAT_NAME.items():
        llms.append('- %s (%s/platforms/%s/): %s'
                    % (name, DOMAIN, src, META['platforms']['en'][src]))
    llms += ['', '## Shows']
    for s in SHOWS:
        llms.append('- %s on %s (%s/shows/%s/): %s'
                    % (s['name'], PLAT_NAME[s['source']], DOMAIN,
                       s['slug'], HK['en'][s['slug']]))
    write('llms.txt', '\n'.join(llms) + '\n')
    write('404.html', page('en', '404.html', 'Not found — DramaPick',
                           'Page not found.',
                           '<h1>404</h1><p>Page not found.</p>'))
    print('pages:', len(urls))

if __name__ == '__main__':
    main()
