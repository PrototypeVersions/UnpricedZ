"""Publish readable copies of research documents and frozen records, never new results."""
from __future__ import annotations

import hashlib
import html
import json
import posixpath
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

REPO = 'https://github.com/PrototypeVersions/UnpricedZ'
HUB = 'https://raw.githubusercontent.com/PrototypeVersions/UnpricedHub/main/site/data/hub.json'
ROOT = Path(__file__).resolve().parents[1]
JSON_FILES = ['config.json', 'risk_lab/registry.json', 'research_program/registry.json',
              'analysis/program-0.1.0/41759065718-1/variance-decomposition.json',
              'archive/program/program-0.1.0/41759065718-1/report.json',
              'archive/program/program-0.1.0/41759065718-1/selection-audit.json']


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def page_path(source):
    return Path(source).with_suffix('.html').as_posix()


def json_view(value, depth=0):
    """Readable exact values, with full nested content available without GitHub."""
    if isinstance(value, dict):
        if depth > 2:
            return '<pre>' + html.escape(json.dumps(value, indent=2, ensure_ascii=False)) + '</pre>'
        return '<dl class="reference-values">' + ''.join(
            '<div><dt>' + html.escape(str(k)) + '</dt><dd>' + json_view(v, depth+1) + '</dd></div>'
            for k, v in value.items()) + '</dl>'
    if isinstance(value, list):
        if not value:
            return '<span class="muted">Empty list</span>'
        if all(not isinstance(x, (dict, list)) for x in value):
            return '<code>' + html.escape(json.dumps(value, ensure_ascii=False)) + '</code>'
        return ''.join('<details><summary>Item ' + str(i+1) + '</summary>' + json_view(v, depth+1) + '</details>'
                       for i, v in enumerate(value))
    return '<code>' + html.escape(json.dumps(value, ensure_ascii=False)) + '</code>'


class DocumentHTML(HTMLParser):
    """Keep document HTML inert and rewrite links to the corresponding on-site copies."""
    tags = set('h1 h2 h3 h4 h5 h6 p ul ol li a table thead tbody tr td th em strong blockquote pre code hr br details summary dl dt dd div span sup sub'.split())

    def __init__(self, source, available):
        super().__init__(convert_charrefs=False)
        self.source, self.available, self.output = source, available, []

    def link(self, href):
        parsed = urlsplit(href)
        if href.startswith(REPO + '/blob/main/'):
            target = parsed.path.split('/blob/main/', 1)[1]
        elif parsed.scheme:
            return href if parsed.scheme in ('https', 'http') else '#'
        elif not parsed.path:
            return href
        else:
            target = posixpath.normpath(posixpath.join(posixpath.dirname(self.source), parsed.path))
        suffix = '#' + parsed.fragment if parsed.fragment else ''
        if target in self.available:
            return posixpath.relpath(page_path(target), posixpath.dirname(page_path(self.source)) or '.') + suffix
        if target.startswith('site/data/'):
            return posixpath.relpath('../' + target[5:], posixpath.dirname(page_path(self.source)) or '.') + suffix
        return REPO + '/blob/main/' + target + suffix

    def handle_starttag(self, tag, attrs):
        if tag not in self.tags:
            return
        safe = []
        for key, value in attrs:
            if key in ('id', 'class', 'title', 'colspan', 'rowspan'):
                safe.append((key, value or ''))
            elif key == 'href' and tag == 'a':
                safe.append((key, self.link(value or '')))
        self.output.append('<' + tag + ''.join(' '+k+'="'+html.escape(v, quote=True)+'"' for k,v in safe) + '>')

    def handle_endtag(self, tag):
        if tag in self.tags:
            self.output.append('</'+tag+'>')

    def handle_data(self, data):
        self.output.append(html.escape(data))

    def handle_entityref(self, name):
        self.output.append('&'+name+';')

    def handle_charref(self, name):
        self.output.append('&#'+name+';')


