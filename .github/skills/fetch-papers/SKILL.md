---
name: fetch-papers
description: '获取每日 arXiv 论文并生成速览页面。USE FOR: 抓取每天arXiv新论文、生成daily页面、更新daily站点、刷daily。DO NOT USE FOR: 写深度论文笔记(用write-note/write-note-batch)、下载论文缓存(用fetch-papers download)。'
argument-hint: '可选：指定日期(2026-03-20)、天数(--days 3)、默认获取昨天'
---

# 获取每日 arXiv 论文并生成速览页面

## 触发条件
- 用户要求"抓今天/昨天的 arXiv"、"刷 daily"、"更新每日论文"
- 用户要求"生成 daily 页面"、"看看今天有什么新论文"

## 核心原则
- **只关注 A 档** — 筛选后只展示 20 篇精选论文，不展示全部 400+ 篇
- **自动分类** — 28 个领域自动归类，按领域分组展示
- **幂等** — 重复运行同一天不会出错（覆盖更新）
- **可定制** — 所有参数通过 config.yaml 配置

## 追踪类别
`cs.CV` `cs.CL` `cs.AI` `cs.LG` `cs.MM` `cs.IR` `cs.RO`

## 输出

```
logs/daily_YYYY-MM-DD.json       # 原始数据 (全部论文)
logs/filtered_YYYY-MM-DD.json    # 筛选结果 (A档+B档)
notes/YYYY-MM-DD/index.md        # 每日速览页面
```

## 流程

### Step 1: 获取论文

```bash
cd src && python cli.py fetch 2026-03-20
cd src && python cli.py fetch --days 3
```

### Step 2: 筛选论文 (A/B 两档)

```bash
# 筛选指定日期，默认 A档20篇 + B档40篇
cd src && python cli.py filter 2026-03-20

# 自定义数量
cd src && python cli.py filter 2026-03-20 --top-a 15 --top-b 30

# 批量筛选
cd src && python cli.py filter --days 3
```

筛选规则：
- 只保留关注领域（VLM、LLM推理、Agent、图像生成、3D视觉等 15 个领域）
- 按领域权重 + 团队知名度 + 高价值关键词 + 代码可用性综合打分
- **A 档 (深度笔记)**: 得分最高的 20 篇，读全文写 100+ 行笔记
- **B 档 (轻量笔记)**: 接下来的 40 篇，只用 abstract 写 50 行方法概要

### Step 3: 生成速览页面（A 档 only）

```bash
# 生成指定日期的速览页面（自动使用 filtered JSON，只展示 A 档）
cd src && python cli.py page 2026-03-20

# 重建所有日期页面
cd src && python cli.py page
```

⚠️ 必须先运行 Step 2 筛选，否则 fallback 到全量论文。

### 一键完成

```bash
cd src && python cli.py run              # fetch + filter + page 昨天
cd src && python cli.py run 2026-03-20   # 指定日期
cd src && python cli.py run --days 3     # 过去 3 天
```

### 本地预览

```bash
cd src && python cli.py serve
```

## 配置

编辑 `config.yaml` 定制:
- **categories**: 追踪的 arXiv 类别
- **filter.focus_domains**: 关注的研究领域
- **filter.top_a/top_b**: A/B 档数量
- **filter.teams**: 加分团队
- **filter.high_value_keywords**: 高价值关键词
- **network.proxy**: 代理设置

## 后续操作

获取速览后，写 A 档笔记：

1. **下载 A 档论文缓存**：
   ```bash
   cd src && python cli.py download --filtered 2026-03-20
   # 缓存保存到 paper_cache/arxiv/YYYY-MM-DD/
   ```

2. **写 A 档深度笔记**（用 write-note skill，读全文，每篇 100+ 行）
   - 笔记文件放在 `notes/YYYY-MM-DD/<slug>.md`

3. **笔记写完后更新 index**：
   ```bash
   cd src && python cli.py page 2026-03-20
   ```

## 与其他 skill 的关系

| skill | 关系 |
|-------|------|
| **write-note / write-note-batch** | 下游：对 A 档论文写深度笔记 |
| **publish-site** | 下游：发布笔记到 GitHub Pages |
| **gen-idea** | 下游：从论文生成研究 idea |

## 文件结构

```
daily-arxiv-tool/
├── src/
│   ├── cli.py           # CLI 入口
│   ├── fetch.py         # 获取每日论文
│   ├── filter.py        # 筛选 A/B 两档
│   ├── classify.py      # 论文领域分类规则
│   ├── page.py          # 生成速览页面
│   ├── download.py      # 下载论文全文缓存
│   ├── config.py        # 配置加载
│   └── network.py       # 网络请求（代理支持）
├── notes/               # mkdocs 文档目录
│   ├── index.md         # 首页
│   └── YYYY-MM-DD/
│       ├── index.md     # 每日速览页面
│       └── <paper>.md   # 论文笔记
├── logs/                # 原始 JSON 数据
│   ├── daily_*.json     # 全量论文（~400篇/天）
│   └── filtered_*.json  # 筛选后（A档20+B档40）
├── paper_cache/         # 论文全文缓存
├── config.yaml          # 配置文件
└── mkdocs.yml           # MkDocs 配置
```
