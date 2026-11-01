import os, re, json, html as html_lib
from urllib.parse import quote
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def _load(filename: str) -> str:
    with open(ROOT / filename, 'r', encoding='utf-8') as handle:
        return handle.read()

def _documentation_root() -> str:
    return os.path.join(str(ROOT), 'Documentation')

def _documentation_file(*parts: str) -> str:
    return os.path.join(_documentation_root(), *parts)

def _safe_slug(value: str, *, separator: str='-') -> str:
    clean = re.sub('[^a-z0-9]+', separator, str(value or '').lower()).strip(separator)
    return re.sub(f'{re.escape(separator)}+', separator, clean) or 'command'

def _command_url_slug(command_name: str) -> str:
    return _safe_slug(command_name, separator='-')

def _command_file_slug(command_name: str) -> str:
    return _safe_slug(command_name, separator='_')

def _render_doc_inline(value: str) -> str:
    escaped = html_lib.escape(value or '')
    return re.sub('\\*\\*(.+?)\\*\\*', '<strong>\\1</strong>', escaped)

def _render_doc_markdown(markdown_text: str) -> str:
    rendered: list[str] = []
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            rendered.append('</ul>')
            in_list = False
    for raw_line in (markdown_text or '').replace('\r\n', '\n').split('\n'):
        line = raw_line.strip()
        if not line:
            close_list()
            continue
        if line.startswith('# '):
            close_list()
            rendered.append(f'<h1>{_render_doc_inline(line[2:].strip())}</h1>')
        elif line.startswith('## '):
            close_list()
            rendered.append(f'<h2>{_render_doc_inline(line[3:].strip())}</h2>')
        elif line.startswith('-# '):
            close_list()
            rendered.append(f'<p class="doc-note">{_render_doc_inline(line[3:].strip())}</p>')
        elif line.startswith('- '):
            if not in_list:
                rendered.append('<ul>')
                in_list = True
            rendered.append(f'<li>{_render_doc_inline(line[2:].strip())}</li>')
        else:
            close_list()
            rendered.append(f'<p>{_render_doc_inline(line)}</p>')
    close_list()
    return '\n'.join(rendered)

def _documentation_heading_links(body: str) -> tuple[str, list[tuple[str, str]]]:
    links: list[tuple[str, str]] = []
    used: set[str] = set()

    def replace_heading(match: re.Match) -> str:
        tag = match.group(1)
        attrs = match.group(2) or ''
        inner_html = match.group(3)
        text = re.sub('<[^>]+>', '', inner_html).strip()
        if not text:
            return match.group(0)
        id_match = re.search('\\sid=["\\\']([^"\\\']+)["\\\']', attrs)
        if id_match:
            anchor = id_match.group(1)
        else:
            base = _safe_slug(html_lib.unescape(text), separator='-')
            anchor = base
            counter = 2
            while anchor in used:
                anchor = f'{base}-{counter}'
                counter += 1
            attrs = f'{attrs} id="{html_lib.escape(anchor)}"'
        used.add(anchor)
        links.append((anchor, html_lib.unescape(text)))
        return f'<{tag}{attrs}>{inner_html}</{tag}>'
    updated = re.sub('<(h[12])([^>]*)>(.*?)</\\1>', replace_heading, body, flags=re.IGNORECASE | re.DOTALL)
    return (updated, links)

def _read_documentation_markdown(*parts: str, strip_name_line: bool=False) -> tuple[str | None, str | None]:
    path = _documentation_file(*parts)
    if not os.path.exists(path):
        return (None, None)
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            text = handle.read()
    except OSError:
        return (None, None)
    display_name = None
    lines = text.replace('\r\n', '\n').split('\n')
    if lines and lines[0].strip().startswith('{name:') and lines[0].strip().endswith('}'):
        display_name = lines[0].strip()[6:-1].strip() or None
        if strip_name_line:
            text = '\n'.join(lines[1:])
    return (_render_doc_markdown(text), display_name)

