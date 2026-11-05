"""Build a portable static blog from explicitly imported, published articles."""
from pathlib import Path
from html import escape
from html.parser import HTMLParser
from datetime import datetime
from email.utils import format_datetime
from xml.etree import ElementTree as ET
import json
import re
import shutil

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'dist'
CONFIG = json.loads((ROOT / 'site.json').read_text(encoding='utf-8'))
BASE = CONFIG['url'].rstrip('/')
E = escape

class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []
    def handle_data(self, text): self.parts.append(text)

def plain(html):
    p = Text(); p.feed(html)
    return re.sub(r'\s+', ' ', ' '.join(p.parts)).strip()

def shell(title, body, path='/', description=None, article=None):
    description = description or CONFIG['description']
    structured = {'@context':'https://schema.org', '@type':'Blog', 'name':'Sylan', 'url':BASE}
    if article:
        structured.update({'@type':'BlogPosting', 'headline':article['title'], 'datePublished':article['published_at'], 'author':{'@type':'Person','name':'Sylan'}, 'mainEntityOfPage':BASE+path, 'isBasedOn':article['source_url']})
    structured_json = json.dumps(structured,ensure_ascii=False).replace('<','\\u003c')
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)} · Sylan</title><meta name="description" content="{E(description, quote=True)}">
<meta name="theme-color" content="#f5f1e8"><link rel="icon" href="/assets/avatar.png">
<link rel="canonical" href="{BASE}{path}"><link rel="alternate" type="application/rss+xml" title="Sylan" href="/feed.xml">
<meta property="og:type" content="{'article' if article else 'website'}"><meta property="og:title" content="{E(title, quote=True)}">
<meta property="og:description" content="{E(description, quote=True)}"><meta property="og:url" content="{BASE}{path}">
<meta property="og:image" content="{BASE}/assets/avatar.png"><link rel="stylesheet" href="/assets/style.css">
<script type="application/ld+json">{structured_json}</script></head>
<body><a class="skip" href="#main">跳到正文</a><header class="masthead"><a class="brand" href="/">Sylan<span>.</span></a>
<nav aria-label="主导航"><a href="/">文章</a><a href="{CONFIG['linktree']}">Linktree ↗</a><a href="/feed.xml">RSS</a></nav></header>
{body}<footer class="footer"><a href="/">Sylan</a><div><a href="https://github.com/ningsiyuan1024">GitHub ↗</a><a href="{CONFIG['linktree']}">各平台主页 ↗</a></div><a href="#top" aria-label="回到顶部">↑</a></footer>
<script src="/assets/app.js" defer></script></body></html>'''

def write(path, content):
    dest = OUT / path; dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding='utf-8')

def build():
    # Only remove generated output inside this project.
    if OUT.resolve().parent != ROOT.resolve(): raise ValueError('Unsafe output directory')
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / 'assets', OUT / 'assets')
    posts = []
    for path in sorted((ROOT / 'content').glob('*/article.json')):
        p = json.loads(path.read_text(encoding='utf-8'))
        if p.get('status') != 'published_verified': raise ValueError(f'Unverified content: {path}')
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', p['slug']): raise ValueError('Invalid slug')
        p['html'] = (path.parent / 'body.html').read_text(encoding='utf-8')
        p['text'] = plain(p['html'])
        if not p['text']: raise ValueError('Empty article')
        p['description'] = p['text'][:130]
        p['minutes'] = max(1, round(len(p['text']) / 400))
        p['path'] = '/articles/' + p['slug'] + '/'
        posts.append(p)
        if (path.parent / 'assets').exists(): shutil.copytree(path.parent / 'assets', OUT / 'articles' / p['slug'] / 'assets')
    posts.sort(key=lambda p:(p['published_at'],p['slug']), reverse=True)
    if len({p['slug'] for p in posts}) != len(posts): raise ValueError('Duplicate slugs')
    cards = []
    for i,p in enumerate(posts):
        cover = f'<img src="{E(p["cover"],quote=True)}" alt="" loading="lazy">' if p.get('cover') else '<div class="cover-type" aria-hidden="true">S<span>.</span></div>'
        cards.append(f'''<article class="entry" data-search="{E(p['title']+' '+p['text'],quote=True)}"><a class="entry-image" href="{p['path']}" tabindex="-1" aria-hidden="true">{cover}</a><div class="entry-copy"><div class="meta"><time datetime="{p['published_at']}">{p['published_at'][:10].replace('-','.')} </time><span>{p['minutes']} 分钟</span></div><h2><a href="{p['path']}">{E(p['title'])}</a></h2><p>{E(p['description'])}…</p><a class="read" href="{p['path']}" aria-label="阅读：{E(p['title'],quote=True)}">阅读全文 <span>↗</span></a></div></article>''')
        content = f'''<main id="main" class="article-page"><a class="back" href="/">← 所有文章</a><header class="article-header" id="top"><div class="meta"><time datetime="{p['published_at']}">{p['published_at'][:10].replace('-','.')}</time><span>{p['minutes']} 分钟</span><a href="{E(p['source_url'],quote=True)}">首发于{E(p.get('platform','原平台'))} ↗</a></div><h1>{E(p['title'])}</h1><div class="byline"><img src="/assets/avatar.png" width="28" height="28" alt="">Sylan</div></header><div class="prose">{p['html']}</div><div class="article-end"><a href="{E(p['source_url'],quote=True)}">阅读原平台版本 ↗</a><a href="/">返回文章列表 →</a></div></main>'''
        write('articles/'+p['slug']+'/index.html',shell(p['title'],content,p['path'],p['description'],p))
    body = f'''<main id="main"><section class="intro" id="top"><div><p class="eyebrow">Sylan 的个人博客</p><h1>AI、Agent<br>与创造<span>。</span></h1></div><img class="portrait" src="/assets/avatar.png" alt="Sylan 的黑猫头像" width="152" height="152"></section><section class="archive" aria-labelledby="archive-title"><div class="archive-head"><h2 id="archive-title">文章 <span>{len(posts):02d}</span></h2><label class="search"><span class="sr-only">搜索文章</span><input id="search" type="search" placeholder="搜索文章" autocomplete="off"><span aria-hidden="true">⌕</span></label></div><div id="articles">{''.join(cards)}</div><p id="no-results" hidden role="status">没有找到相关文章。</p></section></main>'''
    write('index.html',shell('个人博客',body))
    write('404.html',shell('页面未找到','<main id="main" class="article-page"><h1>页面未找到</h1><a href="/">返回文章列表 →</a></main>','/404.html'))
    write('.nojekyll','')
    write('robots.txt',f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
    sitemap=ET.Element('urlset',xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for path in ['/']+[p['path'] for p in posts]:
        ET.SubElement(ET.SubElement(sitemap,'url'),'loc').text=BASE+path
    write('sitemap.xml',ET.tostring(sitemap,encoding='unicode',xml_declaration=True))
    rss=ET.Element('rss',version='2.0'); channel=ET.SubElement(rss,'channel')
    for k,v in {'title':'Sylan','link':BASE,'description':CONFIG['description'],'language':'zh-CN'}.items(): ET.SubElement(channel,k).text=v
    for p in posts:
        item=ET.SubElement(channel,'item')
        date=datetime.fromisoformat(p['published_at'][:10]+'T00:00:00+08:00')
        for k,v in {'title':p['title'],'link':BASE+p['path'],'guid':BASE+p['path'],'description':p['description'],'pubDate':format_datetime(date)}.items(): ET.SubElement(item,k).text=v
    write('feed.xml',ET.tostring(rss,encoding='unicode',xml_declaration=True))
    print(json.dumps({'articles':len(posts),'output':str(OUT),'slugs':[p['slug'] for p in posts]},ensure_ascii=False))

if __name__ == '__main__': build()
