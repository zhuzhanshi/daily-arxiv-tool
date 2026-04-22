"""生成 mkdocs 页面 — 每日速览 + 首页索引。"""

import json
import re
from pathlib import Path

from classify import (
    classify_paper, get_domain_name, get_domain_emoji, domain_sort_key,
)
from config import Config

SOURCE_LABELS = {
    "arxiv": "arXiv",
    "media": "MedIA",
    "tmi": "TMI",
}


def _slugify(title: str) -> str:
    """从论文标题生成 slug（用于匹配已有笔记文件）。"""
    s = title.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s-]+", "-", s).strip("-")
    return s[:60]


def gen_daily_page(
    date: str,
    tier_a: list[dict],
    cfg: Config,
    tier_b: list[dict] | None = None,
    source_label: str = "arXiv",
) -> str:
    """生成某天的 daily page markdown。"""
    tier_b = tier_b or []
    all_papers = tier_a + tier_b

    for p in all_papers:
        if "domain" not in p:
            p["domain"] = classify_paper(p["title"], p["abstract"], cfg)

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

    def _attach_note_link(papers: list[dict]) -> list[tuple[dict, str | None]]:
        """匹配已有笔记；如果没有笔记，也展示到 daily 页面里。"""
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
        return display_papers

    def _render_paper(p: dict, note_link: str | None, default_status: str) -> list[str]:
        title = p["title"]
        domain = p["domain"]
        emoji = get_domain_emoji(domain, cfg)
        name = get_domain_name(domain, cfg)
        score = p.get("score")

        # 优先展示笔记中的中文总结，否则回退到摘要片段
        summary = note_summary.get(note_link, p.get("summary") or p.get("abstract", "")[:220])
        if len(summary) > 220:
            summary = summary[:217] + "..."

        rendered = []
        if note_link:
            rendered.append(f"### [{title}]({note_link})\n")
            rendered.append(f"{emoji} {name} | 已有笔记")
        else:
            link = p.get("url") or f"https://arxiv.org/abs/{p['arxiv_id']}"
            rendered.append(f"### [{title}]({link})\n")
            rendered.append(f"{emoji} {name} | {default_status}")

        if score is not None:
            identifier = p.get("doi") or p.get("arxiv_id", "")
            rendered.append(f"| 分数 | {score:.0f} | 来源 | {source_label} | ID | `{identifier}` |\n")

        rendered.append(f"{summary}\n")
        rendered.append("---\n")
        return rendered

    display_a = _attach_note_link(tier_a)
    display_b = _attach_note_link(tier_b)

    lines = []
    lines.append(f"# 📅 {date} {source_label} 研究看板\n")
    lines.append(f"> A档精读 **{len(display_a)}** 篇 | B档浏览 **{len(display_b)}** 篇\n")
    lines.append("---\n")

    lines.append("## A档：建议精读\n")
    if display_a:
        for p, note_link in display_a:
            lines.extend(_render_paper(p, note_link, "待精读"))
    else:
        lines.append("今天没有 A 档候选。\n")

    lines.append("## B档：快速浏览 / 备选\n")
    if display_b:
        for p, note_link in display_b:
            lines.extend(_render_paper(p, note_link, "待浏览"))
    else:
        lines.append("今天没有 B 档候选。\n")

    return "\n".join(lines)


def gen_main_index(cfg: Config) -> str:
    """生成首页。"""
    cats = " ".join(f"`{c}`" for c in cfg.categories)

    lines = []
    lines.append(f"# {cfg.output.site_name}\n")
    lines.append("这里不是通用论文首页，而是我的研究看板。\n")
    lines.append("## 来源入口\n")
    lines.append("- [arXiv](arxiv/index.md)：每日预印本候选\n")
    lines.append("- [MedIA](media/index.md)：Medical Image Analysis articles in press\n")
    lines.append("- [TMI](tmi/index.md)：IEEE Transactions on Medical Imaging 目录更新\n")
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


def gen_source_index(cfg: Config, source: str) -> str:
    label = SOURCE_LABELS[source]
    source_dir = cfg.docs_path / source
    date_dirs = []
    if source_dir.exists():
        date_dirs = sorted(
            [p.name for p in source_dir.iterdir() if p.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}", p.name)],
            reverse=True,
        )

    lines = [f"# {label}\n"]
    if not date_dirs:
        lines.append("暂无更新。\n")
        return "\n".join(lines)
    lines.append("## 每日更新\n")
    for date in date_dirs[:30]:
        lines.append(f"- [{date} 研究看板]({date}/index.md)\n")
    return "\n".join(lines)


def _write_source_page(cfg: Config, source: str, date: str, tier_a: list[dict], tier_b: list[dict]):
    out_dir = cfg.docs_path / source / date
    out_dir.mkdir(parents=True, exist_ok=True)
    page = gen_daily_page(date, tier_a, cfg, tier_b, SOURCE_LABELS[source])
    (out_dir / "index.md").write_text(page, encoding="utf-8")
    (cfg.docs_path / source).mkdir(parents=True, exist_ok=True)
    (cfg.docs_path / source / "index.md").write_text(gen_source_index(cfg, source), encoding="utf-8")


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

        # 优先使用 filtered (A/B档)
        filtered_path = logs_dir / f"filtered_{date}.json"
        if filtered_path.exists():
            with open(filtered_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            tier_a = data.get("tier_a", [])
            tier_b = data.get("tier_b", [])
            print(f"  📄 {date}: filtered A档 {len(tier_a)} 篇, B档 {len(tier_b)} 篇")
        else:
            with open(jf, "r", encoding="utf-8") as f:
                tier_a = json.load(f)
            tier_b = []
            print(f"  📄 {date}: 全量 {len(tier_a)} 篇")

        out_dir = docs_dir / date
        out_dir.mkdir(parents=True, exist_ok=True)
        page = gen_daily_page(date, tier_a, cfg, tier_b)
        (out_dir / "index.md").write_text(page, encoding="utf-8")
        _write_source_page(cfg, "arxiv", date, tier_a, tier_b)

    # 首页
    index = gen_main_index(cfg)
    (docs_dir / "index.md").write_text(index, encoding="utf-8")
    for source in SOURCE_LABELS:
        source_dir = docs_dir / source
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "index.md").write_text(gen_source_index(cfg, source), encoding="utf-8")
    print(f"  🏠 首页已更新")


def generate_journal_pages(cfg: Config, source: str, specific_date: str | None = None):
    logs_dir = cfg.logs_path
    if specific_date:
        json_files = [logs_dir / f"{source}_filtered_{specific_date}.json"]
    else:
        json_files = sorted(logs_dir.glob(f"{source}_filtered_*.json"))

    for jf in json_files:
        if not jf.exists():
            print(f"⚠️  {jf} 不存在，跳过")
            continue
        m = re.search(rf"{source}_filtered_(\d{{4}}-\d{{2}}-\d{{2}})\.json", jf.name)
        if not m:
            continue
        date = m.group(1)
        data = json.loads(jf.read_text(encoding="utf-8"))
        tier_a = data.get("tier_a", [])
        tier_b = data.get("tier_b", [])
        print(f"  📄 {SOURCE_LABELS[source]} {date}: A档 {len(tier_a)} 篇, B档 {len(tier_b)} 篇")
        _write_source_page(cfg, source, date, tier_a, tier_b)

    index = gen_main_index(cfg)
    (cfg.docs_path / "index.md").write_text(index, encoding="utf-8")
