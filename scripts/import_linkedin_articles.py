#!/usr/bin/env python3
"""Import Chandan's LinkedIn articles as static, first-party portfolio pages."""

from __future__ import annotations

import json
import re
from datetime import datetime
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
PROFILE_URL = "https://www.linkedin.com/in/chandan-venkatesh-53884428/"
USER_AGENT = "Mozilla/5.0 (compatible; ChandanPortfolioArticleImporter/1.0)"

ARTICLES = [
    {
        "slug": "future-of-e-commerce",
        "topic": "Agentic commerce",
        "url": "https://www.linkedin.com/pulse/future-e-commerce-your-next-customer-may-never-browse-venkatesh-psqee",
    },
    {
        "slug": "adaptive-storefront-continued",
        "topic": "Generative UI",
        "url": "https://www.linkedin.com/pulse/adaptive-storefront-continued-chandan-venkatesh-oqzde",
    },
    {
        "slug": "starbucks-ai-supply-chain-reliability",
        "topic": "AI operating models",
        "url": "https://www.linkedin.com/pulse/starbucks-ai-inventory-story-really-supply-chain-lesson-venkatesh-mkpde",
    },
    {
        "slug": "one-refactor-two-ai-assistants",
        "topic": "AI-assisted engineering",
        "description": "A comparative field report on using two coding assistants against the same real-world 5,552-line Python refactor.",
        "url": "https://www.linkedin.com/pulse/one-refactor-two-ai-assistants-5000-lines-chandan-venkatesh-sydfe",
    },
    {
        "slug": "sunday-star-wars-retro",
        "topic": "Agent workflows",
        "url": "https://www.linkedin.com/pulse/sunday-startwars-retro-made-my-ai-team-run-me-darth-venkatesh-9l4le",
    },
]

ALLOWED_TAGS = {
    "p",
    "h2",
    "h3",
    "h4",
    "ul",
    "ol",
    "li",
    "strong",
    "em",
    "b",
    "i",
    "a",
    "br",
    "blockquote",
    "code",
    "pre",
}
VOID_TAGS = {"br"}


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=45) as response:
        return response.read()


class LinkedInArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.schema: dict = {}
        self._in_schema = False
        self._schema_parts: list[str] = []
        self._capture = False
        self._capture_depth = 0
        self._block_parts: list[str] = []
        self.blocks: list[str] = []
        self.poster_url: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "script" and attributes.get("type") == "application/ld+json":
            self._in_schema = True
            self._schema_parts = []

        if tag == "video" and attributes.get("data-poster-url"):
            self.poster_url = attributes["data-poster-url"]

        if (
            not self._capture
            and tag == "div"
            and attributes.get("data-test-id") == "publishing-text-block"
            and "article-main__content" in (attributes.get("class") or "")
        ):
            self._capture = True
            self._capture_depth = 1
            self._block_parts = []
            return

        if not self._capture:
            return

        if tag == "div":
            self._capture_depth += 1
        if tag not in ALLOWED_TAGS:
            return
        if tag == "a":
            href = attributes.get("href") or ""
            self._block_parts.append(f'<a href="{escape(href, quote=True)}" rel="noreferrer">')
        elif tag in VOID_TAGS:
            self._block_parts.append(f"<{tag}>")
        else:
            self._block_parts.append(f"<{tag}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_schema:
            self._in_schema = False
            try:
                candidate = json.loads("".join(self._schema_parts))
                if candidate.get("@type") == "Article":
                    self.schema = candidate
            except (json.JSONDecodeError, AttributeError):
                pass

        if not self._capture:
            return
        if tag == "div":
            self._capture_depth -= 1
            if self._capture_depth == 0:
                self._capture = False
                block = "".join(self._block_parts).strip()
                if block:
                    self.blocks.append(block)
                return
        if tag in ALLOWED_TAGS and tag not in VOID_TAGS:
            self._block_parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if self._in_schema:
            self._schema_parts.append(data)
        if self._capture:
            self._block_parts.append(escape(data))


def paragraphize_pre(block: str) -> str:
    if not (block.startswith("<pre>") and block.endswith("</pre>")):
        return block
    text = block[5:-6].strip()
    chunks = re.split(r"\n\s*\n", text)
    output: list[str] = []
    for chunk in chunks:
        lines = [line.strip() for line in chunk.splitlines() if line.strip()]
        if not lines:
            continue
        if all(line.startswith("- ") for line in lines):
            output.append("<ul>" + "".join(f"<li>{line[2:]}</li>" for line in lines) + "</ul>")
        elif all(re.match(r"^\d+\.\s", line) for line in lines):
            list_items = "".join(
                f"<li>{re.sub('^[0-9]+[.] *', '', line)}</li>" for line in lines
            )
            output.append(
                "<ol>" + list_items + "</ol>"
            )
        else:
            output.append(f"<p>{'<br>'.join(lines)}</p>")
    return "\n".join(output)


def clean_blocks(blocks: list[str]) -> str:
    cleaned: list[str] = []
    for block in blocks:
        block = paragraphize_pre(block)
        block = re.sub(r"<span[^>]*>", "", block)
        block = block.replace("</span>", "")
        block = re.sub(r"<p>\s*<br>\s*</p>", "", block)
        block = re.sub(r"\s+</", "</", block)
        block = re.sub(r"[ \t]+(?=\n|$)", "", block)
        if block.strip():
            cleaned.append(block.strip())
    return "\n".join(cleaned)


def parse_article(config: dict[str, str]) -> dict[str, str]:
    parser = LinkedInArticleParser()
    parser.feed(fetch(config["url"]).decode("utf-8"))
    schema = parser.schema
    author = schema.get("author") or {}
    if author.get("url", "").rstrip("/") != PROFILE_URL.rstrip("/"):
        raise RuntimeError(f"Unexpected LinkedIn author for {config['url']}")

    published = datetime.fromisoformat(schema["datePublished"])
    image = schema.get("image") or {}
    image_url = image.get("url") or parser.poster_url
    description = config.get("description") or schema.get("headline", "").strip()
    if len(description) > 220:
        description = description[:217].rsplit(" ", 1)[0] + "…"

    return {
        **config,
        "title": schema["name"].strip(),
        "description": description,
        "date_iso": published.date().isoformat(),
        "date_display": published.strftime("%B %-d, %Y"),
        "year": str(published.year),
        "body": clean_blocks(parser.blocks),
        "image_url": image_url or "",
    }


def save_cover(article: dict[str, str]) -> str:
    if not article["image_url"]:
        return ""
    data = fetch(article["image_url"])
    extension = ".png" if data.startswith(b"\x89PNG\r\n\x1a\n") else ".jpg"
    destination = ROOT / "assets" / "articles" / f"{article['slug']}{extension}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    for old_extension in (".jpg", ".png"):
        old_destination = destination.with_suffix(old_extension)
        if old_destination != destination and old_destination.exists():
            old_destination.unlink()
    destination.write_bytes(data)
    return f"/assets/articles/{destination.name}"


THEME_BUTTON = """
<button class="icon-button" type="button" data-theme-toggle aria-label="Use light theme">
  <span class="theme-icon theme-icon-sun" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="3.25"></circle><path d="M12 2.75v2M12 19.25v2M21.25 12h-2M4.75 12h-2M18.54 5.46l-1.41 1.41M6.87 17.13l-1.41 1.41M18.54 18.54l-1.41-1.41M6.87 6.87 5.46 5.46"></path></svg></span>
  <span class="theme-icon theme-icon-moon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20 15.1A8.4 8.4 0 0 1 8.9 4a8.4 8.4 0 1 0 11.1 11.1Z"></path></svg></span>
</button>
""".strip()


def header() -> str:
    return f"""
<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header" data-header>
  <a class="brand" href="/" aria-label="Chandan Venkatesh, home"><span class="brand-mark" aria-hidden="true">CV</span><span class="brand-text">Chandan Venkatesh</span></a>
  <nav class="desktop-nav" aria-label="Primary navigation"><a href="/#work">AI work</a><a href="/#impact">Retail depth</a><a href="/articles/" aria-current="page">Articles</a><a href="/#career">Career</a><a href="/#proof">Proof</a></nav>
  <div class="header-actions">{THEME_BUTTON}<a class="button button-small button-ghost header-resume" href="/assets/chandan-venkatesh-resume.pdf" target="_blank" rel="noreferrer">Résumé <span aria-hidden="true">↗</span></a><button class="menu-button" type="button" data-menu-toggle aria-expanded="false" aria-controls="mobile-menu"><span></span><span></span><span class="sr-only">Open navigation</span></button></div>
</header>
<nav class="mobile-menu" id="mobile-menu" data-mobile-menu aria-label="Mobile navigation" hidden><a href="/#work">AI work</a><a href="/#impact">Retail depth</a><a href="/articles/">Articles</a><a href="/#career">Career</a><a href="/#proof">Proof</a><a href="/assets/chandan-venkatesh-resume.pdf" target="_blank" rel="noreferrer">Open résumé</a></nav>
""".strip()


def footer() -> str:
    return """
<footer class="article-footer">
  <p>© <span data-year></span> Chandan Venkatesh</p>
  <div><a href="mailto:chandan07@gmail.com">Email</a><a href="https://github.com/chandanvenkatesh07" target="_blank" rel="noreferrer">GitHub</a><a href="https://www.linkedin.com/in/chandan-venkatesh-53884428/" target="_blank" rel="noreferrer">LinkedIn</a></div>
</footer>
""".strip()


def article_page(article: dict[str, str], all_articles: list[dict[str, str]]) -> str:
    canonical = f"https://chandanvenkatesh.com/articles/{article['slug']}/"
    image_meta = article["cover"] or "https://chandanvenkatesh.com/assets/chandan-venkatesh.jpg"
    image_absolute = f"https://chandanvenkatesh.com{image_meta}" if image_meta.startswith("/") else image_meta
    related = [item for item in all_articles if item["slug"] != article["slug"]][:3]
    related_markup = "".join(
        f'<a href="/articles/{item["slug"]}/"><span>{escape(item["topic"])}</span><strong>{escape(item["title"])}</strong><time datetime="{item["date_iso"]}">{escape(item["date_display"])}</time></a>'
        for item in related
    )
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article["title"],
        "description": article["description"],
        "datePublished": article["date_iso"],
        "dateModified": article["date_iso"],
        "mainEntityOfPage": canonical,
        "author": {"@type": "Person", "name": "Chandan Venkatesh", "url": "https://chandanvenkatesh.com/"},
        "publisher": {"@type": "Person", "name": "Chandan Venkatesh"},
        "image": image_absolute,
        "isBasedOn": article["url"],
    }
    cover = (
        f'<figure class="article-cover"><img src="{article["cover"]}" alt="" width="1280" height="720"></figure>'
        if article["cover"]
        else ""
    )
    return f"""<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{escape(article['description'], quote=True)}">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <meta property="og:type" content="article"><meta property="og:site_name" content="Chandan Venkatesh"><meta property="og:title" content="{escape(article['title'], quote=True)}"><meta property="og:description" content="{escape(article['description'], quote=True)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{image_absolute}">
  <meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{escape(article['title'], quote=True)}"><meta name="twitter:description" content="{escape(article['description'], quote=True)}"><meta name="twitter:image" content="{image_absolute}">
  <meta name="theme-color" content="#0a0d10">
  <title>{escape(article['title'])} — Chandan Venkatesh</title>
  <link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/article-styles.css">
  <script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
</head>
<body class="article-page">
  {header()}
  <main id="main">
    <article>
      <header class="article-hero"><a class="article-back" href="/articles/">← All writing</a><p class="section-kicker">{escape(article['topic'])}</p><h1>{escape(article['title'])}</h1><div class="article-byline"><span>Chandan Venkatesh</span><time datetime="{article['date_iso']}">{escape(article['date_display'])}</time></div></header>
      {cover}
      <div class="article-layout"><div class="article-body">{article['body']}<aside class="article-origin"><span>Originally published on LinkedIn</span><a href="{article['url']}" target="_blank" rel="noreferrer">Read the original and discussion ↗</a></aside></div><aside class="article-author"><img src="/assets/chandan-venkatesh.jpg" alt="Chandan Venkatesh" width="88" height="88"><strong>Chandan Venkatesh</strong><p>Enterprise AI and Commerce Architect. I build grounded AI systems across the retail lifecycle.</p><a href="/">About my work →</a></aside></div>
    </article>
    <section class="related-writing" aria-labelledby="related-title"><p class="section-kicker">Keep reading</p><h2 id="related-title">More field notes</h2><div>{related_markup}</div></section>
  </main>
  {footer()}
  <script src="/script.js"></script>
</body>
</html>
"""


