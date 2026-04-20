"""CLI 入口 — daily-arxiv 命令行工具。"""

import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

import click

from config import load_config


def _resolve_dates(date: str | None, days: int | None) -> list[str]:
    """解析日期参数。"""
    if days:
        return [(datetime.now() - timedelta(days=i + 1)).strftime("%Y-%m-%d")
                for i in range(days)]
    if date:
        return [date]
    return [(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")]


@click.group()
@click.option("--config", "config_path", default=None, help="配置文件路径 (默认: ./config.yaml)")
@click.pass_context
def cli(ctx, config_path):
    """Daily arXiv — 自动追踪 arXiv 每日新论文 🚀"""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path


def _get_cfg(ctx):
    return load_config(ctx.obj.get("config_path"))


@cli.command()
def init():
    """初始化项目 — 生成 config.yaml 配置模板。"""
    dest = Path.cwd() / "config.yaml"
    if dest.exists():
        click.echo("⚠️  config.yaml 已存在，跳过")
        return

    # 从包内复制模板
    src = Path(__file__).parent.parent / "config.example.yaml"
    if src.exists():
        shutil.copy2(src, dest)
    else:
        # fallback: 生成最小配置
        dest.write_text(
            "# Daily arXiv 配置\n"
            "# 完整配置参考: https://github.com/zhuzhanshi/daily-arxiv-tool\n\n"
            "categories:\n"
            "  - cs.CV   # Computer Vision\n"
            "  - cs.CL   # NLP/LLM\n"
            "  - cs.AI   # AI\n"
            "  - cs.LG   # Machine Learning\n",
            encoding="utf-8",
        )
    click.echo(f"✅ 已生成 {dest}")
    click.echo("  编辑 config.yaml 定制你的追踪领域和筛选规则")


@cli.command()
@click.argument("date", required=False)
@click.option("--days", type=int, help="获取过去 N 天")
@click.pass_context
def fetch(ctx, date, days):
    """获取 arXiv 论文。"""
    cfg = _get_cfg(ctx)
    dates = _resolve_dates(date, days)
    from fetch import fetch_daily
    fetch_daily(cfg, dates)


@cli.command("filter")
@click.argument("date", required=False)
@click.option("--days", type=int, help="筛选过去 N 天")
@click.option("--top-a", type=int, help="A档数量")
@click.option("--top-b", type=int, help="B档数量")
@click.pass_context
def filter_cmd(ctx, date, days, top_a, top_b):
    """筛选评分论文。"""
    cfg = _get_cfg(ctx)
    if top_a is not None:
        cfg.filter.top_a = top_a
    if top_b is not None:
        cfg.filter.top_b = top_b
    dates = _resolve_dates(date, days)
    from filter import filter_daily
    filter_daily(cfg, dates)


@cli.command()
@click.argument("date", required=False)
@click.pass_context
def page(ctx, date):
    """生成 mkdocs 页面。"""
    cfg = _get_cfg(ctx)
    from page import generate_pages
    generate_pages(cfg, date)


@cli.command()
@click.argument("date", required=False)
@click.option("--days", type=int, help="下载过去 N 天")
@click.option("--max", "max_per_day", type=int, help="每天最多下载数")
@click.option("--filtered", is_flag=True, help="只下载 A 档论文（从 filtered JSON 读取）")
@click.pass_context
def download(ctx, date, days, max_per_day, filtered):
    """下载论文全文到缓存。"""
    cfg = _get_cfg(ctx)
    dates = _resolve_dates(date, days)
    from download import download_daily
    download_daily(cfg, dates, max_per_day, filtered=filtered)


@cli.command()
@click.argument("date", required=False)
@click.option("--days", type=int, help="处理过去 N 天")
@click.pass_context
def run(ctx, date, days):
    """一键运行: fetch → filter → page。"""
    cfg = _get_cfg(ctx)
    dates = _resolve_dates(date, days)

    click.echo("=" * 60)
    click.echo("Step 1/3: 获取论文")
    click.echo("=" * 60)
    from fetch import fetch_daily
    fetch_daily(cfg, dates)

    click.echo("\n" + "=" * 60)
    click.echo("Step 2/3: 筛选评分")
    click.echo("=" * 60)
    from filter import filter_daily
    filter_daily(cfg, dates)

    click.echo("\n" + "=" * 60)
    click.echo("Step 3/3: 生成页面")
    click.echo("=" * 60)
    from page import generate_pages
    for d in dates:
        generate_pages(cfg, d)

    click.echo("\n🎉 完成！运行 `daily-arxiv serve` 预览站点")


@cli.command()
@click.option("--port", type=int, default=8200, help="端口号")
@click.pass_context
def serve(ctx, port):
    """本地预览 mkdocs 站点。"""
    import subprocess
    cfg = _get_cfg(ctx)
    click.echo(f"🌐 启动预览服务器 http://127.0.0.1:{port}")
    subprocess.run(
        ["mkdocs", "serve", "-a", f"127.0.0.1:{port}"],
        cwd=str(cfg.project_root),
    )


@cli.command()
@click.argument("date", required=False)
@click.pass_context
def stats(ctx, date):
    """查看统计信息。"""
    cfg = _get_cfg(ctx)
    logs_dir = cfg.logs_path

    if date:
        dates = [date]
    else:
        dates = sorted(
            f.stem.replace("daily_", "")
            for f in logs_dir.glob("daily_*.json")
        )

    if not dates:
        click.echo("❌ 没有找到数据，先运行 `daily-arxiv fetch`")
        return

    import json
    from classify import classify_paper, get_domain_emoji, get_domain_name

    for d in dates[-7:]:  # 最近 7 天
        daily_path = logs_dir / f"daily_{d}.json"
        filtered_path = logs_dir / f"filtered_{d}.json"

        if not daily_path.exists():
            continue

        with open(daily_path, "r", encoding="utf-8") as f:
            papers = json.load(f)

        filtered = ""
        if filtered_path.exists():
            with open(filtered_path, "r", encoding="utf-8") as f:
                fdata = json.load(f)
            a_count = fdata.get("stats", {}).get("tier_a_count", 0)
            filtered = f" | A档 {a_count} 篇"

        click.echo(f"  📅 {d}: {len(papers)} 篇{filtered}")


def main():
    cli()


if __name__ == "__main__":
    main()
