"""Import one verified public snapshot. Never scans drafts or publishes by itself."""
from pathlib import Path
from html.parser import HTMLParser
from html import escape
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import argparse
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
ALLOWED = set('p div section article span strong b em i u s mark h1 h2 h3 h4 h5 h6 ul ol li blockquote pre code a img br hr table thead tbody tr td th sup sub figure figcaption video source'.split())
VOID = {'img','br','hr','source'}
DROP = {'script','style','iframe','noscript','form','button','input','svg'}

class Cleaner(HTMLParser):
    def __init__(self, source_url, folder, slug):
        super().__init__(convert_charrefs=True)
        self.out=[]; self.stack=[]; self.skip=0; self.source_url=source_url
        self.folder=folder; self.slug=slug; self.assets={}; self.warnings=[]
    def media(self, raw):
        url=urljoin(self.source_url, raw)
        if url in self.assets: return self.assets[url]['path']
        if urlparse(url).scheme not in ('http','https'): raise ValueError('Unsupported media URL')
        request=Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':self.source_url})
        with urlopen(request, timeout=40) as response:
            mime=response.headers.get_content_type(); blob=response.read()
        extensions={'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp','image/gif':'.gif','image/avif':'.avif'}
        if mime not in extensions or not blob: raise ValueError(f'Unsupported image response: {mime}')
        name=hashlib.sha256(blob).hexdigest()[:24]+extensions[mime]
        (self.folder/'assets').mkdir(parents=True,exist_ok=True)
        (self.folder/'assets'/name).write_bytes(blob)
        path=f'/articles/{self.slug}/assets/{name}'
        self.assets[url]={'path':path,'sha256':hashlib.sha256(blob).hexdigest(),'bytes':len(blob)}
        return path
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag in DROP:
            if tag not in {'input'}: self.skip+=1
            return
        if self.skip or tag not in ALLOWED: return
        kept={}
        if tag=='img':
            raw=attrs.get('data-src') or attrs.get('src')
            if not raw: return
            kept={'src':self.media(raw),'alt':attrs.get('alt',''),'loading':'lazy'}
        elif tag=='a':
            url=urljoin(self.source_url,attrs.get('href',''))
            if urlparse(url).scheme in ('http','https','mailto'): kept={'href':url,'rel':'noopener noreferrer'}
        elif tag in ('video','source'):
            self.warnings.append('Video needs source-platform playback')
            return
        if tag in ('td','th'):
            for name in ('colspan','rowspan'):
                if attrs.get(name,'').isdigit(): kept[name]=attrs[name]
        style=[]
        for part in attrs.get('style','').split(';'):
            key,_,value=part.partition(':'); key=key.strip().lower(); value=value.strip()
            if key in ('color','background-color','font-weight','font-style','text-decoration','text-align') and re.fullmatch(r'[a-zA-Z0-9#(),.%\s-]+',value): style.append(key+':'+value)
        if style: kept['style']=';'.join(style)
        self.out.append('<'+tag+''.join(f' {k}="{escape(v,quote=True)}"' for k,v in kept.items())+'>')
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag,attrs)
        if tag not in VOID: self.handle_endtag(tag)
    def handle_endtag(self, tag):
        if tag in DROP:
            self.skip=max(0,self.skip-1); return
        if not self.skip and tag in ALLOWED and tag not in VOID and tag not in ('video','source'): self.out.append('</'+tag+'>')
    def handle_data(self, data):
        if not self.skip: self.out.append(escape(data))

def run(path):
    src=json.loads(path.read_text(encoding='utf-8-sig'))
    for key in ('slug','title','published_at','source_url','html'):
        if not src.get(key): raise ValueError(f'Missing {key}')
    if src.get('status')!='published_verified': raise ValueError('An explicitly verified public snapshot is required')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*',src['slug']): raise ValueError('Invalid slug')
    if urlparse(src['source_url']).scheme!='https': raise ValueError('HTTPS public source required')
    folder=ROOT/'content'/src['slug']; folder.mkdir(parents=True,exist_ok=True)
    cleaner=Cleaner(src['source_url'],folder,src['slug']); cleaner.feed(src['html']); cleaner.close()
    body=''.join(cleaner.out).replace('\r\n','\n').replace('\r','\n')
    from build import plain
    if re.sub(r'\s','',plain(src['html'])) != re.sub(r'\s','',plain(body)):
        raise ValueError('Article text changed during import; inspect embedded content')
    cover=cleaner.media(src['cover_url']) if src.get('cover_url') else next((x['path'] for x in cleaner.assets.values()),None)
    # Explicit public metadata only: no account tokens, local paths or raw browser snapshots.
    metadata={k:src[k] for k in ('slug','title','published_at','source_url','platform','status') if k in src}
    metadata.update({'cover':cover,'source_html_sha256':hashlib.sha256(src['html'].encode()).hexdigest(),'body_sha256':hashlib.sha256(body.encode()).hexdigest(),'text_preserved':True,'asset_count':len(cleaner.assets),'warnings':sorted(set(cleaner.warnings))})
    (folder/'body.html').write_bytes(body.encode('utf-8'))
    (folder/'article.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('snapshot',type=Path)
    run(parser.parse_args().snapshot)
