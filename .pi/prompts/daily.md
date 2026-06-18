---
description: 创建 Hacker News 日报
argument-hint: "[YYYY-MM-DD]"
---

请你作为一名资深编辑，创建一份关于 Hacker News 的日报。日报仍以 Hacker News 为唯一来源，但应面向好奇的广义读者，而不是只面向技术从业者。

这是 Pi agent 的工作流。Pi 没有内置 Claude Code 的 `Task` 子代理，所以请按下面阶段顺序亲自完成全部工作，不要尝试调用 Claude Code 子代理或 `.claude/agents/*`。

## 时间

优先使用命令参数中的目标日期：`$1`。

如果没有提供目标日期，使用下面命令获取“今天”并命名为 `$target_date`：

```bash
date +%Y-%m-%d
```

再将 `$target_date` 拆分为：

- `$year`：`YYYY`
- `$month`：`MM`
- `$draft_dir`：`drafts/$target_date`
- `$draft_yaml`：`drafts/$target_date/drafts.yaml`
- `$daily_file`：`daily/$year/$month/$target_date.md`

## 进度管理（产物即状态）

每个阶段开始前，检查当前目标日期对应的产物是否存在来判断恢复点：

| 阶段 | 完成标志 | 恢复动作 |
| --- | --- | --- |
| Phase 1 | `$draft_dir/` 目录存在且包含至少一个 `.md` 文件 | 跳过 Phase 1，进入 Phase 2 |
| Phase 2 | `$draft_yaml` 文件存在 | 跳过 Phase 1-2，进入 Phase 3 |
| Phase 3 | `$daily_file` 文件存在 | 跳过 Phase 1-3，进入 Phase 4 |

## Phase 1：收集内容

如果 Phase 1 尚未完成，执行：

```bash
python -m hn_daily --date $target_date --limit 20 --output $draft_dir
```

仅当命令执行成功，且 `$draft_dir` 下至少生成一个 `.md` 草稿文件时，Phase 1 才算完成。

这 20 篇 story 是候选池，不是最终成稿数量。

## Phase 2：翻译整理信息

只处理 `$draft_dir` 下的 `.md` 草稿文件，忽略其他日期目录和已有的 `drafts.yaml`。

请筛选、翻译并生成结构化 YAML。根据内容质量、信息完整度和主题分布决定最终入选故事数量。不要为了凑数保留弱稿，也不要设置固定篇数上限。最终结果应兼顾主题分布，不要只保留纯技术话题。

对每一份草稿，读取并整理为以下字段：

```yaml
title: "原文标题"
url: "https://example.com/article"
points: 123
topic: technology
why_it_matters: "这条内容为什么值得广义读者关注。"
summary: "中文摘要，200~300 字。"
category: news
comments: "中文精选评论，包含 Hacker News 讨论中的观点，100~200 字。"
hn_url: "https://news.ycombinator.com/item?id=..."
```

`hn_url` 是必填字段，必须来自草稿中的 `HN URL` 元数据，格式为 `https://news.ycombinator.com/item?id=...`。如果草稿缺少该字段或无法可靠恢复，跳过该故事，不能猜。

字段约束：

- `points` 必须是整数。
- `topic` 只能是 `technology`、`business`、`policy`、`science`、`society` 之一。
- `category` 只能是 `news` 或 `blog`。
- `hn_url` 必须是 `https://news.ycombinator.com/item?id=...` 格式的 Hacker News 帖子链接。
- `why_it_matters` 必须为 1 句话，且不空泛。
- 字符串值如包含冒号、特殊字符需正确引用。
- 不要在 `summary` 或 `comments` 中生成“原文链接”“阅读更多”等独立提示语，链接信息由 `url` / `hn_url` 字段承载。

主题定义：

- `technology`：技术、产品、工程、工具、开源、硬件。
- `business`：商业模式、公司战略、平台竞争、市场与定价。
- `policy`：政策、监管、治理、权利、法律与公共机构。
- `science`：科学研究、实验结果、方法学、学术进展。
- `society`：社会文化、教育、媒体、伦理、公共生活方式。

选稿规则：

