"""生成 mkdocs 页面 — 每日速览 + 首页索引。"""

import json
import re
from pathlib import Path

from classify import (
    classify_paper, get_domain_name, get_domain_emoji, domain_sort_key,
)
from config import Config


def _slugify(title: str) -> str:
    """从论文标题生成 slug（用于匹配已有笔记文件）。"""
    s = title.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s-]+", "-", s).strip("-")
    return s[:60]


def gen_daily_page(date: str, papers: list[dict], cfg: Config) -> str:
    """生成某天的 daily page markdown（卡片式，匹配笔记链接）。"""
    for p in papers:
        if "domain" not in p:
            p["domain"] = classify_paper(p["title"], p["abstract"], cfg)

    total = len(papers)

    # 扫描已有笔记文件，提取 arXiv ID + 中文摘要
    notes_dir = cfg.docs_path / date
    note_by_arxiv: dict[str, str] = {}   # arxiv_id -> filename
    note_by_stem: dict[str, str] = {}    # stem -> filename
    note_summary: dict[str, str] = {}    # filename -> 中文一句话总结
    if notes_dir.exists():
        for md in notes_dir.glob("*.md"):
            if md.name == "index.md":
                continue
            note_by_stem[md.stem.lower()] = md.name
            try:
                content = md.read_text(encoding="utf-8")
                # 提取 arXiv ID
                m = re.search(r"(\d{4}\.\d{4,5})", content[:500])
                if m:
                    note_by_arxiv[m.group(1)] = md.name
                # 提取"一句话总结"章节内容
                m2 = re.search(r"## 一句话总结\s*\n+(.+?)(?:\n\n|\n##)", content)
                if m2:
                    note_summary[md.name] = m2.group(1).strip()
            except Exception:
                pass

    # 只展示有笔记的论文
    noted_papers = []
    for p in papers:
        arxiv_id = p["arxiv_id"]
        note_link = note_by_arxiv.get(arxiv_id)
        if not note_link:
            title_slug = _slugify(p["title"])
            for stem, fname in note_by_stem.items():
                if stem in title_slug or title_slug[:20] in stem:
                    note_link = fname
                    break
        if note_link:
            noted_papers.append((p, note_link))

    lines = []
    lines.append(f"# 📅 {date} 精选笔记\n")
    lines.append(f"> 共 **{len(noted_papers)}** 篇\n")
    lines.append("---\n")

    for p, note_link in noted_papers:
        title = p["title"]
        domain = p["domain"]
        emoji = get_domain_emoji(domain, cfg)
        name = get_domain_name(domain, cfg)

        # 摘要：从笔记中提取中文一句话总结
        summary = note_summary.get(note_link, p.get("abstract", "")[:200])

        lines.append(f"### [{title}]({note_link})\n")
        lines.append(f"{emoji} {name}\n")
        lines.append(f"{summary}\n")
        lines.append("---\n")

    return "\n".join(lines)


def gen_main_index(cfg: Config) -> str:
    """生成首页。"""
    site_name = cfg.output.site_name
    cats = " ".join(f"`{c}`" for c in cfg.categories)

    lines = []
    lines.append(f"# 📰 {site_name}\n")
    lines.append("每日精选 arXiv 上 AI / LLM / NLP / CV 领域最值得关注的论文，附深度阅读笔记。\n")
    lines.append(f"**追踪类别**: {cats}\n")
    lines.append("从左侧导航栏选择日期，查看当天的论文笔记。\n")
    lines.append("---\n")

    return "\n".join(lines)


def generate_pages(cfg: Config, specific_date: str | None = None):
    """生成 daily 页面和首页。"""
    logs_dir = cfg.logs_path
    docs_dir = cfg.docs_path
    docs_dir.mkdir(parents=True, exist_ok=True)

    if specific_date:
        json_files = [logs_dir / f"daily_{specific_date}.json"]
    else:
        json_files = sorted(logs_dir.glob("daily_*.json"))

    for jf in json_files:
        if not jf.exists():
            print(f"⚠️  {jf} 不存在，跳过")
            continue

        m = re.search(r"daily_(\d{4}-\d{2}-\d{2})\.json", jf.name)
        if not m:
            continue
        date = m.group(1)

        # 优先使用 filtered (A档)
        filtered_path = logs_dir / f"filtered_{date}.json"
        if filtered_path.exists():
            with open(filtered_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            papers = data.get("tier_a", [])
            print(f"  📄 {date}: filtered A档 {len(papers)} 篇")
        else:
            with open(jf, "r", encoding="utf-8") as f:
                papers = json.load(f)
            print(f"  📄 {date}: 全量 {len(papers)} 篇")

        out_dir = docs_dir / date
        out_dir.mkdir(parents=True, exist_ok=True)
        page = gen_daily_page(date, papers, cfg)
        (out_dir / "index.md").write_text(page, encoding="utf-8")

    # 首页
    index = gen_main_index(cfg)
    (docs_dir / "index.md").write_text(index, encoding="utf-8")
    print(f"  🏠 首页已更新")
