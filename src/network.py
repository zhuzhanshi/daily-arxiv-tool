"""网络工具 — 统一处理代理、SSL、速率限制。"""

import ssl
import threading
import time
from urllib.request import ProxyHandler, HTTPSHandler, build_opener, Request

from config import Config

_rate_lock = threading.Lock()
_last_request_time = 0.0


def make_opener(cfg: Config):
    """根据配置创建 urllib opener。"""
    handlers = []

    # 代理
    if cfg.network.proxy:
        handlers.append(ProxyHandler({
            "http": cfg.network.proxy,
            "https": cfg.network.proxy,
        }))

    # SSL
    ctx = ssl.create_default_context()
    if not cfg.network.ssl_verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    handlers.append(HTTPSHandler(context=ctx))

    return build_opener(*handlers)


def rate_limited_request(opener, url: str, interval: float, timeout: int = 30) -> bytes:
    """带全局速率限制的 HTTP 请求。"""
    global _last_request_time
    with _rate_lock:
        now = time.time()
        wait = interval - (now - _last_request_time)
        if wait > 0:
            time.sleep(wait)
        _last_request_time = time.time()

    req = Request(url, headers={"User-Agent": "DailyArxiv/1.0"})
    with opener.open(req, timeout=timeout) as resp:
        return resp.read()
