from pathlib import Path
import json, shutil

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


