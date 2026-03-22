---
name: batch-write-notes
description: '批量写 daily arXiv 论文笔记。USE FOR: 批量写笔记、一口气写完当天论文、刷一天笔记。DO NOT USE FOR: 单篇论文笔记(用write-note)、生成idea(用generate-idea)、获取论文(用daily-arxiv)。'
argument-hint: '指定日期(2026-03-19)或"今天"/"昨天"'
---

# 批量写 Daily arXiv 论文笔记

## 触发条件
- 用户要求"批量写笔记"、"把今天的笔记都写了"、"刷笔记"
- 用户要求"写 3 月 19 号的 A 档笔记"

## 核心原则
- **每篇读全文** — 从 paper_cache 读缓存，不是只看摘要
- **100+ 行** — 深度笔记，不是水笔记
- **断点续传** — 通过检查已有笔记文件跳过已完成的

## 前置条件
- 已运行过 `daily-arxiv fetch` 和 `daily-arxiv filter`（有 filtered JSON）
- 论文缓存**不要求提前全部下载** — 流水线模式会边下边写

## 流程（流水线模式 — 边下载边写笔记）

### Step 1: 加载 A 档论文列表

读取 `logs/filtered_YYYY-MM-DD.json`，提取 `tier_a` 中所有论文。

### Step 2: 检查已完成笔记

扫描 `notes/YYYY-MM-DD/*.md`，跳过已有笔记的论文，得到待写列表。

### Step 3: 后台启动下载 + 立即开始写笔记

**关键：不要等下载全部完成再写笔记。**

1. 在后台终端启动下载（`isBackground=true`），**用 `--filtered` 只下载 A 档 20 篇**：
   ```bash
   cd <project_root> && python src/cli.py download --filtered <date>
   ```
2. 立即开始遍历待写列表，对每篇论文：
   a. 检查缓存 `paper_cache/arxiv/YYYY-MM-DD/<arxiv_id>.txt` 是否存在且 >10KB
   b. **已缓存** → 直接读取全文，写笔记
   c. **未缓存** → 跳过，放入 `pending` 队列，继续下一篇
3. 第一轮结束后，对 `pending` 队列做第二轮：
   a. 再次检查缓存（后台下载可能已完成）
   b. 仍未缓存的，用 `fetch_webpage` 单独获取 `https://arxiv.org/html/<arxiv_id>` 全文
   c. 写笔记
4. 每 5 篇报告一次进度

### Step 4: 更新速览页

所有笔记写完后，重新生成当天的 `notes/YYYY-MM-DD/index.md`，
从速览表格更新为带笔记链接的卡片列表。

## 笔记模板

每篇笔记 100+ 行，中文，结构：

```markdown
# [论文标题]

**arXiv**: [ID](https://arxiv.org/abs/ID)
**代码**: 有/无
**领域**: xxx
**关键词**: [3-5个]

## 一句话总结

## 动机与背景

## 方法

## 实验

## 亮点与局限

## 启发与关联
```

## 质量原则
- **必须读论文全文** — 不是只看摘要复述
- **用自己的话写** — 禁止直接复制粘贴
- **方法部分最详细** — 占全文 30-40%
