"""Сборка служебных частей сайта «Токио между нами».

Запуск из корня репозитория:  python3 tools/build_site.py

Что делает (можно запускать сколько угодно раз — результат одинаковый):
  1. картинки-превью для ссылок: assets/og/chapter-NN.png и assets/og/index.png;
     если есть иллюстрация автора assets/og/art/chapter-NN.jpg (1200×630), берётся она;
  2. блок в <head> каждой страницы между <!-- site:head --> и <!-- /site:head -->:
     иконка, описание, Open Graph/Twitter-превью, подключение assets/reader.css и reader.js;
  3. glossary.html — словарь японских слов из сносок (<span class="term">…<span class="note">…);
  4. sitemap.xml для поисковиков.

Опубликованными считаются главы, у которых в index.html есть незакомментированная ссылка.
Нужны: Pillow, шрифт Cormorant (скачивается сам), Noto Serif CJK (для иероглифов).
"""
import html, os, re, glob, urllib.request, datetime
from PIL import Image, ImageDraw, ImageFont

BASE_URL = 'https://hirotamashi.github.io/project_tokyo/'
SITE = 'Токио между нами'
AUTHOR = 'Хиро Тамаши'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(os.path.expanduser('~'), '.cache', 'tbn-fonts')
CORMORANT = os.path.join(FONT_DIR, 'Cormorant.ttf')
CORMORANT_IT = os.path.join(FONT_DIR, 'Cormorant-Italic.ttf')
CJK_CANDIDATES = ['/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc',
                  '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
SEASONS = {'Весна': '春', 'Лето': '夏', 'Осень': '秋', 'Зима': '冬'}

# Цвета карточек (как в Instagram-шаблонах)
BG = (16, 18, 24); WHITE = (255, 251, 244); SUB = (180, 178, 172)
DESC = (200, 197, 190); FOOT = (120, 118, 114); ACCENT = (214, 108, 82)


def fonts():
    os.makedirs(FONT_DIR, exist_ok=True)
    src = 'https://raw.githubusercontent.com/google/fonts/main/ofl/cormorant/'
    for path, name in [(CORMORANT, 'Cormorant%5Bwght%5D.ttf'), (CORMORANT_IT, 'Cormorant-Italic%5Bwght%5D.ttf')]:
        if not os.path.exists(path):
            urllib.request.urlretrieve(src + name, path)
    cjk = next(p for p in CJK_CANDIDATES if os.path.exists(p))
    return cjk


def cf(path, size, w=500):
    f = ImageFont.truetype(path, size)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f


def read(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()
def write(p, s):
    full = os.path.join(ROOT, p)
    os.makedirs(os.path.dirname(full) or '.', exist_ok=True)
    open(full, 'w', encoding='utf-8').write(s)


def published():
    idx = read('index.html')
    idx = re.sub(r'<!--.*?-->', '', idx, flags=re.S)
    out = []
    for m in re.finditer(r'<a href="(chapter-(\d+)\.html)">\s*<span class="num">\d+</span>\s*'
                         r'<span class="title">(.*?)</span>\s*<span class="tag">(.*?)</span>', idx, re.S):
        tag = html.unescape(m.group(4))
        season = tag.split('·')[-1].strip()
        out.append(dict(file=m.group(1), n=int(m.group(2)), name=html.unescape(m.group(3)).strip(), season=season))
    return out


def plain(fragment):
    fragment = re.sub(r'<span class="note">.*?</span>', '', fragment, flags=re.S)
    fragment = re.sub(r'<span class="sr">.*?</span>', '', fragment, flags=re.S)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', fragment))).strip()


def first_sentence(page):
    prose = page[page.index('<div class="prose">'):page.index('<div class="chapter-footer">')]
    for p in re.findall(r'<p>(.*?)</p>', prose, re.S):
        t = plain(p)
        if len(t) < 40:
            continue
        m = re.match(r'(.+?[.!?…])(\s|$)', t)
        s = m.group(1) if m and len(m.group(1)) >= 40 else t
        return s if len(s) <= 220 else s[:217].rsplit(' ', 1)[0] + '…'
    return f'{SITE} — роман {AUTHOR}.'


def og_chapter(ch, cjk):
    W, H = 1200, 630
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    d.text((80, 64), SEASONS.get(ch['season'], ''), font=ImageFont.truetype(cjk, 60, index=0), fill=FOOT)
    d.text((160, 86), f"ГЛАВА {ch['n']} · {ch['season'].upper()}", font=cf(CORMORANT, 34, 500), fill=SUB)
    d.text((76, 170), ch['name'], font=cf(CORMORANT_IT, 150, 500), fill=WHITE)
    d.rectangle([82, 382, 172, 384], fill=ACCENT)
    d.text((80, 410), SITE, font=cf(CORMORANT, 56, 500), fill=DESC)
    d.text((80, 540), f'{AUTHOR} · роман', font=cf(CORMORANT, 34, 450), fill=FOOT)
    out = f"assets/og/chapter-{ch['n']:02d}.png"
    im.save(os.path.join(ROOT, out), optimize=True)
    return out


def og_index(cjk):
    W, H = 1200, 630
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(cjk, 150, index=0)
    b = d.textbbox((0, 0), '東京', font=f); d.text(((W - b[2]) / 2, 60), '東京', font=f, fill=FOOT)
    for y, t, fnt, col in [(285, SITE, cf(CORMORANT_IT, 110, 500), WHITE),
                           (470, f'роман · {AUTHOR}', cf(CORMORANT, 40, 450), DESC)]:
        b = d.textbbox((0, 0), t, font=fnt); d.text(((W - b[2]) / 2, y), t, font=fnt, fill=col)
    d.rectangle([W / 2 - 45, 440, W / 2 + 45, 442], fill=ACCENT)
    im.save(os.path.join(ROOT, 'assets/og/index.png'), optimize=True)
    return 'assets/og/index.png'


def icons(cjk):
    """Иконка 間 («между») в цветах сайта."""
    for size, name in [(32, 'icon-32.png'), (180, 'apple-touch-icon.png'), (512, 'icon-512.png')]:
        S = size * 4
        im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        r = 0 if name == 'apple-touch-icon.png' else int(S * 0.22)
        d.rounded_rectangle([0, 0, S - 1, S - 1], radius=r, fill=(59, 74, 90, 255))
        f = ImageFont.truetype(cjk, int(S * 0.70), index=0)
        b = d.textbbox((0, 0), '間', font=f)
        d.text(((S - (b[0] + b[2])) / 2, (S - (b[1] + b[3])) / 2), '間', font=f, fill=(244, 241, 233, 255))
        im.resize((size, size), Image.LANCZOS).save(os.path.join(ROOT, 'assets', name))


def head_block(title, desc, image, url, kind):
    e = lambda s: html.escape(s, quote=True)
    return f'''<!-- site:head (собирается tools/build_site.py — правки вручную перезапишутся) -->
<meta name="description" content="{e(desc)}">
<link rel="icon" type="image/png" sizes="32x32" href="assets/icon-32.png">
<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">
<meta name="theme-color" content="#EDEAE3" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#15171B" media="(prefers-color-scheme: dark)">
<meta property="og:site_name" content="{e(SITE)}">
<meta property="og:type" content="{kind}">
<meta property="og:locale" content="ru_RU">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(BASE_URL + image)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="assets/reader.css">
<script src="assets/reader.js"></script>
<!-- /site:head -->'''


def put_head(page, block):
    page = re.sub(r'<!-- site:head.*?<!-- /site:head -->\n?', '', page, flags=re.S)
    return page.replace('</head>', block + '\n</head>', 1)


def glossary(chs):
    entries = {}
    for ch in chs:
        page = read(ch['file'])
        prose = page[page.index('<div class="prose">'):page.index('<div class="chapter-footer">')]
        for note in re.findall(r'<span class="note">(.*?)</span>', prose, re.S):
            t = plain(note)
            m = re.match(r'^«?([^—«»]{1,40}?)»?\s+—\s+(.+)$', t)
            if not m or re.search(r'[A-Za-z.!?,]', m.group(1)) or len(m.group(1).split()) > 3:
                continue
            head, body = m.group(1).strip(), m.group(2).strip()
            key = head.lower().replace('ё', 'е')
            if key not in entries:
                entries[key] = dict(head=head, body=body, n=ch['n'], file=ch['file'])
    order = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
    def sortkey(k): return [order.index(c) if c in order else 100 + ord(c) for c in k.lstrip('-')]
    items = [entries[k] for k in sorted(entries, key=sortkey)]
    rows = '\n'.join(
        f'''      <li id="{html.escape(e['head'].lower())}">
        <p class="g-head">{html.escape(e['head'])}</p>
        <p class="g-body">{html.escape(e['body'][0].upper() + e['body'][1:])}</p>
        <a class="g-where" href="{e['file']}">глава {e['n']} →</a>
      </li>''' for e in items)
    tpl = read('index.html')
    style = tpl[tpl.index('<style>'):tpl.index('</style>') + 8]
    fonts_link = re.search(r'<link href="https://fonts\.googleapis\.com/css2[^>]+>', tpl).group(0)
    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Словарь — {SITE}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
{fonts_link}
{style}
<style>
  .back{{ font-family: var(--mono); font-size: 11px; letter-spacing: .08em; text-transform: uppercase;
          color: var(--ink-soft); text-decoration: none; }}
  .g-intro{{ color: var(--ink-soft); font-style: italic; margin: 8px 0 36px; }}
  .glossary{{ list-style: none; margin: 0; padding: 0; }}
  .glossary li{{ padding: 18px 0; border-top: 1px solid var(--line); }}
  .g-head{{ font-family: var(--serif-display); font-style: italic; font-size: 24px; margin: 0 0 4px; color: var(--ink); }}
  .g-body{{ margin: 0 0 6px; line-height: 1.7; color: var(--ink); }}
  .g-where{{ font-family: var(--mono); font-size: 11px; letter-spacing: .08em; text-transform: uppercase;
             color: var(--accent); text-decoration: none; }}
  .g-where:hover{{ text-decoration: underline; }}
</style>
</head>
<body>
  <main class="page">
    <a class="back" href="index.html">← Оглавление</a>
    <h1 class="wordmark">Словарь</h1>
    <p class="g-intro">Японские слова и места из опубликованных глав — по алфавиту. Пополняется с каждой новой главой.</p>
    <ul class="glossary">
{rows}
    </ul>
  </main>
<!-- статистика посещений (GoatCounter) -->
<script data-goatcounter="https://hirotamashi.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>
</body>
</html>
''', len(items)


def main():
    cjk = fonts()
    os.makedirs(os.path.join(ROOT, 'assets/og'), exist_ok=True)
    icons(cjk)
    chs = published()
    today = datetime.date.today().isoformat()

    for ch in chs:
        page = read(ch['file'])
        art = f"assets/og/art/chapter-{ch['n']:02d}.jpg"
        # иллюстрация автора (1200×630) важнее сгенерированной обложки
        img = art if os.path.exists(os.path.join(ROOT, art)) else og_chapter(ch, cjk)
        title = f"Глава {ch['n']}. {ch['name']}"
        page = re.sub(r'<title>.*?</title>', f'<title>{title} — {SITE}</title>', page, count=1)
        page = put_head(page, head_block(title, first_sentence(page), img, BASE_URL + ch['file'], 'article'))
        write(ch['file'], page)

    idx = read('index.html')
    premise = plain(re.search(r'<p class="premise">(.*?)</p>', idx, re.S).group(1))
    desc = premise if len(premise) <= 200 else premise[:197].rsplit(' ', 1)[0] + '…'
    idx = put_head(idx, head_block(f'{SITE} — роман {AUTHOR}', desc, og_index(cjk), BASE_URL, 'book'))
    if 'href="glossary.html"' not in idx:
        idx = idx.replace('<p>Одна глава в неделю</p>',
                          '<p>Одна глава в неделю</p>\n      <p><a class="glossary-link" href="glossary.html">Словарь японских слов</a></p>', 1)
    write('index.html', idx)

    g, n = glossary(chs)
    g = put_head(g, head_block(f'Словарь — {SITE}', 'Японские слова и места из романа «Токио между нами» с пояснениями.',
                               'assets/og/index.png', BASE_URL + 'glossary.html', 'website'))
    write('glossary.html', g)

    urls = [BASE_URL, BASE_URL + 'glossary.html'] + [BASE_URL + c['file'] for c in chs]
    write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          ''.join(f'  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n' for u in urls) + '</urlset>\n')
    print(f'глав: {len(chs)}, слов в словаре: {n}')


if __name__ == '__main__':
    main()
