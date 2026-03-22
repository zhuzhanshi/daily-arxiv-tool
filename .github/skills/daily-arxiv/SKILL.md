---
name: daily-arxiv
description: '获取每日 arXiv 论文并生成速览页面。USE FOR: 抓取每天arXiv新论文、生成daily页面。DO NOT USE FOR: 写深度笔记(用write-note)、下载论文缓存(用daily-arxiv download)。'
argument-hint: '可选：指定日期(2026-03-20)、天数(--days 3)、默认获取昨天'
---

# 获取每日 arXiv 论文并生成速览页面

## 触发条件
- 用户要求"抓今天/昨天的 arXiv"、"刷 daily"、"更新每日论文"
- 用户要求"看看今天有什么新论文"

## 核心原则
- **只关注 A 档** — 筛选后只展示精选论文
- **自动分类** — 28 个领域自动归类，按领域分组展示
- **可定制** — 所有参数通过 config.yaml 配置

## 流程

### Step 1: 获取论文

```bash
daily-arxiv fetch 2026-03-20
daily-arxiv fetch --days 3
```

### Step 2: 筛选论文

```bash
daily-arxiv filter 2026-03-20
daily-arxiv filter --days 3 --top-a 15
```

### Step 3: 生成速览页面

```bash
daily-arxiv page 2026-03-20
daily-arxiv page   # 重建所有页面
```

### 一键完成

```bash
daily-arxiv run              # fetch + filter + page 昨天
daily-arxiv run 2026-03-20   # 指定日期
daily-arxiv run --days 3     # 过去 3 天
```

### 本地预览

```bash
daily-arxiv serve
```

## 配置

编辑 `config.yaml` 定制:
- **categories**: 追踪的 arXiv 类别
- **filter.focus_domains**: 关注的研究领域
- **filter.top_a/top_b**: A/B 档数量
- **filter.teams**: 加分团队
- **filter.high_value_keywords**: 高价值关键词
- **network.proxy**: 代理设置

## 输出

```
logs/daily_YYYY-MM-DD.json       # 原始数据
logs/filtered_YYYY-MM-DD.json    # 筛选结果
docs/YYYY-MM-DD/index.md         # 每日速览页面
docs/index.md                    # 首页索引
```
