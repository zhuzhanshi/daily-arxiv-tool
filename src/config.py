"""配置加载器 — 从 config.yaml 读取用户配置，提供带默认值的 dataclass。"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class NetworkConfig:
    proxy: str = ""
    ssl_verify: bool = True
    request_interval: float = 3.5
    download_interval: float = 5.0
    download_workers: int = 3


@dataclass
class FilterConfig:
    focus_domains: list[str] = field(default_factory=list)
    domain_weights: dict[str, int] = field(default_factory=dict)
    top_a: int = 20
    top_b: int = 40
    teams: list[str] = field(default_factory=lambda: [
        "google", "deepmind", "openai", "meta", "fair",
        "microsoft", "nvidia", "apple", "anthropic",
        "tencent", "alibaba", "baidu", "bytedance",
        "tsinghua", "peking", "stanford", "mit",
        "berkeley", "cmu", "princeton", "harvard",
        "oxford", "cambridge", "eth zurich", "epfl",
        "kaist", "seoul national", "tokyo",
    ])
    high_value_keywords: list[str] = field(default_factory=lambda: [
        "state-of-the-art", "sota", "novel framework", "first to",
        "we propose", "we introduce", "new paradigm", "unified",
        "surpass", "outperform",
        "scaling law", "emergent", "chain-of-thought", "in-context",
        "instruction tuning", "rlhf", "direct preference",
        "world model", "test-time", "inference-time",
        "long context", "mixture of expert", "moe",
        "multimodal", "vision-language", "video generation",
        "diffusion", "flow matching", "autoregressive",
        "benchmark", "evaluation",
        "open-source", "code available", "publicly available",
    ])
    low_value_signals: list[str] = field(default_factory=lambda: [
        "survey of", "review of", "a survey",
        "position paper", "workshop",
        "dataset only", "annotation tool",
    ])


@dataclass
class OutputConfig:
    docs_dir: str = "notes"
    logs_dir: str = "logs"
    cache_dir: str = "paper_cache"
    site_name: str = "Daily arXiv"
    site_url: str = ""
    repo_url: str = ""


@dataclass
class DomainDef:
    name: str
    emoji: str
    keywords: list[str]
    priority: int = 50


@dataclass
class Config:
    categories: list[str] = field(default_factory=lambda: [
        "cs.CV", "cs.CL", "cs.AI", "cs.LG", "cs.MM", "cs.IR", "cs.RO",
    ])
    domains: dict[str, DomainDef] = field(default_factory=dict)
    filter: FilterConfig = field(default_factory=FilterConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    # 运行时设置（不来自 YAML）
    project_root: Path = field(default_factory=lambda: Path.cwd())

    @property
    def docs_path(self) -> Path:
        return self.project_root / self.output.docs_dir

    @property
    def logs_path(self) -> Path:
        return self.project_root / self.output.logs_dir

    @property
    def cache_path(self) -> Path:
        return self.project_root / self.output.cache_dir


def load_config(config_path: Optional[str] = None, project_root: Optional[Path] = None) -> Config:
    """加载配置文件。优先级: 参数指定 > 环境变量 > 当前目录 config.yaml > 默认值。"""
    if project_root is None:
        # src/ 下运行时，自动回退到项目根目录
        project_root = Path(__file__).resolve().parent.parent

    if config_path is None:
        config_path = os.environ.get("DARXIV_CONFIG")

    if config_path is None:
        default = project_root / "config.yaml"
        if default.exists():
            config_path = str(default)

    cfg = Config(project_root=project_root)

    if config_path is None:
        return cfg

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    # categories
    if "categories" in raw:
        cfg.categories = raw["categories"]

    # domains (用户自定义覆盖)
    if "domains" in raw:
        for domain_id, d in raw["domains"].items():
            cfg.domains[domain_id] = DomainDef(
                name=d.get("name", domain_id),
                emoji=d.get("emoji", "📄"),
                keywords=d.get("keywords", []),
                priority=d.get("priority", 50),
            )

    # filter
    if "filter" in raw:
        flt = raw["filter"]
        if "focus_domains" in flt:
            cfg.filter.focus_domains = flt["focus_domains"]
        if "domain_weights" in flt:
            cfg.filter.domain_weights = flt["domain_weights"]
        if "top_a" in flt:
            cfg.filter.top_a = flt["top_a"]
        if "top_b" in flt:
            cfg.filter.top_b = flt["top_b"]
        if "teams" in flt:
            cfg.filter.teams = flt["teams"]
        if "high_value_keywords" in flt:
            cfg.filter.high_value_keywords = flt["high_value_keywords"]
        if "low_value_signals" in flt:
            cfg.filter.low_value_signals = flt["low_value_signals"]

    # network
    if "network" in raw:
        net = raw["network"]
        if "proxy" in net:
            cfg.network.proxy = net["proxy"] or ""
        if "ssl_verify" in net:
            cfg.network.ssl_verify = net["ssl_verify"]
        if "request_interval" in net:
            cfg.network.request_interval = net["request_interval"]
        if "download_interval" in net:
            cfg.network.download_interval = net["download_interval"]
        if "download_workers" in net:
            cfg.network.download_workers = net["download_workers"]

    # output
    if "output" in raw:
        out = raw["output"]
        for key in ("docs_dir", "logs_dir", "cache_dir", "site_name", "site_url", "repo_url"):
            if key in out:
                setattr(cfg.output, key, out[key])

    return cfg
