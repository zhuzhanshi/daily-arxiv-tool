"""Fetch journal article lists for MedIA and TMI."""

import json
import re
from datetime import datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlencode, urljoin
from urllib.request import Request

from classify import classify_paper
from config import Config
from filter import score_paper
from network import make_opener

MEDIA_URL = "https://www.sciencedirect.com/journal/medical-image-analysis/articles-in-press"
TMI_URL = "https://ieeexplore.ieee.org/xpl/tocresult.jsp?isnumber=4359023"
CROSSREF_ISSN = {
    "media": "1361-8415",
    "tmi": "0278-0062",
}

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_media_articles(html: str) -> list[dict]:
    """Parse ScienceDirect Articles in Press HTML."""
    articles = []
    pattern = re.compile(
        r"https://doi\.org/(?P<doi>10\.1016/j\.media\.\d+\.\d+).*?"
        r"###\s*\[[^\]]+\]\((?P<href>[^)]+)\)|"
        r"https://doi\.org/(?P<doi2>10\.1016/j\.media\.\d+\.\d+).*?"
        r"###\s*(?P<title2>.+?)\n",
        re.S,
    )

    # More robust line-oriented parser for the text-like HTML returned by ScienceDirect.
    lines = html.splitlines()
    pending_doi = ""
    for idx, line in enumerate(lines):
        doi_match = re.search(r"https://doi\.org/(10\.1016/j\.media\.\d+\.\d+)", line)
        if doi_match:
            pending_doi = doi_match.group(1)
            continue

        title_match = re.search(r"###\s*(?:\[[^\]]+\]\((?P<link>[^)]+)\)|(?P<title>.+))", line)
        if not title_match:
            continue

        title = _clean_html(title_match.group("title") or "")
        link = title_match.group("link") or ""
        if not title and link:
            # Markdown-like links in fetched output include the title before link in the same line less often.
            title = _clean_html(re.sub(r"###\s*", "", line))
            title = re.sub(r"\s*\(https?://.+\)$", "", title).strip("[] ")

        if not title:
            continue

        authors = ""
        available = ""
        for follow in lines[idx + 1: idx + 6]:
            if "Available online" in follow:
                available = _clean_html(follow)
                break
            if follow.strip() and not follow.strip().startswith(("http", "Research article", "Article preview")):
                authors = _clean_html(follow)

        articles.append({
            "title": title,
            "abstract": "",
            "summary": available or "Medical Image Analysis article in press.",
            "authors": [a.strip() for a in authors.split(",") if a.strip()][:5],
            "journal": "Medical Image Analysis",
            "source": "media",
            "url": urljoin("https://www.sciencedirect.com", link) if link else f"https://doi.org/{pending_doi}",
            "doi": pending_doi,
            "published": _parse_available_date(available),
        })
        pending_doi = ""

    return _dedupe_by_key(articles, "doi")


def _extract_tmi_articles(html: str) -> list[dict]:
    """Best-effort parser for IEEE TOC pages."""
    articles = []
    for match in re.finditer(
        r'<a[^>]+href="(?P<href>/document/\d+[^"]*)"[^>]*>(?P<title>.*?)</a>',
        html,
        re.I | re.S,
    ):
        title = _clean_html(match.group("title"))
        if not title or len(title) < 12:
            continue
        articles.append({
            "title": title,
            "abstract": "",
            "summary": "IEEE Transactions on Medical Imaging article.",
            "authors": [],
            "journal": "IEEE Transactions on Medical Imaging",
            "source": "tmi",
            "url": urljoin("https://ieeexplore.ieee.org", match.group("href")),
            "doi": "",
            "published": datetime.now().strftime("%Y-%m-%d"),
        })

    # Some IEEE pages embed titles in JSON blobs.
    if not articles:
        for title in re.findall(r'"articleTitle"\s*:\s*"([^"]+)"', html):
            clean = _clean_html(title)
            if clean:
                articles.append({
                    "title": clean,
                    "abstract": "",
                    "summary": "IEEE Transactions on Medical Imaging article.",
                    "authors": [],
                    "journal": "IEEE Transactions on Medical Imaging",
                    "source": "tmi",
                    "url": TMI_URL,
                    "doi": "",
                    "published": datetime.now().strftime("%Y-%m-%d"),
                })

    return _dedupe_by_key(articles, "title")