def _documentation_command_category(command_name: str, source_category: str) -> str:
    normalized_command = ' '.join(str(command_name or '').casefold().split())
    command_root = normalized_command.split(' ', 1)[0] if normalized_command else ''
    normalized_source = re.sub('[^a-z0-9]+', ' ', str(source_category or '').casefold()).strip()
    if command_root == 'engine' or normalized_command in {'debug grant', 'debug revoke'}:
        return 'Owner Restricted'
    if command_root == 'callout':
        return 'Callouts Roleplay'
    if command_root == 'tools':
        return 'Server Tools'
    if command_root in {'economy', 'eco', 'blackeconomy'}:
        return 'Economy'
    if command_root == 'counter':
        return 'Counter'
    if command_root == 'custom':
        return 'Custom Profile'
    if command_root == 'fun':
        return 'Fun and Games'
    if command_root == 'member':
        return 'Member Information'
    if command_root == 'npc':
        return 'NPC Autoresponders'
    if command_root in {'quote', 'quotes'}:
        return 'Quotes'
    if command_root == 'staff':
        return 'Staff Management'
    if command_root == 'ticket':
        return 'Tickets'
    if command_root in {'welcome', 'verification', 'verify', 'booster', 'servertag', 'left'}:
        return 'Arrival System'
    if normalized_command == 'dropdown embed' or normalized_source in {'embed', 'embeds and message systems'}:
        return 'Embed System'
    if normalized_source in {'core and information', 'help', 'invites and access', 'prefix'}:
        return 'Information'
    if normalized_source == 'moderation':
        return 'Moderation'
    return 'Utility'

def _load_secretary_commands_for_docs() -> list[dict]:
    try:
        commands_js = _load('secretary-commands.js')
        match = re.search('root\\.SECRETARY_COMMANDS\\s*=\\s*(\\[[\\s\\S]*?\\]);', commands_js)
        if not match:
            return []
        loaded = json.loads(match.group(1))
    except Exception:
        return []
    commands_data = []
    seen = set()
    for command in loaded:
        if not isinstance(command, dict):
            continue
        command_name = str(command.get('command') or command.get('name') or '').strip().lstrip('/')
        if not command_name:
            continue
        slug = _command_url_slug(command_name)
        if slug in seen:
            continue
        seen.add(slug)
        source_category = str(command.get('docsCategory') or command.get('category') or command.get('module') or 'General').strip()
        commands_data.append({'name': f'/{command_name}', 'command': command_name, 'slug': slug, 'file_slug': _command_file_slug(command_name), 'description': str(command.get('description') or command.get('details') or 'No description available.').strip(), 'details': str(command.get('details') or command.get('description') or 'No detailed notes available.').strip(), 'category': _documentation_command_category(command_name, source_category), 'module': str(command.get('module') or command.get('category') or 'General').strip(), 'usage': str(command.get('usage') or f'/{command_name}').strip(), 'help_usage': str(command.get('helpUsage') or '').strip(), 'search': str(command.get('search') or '').strip()})
    return sorted(commands_data, key=lambda item: (item['category'].lower(), item['command'].lower()))

def _documentation_top_command_categories(limit: int=8) -> list[str]:
    counts: dict[str, int] = {}
    for command in _load_secretary_commands_for_docs():
        category = command.get('category') or 'General'
        counts[category] = counts.get(category, 0) + 1
    return [category for category, _count in sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))[:limit]]

def _docs_changelog_version_key(title: str) -> tuple[int, tuple[int, ...], str]:
    match = re.search('v(\\d+(?:\\.\\d+){0,3})', str(title or ''), flags=re.IGNORECASE)
    if not match:
        return (0, (), str(title or '').lower())
    return (1, tuple((int(part) for part in match.group(1).split('.'))), str(title or '').lower())

