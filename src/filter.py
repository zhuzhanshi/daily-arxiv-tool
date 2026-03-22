"""论文筛选与评分 — 多维打分，分 A/B 两档。"""

import json
from pathlib import Path

from classify import classify_paper, get_domain_name, get_domain_emoji
from config import Config


def score_paper(paper: dict, domain: str, cfg: Config) -> float:
    """对论文打分 (0-100)。"""
    score = 0.0
    title = paper.get("title", "").lower()
    abstract = paper.get("abstract", "").lower()
    authors = [a.lower() for a in paper.get("authors", [])]
    text = f"{title} {abstract}"

    # 1. 领域权重 (0-15)
    domain_weights = {
        "multimodal_vlm": 15, "llm_reasoning": 15, "llm_agent": 14,
        "llm_efficiency": 13, "llm_alignment": 13, "llm_nlp": 12,
        "image_generation": 13, "video_understanding": 13, "3d_vision": 12,
        "model_compression": 11, "self_supervised": 11,
        "nlp_understanding": 11, "nlp_generation": 11,
        "robotics": 13, "ai_safety": 12,
    }
    score += domain_weights.get(domain, 10)

    # 2. 团队加分 (0-15)
    team_text = " ".join(authors)
    team_hits = sum(1 for t in cfg.filter.teams if t in team_text)
    score += min(team_hits * 5, 15)

    # 3. 高价值关键词 (0-30)
    kw_hits = sum(1 for kw in cfg.filter.high_value_keywords if kw in text)
    score += min(kw_hits * 3, 30)

    # 4. 有代码 (0-5)
    if "github.com" in text or "code available" in text or "open-source" in text:
        score += 5

    # 5. 摘要长度 (0-10)
    abstract_len = len(abstract.split())
    if abstract_len > 150:
        score += 5
    if abstract_len > 250:
        score += 5

    # 6. 低价值惩罚 (-10)
    if any(s in text for s in cfg.filter.low_value_signals):
        score -= 10

    return max(score, 0)


def filter_papers(papers: list[dict], cfg: Config) -> dict:
    """筛选论文，返回 A/B 两档。"""
    focus = set(cfg.filter.focus_domains) if cfg.filter.focus_domains else None

    scored = []
    for p in papers:
        domain = classify_paper(p["title"], p["abstract"], cfg)
        if focus and domain not in focus:
            continue
        s = score_paper(p, domain, cfg)
        scored.append({**p, "domain": domain, "score": s})

    scored.sort(key=lambda x: -x["score"])

    top_a = cfg.filter.top_a
    top_b = cfg.filter.top_b
    tier_a = scored[:top_a]
    tier_b = scored[top_a:top_a + top_b]

    return {
        "tier_a": tier_a,
        "tier_b": tier_b,
        "stats": {
            "total": len(papers),
            "in_focus": len(scored),
            "tier_a_count": len(tier_a),
            "tier_b_count": len(tier_b),
            "tier_a_min_score": tier_a[-1]["score"] if tier_a else 0,
            "tier_b_min_score": tier_b[-1]["score"] if tier_b else 0,
        },
    }


def filter_daily(cfg: Config, dates: list[str]) -> dict[str, dict]:
    """筛选指定日期的论文。"""
    logs_dir = cfg.logs_path
    results = {}

    for date in sorted(dates):
        json_path = logs_dir / f"daily_{date}.json"
        if not json_path.exists():
            print(f"⚠️  {json_path} 不存在，跳过 {date}")
            continue

        with open(json_path, "r", encoding="utf-8") as f:
            papers = json.load(f)

        result = filter_papers(papers, cfg)
        _print_summary(date, result, cfg)

        out_path = logs_dir / f"filtered_{date}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n  💾 保存到 {out_path}")

        results[date] = result

    return results


def _print_summary(date: str, result: dict, cfg: Config):
    """打印筛选结果摘要。"""
    stats = result["stats"]
    print(f"\n{'='*60}")
    print(f"📅 {date} 筛选结果")
    print(f"{'='*60}")
    print(f"  总论文: {stats['total']} | 关注领域: {stats['in_focus']} | "
          f"A档: {stats['tier_a_count']} | B档: {stats['tier_b_count']}")

    for tier_name, papers in [("🅰️  A档", result["tier_a"]),
                               ("🅱️  B档", result["tier_b"])]:
        if not papers:
            continue
        print(f"\n  {tier_name}:")
        by_domain: dict[str, list] = {}
        for p in papers:
            by_domain.setdefault(p["domain"], []).append(p)
        for domain in sorted(by_domain, key=lambda d: -len(by_domain[d])):
            emoji = get_domain_emoji(domain, cfg)
            name = get_domain_name(domain, cfg)
            domain_papers = by_domain[domain]
            print(f"    {emoji} {name} ({len(domain_papers)}篇)")
            for p in domain_papers[:3]:
                short = p["title"][:55] + ("..." if len(p["title"]) > 55 else "")
                print(f"      [{p['score']:.0f}] {short}")
            if len(domain_papers) > 3:
                print(f"      ... +{len(domain_papers)-3} 篇")