def _fetch_crossref_articles(cfg: Config, source: str, limit: int = 50) -> list[dict]:
    """Fetch recent journal articles from Crossref as a stable fallback."""
    issn = CROSSREF_ISSN[source]
    query = urlencode({
        "filter": "type:journal-article",
        "sort": "published",
        "order": "desc",
        "rows": str(limit),
    })
    url = f"https://api.crossref.org/journals/{issn}/works?{query}"
    data = json.loads(_request_html(cfg, url))
    articles = []

    journal = "Medical Image Analysis" if source == "media" else "IEEE Transactions on Medical Imaging"
    for item in data.get("message", {}).get("items", []):
        title = " ".join(item.get("title") or []).strip()
        if not title:
            continue
        authors = []
        for author in item.get("author", [])[:5]:
            name = " ".join(part for part in [author.get("given", ""), author.get("family", "")] if part)
            if name:
                authors.append(name)
        published = _crossref_date(item)
        doi = item.get("DOI", "")
        articles.append({
            "title": title,
            "abstract": _clean_html(item.get("abstract", "")),
            "summary": f"{journal} recent article.",
            "authors": authors,
            "journal": journal,
            "source": source,
            "url": item.get("URL") or (f"https://doi.org/{doi}" if doi else ""),
            "doi": doi,
            "published": published,
        })

    return _dedupe_by_key(articles, "doi")


def _crossref_date(item: dict) -> str:
    parts = (
        item.get("published-online", {}).get("date-parts")
        or item.get("published-print", {}).get("date-parts")
        or item.get("published", {}).get("date-parts")
        or []
    )
    if not parts:
        return datetime.now().strftime("%Y-%m-%d")
    raw = parts[0]
    year = raw[0]
    month = raw[1] if len(raw) > 1 else 1
    day = raw[2] if len(raw) > 2 else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def _parse_available_date(text: str) -> str:
    match = re.search(r"Available online ([0-9]{1,2} [A-Za-z]+ [0-9]{4})", text or "")
    if not match:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        return datetime.strptime(match.group(1), "%d %B %Y").strftime("%Y-%m-%d")
    except ValueError:
        return datetime.now().strftime("%Y-%m-%d")


def _dedupe_by_key(items: list[dict], key: str) -> list[dict]:
    seen = set()
    out = []
    for item in items:
        value = item.get(key) or item.get("title")
        if value in seen:
            continue
        seen.add(value)
        out.append(item)
    return out


def _request_html(cfg: Config, url: str) -> str:
    opener = make_opener(cfg)
    req = Request(url, headers=BROWSER_HEADERS)
    with opener.open(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "ignore")


def _score_journal_articles(articles: list[dict], cfg: Config) -> dict:
    scored = []
    for article in articles:
        domain = classify_paper(article["title"], article.get("abstract", ""), cfg)
        if domain == "others":
            domain = "medical_imaging"
        paper = {
            **article,
            "arxiv_id": article.get("doi") or article["title"][:40],
            "domain": domain,
        }
        scored.append({**paper, "score": score_paper(paper, domain, cfg)})

    scored.sort(key=lambda x: -x["score"])
    top_a = cfg.filter.top_a
    top_b = cfg.filter.top_b
    tier_a = scored[:top_a]
    tier_b = scored[top_a:top_a + top_b]
    return {
        "tier_a": tier_a,
        "tier_b": tier_b,
        "stats": {
            "total": len(articles),
            "in_focus": len(scored),
            "tier_a_count": len(tier_a),
            "tier_b_count": len(tier_b),
            "tier_a_min_score": tier_a[-1]["score"] if tier_a else 0,
            "tier_b_min_score": tier_b[-1]["score"] if tier_b else 0,
        },
    }


def fetch_journal_daily(cfg: Config, source: str, date: str) -> dict:
    if source == "media":
        url = MEDIA_URL
        parser = _extract_media_articles
    elif source == "tmi":
        url = TMI_URL
        parser = _extract_tmi_articles
    else:
        raise ValueError(f"Unknown journal source: {source}")

    try:
        html = _request_html(cfg, url)
        articles = parser(html)
    except Exception as exc:
        print(f"  ⚠️  {source} page fetch failed, using Crossref fallback: {exc}")
        articles = []

    if not articles:
        articles = _fetch_crossref_articles(cfg, source)

    logs_dir = cfg.logs_path
    logs_dir.mkdir(parents=True, exist_ok=True)

    raw_path = logs_dir / f"{source}_daily_{date}.json"
    filtered_path = logs_dir / f"{source}_filtered_{date}.json"
    raw_path.write_text(json.dumps(articles, indent=2, ensure_ascii=False), encoding="utf-8")

    filtered = _score_journal_articles(articles, cfg)
    filtered_path.write_text(json.dumps(filtered, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  📰 {source}: {len(articles)} articles -> {raw_path}")
    print(f"  🧭 {source}: A {len(filtered['tier_a'])}, B {len(filtered['tier_b'])} -> {filtered_path}")
    return filtered