def _documentation_layout(*, active: str, eyebrow: str, title: str, intro: str, body: str, right_links: list[tuple[str, str]], next_card: tuple[str, str, str] | None=None) -> str:
    nav = {'welcome': '', 'changelog': '', 'extralogs': '', 'getting-started': '', 'permissions': '', 'commandlogs': ''}
    if active in nav:
        nav[active] = ' active'
    body, generated_links = _documentation_heading_links(body)
    right_links = generated_links or right_links
    right_html = '\n'.join((f'<a href="#{html_lib.escape(anchor)}">{html_lib.escape(label)}</a>' for anchor, label in right_links))
    category_links = ''.join((f'<a class="nav-sub-item" href="/documentation/commandlogs?category={html_lib.escape(quote(category))}">{html_lib.escape(category)}</a>' for category in _documentation_top_command_categories()))
    next_html = ''
    if next_card:
        next_href, next_title, next_label = next_card
        next_html = f'<a class="next-card" href="{html_lib.escape(next_href)}">{html_lib.escape(next_title)}<span>{html_lib.escape(next_label)}</span></a>'
    return f'''<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8" />\n  <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n  <title>{html_lib.escape(title)} | The Secretary Documentation</title>\n  <meta name="twitter:description" content="Read The Secretary Discord bot documentation, setup guides, permissions, changelogs, and complete command reference." />\n  <meta name="twitter:title" content="{html_lib.escape(title)} | The Secretary Documentation" />\n  <meta name="twitter:card" content="summary_large_image" />\n  <meta name="twitter:image" content="https://thesecretary.xyz/meta/documentation.png" />\n  <meta name="description" content="Read The Secretary Discord bot documentation, setup guides, permissions, changelogs, and complete command reference." />\n  <meta property="og:image:height" content="903" />\n  <meta property="og:image:width" content="1900" />\n  <meta property="og:image" content="https://thesecretary.xyz/meta/documentation.png" />\n  <meta property="og:site_name" content="The Secretary" />\n  <meta property="og:type" content="website" />\n  <meta property="og:description" content="Read The Secretary Discord bot documentation, setup guides, permissions, changelogs, and complete command reference." />\n  <meta property="og:title" content="{html_lib.escape(title)} | The Secretary Documentation" />\n  <link rel="icon" href="https://gshergd.github.io/site-assets/favicon.png" />\n  <link rel="preconnect" href="https://fonts.googleapis.com" />\n  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />\n  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800;900&display=swap" rel="stylesheet" />\n  <style>\n    :root {{ --bg:#090a0d; --panel:#0f1014; --panel2:#151720; --line:#252834; --text:#f0f2f7; --muted:#a0a4af; --soft:#c9ced8; --yellow:#e8df31; --blue:#6c94ff; --green:#5ce1a0; }}\n    * {{ box-sizing:border-box; }}\n    html {{ scroll-behavior:smooth; }}\n    body {{ margin:0; min-height:100vh; background:var(--bg); color:var(--text); font-family:"Inter",system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}\n    a {{ color:inherit; text-decoration:none; }}\n    .docs-layout {{ min-height:100vh; display:grid; grid-template-columns:20rem minmax(0,1fr) 16rem; }}\n    .left-nav {{ position:sticky; top:0; height:100vh; overflow:auto; padding:1.35rem 1.25rem 2rem; border-right:1px solid var(--line); background:#0b0c0f; }}\n    .left-nav {{ scrollbar-width:none; -ms-overflow-style:none; }}\n    .left-nav::-webkit-scrollbar {{ width:0; height:0; }}\n    .brand {{ display:flex; align-items:center; gap:.7rem; margin-bottom:2rem; font-weight:900; }}\n    .brand img {{ width:2rem; height:2rem; border-radius:50%; box-shadow:0 0 0 1px rgba(255,255,255,.18); }}\n    .top-links {{ display:grid; gap:.85rem; margin-bottom:2.4rem; color:var(--muted); font-weight:650; }}\n    .top-links a:hover {{ color:var(--yellow); }}\n    .nav-section {{ padding:1.2rem 0; border-top:1px solid var(--line); }}\n    .nav-title {{ margin:0 0 .75rem; color:#d9dbe2; font-size:.78rem; font-weight:900; }}\n    .nav-list {{ display:grid; gap:.25rem; }}\n    .nav-item {{ display:flex; align-items:center; justify-content:space-between; gap:.75rem; min-height:2.25rem; padding:.45rem .75rem; border-radius:.6rem; color:var(--muted); font-weight:650; }}\n    .nav-item:hover,.nav-item.active {{ color:var(--yellow); background:rgba(232,223,49,.09); }}\n    .new {{ color:var(--yellow); background:#07212d; padding:.12rem .35rem; border-radius:.35rem; font-size:.65rem; font-weight:900; }}\n    .doc-main {{ padding:2.5rem clamp(2rem,5vw,5.5rem) 5rem; max-width:60rem; width:100%; margin:0 auto; }}\n    .eyebrow {{ color:var(--yellow); font-size:.9rem; font-weight:900; margin:0 0 .75rem; }}\n    h1 {{ margin:0 0 .65rem; font-size:clamp(2.1rem,4vw,3rem); line-height:1.05; letter-spacing:-.05em; }}\n    h2 {{ margin:3.25rem 0 1rem; font-size:1.55rem; letter-spacing:-.035em; scroll-margin-top:2rem; }}\n    p {{ color:var(--muted); line-height:1.72; font-size:1.02rem; }}\n    strong {{ color:#fff; }}\n    ul {{ color:var(--muted); line-height:1.75; padding-left:1.25rem; }}\n    .hero-copy {{ margin:0 0 2.5rem; font-size:1.12rem; color:#aeb3bf; }}\n    .banner {{ height:3.4rem; margin:2.6rem 0 2.5rem; border-radius:.35rem; background:linear-gradient(90deg,#18264e,#274bc0,#18264e); position:relative; overflow:hidden; border:1px solid #2f3b65; }}\n    .banner::before {{ content:""; position:absolute; inset:0; background:repeating-linear-gradient(135deg,transparent 0 15px,rgba(255,255,255,.08) 15px 16px); opacity:.7; }}\n    .banner img {{ position:absolute; left:50%; top:50%; width:3rem; height:3rem; border-radius:50%; transform:translate(-50%,-50%); background:#fff; }}\n    .callout,.changelog-card,.command-panel {{ border:1px solid var(--line); border-radius:.8rem; background:var(--panel); padding:1rem; }}\n    .callout {{ border-left:3px solid var(--yellow); }}\n    .doc-note {{ display:inline-block; margin:.25rem 0; padding:.45rem .65rem; border:1px solid var(--line); border-radius:.55rem; background:#11131a; color:#cbd3ea; font-size:.92rem; }}\n    .changelog-card {{ margin-top:1rem; }}\n    .changelog-card h2 {{ margin-top:0; }}\n    .changelog-meta {{ display:flex; flex-wrap:wrap; gap:.5rem; color:var(--muted); font-size:.85rem; margin:.5rem 0 1rem; }}\n    .badge {{ display:inline-flex; align-items:center; border:1px solid var(--line); border-radius:999px; padding:.2rem .55rem; color:var(--soft); background:#11131a; font-size:.78rem; font-weight:800; }}\n    .pager {{ display:flex; justify-content:space-between; gap:1rem; margin-top:1.5rem; }}\n    .pager a,.pager span {{ border:1px solid var(--line); border-radius:.6rem; padding:.65rem .85rem; color:var(--soft); background:#0d0e12; }}\n    .next-card {{ display:block; width:fit-content; min-width:11.5rem; max-width:100%; margin:2.4rem 0 0 auto; border:1px solid var(--line); border-radius:.7rem; padding:.8rem .95rem; color:#fff; background:#0d0e12; text-align:right; }}\n    .next-card span {{ display:block; color:var(--muted); margin-top:.18rem; }}\n    .nav-sub-item {{ display:block; margin:.1rem 0 .1rem 1rem; padding:.32rem .55rem; border-radius:.5rem; color:var(--muted); font-size:.86rem; font-weight:650; }}\n    .nav-sub-item:hover {{ color:var(--yellow); background:rgba(232,223,49,.07); }}\n    .command-tools {{ display:grid; grid-template-columns:1fr auto; gap:.75rem; margin:1rem 0; }}\n    .search,.category-select {{ min-height:2.8rem; border:1px solid var(--line); border-radius:.55rem; background:#0d0e12; color:#fff; padding:0 .85rem; outline:none; font:inherit; }}\n    .search:focus,.category-select:focus {{ border-color:var(--blue); box-shadow:0 0 0 3px rgba(108,148,255,.16); }}\n    .command-list {{ display:grid; gap:.7rem; margin-top:1rem; }}\n    .command-row {{ display:block; border:1px solid var(--line); border-radius:.65rem; background:#0d0e12; padding:.9rem; }}\n    .command-row:hover {{ border-color:#3e5eb5; background:#111522; }}\n    .command-head {{ display:flex; align-items:center; justify-content:space-between; gap:.75rem; margin-bottom:.45rem; }}\n    .command-name {{ color:#fff; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-weight:800; }}\n    .command-desc {{ white-space:pre-line; color:var(--muted); line-height:1.65; margin:.35rem 0 .75rem; font-size:.94rem; }}\n    .usage {{ color:#cbd3ea; background:#090a0d; border:1px solid var(--line); border-radius:.45rem; padding:.55rem .65rem; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:.85rem; }}\n    .command-panel + h1,.command-panel + h2 {{ margin-top:2.6rem; }}\n    .command-panel + p,.command-panel + .doc-note,.command-panel + ul {{ margin-top:2rem; }}\n    .right-nav {{ position:sticky; top:0; height:100vh; padding:3.5rem 1.2rem; border-left:1px solid var(--line); background:#0b0c0f; color:var(--muted); }}\n    .right-nav-title {{ color:#cfd2da; font-weight:900; margin-bottom:.7rem; }}\n    .right-nav a {{ display:block; padding:.35rem 0 .35rem .75rem; border-left:2px solid transparent; color:var(--muted); font-size:.9rem; }}\n    .right-nav a:hover,.right-nav a.active {{ color:var(--yellow); border-left-color:var(--yellow); }}\n    .docs-mobile-header,.docs-menu-toggle,.docs-nav-scrim {{ display:none; }}\n    @media(max-width:1100px){{.docs-layout{{grid-template-columns:17rem minmax(0,1fr)}}.right-nav{{display:none}}.doc-main{{padding-inline:2rem}}}}\n    @media(max-width:760px){{\n      html{{scrollbar-width:none}}\n      html::-webkit-scrollbar{{display:none}}\n      body.docs-menu-open{{overflow:hidden}}\n      .docs-layout{{display:block}}\n      .docs-mobile-header{{position:fixed;inset:0 0 auto;z-index:130;height:76px;display:block;padding:8px 12px;pointer-events:none}}\n      .docs-mobile-header-inner{{position:relative;width:100%;height:60px;display:grid;grid-template-columns:44px minmax(0,1fr) 44px;align-items:center;padding:0 8px;border:1px solid rgba(255,255,255,.12);border-radius:999px;background:rgba(10,10,12,.82);box-shadow:0 18px 42px rgba(0,0,0,.3);backdrop-filter:blur(18px) saturate(130%);-webkit-backdrop-filter:blur(18px) saturate(130%);pointer-events:auto}}\n      .docs-menu-toggle{{position:relative;z-index:2;width:38px;height:38px;display:grid;place-content:center;gap:4px;padding:0;border:1px solid #343744;border-radius:50%;background:#111216;color:#fff;cursor:pointer}}\n      .docs-menu-toggle span{{display:block;width:16px;height:1.5px;border-radius:99px;background:currentColor;transition:transform .2s ease,opacity .16s ease}}\n      body.docs-menu-open .docs-menu-toggle span:nth-child(1){{transform:translateY(5.5px) rotate(45deg)}}\n      body.docs-menu-open .docs-menu-toggle span:nth-child(2){{opacity:0}}\n      body.docs-menu-open .docs-menu-toggle span:nth-child(3){{transform:translateY(-5.5px) rotate(-45deg)}}\n      .docs-mobile-brand{{min-width:0;display:inline-flex;align-items:center;justify-content:center;gap:.6rem;justify-self:center;color:#fff;font-size:.82rem;font-weight:900;white-space:nowrap}}\n      .docs-mobile-brand img{{width:30px;height:30px;border-radius:50%;object-fit:cover;background:#fff}}\n      .docs-mobile-brand span{{overflow:hidden;text-overflow:ellipsis}}\n      .docs-mobile-spacer{{width:38px;height:38px;justify-self:end}}\n      .left-nav{{position:fixed;inset:0 auto 0 0;z-index:120;width:min(20rem,86vw);height:100dvh;padding:5rem 1.25rem 2rem;box-shadow:22px 0 60px rgba(0,0,0,.45);transform:translateX(-104%);transition:transform .24s cubic-bezier(.22,1,.36,1);overscroll-behavior:contain}}\n      .left-nav>.brand{{display:none}}\n      .left-nav.open{{transform:translateX(0)}}\n      .docs-nav-scrim{{position:fixed;inset:0;z-index:110;display:block;background:rgba(0,0,0,.6);opacity:0;visibility:hidden;pointer-events:none;transition:opacity .2s ease,visibility .2s ease}}\n      .docs-nav-scrim.open{{opacity:1;visibility:visible;pointer-events:auto}}\n      .doc-main{{padding:5.4rem 1rem 3rem}}\n      .command-tools{{grid-template-columns:1fr}}\n    }}\n  </style>\n</head>\n<body>\n  <header class="docs-mobile-header">\n    <div class="docs-mobile-header-inner">\n      <button id="docsMenuToggle" class="docs-menu-toggle" type="button" aria-label="Open documentation navigation" aria-controls="docsNavigation" aria-expanded="false"><span></span><span></span><span></span></button>\n      <a class="docs-mobile-brand" href="/"><img src="https://gshergd.github.io/site-assets/favicon.png" alt="" /><span>The Secretary</span></a>\n      <span class="docs-mobile-spacer" aria-hidden="true"></span>\n    </div>\n  </header>\n  <div id="docsNavScrim" class="docs-nav-scrim" aria-hidden="true"></div>\n  <div class="docs-layout">\n    <aside id="docsNavigation" class="left-nav">\n      <a class="brand" href="/"><img src="https://gshergd.github.io/site-assets/favicon.png" alt="The Secretary" /> <span>The Secretary</span></a>\n      <nav class="top-links"><a href="/">Home</a><a href="/premium">Premium</a><a href="/dashboard">Dashboard</a><a href="https://thesecretary.xyz/invite">Support</a></nav>\n      <section class="nav-section"><p class="nav-title">Overview</p><div class="nav-list"><a class="nav-item{nav['welcome']}" href="/documentation/welcome">Welcome</a><a class="nav-item{nav['changelog']}" href="/documentation/changelog">Changelog <span class="new">NEW</span></a><a class="nav-item{nav['extralogs']}" href="/documentation/extralogs">Extra Logs</a></div></section>\n      <section class="nav-section"><p class="nav-title">Configuration</p><div class="nav-list"><a class="nav-item{nav['getting-started']}" href="/documentation/getting-started">Getting Started</a><a class="nav-item{nav['permissions']}" href="/documentation/permissions">Permissions</a></div></section>\n      <section class="nav-section"><p class="nav-title">Reference</p><div class="nav-list"><a class="nav-item{nav['commandlogs']}" href="/documentation/commandlogs">Command Reference</a>{category_links}</div></section>\n    </aside>\n    <main class="doc-main">\n      <p class="eyebrow">{html_lib.escape(eyebrow)}</p>\n      <h1>{html_lib.escape(title)}</h1>\n      <p class="hero-copy">{html_lib.escape(intro)}</p>\n      {body}\n      {next_html}\n    </main>\n    <aside class="right-nav"><div class="right-nav-title">On this page</div>{right_html}</aside>\n  </div>\n  <script>\n    (() => {{\n      const button = document.getElementById("docsMenuToggle");\n      const navigation = document.getElementById("docsNavigation");\n      const scrim = document.getElementById("docsNavScrim");\n      const setOpen = (open) => {{\n        navigation.classList.toggle("open", open);\n        scrim.classList.toggle("open", open);\n        document.body.classList.toggle("docs-menu-open", open);\n        button.setAttribute("aria-expanded", String(open));\n        button.setAttribute("aria-label", open ? "Close documentation navigation" : "Open documentation navigation");\n      }};\n      button.addEventListener("click", () => setOpen(!navigation.classList.contains("open")));\n      scrim.addEventListener("click", () => setOpen(false));\n      navigation.querySelectorAll("a").forEach(link => link.addEventListener("click", () => setOpen(false)));\n      document.addEventListener("keydown", event => {{ if (event.key === "Escape") setOpen(false); }});\n      window.addEventListener("resize", () => {{ if (window.innerWidth > 760) setOpen(false); }});\n    }})();\n  </script>\n</body>\n</html>'''

