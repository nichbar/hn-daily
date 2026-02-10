---
description: 创建日报
---

请你作为一名资深的技术编辑，帮助我创建一份关于 Hacker News 的日报。

## 时间

使用 `date -d "yesterday" +%Y-%m-%d'` 获取昨天的日期字符串，日期字符串命名位 $yesterday

## 进度管理（产物即状态）

每个阶段开始前，检查**产物是否存在**来判断恢复点：

| 阶段    | 完成标志                                      | 恢复动作                     |
| ------- | --------------------------------------------- | ---------------------------- |
| Phase 1 | `drafts/` 目录存在且有 `.md` 文件             | 跳过 Phase 1，进入 Phase 2   |
| Phase 2 | `drafts.yaml`文件存在                         | 跳过 Phase 1-2，进入 Phase 3 |
| Phase 3 | `daily/{YYYY}/{MM}/{YYYY-MM-DD}.md` 文件存在 | 跳过 Phase 1-3，进入 Phase 4 |

## 工作流程

请按照以下步骤操作，使用 `Task` 工具协调各个子任务完成工作：

### 1. 收集内容 (Phase 1)

使用 `Task` 工具调用 `crawler` 子任务：

**产出**: `drafts/` 目录下的草稿文件

### 2. 翻译整理信息 (Phase 2)

使用 `Task` 工具调用 `editor` 子任务：

```
prompt: |
  筛选整理 drafts/ 目录中的内容。

请对内容进行筛选、翻译，生成 /drafts/drafts.yaml。
```

**产出**: `drafts/drafts.yaml` ，整理后的高质量内容列表

### 3. 撰写内容 (Phase 3)

使用 `Task` 工具调用 `writer` 子任务：

```
prompt: |
撰写日报内容。

请基于 drafts.yaml 撰写日报，将 $yesterday 拆分为 $year 和 $month，并保存为 `daily/$year/$month/$yesterday.md`（如目录不存在请创建）。
```

**产出**：最终的 Markdown 日报文件 daily/$year/$month/$yesterday.md

### 4. 审核与修订 (Phase 4)

使用 `Task` 工具调用 `reviewer` 子任务：

**循环逻辑**：

- 如果 Reviewer 返回 "PASS"，则任务完成。
- 如果 Reviewer 返回修改意见，使用 `Task` 调用 `writer` 子任务进行修改。
- 再次使用 `Task` 调用 `reviewer` 子任务进行复核。
- 此过程最多重复 3 次。如果 3 次后仍未通过，请保存当前版本并提示用户人工介入。

请务必一次性完成所有任务，过程中无需向我确认，向我呈现最终的日报内容。
