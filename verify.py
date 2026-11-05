"""Check article integrity, generated local links, image files, RSS and sitemap."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
from xml.etree import ElementTree as ET
import hashlib
import json

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'dist'
class Links(HTMLParser):
    def __init__(self): super().__init__(); self.links=[]
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k in ('href','src') and v: self.links.append(v)

def verify():
    articles=list((ROOT/'content').glob('*/article.json'))
    if not articles: raise ValueError('Cannot deploy an empty blog')
    for file in articles:
        p=json.loads(file.read_text(encoding='utf-8')); raw=(file.parent/'body.html').read_text(encoding='utf-8').encode('utf-8')
        assert p['status']=='published_verified' and p['text_preserved']
        assert hashlib.sha256(raw).hexdigest()==p['body_sha256'], file
        assert (OUT/'articles'/p['slug']/'index.html').is_file(), file
    checked=0
    for file in OUT.rglob('*.html'):
        parser=Links(); parser.feed(file.read_text(encoding='utf-8'))
        for link in parser.links:
            u=urlsplit(link)
            if u.scheme or u.netloc or not u.path: continue
            target=(OUT/unquote(u.path).lstrip('/')) if u.path.startswith('/') else file.parent/unquote(u.path)
            if target.is_dir(): target=target/'index.html'
            assert target.is_file(), f'Broken link in {file}: {link}'
            checked+=1
    rss=ET.parse(OUT/'feed.xml'); sitemap=ET.parse(OUT/'sitemap.xml')
    assert len(rss.findall('./channel/item'))==len(articles)
    assert len(sitemap.getroot())==len(articles)+1
    print(json.dumps({'articles_verified':len(articles),'local_links_verified':checked,'rss':'passed','sitemap':'passed'}))

if __name__=='__main__': verify()