def _documentation_welcome_body() -> str:
    fixed = 'The Secretary is a multipurpose Discord management bot focused on moderation, tickets, automation, economy, roleplay systems, and server operations without forcing staff into messy manual workflows.'
    extra, _ = _read_documentation_markdown('welcome.md')
    return f"""<section id="about"><h2>About The Secretary</h2><p><strong>The Secretary</strong> {html_lib.escape(fixed[len('The Secretary '):])}</p><div class="banner"><img src="https://gshergd.github.io/site-assets/favicon.png" alt="The Secretary" /></div>{extra or ''}</section>"""

def _documentation_standard_body(page: str) -> str:
    defaults = {'gettingstarted': '<section id="setup"><h2>Getting Started</h2><p>Invite The Secretary, grant the requested permissions, then open the dashboard to connect your Discord account and choose the server you want to configure.</p><ul><li>Use the dashboard for server-specific settings.</li><li>Keep Discord role order above the roles the bot needs to manage.</li><li>Test welcome, verification, tickets, and moderation flows in a private channel before public launch.</li></ul></section>', 'permissions': '<section id="permissions"><h2>Permissions</h2><p>The Secretary needs the Discord permissions required by the features you enable. Moderation tools need moderation permissions, role tools need role management, and messaging tools need channel access.</p><ul><li>Administrator is simplest for full setup.</li><li>Role management depends on Discord role hierarchy.</li><li>Webhook, embed, and welcome tools need message and channel permissions.</li></ul></section>', 'extralogs': '<section id="extra-logs"><h2>Extra Logs</h2><p>Additional logs for some special features of the bot that requires usage guide.</p></section>', 'commandlogs': '<section id="reference"><h2>Command Reference</h2><p>Complete list of all existing commands usable by users and developers. Each command include possible errors and thier possible fixes.</p></section>'}
    custom, _ = _read_documentation_markdown(f'{page}.md')
    return custom or defaults.get(page, '')

