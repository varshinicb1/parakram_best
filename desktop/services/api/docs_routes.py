"""
Docs API — Serve markdown docs via API for the landing page.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
import re

router = APIRouter()

DOCS_DIR = Path(__file__).parent.parent.parent / "docs"


def md_to_html(md: str) -> str:
    """Simple markdown to HTML (headers, code, bold, links, tables)."""
    lines = md.split('\n')
    html_lines = []
    in_code = False
    in_table = False

    for line in lines:
        # Code blocks
        if line.strip().startswith('```'):
            if in_code:
                html_lines.append('</code></pre>')
                in_code = False
            else:
                lang = line.strip().replace('```', '') or 'text'
                html_lines.append(f'<pre><code class="{lang}">')
                in_code = True
            continue
        if in_code:
            html_lines.append(line.replace('<', '&lt;').replace('>', '&gt;'))
            continue

        # Tables
        if '|' in line and line.strip().startswith('|'):
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if all(set(c) <= set('-: ') for c in cells):
                continue
            if not in_table:
                html_lines.append('<table>')
                tag = 'th'
                in_table = True
            else:
                tag = 'td'
            row = ''.join(f'<{tag}>{c}</{tag}>' for c in cells)
            html_lines.append(f'<tr>{row}</tr>')
            continue
        elif in_table:
            html_lines.append('</table>')
            in_table = False

        # Headers
        if line.startswith('# '):
            html_lines.append(f'<h1>{line[2:]}</h1>')
        elif line.startswith('## '):
            html_lines.append(f'<h2>{line[3:]}</h2>')
        elif line.startswith('### '):
            html_lines.append(f'<h3>{line[4:]}</h3>')
        elif line.startswith('---'):
            html_lines.append('<hr>')
        elif line.strip() == '':
            html_lines.append('<br>')
        else:
            # Inline formatting
            processed = line
            processed = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', processed)
            processed = re.sub(r'`(.+?)`', r'<code class="inline">\1</code>', processed)
            processed = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', processed)
            html_lines.append(f'<p>{processed}</p>')

    if in_table:
        html_lines.append('</table>')

    return '\n'.join(html_lines)


DOC_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — Parakram Docs</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',sans-serif;background:#060609;color:#d0d0dd;line-height:1.7;padding:2rem;max-width:800px;margin:0 auto}}
a{{color:#6da3ff;text-decoration:none}}a:hover{{color:#fff}}
h1{{font-size:1.8rem;font-weight:800;color:#eeeef5;margin:2rem 0 1rem;letter-spacing:-0.5px}}
h2{{font-size:1.3rem;font-weight:700;color:#eeeef5;margin:1.5rem 0 0.5rem;border-bottom:1px solid #1a1a24;padding-bottom:6px}}
h3{{font-size:1rem;font-weight:600;color:#c0c0d0;margin:1rem 0 0.5rem}}
p{{margin:0.3rem 0}}hr{{border:none;border-top:1px solid #1a1a24;margin:2rem 0}}
pre{{background:#0c0c12;border:1px solid #1a1a24;padding:1rem;overflow-x:auto;margin:0.5rem 0;font-size:0.82rem}}
code{{font-family:'JetBrains Mono',monospace;font-size:0.85rem}}
code.inline{{background:#0c0c12;border:1px solid #1a1a24;padding:2px 6px;color:#6da3ff}}
table{{width:100%;border-collapse:collapse;margin:0.5rem 0;font-size:0.85rem}}
th,td{{border:1px solid #1a1a24;padding:8px 12px;text-align:left}}
th{{background:#0c0c12;color:#eeeef5;font-weight:600;font-size:0.75rem;letter-spacing:1px;text-transform:uppercase}}
.back{{display:inline-block;margin-bottom:1.5rem;font-size:0.8rem;color:#55556a}}
</style></head><body>
<a href="/" class="back">← Back to Parakram</a>
{content}
</body></html>"""


@router.get("/docs/{slug}")
async def serve_doc(slug: str):
    """Serve a markdown doc as styled HTML."""
    safe_slug = re.sub(r'[^a-zA-Z0-9_-]', '', slug)
    doc_path = DOCS_DIR / f"{safe_slug}.md"
    if not doc_path.exists():
        raise HTTPException(404, f"Doc '{slug}' not found")
    md_content = doc_path.read_text(encoding='utf-8')
    title = safe_slug.replace('-', ' ').title()
    html_body = md_to_html(md_content)
    return HTMLResponse(DOC_TEMPLATE.format(title=title, content=html_body))


@router.get("/docs")
async def list_docs():
    """List available docs."""
    if not DOCS_DIR.exists():
        return {"docs": []}
    docs = []
    for f in sorted(DOCS_DIR.glob("*.md")):
        docs.append({"slug": f.stem, "title": f.stem.replace('-', ' ').title(), "path": f"/docs/{f.stem}"})
    return {"docs": docs}
