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
    """生成某天的 daily page markdown。"""
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

    # 匹配已有笔记；如果没有笔记，也展示到 daily 页面里。
    display_papers = []
    for p in papers:
        arxiv_id = p["arxiv_id"]
        note_link = note_by_arxiv.get(arxiv_id)
        if not note_link:
            title_slug = _slugify(p["title"])
            for stem, fname in note_by_stem.items():
                if stem in title_slug or title_slug[:20] in stem:
                    note_link = fname
                    break
        display_papers.append((p, note_link))

    lines = []
    lines.append(f"# 📅 {date} 研究看板\n")
    lines.append(f"> A档候选 **{len(display_papers)}** 篇\n")
    lines.append("---\n")

    for p, note_link in display_papers:
        title = p["title"]
        domain = p["domain"]
        emoji = get_domain_emoji(domain, cfg)
        name = get_domain_name(domain, cfg)
        score = p.get("score")

        # 优先展示笔记中的中文总结，否则回退到摘要片段
        summary = note_summary.get(note_link, p.get("summary") or p.get("abstract", "")[:220])
        if len(summary) > 220:
            summary = summary[:217] + "..."

        if note_link:
            lines.append(f"### [{title}]({note_link})\n")
            lines.append(f"{emoji} {name} | 已有笔记")
        else:
            lines.append(f"### [{title}](https://arxiv.org/abs/{p['arxiv_id']})\n")
            lines.append(f"{emoji} {name} | 待精读")

        if score is not None:
            lines.append(f"| 分数 | {score:.0f} | arXiv | `{p['arxiv_id']}` |\n")

        lines.append(f"{summary}\n")
        lines.append("---\n")

    return "\n".join(lines)


def gen_main_index(cfg: Config) -> str:
    """生成首页。"""
    cats = " ".join(f"`{c}`" for c in cfg.categories)
    date_dirs = []
    if cfg.docs_path.exists():
        date_dirs = sorted(
            [p.name for p in cfg.docs_path.iterdir() if p.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}", p.name)],
            reverse=True,
        )

    lines = []
    lines.append(f"# {cfg.output.site_name}\n")
    lines.append("这里不是通用论文首页，而是我的研究看板。\n")
    if date_dirs:
        lines.append("## 最新更新\n")
        for date in date_dirs[:7]:
            lines.append(f"- [{date} 研究看板]({date}/index.md)\n")
    lines.append("## 当前关注\n")
    lines.append("- 医学影像\n- 眼科 AI\n- Agent 系统\n- 计算机视觉\n- 持续学习\n")
    lines.append("## 我希望每天回答的问题\n")
    lines.append("1. 今天出现了哪些和我研究主线直接相关的论文？\n")
    lines.append("2. 哪几篇值得进入精读，而不是只看摘要？\n")
    lines.append("3. 哪些方法、数据设定或实验结论值得纳入后续项目？\n")
    lines.append("4. 哪些工作只是在热点里重复堆料，应该快速跳过？\n")
    lines.append("## 当前追踪类别\n")
    lines.append(f"**追踪类别**: {cats}\n")
    lines.append("从左侧导航栏进入每日页面，先看 A 档候选，再决定哪些进入全文精读。\n")
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
