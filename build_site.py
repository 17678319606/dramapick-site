#!/usr/bin/env python3
"""DramaPick static site builder: DramaCPS catalog micro-site.
Reads selection-links.json (28 shows with official drama_url), downloads
covers (WebP <=80KB), emits a static site into dist/."""
import json, os, re, sys, html, io, hashlib
import requests
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(BASE, 'dist')
DOMAIN = 'https://drama.jinbufenzi.com'
PROXY = {'http': 'http://127.0.0.1:8890', 'https': 'http://127.0.0.1:8890'}
PLATFORMS = {
 'dramabox':   ('DramaBox',   'The volume king: revenge, billionaire romance and comeback stories, with new series landing constantly.'),
 'reelshort':  ('ReelShort',  'The best-known short drama app in the US, built around high-emotion vertical dramas and werewolf romance.'),
 'netshort':   ('NetShort',   'A fast-growing challenger mixing romance, fantasy and game-like survival stories.'),
 'sagabox':    ('SAGABOX',    'Werewolf and fated-mate romance specialist; most of its hits revolve around alphas, lunas and second chances.'),
 'stardusttv': ('StardustTV', 'Fantasy-leaning catalog: immortal kings, hidden heirs and family-underdog stories.'),
 'topshort':   ('TopShort',   'Trending-first catalog that leans into werewolf daddies, secret twins and hidden-identity hooks.'),
}
GENRE_RULES = [
 ('Werewolf Romance', r'alpha|luna|werewolf|lycan|omega|mate\b|moon goddess'),
 ('Billionaire Romance', r'billionaire|ceo|chair|heir|tycoon|mogul'),
 ('Revenge & Comeback', r'revenge|crush you|begs? for mercy|rose from|comeback|pay me|payback'),
 ('Secret Identity', r'secret|hidden|mocked|legendary|nobody|undercover|nobody'),
 ('Fantasy & Powers', r'dragon|archmage|immortal|oracle|awakening|awakener|goddess|mech|grail'),
 ('Mafia & Danger', r'mafia|mob|crime|kidnap|spy|assassin'),
 ('Contract Marriage', r'marry|marrying|wed|bride|husband|wife|marriage'),
 ('Rebirth & Second Chance', r'reborn|second chance|gave away|killed me'),
 ('Survival & Games', r'game|island|survival|death game'),
 ('Family & Kids', r'heirs|quadruplets|twins|baby|son|daughter|mom'),
]
HOOKS = {
 'Werewolf Romance': 'Fated mates, pack politics and an alpha who realizes too late what he threw away.',
 'Billionaire Romance': 'Boardroom power plays with a romance that keeps interrupting the business.',
 'Revenge & Comeback': 'The underestimated lead collects every debt, one episode at a time.',
 'Secret Identity': 'Everyone laughs at the nobody in the room. The nobody is the most dangerous person there.',
 'Fantasy & Powers': 'Hidden bloodlines and powers that wake up exactly when the family needs them.',
 'Mafia & Danger': 'Debts, kidnappings and the one person the underworld should never have touched.',
 'Contract Marriage': 'A deal first, feelings later, and a contract that keeps getting renegotiated by the heart.',
 'Rebirth & Second Chance': 'She already lived the worst ending once. This time the script flips.',
 'Survival & Games': 'Rules, traps and alliances that last exactly as long as they are useful.',
 'Family & Kids': 'Secret babies, hidden heirs and family secrets that refuse to stay buried.',
 'Short Drama': 'A fast, cliffhanger-heavy setup built for one-more-episode viewing.',
}

def slugify(t):
    s = re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')
    return s[:60].strip('-')

def genres_of(show):
    text = (show['name'] + ' ' + show.get('description', '')).lower()
    got = []
    for name, pat in GENRE_RULES:
        if re.search(pat, text):
            got.append(name)
        if len(got) >= 2:
            break
    return got or ['Short Drama']

def premise_of(desc):
    d = ' '.join((desc or '').split())
    parts = re.split(r'(?<=[.!?])\s+', d)
    out = ''
    for p in parts:
        if len(out) + len(p) > 300 and out:
            break
        out = (out + ' ' + p).strip()
        if len(out) > 140:
            break
    return out or d[:280]

