from pathlib import Path
from urllib.parse import urlparse
import json, shutil
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parent.parent
out = root / 'site-output'
if out.exists():
    shutil.rmtree(out)
out.mkdir()
for item in root.iterdir():
    if item.name.startswith('.') or item.name in ('site-output', 'scripts', 'node_modules'):
        continue
    if item.is_dir():
        shutil.copytree(item, out / item.name)
    else:
        shutil.copy2(item, out / item.name)

# Add a self-referencing canonical to every URL listed in the sitemap. Keeping
# this derived from the sitemap prevents future pages from being deployed
# without a canonical and ensures www/non-www variants consolidate correctly.
namespace = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
for location in ET.parse(root / 'sitemap.xml').findall('.//s:loc', namespace):
    canonical = location.text.strip()
    path = urlparse(canonical).path
    if path == '/':
        page = out / 'index.html'
    elif path.startswith('/post/'):
        page = out / ('post-' + path.removeprefix('/post/') + '.html')
    else:
        page = out / (path.strip('/') + '.html')
    html = page.read_text()
    if 'rel="canonical"' not in html:
        html = html.replace('</title>', f'</title>\n<link rel="canonical" href="{canonical}">', 1)
        page.write_text(html)

config = json.loads((root / 'staticwebapp.config.json').read_text())
routes = []
aliases = {}
for route in config['routes']:
    url = route['route']
    if url.startswith('/post-') and route.get('redirect'):
        stem = url.removesuffix('.html')
        aliases[stem] = route['redirect']
    elif url.startswith('/post/') and route.get('rewrite') and (root / route['rewrite'].lstrip('/')).exists():
        # Azure serves /post/slug from /post/slug.html without a rewrite rule.
        target = out / (url.lstrip('/') + '.html')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / route['rewrite'].lstrip('/'), target)
    else:
        routes.append(route)
# Longest first prevents one article's prefix from shadowing another's alias.
redirects = [{'route': stem + '*', 'redirect': aliases[stem], 'statusCode': 301}
             for stem in sorted(aliases, key=lambda s: (-len(s), s))]
config['routes'] = redirects + routes
config['trailingSlash'] = 'never'
encoded = json.dumps(config, separators=(',', ':'))
assert len(encoded.encode()) < 20000, 'Azure configuration exceeds 20 KB'
(out / 'staticwebapp.config.json').write_text(encoded)
print(f'Prepared site with {len(aliases)} legacy blog redirects; configuration {len(encoded.encode())} bytes')