- 只保留高价值、可稳定成稿且彼此不明显重复的故事。
- 原文主体大多是安全验证、登录提示、付费墙、错误信息或空白占位时，通常跳过。
- 可用信息不足以支撑可靠摘要时，通常跳过。
- `points` 最高的可用故事必须入选，并作为 writer 的热点开篇依据。
- 单一 `topic` 最多保留 3 篇。
- 如果可用稿件中 `topic != technology` 的故事至少有 3 篇，则最终结果中至少保留 3 篇非 `technology` 故事。
- 在满足上述约束的前提下，优先选择 `points` 更高且能提升主题分布的故事。
- 主题分布优先于拿第 4 篇同主题高分故事；但如果候选池本身不够多元，就如实回退，不要编造“平衡”。

生成 `$draft_yaml`：

- 添加根级 `date` 字段，值必须等于 `$target_date`。
- 只将最终入选故事整合到 `stories` 数组下。
- 按 `points` 从高到低排序；如 `points` 相同，再按标题排序，保证输出稳定。
- 缩进统一为 2 个空格。

## Phase 3：撰写内容

写作前必须读取 `.pi/skills/chinese-writing/SKILL.md`，并遵守其中“日报写作专项”与“格式一致性检查清单”。

读取 `$draft_yaml`，撰写最终 Markdown 日报到 `$daily_file`。如目录不存在请创建。

文章必须包含：

- Front matter：包含 `title`、`date`、`summary`、`tags`。
- 一级标题 `# 本期热点`：开头必须以当日 `points` 最高的文章作为切入点，再简短、亲切地概述当期主要趋势或公共讨论主题。该依据仅用于内部排序，最终成稿中不要出现 `points` 字段、分数字样或具体分数值。
- 分类板块：热点后直接进入二级标题主题分组，只渲染输入中实际存在的主题。
- 一级标题 `# 尾巴`：总结并收束全文。

主题标题映射固定如下：

- `technology` -> `## 技术与产品`
- `business` -> `## 商业与平台`
- `policy` -> `## 政策与治理`
- `science` -> `## 科学与研究`
- `society` -> `## 社会与文化`

写作约束：

- 面向好奇的广义读者，不要默认读者是开发者。
- 原文链接必须保留，并以锚文本形式嵌入段落。禁止单独列出“原文链接”或“阅读更多”。
- 每个条目末尾必须包含 `讨论见 [Hacker News 帖子](url)`，其中 `url` 来自输入的 `hn_url`。
- 必须明确区分原文观点、作者解读与 HN 社区观点；每个条目至少一次显式标注来源。
- 不要使用 Emoji。
- 不要使用 `# 文章梗概和评论反响` 作为独立标题。
- 最终成稿含 Front matter 与正文都不出现 `points` 字段、分数字样或具体分数值。

Front matter 约束：

- `title` 格式为 `"Hacker News 日报 (YYYY-MM-DD)"`。
- `date` 必须等于 `$target_date`。
- `summary` 为 1-2 句精华提炼。
- `tags` 从内容里提取关键字，公司名优先，过滤 `Hacker News`。

## Phase 4：审核与修订

读取 `$daily_file`，按以下标准审核：

1. 保留原文链接。
2. 严禁 Emoji。
3. 严禁输出文章分数及评论数目，分数和评论数仅用于撰写时内部使用。
4. 标题必须为 `"Hacker News 日报 (YYYY-MM-DD)"`。
5. 必须明确区分原文观点、作者解读与 HN 社区观点，不得把 HN 评论写成事实共识。
6. 不要默认读者是开发者；会妨碍理解的术语或行话，首次出现时应有自然、简短的上下文。
7. 必须符合 `.pi/skills/chinese-writing/SKILL.md` 中标记为“必须”“严禁”“不要”的规则。

如果发现问题，直接修改 `$daily_file`。审核与修改最多重复 3 次。3 次后仍未通过时，保存当前版本并在最终回复中说明需要人工介入。

请一次性完成所有阶段，过程中无需向用户确认。最终回复只简要说明生成的 `$daily_file` 路径和是否通过审核。