def fetch_cover(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return True
    r = requests.get(url, proxies=PROXY, timeout=40)
    r.raise_for_status()
    im = Image.open(io.BytesIO(r.content)).convert('RGB')
    if im.width > 480:
        im = im.resize((480, int(im.height * 480 / im.width)), Image.LANCZOS)
    q = 78
    while q > 30:
        buf = io.BytesIO()
        im.save(buf, 'WEBP', quality=q)
        if buf.tell() <= 80 * 1024:
            break
        q -= 12
    with open(dest, 'wb') as f:
        f.write(buf.getvalue())
    return True

CSS = """
:root{--bg:#0e0f13;--card:#17181f;--line:#26272f;--txt:#e8e8ec;--mut:#9a9cab;--acc:#ff4d6d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:16px/1.55 -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}
a{color:inherit;text-decoration:none}img{display:block;max-width:100%}
.wrap{max-width:1120px;margin:0 auto;padding:0 18px}
header.site{border-bottom:1px solid var(--line);padding:14px 0}
.logo{font-size:22px;font-weight:800;letter-spacing:.3px}.logo span{color:var(--acc)}
nav.top a{margin-left:18px;color:var(--mut);font-size:14px}
.flex{display:flex;align-items:center;justify-content:space-between}
.hero{padding:44px 0 8px}.hero h1{font-size:34px;margin:0 0 10px;line-height:1.2}
.hero p{color:var(--mut);max-width:640px;margin:0}
h2.sec{font-size:21px;margin:34px 0 14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.card img{width:100%;aspect-ratio:3/4;object-fit:cover}
.card .in{padding:12px 14px 14px}.card h3{font-size:16px;margin:0 0 6px;line-height:1.3}
.badge{display:inline-block;font-size:11px;color:#ffd7de;background:#3a1620;border:1px solid #57202f;padding:1px 7px;border-radius:20px;margin-bottom:7px}
.genre{font-size:12px;color:var(--mut)}
.watch{display:inline-block;margin-top:10px;background:var(--acc);color:#fff;font-weight:700;padding:9px 16px;border-radius:9px;font-size:14px}
.watch:hover{opacity:.9}.premise{color:var(--mut);font-size:14px}
.detail{display:grid;grid-template-columns:300px 1fr;gap:26px;padding:30px 0}
@media(max-width:720px){.detail{grid-template-columns:1fr}.detail img{max-width:280px}}
.detail img{border-radius:12px;width:100%}
.disc{font-size:12.5px;color:var(--mut);border-top:1px solid var(--line);margin-top:26px;padding-top:12px}
footer.site{border-top:1px solid var(--line);margin-top:44px;padding:22px 0;color:var(--mut);font-size:13px}
footer.site a{color:var(--mut);text-decoration:underline}
.plat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.plat h3{margin:0 0 6px}.plat p{color:var(--mut);font-size:14px;margin:0 0 10px}
.kicker{font-size:12px;color:var(--acc);font-weight:700;letter-spacing:1.2px;text-transform:uppercase}
"""

def head(title, desc, path, extra=''):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
      '<meta name="viewport" content="width=device-width,initial-scale=1">'
      f'<title>{html.escape(title)}</title>'
      f'<meta name="description" content="{html.escape(desc)}">'
      f'<link rel="canonical" href="{DOMAIN}{path}">'
      f'<meta property="og:title" content="{html.escape(title)}">'
      f'<meta property="og:description" content="{html.escape(desc)}">'
      '<meta property="og:type" content="website">'
      f'<meta property="og:url" content="{DOMAIN}{path}">'
      '<link rel="icon" href="data:,">'
      f'<style>{CSS}</style>{extra}</head>')

def header():
    return ('<header class="site"><div class="wrap flex">'
      '<a class="logo" href="/">Drama<span>Pick</span></a>'
      '<nav class="top"><a href="/">Catalog</a><a href="/platforms/">Platforms</a><a href="/about/">About</a></nav>'
      '</div></header>')

def footer():
    return ('<footer class="site"><div class="wrap">'
      'DramaPick is an independent guide to short drama apps. Some outbound links are affiliate links — '
      'if you watch or subscribe through them, we may earn a commission at no extra cost to you. '
      'See our <a href="/about/">affiliate disclosure</a>. All show artwork belongs to its respective platform.'
      '</div></footer>')

def card_html(s):
    plat = PLATFORMS[s['source']][0]
    return ('<article class="card">'
      f'<a href="/shows/{s["slug"]}/"><img src="/img/{s["base_id"]}.webp" alt="{html.escape(s["name"])} poster" loading="lazy"></a>'
      f'<div class="in"><span class="badge">{plat}</span>'
      f'<h3><a href="/shows/{s["slug"]}/">{html.escape(s["name"])}</a></h3>'
      f'<div class="genre">{html.escape(" · ".join(s["genres"]))}</div>'
      f'<a class="watch" href="{s["drama_url"]}" target="_blank" rel="sponsored noopener">Watch now</a>'
      '</div></article>')

