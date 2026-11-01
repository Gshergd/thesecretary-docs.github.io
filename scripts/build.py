"""Build standalone docs. Run from any directory; no bot, database, or packages required."""
from pathlib import Path
import argparse, html, json, os, re, shutil
import rendering as r
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument("--source-root", required=True, help="Path to The Secretary checkout (read-only content source)")
p.add_argument('--base-path',default='/The-Secretary-Documentation')
a=p.parse_args()
base='/' + a.base_path.strip('/') if a.base_path.strip('/') else ''
SOURCE=Path(a.source_root).resolve()
if not (SOURCE/"Documentation").is_dir() or not (SOURCE/"secretary-commands.js").is_file():
    p.error("--source-root must contain Documentation/ and secretary-commands.js")
r.ROOT=SOURCE
os.chdir(ROOT)
out=ROOT/'dist'
out.mkdir(exist_ok=True)
pages={}

def page(route,title,body,active='welcome',intro=''):
    content=r._documentation_layout(active=active,eyebrow='Documentation',title=title,intro=intro,body=body,right_links=[])
    def link(m):
        target=m.group(2)
        if target.startswith('/documentation'):
            target=base+target.split('?',1)[0].rstrip('/')+'/index.html'+(('?'+target.split('?',1)[1]) if '?' in target else '')
        elif target.startswith('/') and not target.startswith('//'):
            target='https://thesecretary.xyz'+target
        return m.group(1)+target+m.group(3)
    content=re.sub(r'((?:href|src)=\")([^\"]+)(\")',link,content)
    # The runtime layout embeds CSS; keep website styling in a dedicated file.
    style=re.search(r'<style>([\s\S]*?)</style>',content)
    if style:
        (out/'styles.css').write_text(style.group(1),encoding='utf-8')
        content=content[:style.start()]+f'<link rel="stylesheet" href="{base}/styles.css">'+content[style.end():]
    canonical='https://gshergd.github.io'+base+'/'+route
    content=content.replace('</head>',f'<link rel="canonical" href="{canonical}"></head>')
    target=out/route
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(content,encoding='utf-8')
    pages[route]=title

page('documentation/welcome/index.html','Welcome to The Secretary',r._documentation_welcome_body())
for slug,file,title in [('extralogs','extralogs','Extra Logs'),('getting-started','gettingstarted','Getting Started'),('permissions','permissions','Permissions')]:
    page(f'documentation/{slug}/index.html',title,r._documentation_standard_body(file),slug)
page('documentation/commandlogs/index.html','Command Reference',r._documentation_commands_body(),'commandlogs')
commands=r._load_secretary_commands_for_docs()
for command in commands:
    title,intro,body=r._documentation_command_detail_body(command['slug'])
    page(f"documentation/commandlogs/{command['slug']}/index.html",title,body,'commandlogs',intro)
# Preserve manuals even when an older manual has no matching generated command.
manuals=[]
for file in sorted((SOURCE/'Documentation'/'commands').glob('*.md')):
    slug=file.stem.replace('_','-')
    route=f'documentation/commandlogs/{slug}/index.html'
    if route not in pages:
        body,_=r._read_documentation_markdown('commands',file.name)
        page(route,file.stem.replace('_',' '),body or '', 'commandlogs')
    manuals.append(f'<li><a href="/documentation/commandlogs/{slug}">{html.escape(file.stem.replace("_"," "))}</a></li>')
page('documentation/manuals/index.html','All Command Manuals','<ul>'+''.join(manuals)+'</ul>','commandlogs')
entries=[]
for file in (SOURCE/'Documentation'/'changelogs').glob('*.md'):
    body,title=r._read_documentation_markdown('changelogs',file.name,strip_name_line=True)
    if not (body or '').strip(): continue
    title=title or ('Latest update notes' if file.stem=='new' else file.stem)
    entries.append((file.stem,title,body))
entries.sort(key=lambda x:(x[0]=='new',r._docs_changelog_version_key(x[1])),reverse=True)
for i in range(0,len(entries),10):
    n=i//10+1
    route='documentation/changelog/index.html' if n==1 else f'documentation/changelog/page-{n}/index.html'
    cards=''.join(f'<article class="changelog-card"><h2>{html.escape(title)}</h2><p class="badge">{html.escape(stem)}</p>{body}</article>' for stem,title,body in entries[i:i+10])
    nav=' '.join(f'<a href="/documentation/changelog'+('' if j==1 else f'/page-{j}')+f'">{j}</a>' for j in range(1,(len(entries)+9)//10+1))
    page(route,'Changelogs',cards+f'<nav class="pager" aria-label="Changelog pages">{nav}</nav>','changelog')
# Additional documentation remains accessible through a public guide index.
guides=[]
for file in sorted((SOURCE/'Documentation').glob('*.md')):
    if file.stem in {'welcome','gettingstarted','permissions','extralogs'}: continue
    slug=re.sub('[^a-z0-9]+','-',file.stem.lower()).strip('-')
    body,_=r._read_documentation_markdown(file.name)
    page(f'documentation/guides/{slug}/index.html',file.stem,body or '')
    guides.append(f'<li><a href="/documentation/guides/{slug}">{html.escape(file.stem)}</a></li>')
page('documentation/guides/index.html','More Guides','<ul>'+''.join(guides)+'</ul><p><a href="/documentation/manuals">Browse all command manuals</a></p>')
# Make additional guides discoverable in every sidebar.
for route in pages:
    f=out/route
    s=f.read_text(encoding='utf-8').replace('</aside>',f'<a class="nav-item" href="{base}/documentation/guides/index.html">More Guides</a></aside>',1)
    f.write_text(s,encoding='utf-8')
shutil.copy2(out/'documentation/welcome/index.html',out/'index.html')
(out/'.nojekyll').touch()
(out/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>https://gshergd.github.io'+base+'/'+route+'</loc></url>' for route in pages)+'</urlset>',encoding='utf-8')
# Check all generated local links and fragment targets before deployment.
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
class Links(HTMLParser):
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k in ('href','src') and v: links.append(v)
errors=[]
for f in out.rglob('*.html'):
    links=[]; parser=Links(); parser.feed(f.read_text(encoding='utf-8'))
    for v in links:
        u=urlsplit(v)
        if u.scheme or u.netloc or not u.path: continue
        path=unquote(u.path)
        target=out/path[len(base):].lstrip('/') if base and path.startswith(base+'/') else f.parent/path
        if not target.exists(): errors.append(f'{f.relative_to(out)} -> {v}')
if errors: raise SystemExit('\n'.join(errors))
print(f'Built and checked {len(pages)+1} HTML pages, {len(commands)} commands, {len(entries)} changelogs.')
