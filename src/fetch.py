"""从 arXiv API 获取每日新发布的论文。"""

import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

from config import Config
from network import make_opener

NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def _parse_entry(entry, categories: list[str]) -> dict | None:
    """解析 arXiv API 返回的单条 entry。"""
    id_elem = entry.find("atom:id", NS)
    if id_elem is None:
        return None
    id_text = id_elem.text.strip()
    if "api/errors" in id_text:
        return None

    title = entry.find("atom:title", NS).text.strip().replace("\n", " ")
    title = re.sub(r"\s+", " ", title)

    arxiv_id = id_text.split("/")[-1]
    arxiv_id = re.sub(r"v\d+$", "", arxiv_id)

    summary = entry.find("atom:summary", NS).text.strip().replace("\n", " ")
    summary = re.sub(r"\s+", " ", summary)

    cats = [c.get("term") for c in entry.findall("atom:category", NS)]
    primary_cat = cats[0] if cats else ""

    authors = [a.find("atom:name", NS).text for a in entry.findall("atom:author", NS)]

    published = entry.find("atom:published", NS).text.strip()[:10]

    comment_elem = entry.find("arxiv:comment", NS)
    comment = comment_elem.text.strip() if comment_elem is not None and comment_elem.text else ""

    # 只保留主类别在目标列表中的论文
    if not any(c in categories for c in cats[:3]):
        return None

    return {
        "title": title,
        "arxiv_id": arxiv_id,
        "abstract": summary,
        "authors": authors[:5],
        "primary_category": primary_cat,
        "categories": cats[:5],
        "published": published,
        "comment": comment,
    }


def _extract_summary(abstract: str) -> str:
    """从摘要中提取第一句话。"""
    match = re.match(r"^(.+?\.)\s", abstract)
    if match:
        sent = match.group(1)
        return sent[:197] + "..." if len(sent) > 200 else sent
    return abstract[:197] + "..." if len(abstract) > 200 else abstract


def _deduplicate(papers: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for p in papers:
        if p["arxiv_id"] not in seen:
            seen.add(p["arxiv_id"])
            unique.append(p)
    return unique


def _resolve_target_date(
    target_date: str,
    available_dates: list[str],
    max_lookback_days: int = 4,
) -> str | None:
    """将本地目标日期映射到最近一个非空的 arXiv 发布日。

    arXiv 的发布时间与本地“今天/昨天”并不总是一一对应，周末尤其容易出现空日。
    这里优先取 <= target_date 的最近非空 published 日期，并限制最多回看若干天。
    """
    if not available_dates:
        return None

    target_dt = datetime.strptime(target_date, "%Y-%m-%d")
    candidates = []
    for d in available_dates:
        published_dt = datetime.strptime(d, "%Y-%m-%d")
        if published_dt <= target_dt:
            delta_days = (target_dt - published_dt).days
            if delta_days <= max_lookback_days:
                candidates.append((published_dt, d))

    if not candidates:
        return None

    candidates.sort()
    return candidates[-1][1]


def fetch_by_date_range(cfg: Config, from_date: str, to_date: str) -> list[dict]:
    """用 submittedDate 范围查询获取论文。"""
    opener = make_opener(cfg)
    cat_query = "+OR+".join(f"cat:{c}" for c in cfg.categories)
    fd = from_date.replace("-", "")
    td = to_date.replace("-", "")
    base_query = f"({cat_query})+AND+submittedDate:[{fd}0000+TO+{td}2359]"

    all_papers = []
    batch_size = 200
    interval = cfg.network.request_interval

    for start in range(0, 5000, batch_size):
        url = (
            f"http://export.arxiv.org/api/query?"
            f"search_query={base_query}"
            f"&start={start}&max_results={batch_size}"
            f"&sortBy=submittedDate&sortOrder=descending"
        )
        try:
            from network import rate_limited_request
            data = rate_limited_request(opener, url, interval).decode("utf-8")
            root = ET.fromstring(data)
            entries = root.findall("atom:entry", NS)

            if not entries:
                break

            count = 0
            for entry in entries:
                paper = _parse_entry(entry, cfg.categories)
                if paper:
                    all_papers.append(paper)
                    count += 1

            print(f"  Batch start={start}: {len(entries)} entries, {count} kept (total: {len(all_papers)})")

            if len(entries) < batch_size:
                break

        except Exception as e:
            print(f"  ❌ Batch start={start} error: {e}")
            time.sleep(5)

    return all_papers


def fetch_daily(cfg: Config, dates: list[str]) -> dict[str, list[dict]]:
    """获取指定日期的论文，返回 {date: [papers]}。

    Args:
        cfg: 配置
        dates: 日期列表 ["2026-03-20", "2026-03-21"]

    Returns:
        按日期分组的论文字典
    """
    dates = sorted(dates)
    from_date = dates[0]
    to_date = dates[-1]

    print(f"📅 获取 {from_date} ~ {to_date} 的 arXiv 论文")
    print(f"📂 类别: {', '.join(cfg.categories)}")

    # 日期范围扩展。向前多看几天，避免周末或发布时间偏移导致目标日期为空。
    from_dt = datetime.strptime(from_date, "%Y-%m-%d") - timedelta(days=4)
    to_dt = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)

    papers = fetch_by_date_range(cfg, from_dt.strftime("%Y-%m-%d"), to_dt.strftime("%Y-%m-%d"))
    papers = _deduplicate(papers)
    print(f"\n✅ 总计获取 {len(papers)} 篇去重论文")

    # 按 published 日期分组
    by_date: dict[str, list[dict]] = {}
    for p in papers:
        by_date.setdefault(p["published"], []).append(p)

    available_dates = sorted(by_date.keys())

    # 保存目标日期
    logs_dir = cfg.logs_path
    logs_dir.mkdir(parents=True, exist_ok=True)

    result = {}
    for d in dates:
        mapped_date = _resolve_target_date(d, available_dates)
        if mapped_date and mapped_date != d:
            print(f"  ↪ {d} 无新发布，回退到最近非空发布日期 {mapped_date}")

        date_papers = by_date.get(mapped_date or d, [])
        normalized_papers = []
        for p in date_papers:
            p = {**p}
            p["summary"] = _extract_summary(p["abstract"])
            p["target_date"] = d
            p["source_published_date"] = mapped_date or d
            normalized_papers.append(p)
        out_path = logs_dir / f"daily_{d}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(normalized_papers, f, indent=2, ensure_ascii=False)
        print(f"  💾 {d}: {len(normalized_papers)} 篇 → {out_path}")
        result[d] = normalized_papers

    return result