def show_page(s):
    plat_name, plat_blurb = PLATFORMS[s['source']]
    title = f'{s["name"]} — Watch on {plat_name} | DramaPick'
    desc = (f'{s["name"]} ({plat_name}): {s["premise"][:150]}').replace('\n', ' ')
    ld = {'@context': 'https://schema.org', '@type': 'TVSeries', 'name': s['name'],
          'description': s['premise'], 'genre': s['genres'],
          'image': f'{DOMAIN}/img/{s["base_id"]}.webp', 'url': f'{DOMAIN}/shows/{s["slug"]}/'}
    body = [head(title, desc, f'/shows/{s["slug"]}/',
            '<script type="application/ld+json">' + json.dumps(ld) + '</script>'),
      '<body>', header(), '<main class="wrap">',
      f'<div class="kicker" style="margin-top:22px">{plat_name} · {" · ".join(s["genres"])}</div>',
      '<section class="detail">',
      f'<div><img src="/img/{s["base_id"]}.webp" alt="{html.escape(s["name"])} poster"></div>',
      '<div>',
      f'<h1 style="margin:4px 0 12px;font-size:28px;line-height:1.25">{html.escape(s["name"])}</h1>',
      f'<p class="premise" style="font-size:16px">{html.escape(s["premise"])}</p>',
      f'<p><strong>The hook:</strong> {html.escape(s["hook"])}</p>',
      f'<p style="color:var(--mut)">Stream it on {plat_name}. The first episodes are free on the platform; '
      'later episodes unlock with coins or a subscription, depending on the app.</p>',
      f'<a class="watch" href="{s["drama_url"]}" target="_blank" rel="sponsored noopener">Watch on {plat_name}</a>',
      f'<p style="margin-top:22px;color:var(--mut);font-size:14px">More on this platform: '
      f'<a style="text-decoration:underline" href="/platforms/{s["source"]}/">{plat_name} guide and picks</a></p>',
      '<div class="disc">Affiliate disclosure: the Watch button is an affiliate link. '
      'If you install, watch or subscribe through it, DramaPick may earn a commission at no extra cost to you.</div>',
      '</div></section>', '</main>', footer(), '</body></html>']
    return '\n'.join(body)

def platform_page(src, shows):
    name, blurb = PLATFORMS[src]
    title = f'{name} — Best Short Dramas to Watch | DramaPick'
    desc = f'{name} guide: what it is, how watching works, and the DramaPick short drama picks on {name}.'
    cards = '\n'.join(card_html(s) for s in shows)
    body = [head(title, desc, f'/platforms/{src}/'), '<body>', header(), '<main class="wrap">',
      f'<h1 style="margin:26px 0 8px;font-size:28px">{name}</h1>',
      f'<p class="premise" style="max-width:680px;font-size:16px">{html.escape(blurb)}</p>',
      f'<p class="premise" style="max-width:680px">How it works: {name} is a vertical short drama app. '
      'Series are cut into 1–2 minute episodes; the opening episodes are free, and the rest unlock with in-app coins or a subscription. '
      'Prices and free-episode counts change often, so check the app page after you tap through.</p>',
      f'<h2 class="sec">Our {name} picks</h2>', f'<div class="grid">{cards}</div>',
      '<div class="disc">Affiliate disclosure: Watch buttons on this page are affiliate links.</div>',
      '</main>', footer(), '</body></html>']
    return '\n'.join(body)