def index_page(articles: list[dict[str, str]]) -> str:
    cards = "".join(
        f"""<a class="writing-card" href="/articles/{article['slug']}/">
  <div class="writing-card-meta"><span>{escape(article['topic'])}</span><time datetime="{article['date_iso']}">{escape(article['date_display'])}</time></div>
  <h2>{escape(article['title'])}</h2><p>{escape(article['description'])}</p><span class="writing-card-link">Read article →</span>
</a>"""
        for article in articles
    )
    return f"""<!doctype html>
<html lang="en" data-theme="dark">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="Articles by Chandan Venkatesh about enterprise AI, agent workflows, generative interfaces, retail systems, and AI-assisted engineering."><link rel="canonical" href="https://chandanvenkatesh.com/articles/"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><meta property="og:type" content="website"><meta property="og:site_name" content="Chandan Venkatesh"><meta property="og:title" content="Articles — Chandan Venkatesh"><meta property="og:description" content="Field notes on enterprise AI, retail systems, agent workflows, and AI-assisted engineering."><meta property="og:url" content="https://chandanvenkatesh.com/articles/"><meta property="og:image" content="https://chandanvenkatesh.com/assets/chandan-venkatesh.jpg"><meta name="twitter:card" content="summary"><meta name="theme-color" content="#0a0d10"><title>Articles — Chandan Venkatesh</title><link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/article-styles.css"></head>
<body class="writing-index">{header()}<main id="main"><header class="writing-hero"><p class="section-kicker">Articles</p><h1>Writing about AI in practice.</h1><p>Architecture notes, experiments, and operating lessons from building with AI—not commentary from the sidelines.</p></header><section class="writing-grid" aria-label="Articles">{cards}</section></main>{footer()}<script src="/script.js"></script></body></html>
"""


