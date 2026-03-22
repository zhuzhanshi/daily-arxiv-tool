---
name: daily-arxiv-publish
description: '发布 daily-arxiv 笔记到 GitHub Pages 站点。USE FOR: 发布daily笔记、更新daily站点、同步daily到GitHub、推送daily笔记、刷新daily导航。DO NOT USE FOR: 抓取论文(用daily-arxiv)、写论文笔记(用write-note)、下载论文(用daily-arxiv download)。'
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
- 笔记已写好在 `docs/YYYY-MM-DD/` 目录下
- Python 环境已激活

## 流程

### Step 1: 扁平化 notes/ 子目录

检查每个日期目录下是否有 `notes/` 子目录，如有则将笔记移到日期目录下：

```bash
# 找出所有 notes/ 中的文件
find docs -path '*/notes/*.md' | sort

# 对每个文件：移动到日期目录
# 如果日期目录已有同名文件，比较后保留更长的版本
# 示例：
# mv docs/2026-03-20/notes/paper.md docs/2026-03-20/paper.md
```

**注意**：如果日期目录已有同名文件，用 `diff` 比较，保留内容更完整的版本。

### Step 2: 拆分合集文件

检查是否有 `remaining-*.md` 之类的多论文合集文件：

```bash
find docs -name "remaining-*.md" | sort
```

如果有，按 `# ` 标题拆分为独立文件，拆分后删除原合集文件。

### Step 3: 重建每日一览页

为每个日期目录生成 `index.md`，卡片式展示所有笔记：

```bash
daily-arxiv page
```

或针对某天：

```bash
daily-arxiv page 2026-03-20
```

效果：每篇笔记显示标题、领域 emoji、一句话总结。

### Step 4: 重建 mkdocs.yml 导航

手动更新 `mkdocs.yml` 的 `nav` 部分，确保所有日期目录和笔记都被列出：

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

可以用 Python 脚本自动扫描生成：

```python
import os, re, glob, yaml

docs_dir = "docs"
nav = [{"Home": "index.md"}]

for date_dir in sorted(glob.glob(f"{docs_dir}/20*-*-*"), reverse=True):
    date = os.path.basename(date_dir)
    items = [f"{date}/index.md"]
    for md in sorted(glob.glob(f"{date_dir}/*.md")):
        fname = os.path.basename(md)
        if fname == "index.md":
            continue
        # 提取 H1 标题
        with open(md) as f:
            for line in f:
                if line.startswith("# "):
                    title = line[2:].strip()[:45]
                    break
            else:
                title = fname.replace(".md", "")
        items.append({title: f"{date}/{fname}"})
    if items:
        nav.append({date: items})

with open("mkdocs.yml") as f:
    config = yaml.safe_load(f)
config["nav"] = nav
with open("mkdocs.yml", "w") as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
```

### Step 5: 构建验证

```bash
mkdocs build 2>&1
```

检查：
- 无 `WARNING` 或 `ERROR`
- 无 orphan 页面警告
- 如有问题，回到前面步骤处理

### Step 6: 报告结果

不执行 git 操作。告诉用户：
- 本次变更的文件数和内容
- 建议的 commit message，例如：`daily: publish 2026-03-20 notes (15 papers)`
- 提示用户检查后手动执行：

```bash
git add -A
git commit -m "daily: publish 2026-03-20"
git push
```

## 自动化替代

如果启用了 GitHub Actions（`.github/workflows/deploy.yml`），push 到 main 分支后会自动部署到 GitHub Pages，无需额外操作。
