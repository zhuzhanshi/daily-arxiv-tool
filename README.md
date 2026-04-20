# Zhanshi Research Board

这是我个人的论文研究看板，不是通用 arXiv 模板站。

这个仓库每天做三件事：

1. 从 arXiv 里筛出和我当前研究真正相关的论文
2. 用统一标准判断哪些值得进入精读列表
3. 把精读结果沉淀成中文笔记、研究判断和后续 idea

在线入口：
[https://zhuzhanshi.github.io/daily-arxiv-tool/](https://zhuzhanshi.github.io/daily-arxiv-tool/)

## 当前研究主线

当前默认配置围绕这些方向组织：

- 医学影像
- 眼科 AI 任务
- Agent 系统
- 计算机视觉
- 持续学习

这意味着这个项目的目标不是“尽量覆盖所有热点”，而是稳定追踪和我研究计划最相关的论文流。

## 工作方式

工作日 18:00，系统会进入一轮 daily 更新。默认流程是：

1. 抓取当天论文
2. 根据自定义领域和关键词打分
3. 生成 A / B 两档候选
4. 对 A 档做后续精读、笔记和 idea 延展

这套节奏偏研究生产，不偏资讯浏览。

## 默认筛选逻辑

当前评分策略重点偏向以下信号：

- 医学影像与临床场景
- 眼科相关任务，例如 fundus、OCT、glaucoma、DR
- 持续学习与 catastrophic forgetting
- Agent、tool use、planning
- CV 核心任务，例如 segmentation、detection、representation
- 多中心验证、外部验证、泛化与鲁棒性

相应地，纯 survey、纯 leaderboard、纯数据集整理类工作会被压低。

## 使用方式

常用操作：

```bash
cd src && python cli.py run
cd src && python cli.py download --filtered
cd src && python cli.py serve
```

在聊天里也可以直接说：

- `刷今天的 daily arxiv`
- `把今天最值得读的几篇展开`
- `帮我读这篇论文`
- `这篇论文能延伸什么 idea`
- `发布 daily`

## 关键文件

- `config.yaml`
  研究方向、评分规则、代理配置
- `notes/`
  每日看板和论文笔记
- `logs/`
  原始抓取结果和筛选结果
- `paper_cache/`
  全文缓存
- `.github/workflows/`
  自动更新与站点部署

## 站点定位

站点首页不是展示“系统功能”，而是展示当天研究判断的入口。

我希望它回答的是：

- 今天最该看的论文是什么
- 哪些方向在升温
- 哪些论文值得进入精读
- 哪些结果和我的研究主线直接相关

## 部署

仓库通过 GitHub Actions 和 GitHub Pages 在线发布，站点地址固定为：

[https://zhuzhanshi.github.io/daily-arxiv-tool/](https://zhuzhanshi.github.io/daily-arxiv-tool/)
