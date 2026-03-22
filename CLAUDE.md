# Daily arXiv Tool

自动追踪 arXiv 每日新论文的 Skills 驱动工具。

## Skills

本项目通过 `.github/skills/` 下的 Skill 文件驱动工作流。遇到以下请求时，先读取对应 SKILL.md 获取完整指令：

| 用户请求 | 读取 Skill |
|----------|-----------|
| "刷 daily"、"抓论文"、"获取 arXiv" | `.github/skills/daily-arxiv/SKILL.md` |
| "读论文"、"写笔记"、"解读论文" | `.github/skills/write-note/SKILL.md` |
| "批量写笔记"、"把笔记都写了" | `.github/skills/batch-write-notes/SKILL.md` |
| "想 idea"、"brainstorm" | `.github/skills/generate-idea/SKILL.md` |
| "发布"、"更新站点"、"推送笔记" | `.github/skills/daily-arxiv-publish/SKILL.md` |

## 项目结构

- `config.yaml` — 用户配置（arXiv 类别、关注领域、评分规则、网络代理）
- `src/` — Python 脚本（fetch / classify / filter / page / download）
- `notes/` — 生成的论文笔记（mkdocs 页面）
- `logs/` — JSON 原始数据
- `paper_cache/` — 论文全文缓存
- `src/` — Python 脚本（fetch / classify / filter / page / download），可直接 `cd src && python cli.py run [DATE]`

## 规则

- 论文笔记必须读全文后用中文写，100+ 行，禁止只看摘要复述
- 所有网络请求走 `config.yaml` 中的 `network.proxy` 配置
- arXiv API 请求间隔 ≥ 3.5 秒，下载间隔 ≥ 5 秒