def shell(title, body, depth=0, source=None, sha=None):
    prefix = '../' * (depth + 1)
    canonical = 'https://prototypeversions.github.io/UnpricedZ/reference/' + (page_path(source) if source else 'records.html' if title == 'Frozen forecast ledger' else 'index.html')
    provenance = ''
    if source:
        raw = posixpath.relpath('raw/'+source, posixpath.dirname(page_path(source)) or '.')
        provenance = '<div class="reference-provenance"><p>Source: <code>'+html.escape(source)+'</code></p>' \
            + '<p>Exact source-file SHA-256: <code>'+sha+'</code></p>' \
            + '<a download href="'+html.escape(raw)+'">Download the original file</a> · ' \
            + '<a href="'+REPO+'/blob/main/'+html.escape(source)+'">Optional: view source on GitHub ↗</a></div>'
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' \
        + '<title>'+html.escape(title)+' · UNPRICED</title><link rel="stylesheet" href="'+prefix+'styles.css">' \
        + '<link rel="canonical" href="'+html.escape(canonical,quote=True)+'"><meta property="og:url" content="'+html.escape(canonical,quote=True)+'">' \
        + '<meta name="theme-color" content="#F5F2EA"><meta property="og:type" content="article"><meta property="og:site_name" content="UNPRICED">' \
        + '<meta property="og:title" content="'+html.escape(title,quote=True)+' · UNPRICED"><meta property="og:description" content="Read the Market &amp; Sector Risk Lab’s methods, original research and public records.">' \
        + '<meta property="og:image" content="https://prototypeversions.github.io/UnpricedZ/assets/unpriced-paper-ink-social-v1.png"><meta property="og:image:width" content="1734"><meta property="og:image:height" content="907">' \
        + '<meta property="og:image:alt" content="Unpriced. Forecasts, put to the test. Ink lettering and teal market paths on warm paper."><meta name="twitter:card" content="summary_large_image">' \
        + '<meta name="twitter:image" content="https://prototypeversions.github.io/UnpricedZ/assets/unpriced-paper-ink-social-v1.png">' \
        + '<link rel="icon" href="'+prefix+'assets/unpriced-paper-ink-icon-v1.png" type="image/png" sizes="1254x1254"><link rel="icon" href="'+prefix+'assets/favicon-paper-ink-v2.svg" type="image/svg+xml" sizes="any">' \
        + '<link rel="apple-touch-icon" href="'+prefix+'assets/unpriced-paper-ink-icon-v1.png"></head><body>' \
        + '<a class="skip" href="#content">Skip to document</a><header class="masthead"><div class="masthead-top"><a class="wordmark" href="'+prefix+'#risk">Unpriced<span class="wordmark-dot">.</span></a><p>Market &amp; Sector Risk Lab · UnpricedZ</p></div>' \
        + '<nav class="primary-nav" aria-label="Main navigation">' \
        + ''.join('<a href="'+prefix+'#'+route+'">'+label+'</a>' for route,label in [('risk','Overview'),('outlook','Forecasts'),('portfolio','$1,000 experiment'),('record','Results'),('experiments','Research'),('methods','Methods'),('about','About')]) \
        + '</nav></header><main class="reference-page" id="content"><p class="reference-breadcrumb"><a href="'+prefix+'#methods">Methods &amp; documents</a> / '+html.escape(title)+'</p>' \
        + body + provenance + '</main><footer>UNPRICED · Published research documents and records. <a href="'+prefix+'#about">Understand the project</a></footer></body></html>\n'


def collect_sources(root):
    paths = list(root.glob('docs/*.md'))
    paths += [root / p for p in JSON_FILES if (root/p).is_file()]
    paths += list(root.glob('site/data/*.json'))
    paths = [p for p in paths if p.name not in ('presentation.json','reader.json')]
    paths += list(root.glob('records/forecasts/*.json')) + list(root.glob('records/resolutions/*.json'))
    paths += list(root.glob('risk_records/*/forecasts/*.json')) + list(root.glob('risk_records/*/resolutions/*.json'))
    paths += list(root.glob('archive/program/*/*/report.json')) + list(root.glob('archive/program/*/*/selection-audit.json'))
    paths += list(root.glob('risk_archive/*/*/*/report.json'))
    return sorted(set(paths))


