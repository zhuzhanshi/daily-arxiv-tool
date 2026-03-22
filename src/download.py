"""下载 arXiv 论文全文到本地缓存。"""

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request

from config import Config
from network import make_opener

_rate_lock = threading.Lock()
_last_dl_time = 0.0

MAX_RETRIES = 3
RETRY_DELAYS = [10, 30, 60]


class _TextExtractor(HTMLParser):
    """从 HTML 中提取可读文本。"""
    SKIP_TAGS = {"script", "style", "nav", "header", "footer", "noscript",
                 "svg", "button", "select", "textarea"}
    VOID_ELEMENTS = {"area", "base", "br", "col", "embed", "hr", "img",
                     "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS and tag not in self.VOID_ELEMENTS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)


def _html_to_text(html: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(html)
    raw = extractor.get_text()
    lines = []
    for line in raw.split("\n"):
        stripped = line.strip()
        if stripped:
            lines.append(stripped)
        elif lines and lines[-1] != "":
            lines.append("")
    return "\n".join(lines)


def _dl_rate_limit(interval: float):
    global _last_dl_time
    with _rate_lock:
        now = time.time()
        wait = interval - (now - _last_dl_time)
        if wait > 0:
            time.sleep(wait)
        _last_dl_time = time.time()


def _fetch_one(arxiv_id: str, cache_dir: Path, opener, interval: float) -> tuple[str, str, str]:
    """下载并清洗一篇论文。返回 (arxiv_id, status, message)。"""
    out_path = cache_dir / f"{arxiv_id}.txt"

    if out_path.exists() and out_path.stat().st_size > 100:
        return arxiv_id, "cached", "已缓存"

    html_url = f"https://arxiv.org/html/{arxiv_id}"
    text = ""
    need_fallback = False

    for attempt in range(MAX_RETRIES + 1):
        if attempt > 0:
            time.sleep(RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)])

        need_fallback = False
        _dl_rate_limit(interval)
        try:
            req = Request(html_url, headers={"User-Agent": "DailyArxiv/1.0 (paper cache)"})
            with opener.open(req, timeout=30) as resp:
                raw_html = resp.read().decode("utf-8", errors="replace")
            text = _html_to_text(raw_html)
            if len(text) < 500:
                need_fallback = True
            else:
                break
        except HTTPError as e:
            if e.code in (404, 403):
                need_fallback = True
                break
            need_fallback = True
            continue
        except (URLError, TimeoutError, OSError):
            need_fallback = True
            continue

        if not need_fallback:
            break

    status = "ok"
    if need_fallback:
        abs_url = f"https://arxiv.org/abs/{arxiv_id}"
        for attempt in range(MAX_RETRIES + 1):
            if attempt > 0:
                time.sleep(RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)])
            _dl_rate_limit(interval)
            try:
                req = Request(abs_url, headers={"User-Agent": "DailyArxiv/1.0 (paper cache)"})
                with opener.open(req, timeout=30) as resp:
                    raw_html = resp.read().decode("utf-8", errors="replace")
                text = _html_to_text(raw_html)
                if len(text) >= 200:
                    status = "fallback"
                    break
            except Exception:
                continue
        else:
            if len(text) < 200:
                return arxiv_id, "skip", "重试后仍失败"

    if len(text) < 200:
        return arxiv_id, "skip", f"内容太短 ({len(text)} 字符)"

    out_path.write_text(text, encoding="utf-8")
    return arxiv_id, status, f"{len(text)} 字符"


def download_daily(cfg: Config, dates: list[str], max_per_day: int | None = None,
                   filtered: bool = False):
    """下载指定日期的论文全文到缓存。

    Args:
        filtered: 若为 True，只下载 A 档论文（从 filtered_YYYY-MM-DD.json 读取）。
    """
    logs_dir = cfg.logs_path
    opener = make_opener(cfg)
    interval = cfg.network.download_interval
    workers = cfg.network.download_workers

    for date in sorted(dates):
        if filtered:
            json_path = logs_dir / f"filtered_{date}.json"
            if not json_path.exists():
                print(f"⚠️  {json_path} 不存在，跳过 {date}")
                continue
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            papers = data.get("tier_a", [])
        else:
            json_path = logs_dir / f"daily_{date}.json"
            if not json_path.exists():
                print(f"⚠️  {json_path} 不存在，跳过 {date}")
                continue
            with open(json_path, "r", encoding="utf-8") as f:
                papers = json.load(f)

        ids = [p["arxiv_id"] for p in papers if p.get("arxiv_id")]
        if max_per_day:
            ids = ids[:max_per_day]

        if not ids:
            print(f"⚠️  {date}: 没有论文可下载")
            continue

        cache_dir = cfg.cache_path / "arxiv" / date
        cache_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n📥 {date}: 下载 {len(ids)} 篇到 {cache_dir}/")

        ok = cached = fallback = skip = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_fetch_one, aid, cache_dir, opener, interval): aid
                for aid in ids
            }
            for future in as_completed(futures):
                aid, status, msg = future.result()
                if status == "ok":
                    ok += 1
                elif status == "cached":
                    cached += 1
                elif status == "fallback":
                    fallback += 1
                else:
                    skip += 1
                    print(f"    ⚠️  {aid}: {msg}")

        print(f"  ✅ {date}: 新下载 {ok}, 已缓存 {cached}, fallback {fallback}, 跳过 {skip}")

    print("\n✅ 下载完成")