def sitemap(articles: list[dict[str, str]]) -> str:
    entries = [
        ("https://chandanvenkatesh.com/", "2026-11-10", "monthly", "1.0"),
        ("https://chandanvenkatesh.com/articles/", "2026-11-10", "monthly", "0.9"),
    ] + [
        (f"https://chandanvenkatesh.com/articles/{article['slug']}/", article["date_iso"], "yearly", "0.8")
        for article in articles
    ]
    urls = "".join(
        f"  <url>\n    <loc>{url}</loc>\n    <lastmod>{lastmod}</lastmod>\n    <changefreq>{frequency}</changefreq>\n    <priority>{priority}</priority>\n  </url>\n"
        for url, lastmod, frequency, priority in entries
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n'


def main() -> None:
    articles = [parse_article(config) for config in ARTICLES]
    for article in articles:
        article["cover"] = save_cover(article)
    for article in articles:
        destination = ROOT / "articles" / article["slug"] / "index.html"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(article_page(article, articles), encoding="utf-8")
    (ROOT / "articles" / "index.html").write_text(index_page(articles), encoding="utf-8")
    (ROOT / "sitemap.xml").write_text(sitemap(articles), encoding="utf-8")
    print(f"Imported {len(articles)} LinkedIn articles.")


if __name__ == "__main__":
    main()