def _documentation_commands_body() -> str:
    commands_data = _load_secretary_commands_for_docs()
    categories = sorted({command['category'] for command in commands_data})
    intro = _documentation_standard_body('commandlogs')
    category_options = '\n'.join((f'<option value="{html_lib.escape(category)}">{html_lib.escape(category)}</option>' for category in categories))
    rows = []
    for command in commands_data:
        rows.append(f'''<a class="command-row" href="/documentation/commandlogs/{html_lib.escape(command['slug'])}" data-category="{html_lib.escape(command['category'])}" data-search="{html_lib.escape((command['search'] or command['command'] + ' ' + command['description']).lower())}">\n  <div class="command-head"><span class="command-name">{html_lib.escape(command['name'])}</span><span class="badge">{html_lib.escape(command['category'])}</span></div>\n  <div class="command-desc">{html_lib.escape(command['description'])}</div>\n  <div class="usage">{html_lib.escape(command['usage'])}</div>\n</a>''')
    return f"""{intro}\n<section id="commands">\n  <h2>All Commands</h2>\n  <p>{len(commands_data)} commands are available in the current generated command reference.</p>\n  <div class="command-tools">\n    <input class="search" id="commandSearch" type="search" placeholder="Search commands..." autocomplete="off" />\n    <select class="category-select" id="commandCategory"><option value="">All categories</option>{category_options}</select>\n  </div>\n  <div class="command-list" id="commandList">{(''.join(rows) if rows else '<div class="command-panel"><p>No command data is available right now.</p></div>')}</div>\n</section>\n<script>\n  const commandSearch = document.getElementById("commandSearch");\n  const commandCategory = document.getElementById("commandCategory");\n  const commandRows = [...document.querySelectorAll(".command-row")];\n  const presetCategory = new URLSearchParams(window.location.search).get("category");\n  function filterCommands() {{\n    const query = (commandSearch.value || "").trim().toLowerCase();\n    const category = commandCategory.value;\n    commandRows.forEach((row) => {{\n      const categoryMatch = !category || row.dataset.category === category;\n      const queryMatch = !query || row.dataset.search.includes(query);\n      row.style.display = categoryMatch && queryMatch ? "" : "none";\n    }});\n  }}\n  if (presetCategory && [...commandCategory.options].some((option) => option.value === presetCategory)) {{\n    commandCategory.value = presetCategory;\n  }}\n  filterCommands();\n  commandSearch.addEventListener("input", filterCommands);\n  commandCategory.addEventListener("change", filterCommands);\n</script>"""

def _documentation_command_detail_body(command_slug: str) -> tuple[str, str, str]:
    commands_data = _load_secretary_commands_for_docs()
    command = next((item for item in commands_data if item['slug'] == command_slug), None)
    if not command:
        abort(404)
    manual, _ = _read_documentation_markdown('commands', f"{command['file_slug']}.md")
    body = f"""<section id="command">\n  <h2>{html_lib.escape(command['name'])}</h2>\n  <p>{html_lib.escape(command['details'])}</p>\n  <div class="command-panel">\n    <p><strong>Category:</strong> {html_lib.escape(command['category'])}</p>\n    <p><strong>Module:</strong> {html_lib.escape(command['module'])}</p>\n    <div class="usage">{html_lib.escape(command['usage'])}</div>\n  </div>\n  {manual or ''}\n</section>"""
    return (command['name'], command['description'], body)