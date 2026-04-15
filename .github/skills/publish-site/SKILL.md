---
name: publish-site
description: '发布 daily-arxiv 笔记到 GitHub Pages 站点。USE FOR: 发布daily笔记、更新daily站点、同步daily到GitHub、推送daily笔记、刷新daily导航。DO NOT USE FOR: 抓取论文(用fetch-papers)、写论文笔记(用write-note/write-note-batch)、下载论文(用fetch-papers download)。'
argument-hint: '无参数，自动处理所有待发布的笔记'
---

# 发布 daily-arxiv 笔记到 GitHub Pages 站点

## 触发条件
- 用户要求"发布 daily"、"推送 daily 笔记"、"更新 daily 站点"
- 用户要求"同步到 GitHub"、"刷新导航"
- 写完一批 daily 笔记后需要上线

## 核心原则
- **不做 git push** — 只准备文件，让用户检查后手动提交
- **幂等** — 多次运行不会破坏内容

## 前置条件
- 笔记已写好在 `notes/YYYY-MM-DD/` 目录下
- Python 环境已激活

## 流程

### Step 1: 扁平化 notes/ 子目录

检查每个日期目录下是否有 `notes/` 子目录，如有则将笔记移到日期目录下：

```powershell
# Windows 下查找所有 notes/ 中的文件
Get-ChildItem -Path notes -Recurse -Filter "*.md" | Where-Object { $_.DirectoryName -match '\\notes\\' }
```

**注意事项**：
- 如果日期目录已有同名文件，比较内容，保留更完整的版本
- 移动后确认 `notes/` 子目录为空

### Step 2: 拆分合集文件

检查是否有 `remaining-*.md` 之类的多论文合集文件：

```powershell
Get-ChildItem -Path notes -Recurse -Filter "remaining-*.md"
```

如果有，按 `# ` 标题拆分为独立文件，拆分后删除原合集文件。

### Step 3: 重建每日一览页

为每个日期目录生成 `index.md`，卡片式展示所有笔记：

```bash
cd src && python cli.py page
```

或针对某天：

```bash
cd src && python cli.py page 2026-03-20
```

效果：每篇笔记显示标题、领域 emoji、一句话总结。

### Step 4: 重建 mkdocs.yml 导航

更新 `mkdocs.yml` 的 `nav` 部分，确保所有日期目录和笔记都被列出：

```yaml
nav:
- Home: index.md
- '2026-03-20':
  - 2026-03-20/index.md
  - Paper Title 1: 2026-03-20/paper1.md
  - Paper Title 2: 2026-03-20/paper2.md
- '2026-03-19':
  - 2026-03-19/index.md
  - ...
```

用 Python 脚本自动扫描生成（按日期倒序，最新在前）：

```python
import os, glob, yaml

docs_dir = "notes"
nav = [{"Home": "index.md"}]

for date_dir in sorted(glob.glob(f"{docs_dir}/20*-*-*"), reverse=True):
    date = os.path.basename(date_dir)
    items = [f"{date}/index.md"]
    for md in sorted(glob.glob(f"{date_dir}/*.md")):
        fname = os.path.basename(md)
        if fname == "index.md":
            continue
        # 提取 H1 标题
        with open(md, encoding="utf-8") as f:
            for line in f:
                if line.startswith("# "):
                    title = line[2:].strip()[:45]
                    break
            else:
                title = fname.replace(".md", "")
        items.append({title: f"{date}/{fname}"})
    if items:
        nav.append({date: items})

with open("mkdocs.yml", encoding="utf-8") as f:
    config = yaml.safe_load(f)
config["nav"] = nav
with open("mkdocs.yml", "w", encoding="utf-8") as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
```

### Step 5: 构建验证

```bash
mkdocs build 2>&1
```

检查：
- 无 `WARNING` 或 `ERROR`
- 无 `pages exist in the docs directory, but are not included in the "nav"`（orphan 页面）
- 如有 orphan，回到 Step 1 处理

### Step 6: 报告结果

不执行 git 操作。告诉用户：
- 本次变更的文件数和内容摘要
- 建议的 commit message，例如：`daily: publish 2026-03-20 notes (15 papers)`
- 提示用户检查后手动执行：

```bash
git add -A
git commit -m "daily: publish 2026-03-20"
git push
```

## 与其他 skill 的关系

| skill | 关系 |
|-------|------|
| **daily-arxiv** | 上游：抓论文 + 筛选 |
| **write-note / write-note-batch** | 上游：写笔记 |
| **gen-idea** | 平行：写笔记时捕捉的 idea |

## 文件结构

```
daily-arxiv-tool/
├── notes/                    # mkdocs 文档目录（output.docs_dir）
│   ├── index.md              # 首页
│   └── YYYY-MM-DD/
│       ├── index.md          # 卡片式一览（自动生成）
│       └── paper-slug.md     # 论文笔记
├── mkdocs.yml                # nav 自动重建
├── src/
│   ├── cli.py                # CLI 入口（page 命令生成一览页）
│   └── page.py               # 页面生成逻辑
└── .github/workflows/
    └── daily.yml             # GitHub Actions 工作流
```

## 自动化替代

如果启用了 GitHub Actions（`.github/workflows/daily.yml`），push 到 main 分支后会自动部署到 GitHub Pages，无需额外操作。
