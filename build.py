"""Build a portable static blog from explicitly imported, published articles."""
from pathlib import Path
from html import escape
from html.parser import HTMLParser
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from xml.etree import ElementTree as ET
import json
import re
import shutil

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'dist'
CONFIG = json.loads((ROOT / 'site.json').read_text(encoding='utf-8'))
METRICS = json.loads((ROOT / 'platform-metrics.json').read_text(encoding='utf-8'))
BASE = CONFIG['url'].rstrip('/')
E = escape

class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []
    def handle_data(self, text): self.parts.append(text)

def plain(html):
    p = Text(); p.feed(html)
    return re.sub(r'\s+', ' ', ' '.join(p.parts)).strip()

class ReadableText(Text):
    def handle_starttag(self, tag, attrs):
        if tag in ('h1','h2','h3','h4','p','div','section','blockquote','pre','li','br'): self.parts.append('\n')
        if tag=='img':
            src=dict(attrs).get('src','')
            if src:self.parts.append('\n[图片] '+(BASE+src if src.startswith('/') else src)+'\n')
    def handle_endtag(self, tag):
        if tag in ('p','div','section','h1','h2','h3','h4','li','blockquote','pre'):self.parts.append('\n')

def shell(title, body, path='/', description=None, article=None):
    description = description or CONFIG['description']
    person = {'@type':'Person','@id':BASE+'/#author','name':'Sylan','url':BASE+'/', 'sameAs':['https://x.com/syunnng2','https://github.com/ningsiyuan1024',CONFIG['linktree']]}
    structured = {'@context':'https://schema.org', '@type':'Blog', '@id':BASE+'/#blog', 'name':'Sylan', 'url':BASE,'inLanguage':'zh-CN','author':person}
    if article:
        citations = list(dict.fromkeys([article['source_url']]+article.get('alternate_sources',[])+METRICS.get('additional_sources',{}).get(article['slug'],[])))
        structured.update({'@type':'BlogPosting','@id':BASE+path+'#article','url':BASE+path, 'headline':article['title'], 'description':description,'datePublished':article['published_at'], 'mainEntityOfPage':BASE+path, 'isBasedOn':article['source_url'],'citation':citations,'isPartOf':{'@id':BASE+'/#blog'},'image':BASE+(article.get('cover') or '/assets/avatar.png')})
    structured_json = json.dumps(structured,ensure_ascii=False).replace('<','\\u003c')
    social_image = BASE + (article.get('cover') or '/assets/avatar.png') if article else BASE + '/assets/avatar.png'
    text_alternate = f'<link rel="alternate" type="text/plain" href="{path}index.txt">' if path.endswith('/') else ''
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)} · Sylan</title><meta name="description" content="{E(description, quote=True)}">
<meta name="theme-color" content="#f5f1e8"><link rel="icon" href="/assets/avatar.png">
<link rel="canonical" href="{BASE}{path}"><link rel="alternate" type="application/rss+xml" title="Sylan" href="/feed.xml">
{text_alternate}<meta name="robots" content="index,follow,max-image-preview:large">
<meta property="og:type" content="{'article' if article else 'website'}"><meta property="og:title" content="{E(title, quote=True)}">
<meta property="og:description" content="{E(description, quote=True)}"><meta property="og:url" content="{BASE}{path}">
<meta property="og:image" content="{social_image}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{E(title, quote=True)}"><meta name="twitter:description" content="{E(description, quote=True)}"><meta name="twitter:image" content="{social_image}"><link rel="stylesheet" href="/assets/style.css">
<script type="application/ld+json">{structured_json}</script></head>
<body><a class="skip" href="#main">跳到正文</a><header class="masthead"><a class="brand" href="/">Sylan<span>.</span></a>
<nav aria-label="主导航"><a href="/">文章</a><a href="{CONFIG['linktree']}">Linktree ↗</a><a href="/feed.xml">RSS</a></nav></header>
{body}<footer class="footer"><a href="/">Sylan</a><div><a href="https://github.com/ningsiyuan1024">GitHub ↗</a><a href="{CONFIG['linktree']}">各平台主页 ↗</a></div><a href="#top" aria-label="回到顶部">↑</a></footer>
<script src="/assets/app.js" defer></script></body></html>'''

def write(path, content):
    dest = OUT / path; dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding='utf-8')

def article_extras(post):
    urls = list(dict.fromkeys([post['source_url']] + post.get('alternate_sources',[]) +
                            METRICS.get('additional_sources',{}).get(post['slug'],[])))
    rows = []
    for url in urls:
        entry = METRICS['sources'].get(url,{})
        platform = entry.get('platform') or ('微信公众号' if 'mp.weixin.qq.com/' in url else
                    'X' if 'x.com/' in url else '知乎' if 'zhihu.com/' in url else
                    'B站' if 'bilibili.com/' in url else '今日头条' if 'toutiao.com/' in url else '原平台')
        values = []
        for metric in entry.get('metrics',[]):
            # Preserve native names and displayed counts, including genuine zeroes.
            if metric.get('display') is not None:
                values.append(f'<span>{E(metric["label"])} <b>{E(str(metric["display"]))}</b></span>')
        timestamp = entry.get('observed_at')
        if values and not timestamp: raise ValueError('Counters require an observation time: '+url)
        if values:
            stamp = datetime.fromisoformat(timestamp).astimezone(timezone(timedelta(hours=8)))
            updated = f'<time datetime="{E(timestamp,quote=True)}">{stamp:%Y.%m.%d %H:%M} UTC+8</time>'
        else:
            values = ['<span class="metrics-unavailable">数据暂未获取</span>']
            updated = ''
        rows.append(f'<li><a href="{E(url,quote=True)}">{E(platform)} ↗</a><div>{"".join(values)}</div>{updated}</li>')
    stats = '<section class="article-metrics" aria-label="本文各平台数据"><ul>'+''.join(rows)+'</ul></section>'
    author = CONFIG['author_footer']
    directions = ''.join(f'<div><h3>{E(item["title"])}</h3><p>{E(item["text"])}</p></div>' for item in author['directions'])
    bio = f'''<aside class="author-note" aria-label="关于 Sylan"><div class="author-note-head"><img src="/assets/avatar.png" width="40" height="40" alt=""><div><h2>Sylan</h2><p>{E(author['intro'])}</p></div></div><div class="author-directions">{directions}</div><div class="author-contact"><span>微信：{E(author['wechat'])}</span><a href="{CONFIG['linktree']}">各平台与联系 ↗</a></div></aside>'''
    return stats + bio

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
        if not p['text'] and '<img' not in p['html']: raise ValueError('Empty article')
        # Text-note platforms sometimes put the whole note into the title field.
        # Use its original first line for navigation; retain all wording in the body.
        if len(p['title']) > 100:
            first = next((line.strip() for line in p['title'].splitlines() if line.strip()),p['title'])
            p['title'] = first[:80] + ('…' if len(first)>80 else '')
        p['description'] = p['text'][:130] or p['title']
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
        content = f'''<main id="main" class="article-page"><a class="back" href="/">← 所有文章</a><header class="article-header" id="top"><div class="meta"><time datetime="{p['published_at']}">{p['published_at'][:10].replace('-','.')}</time><span>{p['minutes']} 分钟</span><a href="{E(p['source_url'],quote=True)}">原平台：{E(p.get('platform','原平台'))} ↗</a></div><h1>{E(p['title'])}</h1><div class="byline"><img src="/assets/avatar.png" width="28" height="28" alt="">Sylan</div></header><div class="prose">{p['html']}</div>{article_extras(p)}<div class="article-end"><a href="{E(p['source_url'],quote=True)}">阅读原平台版本 ↗</a><a href="/">返回文章列表 →</a></div></main>'''
        write('articles/'+p['slug']+'/index.html',shell(p['title'],content,p['path'],p['description'],p))
        readable=ReadableText();readable.feed(p['html'])
        text_body=re.sub(r'\n[ \t]*\n(?:[ \t]*\n)+','\n\n',''.join(readable.parts)).strip()
        write('articles/'+p['slug']+'/index.txt',f"{p['title']}\n\n作者：Sylan\n原发表日期：{p['published_at']}\n博客地址：{BASE}{p['path']}\n原平台：{p['source_url']}\n\n{text_body}\n")
    body = f'''<main id="main"><section class="intro" id="top"><div><p class="eyebrow">Sylan 的个人博客</p><h1>AI、Agent<br>与创造<span>。</span></h1></div><img class="portrait" src="/assets/avatar.png" alt="Sylan 的黑猫头像" width="152" height="152"></section><section class="archive" aria-labelledby="archive-title"><div class="archive-head"><h2 id="archive-title">文章 <span>{len(posts):02d}</span></h2><label class="search"><span class="sr-only">搜索文章</span><input id="search" type="search" placeholder="搜索文章" autocomplete="off"><span aria-hidden="true">⌕</span></label></div><div id="articles">{''.join(cards)}</div><p id="no-results" hidden role="status">没有找到相关文章。</p></section></main>'''
    write('index.html',shell('个人博客',body))
    listing='\n'.join(f"- [{p['title']}]({BASE}{p['path']}): {p['published_at']} · 原平台 {p['source_url']} · [全文文本]({BASE}{p['path']}index.txt)" for p in posts)
    write('index.txt',f'Sylan\n\n{CONFIG["description"]}\n\n{listing}\n')
    write('llms.txt',f'# Sylan\n\n> Sylan 已公开发表文章的个人博客。\n\n## 作者与来源\n\n- [X](https://x.com/syunnng2)\n- [GitHub](https://github.com/ningsiyuan1024)\n- [Linktree]({CONFIG["linktree"]})\n\n文章保留原发表日期与原平台来源。译文、节选和引用的原始作者信息见各篇正文。\n\n## 文章\n\n{listing}\n\n## 订阅与目录\n\n- [RSS]({BASE}/feed.xml)\n- [站点地图]({BASE}/sitemap.xml)\n')
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
