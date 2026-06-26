"""
Publish a draft blog post: remove noindex and push to git.
Usage: python tools/publish_post.py <slug>
Example: python tools/publish_post.py samsung-990-pro-ssd-2tb-amazon-israel
"""
import sys
import subprocess
from pathlib import Path

TOOLS_DIR = Path(__file__).parent
PROJECT_DIR = TOOLS_DIR.parent
BLOG_DIR = PROJECT_DIR / "blog"


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/publish_post.py <slug>")
        print("Example: python tools/publish_post.py samsung-990-pro-ssd-2tb-amazon-israel")
        sys.exit(1)

    slug = sys.argv[1].removesuffix(".html")
    post_path = BLOG_DIR / f"{slug}.html"

    if not post_path.exists():
        print(f"Error: blog/{slug}.html not found")
        sys.exit(1)

    content = post_path.read_text(encoding="utf-8")

    if 'content="noindex,nofollow"' not in content:
        print(f"⚠️  blog/{slug}.html has no noindex tag — already published?")
        sys.exit(0)

    content = content.replace(
        '  <meta name="robots" content="noindex,nofollow" />\n', ""
    )
    post_path.write_text(content, encoding="utf-8")
    print(f"✅ Removed noindex from blog/{slug}.html")

    subprocess.run(
        ["git", "add", f"blog/{slug}.html"],
        cwd=str(PROJECT_DIR), check=True
    )
    subprocess.run(
        ["git", "commit", "-m", f"blog: publish {slug}"],
        cwd=str(PROJECT_DIR), check=True
    )
    subprocess.run(["git", "push"], cwd=str(PROJECT_DIR), check=True)

    print(f"\n🚀 Published: https://www.amzfreeil.com/blog/{slug}.html")


if __name__ == "__main__":
    main()