def reader_context(root, hub=None):
    def read(path):
        p=root/path
        return json.loads(p.read_text()) if p.is_file() else {}
    cfg, live = read('config.json'), read('site/data/live.json')
    plans = live.get('portfolio',{}).get('plans',[])
    decision = None
    if plans:
        plan=plans[-1]
        # Dates originate in the lab's own public record; refuse path traversal.
        date=datetime.strptime(plan['signalDate'],'%Y-%m-%d').date().isoformat()
        snap=read('records/forecasts/'+date+'.json')
        if snap and snap.get('experiment')==cfg.get('experiment'):
            decision={k:snap.get(k) for k in ['snapshotId','sessionDate','publishedAt','entryDate','exitDate','forecasts']}
            decision['plan']=plan
    risk=read('site/data/risk.json')
    receipt={'status':'unavailable','checkedAt':datetime.now(timezone.utc).isoformat(), 'source':HUB, 'exports':[]}
    if hub:
        lab=next((l for l in hub.get('labs',[]) if l.get('id')=='risk-lab'),None)
        if lab:
            receipt.update(status='available',sourceUpdatedAt=hub.get('updatedAt'),counts=lab.get('receipts',{}))
            for path in sorted((root/'site/data/export').glob('latest-*.json')):
                doc=json.loads(path.read_text())
                r=next((r for r in lab.get('recent',[]) if r.get('forecastId')==doc.get('forecastId')),None)
                receipt['exports'].append({'forecastId':doc.get('forecastId'),'task':doc.get('task',{}).get('description'),
                                          'receipt':r,'matches':bool(r and r.get('sha256')==digest(path.read_bytes()))})
    return {'builtAt':datetime.now(timezone.utc).isoformat(),'riskForecastId':risk.get('latest',{}).get('forecastId'),
            'riskRegistry':read('risk_lab/registry.json'),'directionExperiment':cfg.get('experiment'),
            'portfolioRules':cfg.get('portfolio'),'liveUpdatedAt':live.get('updatedAt'),
            'portfolioDecision':decision,'hub':receipt}


def build(root, hub=None):
    import markdown
    output=root/'site/reference'
    output.mkdir(parents=True,exist_ok=True)
    paths=collect_sources(root)
    available={p.relative_to(root).as_posix() for p in paths}
    manifest=[]
    for path in paths:
        source=path.relative_to(root).as_posix()
        raw=path.read_bytes()
        title=source
        if path.suffix=='.md':
            text=raw.decode('utf-8')
            title=next((line.lstrip('# ').strip() for line in text.splitlines() if line.startswith('# ')),source)
            parser=DocumentHTML(source,available)
            parser.feed(markdown.markdown(text,extensions=['tables','fenced_code','toc']))
            body='<article class="document-content">'+''.join(parser.output)+'</article>'
        else:
            value=json.loads(raw)
            title=source.replace('site/data/','Published report / ')
            body='<h1>'+html.escape(title)+'</h1><p class="muted">Exact recorded values. Nested entries expand below; the original JSON is available at the bottom.</p>'+json_view(value)
        target=output/page_path(source)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(shell(title,body,len(Path(source).parts)-1,source,digest(raw)))
        copy=output/'raw'/source
        copy.parent.mkdir(parents=True,exist_ok=True)
        copy.write_bytes(raw)
        manifest.append({'source':source,'title':title,'page':page_path(source),'sha256':digest(raw)})
    groups=[('Research documents',lambda p:p.startswith('docs/')),
            ('Exact settings',lambda p:p in ['config.json','risk_lab/registry.json','research_program/registry.json']),
            ('Published reports',lambda p:p.startswith(('site/data/','analysis/','archive/','risk_archive/'))),
            ('Frozen forecasts and outcomes',lambda p:p.startswith(('records/','risk_records/')))]
    sections=''
    for heading,match in groups:
        entries=[m for m in manifest if match(m['source'])]
        sections+='<section class="section"><h2>'+heading+'</h2><ul class="document-list">'+''.join(
            '<li><a href="'+m['page']+'">'+html.escape(m['title'])+'</a></li>' for m in entries)+'</ul></section>'
    (output/'index.html').write_text(shell('Documents & records','<h1>Documents &amp; records</h1><p>Read the complete research plans, settings and published records without leaving this site. Historical documents retain the dates, conclusions and limitations of their original versions.</p>'+sections))
    records=[m for m in manifest if m['source'].startswith(('records/','risk_records/'))]
    (output/'records.html').write_text(shell('Frozen forecast ledger','<h1>Frozen forecast ledger</h1><p>Every listed file is a copy of the recorded forecast or resolution, with its exact hash and an original-file download. The Risk Lab and continuing direction study retain separate records.</p><ul class="document-list">'+''.join('<li><a href="'+m['page']+'">'+html.escape(m['source'])+'</a></li>' for m in records)+'</ul>'))
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (root/'site/data/reader.json').write_text(json.dumps(reader_context(root,hub),separators=(',',':'),allow_nan=False)+'\n')
    return manifest


if __name__=='__main__':
    hub=None
    try:
        with urlopen(HUB,timeout=15) as response:
            hub=json.load(response)
    except Exception as exc:
        print('Hub context unavailable; the site will show that explicitly:',type(exc).__name__)
    manifest=build(ROOT,hub)
    print('Published',len(manifest),'readable documents and records; originals were not modified.')
