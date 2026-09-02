"""
Idempotent retrofit: add the share button (btn-share) to every existing
blog post that doesn't already have one. Safe to re-run — files that
already contain 'btn-share' are skipped.

Mirrors the exact markup generate_post.py writes for new posts, so old
and new posts end up identical.
"""
import html
import re
from pathlib import Path

BLOG_DIR = Path(__file__).resolve().parent.parent / "blog"

AUTHOR_LINE_RE = re.compile(
    r'(<span>כת[בה]: <a href="https://www\.amzfreeil\.com/about\.html" style="color:inherit">אילן</a></span>\n)'
    r'(\s*)(</div>)'
)
TITLE_RE = re.compile(r'<title>([^<]*)</title>')


def slug_for(path: Path) -> str:
    return path.stem


def title_for(html_text: str) -> str:
    m = TITLE_RE.search(html_text)
    if not m:
        return ""
    raw = m.group(1)
    # title is "<post title> | AMZ Free Ship Alert" -> keep the post-title part
    return raw.split(" | ")[0].strip()


def main():
    changed = 0
    skipped_has_btn = 0
    skipped_no_match = []

    for f in sorted(BLOG_DIR.glob("*.html")):
        if f.name == "index.html":
            continue
        text = f.read_text(encoding="utf-8")

        if "btn-share" in text:
            skipped_has_btn += 1
            continue

        slug = slug_for(f)
        title = html.escape(title_for(text), quote=True)

        def repl(m):
            indent = m.group(2)
            btn = (
                f'{indent}<span class="blog-meta-sep">·</span>\n'
                f'{indent}<button type="button" class="btn-share" data-slug="{slug}" '
                f'data-title="{title}">\U0001f517 שתף</button>\n'
            )
            return m.group(1) + btn + indent + m.group(3)

        new_text, n = AUTHOR_LINE_RE.subn(repl, text, count=1)
        if n == 0:
            skipped_no_match.append(f.name)
            continue

        f.write_text(new_text, encoding="utf-8")
        changed += 1

    print(f"Updated: {changed}")
    print(f"Already had button: {skipped_has_btn}")
    print(f"No match (needs manual check): {len(skipped_no_match)}")
    for name in skipped_no_match:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