def index_page(shows):
    title = 'DramaPick — Short Dramas Worth Your Coins'
    desc = 'A hand-picked catalog of vertical short dramas on DramaBox, ReelShort, NetShort, SAGABOX and more — premises, genres and where to watch.'
    feats = shows[:6]
    grid = '\n'.join(card_html(s) for s in shows)
    plats = '\n'.join(
      f'<div class="plat"><h3><a href="/platforms/{src}/">{PLATFORMS[src][0]}</a></h3>'
      f'<p>{html.escape(PLATFORMS[src][1])}</p>'
      f'<a class="genre" style="text-decoration:underline" href="/platforms/{src}/">{sum(1 for s in shows if s["source"]==src)} picks →</a></div>'
      for src in PLATFORMS if any(s['source'] == src for s in shows))
    ld = {'@context': 'https://schema.org', '@type': 'ItemList',
          'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'url': f'{DOMAIN}/shows/{s["slug"]}/', 'name': s['name']} for i, s in enumerate(shows)]}
    body = [head(title, desc, '/', '<script type="application/ld+json">' + json.dumps(ld) + '</script>'),
      '<body>', header(), '<main class="wrap">',
      '<section class="hero"><h1>Short dramas worth your coins</h1>'
      '<p>Vertical dramas are a slot machine of cliffhangers. DramaPick reads the premises so you don\'t have to: '
      'a small, honest catalog of series that are actually worth starting, and the app each one lives on.</p></section>',
      '<h2 class="sec">Start with these</h2>', '<div class="grid">' + '\n'.join(card_html(s) for s in feats) + '</div>',
      '<h2 class="sec">Browse by platform</h2>', '<div class="grid">' + plats + '</div>',
      '<h2 class="sec">Full catalog</h2>', '<div class="grid">' + grid + '</div>',
      '</main>', footer(), '</body></html>']
    return '\n'.join(body)

def simple_page(path, h1, paras, title):
    body = [head(title, paras[0][:155], path), '<body>', header(), '<main class="wrap">',
      f'<h1 style="margin:26px 0 12px;font-size:28px">{h1}</h1>']
    body += [f'<p class="premise" style="max-width:700px;font-size:15.5px">{p}</p>' for p in paras]
    body += ['</main>', footer(), '</body></html>']
    return '\n'.join(body)

def main():
    sel = json.load(open(os.path.join(BASE, 'selection-links.json')))
    os.makedirs(os.path.join(DIST, 'img'), exist_ok=True)
    shows = []
    used_slugs = set()
    for s in sel:
        if not s.get('drama_url'):
            print('SKIP no link', s['base_id']); continue
        slug = slugify(s['name'])
        if slug in used_slugs:
            slug = slug + '-' + s['base_id']
        used_slugs.add(slug)
        s['slug'] = slug
        s['genres'] = genres_of(s)
        s['premise'] = premise_of(s.get('description', ''))
        s['hook'] = HOOKS[s['genres'][0]]
        dest = os.path.join(DIST, 'img', s['base_id'] + '.webp')
        try:
            fetch_cover(s['cover_url'], dest)
        except Exception as e:
            print('COVER FAIL', s['base_id'], str(e)[:100]); continue
        shows.append(s)
    print('SHOWS READY', len(shows))
    def w(path, content):
        fp = os.path.join(DIST, path)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        open(fp, 'w').write(content)
    w('index.html', index_page(shows))
    w('platforms/index.html', simple_page('/platforms/', 'Platforms',
        ['Where each short drama app shines, and the picks we list for it. Open a platform guide from the catalog page or the navigation.'],
        'Short Drama Platforms | DramaPick'))
    for s in shows:
        w(f'shows/{s["slug"]}/index.html', show_page(s))
    for src in PLATFORMS:
        ss = [s for s in shows if s['source'] == src]
        if ss:
            w(f'platforms/{src}/index.html', platform_page(src, ss))
    w('about/index.html', simple_page('/about/', 'About DramaPick',
      ['DramaPick is a small independent catalog of vertical short dramas. We read premises across the major apps, keep only the series with a hook worth your first free episodes, and tell you plainly which app each series lives on.',
       'Affiliate disclosure: DramaPick takes part in affiliate programs for the platforms listed here. Watch buttons and some outbound links are affiliate links. If you install an app, watch, or buy coins or a subscription after clicking one, we may earn a commission. It never changes what you pay, and it never buys a show a place in the catalog — picks are editorial.',
       'We do not host or stream any episodes. All viewing happens inside the official apps, and all artwork and titles belong to their respective platforms.'],
      'About & Affiliate Disclosure | DramaPick'))
    w('privacy/index.html', simple_page('/privacy/', 'Privacy',
      ['This site is a static catalog. It sets no cookies, runs no accounts and collects no personal data. Outbound Watch buttons go to the platforms\' own pages and apps, where their own privacy policies apply.'],
      'Privacy | DramaPick'))
    w('404.html', simple_page('/404.html', 'Page not found',
      ['That page wandered off between episodes. Head back to the <a href="/">catalog</a>.'], 'Not Found | DramaPick'))
    urls = ['/', '/platforms/', '/about/', '/privacy/']
    urls += [f'/platforms/{src}/' for src in PLATFORMS if any(s['source'] == src for s in shows)]
    urls += [f'/shows/{s["slug"]}/' for s in shows]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f'<url><loc>{DOMAIN}{u}</loc></url>' for u in urls]
    sm.append('</urlset>')
    w('sitemap.xml', '\n'.join(sm))
    w('robots.txt', f'User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n')
    json.dump(shows, open(os.path.join(BASE, 'shows-final.json'), 'w'), ensure_ascii=False, indent=1)
    print('DIST READY', DIST, 'pages', len(urls))

if __name__ == '__main__':
    main()
